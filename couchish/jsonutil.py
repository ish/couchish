from pollen import jsonutil
from formish import widgets

def file_to_dict(obj):
    return {'filename': obj.filename,'mimetype': obj.mimetype}

def file_from_dict(obj):
    return widgets.File(None, obj['filename'], obj['mimetype'])

jsonutil._system.register_type(widgets.File, file_to_dict, file_from_dict, "file")
jsonutil.decode_mapping['file'] = file_from_dict
jsonutil.encode_mapping[widgets.File] = ('file',file_to_dict)
