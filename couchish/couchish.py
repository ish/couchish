import os, cgi
import logging as log

from couchdb import design
from couchdb.client import ResourceConflict
from pollen import jsonutil
import formish
from formish.dottedDict import dottedDict
from formish import widgets

import copy

def get_files(data,filehandler):
    dd = dottedDict(data)
    files = dottedDict()
    for k in dd.dottedkeys():
        if isinstance(dd[k],widgets.File):
            files[k] = dd[k]
            filename = dd[k].filename
            dd[k] = widgets.File(None,filename,filehandler.get_mimetype(filename))
    return dd.data, files.data

def add_id_and_attr_to_files(data,id):
    dd = dottedDict(data)
    files = dottedDict()
    for k in dd.dottedkeys():
        if isinstance(dd[k],widgets.File):
            dd[k].id = id
            dd[k].attr = k

    return dd.data



class CouchishDB(object):
    
    def __init__(self, request):
        self.request = request
        self.db = request.environ['service.couchdb']
        self.relationships = request.environ['service.relationships']        
        
    def form(self, type):
        return self.request.environ['service.model_forms'][type]()
    
    def get_all(self, type):
        return [add_id_and_attr_to_files(jsonutil.decode_from_dict(item['value']),item['id']) for item in self.db.view('%s/all'%type)]

    def get(self, type, key):
        data = jsonutil.decode_from_dict(self.db[key])
        data = add_id_and_attr_to_files(data,key)
        return data

    def get_attachment(self, key, name):
        return self.db.get_attachment(key, name)

    def create(self, type, data,
               filehandler=formish.filehandler.TempFileHandler()):
        log.debug('creating document type %s with data %s'%(type, data))
        data['model_type'] = type
        data, files = get_files(data, filehandler)
        doc_id = self.db.create(jsonutil.encode_to_dict(dict(data)))
        if len(files.keys()) == 0:
            return
        doc = self.db[doc_id]
        log.debug('detected %s files: %s'%(len(files.keys()),files))
        for key, f in files.items():
            self.db.put_attachment(doc, f.file.read(), key)
        return doc_id


    
    def set(self, type, data, filehandler=formish.filehandler.TempFileHandler()):
        doc_id = data['_id']
        D = self.db[doc_id]
        newD, files = get_files(data, filehandler)
        newD = jsonutil.encode_to_dict(newD)
        if D['_rev'] != data['_rev']:
            raise ResourceConflict('Revision mismatch - the document was changed before this save')
        oldD = copy.copy(D)
        D.update( newD )
        self.db[D['_id']] = D
        for key, f in files.items():
            self.db.delete_attachment(D, key)
            self.db.put_attachment(D, f.file.read(), key)
        self.notify(type, oldD, D)
        
    def set_key(self, type, id, key, value):
        D = self.get(type, id)
        oldD = copy.copy(D)
        D[key] = value
        self.db[id] = D
        self.notify(type, oldD, D)
        
    def delete(self, id):
        del self.db[id]
      

    def view(self, view, **kw):
        return [jsonutil.decode_from_dict(item['value']) for item in self.db.view(view, **kw)]
        
    def notify(self, type, old, new):
        id = old['_id']
        changes = []
        # If this doc type does not have any relationships then return
        if type not in self.relationships:
            return 
        
        # Check each relationship to see if the the changed object will trigger something, if so collect them
        log.debug('notify is scanning changes: %s'%self.relationships[type].items())
        for key, rs in self.relationships[type].items():
	    log.debug('checking key %s'%key)
            if old[key] != new[key]:
	        log.debug('key %s data changed'%key)
                for r in rs:
                    doctype, dockey, docview = r
                    changes.append( (type, id, doctype, dockey, docview) )
		log.debug('adding changes %s'%changes)
                    
        # Process each trigger
        for type, id, doctype, dockey, docview in set(changes):          
            newvalue = self.view(docview, key=id)[0]
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
        return None



    def get_file(self, id):
        """
        Get the file object for this id
        """
        item_id, attribute = id.split('/')
        return self.db.get_attachment(item_id,attribute)
