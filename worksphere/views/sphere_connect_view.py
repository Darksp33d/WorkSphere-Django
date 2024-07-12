from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q
from django.db.models import Prefetch
from ..models.sphere_connect import Message, Group, GroupMessage
from ..models import CustomUser

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
    return Response({
        'message': 'Message sent successfully',
        'message_data': {
            'id': message.id,
            'sender': sender.email,
            'recipient': recipient.email,
            'content': message.content,
            'timestamp': message.timestamp,
            'is_read': message.is_read
        }
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_private_chats(request):
    user = request.user
    private_chats = Message.objects.filter(Q(sender=user) | Q(recipient=user)).values('sender', 'recipient').distinct()
    
    chat_users = set()
    for chat in private_chats:
        chat_users.add(chat['sender'] if chat['sender'] != user.id else chat['recipient'])
    
    chat_data = []
    for user_id in chat_users:
        user = CustomUser.objects.get(id=user_id)
        chat_data.append({
            'id': user.id,
            'name': f"{user.first_name} {user.last_name}",
            'email': user.email,
            'profile_picture': user.profile_picture.url if user.profile_picture else None
        })
    
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
    
    messages_data = [{
        'id': message.id,
        'sender': message.sender.email,
        'recipient': message.recipient.email,
        'content': message.content,
        'timestamp': message.timestamp,
        'is_read': message.is_read
    } for message in messages]
    
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
            'created_by': request.user.email,
            'members': [{'id': member.id, 'name': f"{member.first_name} {member.last_name}"} for member in group.members.all()]
        }
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_groups(request):
    user = request.user
    groups = Group.objects.filter(members=user).prefetch_related(
        Prefetch('members', queryset=CustomUser.objects.only('id', 'first_name', 'last_name', 'email'))
    )
    groups_data = [{
        'id': group.id,
        'name': group.name,
        'created_at': group.created_at,
        'created_by': group.created_by.email if group.created_by else None,
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
    
    return Response({
        'message': 'Message sent successfully',
        'message_data': {
            'id': message.id,
            'group_id': group.id,
            'sender': request.user.email,
            'content': message.content,
            'timestamp': message.timestamp,
            'is_read': True  # It's read by the sender
        }
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_group_messages(request, group_id):
    try:
        group = Group.objects.get(id=group_id, members=request.user)
    except Group.DoesNotExist:
        return Response({'error': 'Group not found or you are not a member'}, status=404)
    
    messages = GroupMessage.objects.filter(group=group).order_by('-timestamp')
    messages_data = [{
        'id': message.id,
        'sender': message.sender.email,
        'content': message.content,
        'timestamp': message.timestamp,
        'is_read': message.read_by.filter(id=request.user.id).exists(),
        'channel_name': group.name
    } for message in messages]
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
def leave_group(request):
    group_id = request.data.get('group_id')
    try:
        group = Group.objects.get(id=group_id, members=request.user)
        group.members.remove(request.user)
        return Response({'message': 'You have left the group successfully'})
    except Group.DoesNotExist:
        return Response({'error': 'Group not found or you are not a member'}, status=404)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_user_to_channel(request):
    group_id = request.data.get('group_id')
    user_id = request.data.get('user_id')
    try:
        group = Group.objects.get(id=group_id)
        user = CustomUser.objects.get(id=user_id)
        group.members.add(user)
        return Response({'message': 'User added to channel successfully'})
    except Group.DoesNotExist:
        return Response({'error': 'Group not found'}, status=404)
    except CustomUser.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_recent_messages(request):
    user = request.user
    recent_messages = GroupMessage.objects.filter(
        group__members=user
    ).select_related('group', 'sender').order_by('-timestamp')[:10]
    
    messages_data = [{
        'id': message.id,
        'sender': message.sender.email,
        'content': message.content,
        'timestamp': message.timestamp,
        'channel_name': message.group.name,
        'group_id': message.group.id,
        'is_read': message.read_by.filter(id=user.id).exists()
    } for message in recent_messages]
    
    return Response({'messages': messages_data})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_unread_sphereconnect_messages(request):
    user = request.user
    unread_messages = GroupMessage.objects.filter(
        group__members=user
    ).exclude(read_by=user).select_related('group', 'sender').order_by('-timestamp')
    
    messages_data = [{
        'id': message.id,
        'sender': message.sender.email,
        'content': message.content,
        'timestamp': message.timestamp,
        'channel_name': message.group.name,
        'group_id': message.group.id,
        'is_read': False
    } for message in unread_messages]
    
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