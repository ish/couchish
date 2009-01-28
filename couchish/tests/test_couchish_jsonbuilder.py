import unittest
from couchish.couchish_jsonbuilder import get_views
import yaml
from sets import Set
from couchish import categories
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
        assert viewdata['viewnames_by_attribute'] == {'author.first_name': Set(['author_name']), 'author.last_name': Set(['author_surname', 'author_name'])}
        assert viewdata['attributes_by_viewname'] == {'author_surname': {'dvd': Set(['writtenby']), \
                                                                         'book': Set(['coauthored'])}, \
                                                      'author_name': {'post': Set(['author']), \
                                                                      'book': Set(['writtenby'])}}
        views = viewdata['views']
        assert simplifyjs(views['customdes/author_name']) == "function(doc){if(doc.model_type=='author'){emit(doc._id,{first_name:doc.first_name,last_name:doc.last_name})}}"
        assert simplifyjs(views['customdes/author_name-rev']) == "function(doc){if(doc.model_type=='post'){emit(doc.author._ref,null)}if(doc.model_type=='book'){emit(doc.writtenby._ref,null)}}"
        assert simplifyjs(views['customdesigndoc/author_surname']) == "function(doc){if(doc.model_type=='author'){emit(doc._id,{last_name:doc.last_name})}}"
        assert simplifyjs(views['customdesigndoc/author_surname-rev']) == "function(doc){if(doc.model_type=='dvd'){emit(doc.writtenby._ref,null)}if(doc.model_type=='book'){emit(doc.coauthored._ref,null)}}"


    
    def test_viewby(self):
        post_definition = yaml.load( open(DATADIR%'test_couchish_by_post.yaml').read() )
        author_definition = yaml.load( open(DATADIR%'test_couchish_by_author.yaml').read() )
        views_definition = yaml.load( open(DATADIR%'test_couchish_by_views.yaml').read() )

        models_definition = {'author': author_definition, 'post': post_definition}
        
        viewdata = get_views(models_definition, views_definition)
        assert simplifyjs(viewdata['views']['author/by_last_name']) == "function(doc){if(doc.model_type=='author'){emit(doc.last_name,null)}}"
        assert viewdata['views']['post/all'] == "function(doc) { if (doc.model_type == 'post')  emit(doc._id, null) }"

    def test_categories_creation(self):
        categories_definition = yaml.load( open(DATADIR%'categories.yaml').read() )
        categories.create_categories(self.db, categories_definition) 

    def test_views_creation(self):
        book_definition = yaml.load( open(DATADIR%'test_couchish_book.yaml').read() )
        dvd_definition = yaml.load( open(DATADIR%'test_couchish_dvd.yaml').read() )
        post_definition = yaml.load( open(DATADIR%'test_couchish_post.yaml').read() )
        author_definition = yaml.load( open(DATADIR%'test_couchish_author.yaml').read() )
        views_definition = yaml.load( open(DATADIR%'test_couchish_views.yaml').read() )
        models_definition = {'book': book_definition, 'author': author_definition,'post': post_definition, 'dvd': dvd_definition}
        viewdata = get_views(models_definition, views_definition)
        for url, view in viewdata['views'].items():
            segments = url[1:].split('/')
            designdoc = segments[0]
            name = '/'.join(segments[1:])
            view = ViewDefinition(designdoc, name, view)
            view.get_doc(self.db)
            view.sync(self.db)


    def test_autoviews(self):
        post_definition = yaml.load( open(DATADIR%'test_couchish_autoviews_post.yaml').read() )
        author_definition = yaml.load( open(DATADIR%'test_couchish_autoviews_author.yaml').read() )
        views_definition = yaml.load( open(DATADIR%'test_couchish_autoviews_views.yaml').read() )

        models_definition = {'author': author_definition, 'post': post_definition}
        
        viewdata = get_views(models_definition, views_definition)
        views = viewdata['views']

        assert simplifyjs(views['couchish/author_name']) == "function(doc){if(doc.model_type=='author'){emit(doc._id,{first_name:doc.first_name,last_name:doc.last_name})}}"
        assert simplifyjs(views['couchish/author_name-rev']) == "function(doc){if(doc.model_type=='post'){emit(doc.author._ref,null)}}"


        
