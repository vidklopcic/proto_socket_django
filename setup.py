import os
from setuptools import setup

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.rst')).read()

setup(
    name='proto-socket-django.py',
    version='0.1',
    packages=['proto_socket_django'],
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
