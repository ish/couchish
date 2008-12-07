import unittest
import couchdb
from couchish import couchish
import datetime
import magic
import schemaish


DATADIR = 'couchish/tests/unittests/data/%s'
relationships = {
    'leader': {
        'surname': [
            ('tour', 'leader', 'leader/name'),
            ('tour', 'assistant', 'leader/name')
          ], 
        'firstname': [
            ('tour', 'leader', 'leader/name'),
            ('tour', 'assistant', 'leader/name')
        ]
    }
}

leader_views= {
    'all': "function(doc) { if (doc.model_type == 'leader')  emit(doc._id, doc) }",
    'name': "function(doc) { if (doc.model_type == 'leader')  emit(doc._id, doc.surname+', '+doc.firstname) }"
  }

tour_views = {
    'all': "function(doc) { if (doc.model_type == 'tour')  emit(null, null) }",
    'byleader': "function(doc) { if (doc.model_type == 'tour')  emit(doc.leader[0],doc._id) }",
    'byassistant': "function(doc) { if (doc.model_type == 'tour')  emit(doc.assistant[0],doc._id) }"
  }

def init_views(db, model_type, views):
    for name, view in views.items():
        view = ViewDefinition(model_type, name, view)
    view.sync(db)

class TestFileHandler():

    def get_path_for_file(self, filename):
        return filename

    def get_mimetype(self, filename):
        return magic.from_file(DATADIR%filename,mime=True)

class TestCouchish(unittest.TestCase):

    def setUp(self):
        dbname = 'test'
        server = couchdb.Server('http://localhost:5984')
        del server[dbname]
        db = server.create(dbname)
        self.db = couchish.CouchishDB(db,filehandler=TestFileHandler())

    def test_simpledata(self):
        data = {'string': 'hello', 'integer': 7, 'float': 12.5}
        doc_id = self.db.create('simple', data)
        out = self.db.get(doc_id)
        del out['_id']
        del out['_rev']
        self.assertEquals(data, out)
        
        
    def test_nesteddict(self):
        data = {'string': 'hello', 'integer': 7, 'float': 12.5, 'sub': {'string': 'hello', 'integer': 7, 'float': 12.5 }}
        doc_id = self.db.create('nesteddict', data)
        out = self.db.get(doc_id)
        del out['_id']
        del out['_rev']
        self.assertEquals(data, out)
        
        
    def test_nestedcomplex(self):
        data = {'list': [1,2,3,4,'5',6,], 'string': 'hello', 'integer': 7, 'float': 12.5, 'sub': {'string': 'hello', 'integer': 7, 'float': 12.5 }, 'listlist': [[1,2],[3,4]]}
        doc_id = self.db.create('nestedcomplex', data)
        out = self.db.get(doc_id)
        del out['_id']
        del out['_rev']
        self.assertEquals(data, out)

    def test_datetime(self):
        data = {'date': datetime.date(2008,12,18)}
        doc_id = self.db.create('date', data)
        out = self.db.get(doc_id)
        del out['_id']
        del out['_rev']
        self.assertEquals(data, out)
        
    def test_file(self):
        myfile = schemaish.type.File(open(DATADIR%'test.jpg'),'test.jpg',magic.from_file(DATADIR%'test.jpg'))
        data = {'file': myfile}
        doc_id = self.db.create('myfile', data,)
        out = self.db.get(doc_id)
        f = self.db.get_attachment(doc_id,'file')
        self.assertEquals(data['file'].filename, out['file'].filename)
        self.assertEquals(data['file'].mimetype, out['file'].mimetype)
        self.assertEquals(open(DATADIR%'test.jpg').read(), f)

    def test_alterdoc(self):
        data = {'string': 'hello', 'integer': 7, 'float': 12.5}
        doc_id = self.db.create('simple', data)
        out = self.db.get(doc_id)
        del out['_id']
        del out['_rev']
        self.assertEquals(data, out)
        out = self.db.get(doc_id)
        out['string'] = 'goodbye'
        out['integer'] = 42
        self.db.set(doc_id, out)
        changed_out = self.db.get(doc_id)
        del changed_out['_rev']
        del out['_rev']
        self.assertEquals(changed_out, out)

    def test_deletedoc(self):
        data = {'string': 'hello', 'integer': 7, 'float': 12.5}
        doc_id = self.db.create('simple', data)
        out = self.db.get(doc_id)
        del out['_id']
        del out['_rev']
        self.assertEquals(data, out)
        self.db.delete(doc_id)
        self.assertRaises(couchdb.ResourceNotFound,self.db.get,doc_id)

    def test_alterfile(self):
        myfile = schemaish.type.File(open(DATADIR%'test.jpg'),'test.jpg',magic.from_file(DATADIR%'test.jpg'))
        data = {'file': myfile}
        doc_id = self.db.create('myfile', data,)
        out = self.db.get(doc_id)
        f = self.db.get_attachment(doc_id,'file')
        self.assertEquals(data['file'].filename, out['file'].filename)
        self.assertEquals(data['file'].mimetype, out['file'].mimetype)
        self.assertEquals(open(DATADIR%'test.jpg').read(), f)
        mynewfile = schemaish.type.File(open(DATADIR%'photo.png'),'photo.png',magic.from_file(DATADIR%'photo.png'))
        out['file'] = mynewfile
        self.db.set('myfile',out)
        changed_out = self.db.get(doc_id)
        f = self.db.get_attachment(doc_id,'file')
        del changed_out['_rev']
        del out['_rev']
        self.assertEquals(out['file'].filename, changed_out['file'].filename)
        self.assertEquals(out['file'].mimetype, changed_out['file'].mimetype)
        self.assertEquals(open(DATADIR%'photo.png').read(), f)
        
       

        
        
        
        
