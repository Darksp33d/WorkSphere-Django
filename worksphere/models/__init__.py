def get_apikey_model():
    from .apikey import APIKey
    return APIKey

def get_email_model():
    from .email import Email
    return Email

def get_outlook_auth_model():
    from .outlook_auth import OutlookAuth
    return OutlookAuth

def get_slack_auth_model():
    from .slack_auth import SlackAuth
    return SlackAuth

def get_user_model():
    from .user import CustomUser
    return CustomUser

def get_sphere_connect_models():
    from .sphere_connect import Contact, Group, Message, GroupMessage
    return Contact, Group, Message, GroupMessage

# You can use these functions to get the models when needed
APIKey = get_apikey_model()
Email = get_email_model()
OutlookAuth = get_outlook_auth_model()
SlackAuth = get_slack_auth_model()
CustomUser = get_user_model()
Contact, Group, Message, GroupMessage = get_sphere_connect_models()

# If you need to use these models elsewhere, import them like this:
# from worksphere.models import APIKey, Email, OutlookAuth, SlackAuth, CustomUser, Contact, Group, Message, GroupMessage