import json
import traceback

from django.http import HttpResponse
from rest_framework_simplejwt.tokens import AccessToken


def auth_header(request):
    return HttpResponse(AccessToken.for_user(request.user).token)


def psd_endpoint(consumer: ApiHttpConsumer):
    def _psd_endpoint(request):
        if request.method != 'POST':
            return HttpResponse(status=405)

        try:
            messages = json.loads(request.body)

            for message in messages:
                try:
                    consumer.receive_json(message)
                except:
                    traceback.print_exc()

            return HttpResponse(consumer.collect_result())
        except:
            traceback.print_exc()
            return HttpResponse(status=400)

    return _psd_endpoint
