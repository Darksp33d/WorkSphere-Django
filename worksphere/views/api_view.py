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
    auth_url += '?' + '&'.join(f"{key}={value}" for key, value in params.items())
    return JsonResponse({'auth_url': auth_url})

@login_required(login_url=None)
def auth_callback(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'User not authenticated'}, status=401)

    code = request.GET.get('code')
    api_key = APIKey.objects.get(user=request.user, service='outlook')
    token_url = f"https://login.microsoftonline.com/{api_key.tenant_id}/oauth2/v2.0/token"
    data = {
        'client_id': api_key.client_id,
        'client_secret': api_key.client_secret,
        'code': code,
        'redirect_uri': 'https://worksphere-django-c79ad3982526.herokuapp.com/auth/callback/',
        'grant_type': 'authorization_code'
    }
    response = requests.post(token_url, data=data)
    tokens = response.json()
    
    api_key.access_token = tokens.get('access_token')
    api_key.refresh_token = tokens.get('refresh_token')
    api_key.save()

    return redirect('https://worksphere-react-2812e798f5dd.herokuapp.com/email')

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_emails(request):
    try:
        api_key = APIKey.objects.get(user=request.user, service='outlook')
        
        headers = {
            'Authorization': f'Bearer {api_key.access_token}',
            'Content-Type': 'application/json'
        }
        response = requests.get(
            'https://graph.microsoft.com/v1.0/me/messages?$top=50&$orderby=receivedDateTime DESC',
            headers=headers
        )
        
        if response.status_code == 401:
            # Token expired, refresh it
            new_tokens = refresh_token(api_key)
            api_key.access_token = new_tokens['access_token']
            api_key.refresh_token = new_tokens['refresh_token']
            api_key.save()
            # Retry the request with the new token
            headers['Authorization'] = f'Bearer {api_key.access_token}'
            response = requests.get(
                'https://graph.microsoft.com/v1.0/me/messages?$top=50&$orderby=receivedDateTime DESC',
                headers=headers
            )

        logger.info(f"Graph API response status: {response.status_code}")
        
        emails = response.json().get('value', [])
        logger.info(f"Number of emails fetched: {len(emails)}")

        formatted_emails = []
        for email in emails:
            email_obj, created = Email.objects.update_or_create(
                user=request.user,
                email_id=email['id'],
                defaults={
                    'sender': email['from']['emailAddress']['name'],
                    'subject': email['subject'],
                    'body': email['body']['content'],
                    'received_date_time': email['receivedDateTime'],
                    'is_read': email['isRead']
                }
            )
            formatted_emails.append({
                'id': email_obj.email_id,
                'sender': email_obj.sender,
                'subject': email_obj.subject,
                'body': email_obj.body,
                'receivedDateTime': email_obj.received_date_time,
                'isRead': email_obj.is_read
            })
        logger.info(f"Number of formatted emails: {len(formatted_emails)}")
        return Response({'emails': formatted_emails})
    except APIKey.DoesNotExist:
        logger.error("Outlook API key not found for user")
        return Response({'error': 'Outlook API key not found'}, status=400)
    except Exception as e:
        logger.exception(f"Unexpected error occurred: {str(e)}")
        return Response({'error': str(e)}, status=500)

def refresh_token(api_key):
    token_url = f"https://login.microsoftonline.com/{api_key.tenant_id}/oauth2/v2.0/token"
    data = {
        'client_id': api_key.client_id,
        'client_secret': api_key.client_secret,
        'refresh_token': api_key.refresh_token,
        'grant_type': 'refresh_token'
    }
    response = requests.post(token_url, data=data)
    return response.json()

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