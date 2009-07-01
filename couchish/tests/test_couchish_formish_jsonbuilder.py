import unittest
from couchish.couchish_formish_jsonbuilder import build
import yaml
import webob
from BeautifulSoup import BeautifulSoup
import urllib
from dottedish import flatten


DATADIR = 'couchish/tests/data/%s'

class Test(unittest.TestCase):

    def request(self, d):
        r = webob.Request.blank('http://localhost/')
        r.method = 'POST'
        r.content_type = 'application/x-www-form-urlencoded'
        kvpairs = []
        for k,v in flatten(d):
            lastsegment = k.split('.')[-1]
            try:
                int(lastsegment)
                k = '.'.join(k.split('.')[:-1])
            except ValueError:
                pass
            for v in d[k]:
                kvpairs.append( (k,v) )

        r.body = urllib.urlencode(kvpairs)
        return r

    def assertRoundTrip(self, f, testdata):
        r = self.request(f._get_request_data())
        d = f.validate(r)
        self.assertEquals(d, testdata)

    def assertIdHasValue(self, f, id, v):
        soup = BeautifulSoup(f())
        self.assertEquals(soup.find(id=id)['value'],v)
        
    def assertIdAttrHasValue(self, f, id, attr, v):
        soup = BeautifulSoup(f())
        s = soup.find(id=id)
        assert 'attr' in s
        self.assertEquals(s['attr'],v)

    def assertIdAttrHasNoValue(self, f, id, attr):
        soup = BeautifulSoup(f())
        s = soup.find(id=id)
        assert 'attr' not in s

    def test_simple(self):
        book_definition = yaml.load( open(DATADIR%'test_couchish_book.yaml').read() )
        dvd_definition = yaml.load( open(DATADIR%'test_couchish_dvd.yaml').read() )
        post_definition = yaml.load( open(DATADIR%'test_couchish_post.yaml').read() )
        author_definition = yaml.load( open(DATADIR%'test_couchish_author.yaml').read() )
        views_definition = yaml.load( open(DATADIR%'test_couchish_views.yaml').read() )

        f = build(author_definition)
        self.assertIdHasValue(f, 'first_name', '')
        # Test None data
        f = build(author_definition)
        testdata = {'first_name': None, 'last_name': None}
        f.defaults = testdata
        self.assertIdHasValue(f, 'first_name', '')
        self.assertRoundTrip(f, testdata)
        # Test sample data
        f = build(author_definition)
        testdata = {'first_name': None, 'last_name': 'Goodall'}
        f.defaults = testdata
        self.assertIdHasValue(f, 'last_name', 'Goodall')
        self.assertRoundTrip(f, testdata)

    def test_fileupload(self):
        upload_definition = yaml.load( open(DATADIR%'test_upload.yaml').read() )
        f = build(upload_definition)

        
