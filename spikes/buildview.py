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


