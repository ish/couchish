from pollen.jsonutil import *
from schemaish.type import File

def file_to_dict(obj):
    return {'filename': obj.filename,'mimetype': obj.mimetype}

def file_from_dict(obj):
    return File(None, obj['filename'], obj['mimetype'])

default_system.register_type(File, file_to_dict, file_from_dict, "file")
decode_mapping['file'] = file_from_dict
encode_mapping[File] = ('file',file_to_dict)

