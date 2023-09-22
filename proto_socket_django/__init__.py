import sys

if '-m' not in sys.argv:
    import proto.messages as pb
    from . import betterproto_patch
    from . import api_models as api_models
    from .consumer import *
    from . import utils
    from .serializers import ProtoSerializer
