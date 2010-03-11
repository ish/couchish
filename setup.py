from setuptools import setup, find_packages
import sys, os

version = '0.2.2'

setup(name='couchish',
      version=version,
      description="Couchdb library that includes reference cacheing triggers and consolidates updates.",
      long_description="""\
A couch wrapper that includes reference info updating, serialisation of complex types into json, filehandling (returning filehandles, storing document filehandles as attachments and many other bits). Get in touch if any of this sounds interesting.
""",
      classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      keywords='',
      author='Tim Parkin & Matt Goodall',
      author_email='info@timparkin.co.uk',
      url='http://ish.io',
      license='',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          # -*- Extra requirements: -*-
          "PyYAML",
          "couchdb-session",
          "dottedish",
          "jsonish",
          "schemaish",
      ],
      extras_require={
          'formish': ['formish'],
      },
      entry_points="""
      # -*- Entry points: -*-
      """,
      test_suite='couchish.tests',
      tests_require=['BeautifulSoup', 'WebOb', 'formish'],
      )

