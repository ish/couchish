from __future__ import with_statement
import os.path
import time
import unittest
import couchdb
from couchish import config, errors, store
from couchish.tests import util

def data_filename(filename, namespace=None):
    if namespace:
        return os.path.join('couchish/tests/data/%s'%namespace, filename)
    return os.path.join('couchish/tests/data', filename)

def type_filename(type,namespace=None):
    return data_filename('test_couchish_%s.yaml' % type, namespace)

db_name = 'test-couchish'

def strip_id_rev_meta(doc):
    couchdoc = dict(doc)
    couchdoc.pop('_id')
    couchdoc.pop('_rev')
    # Clean up the metadata.
    del couchdoc['metadata']['ctime']
    del couchdoc['metadata']['mtime']
    if not couchdoc['metadata']:
        del couchdoc['metadata']
    return couchdoc


class TestStore(util.TempDatabaseMixin, unittest.TestCase):

    def setUp(self):
        super(TestStore, self).setUp()
        self.store = store.CouchishStore(self.db, config.Config({}, {}))

    def test_session(self):
        S = self.store.session()
        doc_id = S.create({})
        S.flush()
        assert self.db.get(doc_id)

    def test_with_session(self):
        with self.store.session() as S:
            S.create({'_id': 'foo'})
        assert self.db.get('foo')

    def test_flush_again(self):
        doc_id = self.db.create({'model_type': 'foo'})
        S = self.store.session()
        doc = S.doc_by_id(doc_id)
        doc['num'] = 1
        S.flush()
        doc['num'] = 2
        S.flush()
        assert self.db.get(doc_id)['num'] == 2

    def test_with_session_exc(self):
        try:
            with self.store.session() as S:
                doc_id = S.create({'_id': 'foo'})
                bang
        except NameError:
            pass
        else:
            self.fail("Should have raised an exception")
        assert self.db.get('foo') is None


class TestMetadata(util.TempDatabaseMixin, unittest.TestCase):

    def setUp(self):
        super(TestMetadata, self).setUp()
        self.store = store.CouchishStore(self.db, config.Config({}, {}))

    def test_create(self):
        S = self.store.session()
        doc_id = S.create({})
        S.flush()
        doc = self.db.get(doc_id)
        assert doc['metadata']['ctime']
        assert doc['metadata']['mtime']
        assert doc['metadata']['ctime'] == doc['metadata']['mtime']

    def test_create2(self):
        S = self.store.session()
        doc1_id = S.create({})
        time.sleep(.5)
        doc2_id = S.create({})
        S.flush()
        doc1 = self.db.get(doc1_id)
        doc2 = self.db.get(doc2_id)
        assert doc1['metadata']['ctime'] == doc1['metadata']['ctime']

    def test_update(self):
        S = self.store.session()
        doc_id = S.create({'model_type': 'test'})
        S.flush()
        doc = S.doc_by_id(doc_id)
        doc['foo'] = ['bar']
        S.flush()
        doc = self.db.get(doc_id)
        assert doc['metadata']['ctime']
        assert doc['metadata']['mtime']
        assert doc['metadata']['mtime'] > doc['metadata']['ctime']

    def test_graceful_upgrade(self):
        doc_id = self.db.create({'model_type': 'foo'})
        S = self.store.session()
        doc = S.doc_by_id(doc_id)
        doc['foo'] = 'bar'
        S.flush()
        assert 'ctime' not in doc['metadata']
        assert doc['metadata']['mtime']

    def test_non_destructive(self):
        S = self.store.session()
        docid = S.create({'model_type': 'test', 'metadata': {'schema_version': '1.1'}})
        S.flush()
        doc = S.doc_by_id(docid)
        assert doc['metadata']['ctime']
        assert doc['metadata']['mtime']
        assert doc['metadata']['schema_version'] == '1.1'
        doc['foo'] = 'bar'
        S.flush()
        assert doc['metadata']['ctime']
        assert doc['metadata']['mtime']
        assert doc['metadata']['schema_version'] == '1.1'


class Test(unittest.TestCase):

    def setUp(self):
        server = couchdb.Server()
        if db_name in server:
            del server[db_name]
        self.db = server.create(db_name)
        self.S = store.CouchishStore(self.db, config.Config.from_yaml(
            dict((name,type_filename(name)) for name in ['book', 'author', 'post', 'dvd']),
            data_filename('test_couchish_views.yaml')
            ))
        self.S.sync_views()

    def test_make_refs(self):
        sess = self.S.session()
        matt = {'model_type': 'author', 'first_name': 'Matt', 'last_name': 'Goodall'}
        matt_id = sess.create(matt)
        tim = {'model_type': 'author', 'first_name': 'Tim', 'last_name': 'Parkin'}
        tim_id = sess.create(tim)
        sess.flush()
        refs = sess.make_refs('customdes/author_name', [matt_id, tim_id])
        assert refs == {matt_id: {'_ref': matt_id, 'first_name': 'Matt', 'last_name': 'Goodall'},
                        tim_id: {'_ref': tim_id, 'first_name': 'Tim', 'last_name': 'Parkin'}}
        ref = sess.make_ref('customdes/author_name', matt_id)
        assert ref == {'_ref': matt_id, 'first_name': 'Matt', 'last_name': 'Goodall'}

    def test_simple_reference(self):
        sess = self.S.session()
        matt = {'model_type': 'author', 'first_name': 'Matt', 'last_name': 'Goodall'}
        matt_id = sess.create(matt)
        tim = {'model_type': 'author', 'first_name': 'Tim', 'last_name': 'Parkin'}
        tim_id = sess.create(tim)
        book = {'model_type': 'book', 'title': 'Title',
                     'writtenby': {'_ref': matt_id, 'first_name': 'Matt', 'last_name': 'Goodall'},
                     'coauthored': {'_ref': tim_id, 'last_name': 'Parkin'}}
        book_id = sess.create(book)
        sess.flush()

        sess = self.S.session()
        matt = sess.doc_by_id(matt_id)
        matt['last_name'] = 'Woodall'
        sess.flush()

        matt = strip_id_rev_meta(self.db[matt_id])
        book = strip_id_rev_meta(self.db[book_id])
        assert matt == {'model_type': 'author', 'first_name': 'Matt', 'last_name': 'Woodall'}
        assert book == {'model_type': 'book', 'title': 'Title',
                            'writtenby': {'_ref': matt_id, 'first_name': 'Matt', 'last_name': 'Woodall'},
                            'coauthored': {'_ref': tim_id, 'last_name': 'Parkin'}}

    def test_simple_reference_addingdictionary(self):
        sess = self.S.session()
        matt = {'model_type': 'author', 'first_name': 'Matt', 'last_name': 'Goodall'}
        matt_id = sess.create(matt)
        tim = {'model_type': 'author', 'first_name': 'Tim', 'last_name': 'Parkin'}
        tim_id = sess.create(tim)
        book = {'model_type': 'book', 'title': 'Title',
                     'writtenby': {'_ref': matt_id, 'first_name': 'Matt', 'last_name': 'Goodall'},
                     'coauthored': {'_ref': tim_id, 'last_name': 'Parkin'}}
        book_id = sess.create(book)
        sess.flush()

        sess = self.S.session()
        matt = sess.doc_by_id(matt_id)
        matt['last_name'] = {'firstpart':'Woo','lastpart':'dall'}
        sess.flush()

        matt = strip_id_rev_meta(self.db[matt_id])
        book = strip_id_rev_meta(self.db[book_id])
        assert matt == {'model_type': 'author', 'first_name': 'Matt', 'last_name': {'firstpart':'Woo','lastpart':'dall'}}
        assert book == {'model_type': 'book', 'title': 'Title',
                 'writtenby': {'_ref': matt_id, 'first_name': 'Matt', 'last_name': {'firstpart':'Woo','lastpart':'dall'}},
                 'coauthored': {'_ref': tim_id, 'last_name': 'Parkin'}}

    def test_multiple_changes(self):
        sess = self.S.session()
        matt = {'model_type': 'author', 'first_name': 'Matt', 'last_name': 'Goodall'}
        matt_id = sess.create(matt)
        book = {'model_type': 'book', 'title': 'Title',
                     'writtenby': {'_ref': matt_id, 'first_name': 'Matt', 'last_name': 'Goodall'},
                     'coauthored': {'_ref': matt_id, 'last_name': 'Goodall'}}
        book_id = sess.create(book)
        sess.flush()

        sess = self.S.session()
        matt = sess.doc_by_id(matt_id)
        matt['last_name'] = 'Woodall'
        sess.flush()

        matt = strip_id_rev_meta(self.db[matt_id])
        book = strip_id_rev_meta(self.db[book_id])
        assert matt == {'model_type': 'author', 'first_name': 'Matt', 'last_name': 'Woodall'}
        assert book == {'model_type': 'book', 'title': 'Title',
                            'writtenby': {'_ref': matt_id, 'first_name': 'Matt', 'last_name': 'Woodall'},
                            'coauthored': {'_ref': matt_id, 'last_name': 'Woodall'}}

    def test_doc_by_id_not_found(self):
        sess = self.S.session()
        self.assertRaises(errors.NotFound, sess.doc_by_id, 'missing')


class TestDeep(unittest.TestCase):

    def setUp(self):
        server = couchdb.Server()
        if db_name in server:
            del server[db_name]
        self.db = server.create(db_name)
        self.S = store.CouchishStore(self.db, config.Config.from_yaml(
            dict((name,type_filename(name,'deepref')) for name in ['book', 'author']),
            type_filename('views','deepref')
            ))
        self.S.sync_views()

    def test_simple(self):
        sess = self.S.session()
        matt = {'model_type': 'author', 'first_name': 'Matt', 'last_name': 'Goodall'}
        matt_id = sess.create(matt)
        tim = {'model_type': 'author', 'first_name': 'Tim', 'last_name': 'Parkin'}
        tim_id = sess.create(tim)
        book = {'model_type': 'book', 'title': 'Title', 'metadata': {
                     'writtenby': {'_ref': matt_id, 'first_name': 'Matt', 'last_name': 'Goodall'},
                     'coauthored': {'_ref': tim_id, 'last_name': 'Parkin'}}}
        book_id = sess.create(book)
        sess.flush()

        sess = self.S.session()
        matt = sess.doc_by_id(matt_id)
        matt['last_name'] = 'Woodall'
        sess.flush()

        matt = strip_id_rev_meta(self.db[matt_id])
        book = strip_id_rev_meta(self.db[book_id])
        assert matt == {'model_type': 'author', 'first_name': 'Matt', 'last_name': 'Woodall'}
        assert book == {'model_type': 'book', 'title': 'Title', 'metadata': {
                            'writtenby': {'_ref': matt_id, 'first_name': 'Matt', 'last_name': 'Woodall'},
                            'coauthored': {'_ref': tim_id, 'last_name': 'Parkin'}}}


class TestDeep2(util.TempDatabaseMixin, unittest.TestCase):

    def test_missing_ref_container(self):
        """
        Check references inside non-existant containers.

        The flush hook drills into the document hunting for references but it
        should check that whatever a reference is inside actually exists first.
        """
        cfg = config.Config({
            'author': {'fields': [
                {'name': 'name'}
            ]},
            'book': {'fields': [
                {'name': 'title'},
                {'name': 'author', 'type': 'Reference()', 'refersto': 'test/author_summary'},
                {'name': 'authors', 'type': 'Sequence(Reference())', 'refersto': 'test/author_summary'},
            ]},
            },
            [{'name': 'author_summary', 'designdoc': 'test', 'uses': ['author.name']}])
        couchish_store = store.CouchishStore(self.db, cfg)
        couchish_store.sync_views()
        S = couchish_store.session()
        author_id = S.create({'model_type': 'author', 'name': 'Matt'})
        book_id = S.create({'model_type': 'book', 'title': 'My First Colouring Book',
                            'author': {'_ref': author_id, 'name': 'Matt'}})
        S.flush()
        # XXX Shouldn't need to do create a new session to make more changes.
        S = couchish_store.session()
        author = S.doc_by_id(author_id)
        author['name'] = 'Jessica'
        S.flush()


class TestRefsInSequences(unittest.TestCase):


    def setUp(self):
        server = couchdb.Server()
        if db_name in server:
            del server[db_name]
        self.db = server.create(db_name)
        self.S = store.CouchishStore(self.db, config.Config.from_yaml(
            dict((name,type_filename(name,'refinseq')) for name in ['book', 'author']),
            type_filename('views','refinseq')
            ))
        self.S.sync_views()

    def test_simple(self):
        sess = self.S.session()
        matt = {'model_type': 'author', 'first_name': 'Matt', 'last_name': 'Goodall'}
        matt_id = sess.create(matt)
        tim = {'model_type': 'author', 'first_name': 'Tim', 'last_name': 'Parkin'}
        tim_id = sess.create(tim)
        book = {'model_type': 'book', 'title': 'Title', 'authors':[ 
                     {'_ref': matt_id, 'first_name': 'Matt', 'last_name': 'Goodall'},
                     {'_ref': tim_id, 'last_name': 'Parkin'}]}
        book_id = sess.create(book)
        sess.flush()

        sess = self.S.session()
        matt = sess.doc_by_id(matt_id)
        matt['last_name'] = 'Woodall'
        sess.flush()

        matt = strip_id_rev_meta(self.db[matt_id])
        book = strip_id_rev_meta(self.db[book_id])
        assert matt == {'model_type': 'author', 'first_name': 'Matt', 'last_name': 'Woodall'}
        assert book == {'model_type': 'book', 'title': 'Title', 'authors': [ {'_ref': matt_id, 'first_name': 'Matt', 'last_name': 'Woodall'}, {'_ref': tim_id, 'last_name': 'Parkin'}]}


class TestNestedRefsInSequences(unittest.TestCase):


    def setUp(self):
        server = couchdb.Server()
        if db_name in server:
            del server[db_name]
        self.db = server.create(db_name)
        self.S = store.CouchishStore(self.db, config.Config.from_yaml(
            dict((name,type_filename(name,'nestedrefinseq')) for name in ['book', 'author']),
            type_filename('views','nestedrefinseq')
            ))
        self.S.sync_views()

    def test_simple(self):
        sess = self.S.session()
        matt = {'model_type': 'author', 'first_name': 'Matt', 'last_name': 'Goodall'}
        matt_id = sess.create(matt)
        tim = {'model_type': 'author', 'first_name': 'Tim', 'last_name': 'Parkin'}
        tim_id = sess.create(tim)
        book = {'model_type': 'book', 'title': 'Title', 'authors':[ 
                     {'nested': {'_ref': matt_id, 'first_name': 'Matt', 'last_name': 'Goodall'}},
                     {'nested': {'_ref': tim_id, 'last_name': 'Parkin'}}]}
        book_id = sess.create(book)
        sess.flush()

        sess = self.S.session()
        matt = sess.doc_by_id(matt_id)
        matt['last_name'] = 'Woodall'
        sess.flush()

        matt = strip_id_rev_meta(self.db[matt_id])
        book = strip_id_rev_meta(self.db[book_id])
        assert matt == {'model_type': 'author', 'first_name': 'Matt', 'last_name': 'Woodall'}
        assert book == {'model_type': 'book', 'title': 'Title', 'authors': [ {'nested': {'_ref': matt_id, 'first_name': 'Matt', 'last_name': 'Woodall'}}, {'nested': {'_ref': tim_id, 'last_name': 'Parkin'}}]}

    def test_twoentries(self):
        sess = self.S.session()
        matt = {'model_type': 'author', 'first_name': 'Matt', 'last_name': 'Goodall'}
        matt_id = sess.create(matt)
        book = {'model_type': 'book', 'title': 'Title', 'authors':[ 
                     {'nested': {'_ref': matt_id, 'first_name': 'Matt', 'last_name': 'Goodall'}},
                     {'nested': {'_ref': matt_id, 'first_name': 'Matt', 'last_name': 'Goodall'}}]}
        book_id = sess.create(book)
        sess.flush()

        sess = self.S.session()
        matt = sess.doc_by_id(matt_id)
        matt['last_name'] = 'Woodall'
        sess.flush()

        matt = strip_id_rev_meta(self.db[matt_id])
        book = strip_id_rev_meta(self.db[book_id])
        assert matt == {'model_type': 'author', 'first_name': 'Matt', 'last_name': 'Woodall'}
        assert book == {'model_type': 'book', 'title': 'Title', 'authors': [ {'nested': {'_ref': matt_id, 'first_name': 'Matt', 'last_name': 'Woodall'}}, {'nested': {'_ref': matt_id, 'first_name': 'Matt', 'last_name': 'Woodall'}}]}

class TestNestedRefsInNestedSequences(unittest.TestCase):


    def setUp(self):
        server = couchdb.Server()
        if db_name in server:
            del server[db_name]
        self.db = server.create(db_name)
        self.S = store.CouchishStore(self.db, config.Config.from_yaml(
            dict((name,type_filename(name,'nestedrefinnestedseq')) for name in ['book', 'author']),
            type_filename('views','nestedrefinnestedseq')
            ))
        self.S.sync_views()

    def test_simple(self):
        sess = self.S.session()
        matt = {'model_type': 'author', 'first_name': 'Matt', 'last_name': 'Goodall'}
        matt_id = sess.create(matt)
        tim = {'model_type': 'author', 'first_name': 'Tim', 'last_name': 'Parkin'}
        tim_id = sess.create(tim)
        book = {'model_type': 'book', 'title': 'Title', 'people':[ {'authors':[ 
                     {'nested': {'_ref': matt_id, 'first_name': 'Matt', 'last_name': 'Goodall'}},
                     {'nested': {'_ref': tim_id, 'last_name': 'Parkin'}}]}]}
        book_id = sess.create(book)
        sess.flush()

        sess = self.S.session()
        matt = sess.doc_by_id(matt_id)
        matt['last_name'] = 'Woodall'
        sess.flush()

        matt = strip_id_rev_meta(self.db[matt_id])
        book = strip_id_rev_meta(self.db[book_id])
        assert matt == {'model_type': 'author', 'first_name': 'Matt', 'last_name': 'Woodall'}
        assert book == {'model_type': 'book', 'title': 'Title', 'people': [{'authors': [ {'nested': {'_ref': matt_id, 'first_name': 'Matt', 'last_name': 'Woodall'}}, {'nested': {'_ref': tim_id, 'last_name': 'Parkin'}}]}]}

    def test_twoentries(self):
        sess = self.S.session()
        matt = {'model_type': 'author', 'first_name': 'Matt', 'last_name': 'Goodall'}
        matt_id = sess.create(matt)
        book = {'model_type': 'book', 'title': 'Title', 'people':[ {'authors':[ 
                     {'nested': {'_ref': matt_id, 'first_name': 'Matt', 'last_name': 'Goodall'}},
                     {'nested': {'_ref': matt_id, 'first_name': 'Matt','last_name': 'Goodall'}}]}]}
        book_id = sess.create(book)
        sess.flush()

        sess = self.S.session()
        matt = sess.doc_by_id(matt_id)
        matt['last_name'] = 'Woodall'
        sess.flush()

        matt = strip_id_rev_meta(self.db[matt_id])
        book = strip_id_rev_meta(self.db[book_id])
        assert matt == {'model_type': 'author', 'first_name': 'Matt', 'last_name': 'Woodall'}
        assert book == {'model_type': 'book', 'title': 'Title', 'people': [{'authors': [ {'nested': {'_ref': matt_id, 'first_name': 'Matt', 'last_name': 'Woodall'}}, {'nested': {'_ref': matt_id, 'first_name':'Matt','last_name': 'Woodall'}}]}]}


class TestMissingKeys(util.TempDatabaseMixin, unittest.TestCase):

    def setUp(self):
        super(TestMissingKeys, self).setUp()
        couchish_store = store.CouchishStore(self.db, config.Config({}, {}))
        couchish_store.sync_views()
        self.session = couchish_store.session()
        for i in range(5):
            self.session.create({'_id': str(i)})
        self.session.flush()

    def test_docs_by_id(self):
        docs = list(self.session.docs_by_id(['3', '4', '5']))
        assert docs[-1] is None

    def test_docs_by_view(self):
        docs = list(self.session.docs_by_view('_all_docs', keys=['3', '4', '5']))
        assert docs[-1] is None

    def test_docs_by_id_filtered(self):
        docs = list(self.session.docs_by_id(['3', '4', '5'], remove_rows_with_missing_doc=True))
        assert len(docs) == 2
        assert None not in docs

    def test_docs_by_view_filtered(self):
        docs = list(self.session.docs_by_view('_all_docs', keys=['3', '4', '5'], remove_rows_with_missing_doc=True))
        assert len(docs) == 2
        assert None not in docs

