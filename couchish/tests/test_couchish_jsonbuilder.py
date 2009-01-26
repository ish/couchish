import unittest
from couchish.couchish_jsonbuilder import build
import yaml

DATADIR = 'couchish/tests/data/%s'

def get_schema(filename):
    definition = yaml.load( open(DATADIR%filename).read() )
    form = build(definition)
    return form.structure.attr

def get_form(filename):
    definition = yaml.load( open(DATADIR%filename).read() )
    form = build(definition)
    return form

class Test(unittest.TestCase):

    def test_simple(self):
        form = get_form('test_couchish_simple.yaml')
        print form
        print form['address'].field
        print form['address'].widget

