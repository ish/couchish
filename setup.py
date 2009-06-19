from setuptools import setup, find_packages
import sys, os

version = '0.2.1'

setup(name='couchish',
      version=version,
      description="",
      long_description="""\
""",
      classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      keywords='',
      author='Tim Parkin & Matt Goodall',
      author_email='info@timparkin.co.uk',
      url='',
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

