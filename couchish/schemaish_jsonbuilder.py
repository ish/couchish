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


def walk_definition(definition):
    """
    Walk the definition keys hierarchy (depth first) generating a sequence of
    (parents, items) tuples, where parents is a sequence of parents with the
    closest parent at the end.
    """

    # Set up a stack to track the parent, None parent to start with.
    stack = [(None, [])]

    for item in definition:

        # Unwind the stack, yielding as we go
        while True:
            parent, children = stack[-1]
            if parent is None or item['key'].startswith(parent['key']):
                break
            parents = [i[0] for i in stack if i[0] is not None]
            yield parents, stack.pop()[1]

        # Grab the top of the stack
        parent, children = stack[-1]

        if item['type'] in ['Structure()','Sequence(Structure())']:
            children.append(item)
            stack.append((item, []))
        else:
            children.append(item)

    # Unwind and yield the remaining stack
    while True:
        if not stack:
            break
        parents = [i[0] for i in stack if i[0] is not None]
        yield parents, stack.pop()[1]

def strip_stars(key):
    outkey = []
    for k in key.split('.'):
        if k != '*':
            outkey.append(k)
    return '.'.join(outkey)


def rec_getattr(obj, attr):
    return reduce(getattr, attr.split('.'), obj)

def rec_setattr(obj, attr, value):
    attrs = attr.split('.')
    setattr(reduce(getattr, attrs[:-1], obj), attrs[-1], value)



class SchemaishTypeRegistry(object):
    """
    Registry for converting an item's type specification to a schemaish type
    instance.
    """

    def __init__(self):
        self.registry = {
                'String()': self.string_factory,
                'Integer()': self.integer_factory,
                'Float()': self.float_factory,
                'Boolean()': self.boolean_factory,
                'Decimal()': self.decimal_factory,
                'Date()': self.date_factory,
                'File()': self.file_factory,
                'Sequence(String())': self.list_factory('String()'),
                'Sequence(Integer())': self.list_factory('Integer()'),
                'Sequence(Date())': self.list_factory('Date()'),
                }


    def make_schemaish_type(self, item_type, **k):
        """
        Map the definition string to a real schemaish type
        XXX: Make the tuple and sequence types work more intelligently (i.e. you shouldn't
        have to match on String, Interger, Date separately)
        """
        if 'Tuple(' in item_type:
            types = ''.join(item_type[7:-1]).split(',')
            return self.tuple_factory(types, **k)
        type_factory = self.registry[item_type]
        return type_factory(**k)


    def string_factory(self, **k):
        return schemaish.String(**k)


    def integer_factory(self, **k):
        return schemaish.Integer(**k)


    def float_factory(self, **k):
        return schemaish.Float(**k)


    def boolean_factory(self, **k):
        return schemaish.Boolean(**k)


    def decimal_factory(self, **k):
        return schemaish.Decimal(**k)


    def date_factory(self, **k):
        return schemaish.Date(**k)


    def file_factory(self, **k):
        return schemaish.File(**k)


    def list_factory(self, subtype):
        def f(**k):
            return schemaish.Sequence(self.make_schemaish_type(subtype), **k)
        return f
    
    def tuple_factory(self, subtypes, **k):
        return schemaish.Tuple([self.make_schemaish_type(subtype) for subtype in subtypes], **k)


schemaish_type_registry=SchemaishTypeRegistry()

def expand_definition(pre_expand_definition):
    definition = []
    for field in pre_expand_definition['fields']:
        item = {}
        item['key'] = strip_stars(field['name'])
        item['starkey'] = field['name']
        if field.get('title') == '':
            item['title'] = None
        else:
            item['title'] = field.get('title')
        item['description'] = field.get('description')
        item['type'] = field.get('type','String()')
        if field.get('required') is True:
            item['validator'] = validator.Required()
        else:
            item['validator'] = None
        definition.append(item)
    return definition


def build(definition, type_registry=schemaish_type_registry):
    definition = expand_definition(definition)
    schema = schemaish.Structure()
    cache = {}    
    for parents, children in walk_definition(definition):

        if parents:
            parent = parents[-1]
        else:
            parent = None

        # Decide how children will be added.
        #
        # When there is a parent we add to a list, cached against the parent's
        # key, so that the children can be added later (we're walking depth
        # first). When there's no parent we can add directly to the form.
        if parent is None:
            child_adder = lambda s: schema.add(*s)
        else:
            child_items = []
            cache[parent['key']] = child_items
            child_adder = child_items.append

        for item in children:

            # Calculate the form item's key
            schemaish_key = relative_schemaish_key(item, parent)

            if item['type'] == 'Structure()':
                # Create a Group, add the cached children and add the group itself.
                group = schemaish.Structure()
                for child in cache.pop(item['key']):
                    group.add(*child)
                child_adder((schemaish_key, group))
            elif item['type'] == 'Sequence(Structure())':
                group = schemaish.Structure()
                for child in cache.pop(item['key']):
                    group.add(*child)
                child_adder((schemaish_key, schemaish.Sequence(group)))
            else:
                # Create and add a field.
                schemaish_type = type_registry.make_schemaish_type(
                    item.get('type','String()'), title=item.get('title'),
                    description=item.get('description'), validator=item.get('validator') )

                child_adder((schemaish_key, schemaish_type))
                
    return schema
        
        

        

