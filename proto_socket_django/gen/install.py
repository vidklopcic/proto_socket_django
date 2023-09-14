import argparse
import os
import subprocess
import sys
import traceback


def for_flutter():
    subprocess.check_output(['pub', 'global', 'activate', 'protoc_plugin'])


def for_react():
    subprocess.check_output(['npm', 'install', '--global', 'protobufjs'])


def for_django():
    import pip
    if os.geteuid() != 0:
        result = input('Installing "betterproto[compiler]" without sudo privileges. If this is a global installation '
                       '"protoc-gen-python_betterproto" binary won\'t be added to the system path. Continue? [y/N]')
        if result.strip() != 'y':
            sys.exit(1)

    pip.main(['install', 'betterproto[compiler]'])


def protoc():
    if sys.platform == 'darwin':
        try:
            subprocess.check_output(['brew', 'install', 'protobuf'])
        except FileNotFoundError:
            raise FileNotFoundError('Homebrew must be installed first')
    elif sys.platform == 'linux':
        if os.geteuid() != 0:
            raise Exception('Cannot install protoc without sudo privileges (sudo apt install protobuf-compiler).')
        subprocess.check_output(['sudo', 'apt', 'install', '-y', 'protobuf-compiler'])
    else:
        raise NotImplementedError('for now, protoc installation is only supported on OSX using Homebrew')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Install / check required dependencies for supported platforms (e.g., protobuf)')
    args = parser.parse_args()

    try:
        subprocess.check_output('protoc')
    except FileNotFoundError:
        print('===== Installing protoc =====')
        try:
            protoc()
        except:
            traceback.print_exc()
            print('Failed to install protoc')

    print('===== Installing protoc_plugin for flutter =====')
    try:
        for_flutter()
    except:
        traceback.print_exc()
        print('Failed to install protoc_plugin for flutter')

    print('===== Installing protobufjs for react =====')
    try:
        for_react()
    except:
        traceback.print_exc()
        print('Failed to install protobufjs for react')

    print('===== Installing betterproto[compiler] for django =====')
    try:
        for_django()
    except:
        traceback.print_exc()
        print('Failed to install betterproto[compiler] for django')
