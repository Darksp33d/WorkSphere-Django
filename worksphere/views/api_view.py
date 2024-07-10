from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from ..models.apikey import APIKey
import json
import requests

@login_required
@csrf_exempt
def manage_api_key(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        client_id = data.get('clientId')
        tenant_id = data.get('tenantId')
        client_secret = data.get('clientSecret')
        APIKey.objects.update_or_create(
            user=request.user,
            service='outlook',
            defaults={'client_id': client_id, 'tenant_id': tenant_id, 'client_secret': client_secret}
        )
        return JsonResponse({'status': 'success'})
    elif request.method == 'DELETE':
        data = json.loads(request.body)
        service = data.get('service')
        APIKey.objects.filter(user=request.user, service=service).delete()
        return JsonResponse({'status': 'success'})
    elif request.method == 'GET':
        keys = APIKey.objects.filter(user=request.user, service='outlook').values('client_id', 'tenant_id', 'client_secret')
        if keys.exists():
            keys = keys.first()
            return JsonResponse({'keys': keys})
        else:
            return JsonResponse({'keys': {}})

@login_required
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
        return JsonResponse({'emails': emails})
    except APIKey.DoesNotExist:
        return JsonResponse({'error': 'Outlook API key not found'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@csrf_exempt
def send_email(request):
    if request.method == 'POST':
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
            data = json.loads(request.body)
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
                return JsonResponse({'status': 'success'})
            else:
                return JsonResponse({'error': 'Failed to send email'}, status=400)
        except APIKey.DoesNotExist:
            return JsonResponse({'error': 'Outlook API key not found'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
