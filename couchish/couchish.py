import os

from couchdb import design
from couchdb.client import ResourceConflict
from pollen import jsonutil

import copy

class CouchishDB(object):
    
    def __init__(self, request):
        self.request = request
        self.db = request.environ['service.couchdb']
        self.relationships = request.environ['service.relationships']        
        
    def form(self, type):
        return self.request.environ['service.model_forms'][type]()
    
    def get_all(self, type):
        return [jsonutil.decode_from_dict(item['value']) for item in self.db.view('%s/all'%type)]

    def get(self, type, key):
        return self.db[key]

    def create(self, type, data):
        data['model_type'] = type
        return self.db.create(jsonutil.encode_to_dict(dict(data)))
    
    def set(self, type, data):
        D = self.db[data['_id']]
        newD = jsonutil.encode_to_dict(dict(data))
        if D['_rev'] != data['_rev']:
            raise ResourceConflict('Revision mismatch - the document was changed before this save')
        oldD = copy.copy(D)
        D.update( newD )
        self.db[D['_id']] = D
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
        for key, rs in self.relationships[type].items():
            if old[key] != new[key]:
                for r in rs:
                    doctype, dockey, docview = r
                    changes.append( (type, id, doctype, dockey, docview) )
                    
        # Process each trigger
        for c in set(changes):          
            newvalue = self.view(docview, key=id)[0]
            tochange = self.view('%s/by%s'%(doctype,dockey), key=id)
            for item in tochange:
                self.set_key(doctype,item,dockey,(id,newvalue))

