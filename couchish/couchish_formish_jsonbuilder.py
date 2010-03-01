import schemaish, formish, subprocess, uuid, os
from jsonish import pythonjson as json
from couchish.formish_jsonbuilder import build as formish_build
from couchish.schemaish_jsonbuilder import SchemaishTypeRegistry
from couchish.formish_jsonbuilder import FormishWidgetRegistry
from formish import widgets, filestore, safefilename, util
from PIL import Image
from schemaish.type import File as SchemaFile
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



class Reference(schemaish.attr.LeafAttribute):
    """ a generic reference
    """
    type = "Reference"

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

    type="ImageFileUpload"

    def __init__(self, filestore=filestore, show_file_preview=True, show_download_link=False, show_image_thumbnail=False, url_base=None, \
                 css_class=None, image_thumbnail_default=None, url_ident_factory=None, identify_size=False):
        formish.FileUpload.__init__(self, filestore=filestore, show_file_preview=show_file_preview, show_download_link=show_download_link, \
            show_image_thumbnail=show_image_thumbnail, url_base=url_base, css_class=css_class, image_thumbnail_default=image_thumbnail_default, url_ident_factory=url_ident_factory)
        self.identify_size = identify_size

    def pre_parse_incoming_request_data(self, field, data):
        """
        File uploads are wierd; in out case this means assymetric. We store the
        file in a temporary location and just store an identifier in the field.
        This at least makes the file look symmetric.
        """
        if data.get('remove', [None])[0] is not None:
            data['name'] = ['']
            data['mimetype'] = ['']
            data['height'] = ['']
            data['width'] = ['']
            return data

        fieldstorage = data.get('file', [''])[0]
        if getattr(fieldstorage,'file',None):
            key = uuid.uuid4().hex
            self.filestore.put(key, fieldstorage.file, uuid.uuid4().hex, [('Content-Type',fieldstorage.type),('Filename',fieldstorage.filename)])
            data['name'] = [util.encode_file_resource_path('tmp', key)] 
            data['mimetype'] = [fieldstorage.type]
        if self.identify_size is True and fieldstorage != '':
            fieldstorage.file.seek(0)
            width, height = Image.open(fieldstorage.file).size
            data['width'] = [width]
            data['height'] = [height]
        else:
            data['width'] = [None]
            data['height'] = [None]
        return data

    def from_request_data(self, field, request_data):
        """
        Creates a File object if possible
        """
        # XXX We could add a file converter that converts this to a string data?

        if request_data['name'] == ['']:
            return None
        elif request_data['name'] == request_data['default']:
            return SchemaFile(None, None, None)
        else:
            key = util.decode_file_resource_path(request_data['name'][0])[1]
            try:
                cache_tag, headers, f = self.filestore.get(key)
            except KeyError:
                return None
            headers = dict(headers)
            if self.identify_size == True:
                metadata = {'width':request_data['width'][0], 'height': request_data['height'][0]}
            else:
                metadata = None
            return SchemaFile(f, headers['Filename'], headers['Content-Type'],metadata=metadata)

class SelectChoiceCouchDB(widgets.Widget):

    none_option = (None, '- choose -')
    type="SelectChoice"
    template='field.SelectChoice'


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


    def selected(self, option, field):
        if field.value == ['']:
            v = self.empty
        else:
            v = field.value[0]
        if option[0] == v:
            return ' selected="selected"'
        else:
            return ''


    def to_request_data(self, field, data):
        """
        Before the widget is rendered, the data is converted to a string
        format.If the data is None then we return an empty string. The sequence
        is request data representation.
        """
        if data is None:
            return ['']
        string_data = data.get('_ref')
        return [string_data]


    def from_request_data(self, field, request_data):
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

    def get_none_option_value(self, field):
        """
        Get the default option (the 'unselected' option)
        """
        none_option =  self.none_option[0]
        if none_option is self.empty:
            return ''
        return none_option

    def get_options(self, field=None):
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
    _options = list(options)
    _options.sort(lambda x, y: cmp(len(x[0].split('.')), len(y[0].split('.'))))
    last_segments_len = 1
    root = {'': {'data':('root', 'Root'), 'children':[]} }
    for id, label in _options:
        segments = id.split('.')
        parent = get_parent(segments)
        root[id] = {'data': (id, label), 'children':[]}
        root[parent]['children'].append(root[id])
    return root['']




class SelectChoiceFacetTreeCouchDB(widgets.Widget):
    """
    Select a single category from a facet using a <select> list.
    """

    template='field.SelectChoice'
    type = "SelectChoiceFacetTree"

    none_option = ('', '- choose -')

    def __init__(self, options, **k):
        widgets.Widget.__init__(self, **k)
        # "Indent" nodes' labels.
        def indented_label(key, label):
            return ''.join(['-']*(len(key.split('.'))-1)+[label])
        self.options = [(key, indented_label(key, value['data']['label']))
                        for (key, value) in options]
        # Used to map from chosen item back to category reference.
        self.options_by_path = dict(options)

    ##
    # Request data methods.

    def to_request_data(self, field, data):
        if data is None:
            return [None]
        return [data['path']]

    def from_request_data(self, field, data):
        if data[0] == self.none_option[0]:
            return None
        return self.options_by_path[data[0]]

    ##
    # Methods required by the SelectChoice template

    def get_none_option_value(self, field):
        return self.none_option[0]

    def get_options(self, field):
        return self.options

    def selected(self, option, field):
        if field.value is not None and option[0] == field.value[0]:
            return ' selected="selected"'
        return ''


# XXX Rename to include "Facet"

class CheckboxMultiChoiceTreeCouchDB(formish.CheckboxMultiChoiceTree):

    template='field.CheckboxMultiChoiceTreeCouchDB'
    type = "CheckboxMultiChoiceTree"
    default_value = []

    def __init__(self, full_options, css_class=None):
        self.options = [ (key, value['data']['label']) for key, value in full_options]
        self.full_options = dict(full_options)
        self.optiontree = mktree(self.options)
        widgets.Widget.__init__(self,css_class=css_class)

    def to_request_data(self, field, data):
        if data is None:
            return []
        return [c['path'] for c in data]

    def checked(self, option, field):
        if field.value is not None and option[0] in field.value:
            return ' checked="checked"'
        else:
            return ''

    def from_request_data(self, field, data):
        return [self.full_options[item] for item in data]


class RefInput(formish.Input):
    """
    Simple text input field for entering a reference to another object.
    """

    type = "RefInput"

    def __init__(self, db, **k):
        self.db = db
        self.additional_fields = k.pop('additional_fields', [])
        formish.Input.__init__(self, **k)

    def to_request_data(self, field, data):
        if data is None:
            return ['']
        additional_fields = ['_ref'] + self.additional_fields
        return ['|'.join(data.get(attr, '') for attr in additional_fields)]

    def from_request_data(self, field, request_data):
        data = request_data[0].strip()
        # Extract the id from the content.
        id = data.split('|', 1)[0]
        # Return default if nothing entered.
        if not id:
            return self.empty
        # Convert the id into a ref and return.
        row = iter(self.db.view(field.attr.refersto, key=id)).next()
        ref = row.value
        ref.update({'_ref': row.key})
        return ref


class SeqRefTextArea(formish.Input):
    """
    Textarea input field

    :arg cols: set the cols attr on the textarea element
    :arg rows: set the cols attr on the textarea element
    """

    template = 'field.SeqRefTextArea'
    type="SeqRefTextArea"

    def __init__(self, db, view, **k):
        self.cols = k.pop('cols', None)
        self.rows = k.pop('rows', None)
        self.additional_fields = k.pop('additional_fields', [])
        self.db = db
        self.view = view
        formish.Input.__init__(self, **k)
        if not self.converter_options.has_key('delimiter'):
            self.converter_options['delimiter'] = '\n'

    def to_request_data(self, field, data):
        """
        We're using the converter options to allow processing sequence data
        using the csv module
        """
        if data is None:
            return []
        additional_fields = ['_ref'] + self.additional_fields
        return ['|'.join(d.get(attr, '') for attr in additional_fields) for d in data]

    def from_request_data(self, field, request_data):
        """
        We're using the converter options to allow processing sequence data
        using the csv module
        """
        # Extract the list of ids from the content, discarding empty lines.
        rows = request_data[0].splitlines()
        rows = (row.strip() for row in rows)
        rows = (row for row in rows if row)
        rows = (row.split('|', 1) for row in rows)
        ids = [row[0] for row in rows]
        # Return default if nothing entered.
        if not ids:
            return self.empty
        # Convert the ids into refs.
        rows = self.db.view(self.view, keys=ids)
        for row in rows:
            row.value.update({'_ref': row.key})
        return [row.value for row in rows]

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

    def __init__(self, store):
        FormishWidgetRegistry.__init__(self)
        self.store = store
        self.registry['RefInput'] = self.refinput_factory
        self.registry['SeqRefTextArea'] = self.seqreftextarea_factory
        self.registry['SelectChoiceCouchDB'] = self.selectchoice_couchdb_factory
        self.registry['SelectChoiceFacetTreeCouchDB'] = self.selectchoice_couchdbfacet_factory
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
        return SelectChoiceCouchDB(self.store.db, view, label_template, **k)

    def checkboxmultichoicetree_couchdb_factory(self, spec, k):
        widgetSpec = spec.get('widget')
        def options(db, view):
            return [(item.id,item.doc['label']) for item in list(db.view(view, include_docs=True))]
        view = widgetSpec['options']
        return formish.CheckboxMultiChoiceTree(options=options(self.store.db, view), **k)

    def refinput_factory(self, spec, k):
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
        additional_fields = widget_spec.get('additional_fields',[])
        return RefInput(self.store.db, additional_fields=additional_fields, **k)

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
        additional_fields = widget_spec.get('additional_fields',[])
        return SeqRefTextArea(self.store.db, view, additional_fields=additional_fields, **k)

    def selectchoice_couchdbfacet_factory(self, spec, k):
        widgetSpec = spec.get('widget')
        def options(db, view):
            facet = list(db.view(view, include_docs=True))[0].doc
            options = []
            for item in facet['category']:
                options.append( (item['path'],item) )
            return options
        config = self.store.config.types['facet_%s'%widgetSpec['facet']]
        view = config['metadata']['views']['all']
        return SelectChoiceFacetTreeCouchDB(options=options(self.store.db, view), **k)

    def checkboxmultichoicetree_couchdbfacet_factory(self, spec, k):
        widgetSpec = spec.get('widget')
        def options(db, view):
            facet = list(db.view(view, include_docs=True))[0].doc
            options = []
            for item in facet['category']:
                options.append( (item['path'],item) )
            return options
        config = self.store.config.types['facet_%s'%widgetSpec['facet']]
        view = config['metadata']['views']['all']
        return CheckboxMultiChoiceTreeCouchDB(full_options=options(self.store.db, view), **k)

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
        url_base = widget_spec.get('url_base',None)
        image_thumbnail_default = widget_spec.get('image_thumbnail_default','/images/missing-image.jpg')
        show_download_link = widget_spec.get('show_download_link',False)
        show_file_preview = widget_spec.get('show_file_preview',True)
        show_image_thumbnail = widget_spec.get('show_image_thumbnail',False)
        identify_size = widget_spec.get('identify_size',False)
        return FileUpload( filestore=filestore.CachedTempFilestore(),
             url_base=url_base,
             image_thumbnail_default=image_thumbnail_default,
             show_download_link=show_download_link,
             show_file_preview=show_file_preview,
             show_image_thumbnail=show_image_thumbnail,
             url_ident_factory=url_ident_factory,
             identify_size=identify_size,
             **k )





def build(definition, store=None, name=None, defaults=None, errors=None, action='', widget_registry=None, type_registry=None, add_id_and_rev=False):
    if widget_registry is None:
        widget_registry=WidgetRegistry(store)
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

