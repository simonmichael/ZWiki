#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name = "Zwiki",
    version = "2.0b1",
    author = "Simon Michael & co.",
    author_email = "simon@joyful.com",
    description = "Zwiki, the Zope-based wiki engine.",
    long_description = "Zwiki, the Zope-based wiki engine.",
    url = "http://zwiki.org",
    platforms = [],
    keywords = "wiki zope",
    classifiers = [],
    license = "GPL",
    scripts = [],
    packages=find_packages('src'),
    package_dir={'': 'src'},
    namespace_packages=['Products'],
    package_data = {
      '':['*.txt'],
      },
    install_requires = [
      'Zope2>=2.12',
      ],
    )
