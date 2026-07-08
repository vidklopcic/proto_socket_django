import json
import os
import shutil
from pathlib import Path as P, Path

COMMON_PROTO = str(P(__file__).parent.resolve() / 'common')


def discover_protos(dir: str):
    # sorted traversal so generated output is deterministic across runs
    protos = []
    for root, dirnames, filenames in os.walk(dir):
        dirnames.sort()
        for filename in sorted(filenames):
            if os.path.splitext(filename)[1].lower() == '.proto':
                protos.append(str(P(root) / filename))
    return protos


def delete_existing(dir):
    if os.path.isdir(dir):
        shutil.rmtree(dir)
    os.makedirs(dir)


def get_protos(config, path_arg):
    # sorted, deduped dirs so protoc/pbjs see files in a stable order and the
    # generated modules don't churn between runs
    proto_dirs = sorted(set([os.path.expandvars(p) for p in config['protos']]))
    if config.get('include_common', True) and COMMON_PROTO not in proto_dirs:
        proto_dirs.append(COMMON_PROTO)
    proto_path = ' '.join([path_arg + ' ' + i for i in proto_dirs])
    protos = [p for ps in [discover_protos(i) for i in proto_dirs] for p in ps]
    return proto_path, protos
