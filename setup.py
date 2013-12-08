# -*- coding: utf-8 -*-
"""Installer for this package."""

from setuptools import setup
from setuptools import find_packages

import os


# shamlessly stolen from niteoweb.fabfile from Hexagon IT guys
def read(*rnames):
    return open(os.path.join(os.path.dirname(__file__), *rnames)).read()

version = '0.0.1dev'

setup(name='workparser',
      version=version,
      description="Parser of structured file from which working time is calculated. It has also script which track working time (when computer isn't in sleep or has lock screen).",
      long_description=read('README.md')
                       + read('LICENSE')
                       + read('docs', 'HISTORY.txt')
                       ,
      classifiers=[
        "Programming Language :: Python",
        ],
      keywords='Trac Python',
      author='@predkambrij',
      author_email='lojze.blatnik@gmail.com',
      #url='',
      license='GPLv2 or later',
      packages=find_packages(exclude=['ez_setup']),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          # list project dependencies
          'setuptools',
          'nose',
          'sphinx',
          'sphinxcontrib-jinjadomain',
          'pyyaml',
      ],
      test_suite="tests",
)