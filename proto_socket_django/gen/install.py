import argparse
import os
import subprocess
import sys
import traceback


def run_as_user(command):
    user = os.getenv('SUDO_USER', os.getenv('USER'))
    return subprocess.check_output(['sudo', '-u', user] + command)


def for_flutter():
    run_as_user(['dart', 'pub', 'global', 'activate', 'protoc_plugin'])


def for_react():
    run_as_user(['npm', 'install', '--global', 'protobufjs'])


def for_django():
    import pip
    try:
        import betterproto
        return  # already installed
    except ImportError:
        pass
    pip.main(['install', 'betterproto[compiler]==1.2.5'])


def protoc():
    if sys.platform == 'darwin':
        try:
            run_as_user(['brew', 'install', 'protobuf'])
        except FileNotFoundError:
            raise FileNotFoundError('Homebrew must be installed first')
    elif sys.platform == 'linux':
        subprocess.check_output(['apt', 'install', '-y', 'protobuf-compiler'])
    else:
        raise NotImplementedError(
            'for now, protoc installation is only supported on OSX using Homebrew and on Linux using apt.'
        )


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Install / check required dependencies for supported platforms (e.g., protobuf)')
    args = parser.parse_args()

    if os.geteuid() != 0:
        raise Exception('Script must be run as root (needed for protoc installation)')

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
