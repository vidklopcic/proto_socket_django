import os
import subprocess
import sys
import json
from . import get_protos, delete_existing
from .platforms.react.messages_generator import generate

if not os.path.isfile('fps_config.json') or not os.path.isfile('package.json'):
    print('Run the command from react project root, containing fps_config.json and package.json.')
    sys.exit(1)

proto_out = 'src/proto'
delete_existing(proto_out)
config = json.load(open('fps_config.json'))
proto_path, protos = get_protos(config, '-p')
subprocess.run(f'pbjs {proto_path} -t static-module -w es6 -o {proto_out}/compiled.js {" ".join(protos)}', shell=True)
subprocess.run(f'pbts -o {proto_out}/compiled.d.ts {proto_out}/compiled.js', shell=True)
generate(protos, config.get('proto-socket-module', False))
