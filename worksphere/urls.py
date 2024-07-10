"""
URL configuration for worksphere project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from worksphere.views.hello_world import hello_world
from worksphere.views.auth_view import login_view, logout_view
from worksphere.views.dashboard_view import dashboard_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/hello/', hello_world, name='hello_world'),
    path('api/login/', login_view, name='login'),
    path('api/logout/', logout_view, name='logout'),
    path('api/dashboard/', dashboard_view, name='dashboard'),
]
