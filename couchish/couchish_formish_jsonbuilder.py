import schemaish, formish
from couchish.formish_jsonbuilder import build as formish_build
from couchish.schemaish_jsonbuilder import SchemaishTypeRegistry
from couchish.formish_jsonbuilder import FormishWidgetRegistry


class Reference(schemaish.attr.Attribute):
    """ a generic reference
    """
    def __init__(self, **k):
        self.refersto = k.pop('refersto')
        schemaish.attr.Attribute.__init__(self,**k)
        


class TypeRegistry(SchemaishTypeRegistry):


    def __init__(self):
        SchemaishTypeRegistry.__init__(self)
        self.registry['Reference()'] = self.reference_factory

    def reference_factory(self, **k):
        return Reference(**k)



class SelectCouchDBChoice(formish.SelectChoice):

    def selected(self, option, value, schemaType):
        o = string_converter(schemaish.Sequence(schemaish.String())).toType(option[0])[0]
        if value:
            v = string_converter(schemaish.Sequence(schemaish.String())).toType(value)[0]
        else:
            v = None
        if o == v:
            return ' selected="selected"'
        else:
            return ''

class WidgetRegistry(FormishWidgetRegistry):

    def __init__(self, db=None):
        self.db = db
        FormishWidgetRegistry.__init__(self)
        self.registry['SelectCouchDBChoice()'] = self.selectcouchdbchoice_factory
        self.defaults['Reference()'] = self.input_factory


    def selectcouchdbchoice_factory(self, widgetSpec):
        def options(db, label_template, view, datakeys):
            results = [jsonutil.decode_from_dict(item['value']) for item in db.view(view)]
            return [ (tuple([result[key] for key in datakeys]), label_template%result) for result in results]
        label_template = widgetSpec['options']['label']
        reference = widgetSpec['options']['reference']
        datakeys = widgetSpec['options']['datakeys']
        view = '%s/all'%reference
        return SelectCouchDBChoice(options=options(self.db, label_template, view, datakeys))


def expand_definition(pre_expand_definition):
    definition = []
    for field in pre_expand_definition['fields']:
        item = {}
        item['key'] = strip_stars(field['name'])
        item['type'] = field.get('type','String()')
        item['view'] = field.get('view', None)
        definition.append(item) 
    return definition


def build(definition, name=None, defaults=None, errors=None, action='', widget_registry=WidgetRegistry(), type_registry=TypeRegistry()):
    form = formish_build(definition, name=name, defaults=defaults, errors=errors, action=action, widget_registry=widget_registry, type_registry=type_registry)
    return form
