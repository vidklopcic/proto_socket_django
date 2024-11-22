from django.apps import AppConfig
import sys
from proto_socket_django import ApiWebsocketConsumer


class ApiConfig(AppConfig):
    name = 'proto_socket_django'

    def ready(self):
        if 'manage.py' not in sys.argv:
            ApiWebsocketConsumer.static_init()