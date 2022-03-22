import json
import os
import shutil
from pathlib import Path as P


def discover_protos(dir: str):
    protos = []
    for root, dirnames, filenames in os.walk(dir):
        for filename in filenames:
            if os.path.splitext(filename)[1].lower() == '.proto':
                protos.append(str(P(root) / filename))
    return protos


COMMON_PROTO = P(__file__).parent.resolve() / 'common'


def delete_existing(dir):
    if os.path.isdir(dir):
        shutil.rmtree(dir)
    os.makedirs(dir)


def get_protos(config, parth_arg):
    config['protos'] = set([os.path.expandvars(p) for p in config['protos']] + [COMMON_PROTO])
    proto_path = ' '.join([parth_arg + ' ' + i for i in config['protos']])
    protos = ' '.join([p for ps in [discover_protos(i) for i in config['protos']] for p in ps])
    return proto_path, protos
