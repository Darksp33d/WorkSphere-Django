from rest_framework.decorators import api_view, permission_classes
from django.contrib.auth.decorators import login_required
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from ..models.apikey import APIKey
from ..models.email import Email
import requests
import json
import logging

logger = logging.getLogger(__name__)

@api_view(['GET', 'POST', 'DELETE'])
@permission_classes([IsAuthenticated])
def manage_api_key(request):
    if request.method == 'POST':
        data = request.data
        client_id = data.get('clientId')
        tenant_id = data.get('tenantId')
        client_secret = data.get('clientSecret')
        APIKey.objects.update_or_create(
            user=request.user,
            service='outlook',
            defaults={'client_id': client_id, 'tenant_id': tenant_id, 'client_secret': client_secret}
        )
        return Response({'status': 'success'})
    elif request.method == 'DELETE':
        data = request.data
        service = data.get('service')
        APIKey.objects.filter(user=request.user, service=service).delete()
        return Response({'status': 'success'})
    elif request.method == 'GET':
        keys = APIKey.objects.filter(user=request.user, service='outlook').values('client_id', 'tenant_id', 'client_secret')
        if keys.exists():
            keys = keys.first()
            return Response({'keys': keys})
        else:
            return Response({'keys': {}})

@login_required(login_url=None)
def start_auth(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'User not authenticated'}, status=401)

    api_key, created = APIKey.objects.get_or_create(user=request.user, service='outlook')
    auth_url = f"https://login.microsoftonline.com/{api_key.tenant_id}/oauth2/v2.0/authorize"
    params = {
        'client_id': api_key.client_id,
        'response_type': 'code',
        'redirect_uri': 'https://worksphere-django-c79ad3982526.herokuapp.com/auth/callback/',
        'scope': 'offline_access Mail.Read',
        'response_mode': 'query'
    }
    full_auth_url = auth_url + '?' + '&'.join(f"{key}={value}" for key, value in params.items())
    return JsonResponse({'auth_url': full_auth_url})

@login_required(login_url=None)
def auth_callback(request):
    logger.info(f"Auth callback received for user: {request.user.username}")
    if not request.user.is_authenticated:
        logger.error("User not authenticated in auth_callback")
        return JsonResponse({'error': 'User not authenticated'}, status=401)

    code = request.GET.get('code')
    if not code:
        logger.error("Authorization code not received in auth_callback")
        return JsonResponse({'error': 'Authorization code not received'}, status=400)

    try:
        api_key = APIKey.objects.get(user=request.user, service='outlook')
        logger.info(f"API key retrieved for user: {request.user.username}")
        
        token_url = f"https://login.microsoftonline.com/{api_key.tenant_id}/oauth2/v2.0/token"
        data = {
            'client_id': api_key.client_id,
            'client_secret': api_key.client_secret,
            'code': code,
            'redirect_uri': 'https://worksphere-django-c79ad3982526.herokuapp.com/auth/callback/',
            'grant_type': 'authorization_code'
        }
        response = requests.post(token_url, data=data)
        logger.info(f"Token exchange response status: {response.status_code}")
        
        tokens = response.json()
        if 'access_token' in tokens and 'refresh_token' in tokens:
            api_key.access_token = tokens['access_token']
            api_key.refresh_token = tokens['refresh_token']
            api_key.save()
            logger.info(f"Tokens successfully saved for user: {request.user.username}")
            return redirect('https://worksphere-react-2812e798f5dd.herokuapp.com/email')
        else:
            logger.error(f"Failed to obtain tokens. Response: {tokens}")
            return JsonResponse({'error': 'Failed to obtain tokens'}, status=400)
    except APIKey.DoesNotExist:
        logger.error(f"API key not found for user: {request.user.username}")
        return JsonResponse({'error': 'API key not found'}, status=400)
    except Exception as e:
        logger.exception(f"Unexpected error in auth_callback: {str(e)}")
        return JsonResponse({'error': 'Unexpected error occurred'}, status=500)
    
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_emails(request):
    try:
        logger.info(f"Attempting to fetch emails for user: {request.user.username}")
        api_key = APIKey.objects.get(user=request.user, service='outlook')
        logger.info(f"API key retrieved for user: {request.user.username}")
        
        headers = {
            'Authorization': f'Bearer {api_key.access_token}',
            'Content-Type': 'application/json'
        }
        logger.info("Making request to Microsoft Graph API")
        response = requests.get(
            'https://graph.microsoft.com/v1.0/me/messages?$top=50&$orderby=receivedDateTime DESC',
            headers=headers
        )
        
        logger.info(f"Graph API response status: {response.status_code}")
        logger.info(f"Graph API response content: {response.text[:200]}...")  # Log first 200 characters
        
        if response.status_code == 401:
            logger.warning("Received 401 from Graph API, attempting to refresh token")
            new_tokens = refresh_token(api_key)
            if new_tokens:
                headers['Authorization'] = f'Bearer {new_tokens["access_token"]}'
                response = requests.get(
                    'https://graph.microsoft.com/v1.0/me/messages?$top=50&$orderby=receivedDateTime DESC',
                    headers=headers
                )
                logger.info(f"Graph API response after token refresh: {response.status_code}")
            else:
                logger.error("Failed to refresh token")
                return Response({'error': 'Failed to refresh token'}, status=401)
        
        if response.status_code == 200:
            emails = response.json().get('value', [])
            logger.info(f"Number of emails fetched: {len(emails)}")
            return Response({'emails': emails})
        else:
            logger.error(f"Failed to fetch emails. Status code: {response.status_code}")
            return Response({'error': 'Failed to fetch emails'}, status=response.status_code)
        
    except APIKey.DoesNotExist:
        logger.error(f"Outlook API key not found for user: {request.user.username}")
        return Response({'error': 'Outlook API key not found'}, status=400)
    except Exception as e:
        logger.exception(f"Unexpected error occurred: {str(e)}")
        return Response({'error': str(e)}, status=500)

def refresh_token(api_key):
    logger.info(f"Attempting to refresh token for user: {api_key.user.username}")
    token_url = f"https://login.microsoftonline.com/{api_key.tenant_id}/oauth2/v2.0/token"
    data = {
        'client_id': api_key.client_id,
        'client_secret': api_key.client_secret,
        'refresh_token': api_key.refresh_token,
        'grant_type': 'refresh_token'
    }
    response = requests.post(token_url, data=data)
    logger.info(f"Token refresh response status: {response.status_code}")
    
    if response.status_code == 200:
        tokens = response.json()
        api_key.access_token = tokens['access_token']
        if 'refresh_token' in tokens:
            api_key.refresh_token = tokens['refresh_token']
        api_key.save()
        logger.info("Token refreshed successfully")
        return tokens
    else:
        logger.error(f"Failed to refresh token. Response: {response.text}")
        return None
    
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_as_read(request):
    try:
        email_id = request.data.get('emailId')
        email = Email.objects.get(user=request.user, email_id=email_id)
        email.is_read = True
        email.save()

        # You might want to sync this with Outlook as well
        # This would require additional API calls to Microsoft Graph

        return Response({'status': 'success'})
    except Email.DoesNotExist:
        return Response({'error': 'Email not found'}, status=404)
    except Exception as e:
        logger.exception(f"Unexpected error occurred: {str(e)}")
        return Response({'error': str(e)}, status=500)