import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models.sphere_connect import Message, GroupMessage, Group
from django.contrib.auth import get_user_model

User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'chat_{self.room_name}'

        # Check authentication
        if self.scope["user"].is_anonymous:
            await self.close()
        else:
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_type = text_data_json['type']

        if message_type == 'chat.message':
            message = text_data_json['message']
            if 'group_id' in text_data_json:
                await self.save_group_message(text_data_json['group_id'], message)
            else:
                await self.save_private_message(text_data_json['recipient_id'], message)
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat.message',
                    'message': message
                }
            )
        elif message_type == 'typing.status':
            channel_id = text_data_json.get('channel_id')
            is_typing = text_data_json['is_typing']
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'typing.status',
                    'channel_id': channel_id,
                    'is_typing': is_typing
                }
            )
            
    async def chat_message(self, event):
        message = event['message']
        await self.send(text_data=json.dumps({
            'type': 'chat.message',
            'message': message
        }))

    async def typing_status(self, event):
        await self.send(text_data=json.dumps({
            'type': 'typing.status',
            'channel_id': event['channel_id'],
            'is_typing': event['is_typing']
        }))

    @database_sync_to_async
    def save_group_message(self, group_id, message):
        group = Group.objects.get(id=group_id)
        sender = User.objects.get(first_name=message['sender'])
        GroupMessage.objects.create(
            group=group,
            sender=sender,
            content=message['content']
        )

    @database_sync_to_async
    def save_private_message(self, recipient_id, message):
        sender = User.objects.get(first_name=message['sender'])
        recipient = User.objects.get(id=recipient_id)
        Message.objects.create(
            sender=sender,
            recipient=recipient,
            content=message['content']
        )