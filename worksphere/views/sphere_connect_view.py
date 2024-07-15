from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q
from ..models.sphere_connect import Message, Group, GroupMessage, Contact
from ..models import CustomUser
import json
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_contacts(request):
    contacts = CustomUser.objects.exclude(id=request.user.id)
    contacts_data = [{
        'id': contact.id,
        'name': f"{contact.first_name} {contact.last_name}",
        'email': contact.email,
        'profile_picture': contact.profile_picture.url if contact.profile_picture else None
    } for contact in contacts]
    return Response({'contacts': contacts_data})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_private_message(request):
    sender = request.user
    recipient_id = request.data.get('recipient_id')
    content = request.data.get('content')
    if not recipient_id or not content:
        return Response({'error': 'Recipient ID and content are required'}, status=400)
    try:
        recipient = CustomUser.objects.get(id=recipient_id)
    except CustomUser.DoesNotExist:
        return Response({'error': 'Recipient not found'}, status=404)
    
    message = Message.objects.create(sender=sender, recipient=recipient, content=content)
    
    # Send message to WebSocket
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"chat_{sender.id}_{recipient.id}",
        {
            "type": "chat.message",
            "message": message.to_dict()
        }
    )
    
    return Response({
        'message': 'Message sent successfully',
        'message_data': message.to_dict()
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_private_chats(request):
    user = request.user
    private_chats = Contact.objects.filter(user=user).select_related('contact')
    
    chat_data = [{
        'id': chat.contact.id,
        'name': f"{chat.contact.first_name} {chat.contact.last_name}",
        'email': chat.contact.email,
        'profile_picture': chat.contact.profile_picture.url if chat.contact.profile_picture else None
    } for chat in private_chats]
    
    return Response({'private_chats': chat_data})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_private_messages(request):
    user = request.user
    other_user_id = request.query_params.get('user_id')
    
    if not other_user_id:
        return Response({'error': 'user_id is required'}, status=400)
    
    try:
        other_user = CustomUser.objects.get(id=other_user_id)
    except CustomUser.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)
    
    messages = Message.objects.filter(
        (Q(sender=user) & Q(recipient=other_user)) |
        (Q(sender=other_user) & Q(recipient=user))
    ).order_by('timestamp')
    
    messages_data = [message.to_dict() for message in messages]
    
    return Response({'messages': messages_data})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_group(request):
    name = request.data.get('name')
    member_ids = request.data.get('member_ids', [])
    if not name:
        return Response({'error': 'Group name is required'}, status=400)
    
    group = Group.objects.create(name=name, created_by=request.user)
    group.members.add(request.user)
    
    for member_id in member_ids:
        try:
            member = CustomUser.objects.get(id=member_id)
            group.members.add(member)
        except CustomUser.DoesNotExist:
            pass  # Silently ignore invalid member IDs
    
    return Response({
        'message': 'Group created successfully',
        'group_data': {
            'id': group.id,
            'name': group.name,
            'created_at': group.created_at,
            'created_by': request.user.first_name,
            'members': [{'id': member.id, 'name': f"{member.first_name} {member.last_name}"} for member in group.members.all()]
        }
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_groups(request):
    user = request.user
    groups = Group.objects.filter(members=user).prefetch_related('members')
    groups_data = [{
        'id': group.id,
        'name': group.name,
        'created_at': group.created_at,
        'created_by': group.created_by.first_name if group.created_by else None,
        'members': [{'id': member.id, 'name': f"{member.first_name} {member.last_name}"} for member in group.members.all()]
    } for group in groups]
    return Response({'groups': groups_data})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_group_message(request):
    group_id = request.data.get('group_id')
    content = request.data.get('content')
    if not group_id or not content:
        return Response({'error': 'Group ID and content are required'}, status=400)
    try:
        group = Group.objects.get(id=group_id, members=request.user)
    except Group.DoesNotExist:
        return Response({'error': 'Group not found or you are not a member'}, status=404)
    
    message = GroupMessage.objects.create(group=group, sender=request.user, content=content)
    message.read_by.add(request.user)  # Mark as read for the sender
    
    # Send message to WebSocket
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"group_{group.id}",
        {
            "type": "chat.message",
            "message": message.to_dict()
        }
    )
    
    return Response({
        'message': 'Message sent successfully',
        'message_data': message.to_dict()
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_group_messages(request, group_id):
    try:
        group = Group.objects.get(id=group_id, members=request.user)
    except Group.DoesNotExist:
        return Response({'error': 'Group not found or you are not a member'}, status=404)
    
    messages = GroupMessage.objects.filter(group=group).order_by('-timestamp')
    messages_data = [message.to_dict() for message in messages]
    return Response({'messages': messages_data})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_message_read(request):
    message_id = request.data.get('message_id')
    try:
        message = Message.objects.get(id=message_id, recipient=request.user)
        message.is_read = True
        message.save()
        return Response({'message': 'Message marked as read'})
    except Message.DoesNotExist:
        return Response({'error': 'Message not found'}, status=404)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_group_message_read(request):
    message_id = request.data.get('message_id')
    try:
        message = GroupMessage.objects.get(id=message_id, group__members=request.user)
        message.read_by.add(request.user)
        return Response({'message': 'Group message marked as read'})
    except GroupMessage.DoesNotExist:
        return Response({'error': 'Group message not found'}, status=404)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_user_to_channel(request):
    group_id = request.data.get('group_id')
    email = request.data.get('email')
    try:
        group = Group.objects.get(id=group_id)
        user = CustomUser.objects.get(email=email)
        group.members.add(user)
        return Response({'message': 'User added to channel successfully'})
    except Group.DoesNotExist:
        return Response({'error': 'Group not found'}, status=404)
    except CustomUser.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def remove_user_from_channel(request):
    group_id = request.data.get('group_id')
    user_id = request.data.get('user_id')
    try:
        group = Group.objects.get(id=group_id)
        user = CustomUser.objects.get(id=user_id)
        group.members.remove(user)
        return Response({'message': 'User removed from channel successfully'})
    except Group.DoesNotExist:
        return Response({'error': 'Group not found'}, status=404)
    except CustomUser.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def user_typing(request):
    channel_id = request.data.get('channel_id')
    contact_id = request.data.get('contact_id')
    is_typing = request.data.get('is_typing', False)

    channel_layer = get_channel_layer()
    if channel_id:
        async_to_sync(channel_layer.group_send)(
            f"group_{channel_id}",
            {
                "type": "typing.status",
                "user_id": request.user.id,
                "is_typing": is_typing
            }
        )
    elif contact_id:
        async_to_sync(channel_layer.group_send)(
            f"chat_{request.user.id}_{contact_id}",
            {
                "type": "typing.status",
                "user_id": request.user.id,
                "is_typing": is_typing
            }
        )
    else:
        return Response({'error': 'Either channel_id or contact_id is required'}, status=400)

    return Response({'status': 'ok'})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_recent_messages(request):
    user = request.user
    recent_messages = GroupMessage.objects.filter(
        group__members=user
    ).select_related('group', 'sender').order_by('-timestamp')[:10]
    
    messages_data = [message.to_dict() for message in recent_messages]
    
    return Response({'messages': messages_data})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_unread_sphereconnect_messages(request):
    user = request.user
    unread_messages = GroupMessage.objects.filter(
        group__members=user
    ).exclude(read_by=user).select_related('group', 'sender').order_by('-timestamp')
    
    messages_data = [message.to_dict() for message in unread_messages]
    
    return Response({'messages': messages_data})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_sphereconnect_message_read(request):
    message_id = request.data.get('message_id')
    try:
        message = GroupMessage.objects.get(id=message_id, group__members=request.user)
        message.read_by.add(request.user)
        return Response({'message': 'SphereConnect message marked as read'})
    except GroupMessage.DoesNotExist:
        return Response({'error': 'SphereConnect message not found'}, status=404)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_contact(request):
    contact_id = request.data.get('contact_id')
    if not contact_id:
        return Response({'error': 'Contact ID is required'}, status=400)
    try:
        contact = CustomUser.objects.get(id=contact_id)
        Contact.objects.get_or_create(user=request.user, contact=contact)
        return Response({'message': 'Contact added successfully'})
    except CustomUser.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def remove_contact(request):
    contact_id = request.data.get('contact_id')
    if not contact_id:
        return Response({'error': 'Contact ID is required'}, status=400)
    try:
        contact = CustomUser.objects.get(id=contact_id)
        Contact.objects.filter(user=request.user, contact=contact).delete()
        return Response({'message': 'Contact removed successfully'})
    except CustomUser.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_users(request):
    query = request.GET.get('q', '')
    if len(query) < 3:
        return Response({'error': 'Search query must be at least 3 characters long'}, status=400)
    
    users = CustomUser.objects.filter(
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query) |
        Q(email__icontains=query)
    ).exclude(id=request.user.id)[:10]  # Limit to 10 results
    
    users_data = [{
        'id': user.id,
        'name': f"{user.first_name} {user.last_name}",
        'email': user.email,
        'profile_picture': user.profile_picture.url if user.profile_picture else None
    } for user in users]
    
    return Response({'users': users_data})