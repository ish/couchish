import os.path
import uuid
import couchdb
from couchish import config, store

def data_filename(filename):
    return os.path.join('couchish/tests/data', filename)

def type_filename(type):
    return data_filename('test_couchish_%s.yaml' % (type,))

db_name = 'couchish'
#db_name = 't%s' % (str(uuid.uuid4()),)
print "db_name:", db_name

db = couchdb.Server()[db_name]
S = store.CouchishStore(db, config.Config.from_yaml(
    dict((name,type_filename(name)) for name in ['book', 'author', 'post', 'dvd']),
    data_filename('test_couchish_views.yaml')
    ))
S.sync_views()

sess = S.session()
matt_id = sess.create({'model_type': 'author', 'first_name': 'Matt', 'last_name': 'Goodall'})
tim_id = sess.create({'model_type': 'author', 'first_name': 'Tim', 'last_name': 'Parkin'})
sess.create({'model_type': 'book', 'title': 'Title',
             'writtenby': {'_ref': matt_id, 'first_name': 'Matt', 'last_name': 'Goodall'},
             'coauthored': {'_ref': tim_id, 'last_name': 'Parkin'}})
sess.flush()

sess = S.session()
matt = sess.doc_by_id(matt_id)
matt['last_name'] = 'Woodall'
sess.flush()

