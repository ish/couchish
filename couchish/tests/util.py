import uuid
import couchdb


class TempDatabaseMixin(object):

    def setUp(self):
        self.db_name = 'couchish-' + str(uuid.uuid4())
        self.db = couchdb.Server().create(self.db_name)

    def tearDown(self):
        del couchdb.Server()[self.db_name]

