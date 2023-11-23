server_message = '''

class {prefix}{proto}({prefix}Message):
    type = '{type}'
    proto: {proto} = {proto}
    auth_required = {auth}
'''

boilerplate = '''


class RxMessageData:
    def __init__(self, json_data: dict):
        self.headers = json_data.get('headers')
        self.body = json_data.get('body')
        self.apiVersion = self.headers.get('apiVersion')
        self.authHeader = self.headers.get('authHeader')
        self.ack = self.headers.get('ack')
        self.uuid = self.headers.get('uuid')
        self.type = self.headers.get('messageType')
        self.retryCount = self.headers.get('retryCount', 0)


class RxMessage(ABC):
    proto = None
    type = None
    auth_required = True

    def __init__(self, data: Optional[Union[RxMessageData, betterproto.Message]] = None, user=None):
        self.data = None
        if not data:
            self.proto = self.proto()
        elif isinstance(data, betterproto.Message):
            self.proto = data
        else:
            self.data = data
            self.set_data(data)
        self.user = user

    def set_data(self, data: RxMessageData):
        self.proto = self.proto().from_dict(data.body)

class TxMessage(ABC):
    proto: betterproto.Message = None
    type: str = None

    def __init__(self, proto=None):
        self.fields = {}
        if proto is not None:
            assert isinstance(proto, self.proto)
            self.proto = proto
        else:
            self.proto = self.proto()

    def get_message(self) -> dict:
        return {
            'headers': {
                'messageType': self.type,
            },
            'body': self.proto.to_dict()
        }

def init_default_gen_patch(self):
    default_gen = {}

    for field in dataclasses.fields(self.cls):
        meta = FieldMetadata.get(field)
        if meta.proto_type == TYPE_MESSAGE:
            default_gen[field.name] = self.cls._get_field_default_gen(field, meta)
        else:
            default_gen[field.name] = lambda: None

    self.default_gen = default_gen

betterproto.ProtoClassMetadata.init_default_gen = init_default_gen_patch
'''
