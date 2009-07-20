from __future__ import with_statement
import unittest
import os.path
import couchdb
from couchish import config, store
from schemaish.type import File
from couchish import jsonutil

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


def matches_supplied(test, supplied):
    test = dict((key, value) for (key, value) in test.iteritems() if key in supplied)
    return test == supplied


class TestFiles(unittest.TestCase):

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


    def test_addition_file(self):
        # create a file
        fh = open('couchish/tests/data/files/test.txt','r')
        f = jsonutil.CouchishFile(fh, 'test.txt','text/plain')
        
        matt = {'model_type': 'author', 'first_name': 'Matt', 'last_name': 'Goodall','photo': f}
        with self.S.session() as S:
            matt_id = S.create(matt)
        fh.close()

        # check the attachment
        first_created_photo_id = matt['photo'].id
        sess = self.S.session()
        attachment = sess.session._db.get_attachment(matt_id, first_created_photo_id)
        assert attachment == 'this is a test for the file attachment processing test in test_couchish_store\n'
        assert hasattr(matt['photo'],'id')

        # get the doc back out using couchish and check it's OK
        with self.S.session() as S:
            matt = S.doc_by_id(matt_id)
        assert len(matt['_attachments']) == 1
        assert matches_supplied(matt['_attachments'][matt['photo'].id], {'stub': True, 'length': 78, 'content_type': 'text/plain'})


    def test_change_file(self):

        # create a file
        fh = open('couchish/tests/data/files/test.txt','r')
        f = jsonutil.CouchishFile(fh, 'test.txt','text/plain')
        matt = {'model_type': 'author', 'first_name': 'Matt', 'last_name': 'Goodall','photo': f}
        with self.S.session() as S:
            matt_id = S.create(matt)
        fh.close()

        # check the attachment
        first_created_photo_id = matt['photo'].id
        sess = self.S.session()
        attachment = sess.session._db.get_attachment(matt_id, first_created_photo_id)
        assert attachment == 'this is a test for the file attachment processing test in test_couchish_store\n'
        assert hasattr(matt['photo'],'id')

        # get the doc back out using couchish and check it's OK
        with self.S.session() as S:
            matt = S.doc_by_id(matt_id)
        assert len(matt['_attachments']) == 1
        assert matches_supplied(matt['_attachments'][matt['photo'].id], {'stub': True, 'length': 78, 'content_type': 'text/plain'})

        # now lets replace the file
        fh = open('couchish/tests/data/files/test-changed.txt','r')
        f = jsonutil.CouchishFile(fh, 'test-changed.txt','text/plain')
        matt = {'model_type': 'author', 'first_name': 'Matt', 'last_name': 'Goodall','photo': f}
        with self.S.session() as S:
            matt = S.doc_by_id(matt_id)
            matt['photo'] = f
        fh.close()
        new_photo_id = matt.__subject__['photo'].id

        sess = self.S.session()
        attachment = 'foo'
        attachment = sess.session._db.get_attachment(matt_id,new_photo_id)
        assert attachment == 'and now it\'s changed\n'
        assert new_photo_id == first_created_photo_id
        
        with self.S.session() as S:
            matt = S.doc_by_id(matt_id)
        assert len(matt['_attachments']) == 1
        assert matches_supplied(matt['_attachments'][matt['photo'].id], {'stub': True, 'length': 21, 'content_type': 'text/plain'})


    def test_remove_file(self):

        # create a file
        fh = open('couchish/tests/data/files/test.txt','r')
        f = File(fh, 'test.txt','text/plain')
        matt = {'model_type': 'author', 'first_name': 'Matt', 'last_name': 'Goodall','photo': f}
        with self.S.session() as S:
            matt_id = S.create(matt)
        fh.close()

        # check the attachment
        first_created_photo_id = matt['photo'].id
        sess = self.S.session()
        attachment = sess.session._db.get_attachment(matt_id, first_created_photo_id)
        assert attachment == 'this is a test for the file attachment processing test in test_couchish_store\n'
        assert hasattr(matt['photo'],'id')

        # get the doc back out using couchish and check it's OK
        with self.S.session() as S:
            matt = S.doc_by_id(matt_id)
        assert len(matt['_attachments']) == 1
        assert matches_supplied(matt['_attachments'][matt['photo'].id], {'stub': True, 'length': 78, 'content_type': 'text/plain'})

        with self.S.session() as S:
            matt = S.doc_by_id(matt_id)
            matt['photo'] = None

        with self.S.session() as S:
            matt = S.doc_by_id(matt_id)
        assert not '_attachments' in matt
        assert matt['photo'] == None

    def test_moving_in_sequence(self):

        # create a file
        fh = open('couchish/tests/data/files/test.txt','r')
        f = File(fh, 'test.txt','text/plain')
        matt = {'model_type': 'book', 'first_name': 'Matt', 'last_name': 'Goodall','photo':[ f ]}
        with self.S.session() as S:
            matt_id = S.create(matt)
        fh.close()

        # check the attachment
        first_created_photo_id = matt['photo'][0].id
        sess = self.S.session()
        attachment = sess.session._db.get_attachment(matt_id, first_created_photo_id)
        assert attachment == 'this is a test for the file attachment processing test in test_couchish_store\n'
        assert  hasattr(matt['photo'][0],'id')
    
        fh2 = open('couchish/tests/data/files/test-changed.txt','r')
        f2 = File(fh2, 'test2.txt','text/plain')
        with self.S.session() as S:
            matt = S.doc_by_id(matt_id)
            matt['photo'].append( f2  )
        fh2.close()


        with self.S.session() as S:
            matt = S.doc_by_id(matt_id)
        assert matches_supplied(matt['_attachments'][ matt['photo'][0].id ], {'stub': True, 'length': 78, 'content_type': 'text/plain'})
        assert matches_supplied(matt['_attachments'][ matt['photo'][1].id ], {'stub': True, 'length': 21, 'content_type': 'text/plain'})
        assert len(matt['_attachments']) == 2

        with self.S.session() as S:
            matt = S.doc_by_id(matt_id)
            matt['photo'].pop(0)

        with self.S.session() as S:
            matt = S.doc_by_id(matt_id)
        assert len(matt['_attachments']) == 1
        assert matches_supplied(matt['_attachments'][ matt['photo'][0].id ], {'stub': True, 'length': 21, 'content_type': 'text/plain'})

    def test_unchanged_file(self):
        fh = open('couchish/tests/data/files/test.txt','r')
        f = File(fh, 'test.txt','text/plain')
        matt = {'model_type': 'book', 'first_name': 'Matt', 'last_name': 'Goodall','photo': f }

        # create a file
        with self.S.session() as S:
            matt_id = S.create(matt)
        fh.close()

        # check the attachment
        first_created_photo_id = matt['photo'].id
        sess = self.S.session()
        attachment = sess.session._db.get_attachment(matt_id, first_created_photo_id)
        assert attachment == 'this is a test for the file attachment processing test in test_couchish_store\n'
        assert hasattr(matt['photo'],'id')

        # get the doc back out using couchish and check it's OK
        with self.S.session() as S:
            matt = S.doc_by_id(matt_id)
        assert len(matt['_attachments']) == 1
        assert matches_supplied(matt['_attachments'][matt['photo'].id], {'stub': True, 'length': 78, 'content_type': 'text/plain'})

        # now lets replace the file
        with self.S.session() as S:
            matt = S.doc_by_id(matt_id)
            matt['photo'] = File(None,'test_ADDEDSUFFIX.txt','text/plain')
        new_photo_id = matt.__subject__['photo'].id

        sess = self.S.session()
        attachment = sess.session._db.get_attachment(matt_id, new_photo_id)
        assert new_photo_id == first_created_photo_id
        
        with self.S.session() as S:
            matt = S.doc_by_id(matt_id)
        matt = matt.__subject__
        assert len(matt['_attachments']) == 1
        assert matches_supplied(matt['_attachments'][matt['photo'].id], {'stub': True, 'length': 78, 'content_type': 'text/plain'})
        assert matt['photo'].filename == 'test_ADDEDSUFFIX.txt'
