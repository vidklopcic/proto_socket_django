import dataclasses
import datetime
from base64 import b64decode
import betterproto
from betterproto import safe_snake_case

def from_dict_patch(self, value: dict):
    """
    Parse the key/value pairs in `value` into this message instance. This
    returns the instance itself and is therefore assignable and chainable.
    """
    self._serialized_on_wire = True
    fields_by_name = {f.name: f for f in dataclasses.fields(self)}
    for key in value:
        snake_cased = safe_snake_case(key)
        if snake_cased in fields_by_name:
            field = fields_by_name[snake_cased]
            meta = betterproto.FieldMetadata.get(field)

            if value[key] is not None:
                if meta.proto_type == "message":
                    v = getattr(self, field.name)
                    if isinstance(v, list):
                        cls = self._betterproto.cls_by_field[field.name]
                        for i in range(len(value[key])):
                            v.append(cls().from_dict(value[key][i]))
                    elif isinstance(v, datetime.datetime):
                        v = datetime.datetime.fromisoformat(
                            value[key].replace("Z", "+00:00")
                        )
                        setattr(self, field.name, v)
                    elif isinstance(v, datetime.timedelta):
                        v = datetime.timedelta(seconds=float(value[key][:-1]))
                        setattr(self, field.name, v)
                    elif meta.wraps:
                        setattr(self, field.name, value[key])
                    else:
                        v.from_dict(value[key])
                elif meta.map_types and meta.map_types[1] == betterproto.TYPE_MESSAGE:
                    v = getattr(self, field.name) or {}
                    cls = self._betterproto.cls_by_field[field.name + ".value"]
                    for k in value[key]:
                        v[k] = cls().from_dict(value[key][k])
                    setattr(self, field.name, v)
                else:
                    v = value[key]
                    if meta.proto_type in betterproto.INT_64_TYPES:
                        if isinstance(value[key], list):
                            v = [int(n) for n in value[key]]
                        else:
                            v = int(value[key])
                    elif meta.proto_type == betterproto.TYPE_BYTES:
                        if isinstance(value[key], list):
                            v = [b64decode(n) for n in value[key]]
                        else:
                            v = b64decode(value[key])
                    elif meta.proto_type == betterproto.TYPE_ENUM:
                        enum_cls = self._betterproto.cls_by_field[field.name]
                        if isinstance(v, list):
                            v = [enum_cls.from_string(e) for e in v]
                        elif isinstance(v, str):
                            v = enum_cls.from_string(v)

                    if v is not None:
                        setattr(self, field.name, v)
    return self


def to_dict_patch(self, casing: betterproto.Casing = betterproto.Casing.CAMEL,
                  include_default_values: bool = False) -> dict:
    """
    Returns a dict representation of this message instance which can be
    used to serialize to e.g. JSON. Defaults to camel casing for
    compatibility but can be set to other modes.

    `include_default_values` can be set to `True` to include default
    values of fields. E.g. an `int32` type field with `0` value will
    not be in returned dict if `include_default_values` is set to
    `False`.
    """
    output: betterproto.Dict[str, betterproto.Any] = {}
    for field in betterproto.dataclasses.fields(self):
        meta = betterproto.FieldMetadata.get(field)
        v = getattr(self, field.name)
        if isinstance(v, betterproto._PLACEHOLDER) and not include_default_values:
            continue
        cased_name = casing(field.name).rstrip("_")  # type: ignore
        if meta.proto_type == "message":
            if isinstance(v, betterproto.datetime):
                if v != betterproto.DATETIME_ZERO or include_default_values:
                    output[cased_name] = betterproto._Timestamp.timestamp_to_json(v)
            elif isinstance(v, betterproto.timedelta):
                if v != betterproto.timedelta(0) or include_default_values:
                    output[cased_name] = betterproto._Duration.delta_to_json(v)
            elif meta.wraps:
                if v is not None or include_default_values:
                    output[cased_name] = v
            elif isinstance(v, list):
                # Convert each item.
                v = [i.to_dict(casing, include_default_values) for i in v]
                if v or include_default_values:
                    output[cased_name] = v
            else:
                if getattr(v, '_serialized_on_wire', False) or include_default_values:
                    output[cased_name] = v.to_dict(casing, include_default_values)
        elif meta.proto_type == "map":
            for k in (v or dict()):
                if hasattr(v[k], "to_dict"):
                    v[k] = v[k].to_dict(casing, include_default_values)

            if v or include_default_values:
                output[cased_name] = v
        elif v != self._get_field_default(field, meta) or include_default_values:
            if meta.proto_type in betterproto.INT_64_TYPES:
                if isinstance(v, list):
                    output[cased_name] = [str(n) for n in v]
                else:
                    output[cased_name] = str(v)
            elif meta.proto_type == betterproto.TYPE_BYTES:
                if isinstance(v, list):
                    output[cased_name] = [betterproto.b64encode(b).decode("utf8") for b in v]
                else:
                    output[cased_name] = betterproto.b64encode(v).decode("utf8")
            elif meta.proto_type == betterproto.TYPE_STRING:
                if isinstance(v, list):
                    output[cased_name] = [str(b) for b in v]
                else:
                    output[cased_name] = str(v)
            elif meta.proto_type == betterproto.TYPE_ENUM:
                enum_values = {
                    int(v): v for v in self._betterproto.cls_by_field[field.name]
                }  # type: ignore
                if isinstance(v, list):
                    output[cased_name] = [enum_values[e].name for e in v]
                else:
                    output[cased_name] = enum_values[v].name
            else:
                output[cased_name] = v
    return output

betterproto.Message.to_dict = to_dict_patch
betterproto.Message.from_dict = from_dict_patch
default_app_config = 'proto_socket_django.apps.ApiConfig'
