from django.contrib import admin
from django.urls import path
from worksphere.views.hello_world import hello_world
from worksphere.views.auth_view import login_view, logout_view
from worksphere.views.dashboard_view import dashboard_view
from worksphere.views.api_view import manage_api_key, get_emails, send_email

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/hello/', hello_world, name='hello_world'),
    path('api/login/', login_view, name='login'),
    path('api/logout/', logout_view, name='logout'),
    path('api/dashboard/', dashboard_view, name='dashboard'),
    path('api/manage-key/', manage_api_key, name='manage_api_key'),
    path('api/emails/', get_emails, name='get_emails'),
    path('api/send-email/', send_email, name='send_email'),
]
