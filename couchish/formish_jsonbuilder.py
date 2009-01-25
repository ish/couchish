from couchish.schemaish_jsonbuilder import build as schema_build, schemaish_type_registry, strip_stars
import formish
from formish import filehandler

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


    def make_formish_widget(self, item_type, widget_spec):
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
        # If there is a widget spec then that takes precedence
        if widget_spec is not None:
            return self.registry[widget_spec['type']](widget_spec)
        # No widget spec so see if there's a user-friendly default for the data type
        default = self.defaults.get(item_type)
        if default is not None:
            return default(widget_spec)
        # OK, so leave it for Formish to decide then
        return None


    def input_factory(self, widget_spec):
        """
        TextInput widget factory.

        Specification attributes:
            None
        """
        return formish.Input()

    def hidden_factory(self, widget_spec):
        """
        Hidden widget factory.

        Specification attributes:
            None
        """
        return formish.Hidden()


    def textarea_factory(self, widget_spec):
        """
        TextArea widget factory.

        Specification attributes:
            None
        """
        return formish.TextArea()


    def selectchoice_factory(self, widget_spec):
        """
        SelectChoice widget factory.

        Specification attributes:
            'options': a sequence of mappings containing 'name' and
                'description' keys.
        """
        first = widget_spec['options'][0]
        if isinstance(first, dict):
            options = [(o['name'], o['description']) for o in widget_spec['options']]
        elif isinstance(first, tuple) or isinstance(first, list):
            options = [(o[0], o[1]) for o in widget_spec['options']]
        else:
            options = [(o, o) for o in widget_spec['options']]
        return formish.SelectChoice(options=options)


    def radiochoice_factory(self, widget_spec):
        """
        SelectChoice widget factory.

        Specification attributes:
            'options': a sequence of mappings containing 'name' and
                'description' keys.
        """
        first = widget_spec['options'][0]
        if isinstance(first, dict):
            options = [(o['name'], o['description']) for o in widget_spec['options']]
        elif isinstance(first, tuple) or isinstance(first, list):
            options = [(o[0], o[1]) for o in widget_spec['options']]
        else:
            options = [(o, o) for o in widget_spec['options']]
        return formish.RadioChoice(options=options)


    def selectwithotherchoice_factory(self, widget_spec):
        """
        SelectChoice widget factory.

        Specification attributes:
            'options': a sequence of strings
        """
        first = widget_spec['options'][0]
        if isinstance(first, dict):
            options = [(o['name'], o['description']) for o in widget_spec['options']]
        elif isinstance(first, tuple) or isinstance(first, list):
            options = [(o[0], o[1]) for o in widget_spec['options']]
        else:
            options = [(o, o) for o in widget_spec['options']]
        return formish.SelectWithOtherChoice(options=options)


    def checkboxmultichoice_factory(self, widget_spec):
        """
        SelectChoice widget factory.

        Specification attributes:
            'options': a sequence of mappings containing 'name' and
                'description' keys.
        """
        first = widget_spec['options'][0]
        if isinstance(first, dict):
            options = [(o['name'], o['description']) for o in widget_spec['options']]
        elif isinstance(first, tuple) or isinstance(first, list):
            options = [(o[0], o[1]) for o in widget_spec['options']]
        else:
            options = [(o, o) for o in widget_spec['options']]
        return formish.CheckboxMultiChoice(options=options)

    def checkbox_factory(self, widget_spec):
        """
        Checkbox widget factory.

        Specification attributes:
            None
        """
        return formish.Checkbox()


    def dateparts_factory(self, widget_spec):
        """
        SelectChoice widget factory.

        Specification attributes:
            None
        """
        return formish.DateParts(day_first=True)


    def fileupload_factory(self,widget_spec):
        if widget_spec is None:
            widget_spec = {}
        originalurl = widget_spec.get('originalurl','/images/missing-image.jpg')
        def urlfactory(obj):
            if isinstance(obj,schemaish.type.File):
                suffix = obj.filename.split('.')[-1]
                return '%s/%s.%s'%(obj.id, obj.attr,suffix)
            else:
                return None
        resource_root = widget_spec.get('options',{}).get('resource_root','/filehandler')
        return formish.FileUpload(filehandler.TempFileHandlerWeb(default_url=originalurl, resource_root=resource_root,urlfactory=urlfactory),originalurl=originalurl)

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
        w = widget_registry.make_formish_widget(item['type'], item.get('widget'))
        if w is not None:
            form[item['starkey']].widget = w

    return form
