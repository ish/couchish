from pollen import jsonutil
from schemaish.type import File
from dottedish import dotted

class CouchishFile(File):

    def __init__(self, file, filename, mimetype, id=None, inline=True):
        self.file = file
        self.filename = filename
        self.mimetype = mimetype
        self.id = id
        self.inline = inline

    def __repr__(self):
        return '<couchish.jsonutil.CouchishFile file="%r" filename="%s", mimetype="%s", id="%s", inline="%s" >'%(self.file, self.filename, self.mimetype, self.id, self.inline)

def file_to_dict(obj):
    return {'__type__': 'file','filename': obj.filename,'mimetype': obj.mimetype, 'file':None,'id':getattr(obj,'id',None)}


def file_from_dict(obj):
    filename = obj['filename']
    mimetype =  obj['mimetype']
    data = obj['file']
    id = obj.get('id')
    return CouchishFile(data, filename, mimetype, id)

jsonutil.default_system.register_type(File, file_to_dict, file_from_dict, "file")
jsonutil.default_system.register_type(CouchishFile, file_to_dict, file_from_dict, "file")
jsonutil.decode_mapping['file'] = file_from_dict
jsonutil.encode_mapping[File] = ('file',file_to_dict)
jsonutil.encode_mapping[CouchishFile] = ('file',file_to_dict)

encode_to_dict = jsonutil.encode_to_dict
decode_from_dict = jsonutil.decode_from_dict

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
    obj = jsonutil.dumps(obj)
    return obj

def wraploads(obj):
    obj = jsonutil.loads(obj)
    obj = add_id_and_attr_to_files(obj)
    return obj



dumps = wrapdumps
loads = wraploads
