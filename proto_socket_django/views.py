from django.http import HttpResponse
from rest_framework_simplejwt.tokens import AccessToken


def auth_header(request):
    if request.user.is_authenticated:
        return HttpResponse(str(AccessToken.for_user(request.user)))
    else:
        return HttpResponse(status=401)
