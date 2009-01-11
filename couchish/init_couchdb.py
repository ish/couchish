import os, logging

import couchdb


log = logging.getLogger(__name__)

def get_couchdb(couchdb_name):
    uri = os.environ.get('COUCHDB_URI', 'http://localhost:5984/')
    server = couchdb.Server(uri)
    if couchdb_name not in server:
        server.create(couchdb_name)
    db = server[couchdb_name]
    log.debug('couchdbname: %s'%db)
    return db
