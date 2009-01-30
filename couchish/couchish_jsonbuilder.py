from sets import Set
from couchish.createview import getjs
from couchish.schemaish_jsonbuilder import strip_stars

from string import Template

def buildview(view):
    """
    function (doc) {
        if (doc.model_type == 'book'){
            for (var i1 in doc.metadata) {
            for (var i2 in doc.metadata[i1].authors) {
                emit(doc.metadata[i1].authors[i2]._ref, null);
            }
            }
        }
    }
    """

    main_template = Template( \
"""    function (doc) {
$body
    }""")

    if_template = Template( \
"""        if (doc.model_type == '$type'){
$body
        }
""")

    for_template = Template( \
"""            for (var i$n in doc$attr) {
$body
            }""")

    emit_template = Template( \
"""                emit(doc$attr._ref, null);""")

    out = ''
    for type, attrs in view.items():
        out_fors = ''
        for attr in attrs:
            templ_if = if_template.substitute({'type': type, 'body':'$body'})
            segments = attr.replace('.*','*').split('.')
            cleansegments = attr.replace('.*','').split('.')
            out_attr = ''
            templ_fors = '$body\n'
            for n,segment in enumerate(segments):
                if segment.endswith('*'):
                    out_loop_var = out_attr + '.%s'%cleansegments[n]
                    out_attr += '.%s[i%s]'%(cleansegments[n], n)
                    templ_for = for_template.substitute(n=n, attr=out_loop_var, body='$body')
                    templ_fors = Template(templ_fors).substitute(body=templ_for)
                else:
                    out_attr += '.%s'%cleansegments[n]
            out_emit = emit_template.substitute(attr=out_attr)
            out_fors += Template(templ_fors).substitute(body=out_emit)
        out += Template(templ_if).substitute(body=out_fors)
                                                          
                    
    return main_template.substitute(body=out)




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
    viewdef += '        emit(doc._id, %s )\n'%getjs(uses)
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
        views_by_viewname[view['name']] = {'url':view['url'], 'key': view.get('key','_id'), 'uses': view.get('uses')}
        if 'map' in view:
            views_by_viewname[view['name']]['map'] = view['map']
            views[view['url']] = view['map']


    parents = []
    field_to_view = {}
    for type, definition in models_definition.items():
        for field in definition['fields']:
            # some uses need to know whether the attr is composed of any sequences
            field['key'] = strip_stars(field['name'])
            
            # If we have any references, build the appropriate lookups
            if 'refersto' in field:
                refersto = field['refersto']
                view = views_by_viewname[refersto]
                uses = view['uses']
                # Build the reference views dynamically if not explicit
                if 'map' not in view:
                        map = build_refersto_view(uses)
                        view['map'] = map
                        views[view['url']] = map

                if field['type'].startswith('Sequence'):
                    fieldname = '%s.*'%field['name']
                else:
                    fieldname = field['name']

                if isinstance(uses, basestring):
                    views_by_uses.setdefault(view['url']+'-rev',{}).setdefault(type,[]).append( fieldname )
                    viewnames_by_attribute.setdefault(uses, Set()).add(refersto)
                    attributes_by_viewname.setdefault(refersto, {}).setdefault(type,Set()).add( fieldname.replace('.*','*') )
                else:
                    views_by_uses.setdefault(view['url']+'-rev',{}).setdefault(type,[]).append( fieldname )
                    attributes_by_viewname.setdefault(refersto, {}).setdefault(type,Set()).add( fieldname.replace('.*','*') )
                    for use in uses:
                        viewnames_by_attribute.setdefault(use, Set()).add(refersto)

            # Create any 'viewby' views
            if 'viewby' in field:
                if '*' in fieldname:
                    raise Exception('Can\'t generate viewby views on attributes in sequences')
                if field['viewby'] == True:
                    url = '%s/by_%s'%(type,fieldname)
                else:
                    url = field['viewby']
                views[url] = "function(doc) { if (doc.model_type=='%s') { emit(doc.%s,  null ); } }"%(type,field['name'])
        # Add the 'all' view
        views['%s/all'%type] = "function(doc) { if (doc.model_type == '%s') { emit(doc._id, null); } }"%type



    # Generate dynamic views for reference reverse lookups 
    for url, view in views_by_uses.items():
        views[url] = buildview(view)

    out = {'views': views,'views_by_viewname': views_by_viewname, 'viewnames_by_attribute': viewnames_by_attribute, 'attributes_by_viewname':attributes_by_viewname,'views_by_uses':views_by_uses}
    return out

