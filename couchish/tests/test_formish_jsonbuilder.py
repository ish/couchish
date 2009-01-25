import unittest
from couchish.formish_jsonbuilder import build
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
        schema = get_schema('test_simple.yaml')
        assert 'schemaish.attr.Structure' in repr(schema)
        assert len(schema.attrs) == 3
        keys = [ k for k,v in schema.attrs]
        assert keys == ['first_name','last_name','birthday']
        first_name = schema.attrs[0][1]
        last_name = schema.attrs[1][1]
        birthday = schema.attrs[2][1]
        assert 'schemaish.attr.String' in repr(first_name)
        assert 'schemaish.attr.String' in repr(last_name)
        assert 'schemaish.attr.Date' in repr(birthday)

    def test_types(self):
        schema = get_schema('test_types.yaml')
        keys = [ k for k,v in schema.attrs]
        expected = ['string', 'integer', 'float', 'boolean', 'decimal', 'date',
               'file', 'sequence_string', 'sequence_integer', 'sequence_date']
        assert keys == expected
        for attr in schema.attrs:
            firstbit = attr[0].split('_')[0]
            assert firstbit in repr(attr[1]).lower()
            if len(attr[0]) > len(firstbit):
                nextbit = attr[0].split('_')[1]
                assert nextbit in repr(attr[1].attr).lower()
                if len(attr[0]) > len(firstbit+'_'+nextbit):
                    nextbit = attr[0].split('_')[2]
                    assert nextbit in repr(attr[1].attr.attr).lower()

    def test_substructure(self):
        schema = get_schema('test_substructure.yaml')
        assert 'schemaish.attr.Structure' in repr(schema)
        assert len(schema.attrs) == 3
        keys = [ k for k,v in schema.attrs]
        assert keys == ['first_name','last_name','address']
        first_name = schema.attrs[0][1]
        last_name = schema.attrs[1][1]
        address = schema.attrs[2][1]
        assert 'schemaish.attr.String' in repr(first_name)
        assert 'schemaish.attr.String' in repr(last_name)
        assert 'schemaish.attr.Structure' in repr(address)
        address = address.attrs
        assert len(address) == 4
        for attr in address:
            assert 'schemaish.attr.String' in repr(attr[1])

        
    def test_sequence(self):
        schema = get_schema('test_sequence.yaml')
        countries = schema.attrs[2][1]
        assert 'schemaish.attr.Sequence' in repr(countries)
        assert 'schemaish.attr.String' in repr(countries.attr)


    def test_sequenceofstructs(self):
        schema = get_schema('test_sequenceofstructures.yaml')
        addresses = schema.attrs[2][1]
        assert 'schemaish.attr.Sequence' in repr(addresses)
        address = addresses.attr.attrs
        assert len(address) == 4
        for attr in address:
            assert 'schemaish.attr.String' in repr(attr[1])


    def test_widgets(self):
        form = get_form('test_widgets.yaml')
        assert repr(form['input'].widget) == '<bound widget name="input", widget="Input", type="String">'
        assert repr(form['hidden'].widget) == '<bound widget name="hidden", widget="Hidden", type="String">'
        assert repr(form['textarea'].widget) == '<bound widget name="textarea", widget="TextArea", type="String">'
        assert repr(form['selectchoice'].widget) == '<bound widget name="selectchoice", widget="SelectChoice", type="String">'
        assert repr(form['radiochoice'].widget) == '<bound widget name="radiochoice", widget="RadioChoice", type="String">'
        assert repr(form['selectwithotherchoice'].widget) == '<bound widget name="selectwithotherchoice", widget="SelectWithOtherChoice", type="String">'
        assert repr(form['checkboxmultichoice'].widget) == '<bound widget name="checkboxmultichoice", widget="CheckboxMultiChoice", type="Sequence">'
        
        

