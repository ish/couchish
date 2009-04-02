import schemaish, formish, subprocess, uuid, os
from jsonish import pythonjson as json
from couchish.formish_jsonbuilder import build as formish_build
from couchish.schemaish_jsonbuilder import SchemaishTypeRegistry
from couchish.formish_jsonbuilder import FormishWidgetRegistry
from formish import widgets, filestore, safefilename
from PIL import Image
from schemaish.type import File as SchemaFile
from dottedish import get_dict_from_dotted_dict
from convertish.convert import string_converter

def get_size(filename):
    IDENTIFY = '/usr/bin/identify'
    stdout = subprocess.Popen([IDENTIFY, filename], stdout=subprocess.PIPE).communicate()[0]
    if 'JPEG' in stdout:
        type = 'JPEG'
    if 'PNG' in stdout:
        type = 'PNG'
    if 'GIF' in stdout:
        type = 'GIF'
    dims = stdout.split(type)[1].split(' ')[1]
    width, height = [int(s) for s in dims.split('x')]
    return width, height



class Reference(schemaish.attr.Attribute):
    """ a generic reference
    """
    def __init__(self, **k):
        self.refersto = k['attr']['refersto']
        #self.uses = k['attr']['uses']
        schemaish.attr.Attribute.__init__(self,**k)
        


class TypeRegistry(SchemaishTypeRegistry):


    def __init__(self):
        SchemaishTypeRegistry.__init__(self)
        self.registry['Reference'] = self.reference_factory

    def reference_factory(self, field):
        return Reference(**field)


UNSET = object()

class FileUpload(formish.FileUpload):

    def __init__(self, filestore, show_file_preview=True, show_download_link=False, show_image_thumbnail=False, url_base=None, \
                 css_class=None, image_thumbnail_default=None, url_ident_factory=None, identify_size=False):
        formish.FileUpload.__init__(self, filestore, show_file_preview=show_file_preview, show_download_link=show_download_link, \
            show_image_thumbnail=show_image_thumbnail, url_base=url_base, css_class=css_class, image_thumbnail_default=image_thumbnail_default, url_ident_factory=url_ident_factory)
        self.identify_size = identify_size

    def pre_parse_request(self, schema_type, data, full_request_data):
        """
        File uploads are wierd; in out case this means assymetric. We store the
        file in a temporary location and just store an identifier in the field.
        This at least makes the file look symmetric.
        """
        if data.get('remove', [None])[0] is not None:
            data['name'] = ['']
            data['mimetype'] = ['']
            return data

        fieldstorage = data.get('file', [''])[0]
        if getattr(fieldstorage,'file',None):
            filename = '%s-%s'%(uuid.uuid4().hex,fieldstorage.filename)
            self.filestore.put(filename, fieldstorage.file, fieldstorage.type, uuid.uuid4().hex)
            data['name'] = [filename]
            data['mimetype'] = [fieldstorage.type]
        if self.identify_size is True and fieldstorage != '':
            fieldstorage.file.seek(0)
            width, height = Image.open(fieldstorage.file).size
            data['width'] = [width]
            data['height'] = [height]
        return data

    def convert(self, schema_type, request_data):
        """
        Creates a File object if possible
        """
        # XXX We could add a file converter that converts this to a string data?

        if request_data['name'] == ['']:
            return None
        elif request_data['name'] == request_data['default']:
            return SchemaFile(None, None, None)
        else:
            filename = request_data['name'][0]
            try:
                content_type, cache_tag, f = self.filestore.get(filename)
            except KeyError:
                return None
            if self.identify_size == True:
                metadata = {'width':request_data['width'][0], 'height': request_data['height'][0]}
            else:
                metadata = None
            return SchemaFile(f, filename, content_type, metadata=metadata)

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
        self.sort = k.pop('sort', UNSET)
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
        if self.sort == True:
            _options.sort(lambda x, y: cmp(x[1], y[1]))

        self.options = []
        for (value, label) in _options:
            if value == self.empty:
                self.options.append( ('',label) )
            else:
                self.options.append( (value,label) )
        return self.options



def get_parent(segments):
    if len(segments) == 1:
        return ''
    else:
        return '.'.join(segments[:-1])

def mktree(options):
    last_segments_len = 1
    root = {'': {'data':('root', 'Root'), 'children':[]} }
    for id, label in options:
        segments = id.split('.')
        parent = get_parent(segments)
        root[id] = {'data': (id, label), 'children':[]}
        root[parent]['children'].append(root[id])
    return root['']

class CheckboxMultiChoiceTreeCouchDB(formish.CheckboxMultiChoiceTree):

    _template='CheckboxMultiChoiceTreeCouchDB'

    def __init__(self, full_options, cssClass=None):
        self.options = [ (key, value['data']['label']) for key, value in full_options]
        self.full_options = dict(full_options)
        self.optiontree = mktree(self.options)
        widgets.Widget.__init__(self,cssClass=cssClass)

    def pre_render(self, schema_type, data):
        if data is None:
            return []
        return [c['path'] for c in data]

    def checked(self, option, values, schema_type):
        if values is not None and option[0] in values:
            return ' checked="checked"'
        else:
            return ''

    def convert(self, schema_type, data):
        out = []
        for item in data:
            out.append(self.full_options[item])
        return out

class SeqRefTextArea(formish.Input):
    """
    Textarea input field

    :arg cols: set the cols attr on the textarea element
    :arg rows: set the cols attr on the textarea element
    """

    _template = 'SeqRefTextArea'

    def __init__(self, db, view, **k):
        self.cols = k.pop('cols', None)
        self.rows = k.pop('rows', None)
        self.strip = k.pop('strip', True)
        self.db = db
        self.view = view
        formish.Input.__init__(self, **k)
        if not self.converter_options.has_key('delimiter'):
            self.converter_options['delimiter'] = '\n'

    def pre_render(self, schema_type, data):
        """
        We're using the converter options to allow processing sequence data
        using the csv module
        """
        if data is None:
            return []
        string_data = [d['_ref'] for d in data]
        return string_data

    def convert(self, schema_type, request_data):
        """
        We're using the converter options to allow processing sequence data
        using the csv module
        """
        string_data = request_data[0]
        if self.strip is True:
            string_data = string_data.strip()
        if string_data == '':
            return self.empty
        ids = [s.strip() for s in string_data.splitlines()]
        docs = self.db.view(self.view, keys=ids)
        out = []
        for d in docs:
            d.value.update({'_ref': d.key})
            out.append(d.value)
        return out

    def __repr__(self):
        attributes = []
        if self.strip is False:
            attributes.append('strip=%r'%self.strip)
        if self.converter_options != {'delimiter':','}:
            attributes.append('converter_options=%r'%self.converter_options)
        if self.css_class:
            attributes.append('css_class=%r'%self.css_class)
        if self.empty is not None:
            attributes.append('empty=%r'%self.empty)

        return 'couchish_formish_jsonbuilder.%s(%s)'%(self.__class__.__name__, ', '.join(attributes))


class WidgetRegistry(FormishWidgetRegistry):

    def __init__(self, db=None):
        self.db = db
        FormishWidgetRegistry.__init__(self)
        self.registry['SeqRefTextArea'] = self.seqreftextarea_factory
        self.registry['SelectChoiceCouchDB'] = self.selectchoice_couchdb_factory
        self.registry['CheckboxMultiChoiceTreeCouchDB'] = self.checkboxmultichoicetree_couchdb_factory
        self.registry['CheckboxMultiChoiceTreeCouchDBFacet'] = self.checkboxmultichoicetree_couchdbfacet_factory
        self.defaults['Reference'] = self.selectchoice_couchdb_factory


    def selectchoice_couchdb_factory(self, spec, k):
        if spec is None:
            spec = {}
        widget_spec = spec.get('widget')
        if widget_spec is None:
            widget_spec = {}
        label_template = widget_spec.get('label', '%s')
        k['sort'] = widget_spec.get('sort')
        attr = spec.get('attr',{})
        if attr is None:
            refersto = None
        else:
            refersto = attr.get('refersto')
        view = widget_spec.get('view', refersto)
        return SelectChoiceCouchDB(self.db, view, label_template, **k)

    def checkboxmultichoicetree_couchdb_factory(self, spec, k):
        widgetSpec = spec.get('widget')
        def options(db, view):
            return [(item.id,item.doc['label']) for item in list(db.view(view, include_docs=True))]
        view = widgetSpec['options']
        return formish.CheckboxMultiChoiceTree(options=options(self.db,view), **k)

    def seqreftextarea_factory(self, spec, k):
        if spec is None:
            spec = {}
        widget_spec = spec.get('widget')
        if widget_spec is None:
            widget_spec = {}
        attr = spec.get('attr',{}).get('attr',{})
        if attr is None:
            refersto = None
        else:
            refersto = attr.get('refersto')
        view = widget_spec.get('view', refersto)
        return SeqRefTextArea(self.db, view, **k)

    def checkboxmultichoicetree_couchdbfacet_factory(self, spec, k):
        widgetSpec = spec.get('widget')
        def options(db, view):
            facet = list(db.view(view, include_docs=True))[0].doc
            options = []
            for item in facet['category']:
                options.append( (item['path'],item) )
            return options
        view = 'facet_%s/all'%widgetSpec['facet']

        return CheckboxMultiChoiceTreeCouchDB(full_options=options(self.db,view), **k)

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
        identify_size = widget_spec.get('options',{}).get('identify_size',False)
        return FileUpload(filestore.CachedTempFilestore(root_dir=root_dir), \
             url_base=url_base,
             image_thumbnail_default=image_thumbnail_default,
             show_download_link=show_download_link,
             show_file_preview=show_file_preview,
             show_image_thumbnail=show_image_thumbnail,
             url_ident_factory=url_ident_factory,
             identify_size=identify_size,
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

