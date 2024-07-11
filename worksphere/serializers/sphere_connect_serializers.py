from rest_framework import serializers
from ..models.sphere_connect import Message, Group, GroupMessage
from ..models import CustomUser

class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'first_name', 'last_name', 'phone_number', 'profile_pic']
        read_only_fields = ['id']

class MessageSerializer(serializers.ModelSerializer):
    sender = CustomUserSerializer(read_only=True)
    recipient = CustomUserSerializer(read_only=True)
    recipient_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Message
        fields = ['id', 'sender', 'recipient', 'recipient_id', 'content', 'timestamp', 'is_read']
        read_only_fields = ['id', 'sender', 'timestamp']

    def create(self, validated_data):
        recipient_id = validated_data.pop('recipient_id')
        recipient = CustomUser.objects.get(id=recipient_id)
        return Message.objects.create(recipient=recipient, **validated_data)

class GroupSerializer(serializers.ModelSerializer):
    members = CustomUserSerializer(many=True, read_only=True)
    member_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )

    class Meta:
        model = Group
        fields = ['id', 'name', 'members', 'member_ids', 'created_at']
        read_only_fields = ['id', 'created_at']

    def create(self, validated_data):
        member_ids = validated_data.pop('member_ids', [])
        group = Group.objects.create(**validated_data)
        group.members.add(*member_ids)
        return group

class GroupMessageSerializer(serializers.ModelSerializer):
    sender = CustomUserSerializer(read_only=True)
    group = GroupSerializer(read_only=True)
    group_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = GroupMessage
        fields = ['id', 'group', 'group_id', 'sender', 'content', 'timestamp']
        read_only_fields = ['id', 'sender', 'timestamp']

    def create(self, validated_data):
        group_id = validated_data.pop('group_id')
        group = Group.objects.get(id=group_id)
        return GroupMessage.objects.create(group=group, **validated_data)