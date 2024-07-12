import json
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from ..models import CustomUser 

import logging

logger = logging.getLogger(__name__)

@csrf_exempt
@require_http_methods(["POST"])
def login_view(request):
    try:
        data = json.loads(request.body)
        email = data.get('email')
        password = data.get('password')
    except json.JSONDecodeError:
        logger.warning("Login failed: Invalid JSON")
        return JsonResponse({'success': False, 'message': 'Invalid request format'}, status=400)
    
    logger.info(f"Login attempt for email: {email}")
    
    if not email or not password:
        logger.warning("Login failed: Email or password missing")
        return JsonResponse({'success': False, 'message': 'Email and password are required'}, status=400)
    
    user = authenticate(request, email=email, password=password)
    if user is not None:
        login(request, user)
        logger.info(f"Login successful for user: {email}")
        return JsonResponse({
            'success': True, 
            'message': 'Login successful',
            'user': {
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
            }
        })
    else:
        logger.warning(f"Login failed: Invalid credentials for email: {email}")
        return JsonResponse({'success': False, 'message': 'Invalid credentials'}, status=400)

def logout_view(request):
    logout(request)
    return JsonResponse({'success': True, 'message': 'Logout successful'})