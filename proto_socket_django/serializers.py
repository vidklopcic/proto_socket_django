import abc
from proto.messages import TxMessage, RxMessage


class ProtoSerializer(abc.ABC):
    tx: TxMessage

    def msg(self):
        return self.tx(self)
