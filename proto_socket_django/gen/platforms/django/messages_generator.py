import argparse
import sys
import re
import os
from typing import List

import messages_templates as templates
from proto_socket_django.gen.platforms import get_psd_messages


class MessagesGenerator:
    def __init__(self, path, spec, proto):
        self.path = path
        self.proto = proto.strip()
        self.spec = spec.strip()
        self.spec_items = [i.strip() for i in self.spec.split('\n') if i.strip()]
        self.package = self.path.split(".proto")[0].split("/")[-1]

    def get_type(self):
        return re.search('type.+=.+\'(.+)\'', self.spec).group(1)

    def get_import(self):
        return 'from proto.%s import *' % self.package

    def get_server_prefix(self):
        if 'client' in re.search('origin.+=(.+)', self.spec).group(1):
            return 'Rx'
        else:
            return 'Tx'

    def get_server_message_classname(self):
        return self.get_server_prefix() + self.proto

    def is_auth_required(self):
        auth = re.search('auth\s*=\s*(.+)\s*', self.spec)
        if auth:
            return auth.group(1).capitalize()
        else:
            return 'True'

    def get_server_message(self) -> str:
        return templates.server_message.format(prefix=self.get_server_prefix(), proto=self.proto,
                                               type=self.get_type(), auth=self.is_auth_required())

    def __str__(self):
        return self.proto + ' (' + self.path + ')'


def generate(protos: List[str]):
    generators = []
    imports = {'from abc import ABC', 'import dataclasses', 'from betterproto import *'}
    for f in protos:
        proto_content = open(f, 'r', encoding='utf-8').read()
        imports.add(f'from proto.{os.path.splitext(os.path.basename(f))[0]} import *')
        generators += [MessagesGenerator(f, i[0], i[1]) for i in get_psd_messages(proto_content)]

    with open('proto/messages.py', 'w', encoding='utf-8') as f:
        f.write('\n'.join(imports))
        f.write(templates.boilerplate)
        for generator in generators:
            try:
                f.write(generator.get_server_message())
            except Exception as e:
                print('Syntax error:', generator, '|', e)


if __name__ == '__main__':
    args = argparse.ArgumentParser(description='Generate message objects from proto and docstring specs.')
    args.add_argument(type=str, nargs='+', dest='protos', help='list of proto files')
    generate(args.parse_args(sys.argv[1:]).protos)
