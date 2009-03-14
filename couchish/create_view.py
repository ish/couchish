import simplejson as json

def setitem(v, k):
    n, key, value = k
    if n == 1:
        v[key] = value
        return
    try:
        return v[key]
    except KeyError:
        v[key] = {}
        return v[key]

def _set(data,path,value):
    segments = path.split('.')
    s = [(len(segments)-n, v, value) for n, v in enumerate(segments)]
    return reduce(setitem, s , data)

def getjs(uses):
    data = {}
    for use in uses:
        attr = '.'.join( use.split('.')[1:] )
        model_type = use.split('.')[0]
        _set(data, '%s|%s'%(model_type,attr), '#%s#'%use)

    js = json.dumps(data)
    for use in uses:
        attr = '.'.join( use.split('.')[1:] )
        model_type = use.split('.')[0]
        target = '\"#%s#\"'%use
        replacement = 'doc.%s'%attr
        js = js.replace(target, replacement)
        target = '\"%s|%s\"'%(model_type,attr)
        if '.' in target:
            target = '%s"'%target.split('.')[0]
        replacement = attr
        if '.' in replacement:
            replacement = replacement.split('.')[0]
        js = js.replace(target, replacement)
        target = '\"#%s#\"'%use
    return js


if __name__ == '__main__':
    uses =[ 'author.first_name', 'author.last_name', 'author.address.city','author.address.postcode','author.address.street.street2']
    js = getjs(uses)
    print js
