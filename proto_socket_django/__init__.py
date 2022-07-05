try:
    import betterproto
    import abc
    import datetime
    import json
    import traceback
    from typing import Union, Type, Dict, List, Callable, Optional, Any
    from uuid import UUID
    import pytz
    from asgiref.sync import async_to_sync
    from channels.generic.websocket import JsonWebsocketConsumer
    from channels.layers import get_channel_layer
    from django.utils import timezone
    from proto.messages import TxMessage, RxMessage
    import proto.messages as pb
    from django.conf import settings
    from proto_socket_django.async_worker import AsyncWorker, AsyncMessage


    class ApiWebsocketConsumer(JsonWebsocketConsumer):
        receivers: List[Type['FPSReceiver']] = []
        async_workers: List['AsyncWorker'] = None

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

            # spawn async workers on first connection
            if ApiWebsocketConsumer.async_workers is None:
                ApiWebsocketConsumer.async_workers = []
                for i in range(getattr(settings, 'PSD_N_ASYNC_WORKERS', 0)):
                    print('starting async worker', i)
                    ApiWebsocketConsumer.async_workers.append(AsyncWorker())

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

        def send_message(self, message: 'TxMessage'):
            json = message.get_message()
            if settings.DEBUG:
                print('tx:', json)
            self.send_json(json)

        def encode_json(cls, content):
            return json.dumps(content, cls=UUIDEncoder)

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
            if not cls.async_workers:
                raise Exception('No async workers. Is PSD_N_ASYNC_WORKERS > 0 and consumer set-up?')

            async_message = AsyncMessage(
                handler=handler,
                args=args,
                kwargs=kwargs,
                run=lambda: AsyncWorker.message_queue.append(async_message)
            )
            return async_message


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

                    if (auth or whitelist_groups or blacklist_groups or permissions) and not user.is_superuser:
                        if user is None:
                            authorized = False
                        elif permissions and not user.has_perms(permissions):
                            authorized = False
                        elif whitelist_groups and not user.groups.filter(name__in=whitelist_groups).exists():
                            authorized = False
                        elif blacklist_groups and user.groups.filter(name__in=blacklist_groups).exists():
                            authorized = False

                    if not authorized:
                        raise Exception('unauthorized')

                    # call receiver implementation
                    result = method(self, message(message_data, user))

                    # handle ack
                    if message_data.ack:
                        if type(result) is AsyncMessage:
                            result.on_result = _handle_result
                        else:
                            _handle_result(result)

                    if type(result) is AsyncMessage:
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


    class UUIDEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, UUID):
                # if the obj is uuid, we simply return the value of uuid
                return str(obj)
            return json.JSONEncoder.default(self, obj)


    def to_dict_patch(self, casing: betterproto.Casing = betterproto.Casing.CAMEL,
                      include_default_values: bool = False) -> dict:
        """
        Returns a dict representation of this message instance which can be
        used to serialize to e.g. JSON. Defaults to camel casing for
        compatibility but can be set to other modes.

        `include_default_values` can be set to `True` to include default
        values of fields. E.g. an `int32` type field with `0` value will
        not be in returned dict if `include_default_values` is set to
        `False`.
        """
        output: betterproto.Dict[str, betterproto.Any] = {}
        for field in betterproto.dataclasses.fields(self):
            meta = betterproto.FieldMetadata.get(field)
            v = getattr(self, field.name)
            if isinstance(v, betterproto._PLACEHOLDER) and not include_default_values:
                continue
            cased_name = casing(field.name).rstrip("_")  # type: ignore
            if meta.proto_type == "message":
                if isinstance(v, betterproto.datetime):
                    if v != betterproto.DATETIME_ZERO or include_default_values:
                        output[cased_name] = betterproto._Timestamp.timestamp_to_json(v)
                elif isinstance(v, betterproto.timedelta):
                    if v != betterproto.timedelta(0) or include_default_values:
                        output[cased_name] = betterproto._Duration.delta_to_json(v)
                elif meta.wraps:
                    if v is not None or include_default_values:
                        output[cased_name] = v
                elif isinstance(v, list):
                    # Convert each item.
                    v = [i.to_dict(casing, include_default_values) for i in v]
                    if v or include_default_values:
                        output[cased_name] = v
                else:
                    if getattr(v, '_serialized_on_wire', False) or include_default_values:
                        output[cased_name] = v.to_dict(casing, include_default_values)
            elif meta.proto_type == "map":
                for k in v:
                    if hasattr(v[k], "to_dict"):
                        v[k] = v[k].to_dict(casing, include_default_values)

                if v or include_default_values:
                    output[cased_name] = v
            elif v != self._get_field_default(field, meta) or include_default_values:
                if meta.proto_type in betterproto.INT_64_TYPES:
                    if isinstance(v, list):
                        output[cased_name] = [str(n) for n in v]
                    else:
                        output[cased_name] = str(v)
                elif meta.proto_type == betterproto.TYPE_BYTES:
                    if isinstance(v, list):
                        output[cased_name] = [betterproto.b64encode(b).decode("utf8") for b in v]
                    else:
                        output[cased_name] = betterproto.b64encode(v).decode("utf8")
                elif meta.proto_type == betterproto.TYPE_ENUM:
                    enum_values = {
                        int(v): v for v in self._betterproto.cls_by_field[field.name]
                    }  # type: ignore
                    if isinstance(v, list):
                        output[cased_name] = [enum_values[e].name for e in v]
                    else:
                        output[cased_name] = enum_values[v].name
                else:
                    output[cased_name] = v
        return output


    betterproto.Message.to_dict = to_dict_patch
except:
    pass
