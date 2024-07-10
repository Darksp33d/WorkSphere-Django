from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import redirect
from django.conf import settings
from ..models.outlook_auth import OutlookAuth
import requests
import logging

logger = logging.getLogger(__name__)

OUTLOOK_AUTH_URL = 'https://login.microsoftonline.com/common/oauth2/v2.0/authorize'
OUTLOOK_TOKEN_URL = 'https://login.microsoftonline.com/common/oauth2/v2.0/token'
OUTLOOK_SCOPE = 'offline_access Mail.Read'
REDIRECT_URI = 'https://worksphere-django-c79ad3982526.herokuapp.com/auth/outlook/callback/'

@api_view(['GET'])
def start_outlook_auth(request):
    auth_url = f"{OUTLOOK_AUTH_URL}?client_id={settings.OUTLOOK_CLIENT_ID}&response_type=code&redirect_uri={REDIRECT_URI}&scope={OUTLOOK_SCOPE}&response_mode=query"
    return Response({'auth_url': auth_url})

@api_view(['GET'])
def outlook_auth_callback(request):
    code = request.GET.get('code')
    if not code:
        return Response({'error': 'No code provided'}, status=400)

    data = {
        'client_id': settings.OUTLOOK_CLIENT_ID,
        'client_secret': settings.OUTLOOK_CLIENT_SECRET,
        'code': code,
        'redirect_uri': REDIRECT_URI,
        'grant_type': 'authorization_code'
    }

    response = requests.post(OUTLOOK_TOKEN_URL, data=data)
    tokens = response.json()

    if 'access_token' in tokens and 'refresh_token' in tokens:
        OutlookAuth.objects.update_or_create(
            user=request.user,
            defaults={
                'access_token': tokens['access_token'],
                'refresh_token': tokens['refresh_token'],
                'expires_in': tokens['expires_in']
            }
        )
        return redirect('/email')  # Redirect to your email interface
    else:
        return Response({'error': 'Failed to obtain tokens'}, status=400)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_emails(request):
    try:
        auth = OutlookAuth.objects.get(user=request.user)
    except OutlookAuth.DoesNotExist:
        return Response({'error': 'Outlook not connected'}, status=401)

    headers = {
        'Authorization': f'Bearer {auth.access_token}',
        'Content-Type': 'application/json'
    }

    response = requests.get(
        'https://graph.microsoft.com/v1.0/me/messages?$top=50&$orderby=receivedDateTime DESC',
        headers=headers
    )

    if response.status_code == 401:
        # Token expired, refresh it
        new_tokens = refresh_token(auth)
        if new_tokens:
            headers['Authorization'] = f'Bearer {new_tokens["access_token"]}'
            response = requests.get(
                'https://graph.microsoft.com/v1.0/me/messages?$top=50&$orderby=receivedDateTime DESC',
                headers=headers
            )
        else:
            return Response({'error': 'Failed to refresh token'}, status=401)

    if response.status_code == 200:
        emails = response.json().get('value', [])
        return Response({'emails': emails})
    else:
        return Response({'error': 'Failed to fetch emails'}, status=response.status_code)

def refresh_token(auth):
    data = {
        'client_id': settings.OUTLOOK_CLIENT_ID,
        'client_secret': settings.OUTLOOK_CLIENT_SECRET,
        'refresh_token': auth.refresh_token,
        'grant_type': 'refresh_token'
    }
    response = requests.post(OUTLOOK_TOKEN_URL, data=data)
    
    if response.status_code == 200:
        tokens = response.json()
        auth.access_token = tokens['access_token']
        auth.refresh_token = tokens.get('refresh_token', auth.refresh_token)
        auth.expires_in = tokens['expires_in']
        auth.save()
        return tokens
    else:
        logger.error(f"Failed to refresh token. Response: {response.text}")
        return None
