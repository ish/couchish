from couchish.schemaish_jsonbuilder import build as schema_build, schemaish_type_registry, strip_stars
import formish
from formish import filestore
from validatish import validator

class FormishWidgetRegistry(object):
    """
    A registry for mapping a widget specifiction to a Formish widget factory,
    including sensible user-friendly defaults instead of the "developer"
    versions Formish defaults to.
    """
    def __init__(self):
        self.registry = {
                'Input()': self.input_factory,
                'Hidden()': self.hidden_factory,
                'TextArea()': self.textarea_factory,
                'SelectChoice()': self.selectchoice_factory,
                'SelectWithOtherChoice()': self.selectwithotherchoice_factory,
                'Checkbox()': self.checkbox_factory,
                'CheckboxMultiChoice()': self.checkboxmultichoice_factory,
                'RadioChoice()': self.radiochoice_factory,
                'DateParts()': self.dateparts_factory,
                }
        self.defaults = {
                'Date()': self.dateparts_factory,
                'String()': self.input_factory,
                'Integer()': self.input_factory,
                'File()': self.fileupload_factory,
                }


    def make_formish_widget(self,item):
        """
        Create and return a Formish widget factory for the item type and widget
        specifiction.

        If widget_spec is provided then it is used to locate/create and return a
        widget factory.

        If widget_spec is None then either a user-friendly default for the
        item_type is returned or it's left to Formish to decide.

        The widget_spec dictionary must contain a 'type' key, as well as any
        other information needed to build the widget.

        Parameters:
            item_type: the type of the value (string)
            widget_spec: a dictionary containing a widget specification
        """
        widget_spec = item.get('widget')
        item_type = item.get('type')
        # If there is a widget spec then that takes precedence
        if widget_spec is not None:
            return self.registry[widget_spec['type']](item)
        # No widget spec so see if there's a user-friendly default for the data type
        default = self.defaults.get(item_type)
        if default is not None:
            return default(widget_spec)
        # OK, so leave it for Formish to decide then
        return None


    def input_factory(self, spec):
        """
        TextInput widget factory.

        Specification attributes:
            None
        """
        return formish.Input()

    def hidden_factory(self, spec):
        """
        Hidden widget factory.

        Specification attributes:
            None
        """
        return formish.Hidden()


    def textarea_factory(self, spec):
        """
        TextArea widget factory.

        Specification attributes:
            None
        """
        return formish.TextArea()


    def selectchoice_factory(self, spec):
        """
        SelectChoice widget factory.

        Specification attributes:
            'options': a sequence of mappings containing 'name' and
                'description' keys.
        """
        widget_spec = spec.get('widget')
        first = widget_spec['options'][0]
        if isinstance(first, dict):
            options = [(o['name'], o['description']) for o in widget_spec['options']]
        elif isinstance(first, tuple) or isinstance(first, list):
            options = [(o[0], o[1]) for o in widget_spec['options']]
        else:
            options = [(o, o) for o in widget_spec['options']]
        return formish.SelectChoice(options=options)


    def radiochoice_factory(self, spec):
        """
        SelectChoice widget factory.

        Specification attributes:
            'options': a sequence of mappings containing 'name' and
                'description' keys.
        """
        widget_spec = spec.get('widget')
        first = widget_spec['options'][0]
        if isinstance(first, dict):
            options = [(o['name'], o['description']) for o in widget_spec['options']]
        elif isinstance(first, tuple) or isinstance(first, list):
            options = [(o[0], o[1]) for o in widget_spec['options']]
        else:
            options = [(o, o) for o in widget_spec['options']]
        return formish.RadioChoice(options=options)


    def selectwithotherchoice_factory(self, spec):
        """
        SelectChoice widget factory.

        Specification attributes:
            'options': a sequence of strings
        """
        widget_spec = spec.get('widget')
        first = widget_spec['options'][0]
        if isinstance(first, dict):
            options = [(o['name'], o['description']) for o in widget_spec['options']]
        elif isinstance(first, tuple) or isinstance(first, list):
            options = [(o[0], o[1]) for o in widget_spec['options']]
        else:
            options = [(o, o) for o in widget_spec['options']]
        return formish.SelectWithOtherChoice(options=options)


    def checkboxmultichoice_factory(self, spec):
        """
        SelectChoice widget factory.

        Specification attributes:
            'options': a sequence of mappings containing 'name' and
                'description' keys.
        """
        widget_spec = spec.get('widget')
        first = widget_spec['options'][0]
        if isinstance(first, dict):
            options = [(o['name'], o['description']) for o in widget_spec['options']]
        elif isinstance(first, tuple) or isinstance(first, list):
            options = [(o[0], o[1]) for o in widget_spec['options']]
        else:
            options = [(o, o) for o in widget_spec['options']]
        return formish.CheckboxMultiChoice(options=options)

    def checkbox_factory(self, spec):
        """
        Checkbox widget factory.

        Specification attributes:
            None
        """
        return formish.Checkbox()


    def dateparts_factory(self, spec):
        """
        SelectChoice widget factory.

        Specification attributes:
            None
        """
        return formish.DateParts(day_first=True)


    def fileupload_factory(self, spec):
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
                                 )

formish_widget_registry = FormishWidgetRegistry()

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
        if 'widget' in field:
            item['widget'] = {'type': field['widget']['type']}
            if 'options' in field['widget']:
                item['widget']['options'] = field['widget']['options']
        definition.append(item)
    return definition


def build(definition, name=None, defaults=None, errors=None, action='', widget_registry=formish_widget_registry, type_registry=schemaish_type_registry):
    schema = schema_build(definition, type_registry=type_registry)
    definition = expand_definition(definition)
    form = formish.Form(schema, name=name, defaults=defaults, errors=errors, action_url=action)

    for item in definition:
        w = widget_registry.make_formish_widget(item)
        if w is not None:
            form[item['starkey']].widget = w

    return form
