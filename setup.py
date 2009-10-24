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
    py_modules = [
      "__init__",
      "Admin",
      "CMF",
      "Catalog",
      "Comments",
      "Defaults",
      "Diff",
      "Editing",
      "History",
      "Mail",
      "Outline",
      "OutlineSupport",
      "PageTypes",
      "Permissions",
      "Regexps",
      "Splitter",
      "TextFormatter",
      "Utils",
      "Views",
      "ZWikiPage",
      ],
    packages = find_packages(),
    package_data = {
      '':['*.txt'],
      },
    install_requires = [
      'Zope2>=2.12',
      ],
    )
