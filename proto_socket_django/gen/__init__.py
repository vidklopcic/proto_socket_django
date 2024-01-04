import json
import os
import shutil
from pathlib import Path as P, Path

COMMON_PROTO = str(P(__file__).parent.resolve() / 'common')


def discover_protos(dir: str):
    protos = []
    for root, dirnames, filenames in os.walk(dir):
        for filename in filenames:
            if os.path.splitext(filename)[1].lower() == '.proto':
                protos.append(str(P(root) / filename))
    return protos


def delete_existing(dir):
    if os.path.isdir(dir):
        shutil.rmtree(dir)
    os.makedirs(dir)


def get_protos(config, path_arg):
    config['protos'] = set([os.path.expandvars(p) for p in config['protos']])
    protos = [p for ps in [discover_protos(i) for i in config['protos']] for p in ps]
    proto_dirs = set(config['protos'])
    if config.get('include_common', False):
        proto_dirs.add(COMMON_PROTO)
    proto_path = ' '.join([path_arg + ' ' + i for i in proto_dirs])
    return proto_path, protos
