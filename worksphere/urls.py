from django.contrib import admin
from django.urls import path, include
from worksphere.views.hello_world import hello_world
from worksphere.views.auth_view import login_view, logout_view
from worksphere.views.dashboard_view import dashboard_view
from worksphere.views.api_view import get_emails, start_outlook_auth, outlook_auth_callback, mark_email_read, check_outlook_connection, get_unread_emails
from worksphere.views.csrf_token_view import get_csrf_token
from worksphere.views.slack_view import start_slack_auth, slack_auth_callback, check_slack_connection, get_unread_slack_messages
from worksphere.views.sphere_connect_view import *
from worksphere.views.user_view import current_user, update_profile
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
    path('api/mark-email-read/', mark_email_read, name='mark_email_read'),
    path('api/check-outlook-connection/', check_outlook_connection, name='check_outlook_connection'),
    path('api/unread-emails/', get_unread_emails, name='get_unread_emails'),
    path('api/slack/auth/', start_slack_auth, name='start_slack_auth'),
    path('auth/slack/callback/', slack_auth_callback, name='slack_auth_callback'),
    path('api/check-slack-connection/', check_slack_connection, name='check_slack_connection'),
    path('api/get-unread-slack-messages/', get_unread_slack_messages, name='get_unread_slack_messages'),
    path('api/current-user/', current_user, name='current_user'),
    path('api/update-profile/', update_profile, name='update_profile'),
    path('api/get-contacts/', get_contacts, name='get_contacts'),
    path('api/send-private-message/', send_private_message, name='send_private_message'),
    path('api/get-private-chats/', get_private_chats, name='get_private_chats'),
    path('api/get-private-messages/', get_private_messages, name='get_private_messages'),
    path('api/create-group/', create_group, name='create_group'),
    path('api/get-groups/', get_groups, name='get_groups'),
    path('api/send-group-message/', send_group_message, name='send_group_message'),
    path('api/get-group-messages/<int:group_id>/', get_group_messages, name='get_group_messages'),
    path('api/mark-message-read/', mark_message_read, name='mark_message_read'),
    path('api/mark-group-message-read/', mark_group_message_read, name='mark_group_message_read'),
    path('api/add-user-to-channel/', add_user_to_channel, name='add_user_to_channel'),
    path('api/remove-user-from-channel/', remove_user_from_channel, name='remove_user_from_channel'),
    path('api/user-typing/', user_typing, name='user_typing'),
    path('api/get-recent-messages/', get_recent_messages, name='get_recent_messages'),
    path('api/get-unread-sphereconnect-messages/', get_unread_sphereconnect_messages, name='get_unread_sphereconnect_messages'),
    path('api/mark-sphereconnect-message-read/', mark_sphereconnect_message_read, name='mark_sphereconnect_message_read'),
    path('api/add-contact/', add_contact, name='add_contact'),
    path('api/remove-contact/', remove_contact, name='remove_contact'),
    path('api/search-users/', search_users, name='search_users'),
    path('ws/', include('worksphere.routing')),

]
