import argparse
import os
import sys


def is_django_project():
    return os.path.isfile('manage.py') and os.path.isfile('fps_config.json')


def is_flutter_project():
    # You can define similar logic to detect a Flutter project
    return os.path.isfile('pubspec.yaml') and os.path.isfile('fps_config.json')


def is_react_project():
    # Define similar logic to detect a React project
    return os.path.isdir('node_modules') and os.path.isfile('fps_config.json')


def run_django_generator():
    from .gen.django import main as platform_gen
    platform_gen()


def run_flutter_generator():
    from .gen.flutter import main as platform_gen
    platform_gen()


def run_react_generator():
    from .gen.react import main as platform_gen
    platform_gen()


def main():
    parser = argparse.ArgumentParser(
        description='Proto Socket Django - a Django-based library for building web applications with real-time communication'
    )

    subparsers = parser.add_subparsers(dest='command')

    # Add the 'generate' command
    generate_parser = subparsers.add_parser('generate')

    args = parser.parse_args()

    if args.command == 'generate':
        if is_django_project():
            run_django_generator()
        elif is_flutter_project():
            run_flutter_generator()
        elif is_react_project():
            run_react_generator()
        else:
            print(
                "Error: The current directory does not seem to be a Django, Flutter, or React project with a 'fps_config.json'."
            )
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
