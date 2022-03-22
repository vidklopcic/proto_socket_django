import argparse
import subprocess
import sys


def for_flutter():
    pass

def for_react():
    subprocess.check_output(['npm', 'install', '--global', 'pbjs'])


def for_django():
    import pip
    pip.main(['install', 'betterproto[compiler]'])


def protoc():
    if sys.platform == 'darwin':
        try:
            subprocess.check_output(['brew', 'install', 'protobuf'])
        except FileNotFoundError:
            raise FileNotFoundError('Homebrew must be installed first')
    else:
        raise NotImplementedError('for now, protoc installation is only supported on OSX using Homebrew')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Install / check required dependencies for supported platforms (e.g., protobuf)')
    parser.add_argument('--protoc')
    parser.add_argument('--platforms', type=str, default='flutter,react,django.py')
    args = parser.parse_args()

    if args.protoc:
        protoc()

    try:
        subprocess.check_output('protoc')
    except FileNotFoundError:
        raise FileNotFoundError('protoc must be installed first')

    if args.platforms:
        for platform in [p.strip() for p in args.platforms.split(',')]:
            try:
                exec(f'for_{platform}()')
            except NameError as e:
                print('platform', platform, 'is not supported')
