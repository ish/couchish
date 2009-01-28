from __future__ import with_statement

import unittest
import uuid

import couchdb
from couchish import config, store


class TestCase(unittest.TestCase):

    def setUp(self):
        self.db_name = 'couchish-' + str(uuid.uuid4())
        self.db = couchdb.Server().create(self.db_name)
        self.store = store.CouchishStore(self.db, config.Config({}, {}))

    def tearDown(self):
        del couchdb.Server()[self.db_name]


class TestStore(TestCase):

    def test_session(self):
        S = self.store.session()
        doc_id = S.create({})
        S.flush()
        assert self.db.get(doc_id)

    def test_with_session(self):
        with self.store.session() as S:
            S.create({'_id': 'foo'})
        assert self.db.get('foo')

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


if __name__ == '__main__':
    unittest.main()

