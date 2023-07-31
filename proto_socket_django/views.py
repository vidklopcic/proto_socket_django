from django.http import HttpResponse
from rest_framework_simplejwt.tokens import AccessToken


def auth_header(request):
    if request.user:
        return HttpResponse(AccessToken.for_user(request.user).token)
    else:
        return HttpResponse(status=401)
