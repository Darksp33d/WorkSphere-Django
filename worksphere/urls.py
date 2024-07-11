from django.contrib import admin
from django.urls import path
from worksphere.views.hello_world import hello_world
from worksphere.views.auth_view import login_view, logout_view
from worksphere.views.dashboard_view import dashboard_view
from worksphere.views.api_view import get_emails, start_outlook_auth, outlook_auth_callback
from worksphere.views.csrf_token_view import get_csrf_token

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/hello/', hello_world, name='hello_world'),
    path('api/login/', login_view, name='login'),
    path('api/logout/', logout_view, name='logout'),
    path('api/dashboard/', dashboard_view, name='dashboard'),
    path('get-csrf-token/', get_csrf_token, name='get_csrf_token'),
    path('api/outlook/auth/', start_outlook_auth, name='start_outlook_auth'),
    path('auth/outlook/callback/', outlook_auth_callback, name='outlook_auth_callback'),
    path('api/emails/', get_emails, name='get_emails'),
]