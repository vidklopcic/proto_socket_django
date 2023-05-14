import argparse
import json
import sys
import re
from typing import List
from proto_socket_django.gen.platforms.react import messages_templates as templates
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

    def get_client_prefix(self):
        if 'client' in re.search('origin.+=(.+)', self.spec).group(1):
            return 'Tx'
        else:
            return 'Rx'

    def origin_is_client(self):
        return 'client' in re.search('origin.+=(.+)', self.spec).group(1)

    def get_client_message_classname(self):
        return self.get_client_prefix() + self.proto

    def get_client_cache_duration(self):
        if re.search('client\s+cache\s*=', self.spec):
            cache = re.search('client\s+cache\s*=(.+)', self.spec).group(1)
            cache_duration = {
                'seconds': 0,
                'minutes': 0,
                'hours': 0,
                'days': 0,
            }
            if 'seconds' in cache:
                cache_duration['seconds'] = int(re.search('seconds\((.+)\)', cache).group(1))
            if 'minutes' in cache:
                cache_duration['minutes'] = int(re.search('minutes\((.+)\)', cache).group(1))
            if 'hours' in cache:
                cache_duration['hours'] = int(re.search('hours\((.+)\)', cache).group(1))
            if 'days' in cache:
                cache_duration['days'] = int(re.search('days\((.+)\)', cache).group(1))
            if 'years' in cache:
                cache_duration['days'] += int(re.search('years\((.+)\)', cache).group(1)) * 365
            return 'const Duration(days: {days}, hours: {hours}, minutes: {minutes}, seconds: {seconds})'.format(
                **cache_duration)

    def get_spec_fields_and_cache_class(self):
        common_fields = []
        tx_fields = []
        rx_fields = []
        # todo - persistence not yet implemented
        return common_fields, rx_fields, tx_fields, ''

    def is_auth_required(self):
        auth = re.search('auth\s*=\s*(.+)\s*', self.spec)
        if auth:
            return auth.group(1)
        else:
            return 'true'

    def get_client_message(self) -> str:
        common_fields, rx_fields, tx_fields, cache_class = self.get_spec_fields_and_cache_class()
        if self.origin_is_client():
            return cache_class + '\n\n' + templates.tx_message_class.format(
                prefix=self.get_client_prefix(),
                type=self.get_type(),
                proto=self.proto,
                auth=self.is_auth_required(),
                package=self.package,
                fields='\n  '.join(common_fields + tx_fields),
            )
        else:
            return cache_class + '\n\n' + templates.rx_message_class.format(
                prefix=self.get_client_prefix(),
                type=self.get_type(),
                proto=self.proto,
                package=self.package,
                fields='\n  '.join(common_fields + rx_fields),
            )

    def __eq__(self, other):
        return isinstance(other, MessagesGenerator) and self.proto == other.proto

    def __hash__(self):
        return hash(self.proto)

    def __str__(self):
        return self.proto + ' (' + self.path + ')'


def generate(protos: List[str], is_proto_socket_module=False):
    generators = []
    for f in protos:
        proto_content = open(f, 'r', encoding='utf-8').read()
        generators += [MessagesGenerator(f, i[0], i[1]) for i in get_psd_messages(proto_content)]
    generators = list(set(generators))
    generators.sort(key=lambda g: f'{g.package}_{g.proto}')

    imports = set()
    if is_proto_socket_module:
        imports.add('import {SocketRxMessage, SocketRxMessageData, SocketTxMessage} from "../socket_messages";')
    else:
        imports.add('import {SocketRxMessage, SocketRxMessageData, SocketTxMessage} from "proto_socket_typescript";')

    import_names = ', '.join(set([i.package for i in generators]))
    imports.add(f'import {{{import_names}}} from "./compiled";')

    with open('./src/proto/messages.ts', 'w', encoding='utf-8') as f:
        f.write('\n'.join(imports))

        f.write('\n\nexport namespace proto {')
        rx_classnames = []
        for generator in generators:
            try:
                f.write(generator.get_client_message())
                if not generator.origin_is_client():
                    rx_classnames.append(generator.get_client_message_classname())
            except IndexError as e:
                print('Syntax error:', generator)
                print(e)
        f.write('''

        export const rxMessages: SocketRxMessage<any>[] = [
            %s
        ];''' % ',\n    '.join(['new {}()'.format(i) for i in rx_classnames]))
        f.write('\n}')


if __name__ == '__main__':
    args = argparse.ArgumentParser(description='Generate message objects from proto and docstring specs.')
    args.add_argument(type=str, nargs='+', dest='protos', help='list of proto files')
    params = args.parse_args(sys.argv[1:])
    generate(params.protos, json.load(open('fps_config.json')).get('proto-socket-module', False))
