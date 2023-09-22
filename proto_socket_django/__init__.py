import sys

if '-m' not in sys.argv:
    import proto.messages as pb
    import api_models as api_models
    from consumer import ApiWebsocketConsumer
