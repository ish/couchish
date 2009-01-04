import os, cgi
import logging as log
import copy

from pollen import jsonutil

import formish
from formish.dottedDict import dottedDict
from schemaish.type import File
from formish.filehandler import TempFileHandlerWeb

from couchdb import design
from couchdb.client import ResourceConflict
from datetime import datetime


def file_to_dict(obj):
    return {'filename': obj.filename,'mimetype': obj.mimetype}

def file_from_dict(obj):
    return File(None, obj['filename'], obj['mimetype'])

jsonutil.default_system.register_type(File, file_to_dict, file_from_dict, "file")
jsonutil.decode_mapping['file'] = file_from_dict
jsonutil.encode_mapping[File] = ('file',file_to_dict)

def get_files(data,filehandler, original=None):
    dd = dottedDict(data)
    ddoriginal = dottedDict(original)
    files = {}
    for k in dd.dottedkeys():
        if isinstance(dd[k],File):
            # if the file is blank
            if dd[k].file is None and dd[k].filename is None and dd[k].mimetype is None:
                # if we have no original then the result is None
                if original is None:
                    dd[k] = None
                # otherwise the result is unchanged
                else:
                    dd[k] = ddoriginal[k].data
            else:
                # remove the file data from document and add to files for attachment handling
                files[k] = dd[k]
                filename = dd[k].filename
                dd[k] = File(None,filename,filehandler.get_mimetype(filename))
    return dd.data, files

def add_id_and_attr_to_files(data,id):
    dd = dottedDict(data)
    for k in dd.dottedkeys():
        if isinstance(dd[k],File):
            dd[k].id = id
            dd[k].attr = k

    return dd.data


class CouchishDB(object):
    
    def __init__(self, db, relationships = {}, filehandler=TempFileHandlerWeb()):
        self.db = db
        self.relationships = relationships
        self.filehandler = filehandler
        
    def get_all(self, type):
        return [add_id_and_attr_to_files(jsonutil.decode_from_dict(item['value']),item['id']) for item in self.db.view('%s/all'%type)]

    def get(self, key):
        data = jsonutil.decode_from_dict(self.db[key])
        data = add_id_and_attr_to_files(data,key)
        return data


    def get_attachment(self, key, name):
        return self.db.get_attachment(key, name)


    def create(self, type, data):
        log.debug('creating document type %s with data %s'%(type, data))
        data['model_type'] = type
        data, files = get_files(data, self.filehandler)
        doc_id = self.db.create(jsonutil.encode_to_dict(dict(data)))
        if len(files.keys()) == 0:
            return doc_id
        doc = self.db[doc_id]
        log.debug('detected %s files: %s'%(len(files.keys()),files))
        for key, f in files.items():
            log.debug('(in create) Putting attachment %s for key %s'%(f.filename,key))
            log.debug('Putting attachment %s'%f.filename)
            self.db.put_attachment(doc, f.file.read(), key)
        return doc_id

    
    def set(self, type, data):
        doc_id = data['_id']
        D = self.db[doc_id]
        newD, files = get_files(data, self.filehandler, original=D)
        newD = jsonutil.encode_to_dict(newD)
        if D['_rev'] != data['_rev']:
            raise ResourceConflict('Revision mismatch - the document was changed before this save')
        oldD = copy.copy(D)
        D.update( newD )
        self.db[D['_id']] = D
        for key, f in files.items():
            log.debug('(in set) Deleting attachment %s for key %s'%(f.filename,key))
            self.db.delete_attachment(D, key)
            log.debug('(in set) Putting attachment %s for key %s'%(f.filename,key))
            self.db.put_attachment(D, f.file.read(), key)
        self.notify(D, oldD)
  

    def set_key(self, type, id, key, value):
        D = self.get(id)
        oldD = copy.copy(D)
        D[key] = value
        self.db[id] = D
        self.notify(D, oldD)
 

    def delete(self, id):
        del self.db[id]
      

    def view(self, view, **kw):
        return [jsonutil.decode_from_dict(item['value']) for item in self.db.view(view, **kw)]
 

    def notify(self, new, old=None):
        type = new['model_type']
        id = new['_id']
        changes = []
        # If this doc type does not have any relationships then return
        if type not in self.relationships:
            return 
        
        # Check each relationship to see if the the changed object will trigger something, if so collect them
        log.debug('notify is scanning changes: %s'%self.relationships[type].items())
        for key, rs in self.relationships[type].items():
            log.debug('checking key %s'%key)
            if old is None or old[key] != new[key]:
                log.debug('key %s data changed'%key)
                for r in rs:
                    doctype, dockey, docview, datakeys = r
                    changes.append( (type, id, doctype, dockey, docview, datakeys) )
                log.debug('adding changes %s'%changes)
                    
        # Process each trigger
        for type, id, doctype, dockey, docview, datakeys in changes:          
            data = self.view(docview, key=id)[0]
            newvalue = tuple( [data[k] for k in datakeys] )
            tochange = self.view('%s/by%s'%(doctype,dockey), key=id)
            log.debug('view %s/by%s returned %s'%(doctype,dockey, tochange))
            for item in tochange:
                log.debug('for type %s and item %s changing key %s to %s'%(doctype,item,dockey,(id,newvalue)))
                self.set_key(doctype,item,dockey,(id,newvalue))


class FileAccessor(object):
    """
    A skeleton class that should be implemented so that the files resource can
    build caches, etc
    """

    def __init__(self, db):
        self.db = db

    def get_mimetype(self, id):
        """
        Get the mime type of the file with this id
        """
        item_id, attribute = id.split('/')
        return self.db.get(item_id)[attribute].mimetype


    def get_mtime(self, id):
        item_id, attribute = id.split('/')
        return datetime( 2008,1,1 )


    def get_file(self, id):
        """
        Get the file object for this id
        """
        item_id, attribute = id.split('/')
        return self.db.get_attachment(item_id,attribute)




