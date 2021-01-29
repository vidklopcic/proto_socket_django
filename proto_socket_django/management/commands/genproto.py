import importlib
import inspect
from typing import Dict, Tuple, Union, List

import stringcase
from django.core.management.base import BaseCommand
import os
import re

from django.db import models
from django.utils.datetime_safe import datetime

from ... import api_models


class FieldType:
    django_to_proto_type = {
        models.CharField: 'string',
        models.FloatField: 'double',
        models.IntegerField: 'int32',
        models.AutoField: 'int32',
        models.BigIntegerField: 'int64',
        models.PositiveIntegerField: 'uint32',
        models.PositiveBigIntegerField: 'uint64',
        models.FileField: 'string',
        models.DateTimeField: 'uint64',
        models.DateField: 'uint64',
        models.ForeignKey: 'uint16',
        models.BooleanField: 'bool',
    }

    serializers = {
        models.FileField: lambda file: file.url,
        models.DateTimeField: lambda dt: int(dt.timestamp() * 1000),
        models.DateField: lambda dt: int(datetime(dt.year, dt.month, dt.day).timestamp() * 1000),
    }

    deserializers = {
        models.FileField: lambda file: file.url,
        models.DateTimeField: lambda ts: datetime.fromtimestamp(ts / 1000.0),
        models.DateField: lambda ts: datetime.fromtimestamp(ts / 1000.0).date(),
    }

    def __init__(self, django_type):
        self.djange_type = django_type
        self.proto_type = FieldType.django_to_proto_type[django_type]

    def serialize(self, value):
        try:
            return FieldType.serializers.get(self.djange_type, lambda x: x)(value)
        except:
            print('error serializing', value)
            return None

    def deserialize(self, value):
        try:
            return FieldType.deserializers.get(self.proto_type, lambda x: x)(value)
        except:
            print('error deserializing', value)
            return None


class ProtoGen:
    type_map = {
        models.CharField: FieldType(models.CharField),
        models.FloatField: FieldType(models.FloatField),
        models.IntegerField: FieldType(models.IntegerField),
        models.AutoField: FieldType(models.AutoField),
        models.BigIntegerField: FieldType(models.BigIntegerField),
        models.PositiveIntegerField: FieldType(models.PositiveIntegerField),
        models.PositiveBigIntegerField: FieldType(models.PositiveBigIntegerField),
        models.FileField: FieldType(models.FileField),
        models.DateTimeField: FieldType(models.DateTimeField),
        models.DateField: FieldType(models.DateField),
        models.ForeignKey: FieldType(models.ForeignKey),
        models.BooleanField: FieldType(models.BooleanField),
    }

    reg_api_models = re.compile('')

    def __init__(self, module: str, out_dir: str, namespace: str):
        self.namespace = namespace
        self.module = importlib.import_module(module)
        self.api_models = [v for k, v in self.module.__dict__.items() if
                           inspect.isclass(v) and issubclass(v, api_models.ApiModel)]
        self.out_dir = out_dir

    @staticmethod
    def get_proto(api_model: models.Model) -> Tuple[
        List[Tuple[str, List[api_models.Choice]]], List[Tuple[str, str]]]:
        data_fields: List[Tuple[str, str]] = []
        enums: List[Tuple[str, List[api_models.Choice]]] = []
        choices_classes = {}
        for field, value in api_model.__dict__.items():
            if inspect.isclass(value) and issubclass(value, api_models.Choices):
                choices_classes[stringcase.snakecase(field)] = value
        for field in api_model._meta.get_fields():
            field_type = type(field)
            field_name = field.name

            if field.related_model:
                field_type = type(field.related_model._meta.pk)
                field_name += '_id'

            if field_type not in ProtoGen.type_map:
                print('WARNING:', field_type, 'it not in known types! Ignoring.')
                continue

            if field.choices:
                # todo, support imported enums (eg. related = 'app.models.ModelName.ChoicesClass')
                camel_capital_name = stringcase.capitalcase(stringcase.camelcase(field.name))
                if field.name not in choices_classes:
                    print('ERROR:', field.name,
                          'has choices, but {} Choices class does not exist! Ignoring.'.format(camel_capital_name))
                    continue
                enums.append((camel_capital_name, choices_classes[field.name].enum()))
                data_fields.append((camel_capital_name, field_name))
            else:
                data_fields.append((ProtoGen.type_map[field_type], field_name))
        return enums, data_fields

    def write(self):
        enums: List[Tuple[str, List[api_models.Choice]]] = []
        messages = []
        for model in self.api_models:
            model_enums, fields = self.get_proto(model)
            enums += model_enums
            messages.append([model.__name__, fields])

        with open(os.path.join(self.out_dir, '{namespace}.proto'.format(namespace=self.namespace)), 'w',
                  encoding='utf-8') as f:
            f.write(PROTO_HEADER.format(namespace=self.namespace))

            for name, fields in messages:
                fields = [PROTO_FIELD.format(type=f[0], name=f[1], index=i) for i, f in enumerate(fields, start=1)]
                f.write(PROTO_MESSAGE.format(name=name, fields=PROTO_FIELD_SEPARATOR.join(fields)))

            for enum in enums:
                fields = [PROTO_ENUM_FIELD.format(name=f.key, index=f.index) for f in enum[1]]
                f.write(PROTO_ENUM.format(name=enum[0], fields=PROTO_FIELD_SEPARATOR.join(fields)))

    def get_api_models(self):
        pass


class Command(BaseCommand):
    help = 'Generates the proto files for the specified apps'

    def add_arguments(self, parser):
        parser.add_argument('apps', nargs='+', type=str)

    def handle(self, *args, **options):
        prefix = [d for d in os.listdir(os.getcwd()) if os.path.isfile(os.path.join(d, 'settings.py'))][0]
        for app in options['apps']:
            namespace = '{project}_{app}'.format(project=prefix, app=app)
            out_dir = os.path.join(app, 'proto')
            if not os.path.isdir(out_dir):
                os.makedirs(out_dir)
            ProtoGen('{}.models'.format(app), out_dir, namespace).write()
            self.stdout.write(self.style.SUCCESS('Wrote proto files for app {app} to {app}/proto'.format(app=app)))


PROTO_HEADER = '''syntax = "proto3";
package {namespace};

'''

PROTO_MESSAGE = '''message {name} {{
    {fields}
}}

'''

PROTO_FIELD = '{type} {name} = {index};'
PROTO_FIELD_SEPARATOR = '\n    '

PROTO_ENUM = '''enum {name} {{
    {fields}
}}

'''

PROTO_ENUM_FIELD = '{name} = {index};'
