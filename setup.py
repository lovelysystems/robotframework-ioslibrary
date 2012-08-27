#!/usr/bin/env python

from os.path import join, dirname

execfile(join(dirname(__file__), 'src', 'IOSLibrary', 'version.py'))

from distutils.core import setup

CLASSIFIERS = """
Programming Language :: Python
Topic :: Software Development :: Testing
"""[1:-1]

long_description=open(join(dirname(__file__), 'README.rst',)).read()

setup(
  name             = 'robotframework-ioslibrary',
  version          = VERSION,
  description      = 'Robot Framework Automation Library for iOS',
  long_description = long_description,
  author           = 'Lovely Systems GmbH',
  author_email     = 'office@lovelysystems.com',
  url              = 'https://github.com/lovelysystems/robotframework-ioslibrary',
  license          = 'EPL',
  keywords         = 'robotframework testing testautomation ios calabash iphone ipad',
  platforms        = 'any',
  zip_safe         = False,
  classifiers      = CLASSIFIERS.splitlines(),
  package_dir      = {'' : 'src'},
  install_requires = ['robotframework', 'requests'],
  packages         = ['IOSLibrary'],
  package_data     = {'IOSLibrary': ['resources/*']}
)
