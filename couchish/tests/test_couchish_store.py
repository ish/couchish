from __future__ import with_statement
import unittest
import os.path
import uuid
import couchdb
from couchish import config, errors, store
from copy import copy

def data_filename(filename):
    return os.path.join('couchish/tests/data', filename)

def type_filename(type,namespace=None):
    if namespace:
        namespace = '_%s'%namespace
    else:
        namespace = ''
    return data_filename('test_couchish%s_%s.yaml' % (namespace,type))

db_name = 'test-couchish'

def strip_id_rev(doc):
    couchdoc = dict(doc)
    couchdoc.pop('_id')
    couchdoc.pop('_rev')
    return couchdoc

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

        matt = strip_id_rev(self.db[matt_id])
        book = strip_id_rev(self.db[book_id])
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

        matt = strip_id_rev(self.db[matt_id])
        book = strip_id_rev(self.db[book_id])
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

        matt = strip_id_rev(self.db[matt_id])
        book = strip_id_rev(self.db[book_id])
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

        matt = strip_id_rev(self.db[matt_id])
        book = strip_id_rev(self.db[book_id])
        assert matt == {'model_type': 'author', 'first_name': 'Matt', 'last_name': 'Woodall'}
        assert book == {'model_type': 'book', 'title': 'Title', 'metadata': {
                            'writtenby': {'_ref': matt_id, 'first_name': 'Matt', 'last_name': 'Woodall'},
                            'coauthored': {'_ref': tim_id, 'last_name': 'Parkin'}}}


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

        matt = strip_id_rev(self.db[matt_id])
        book = strip_id_rev(self.db[book_id])
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

        matt = strip_id_rev(self.db[matt_id])
        book = strip_id_rev(self.db[book_id])
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

        matt = strip_id_rev(self.db[matt_id])
        book = strip_id_rev(self.db[book_id])
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

        matt = strip_id_rev(self.db[matt_id])
        book = strip_id_rev(self.db[book_id])
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

        matt = strip_id_rev(self.db[matt_id])
        book = strip_id_rev(self.db[book_id])
        assert matt == {'model_type': 'author', 'first_name': 'Matt', 'last_name': 'Woodall'}
        assert book == {'model_type': 'book', 'title': 'Title', 'people': [{'authors': [ {'nested': {'_ref': matt_id, 'first_name': 'Matt', 'last_name': 'Woodall'}}, {'nested': {'_ref': matt_id, 'first_name':'Matt','last_name': 'Woodall'}}]}]}



