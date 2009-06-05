import unittest
import uuid
import couchdb

from couchish import config, filestore, store


class TestSource(unittest.TestCase):

    def setUp(self):
        self.db_name = 't' + uuid.uuid4().hex
        self.server = couchdb.Server()
        self.db = self.server.create(self.db_name)
        self.store = store.CouchishStore(self.db, config.Config({}, []))
        self.source = filestore.CouchDBAttachmentSource(self.store)

    def tearDown(self):
        del self.server[self.db_name]

    def test_get_cache_hit(self):
        self.db['doc'] = {}
        doc = self.db['doc']
        self.db.put_attachment(doc, 'Yay!', 'foo.txt', 'text/plain')
        (cache_tag, headers, f) = self.source.get('doc/foo.txt', cache_tag=doc['_rev'])
        headers = dict(headers)
        assert cache_tag == doc['_rev']
        assert headers['Content-Type'] is None
        assert f is None

    def test_get_cache_miss(self):
        self.db['doc'] = {}
        doc = self.db['doc']
        self.db.put_attachment(doc, 'Yay!', 'foo', 'text/plain')
        (cache_tag, headers, f) = self.source.get('doc/foo', cache_tag='miss')
        headers = dict(headers)
        try:
            assert cache_tag == doc['_rev']
            assert headers['Content-Type'] == 'text/plain'
            assert f is not None
            assert f.read() == 'Yay!'
        finally:
            f.close()

    def test_missing_doc(self):
        self.assertRaises(KeyError, self.source.get, 'missing_doc/attachment')

    def test_missing_attachment(self):
        self.db['doc'] = {}
        self.assertRaises(KeyError, self.source.get, 'doc/missing_attachment')

