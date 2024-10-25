import sys

if '-m' not in sys.argv:
    from proto.messages import *
    from . import betterproto_patch
    from .consumer import ApiWebsocketConsumer
    from . import utils
    from .serializers import ProtoSerializer
