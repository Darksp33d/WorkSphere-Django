from django.http import JsonResponse
from django.views.decorators.http import require_GET

@require_GET
def hello_world(request):
    return JsonResponse({"message": "Hello, World!"})
