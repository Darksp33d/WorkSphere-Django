import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models.sphere_connect import Message, GroupMessage

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'chat_{self.room_name}'

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
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat.message',
                    'message': message
                }
            )
        elif message_type == 'typing.status':
            user_id = text_data_json['user_id']
            is_typing = text_data_json['is_typing']
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'typing.status',
                    'user_id': user_id,
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
        user_id = event['user_id']
        is_typing = event['is_typing']
        await self.send(text_data=json.dumps({
            'type': 'typing.status',
            'user_id': user_id,
            'is_typing': is_typing
        }))