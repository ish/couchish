import schemaish, formish
from jsonish import pythonjson as json
from couchish.formish_jsonbuilder import build as formish_build
from couchish.schemaish_jsonbuilder import SchemaishTypeRegistry
from couchish.formish_jsonbuilder import FormishWidgetRegistry
from formish import widgets, filestore


class Reference(schemaish.attr.Attribute):
    """ a generic reference
    """
    def __init__(self, **k):
        self.refersto = k['attr']['refersto']
        self.uses = k['attr']['uses']
        schemaish.attr.Attribute.__init__(self,**k)
        


class TypeRegistry(SchemaishTypeRegistry):


    def __init__(self):
        SchemaishTypeRegistry.__init__(self)
        self.registry['Reference'] = self.reference_factory

    def reference_factory(self, field):
        return Reference(**field)


UNSET = object()

class SelectChoiceCouchDB(widgets.Widget):

    none_option = (None, '- choose -')
    _template='SelectChoice'

    def __init__(self, db, view, label_template, **k):
        """
        :arg options: either a list of values ``[value,]`` where value is used for the label or a list of tuples of the form ``[(value, label),]``
        :arg none_option: a tuple of ``(value, label)`` to use as the unselected option
        :arg css_class: a css class to apply to the field
        """
        none_option = k.pop('none_option', UNSET)
        if none_option is not UNSET:
            self.none_option = none_option
        widgets.Widget.__init__(self, **k)
        self.db = db
        self.view = view
        self.label_template = label_template
        self.options = None
        self.results = None


    def selected(self, option, value, schemaType):
        if value == '':
            v = self.empty
        else:
            v = value
        if option[0] == v:
            return ' selected="selected"'
        else:
            return ''


    def pre_render(self, schema_type, data):
        """
        Before the widget is rendered, the data is converted to a string
        format.If the data is None then we return an empty string. The sequence
        is request data representation.
        """
        if data is None:
            return ['']
        string_data = data.get('_ref')
        return [string_data]


    def convert(self, schema_type, request_data):
        """
        after the form has been submitted, the request data is converted into
        to the schema type.
        """
        self.get_options()
        string_data = request_data[0]
        if string_data == '':
            return self.empty
        result = self.results[string_data]
        if isinstance(result, dict):
            result['_ref'] = string_data
            return result
        else:
            return {'_ref':string_data, 'data':result}

    def get_none_option_value(self, schema_type):
        """
        Get the default option (the 'unselected' option)
        """
        none_option =  self.none_option[0]
        if none_option is self.empty:
            return ''
        return none_option

    def get_options(self, schema_type=None):
        """
        Return all of the options for the widget
        """
        if self.options is not None:
            return self.options
        results = [json.decode_from_dict(item) for item in self.db.view(self.view)]
        self.results = dict((result['id'], result['value']) for result in results)
        _options = [ (result['id'], self.label_template%result['value']) for result in results]

        self.options = []
        for (value, label) in _options:
            if value == self.empty:
                self.options.append( ('',label) )
            else:
                self.options.append( (value,label) )
        return self.options




class WidgetRegistry(FormishWidgetRegistry):

    def __init__(self, db=None):
        self.db = db
        FormishWidgetRegistry.__init__(self)
        self.registry['SelectChoiceCouchDB'] = self.selectchoice_couchdb_factory
        self.registry['CheckboxMultiChoiceTreeCouchDB'] = self.checkboxmultichoicetree_couchdb_factory
        self.defaults['Reference'] = self.selectchoice_couchdb_factory


    def selectchoice_couchdb_factory(self, spec, k):
        if spec is None:
            spec = {}
        widget_spec = spec.get('widget')
        if widget_spec is None:
            widget_spec = {}
        label_template = widget_spec.get('label', '%s')
        view = widget_spec.get('view', spec.get('attr',{}).get('refersto'))
        return SelectChoiceCouchDB(self.db, view, label_template, **k)

    def checkboxmultichoicetree_couchdb_factory(self, spec, k):
        widgetSpec = spec.get('widget')
        def options(db, view):
            return [(item.id,item.doc['label']) for item in list(db.view(view, include_docs=True))]
        view = widgetSpec['options']
        return formish.CheckboxMultiChoiceTree(options=options(self.db,view), **k)

    def fileupload_factory(self, spec, k):
        widget_spec = spec.get('widget')
        if widget_spec is None:
            widget_spec = {}
        def url_ident_factory(obj):
            if isinstance(obj,schemaish.type.File):
                return '%s/%s'%(obj.doc_id, obj.id)
            elif obj:
                return obj
            else:
                return None
        root_dir = widget_spec.get('options',{}).get('root_dir',None)
        url_base = widget_spec.get('options',{}).get('url_base',None)
        image_thumbnail_default = widget_spec.get('image_thumbnail_default','/images/missing-image.jpg')
        show_download_link = widget_spec.get('options',{}).get('show_download_link',False)
        show_file_preview = widget_spec.get('options',{}).get('show_file_preview',True)
        show_image_thumbnail = widget_spec.get('options',{}).get('show_image_thumbnail',False)
        return formish.FileUpload(filestore.CachedTempFilestore(root_dir=root_dir), \
             url_base=url_base,
             image_thumbnail_default=image_thumbnail_default,
             show_download_link=show_download_link,
             show_file_preview=show_file_preview,
             show_image_thumbnail=show_image_thumbnail,
             url_ident_factory=url_ident_factory,
             **k )


def build(definition, db=None, name=None, defaults=None, errors=None, action='', widget_registry=None, type_registry=None, add_id_and_rev=False):
    if widget_registry is None:
        widget_registry=WidgetRegistry(db)
    if type_registry is None:
        type_registry=TypeRegistry()
    if add_id_and_rev is True:
        # Copy the definition fict and its fields item so we can make changes
        # without affecting the spec.
        definition = dict(definition)
        definition['fields'] = list(definition['fields'])
        definition['fields'].insert(0, {'name': '_rev', 'widget':{'type': 'Hidden'}})
        definition['fields'].insert(0, {'name': '_id', 'widget':{'type': 'Hidden'}})
    form = formish_build(definition, name=name, defaults=defaults, errors=errors, action=action, widget_registry=widget_registry, type_registry=type_registry)
    return form

