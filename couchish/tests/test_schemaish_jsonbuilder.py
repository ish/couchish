import unittest
from couchish.schemaish_jsonbuilder import build
import yaml

DATADIR = 'couchish/tests/data/schemaish_jsonbuilder/%s'

def build_schema(filename):
    definition = yaml.load( open(DATADIR%filename).read() )
    schema = build(definition)
    return schema

class Test(unittest.TestCase):

    def test_simple(self):
        schema = build_schema('test_simple.yaml')
        assert 'schemaish.Structure' in repr(schema)
        assert len(schema.attrs) == 3
        keys = [ k for k,v in schema.attrs]
        assert keys == ['first_name','last_name','birthday']
        first_name = schema.attrs[0][1]
        last_name = schema.attrs[1][1]
        birthday = schema.attrs[2][1]
        assert 'schemaish.String' in repr(first_name)
        assert 'schemaish.String' in repr(last_name)
        assert 'schemaish.Date' in repr(birthday)

    def test_types(self):
        schema = build_schema('test_types.yaml')
        keys = [ k for k,v in schema.attrs]
        expected = ['string', 'integer', 'float', 'boolean', 'decimal', 'date',
               'file', 'sequence_string', 'sequence_integer', 'sequence_date','sequence_sequence_string']
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
        schema = build_schema('test_substructure.yaml')
        assert 'schemaish.Structure' in repr(schema)
        assert len(schema.attrs) == 3
        keys = [ k for k,v in schema.attrs]
        assert keys == ['first_name','last_name','address']
        first_name = schema.attrs[0][1]
        last_name = schema.attrs[1][1]
        address = schema.attrs[2][1]
        assert 'schemaish.String' in repr(first_name)
        assert 'schemaish.String' in repr(last_name)
        assert 'schemaish.Structure' in repr(address)
        address = address.attrs
        assert len(address) == 4
        for attr in address:
            assert 'schemaish.String' in repr(attr[1])

        
    def test_sequence(self):
        schema = build_schema('test_sequence.yaml')
        countries = schema.attrs[2][1]
        assert 'schemaish.Sequence' in repr(countries)
        assert 'schemaish.String' in repr(countries.attr)


    def test_sequenceofstructs(self):
        schema = build_schema('test_sequenceofstructures.yaml')
        addresses = schema.attrs[2][1]
        assert 'schemaish.Sequence' in repr(addresses)
        address = addresses.attr.attrs
        assert len(address) == 4
        for attr in address:
            assert 'schemaish.String' in repr(attr[1])



        

