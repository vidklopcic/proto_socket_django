from django.apps import AppConfig

from proto_socket_django import ApiWebsocketConsumer


class ApiConfig(AppConfig):
    name = 'proto_socket_django'

    def ready(self):
        ApiWebsocketConsumer.static_init()