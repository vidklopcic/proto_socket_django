import traceback
from django.contrib.auth import get_user_model
import inspect
import abc
import json
from typing import Union, Type, Dict, List, Callable, Optional, Any
from asgiref.sync import async_to_sync
from channels.generic.websocket import JsonWebsocketConsumer
from channels.layers import get_channel_layer
from proto.messages import TxMessage
import proto.messages as pb
from django.conf import settings
from proto_socket_django.worker import SyncWorker, AsyncWorker, LongRunningTask


class ApiWebsocketConsumer(JsonWebsocketConsumer):
    receivers: List[Type['FPSReceiver']] = []
    sync_workers: List['SyncWorker'] = None
    async_worker: Optional[AsyncWorker] = None

    @classmethod
    def static_init(cls):
        if ApiWebsocketConsumer.sync_workers is None:
            ApiWebsocketConsumer.sync_workers = []
            if hasattr(settings, 'PSD_N_ASYNC_WORKERS'):
                raise Exception('PSD_N_ASYNC_WORKERS renamed to PSD_N_SYNC_WORKERS')

            for i in range(getattr(settings, 'PSD_N_SYNC_WORKERS', 0)):
                print('starting sync worker', i)
                ApiWebsocketConsumer.sync_workers.append(SyncWorker())

        if getattr(settings, 'PSD_RUN_ASYNC_WORKER', True) and ApiWebsocketConsumer.async_worker is None:
            print('starting async worker')
            ApiWebsocketConsumer.async_worker = AsyncWorker()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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

    def send_message(self, message: 'TxMessage', uuid: Optional[str] = None):
        json = message.get_message()
        if uuid is not None:
            json['headers']['uuid'] = uuid
        if settings.DEBUG:
            print('tx:', json)
        self.send_json(json)

    def encode_json(cls, content):
        return json.dumps(content, cls=UUIDEncoder)

    def connect(self):
        self.accept()

        self.user = self.scope.get('user')
        if getattr(self.user, 'id', None) is None:
            self.user = None

        if self.user:
            self.on_authenticated()

    # todo - refactor
    def refresh_token(self, refresh_token: str):
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken(refresh_token)
        refresh.set_jti()
        refresh.set_exp()
        refresh.set_iat()
        return str(refresh), str(refresh.access_token)

    def _refresh_token(self, refresh_token: str):
        try:
            refresh_token, self.token = self.refresh_token(refresh_token)
            self._authenticate()
            self.send_message(pb.TxLoginToken(pb.TxLoginToken.proto(
                token=self.token,
                refresh=refresh_token,
            )))
        except:
            traceback.print_exc()
            self.send_message(pb.TxRefreshTokenInvalid())

    def authenticate(self):
        from rest_framework_simplejwt.state import token_backend
        try:
            valid_data = token_backend.decode(self.token)
            assert valid_data['token_type'] == 'access'
            return get_user_model().objects.filter(pk=valid_data['user_id']).first()
        except:
            traceback.print_exc()
            return None

    def _authenticate(self):
        self.user = self.authenticate()
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
            self._authenticate()

        # todo - refactor
        if data.type == 'refresh-token':
            self._refresh_token(data.body['refresh_token'])

        for handler in self.handlers.get(data.type, []):
            handler.__func__(ReceiverProxy(handler.__self__, data.uuid), data, self.user)

    def on_authenticated(self):
        pass

    def broadcast_message(self, event):
        self.send_json(event['event'])

    @staticmethod
    def broadcast(group: str, message: 'TxMessage'):
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

    @classmethod
    def continue_async(cls, handler: Callable[[Any], Union[Any, None]], *args, **kwargs):
        is_coroutine = inspect.iscoroutinefunction(handler)
        if not is_coroutine and not cls.sync_workers:
            raise Exception('No sync workers. Is PSD_N_ASYNC_WORKERS > 0 and consumer set-up?')

        if is_coroutine and not cls.async_worker:
            raise Exception('No async worker. Is PSD_RUN_ASYNC_WORKER = True and consumer set-up?')

        queue = AsyncWorker.task_queue if is_coroutine else SyncWorker.task_queue
        task = LongRunningTask(
            handler=handler,
            args=args,
            kwargs=kwargs,
            run=lambda: queue.put(task),
            is_coroutine=is_coroutine,
        )
        return task


class FPSReceiver(abc.ABC):
    receivers: Dict[str, str] = {}

    def __init__(self, consumer: ApiWebsocketConsumer):
        self.consumer = consumer

    def continue_async(self, handler: Callable[[Any], Union[Any, None]], *args, **kwargs):
        return ApiWebsocketConsumer.continue_async(handler, *args, **kwargs)


class FPSReceiverError:
    def __init__(self, message, code=None):
        self.message = message
        self.code = code


# decorators
#
def receive(permissions: List[str] = None, auth: bool = None, whitelist_groups: List[str] = None,
            blacklist_groups: List[str] = None):
    if auth is None:
        auth = getattr(settings, 'PSD_DEFAULT_AUTH', True)
    forward_exceptions = getattr(settings, 'PSD_FORWARD_EXCEPTIONS', False)
    format_exception = getattr(settings, 'PSD_EXCEPTION_FORMATTER', lambda e: str(e))

    def _receive(method):
        message = method.__annotations__.get('message')
        assert message is not None and hasattr(message, 'proto')

        from django.contrib.auth.models import User
        def wrapper(self: FPSReceiver, message_data: pb.RxMessageData, user: User):
            def _handle_result(result):
                ack_message = pb.TxAck(pb.Ack(uuid=message_data.uuid))
                if type(result) is FPSReceiverError:
                    ack_message.proto.error_message = result.message
                    ack_message.proto.error_code = result.code
                self.consumer.send_message(ack_message)

            try:
                authorized = True

                if (auth or whitelist_groups or blacklist_groups or permissions) and (
                        not user or not user.is_superuser):
                    if user is None:
                        authorized = False
                    elif permissions and not user.has_perms(permissions):
                        authorized = False
                    elif whitelist_groups and not user.groups.filter(name__in=whitelist_groups).exists():
                        authorized = False
                    elif blacklist_groups and user.groups.filter(name__in=blacklist_groups).exists():
                        authorized = False

                if not authorized:
                    raise Exception(user, 'is unauthorized for', message)

                # call receiver implementation
                result = method(self, message(message_data, user))

                # handle ack
                if message_data.ack:
                    if type(result) is LongRunningTask:
                        result.on_result = _handle_result
                        result.ack = message_data.ack
                    else:
                        _handle_result(result)

                if type(result) is LongRunningTask:
                    result.run()

                return result
            except Exception as e:
                if forward_exceptions and message_data.ack:
                    _handle_result(FPSReceiverError(format_exception(e)))
                elif not forward_exceptions:
                    raise
                traceback.print_exc()

        wrapper.__receive = message
        wrapper.__receive_auth = auth
        wrapper.__receive_permissions = permissions
        return wrapper

    return _receive

class ConsumerProxy:
    # noinspection PyMissingConstructor
    def __init__(self, original, uuid: str):
        self.original = original
        self.uuid = uuid

    def __getattr__(self, name):
        attr = getattr(self.original, name)
        if callable(attr) and inspect.ismethod(attr):
            def method(*args, **kwargs):
                return attr.__func__(self, *args, **kwargs)

            return method
        return attr

    def send_message(self, message: 'TxMessage', uuid: Optional[str] = None):
        self.original.send_message(message, uuid or self.uuid)


class ReceiverProxy:
    # noinspection PyMissingConstructor
    def __init__(self, original, uuid: str):
        self.original = original
        self.consumer = ConsumerProxy(original.consumer, uuid)

    def __getattr__(self, name):
        attr = getattr(self.original, name)
        if callable(attr) and inspect.ismethod(attr):
            def method(*args, **kwargs):
                return attr.__func__(self, *args, **kwargs)

            return method
        return attr