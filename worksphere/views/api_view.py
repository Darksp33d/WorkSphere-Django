from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.http import JsonResponse
from ..models.apikey import APIKey
import requests
import json

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
        data = request.data
        email_data = {
            'message': {
                'subject': data['subject'],
                'body': {
                    'contentType': 'Text',
                    'content': data['body']
                },
                'toRecipients': [
                    {
                        'emailAddress': {
                            'address': data['to']
                        }
                    }
                ]
            }
        }
        response = requests.post(
            'https://graph.microsoft.com/v1.0/me/sendMail',
            headers=headers,
            json=email_data
        )
        if response.status_code == 202:
            return Response({'status': 'success'})
        else:
            return Response({'error': 'Failed to send email'}, status=400)
    except APIKey.DoesNotExist:
        return Response({'error': 'Outlook API key not found'}, status=400)
    except Exception as e:
        return Response({'error': str(e)}, status=500)