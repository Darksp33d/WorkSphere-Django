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
        service = data.get('service')
        key = data.get('key')
        APIKey.objects.update_or_create(
            user=request.user,
            service=service,
            defaults={'key': key}
        )
        return JsonResponse({'status': 'success'})
    elif request.method == 'DELETE':
        data = json.loads(request.body)
        service = data.get('service')
        APIKey.objects.filter(user=request.user, service=service).delete()
        return JsonResponse({'status': 'success'})
    elif request.method == 'GET':
        keys = APIKey.objects.filter(user=request.user).values('service', 'key')
        return JsonResponse({'keys': list(keys)})

@login_required
def get_emails(request):
    try:
        api_key = APIKey.objects.get(user=request.user, service='outlook')
        headers = {
            'Authorization': f'Bearer {api_key.key}',
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
            headers = {
                'Authorization': f'Bearer {api_key.key}',
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
