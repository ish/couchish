import os, logging

import yaml
from couchdb.design import ViewDefinition
    
import formishbuilderutil

log = logging.getLogger(__name__)

def setup_relationships(relationships, definition, name):
    for item in definition['fields']:
        if 'widget' in item and 'select-choice-couchdb' in item['widget']['type']:
            options_label = item['widget']['options']['label']
            options_reference = item['widget']['options']['reference']
            options_keys = item['widget']['options']['keys']
            options_datakeys = item['widget']['options']['datakeys']

            for key in options_keys:
                relationships.setdefault(options_reference,{}).setdefault(key,[]).append(
                            ( name, item['name'], '%s/all'%options_reference, options_datakeys)
                )
    log.debug('relationships: %s'%relationships)
    return relationships


def init_views(db, model_type, definition):
    views = definition.get('views',{})
    reference_fields = [f['name'] for f in definition['fields'] if f.get('widget',{'type':None}).get('type') == 'select-choice-couchdb']
    log.debug('reference fields: %s'%reference_fields)

    for field_name in reference_fields:
        name = 'by%s'%field_name 
        if name not in views:
            log.debug('automatically adding view: %s'%name)
            views[name] = "function(doc) { if (doc.model_type == '%s')  emit(doc.%s[0],doc._id) }"%(model_type, field_name)

    if 'all' not in views:
        log.debug('adding default "all" view')
        views['all'] = "function(doc) { if (doc.model_type == '%s')  emit(doc._id, doc) }"%model_type

    for name, view in views.items():
        view = ViewDefinition(model_type, name, views[name])
        view.sync(db)

def get_model(definition, db, name):
    def _():
        return  formishbuilderutil.build_formish_form(definition, db, name)
    return _


def build_model(db, model_dir):
    model = {}
    relationships = {}
    metadata = {}
    for file in os.listdir(model_dir):
        if not file.endswith('.yaml'):
            continue
        name = file.split('.')[0]
        definition = yaml.load(open('%s/%s'%(model_dir,file)))
        metadata[name] = definition.get('metadata',{})
        log.debug('name: %s'%name)
        log.debug('definition: %s'%definition)
        model[name] = get_model(definition, db, name)
        setup_relationships(relationships, definition, name) 
        init_views(db, name, definition)
    return model, relationships, metadata
