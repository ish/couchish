from pollen.jsonutil import *
from formish import widgets

def file_to_dict(obj):
    return {'filename': obj.filename,'mimetype': obj.mimetype}

def file_from_dict(obj):
    return widgets.File(None, obj['filename'], obj['mimetype'])

default_system.register_type(widgets.File, file_to_dict, file_from_dict, "file")
decode_mapping['file'] = file_from_dict
encode_mapping[widgets.File] = ('file',file_to_dict)

