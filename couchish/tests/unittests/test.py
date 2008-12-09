import unittest
from couchdb.design import ViewDefinition
import couchdb
from couchish import couchish
import datetime
import magic
import schemaish


DATADIR = 'couchish/tests/unittests/data/%s'


def init_views(db, model_type, views):
    for name, view in views.items():
        view = ViewDefinition(model_type, name, view)
    view.sync(db)



class TestFileHandler():

    def get_path_for_file(self, filename):
        return filename

    def get_mimetype(self, filename):
        return magic.from_file(DATADIR%filename,mime=True)



class TestCase(unittest.TestCase):

    def setUp(self):
        self.dbname = 'test'
        self.server = couchdb.Server('http://localhost:5984')
        if self.dbname in self.server:
            del self.server[self.dbname]
        self.DB = self.server.create(self.dbname)
        self.db = couchish.CouchishDB(self.DB,filehandler=TestFileHandler())


class TestData(TestCase):


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
        
       

class TestSimpleRelationships(TestCase):

    relationships = {
        'author': {
            'name': [
                ('book', 'author', 'author/name'),
              ], 
        }
    }

    author_views= {
        'all': "function(doc) { if (doc.model_type == 'author')  emit(doc._id, doc) }",
        'name': "function(doc) { if (doc.model_type == 'author')  emit(doc._id, doc.name) }"
      }

    book_views = {
        'all': "function(doc) { if (doc.model_type == 'book')  emit(null, null) }",
        'byauthor': "function(doc) { if (doc.model_type == 'book')  emit(doc.author[0],doc._id) }",
      }


    def init_views(self, db, model_type, views):
        for name, view in views.items():
            view = ViewDefinition(model_type, name, view)
        view.sync(db)


    def setUp(self):
        TestCase.setUp(self)
        self.db = couchish.CouchishDB(self.DB,relationships=self.relationships,filehandler=TestFileHandler())
        self.init_views(self.DB, 'book', self.book_views)
        self.init_views(self.DB, 'author', self.author_views)


    def test_simpledata(self):
        author1 = {'name': 'Tim Parkin'}
        author1_id = self.db.create('author',author1)
        book1 = {'title': 'MyBookOne','author': [author1_id, author1['name']]}
        book1_id = self.db.create('book',book1)
        author2 = {'name': 'Matt Goodall'}
        author2_id = self.db.create('author',author2)
        book2 = {'title': 'MyBookTwo','author': [author2_id, author2['name']]}
        book2_id = self.db.create('book',book2)

        author1 = self.db.get(author1_id)
        author1['name'] = 'Denzil Washington'
        self.db.set('author',author1)
        book1 = self.db.get(book1_id)
        self.assertEquals(book1['author'], [author1_id, author1['name']])
        


class TestComplexRelationships(TestCase):

    leader_views= {
        'all': "function(doc) { if (doc.model_type == 'leader')  emit(doc._id, doc) }",
        'name': "function(doc) { if (doc.model_type == 'leader')  emit(doc._id, doc.surname+', '+doc.firstname) }"
      }

    tour_views = {
        'all': "function(doc) { if (doc.model_type == 'tour')  emit(null, null) }",
        'byleader': "function(doc) { if (doc.model_type == 'tour')  emit(doc.leader[0],doc._id) }",
      }
    relationships = {
        'leader': {
            'surname': [
                ('tour', 'leader', 'leader/name'),
            ],
            'firstname': [
                ('tour', 'leader', 'leader/name'),
            ]
        }
    }


    def init_views(self, db, model_type, views):
        for name, view in views.items():
            view = ViewDefinition(model_type, name, view)
        view.sync(db)


    def setUp(self):
        TestCase.setUp(self)
        self.db = couchish.CouchishDB(self.DB,relationships=self.relationships,filehandler=TestFileHandler())
        self.init_views(self.DB, 'leader', self.leader_views)
        self.init_views(self.DB, 'tour', self.tour_views)


    def test_complexjoin(self):
        leader1 = {'firstname': 'Tim', 'surname': 'Parkin'}
        leader1_id = self.db.create('leader',leader1)
        tour1 = {'title': 'MyTourOne','leader': [leader1_id, leader1['surname']+', '+leader1['firstname']]}
        tour1_id = self.db.create('tour',tour1)
        leader2 = {'firstname': 'Matt', 'surname': 'Goodall'}
        leader2_id = self.db.create('leader',leader2)
        tour2 = {'title': 'MyTourTwo','leader': [leader2_id, leader2['surname']+', '+leader2['firstname']]}
        tour2_id = self.db.create('tour',tour2)

        leader1 = self.db.get(leader1_id)
        leader1['surname'] = 'Washington'
        self.db.set('leader',leader1)
        tour1 = self.db.get(tour1_id)
        self.assertEquals(tour1['leader'], [leader1_id, leader1['surname']+', '+leader1['firstname']])
        


