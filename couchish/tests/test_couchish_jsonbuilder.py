import unittest
from couchish.couchish_jsonbuilder import build, get_views
import yaml

DATADIR = 'couchish/tests/data/%s'

class Test(unittest.TestCase):

    def test_simple(self):
        book_definition = yaml.load( open(DATADIR%'test_couchish_book.yaml').read() )
        dvd_definition = yaml.load( open(DATADIR%'test_couchish_dvd.yaml').read() )
        post_definition = yaml.load( open(DATADIR%'test_couchish_post.yaml').read() )
        author_definition = yaml.load( open(DATADIR%'test_couchish_author.yaml').read() )
        views_definition = yaml.load( open(DATADIR%'test_couchish_views.yaml').read() )

        form = build(book_definition)
        assert form.structure.attr.attrs[1][1].refersto == 'author_name'

        models_definition = {'book': book_definition, 'author': author_definition,'post': post_definition, 'dvd': dvd_definition}
        viewdata = get_views(models_definition, views_definition)
        from pprint import pprint
        pprint(viewdata)
        
