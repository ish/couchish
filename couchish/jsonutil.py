from jsonish import pythonjson
from schemaish.type import File
from dottedish import dotted

class CouchishFile(File):

    def __init__(self, file, filename, mimetype, id=None, doc_id=None,inline=False):
        self.file = file
        self.filename = filename
        self.mimetype = mimetype
        self.id = id
        self.doc_id = doc_id
        self.inline = inline

    def __repr__(self):
        return '<couchish.jsonutil.CouchishFile file="%r" filename="%s", mimetype="%s", id="%s", doc_id="%s", inline="%s" >' % (self.file, self.filename, self.mimetype, self.id, getattr(self, 'doc_id'), self.inline)

def file_to_dict(obj):
    return {'__type__': 'file','filename': obj.filename,'mimetype': obj.mimetype, 'file': None, 'id': getattr(obj, 'id', None), 'doc_id': getattr(obj, 'doc_id', None)}


def file_from_dict(obj):
    filename = obj['filename']
    mimetype =  obj['mimetype']
    data = obj['file']
    id = obj.get('id')
    doc_id = obj.get('doc_id')
    return CouchishFile(data, filename, mimetype, id, doc_id)

pythonjson.json.register_type(File, file_to_dict, file_from_dict, "file")
pythonjson.json.register_type(CouchishFile, file_to_dict, file_from_dict, "file")
pythonjson.decode_mapping['file'] = file_from_dict
pythonjson.encode_mapping[File] = ('file',file_to_dict)
pythonjson.encode_mapping[CouchishFile] = ('file',file_to_dict)

encode_to_dict = pythonjson.encode_to_dict
decode_from_dict = pythonjson.decode_from_dict

def add_id_and_attr_to_files(data):
    if not isinstance(data, dict):
        return data
    dd = dotted(data)
    for k in dd.dottedkeys():
        if isinstance(dd[k],File):
            if '_id' in dd and '_rev' in dd:
                dd[k].doc_id = dd['_id']
                dd[k].rev = dd['_rev']
                return dd.data
            segments = k.split('.')
            for n in xrange(1,len(segments)):
                subpath = '.'.join(segments[:-n])
                if '_id' in dd[subpath] and '_rev' in dd[subpath]:
                    dd[k].doc_id = dd[subpath]['_id']
                    dd[k].rev = dd[subpath]['_rev']

    return dd.data


def wrapdumps(obj):
    obj = pythonjson.dumps(obj)
    return obj

def wraploads(obj):
    obj = pythonjson.loads(obj)
    obj = add_id_and_attr_to_files(obj)
    return obj



dumps = wrapdumps
loads = wraploads
