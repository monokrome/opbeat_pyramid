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
    'mock',
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
    author='Bailey Stoner',
    author_email='monokrome@monokro.me',
    url='https://github.com/monokrome/opbeat_pyramid',
    keywords='web pyramid pylons',
    packages=[MODULE_NAME],
    include_package_data=True,
    zip_safe=False,
    install_requires=REQUIRES,
    test_suite=MODULE_NAME,
    license='MIT',
    classifiers=[
        "Programming Language :: Python",
        "Framework :: Pyramid",
    ],
)
