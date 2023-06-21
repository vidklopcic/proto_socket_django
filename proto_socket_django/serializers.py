import abc
from proto.messages import TxMessage, RxMessage


class ProtoSerializer(abc.ABC):
    tx: TxMessage

    def __new__(cls, *args, **kwargs):
        cls.__module__ = cls.__bases__[0].__module__
        return super().__new__(cls)

    def msg(self):
        return self.tx(self)
