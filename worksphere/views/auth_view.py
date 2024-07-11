from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from ..models import CustomUser 

import logging

logger = logging.getLogger(__name__)

@csrf_exempt
@require_http_methods(["POST"])
def login_view(request):
    email = request.POST.get('email')
    password = request.POST.get('password')
    
    logger.info(f"Login attempt for email: {email}")
    logger.debug(f"Request POST data: {request.POST}")
    
    if not email or not password:
        logger.warning("Login failed: Email or password missing")
        return JsonResponse({'success': False, 'message': 'Email and password are required'}, status=400)
    
    user = authenticate(request, email=email, password=password)
    if user is not None:
        login(request, user)
        logger.info(f"Login successful for user: {email}")
        return JsonResponse({'success': True, 'message': 'Login successful'})
    else:
        logger.warning(f"Login failed: Invalid credentials for email: {email}")
        return JsonResponse({'success': False, 'message': 'Invalid credentials'}, status=400)

def logout_view(request):
    logout(request)
    return JsonResponse({'success': True, 'message': 'Logout successful'})
