import betterproto
from django.apps import AppConfig


class ApiConfig(AppConfig):
    name = 'proto_socket_django'


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
        cased_name = betterproto.casing(field.name).rstrip("_")  # type: ignore
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
                if v._serialized_on_wire or include_default_values:
                    output[cased_name] = v.to_dict(casing, include_default_values)
        elif meta.proto_type == "map":
            for k in v:
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
