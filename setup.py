import os
from setuptools import setup

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.rst')).read()

from glob import glob


def find_data_files():
    pathlist = ['gen/common']
    data = {}
    for path in pathlist:
        for root, d_names, f_names in os.walk(path, topdown=True, onerror=None, followlinks=False):
            data[root] = list()
            for f in f_names:
                data[root].append(os.path.join(root, f))

    fn = [(k, v) for k, v in data.items()]
    return fn

setup(
    name='proto-socket-django',
    version='0.1',
    packages=[
        'proto_socket_django',
        'proto_socket_django.gen',
        'proto_socket_django.gen.platforms',
        'proto_socket_django.gen.platforms.django',
        'proto_socket_django.gen.platforms.flutter',
        'proto_socket_django.gen.platforms.react',
    ],
    data_files=find_data_files(),
    description='A simple library that works with flutter_persistent_socket library.',
    long_description=README,
    author='Vid Klopcic',
    author_email='klopcic.vid@gmail.com',
    url='https://github.com/vidklopic/flutter_persistent_socket',
    license='MIT',
    install_requires=[
        'Django>=2.1',
    ]
)
