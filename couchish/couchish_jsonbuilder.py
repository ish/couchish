import schemaish, formish
from couchish.formish_jsonbuilder import build as formish_build
from couchish.schemaish_jsonbuilder import SchemaishTypeRegistry
from couchish.formish_jsonbuilder import FormishWidgetRegistry
from sets import Set


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

def get_views(models_definition, views_definition):


    views = {} 
    views_by_viewname = {}
    views_by_uses = {} 
    viewnames_by_attribute = {} 
    attributes_by_viewname = {}

    for view in views_definition:
        if 'url' not in view:
            view['url'] = '/couchish/%s'%view['name']
        views_by_viewname[view['name']] = {'url':view['url'], 'map': view['map'], 'key': view.get('key','_id'), 'uses': view('uses',None)}
        views[view['url']] = view['map']


    field_to_view = {}
    for type, definition in models_definition.items():
        for field in definition['fields']:
            if 'refersto' in field:
                refersto = field['refersto']
                view = views_by_viewname[refersto]
                uses = view['uses']

                
                if isinstance(uses, basestring):
                    views_by_uses.setdefault(view['url']+'-rev',{}).setdefault(type,[]).append( field['name'] )
                    viewnames_by_attribute.setdefault(uses, Set()).add(refersto)
                    attributes_by_viewname.setdefault(refersto, {}).setdefault(type,Set()).add( uses )
                else:
                    views_by_uses.setdefault(view['url']+'-rev',{}).setdefault(type,[]).append( field['name'] )
                    for use in uses:
                        viewnames_by_attribute.setdefault(use, Set()).add(refersto)
                        attributes_by_viewname.setdefault(refersto, {}).setdefault(type,Set()).add( use )
            if 'viewby' in field:
                if field['viewby'] == True:
                    url = '/%s/by_%s'%(type,field['name'])
                else:
                    url = field['viewby']
                views[url] = "function(doc) { if (doc.model_type=='%s') { emit(doc.%s,  null ); } }"%(type,field['name'])
            views['/%s/all'%type] = "function(doc) { if (doc.model_type == '%s')  emit(doc._id, null) }"%type




    for url, view in views_by_uses.items():
        viewdef = 'function (doc) {\n'
        for type, attrs in view.items():
            viewdef += '    if (doc.model_type == \''+type+'\'){\n'
            for attr in attrs:
                viewdef += '        emit(doc.'+attr+'._ref, null);\n'
            viewdef += '    }\n'
        viewdef += '}\n'
        views[url] = viewdef

    out = {'views': views,'views_by_viewname': views_by_viewname, 'viewnames_by_attribute': viewnames_by_attribute, 'attributes_by_viewname':attributes_by_viewname}
    return out



def build(definition, name=None, defaults=None, errors=None, action='', widget_registry=WidgetRegistry(), type_registry=TypeRegistry()):
    form = formish_build(definition, name=name, defaults=defaults, errors=errors, action=action, widget_registry=widget_registry, type_registry=type_registry)


    return form
