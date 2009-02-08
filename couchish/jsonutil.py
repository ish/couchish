from pollen.jsonutil import *
from schemaish.type import File as SchemaishFile
from couchish.type import File as CouchishFile

def couchishfile_to_dict(obj):
    return {'filename': obj.filename,'mimetype': obj.mimetype, 'id': obj.id}

def schemaishfile_to_dict(obj):
    return {'filename': obj.filename,'mimetype': obj.mimetype}

def couchishfile_from_dict(obj):
    if id in obj:
        return CouchishFile(None, obj['filename'], obj['mimetype'], obj['id'])
    else:
        return SchemaishFile(None, obj['filename'], obj['mimetype'])

default_system.register_type(File, file_to_dict, file_from_dict, "file")
decode_mapping['file'] = file_from_dict
encode_mapping[SchemaishFile] = ('file',couchishfile_to_dict)
encode_mapping[CouchishFile] = ('file',schemaishfile_to_dict)

