from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import redirect
from django.conf import settings
from ..models.outlook_auth import OutlookAuth
from ..models.email import Email
import requests
import logging

logger = logging.getLogger(__name__)

OUTLOOK_AUTH_URL = 'https://login.microsoftonline.com/common/oauth2/v2.0/authorize'
OUTLOOK_TOKEN_URL = 'https://login.microsoftonline.com/common/oauth2/v2.0/token'
OUTLOOK_SCOPE = 'offline_access Mail.ReadWrite Mail.Send'
REDIRECT_URI = 'https://worksphere-django-c79ad3982526.herokuapp.com/auth/outlook/callback/'
GRAPH_API_BASE = 'https://graph.microsoft.com/v1.0/me'

def refresh_token(auth):
    logger.info("Refreshing access token.")
    data = {
        'client_id': settings.OUTLOOK_CLIENT_ID,
        'client_secret': settings.OUTLOOK_CLIENT_SECRET,
        'refresh_token': auth.refresh_token,
        'grant_type': 'refresh_token'
    }
    response = requests.post(OUTLOOK_TOKEN_URL, data=data)
    logger.debug(f"Token refresh response: {response.status_code} {response.text}")
    
    if response.status_code == 200:
        tokens = response.json()
        auth.access_token = tokens['access_token']
        auth.refresh_token = tokens.get('refresh_token', auth.refresh_token)
        auth.expires_in = tokens['expires_in']
        auth.save()
        logger.info("Token refreshed successfully.")
        return tokens
    else:
        logger.error(f"Failed to refresh token. Response: {response.text}")
        return None

@api_view(['GET'])
def start_outlook_auth(request):
    logger.info("Starting Outlook authentication process.")
    auth_url = f"{OUTLOOK_AUTH_URL}?client_id={settings.OUTLOOK_CLIENT_ID}&response_type=code&redirect_uri={REDIRECT_URI}&scope={OUTLOOK_SCOPE}&response_mode=query"
    logger.debug(f"Generated auth URL: {auth_url}")
    return Response({'auth_url': auth_url})

@api_view(['GET'])
def outlook_auth_callback(request):
    logger.info("Handling Outlook authentication callback.")
    code = request.GET.get('code')
    if not code:
        logger.error("No code provided in the callback request.")
        return Response({'error': 'No code provided'}, status=400)

    data = {
        'client_id': settings.OUTLOOK_CLIENT_ID,
        'client_secret': settings.OUTLOOK_CLIENT_SECRET,
        'code': code,
        'redirect_uri': REDIRECT_URI,
        'grant_type': 'authorization_code'
    }
    logger.debug(f"Sending token request with data: {data}")

    response = requests.post(OUTLOOK_TOKEN_URL, data=data)
    logger.debug(f"Token request response: {response.status_code} {response.text}")
    
    if response.status_code != 200:
        logger.error(f"Token request failed with status {response.status_code}: {response.text}")
        return Response({'error': 'Failed to obtain tokens', 'details': response.text}, status=response.status_code)

    tokens = response.json()
    logger.debug(f"Received tokens: {tokens}")
    
    if 'access_token' in tokens and 'refresh_token' in tokens:
        OutlookAuth.objects.update_or_create(
            user=request.user,
            defaults={
                'access_token': tokens['access_token'],
                'refresh_token': tokens['refresh_token'],
                'expires_in': tokens['expires_in']
            }
        )
        logger.info("Tokens saved successfully. Redirecting to email interface.")
        return redirect('https://worksphere-react-2812e798f5dd.herokuapp.com/email')
    else:
        logger.error(f"Token response missing tokens: {tokens}")
        return Response({'error': 'Failed to obtain tokens', 'details': tokens}, status=400)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_emails(request):
    logger.info("Fetching emails for user.")
    try:
        auth = OutlookAuth.objects.get(user=request.user)
    except OutlookAuth.DoesNotExist:
        logger.warning("User's Outlook account is not connected.")
        return Response({'error': 'Outlook not connected'}, status=401)

    headers = {
        'Authorization': f'Bearer {auth.access_token}',
        'Content-Type': 'application/json'
    }

    response = requests.get(
        'https://graph.microsoft.com/v1.0/me/messages?$top=50&$orderby=receivedDateTime DESC',
        headers=headers
    )
    logger.debug(f"Email fetch response: {response.status_code} {response.text}")

    if response.status_code == 401:
        logger.info("Access token expired, attempting to refresh token.")
        new_tokens = refresh_token(auth)
        if new_tokens:
            headers['Authorization'] = f'Bearer {new_tokens["access_token"]}'
            response = requests.get(
                'https://graph.microsoft.com/v1.0/me/messages?$top=50&$orderby=receivedDateTime DESC',
                headers=headers
            )
        else:
            logger.error("Failed to refresh token.")
            return Response({'error': 'Failed to refresh token'}, status=401)

    if response.status_code == 200:
        emails = response.json().get('value', [])
        # Save emails to database and include read/unread status
        for email_data in emails:
            email, created = Email.objects.update_or_create(
                email_id=email_data['id'],
                defaults={
                    'user': request.user,
                    'sender': email_data['from']['emailAddress']['address'],
                    'subject': email_data['subject'],
                    'body': email_data['body']['content'],
                    'received_date_time': email_data['receivedDateTime'],
                    'is_read': email_data.get('isRead', False)
                }
            )
        logger.info("Emails fetched successfully.")
        # Return emails with read/unread status from the database
        emails = Email.objects.filter(user=request.user).values()
        return Response({'emails': list(emails)})
    else:
        logger.error(f"Failed to fetch emails with status {response.status_code}")
        return Response({'error': 'Failed to fetch emails'}, status=response.status_code)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_email_read(request):
    logger.info("Marking email as read/unread.")
    email_id = request.data.get('email_id')
    is_read = request.data.get('is_read', True)
    try:
        email = Email.objects.get(email_id=email_id, user=request.user)
        email.is_read = is_read
        email.save()
        logger.info(f"Email with ID: {email_id} marked as {'read' if is_read else 'unread'}.")
        return Response({'status': 'Email marked as read/unread successfully'})
    except Email.DoesNotExist:
        logger.error(f"Email with ID: {email_id} not found.")
        return Response({'error': 'Email not found'}, status=404)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_outlook_connection(request):
    logger.info("Checking if user's Outlook account is connected.")
    try:
        auth = OutlookAuth.objects.get(user=request.user)
        return Response({'connected': True})
    except OutlookAuth.DoesNotExist:
        return Response({'connected': False})
