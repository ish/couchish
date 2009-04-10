from jsonish import pythonjson
from schemaish.type import File
import base64
from dottedish import dotted

class CouchishFile(File):

    def __init__(self, file, filename, mimetype, id=None, doc_id=None, inline=False, b64=False, metadata=None):
        self.file = file
        self.filename = filename
        self.mimetype = mimetype
        self.id = id
        self.doc_id = doc_id
        self.inline = inline
        self.b64 = b64
        if metadata is None:
            metadata = {}
        self.metadata = metadata

    def __repr__(self):
        return '<couchish.jsonutil.CouchishFile file="%r" filename="%s", mimetype="%s", id="%s", doc_id="%s", inline="%s", b64="%s", metadata="%r" >' % (getattr(self,'file',None), self.filename, self.mimetype, self.id, getattr(self, 'doc_id',None), getattr(self,'inline',None), getattr(self,'b64', None), getattr(self, 'metadata', {}))


def file_to_dict(obj):
    d = {
        '__type__': 'file',
        'filename': obj.filename,
        'mimetype': obj.mimetype,
        'id': getattr(obj, 'id', None),
        }
    if hasattr(obj, 'metadata') and obj.metadata:
        d['metadata'] = obj.metadata
    if hasattr(obj,'doc_id') and obj.doc_id is not None:
        d['doc_id'] = obj.doc_id
    if hasattr(obj, 'inline') and obj.inline is not False:
        d['inline'] = obj.inline
    if hasattr(obj,'file') and hasattr(obj,'b64'):
        d['base64'] = obj.file
    else:
        if hasattr(obj,'file') and obj.file is not None:
            d['base64'] = base64.encodestring(obj.file.read())
    return d


def file_from_dict(obj):
    filename = obj['filename']
    mimetype =  obj['mimetype']
    inline = obj.get('inline', False)
    id = obj.get('id')
    doc_id = obj.get('doc_id')
    metadata = obj.get('metadata',{})
    if 'base64' in obj:
        data = obj['base64']
        return CouchishFile(data, filename, mimetype, id=id, doc_id=doc_id, inline=inline, b64=True, metadata=metadata)
    elif 'file' in obj:
        data = obj['file']
        return CouchishFile(data, filename, mimetype, id=id, doc_id=doc_id, inline=inline, metadata=metadata)
    else:
        return CouchishFile(None, filename, mimetype, id=id, doc_id=doc_id, metadata=metadata)


pythonjson.json.register_type(File, file_to_dict, file_from_dict, "file")
pythonjson.json.register_type(CouchishFile, file_to_dict, file_from_dict, "file")
pythonjson.decode_mapping['file'] = file_from_dict
pythonjson.encode_mapping[File] = ('file',file_to_dict)
pythonjson.encode_mapping[CouchishFile] = ('file',file_to_dict)


def wrap_encode_to_dict(obj):
    return pythonjson.encode_to_dict(obj)

def wrap_decode_from_dict(d):
    obj = pythonjson.decode_from_dict(d)
    obj = add_id_and_attr_to_files(obj)
    return obj


encode_to_dict = wrap_encode_to_dict
decode_from_dict = wrap_decode_from_dict

def add_id_and_attr_to_files(data):
    if not isinstance(data, dict):
        return data
    dd = dotted(data)
    for k in dd.dottedkeys():
        if isinstance(dd[k],File):
            if '_id' in dd and '_rev' in dd:
                dd[k].doc_id = dd['_id']
                dd[k].rev = dd['_rev']
            segments = k.split('.')
            for n in xrange(1,len(segments)):
                subpath = '.'.join(segments[:-n])
                if '_id' in dd[subpath] and '_rev' in dd[subpath]:
                    dd[k].doc_id = dd[subpath]['_id']
                    dd[k].rev = dd[subpath]['_rev']

    data = dd.data
    return data

dumps = pythonjson.dumps
loads = pythonjson.loads
