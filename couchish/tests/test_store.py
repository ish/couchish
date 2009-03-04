from __future__ import with_statement

import unittest

from couchish import config, store
from couchish.tests import util


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


if __name__ == '__main__':
    unittest.main()

