from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.http import JsonResponse
from ..models.apikey import APIKey
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

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_emails(request):
    try:
        api_key = APIKey.objects.get(user=request.user, service='outlook')
        client_id = api_key.client_id
        tenant_id = api_key.tenant_id
        client_secret = api_key.client_secret

        token_url = f'https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token'
        token_data = {
            'grant_type': 'client_credentials',
            'client_id': client_id,
            'client_secret': client_secret,
            'scope': 'https://graph.microsoft.com/.default',
        }
        token_r = requests.post(token_url, data=token_data)
        access_token = token_r.json().get('access_token')

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        response = requests.get(
            'https://graph.microsoft.com/v1.0/me/messages',
            headers=headers
        )
        emails = response.json().get('value', [])
        formatted_emails = [
            {
                'id': email['id'],
                'sender': email['from']['emailAddress']['name'],
                'subject': email['subject'],
                'body': email['body']['content'],
                'receivedDateTime': email['receivedDateTime'],
            }
            for email in emails
        ]
        return Response({'emails': formatted_emails})
    except APIKey.DoesNotExist:
        return Response({'error': 'Outlook API key not found'}, status=400)
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_email(request):
    try:
        # Log the incoming request data
        logger.info(f"Received email send request: {request.data}")

        api_key = APIKey.objects.get(user=request.user, service='outlook')
        client_id = api_key.client_id
        tenant_id = api_key.tenant_id
        client_secret = api_key.client_secret

        # Get access token
        token_url = f'https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token'
        token_data = {
            'grant_type': 'client_credentials',
            'client_id': client_id,
            'client_secret': client_secret,
            'scope': 'https://graph.microsoft.com/.default',
        }
        token_r = requests.post(token_url, data=token_data)
        token_r.raise_for_status()  # Raise an exception for bad status codes
        access_token = token_r.json().get('access_token')

        if not access_token:
            logger.error("Failed to obtain access token")
            return Response({'error': 'Failed to authenticate with Outlook API'}, status=401)

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

        # Parse request data
        data = request.data
        to = data.get('to')
        subject = data.get('subject')
        body = data.get('body')

        if not all([to, subject, body]):
            logger.error(f"Missing required fields. Received: {data}")
            return Response({'error': 'Missing required fields: to, subject, or body'}, status=400)

        email_data = {
            'message': {
                'subject': subject,
                'body': {
                    'contentType': 'Text',
                    'content': body
                },
                'toRecipients': [
                    {
                        'emailAddress': {
                            'address': to
                        }
                    }
                ]
            }
        }

        # Send email
        response = requests.post(
            'https://graph.microsoft.com/v1.0/me/sendMail',
            headers=headers,
            json=email_data
        )
        
        response.raise_for_status()  # Raise an exception for bad status codes

        if response.status_code == 202:
            logger.info(f"Email sent successfully to {to}")
            return Response({'status': 'success'})
        else:
            logger.error(f"Unexpected response status: {response.status_code}")
            return Response({'error': 'Unexpected response from Outlook API'}, status=500)

    except APIKey.DoesNotExist:
        logger.error("Outlook API key not found for user")
        return Response({'error': 'Outlook API key not found'}, status=400)
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {str(e)}")
        return Response({'error': f'Request failed: {str(e)}'}, status=500)
    except Exception as e:
        logger.exception(f"Unexpected error occurred: {str(e)}")
        return Response({'error': f'An unexpected error occurred: {str(e)}'}, status=500)