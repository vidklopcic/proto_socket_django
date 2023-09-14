#!/usr/bin/python3
import os
import subprocess
import sys
import json
from . import get_protos, delete_existing
from .platforms.django.messages_generator import generate


def main():
    if not os.path.isfile('fps_config.json') or not os.path.isfile('manage.py'):
        print('Run the command from django project root, containing fps_config.json and manage.py.')
        sys.exit(1)

    proto_out = 'proto'
    delete_existing(proto_out)
    proto_path, protos = get_protos(json.load(open('fps_config.json')), '-I')
    subprocess.run(f'protoc {proto_path} --python_betterproto_out={proto_out} {" ".join(protos)}', shell=True)
    generate(protos)


if __name__ == '__main__':
    main()
