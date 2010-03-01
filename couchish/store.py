"""
Views we can build:
    * by type, one view should be ok
    * x_by_y views, from config (optional)
    * ref and ref reversed views, one pair per relationship
"""

from datetime import datetime
from couchdb.design import ViewDefinition
from couchdbsession import a8n, session
import schemaish.type

from couchish import filehandling, errors, jsonutil


class CouchishStore(object):

    def __init__(self, db, config, pre_flush_hook=None, post_flush_hook=None):
        self.db = db
        self.config = config
        self.pre_flush_hook = pre_flush_hook
        self.post_flush_hook = post_flush_hook

    def sync_views(self):
        for url, view in self.config.viewdata['views'].items():
            segments = url.split('/')
            designdoc = segments[0]
            name = '/'.join(segments[1:])
            view = ViewDefinition(designdoc, name, view[0], view[1])
            view.get_doc(self.db)
            view.sync(self.db)

    def session(self):
        """
        Create an editing session.
        """
        return CouchishStoreSession(self)



class CouchishStoreSession(object):

    def __init__(self, store):
        self.store = store
        self.session = Session(store.db,
              pre_flush_hook=self._pre_flush_hook,
              post_flush_hook=self._post_flush_hook,
              encode_doc=jsonutil.encode_to_dict,
              decode_doc=lambda d: jsonutil.decode_from_dict(d, self))
        self.file_additions = {}
        self.file_deletions = {}
        self._flush_timestamp = None

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
        return self.session._db.put_attachment(doc, content,
                                            filename=filename, content_type=content_type)

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

    def doc_by_view(self, view, key=None):
        if key is not None:
            results = self.session.view(view, startkey=key, endkey=key, limit=2,
                                    include_docs=True)
        else:
            results = self.session.view(view, limit=2, include_docs=True)
        rows = results.rows
        if len(rows) == 0:
            message = "No document in view %r"%view
            if key is not None:
                message += " with key %r"%key
            raise errors.NotFound(message)
        elif len(rows) == 2:
            message = "Too many documents in view %r"%view
            if key is not None:
                message += " with key %r"%key
            raise errors.TooMany(message)
        return rows[0].doc

    def docs_by_id(self, ids, remove_rows_with_missing_doc=False, **options):
        """
        Generate the sequence of documents with the given ids.
        """
        options['keys'] = ids
        return self.docs_by_view(
            '_all_docs',
            remove_rows_with_missing_doc=remove_rows_with_missing_doc,
            **options)

    def docs_by_type(self, type, remove_rows_with_missing_doc=False,
                     **options):
        """
        Generate the sequence of docs of a given type.
        """
        config = self.store.config.types[type]
        view = config.get('metadata', {}).get('views', {}).get('all')
        if not view:
            view = '%s/all'%type
        return self.docs_by_view(
            view, remove_rows_with_missing_doc=remove_rows_with_missing_doc,
            **options)

    def docs_by_view(self, view, remove_rows_with_missing_doc=False,
                     **options):
        options['include_docs'] = True
        results = self.view(view, **options)
        docs = (row.doc for row in results.rows)
        if remove_rows_with_missing_doc:
            docs = (doc for doc in docs if doc is not None)
        return docs

    def view(self, view, **options):
        """
        Call and return a view.
        """
        return self.session.view(view, **options)

    def _pre_flush_hook(self, session, deletions, additions, changes):
        # We're iterating the sequences multiple time so we might as well just
        # turn them into lists and be done with it.
        deletions, additions, changes = \
                list(deletions), list(additions), list(changes)
        if self.store.pre_flush_hook is not None:
            self.store.pre_flush_hook(deletions, additions, changes)
        # Record ctime and mtime for addited and updated documents.
        for doc in additions:
            metadata = doc.setdefault('metadata', {})
            metadata['ctime'] = metadata['mtime'] = self._flush_timestamp
        for doc, _ in changes:
            metadata = doc.setdefault('metadata', {})
            metadata['mtime'] = self._flush_timestamp
        # Record any files that need storing.
        file_deletions, file_additions = filehandling._parse_changes_for_files(
            session, deletions, additions, changes)
        self.file_deletions.update(file_deletions)
        self.file_additions.update(file_additions)

    def flush(self):
        """
        Flush the session.
        """
        # Record the timestamp of the flush, used for all timestamps during the save.
        self._flush_timestamp = datetime.utcnow().isoformat()
        returnvalue =  self.session.flush()
        filehandling._handle_separate_attachments(self.session, self.file_deletions, self.file_additions)
        self.file_additions = {}
        self.file_deletions = {}
        return returnvalue

    def reset(self):
        """
        Reset the session, forgetting everything it knows.
        """
        self.session.reset()

    def make_refs(self, view, ref_keys):
        """
        Build a mapping of ref_keys to refs, where a ref is a dict containing a
        '_ref' item and anything else returned as the view's value.
        """
        def ref_from_row(row):
            ref = row.value
            ref['_ref'] = row.key
            return ref
        rows = self.view(view, keys=ref_keys)
        return dict((row.key, ref_from_row(row)) for row in rows)

    def make_ref(self, view, ref_key):
        """
        Build a ref (see make_refs) for the row with the given ref_key.
        """
        return self.make_refs(view, [ref_key])[ref_key]

    def _post_flush_hook(self, session, deletions, additions, changes):
        if self.store.post_flush_hook is not None:
            self.store.post_flush_hook(deletions, additions, changes)

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
                        if isinstance(ref_data, dict):
                            ref_data['_ref'] = ref_key
                        else:
                            ref_data = {'_ref': ref_key, 'data': ref_data}
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
            current_ref = ref_doc.get(current)
            if current_ref is None:
                return
            if is_seq:
                for ref_doc_ref in current_ref:
                    self._find_and_match_nested_item(ref_doc_ref, segments, ref_data, prefix)
            else:
                self._find_and_match_nested_item(current_ref, segments, ref_data, prefix)



class Tracker(a8n.Tracker):
    def _track(self, obj, path):
        if isinstance(obj, (jsonutil.CouchishFile, schemaish.type.File)):
            return obj
        return super(Tracker, self)._track(obj, path)


class Session(session.Session):
    tracker_factory = Tracker

