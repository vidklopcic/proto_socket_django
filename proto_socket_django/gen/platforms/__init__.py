import re


def get_psd_messages(proto_content: str):
    return re.findall('/\*(.+?)\*/\nmessage(.+?){', proto_content, flags=re.S)
