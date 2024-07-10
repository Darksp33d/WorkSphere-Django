from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.http import JsonResponse
from ..models.apikey import APIKey
from ..models.email import Email
import requests
import json
import logging
from django.views.decorators.csrf import ensure_csrf_cookie

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

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_emails(request):
    try:
        api_key = APIKey.objects.get(user=request.user, service='outlook')
        client_id = api_key.client_id
        tenant_id = api_key.tenant_id
        client_secret = api_key.client_secret

        logger.info(f"Fetching emails for user: {request.user.username}")
        logger.info(f"Using client_id: {client_id}, tenant_id: {tenant_id}")

        token_url = f'https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token'
        token_data = {
            'grant_type': 'client_credentials',
            'client_id': client_id,
            'client_secret': client_secret,
            'scope': 'https://graph.microsoft.com/.default',
        }
        token_r = requests.post(token_url, data=token_data)
        logger.info(f"Token response status: {token_r.status_code}")
        logger.info(f"Token response: {token_r.text}")
        
        access_token = token_r.json().get('access_token')

        if not access_token:
            logger.error("Failed to obtain access token")
            return Response({'error': 'Failed to authenticate with Outlook API'}, status=401)

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        response = requests.get(
            'https://graph.microsoft.com/v1.0/me/messages?$top=50&$orderby=receivedDateTime DESC',
            headers=headers
        )
        logger.info(f"Graph API response status: {response.status_code}")
        logger.info(f"Graph API response: {response.text}")

        emails = response.json().get('value', [])
        logger.info(f"Number of emails fetched: {len(emails)}")

        formatted_emails = []
        for email in emails:
            email_obj, created = Email.objects.get_or_create(
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