import sys

if '-m' not in sys.argv:
    import proto.messages as pb
    from .consumer import ApiWebsocketConsumer, FPSReceiver, FPSReceiverError, receive
    from . import utils
    from . import serializers
