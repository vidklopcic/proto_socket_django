from django.apps import AppConfig

from proto_socket_django.app_channel.app_channel import AppChannel


class ApiConfig(AppConfig):
    name = 'proto_socket_django'

    def ready(self):
        AppChannel.init()
