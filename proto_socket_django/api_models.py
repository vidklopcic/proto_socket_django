# db models
#
import importlib
import uuid
from typing import List, Type
import betterproto
import stringcase
from django.db import models
from bolder_scena import settings


class ApiModel(models.Model):
    id = models.CharField(max_length=64, default=uuid.uuid1, primary_key=True)
    date_created = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)
    user = None

    class Meta:
        abstract = True

    def to_proto_map(self):
        from .management.commands.genproto import ProtoGen
        proto_map = {}
        for field in self._meta.get_fields():
            field_type = type(field)
            field_name = field.name

            if getattr(self, field_name) is None:
                continue

            if field.related_model:
                field_type = type(field.related_model._meta.pk)
                field_name = field.name + '_id'
                proto_map[field_name] = ProtoGen.type_map[field_type].serialize(getattr(self, field_name))
            elif field.choices:
                camel_capital_name = stringcase.capitalcase(stringcase.camelcase(field.name))
                choices: Choices = getattr(self, camel_capital_name)
                proto_map[field_name] = choices.get_by_key(getattr(self, field.name)).index
            else:
                proto_map[field_name] = ProtoGen.type_map[field_type].serialize(getattr(self, field_name))
        return proto_map

    def to_proto(self):
        protos = importlib.import_module(
            'proto.{project}_{app}'.format(project=settings.PROJECT, app=self._meta.app_label))
        proto: Type[betterproto.Message] = getattr(protos, self.__class__.__name__)
        return proto().from_dict(self.to_proto_map())


class Choice:
    def __init__(self, key, value, index):
        self.key = key
        self.value = value
        self.index = index

    def __eq__(self, obj):
        return isinstance(obj, type(self.key)) and obj == self.key


class Choices:
    @classmethod
    def choices(cls):
        fields = cls.__dict__
        choices = []
        for field, value in fields.items():
            if type(value) is not Choice: continue
            choices.append((value.key, value.key))
        return choices

    @classmethod
    def enum(cls) -> List[Choice]:
        fields = [i[1] for i in cls.__dict__.items() if type(i[1]) is Choice]
        return sorted(fields, key=lambda i: i.index)

    @classmethod
    def get_by_key(cls, key) -> Choice:
        for i in cls.__dict__.items():
            if type(i[1]) is not Choice:
                continue
            if key == i[1].key:
                return i[1]
