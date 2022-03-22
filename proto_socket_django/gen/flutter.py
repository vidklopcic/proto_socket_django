import os
import subprocess
import sys
import json
from . import get_protos, delete_existing
from .platforms.flutter.messages_generator import generate

if not os.path.isfile('pubspec.yaml') or not os.path.isfile('fps_config.json'):
    print('Run the command from flutter project root, containing fps_config.json and pubspec.yaml.')
    sys.exit(1)

proto_out = 'src/proto'
delete_existing(proto_out)
proto_path, protos = get_protos(json.load(open('fps_config.json')), '-I')
subprocess.run(f'pbjs {proto_path} -t static-module -w es6 -o {proto_out}/compiled.js {" ".join(protos)}', shell=True)
subprocess.run(f'pbts -o {proto_out}/compiled.d.ts {proto_out}/compiled.js', shell=True)
generate(protos)
