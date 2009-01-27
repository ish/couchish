import unittest
from couchish.couchish_jsonbuilder import build, get_views
import yaml
from sets import Set

DATADIR = 'couchish/tests/data/%s'

def simplifyjs(string):
    string = string.replace(';','')
    string = string.replace(' ','')
    string = string.replace('\n','')
    return string

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
        assert viewdata['viewnames_by_attribute'] == {'author.first_name': Set(['author_name']), 'author.last_name': Set(['author_surname', 'author_name'])}
        assert viewdata['attributes_by_viewname'] == {'author_name':    {'book': Set(['author.last_name', 'author.first_name']), \
                                                                         'post': Set(['author.last_name', 'author.first_name'])}, \
                                                      'author_surname': {'book': Set(['author.last_name']), \
                                                                         'dvd': Set(['author.last_name'])}}
        views = viewdata['views']
        assert simplifyjs(views['/couchish/author_name']) == "function(doc){if(model_type=='author'){emit(doc._id,{first_name:doc.first_name,last_name:doc.last_name})}}"
        assert simplifyjs(views['/couchish/author_name-rev']) == "function(doc){if(type=='post'){emit(doc.author._ref,doc._id)}if(type=='book'){emit(doc.writtenby._ref,doc._id)}}"
        assert simplifyjs(views['/customdesigndoc/author_surname']) == "function(doc){if(model_type=='author'){emit(doc._id,{last_name:doc.last_name})}}"
        assert simplifyjs(views['/customdesigndoc/author_surname-rev']) == "function(doc){if(type=='dvd'){emit(doc.writtenby._ref,doc._id)}if(type=='book'){emit(doc.coauthored._ref,doc._id)}}"
        print '*'*80
        from pprint import pprint
        pprint(viewdata['views'])

        print '*'*80


    
    def test_viewby(self):
        post_definition = yaml.load( open(DATADIR%'test_couchish_by_post.yaml').read() )
        author_definition = yaml.load( open(DATADIR%'test_couchish_by_author.yaml').read() )
        views_definition = yaml.load( open(DATADIR%'test_couchish_by_views.yaml').read() )

        models_definition = {'author': author_definition, 'post': post_definition}
        
        viewdata = get_views(models_definition, views_definition)
        assert simplifyjs(viewdata['views']['/author/by_last_name']) == "function(doc){if(model_type=='author'){emit(doc.last_name,doc._id)}}"
        assert viewdata['views']['/post/all'] == "function(doc) { if (doc.model_type == 'post')  emit(doc._id, doc) }"
        from pprint import pprint
        pprint(viewdata['views'])
        print '*'*80
