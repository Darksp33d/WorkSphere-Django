from django.shortcuts import redirect
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
import requests
from ..models import SlackAuth

SLACK_CLIENT_ID = settings.SLACK_CLIENT_ID
SLACK_CLIENT_SECRET = settings.SLACK_CLIENT_SECRET
SLACK_REDIRECT_URI = settings.SLACK_REDIRECT_URI

@api_view(['GET'])
def start_slack_auth(request):
    auth_url = f"https://slack.com/oauth/v2/authorize?client_id={SLACK_CLIENT_ID}&scope=channels:history,groups:history,im:history,mpim:history,channels:read,groups:read,im:read,mpim:read&redirect_uri={SLACK_REDIRECT_URI}"
    return redirect(auth_url)

@api_view(['GET'])
def slack_auth_callback(request):
    code = request.GET.get('code')
    response = requests.post('https://slack.com/api/oauth.v2.access', data={
        'client_id': SLACK_CLIENT_ID,
        'client_secret': SLACK_CLIENT_SECRET,
        'code': code,
        'redirect_uri': SLACK_REDIRECT_URI
    })
    data = response.json()
    if data['ok']:
        SlackAuth.objects.update_or_create(
            user=request.user,
            defaults={'access_token': data['access_token']}
        )
        return redirect('https://your-frontend-url/settings')
    return Response({'error': 'Slack authentication failed'}, status=400)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_slack_connection(request):
    try:
        SlackAuth.objects.get(user=request.user)
        return Response({'connected': True})
    except SlackAuth.DoesNotExist:
        return Response({'connected': False})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_unread_slack_messages(request):
    try:
        slack_auth = SlackAuth.objects.get(user=request.user)
        headers = {
            'Authorization': f'Bearer {slack_auth.access_token}',
            'Content-Type': 'application/json'
        }
        
        # Fetch unread messages from Slack
        channels_response = requests.get('https://slack.com/api/conversations.list?types=public_channel,private_channel,im,mpim', headers=headers)
        if not channels_response.json().get('ok'):
            return Response({'error': 'Failed to fetch channels'}, status=400)

        unread_messages = []
        for channel in channels_response.json().get('channels', []):
            history_response = requests.get(f'https://slack.com/api/conversations.history?channel={channel["id"]}', headers=headers)
            if history_response.json().get('ok'):
                messages = history_response.json().get('messages', [])
                unread_messages.extend([msg for msg in messages if not msg.get('is_read')])

        return Response({'messages': unread_messages})
    except SlackAuth.DoesNotExist:
        return Response({'error': 'Slack not connected'}, status=401)
