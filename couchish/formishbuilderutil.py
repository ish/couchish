import logging
import yaml
from couchdb.design import ViewDefinition

from pollen import jsonutil

import formish
from formishbuilder.builder import process_formishbuilder_form_definition, build
from formishbuilder.registry import formishTypeRegistry, formishWidgetRegistry, FormishWidgetRegistry, FormishTypeRegistry
from convertish.convert import string_converter
import schemaish.type

log = logging.getLogger(__name__)

class CouchDBSelectChoice(formish.SelectChoice):

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
    def __init__(self, db):
        self.db = db
        FormishWidgetRegistry.__init__(self)
        self.registry['select-choice-couchdb'] = self.selectChoiceCouchDBFactory
        self.registry['checkbox-multi-choice-tree-couchdb'] = self.checkboxMultiChoiceTreeCouchDBFactory
        self.registry['file-upload-couchdb'] = self.fileUploadCouchDBFactory
    def selectChoiceCouchDBFactory(self, widgetSpec):
        def options(db, label_template, view, datakeys):
            results = [jsonutil.decode_from_dict(item['value']) for item in db.view(view)]
            return [ (tuple([result[key] for key in datakeys]), label_template%result) for result in results]
        label_template = widgetSpec['options']['label']
        reference = widgetSpec['options']['reference']
        datakeys = widgetSpec['options']['datakeys'] 
        view = '%s/all'%reference
        return CouchDBSelectChoice(options=options(self.db, label_template, view, datakeys))
    def checkboxMultiChoiceTreeCouchDBFactory(self, widgetSpec):
        def options(db, view):
            return [(item['key'][0],item['key'][1]) for item in db.view(view)]
        view = widgetSpec['options']
        return formish.CheckboxMultiChoiceTree(options=options(self.db,view))
    def fileUploadCouchDBFactory(self, widgetSpec):
        originalurl = widgetSpec['options'].get('originalurl','/images/missing-image.jpg')
        def urlfactory(obj):
            if isinstance(obj,schemaish.type.File):
                suffix = obj.filename.split('.')[-1]
                return '%s/%s.%s'%(obj.id, obj.attr,suffix)
            else:
                return None
        resource_root = widgetSpec['options']['resource_root']
        return formish.FileUpload(
            filehandler=formish.filehandler.TempFileHandlerWeb(resource_root=resource_root, urlfactory=urlfactory), originalurl=originalurl,show_image_preview=True)



class TypeRegistry(FormishTypeRegistry):
    pass

            

def build_formish_form(definition, db, name):
    definition['fields'].insert(0, {'name': '_rev', 'widget':{'type': 'hidden'}})
    definition['fields'].insert(0, {'name': '_id', 'widget':{'type': 'hidden'}})
        
    return build(process_formishbuilder_form_definition( definition ), widgetRegistry=WidgetRegistry(db), typeRegistry=TypeRegistry())


def init_views(db, model_type, views):
    for name, view in views.items():
        log.debug('initialising view (model_type, name, view): (%s,%s,%s)'%(model_type,name,view))
        view = ViewDefinition(model_type, name, view)
        view.sync(db)


