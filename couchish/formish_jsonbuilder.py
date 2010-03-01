from couchish.schemaish_jsonbuilder import build as schema_build, schemaish_type_registry, strip_stars, split_prefix
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
                'Input': self.input_factory,
                'Hidden': self.hidden_factory,
                'TextArea': self.textarea_factory,
                'SelectChoice': self.selectchoice_factory,
                'SelectWithOtherChoice': self.selectwithotherchoice_factory,
                'Checkbox': self.checkbox_factory,
                'CheckboxMultiChoice': self.checkboxmultichoice_factory,
                'RadioChoice': self.radiochoice_factory,
                'DateParts': self.dateparts_factory,
                }
        self.defaults = {
                'Date': self.dateparts_factory,
                'String': self.input_factory,
                'Integer': self.input_factory,
                'File': self.fileupload_factory,
                'Boolean': self.checkbox_factory,
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
        k = {}
        if widget_spec:
            if 'css_class' in widget_spec:
                k['css_class'] = widget_spec['css_class']
            if 'type' in widget_spec:
                return self.registry[widget_spec['type']](item, k)
        # No widget spec so see if there's a user-friendly default for the data type
        default = self.defaults.get(item_type)
        if default is not None:
            return default(item, k)
        # OK, so leave it for Formish to decide then
        return None


    def input_factory(self, spec, k):
        """
        TextInput widget factory.

        Specification attributes:
            None
        """
        return formish.Input(**k)

    def hidden_factory(self, spec, k):
        """
        Hidden widget factory.

        Specification attributes:
            None
        """
        return formish.Hidden(**k)


    def textarea_factory(self, spec, k):
        """
        TextArea widget factory.

        Specification attributes:
            None
        """
        widget_spec = dict(spec['widget'])
        widget_spec.pop('type')
        widget_spec.update(k)
        return formish.TextArea(**widget_spec)


    def selectchoice_factory(self, spec, k):
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
        return formish.SelectChoice(options=options, **k)


    def radiochoice_factory(self, spec, k):
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
        return formish.RadioChoice(options=options, **k)


    def selectwithotherchoice_factory(self, spec, k):
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
        return formish.SelectWithOtherChoice(options=options, **k)


    def checkboxmultichoice_factory(self, spec, k):
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
        return formish.CheckboxMultiChoice(options=options, **k)

    def checkbox_factory(self, spec, k):
        """
        Checkbox widget factory.

        Specification attributes:
            None
        """
        return formish.Checkbox(**k)


    def dateparts_factory(self, spec, k):
        """
        SelectChoice widget factory.

        Specification attributes:
            None
        """
        return formish.DateParts(day_first=True, **k)


    def fileupload_factory(self, spec, k):
        widget_spec = spec.get('widget')
        if widget_spec is None:
            widget_spec = {}
        root_dir = widget_spec.get('root_dir',None)
        url_base = widget_spec.get('url_base',None)
        image_thumbnail_default = widget_spec.get('image_thumbnail_default','/images/missing-image.jpg')
        show_download_link = widget_spec.get('show_download_link',False)
        show_file_preview = widget_spec.get('show_file_preview',True)
        show_image_thumbnail = widget_spec.get('show_image_thumbnail',False)
        return formish.FileUpload(
             filestore.CachedTempFilestore(filestore.FileSystemHeaderedFilestore(root_dir=root_dir)),
             url_base=url_base,
             image_thumbnail_default=image_thumbnail_default,
             show_download_link=show_download_link,
             show_file_preview=show_file_preview,
             show_image_thumbnail=show_image_thumbnail,
             **k )

formish_widget_registry = FormishWidgetRegistry()

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
        if 'default' in item:
            field['default'] = item['default']
        field['attr'] = item.get('attr')
        if item.get('required') is True:
            field['validator'] = validator.Required()
        else:
            field['validator'] = None
        field['widget'] = item.get('widget')
        definition.append(field)
    return definition


def build(definition, name=None, defaults=None, errors=None, action='', widget_registry=formish_widget_registry, type_registry=schemaish_type_registry):
    schema = schema_build(definition, type_registry=type_registry)
    definition = expand_definition(definition)
    form = formish.Form(schema, name=name, defaults=defaults, errors=errors, action_url=action)

    for item in definition:
        w = widget_registry.make_formish_widget(item)
        if w is not None:
            form[item['name']].widget = w
        if 'default' in item:
            form[item['name']].default = item['default']


    return form
