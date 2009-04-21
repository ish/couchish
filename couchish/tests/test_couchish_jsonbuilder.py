import unittest
from couchish.couchish_jsonbuilder import get_views
import yaml
from couchish import sync_categories
import couchdb
from couchdb.design import ViewDefinition


DATADIR = 'couchish/tests/data/%s'

def simplifyjs(string):
    string = string.replace(';','')
    string = string.replace(' ','')
    string = string.replace('\n','')
    return string

server = couchdb.Server('http://localhost:5984')
if 'test-couchish' in server:
    del server['test-couchish']
db = server.create('test-couchish')

class Test(unittest.TestCase):

    def setUp(self):
        self.db = db

    def test_simple(self):
        book_definition = yaml.load( open(DATADIR%'test_couchish_book.yaml').read() )
        dvd_definition = yaml.load( open(DATADIR%'test_couchish_dvd.yaml').read() )
        post_definition = yaml.load( open(DATADIR%'test_couchish_post.yaml').read() )
        author_definition = yaml.load( open(DATADIR%'test_couchish_author.yaml').read() )
        views_definition = yaml.load( open(DATADIR%'test_couchish_views.yaml').read() )

        models_definition = {'book': book_definition, 'author': author_definition,'post': post_definition, 'dvd': dvd_definition}
        viewdata = get_views(models_definition, views_definition)
        assert viewdata['viewnames_by_attribute'] == {'author.first_name': set(['customdes/author_name']), 'author.last_name': set(['customdesigndoc/author_surname', 'customdes/author_name'])}
        assert viewdata['attributes_by_viewname'] == {'customdesigndoc/author_surname': {'dvd': set(['writtenby']), \
                                                                         'book': set(['coauthored'])}, \
                                                      'customdes/author_name': {'post': set(['author']), \
                                                                      'book': set(['writtenby'])}}
        views = viewdata['views']
        assert simplifyjs(views['customdes/author_name'][0]) == "function(doc){if(doc.model_type=='author'){emit(doc._id,{first_name:doc.first_name,last_name:doc.last_name})}}"
        assert simplifyjs(views['customdes/author_name-rev'][0]) == "function(doc){if(doc.model_type=='post'){emit(doc.author._ref,null)}if(doc.model_type=='book'){emit(doc.writtenby._ref,null)}}"
        assert simplifyjs(views['customdesigndoc/author_surname'][0]) == "function(doc){if(doc.model_type=='author'){emit(doc._id,{last_name:doc.last_name})}}"
        assert simplifyjs(views['customdesigndoc/author_surname-rev'][0]) == "function(doc){if(doc.model_type=='dvd'){emit(doc.writtenby._ref,null)}if(doc.model_type=='book'){emit(doc.coauthored._ref,null)}}"


    
    def test_viewby(self):
        post_definition = yaml.load( open(DATADIR%'by/test_couchish_by_post.yaml').read() )
        author_definition = yaml.load( open(DATADIR%'by/test_couchish_by_author.yaml').read() )
        views_definition = yaml.load( open(DATADIR%'by/test_couchish_by_views.yaml').read() )

        models_definition = {'author': author_definition, 'post': post_definition}
        
        viewdata = get_views(models_definition, views_definition)
        assert simplifyjs(viewdata['views']['author/by_last_name'][0]) == "function(doc){if(doc.model_type=='author'){emit(doc.last_name,null)}}"
        assert simplifyjs(viewdata['views']['post/all'][0]) == "function(doc){if(doc.model_type=='post'){emit(doc._id,null)}}"

    def test_categories_creation(self):
        categories_definition = yaml.load( open(DATADIR%'categories.yaml').read() )
        sync_categories.sync(self.db, categories_definition) 

    def test_views_creation(self):
        book_definition = yaml.load( open(DATADIR%'test_couchish_book.yaml').read() )
        dvd_definition = yaml.load( open(DATADIR%'test_couchish_dvd.yaml').read() )
        post_definition = yaml.load( open(DATADIR%'test_couchish_post.yaml').read() )
        author_definition = yaml.load( open(DATADIR%'test_couchish_author.yaml').read() )
        views_definition = yaml.load( open(DATADIR%'test_couchish_views.yaml').read() )
        models_definition = {'book': book_definition, 'author': author_definition,'post': post_definition, 'dvd': dvd_definition}
        viewdata = get_views(models_definition, views_definition)
        for url, view in viewdata['views'].items():
            designdoc = url.split('/')[0]
            view = ViewDefinition(designdoc, url, view[0])
            view.get_doc(self.db)
            view.sync(self.db)


    def test_autoviews(self):
        post_definition = yaml.load( open(DATADIR%'autoviews/test_couchish_post.yaml').read() )
        author_definition = yaml.load( open(DATADIR%'autoviews/test_couchish_author.yaml').read() )
        views_definition = yaml.load( open(DATADIR%'autoviews/test_couchish_views.yaml').read() )

        models_definition = {'author': author_definition, 'post': post_definition}
        
        viewdata = get_views(models_definition, views_definition)
        views = viewdata['views']

        assert simplifyjs(views['couchish/author_name'][0]) == "function(doc){if(doc.model_type=='author'){emit(doc._id,{first_name:doc.first_name,last_name:doc.last_name})}}"
        assert simplifyjs(views['couchish/author_name-rev'][0]) == "function(doc){if(doc.model_type=='post'){emit(doc.author._ref,null)}}"




        
