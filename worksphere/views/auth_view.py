from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return JsonResponse({'success': True, 'message': 'Login successful'})
        else:
            return JsonResponse({'success': False, 'message': 'Invalid credentials'}, status=400)
    return JsonResponse({'message': 'Method not allowed'}, status=405)

def logout_view(request):
    logout(request)
    return JsonResponse({'success': True, 'message': 'Logout successful'})