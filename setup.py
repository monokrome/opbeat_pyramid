#!/usr/bin/env python


import opbeat_pyramid
import os

from setuptools import setup


here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.md')) as f:
    README = f.read()


MODULE_NAME = opbeat_pyramid.__name__


REQUIRES = [
    'pyramid',
    'setuptools>=18',
]


TEST_REQUIRES = REQUIRES + [
    'coveralls',
    'flake8',
    'flake8-print',
    'opbeat',
    'pytest',
    'pytest-cov',
]


setup(
    name=MODULE_NAME,
    version=opbeat_pyramid.__VERSION__,
    description='Provides opbeat instrumentation for your Pyramid projects.',
    long_description=README,
    classifiers=[
        "Programming Language :: Python",
        "Framework :: Pyramid",
    ],
    author='Brit + Co ',
    author_email='nerds@brit.co',
    url='https://www.brit.co/',
    keywords='web pyramid pylons',
    packages=[],
    include_package_data=True,
    zip_safe=False,
    install_requires=REQUIRES,
    tests_require=REQUIRES,
    test_suite=MODULE_NAME,
)
