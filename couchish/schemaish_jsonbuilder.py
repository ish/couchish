import schemaish
from validatish import validator

KEY_MUNGING = [
        ('-', '__dash__'),
        ('/', '__slash__'),
        ]

def relative_schemaish_key(item, parent):
    """
    Calculate and return the item's key relative to the parent.
    """
    # We only care about the keys
    item = splitkey(item['key'])
    if parent is not None:
        parent = splitkey(parent['key'])
    # Do basic sanity checks
    if parent is not None and not is_descendant_key(item, parent):
        raise ValueError("'item' is not a descendant of 'parent'")
    # Remove the parent's part of the key, that should already have
    # been accounted for as a group item.
    if parent is not None:
        item = descendant_key_part(item, parent)
    # Turn the item key back into a string.
    item = joinkey(item)
    # Replace characters that formish doesn't allow
    for search, replace in KEY_MUNGING:
        item = item.replace(search, replace)
    return item


def full_schemaish_key(item, parents):
    """
    Calculate and return the full formish key of the item specified by the item
    chain.
    """
    # Build a chain of items with a None at the end that is convenient for
    # feeding to relative_schemaish_key.
    itemchain = list(parents)
    itemchain.append(item)
    itemchain.reverse()
    itemchain.append(None)
    # Build the full key from the relative formish key for each of the pairs,
    # all joined together again.
    fullkey = [relative_schemaish_key(item, parent) for (item, parent) in pairs(itemchain)]
    fullkey.reverse()
    return joinkey(fullkey)


def pairs(s):
    """
    Simple generator that yields len(s)-1 pairs of items, i.e. each item except
    the last is yielded as the first item.
    """
    unset = object()
    first, second = unset, unset
    it = iter(s)
    while True:
        if first is unset:
            first = it.next()
        second = it.next()
        yield (first, second)
        first = second


def splitkey(key):
    """
    Split a key in string form into its parts.
    """
    return key.split('.')


def joinkey(key):
    """
    Join a key's parts to create a key in string form.
    """
    return '.'.join(key)


def is_descendant_key(item, ancestor):
    """
    Test if item is a descendant of ancestor.
    """
    return item[:len(ancestor)] == ancestor


def descendant_key_part(item, ancestor):
    """
    Return the part of the item key that is not shared with the ancestor.
    """
    return item[len(ancestor):]


def strip_stars(key):
    outkey = []
    for k in key.split('.'):
        if k != '*':
            outkey.append(k)
    return '.'.join(outkey)

def split_prefix(key):
    segments = key.split('.')
    return '.'.join(segments[:-1]), segments[-1]


def rec_getattr(obj, attr):
    return reduce(getattr, attr.split('.'), obj)

def rec_setattr(obj, attr, value):
    attrs = attr.split('.')
    setattr(reduce(getattr, attrs[:-1], obj), attrs[-1], value)



class SchemaishTypeRegistry(object):
    """
    Registry for converting an field's type specification to a schemaish type
    instance.
    """
    
    def __init__(self):
        self.registry = {
                'String': self.string_factory,
                'Integer': self.integer_factory,
                'Float': self.float_factory,
                'Boolean': self.boolean_factory,
                'Decimal': self.decimal_factory,
                'Date': self.date_factory,
                'Time': self.time_factory,
                'DateTime': self.datetime_factory,
                'File': self.file_factory,
                'Sequence': self.list_factory,
                'Tuple': self.tuple_factory,
                'Structure': self.structure_factory,
                }
        self.default_type = 'String'


    def make_schemaish_type(self, field):
        field_type = field.get('type',self.default_type)
        return self.registry[field_type](field)


    def string_factory(self, field):
        return schemaish.String(**field)

    def integer_factory(self, field):
        return schemaish.Integer(**field)

    def float_factory(self, field):
        return schemaish.Float(**field)

    def boolean_factory(self, field):
        return schemaish.Boolean(**field)

    def decimal_factory(self, field):
        return schemaish.Decimal(**field)

    def date_factory(self, field):
        return schemaish.Date(**field)

    def time_factory(self, field):
        return schemaish.Time(**field)

    def datetime_factory(self, field):
        return schemaish.DateTime(**field)

    def file_factory(self, field):
        return schemaish.File(**field)

    def list_factory(self, field):
        field = dict(field)
        attr = field.pop('attr')
        attr_type = self.make_schemaish_type(attr)
        return schemaish.Sequence(attr_type, **field)
    
    def tuple_factory(self, field):
        field = dict(field)
        attr = field.pop('attr')
        attr_types = []
        for a in attr['types']:
            attr_types.append(self.make_schemaish_type(a))
        return schemaish.Tuple(attr_types, **field)

    def structure_factory(self, field):
        return schemaish.Structure(**field)

schemaish_type_registry=SchemaishTypeRegistry()

def expand_definition(pre_expand_definition):
    definition = []
    for item in pre_expand_definition['fields']:
        field = {}
        field['name'] = item['name']
        field['fullkey'] = strip_stars(item['name'])
        field['keyprefix'], field['key'] = split_prefix(field['fullkey'])
        field['starkey'] = item['name']
        field['title'] = item.get('title')
        field['description'] = item.get('description')
        field['type'] = item.get('type','String')
        field['attr'] = item.get('attr')
        if item.get('required') is True:
            field['validator'] = validator.Required()
        else:
            field['validator'] = None
        definition.append(field)
    return definition

def get_nested_attr(schema_type):
    if hasattr(schema_type, 'attr'):
        return get_nested_attr(schema_type.attr)
    else:
        return schema_type

def build(definition, type_registry=schemaish_type_registry):
    definition = expand_definition(definition)
    schema = schemaish.Structure()
    schema_pointer_hash = {'': schema}
    for field in definition:
        if 'name' not in field:
            continue
        fullkey = field['fullkey']
        keyprefix = field['keyprefix']
        key = field['key']

        try:
            S = schema_pointer_hash[keyprefix]
        except KeyError: 
            raise KeyError('It is likely that you haven\'t defined your keys in the right order. A field must exist before sub-fields are encountered')
        schema_type = type_registry.make_schemaish_type(field)
        S.add( key, schema_type )

        schema_pointer_hash[fullkey] = get_nested_attr(schema_type)
            
    return schema
        
        

        

