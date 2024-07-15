import os
from django.core.asgi import get_asgi_application
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
import worksphere.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'worksphere.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            worksphere.routing.websocket_urlpatterns
        )
    ),
})
