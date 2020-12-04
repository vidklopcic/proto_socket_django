import abc
import uuid
from typing import Union, Type, Dict, List, Callable

from asgiref.sync import async_to_sync
from channels.generic.websocket import JsonWebsocketConsumer
from channels.layers import get_channel_layer
from proto.messages import TxMessage
import proto.messages as pb


# API
#
class ApiWebsocketConsumer(JsonWebsocketConsumer):
    receivers: List[Type['FPSReceiver']] = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = None
        self.token = None
        self.handlers: Dict[str, List[Callable]] = {}

        # register all receivers
        for receiver in self.receivers:
            receiver_instance = receiver(self)
            for member_name, method in receiver.__dict__.items():
                if hasattr(method, "__receive"):
                    mtype = getattr(method, "__receive").type
                    if mtype not in self.handlers:
                        self.handlers[mtype] = []
                    self.handlers[mtype].append(getattr(receiver_instance, member_name))

    def send_message(self, message: TxMessage):
        json = message.get_message()
        print('tx:', json)
        self.send_json(json)

    def connect(self):
        self.accept()

    def receive_json(self, json_data, **kwargs):
        from authentication.models import Token
        print('rx:', json_data)
        data = pb.RxMessageData(json_data)
        if data.authHeader != self.token and data.authHeader:
            self.token = data.authHeader
            self.user = Token.authenticate(data.authHeader)
        for handler in self.handlers.get(data.type, []):
            handler(data, self.user)

    def broadcast_message(self, event):
        print('tx broadcast:', event['event'])
        self.send_json(event['event'])

    @staticmethod
    def broadcast(group: str, message: TxMessage):
        async_to_sync(get_channel_layer().group_send)(group,
                                                      {'type': 'broadcast.message', 'event': message.get_message()})


class FPSReceiver(abc.ABC):
    receivers: Dict[str, str] = {}

    def __init__(self, consumer: ApiWebsocketConsumer):
        self.consumer = consumer


# decorators
#
def receive(message: Type[pb.RxMessage], permissions: List[str] = None, auth: bool = True):
    def _receive(method):
        from django.contrib.auth.models import User
        def wrapper(self, message_data: pb.RxMessageData, user: User):
            if (auth and user is None) or (user and permissions and not user.has_perms(permissions)):
                raise Exception('unauthorized')
            return method(self, message(message_data), user)
        wrapper.__receive = message
        wrapper.__receive_auth = auth
        wrapper.__receive_permissions = permissions
        return wrapper

    return _receive


def generate_proto(f):
    return f
