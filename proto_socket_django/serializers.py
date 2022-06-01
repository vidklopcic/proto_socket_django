import abc
from proto.messages import TxMessage, RxMessage


class ProtoSerializer(abc.ABC):
    tx: TxMessage

    def __new__(cls, *args, **kwargs):
        if cls.tx:
            cls.tx.proto()  # hack to set original vars() to current module (not really sure why it fails otherwise)
        return super().__new__(cls)

    def msg(self):
        return self.tx(self)
