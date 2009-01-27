from sets import Set


def build_refersto_view(uses):
    model_types = set()
    if isinstance(uses, basestring):
        model_type = uses.split('.')[0]
        uses = [uses]
    else:
        for use in uses:
            mt = use.split('.')[0]
            model_types.add(mt)
        if len(model_types) > 1:
            raise ValueError('Can only use one model type in "uses" at the moment')
        model_type = list(model_types)[0]
    viewdef = 'function (doc) {\n'
    viewdef += '    if (doc.model_type == \''+model_type+'\'){\n'
    viewdef += '        emit(doc._id, {'
    for use in uses:
        attr = '.'.join( use.split('.')[1:] )
        viewdef += 'doc.'+attr+', '
    viewdef += ' })\n'
    viewdef += '    }\n'
    viewdef += '}\n'
    return viewdef


def get_views(models_definition, views_definition):

    views = {} 
    views_by_viewname = {}
    views_by_uses = {} 
    viewnames_by_attribute = {} 
    attributes_by_viewname = {}

    for view in views_definition:
        if 'url' not in view:
            if 'designdoc' not in view:
                view['url'] = 'couchish/%s'%view['name']
            else:
                view['url'] = '%s/%s'%(view['designdoc'],view['name'])
        views_by_viewname[view['name']] = {'url':view['url'], 'map': view['map'], 'key': view.get('key','_id'), 'uses': view.get('uses')}
        if 'map' in view:
            views[view['url']] = view['map']


    field_to_view = {}
    for type, definition in models_definition.items():
        for field in definition['fields']:
            if 'refersto' in field:
                refersto = field['refersto']
                view = views_by_viewname[refersto]
                uses = view['uses']
                #if 'map' not in view:
                    #    map = build_refersto_view(uses)
                    #    view['map'] = map
                    #    views[view['url']] = map

                
                if isinstance(uses, basestring):
                    views_by_uses.setdefault(view['url']+'-rev',{}).setdefault(type,[]).append( field['name'] )
                    viewnames_by_attribute.setdefault(uses, Set()).add(refersto)
                    attributes_by_viewname.setdefault(refersto, {}).setdefault(type,Set()).add( field['name'] )
                else:
                    views_by_uses.setdefault(view['url']+'-rev',{}).setdefault(type,[]).append( field['name'] )
                    attributes_by_viewname.setdefault(refersto, {}).setdefault(type,Set()).add( field['name'] )
                    for use in uses:
                        viewnames_by_attribute.setdefault(use, Set()).add(refersto)
            if 'viewby' in field:
                if field['viewby'] == True:
                    url = '%s/by_%s'%(type,field['name'])
                else:
                    url = field['viewby']
                views[url] = "function(doc) { if (doc.model_type=='%s') { emit(doc.%s,  null ); } }"%(type,field['name'])
            views['%s/all'%type] = "function(doc) { if (doc.model_type == '%s')  emit(doc._id, null) }"%type




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

