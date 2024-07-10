from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

import logging

logger = logging.getLogger(__name__)

@csrf_exempt
@require_http_methods(["POST"])
def login_view(request):
    username = request.POST.get('username')
    password = request.POST.get('password')
    
    logger.info(f"Login attempt for username: {username}")
    logger.debug(f"Request POST data: {request.POST}")
    
    if not username or not password:
        logger.warning("Login failed: Username or password missing")
        return JsonResponse({'success': False, 'message': 'Username and password are required'}, status=400)
    
    user = authenticate(request, username=username, password=password)
    if user is not None:
        login(request, user)
        logger.info(f"Login successful for user: {username}")
        return JsonResponse({'success': True, 'message': 'Login successful'})
    else:
        logger.warning(f"Login failed: Invalid credentials for username: {username}")
        return JsonResponse({'success': False, 'message': 'Invalid credentials'}, status=400)

def logout_view(request):
    logout(request)
    return JsonResponse({'success': True, 'message': 'Logout successful'})