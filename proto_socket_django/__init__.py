import abc
import datetime
import uuid
from typing import Union, Type, Dict, List, Callable, Optional
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


class FPSReceiverError:
    def __init__(self, message):
        self.message = message


# decorators
#
def receive(message: Type[pb.RxMessage], permissions: List[str] = None, auth: bool = True):
    def _receive(method):
        from django.contrib.auth.models import User
        def wrapper(self, message_data: pb.RxMessageData, user: User):
            # check permissions
            if (auth and user is None) or (user and permissions and not user.has_perms(permissions)):
                raise Exception('unauthorized')

            # call receiver implementation
            result = method(self, message(message_data), user)

            # handle ack
            if message_data.ack:
                ack_message = pb.TxAck(pb.Ack(uuid=message_data.uuid))
                if type(result) is FPSReceiverError:
                    ack_message.proto.error_message = result.message
                self.consumer.send_message(ack_message)

            return result

        wrapper.__receive = message
        wrapper.__receive_auth = auth
        wrapper.__receive_permissions = permissions
        return wrapper

    return _receive


def generate_proto(f):
    return f


def to_timestamp(datetime: datetime.datetime) -> Optional[int]:
    if datetime is None:
        return None
    return int(datetime.timestamp() * 1000)


def from_timestamp(ts) -> Optional[datetime.datetime]:
    if ts is None:
        return None
    return datetime.datetime.fromtimestamp(ts / 1000)
