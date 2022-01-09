import abc
import datetime
from typing import Union, Type, Dict, List, Callable, Optional, Any
import pytz
from asgiref.sync import async_to_sync
from channels.generic.websocket import JsonWebsocketConsumer
from channels.layers import get_channel_layer
from django.utils import timezone
from proto.messages import TxMessage, RxMessage
import proto.messages as pb
from django.conf import settings
import threading

from proto_socket_django.async_worker import AsyncWorker, AsyncMessage


class ApiWebsocketConsumer(JsonWebsocketConsumer):
    receivers: List[Type['FPSReceiver']] = []
    async_workers: List[AsyncWorker] = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # spawn async workers on first connection
        if self.async_workers is None:
            self.async_workers = []
            for i in range(getattr(settings, 'PSD_N_ASYNC_WORKERS', 0)):
                print('starting async worker', i)
                self.async_workers.append(AsyncWorker())

        self.receiver_instances = {}
        self.registered_groups = []
        self.user = None
        self.token = None
        self.handlers: Dict[str, List[Callable]] = {}

        # register all receivers
        for receiver in self.receivers:
            receiver_instance = receiver(self)
            self.receiver_instances[receiver] = receiver_instance
            for member_name, method in receiver.__dict__.items():
                if hasattr(method, "__receive"):
                    mtype = getattr(method, "__receive").type
                    if mtype not in self.handlers:
                        self.handlers[mtype] = []
                    self.handlers[mtype].append(getattr(receiver_instance, member_name))

    def send_message(self, message: TxMessage):
        json = message.get_message()
        if settings.DEBUG:
            print('tx:', json)
        self.send_json(json)

    def connect(self):
        self.accept()

    def authenticate(self):
        from authentication.models import Token
        self.user = Token.authenticate(self.token)
        if self.user:
            self.on_authenticated()
        else:
            self.send_message(pb.TxTokenInvalid())
            return

    def receive_json(self, json_data, **kwargs):
        if settings.DEBUG:
            print('rx:', json_data)
        data = pb.RxMessageData(json_data)

        if data.authHeader != self.token and data.authHeader:
            self.token = data.authHeader
            self.authenticate()

        for handler in self.handlers.get(data.type, []):
            handler(data, self.user)

    def on_authenticated(self):
        pass

    def broadcast_message(self, event):
        self.send_json(event['event'])

    @staticmethod
    def broadcast(group: str, message: TxMessage):
        async_to_sync(get_channel_layer().group_send)(group,
                                                      {'type': 'broadcast.message', 'event': message.get_message()})

    def remove_groups(self):
        for name in self.registered_groups:
            async_to_sync(self.channel_layer.group_discard)(name, self.channel_name)

    def add_group(self, name):
        if name in self.registered_groups:
            return
        async_to_sync(self.channel_layer.group_add)(name, self.channel_name)
        self.registered_groups.append(name)

    def remove_group(self, name):
        if name not in self.registered_groups:
            return
        async_to_sync(self.channel_layer.group_discard)(name, self.channel_name)
        self.registered_groups.remove(name)

    def disconnect(self, close_code):
        self.remove_groups()


class FPSReceiver(abc.ABC):
    receivers: Dict[str, str] = {}

    def __init__(self, consumer: ApiWebsocketConsumer):
        self.consumer = consumer

    def continue_async(self, handler: Callable[[RxMessage], Union[Any, None]], message: RxMessage):
        if not self.consumer.async_workers:
            raise Exception('No async workers. PSD_N_ASYNC_WORKERS should be greater than 0.')

        async_message = AsyncMessage(
            handler=handler,
            message=message,
        )
        AsyncWorker.message_queue.append(async_message)
        return async_message


class FPSReceiverError:
    def __init__(self, message):
        self.message = message


# decorators
#
def receive(permissions: List[str] = None, auth: bool = None, whitelist_groups: List[str] = None,
            blacklist_groups: List[str] = None):
    if auth is None:
        auth = getattr(settings, 'PSD_DEFAULT_AUTH', True)

    def _receive(method):
        message = method.__annotations__.get('message')
        assert message is not None and hasattr(message, 'proto')

        from django.contrib.auth.models import User
        def wrapper(self: FPSReceiver, message_data: pb.RxMessageData, user: User):
            authorized = True
            if auth and user is None:
                authorized = False
            elif user and permissions and not user.has_perms(permissions):
                authorized = False
            elif user and whitelist_groups and not user.groups.filter(name__in=whitelist_groups).exists():
                authorized = False
            elif user and blacklist_groups and user.groups.filter(name__in=blacklist_groups).exists():
                authorized = False

            if not authorized:
                raise Exception('unauthorized')

            # call receiver implementation
            result = method(self, message(message_data, user))

            # handle ack
            if message_data.ack:
                def _handle_result(result):
                    ack_message = pb.TxAck(pb.Ack(uuid=message_data.uuid))
                    if type(result) is FPSReceiverError:
                        ack_message.proto.error_message = result.message
                    self.consumer.send_message(ack_message)

                if type(result) is AsyncMessage:
                    result.on_result = _handle_result
                else:
                    _handle_result(result)

            return result

        wrapper.__receive = message
        wrapper.__receive_auth = auth
        wrapper.__receive_permissions = permissions
        return wrapper

    return _receive


class ApiHttpConsumer(ApiWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = None
        self.result: List[Dict] = []

    def send_json(self, content, close=False):
        self.result.append(self.encode_json(content))

    def collect_result(self):
        result = self.encode_json({
            'messages': self.result
        })
        self.result.clear()
        return result


def generate_proto(f):
    return f


def to_timestamp(dt: Union[timezone.datetime, datetime.date]) -> Optional[int]:
    if dt is None:
        return None
    if not hasattr(dt, 'timestamp'):
        dt = timezone.datetime(dt.year, dt.month, dt.day)
    return int(dt.timestamp() * 1000)


def from_timestamp(ts) -> Optional[timezone.datetime]:
    if ts is None:
        return None
    return timezone.datetime.fromtimestamp(ts / 1000, tz=pytz.utc)
