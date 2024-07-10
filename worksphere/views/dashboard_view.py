from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

@login_required
def dashboard_view(request):
    return JsonResponse({'message': 'Welcome to the dashboard', 'username': request.user.username})