"""
Views we can build:
    * by type, one view should be ok
    * x_by_y views, from config (optional)
    * ref and ref reversed views, one pair per relationship
"""

from couchdb.design import ViewDefinition

from couchdbsession import session

from dottedish import dotted
from copy import copy
import base64
import uuid
from couchish import filehandling, errors


class CouchishStore(object):

    def __init__(self, db, config):
        self.db = db
        self.config = config

    def sync_views(self):
        for url, view in self.config.viewdata['views'].items():
            segments = url.split('/')
            designdoc = segments[0]
            name = '/'.join(segments[1:])
            view = ViewDefinition(designdoc, name, view)
            view.get_doc(self.db)
            view.sync(self.db)

    def session(self):
        """
        Create an editing session.
        """
        return CouchishStoreSession(self)

    def _view(self, view):
        """
        Return the full name of the view, i.e. including the CouchishStore's
        namespace.
        """
        return 'couchish/%s' % (self.design_doc, view)


class CouchishStoreSession(object):

    def __init__(self, store):
        self.store = store
        self.session = session.Session(store.db,
              pre_flush_hook=self._pre_flush_hook,
              post_flush_hook=self._post_flush_hook)
        self.file_additions = {}
        self.file_deletions = {}

    def __enter__(self):
        """
        "with" statement entry.
        """
        return self

    def __exit__(self, type, value, traceback):
        """
        "with" statement exit.
        """
        if type is None:
            self.flush()
        else:
            self.reset()

    def create(self, doc):
        """
        Create a document.
        """
        return self.session.create(doc)

    def delete(self, doc_or_tuple):
        """
        Delete the given document.
        """
        if isinstance(doc_or_tuple, tuple):
            id, rev = doc_or_tuple
            doc = {'_id': id, 'rev': rev}
        else:
            doc = doc_or_tuple
        return self.session.delete(doc)

    def get_attachment(self, id_or_doc, filename):
        return self.session._db.get_attachment(id_or_doc, filename)

    def put_attachment(self, doc, content, filename=None, content_type=None):
        return self.session._db.put_attachment(doc, content, filename=filename,
                                               content_type=content_type)

    def delete_attachment(self, doc, filename):
        return self.session._db.delete_attachment(doc, filename)

    def doc_by_id(self, id):
        """
        Return a single document, given it's ID.
        """
        doc = self.session.get(id)
        if doc is None:
            raise errors.NotFound("No document with id %r" % (id,))
        return doc

    def doc_by_view(self, view, key):
        results = self.session.view(view, startkey=key, endkey=key, limit=2,
                                    include_docs=True)
        rows = results.rows
        if len(rows) == 0:
            raise errors.NotFound("No document in view %r with key %r" % (view, key))
        elif len(rows) == 2:
            raise errors.TooMany("Too many documents in view %r for key %r" % (view, key))
        return rows[0].doc

    def docs_by_id(self, ids, **options):
        """
        Generate the sequence of documents with the given ids.
        """
        options = dict(options)
        options['keys'] = ids
        options['include_docs'] = True
        results = self.session.view('_all_docs', **options)
        return (row.doc for row in results.rows)

    def docs_by_type(self, type, **options):
        """
        Generate the sequence of docs of a given type.
        """
        options = dict(options)
        options['startkey'] = type
        options['endkey'] = type
        options['include_docs'] = True
        results = self.view(self.store._view(type), **options)
        return (row.doc for row in results.rows)

    def docs_by_view(self, view, **options):
        options = dict(options)
        options['include_docs'] = True
        results = self.session.view(view, **options)
        return (row.doc for row in results.rows)

    def view(self, view, **options):
        """
        Call and return a view.
        """
        return self.session.view(view, **options)

    def _pre_flush_hook(self, session, deletions, additions, changes):
        self.file_deletions, self.file_additions = filehandling._parse_changes_for_files(session, deletions, additions, changes)

    def flush(self):
        """
        Flush the session.
        """
        returnvalue =  self.session.flush()
        filehandling._handle_separate_attachments(self.session, self.file_deletions, self.file_additions)
        return returnvalue

    def reset(self):
        """
        Reset the session, forgetting everything it knows.
        """
        self.session.reset()

    def _post_flush_hook(self, session, deletions, additions, changes):

        # Sentinel to indicate we haven't retrieved the ref view data yet.
        NO_REF_DATA = object()

        # Easy access to the config.
        views_by_viewname =  self.store.config.viewdata['views_by_viewname']
        viewnames_by_attribute =  self.store.config.viewdata['viewnames_by_attribute']
        attributes_by_viewname =  self.store.config.viewdata['attributes_by_viewname']

        # Updates any documents that refer to documents that have been changed.
        for doc, actions in changes:
            doc_type = doc['model_type']
            edited = set('.'.join([doc_type, '.'.join(str(p) for p in action['path'])])
                         for action in actions if action['action'] == 'edit')
            # Build a set of all the views affected by the changed attributes.
            views = set()
            for attr in edited:
                views.update(viewnames_by_attribute.get(attr, []))
            for view in views:
                # Lazy load the ref_data.
                ref_data = NO_REF_DATA
                attrs_by_type = attributes_by_viewname[view]
                view_url = views_by_viewname[view]['url']
                # XXX should build a full key here, but let's assume just the
                # id for a moment.
                ref_key = doc['_id']
                for ref_doc in self.docs_by_view(view_url+'-rev', startkey=ref_key, endkey=ref_key):
                    # Fetch the ref data for this ref view, if we don't already
                    # have it.
                    if ref_data is NO_REF_DATA:
                        ref_data = self.view(view_url, startkey=ref_key, limit=1).rows[0].value
                        ref_data['_ref'] = ref_key
                    for attr in attrs_by_type[ref_doc['model_type']]:
                        # Any of the attrs sections could be a sequence.. we need to iterate over them all to find matches.. 
                        # e.g. we may have authors*. or metadata*.authors*
                        self._find_and_match_nested_item(ref_doc, attr.split('.'), ref_data)

    def _find_and_match_nested_item(self, ref_doc, segments, ref_data, prefix=None):
        # Initialise of copy the prefix list, because we're about to change it.
        if prefix is None:
            prefix = []
        else:
            prefix = list(prefix)

        if segments == []:
            if ref_doc['_ref'] == ref_data['_ref']:
                ref_doc.update(ref_data)
        else:
            current, segments = segments[0], segments[1:]
            if current.endswith('*'):
                is_seq = True
            else:
                is_seq = False
            current = current.replace('*','')

            prefix.append(current)
            current_ref = ref_doc[current]
            if is_seq:
                for ref_doc_ref in current_ref:
                    self._find_and_match_nested_item(ref_doc_ref, segments, ref_data, prefix)
            else:
                self._find_and_match_nested_item(current_ref, segments, ref_data, prefix)

