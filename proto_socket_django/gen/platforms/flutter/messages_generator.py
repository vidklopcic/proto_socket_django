import argparse
import sys
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List
from proto_socket_django.gen.platforms.flutter import messages_templates as templates
from proto_socket_django.gen.platforms import get_psd_messages


def to_camel_case(snake_str):
    components = snake_str.split('_')
    # We capitalize the first letter of each component except the first one
    # with the 'title' method and join them together.
    return components[0] + ''.join(x.title() for x in components[1:])


class MessagesGenerator:
    def __init__(self, path, spec, proto):
        self.path = path
        self.proto = proto.strip()
        self.spec = spec.strip()
        self.spec_items = [i.strip() for i in self.spec.split('\n') if i.strip()]
        self.package = Path(self.path).stem

    def get_type(self):
        return re.search('type.+=.+\'(.+)\'', self.spec).group(1)

    def get_import(self):
        prefix = ''
        if 'flutter_persistent_socket' in self.path:
            prefix = 'package:flutter_persistent_socket/'
        return "import '{}proto/{}.pb.dart';".format(prefix, self.package)

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
        cache_class = ''
        client_cache = self.get_client_cache_duration()
        if client_cache:
            common_fields.append('final Duration cache = {};'.format(client_cache))

        if re.search('client\s+cache_keys\s*=', self.spec):
            cache_keys = re.search('client\s+cache_keys\s*=(.+)', self.spec).group(1)

            def find_keys(key_type: str):
                if re.search(f'{key_type}\((.+?)\)', cache_keys):
                    return re.findall('\'(.+?)\'', re.search(f'{key_type}\((.+?)\)', cache_keys).group(1))
                return []

            text_keys = find_keys('text')
            real_keys = find_keys('real')
            date_keys = find_keys('date')
            int_keys = find_keys('int')



            if text_keys or real_keys or date_keys or int_keys:
                text_keys = [to_camel_case(k) for k in text_keys]
                real_keys = [to_camel_case(k) for k in real_keys]
                date_keys = [to_camel_case(k) for k in date_keys]
                int_keys = [to_camel_case(k) for k in int_keys]
                common_fields.append(
                    '''final {prefix}{proto}CacheKeys cacheKeys = const {prefix}{proto}CacheKeys();'''.format(
                        prefix=self.get_client_prefix(), proto=self.proto
                    )
                )
                rx_fields.append(
                    f'late {self.get_client_prefix()}{self.proto}Table table;'
                )
                table_fields_initializers = []
                table_fields = []
                cache_fields = []
                cache_keys = []

                def add_key(index: int, key: str, key_type: str, column: str):
                    cache_keys.append(
                        f'''final CacheKey {key}Key = const CacheKey(CacheKeyType.{key_type}, {index}, '{key}');'''
                    )
                    cache_fields.append(f'{column} {key}(table) => {key}Key.{key_type}Field(table);')
                    table_fields.append(f'final {column} {key};')
                    table_fields_initializers.append(
                        f'{key} = message.cacheKeys.{key}Key.{key_type}Field(table)'
                    )

                for i, key in enumerate(text_keys):
                    add_key(i, key, 'text', 'TextColumn')

                for i, key in enumerate(real_keys):
                    add_key(i, key, 'real', 'RealColumn')

                for i, key in enumerate(date_keys):
                    add_key(i, key, 'date', 'DateTimeColumn')

                for i, key in enumerate(int_keys):
                    add_key(i, key, 'int', 'IntColumn')


                cache_class = templates.cache_keys_class.format(
                    prefix=self.get_client_prefix(), proto=self.proto,
                    text_keys="'" + "', '".join(text_keys) + "'" if text_keys else '',
                    real_keys="'" + "', '".join(real_keys) + "'" if real_keys else '',
                    date_keys="'" + "', '".join(date_keys) + "'" if date_keys else '',
                    int_keys="'" + "', '".join(int_keys) + "'" if int_keys else '',
                    fields='\n  '.join(cache_keys + cache_fields)
                ) + '\n\n' + templates.cache_keys_table_class.format(
                    prefix=self.get_client_prefix(), proto=self.proto,
                    fields='\n  '.join(table_fields),
                    initializers=', '.join(table_fields_initializers)
                )

        return common_fields, rx_fields, tx_fields, cache_class

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
                fields='\n  '.join(common_fields + tx_fields),
            )
        else:
            return cache_class + '\n\n' + templates.rx_message_class.format(
                prefix=self.get_client_prefix(),
                type=self.get_type(),
                table_type=f'<{self.get_client_prefix()}{self.proto}Table>' if cache_class else '',
                proto=self.proto,
                fields='\n  '.join(common_fields + rx_fields),
                table=f'\n\n  void setTable(tbl) => table = {self.get_client_prefix()}{self.proto}Table(this, tbl);' if cache_class else ''
            )

    def __eq__(self, other):
        return isinstance(other, MessagesGenerator) and self.proto == other.proto

    def __hash__(self):
        return hash(self.proto)

    def __str__(self):
        return self.proto + ' (' + self.path + ')'


def generate(protos: List[str]):
    generators = []
    for f in protos:
        proto_content = open(f, 'r', encoding='utf-8').read()
        generators += [MessagesGenerator(f, i[0], i[1]) for i in get_psd_messages(proto_content)]
    generators = list(set(generators))
    generators.sort(key=lambda g: f'{g.package}_{g.proto}')

    imports = set()
    imports.add("import 'package:flutter_persistent_socket/communication/socket_messages.dart';")
    imports.add("import 'package:provider/provider.dart';")
    imports.add("import 'package:flutter_persistent_socket/communication/socket_api.dart';")
    imports.add("import 'package:provider/single_child_widget.dart';")
    imports.add("import 'package:drift/drift.dart';")
    imports.update(set([i.get_import() for i in generators]))

    with open('./lib/messages.dart', 'w', encoding='utf-8') as f:
        f.write('\n'.join(imports))

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

        List<SocketRxMessage> rxMessages = [
          %s
        ];''' % ',\n  '.join(['{}()'.format(i) for i in rx_classnames]))


if __name__ == '__main__':
    args = argparse.ArgumentParser(description='Generate message objects from proto and docstring specs.')
    args.add_argument(type=str, nargs='+', dest='protos', help='list of proto files')
    params = args.parse_args(sys.argv[1:])
    generate(params.protos)
