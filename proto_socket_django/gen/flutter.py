import os
import subprocess
import sys
import json
from . import get_protos, delete_existing
from .platforms.flutter.messages_generator import generate

def main():
    if not os.path.isfile('pubspec.yaml') or not os.path.isfile('fps_config.json'):
        print('Run the command from flutter project root, containing fps_config.json and pubspec.yaml.')
        sys.exit(1)

    proto_out = 'lib/proto'
    delete_existing(proto_out)
    proto_path, protos = get_protos(json.load(open('fps_config.json')), '-I')
    subprocess.run(f'protoc {proto_path} --dart_out={proto_out} {" ".join(protos)}', shell=True)
    subprocess.run(
        "sed -i '' 's/sfiles.pb.dart/package:flutter_persistent_socket\/proto\/sfiles.pb.dart/g' ./lib/proto/*",
        shell=True
    )
    subprocess.run(
        "sed -i '' 's/uploader.pb.dart/package:flutter_persistent_socket\/proto\/uploader.pb.dart/g' ./lib/proto/*",
        shell=True
    )
    generate(protos)

if __name__ == '__main__':
    main()