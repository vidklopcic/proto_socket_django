# db models
#
import importlib
import uuid
from typing import List, Type, Tuple
import betterproto
import stringcase
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.conf import settings


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

    def populate_unrelated_proto(self, proto: betterproto.Message) -> List[str]:
        from .management.commands.genproto import ProtoGen
        unbound: List[str] = []

        for field in self._meta.get_fields():
            field_type = type(field)
            field_name = field.name
            field_value = getattr(self, field_name)
            if field_value is None:
                continue

            # fixme: check if it's foreignkey set!
            if not hasattr(proto, field_name) and not field.related_model:
                unbound.append(field_name)
                continue

            if field.related_model:
                field_type = type(field.related_model._meta.pk)
                field_name = field.name + '_id'
                if hasattr(proto, field_name) and isinstance(getattr(proto, field_name), field_type):
                    setattr(proto, field_name, field_value.pk)
                else:
                    unbound.append(field_name)
            elif field.choices:
                camel_capital_name = stringcase.capitalcase(stringcase.camelcase(field.name))
                choices: Choices = getattr(self, camel_capital_name)
                setattr(proto, field_name, choices.get_by_key(getattr(self, field.name)).index)
            else:
                if field_type not in ProtoGen.type_map:
                    print('WARNING:', field_type, 'it not in known types! Ignoring.')
                    continue
                setattr(proto, field_name, ProtoGen.type_map[field_type].serialize(getattr(self, field_name)))

        proto._unbount = unbound
        return proto

    @classmethod
    def permission(cls, action: str):
        return f'{cls._meta.app_label}.{action}_{cls._meta.model_name}'

    @classmethod
    def perms_add(cls) -> List[str]:
        return [cls.permission('add')]

    @classmethod
    def perms_delete(cls) -> List[str]:
        return [cls.permission('delete')]

    @classmethod
    def perms_change(cls) -> List[str]:
        return [cls.permission('change')]

    @classmethod
    def perms_view(cls) -> List[str]:
        return [cls.permission('view')]

    @classmethod
    def perms_all(cls) -> List[str]:
        return cls.perms_add() + cls.perms_change() + cls.perms_delete() + cls.perms_view()


class Choice:
    def __init__(self, key, value, index):
        self.key = key
        self.value = value
        self.index = index

    def __eq__(self, obj):
        return isinstance(obj, type(self.key)) and obj == self.key

    def __str__(self):
        return self.value


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
