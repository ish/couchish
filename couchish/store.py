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

class CouchishError(Exception):
    """
    Base class type for all couchish exception types.
    """
    pass


class NotFound(CouchishError):
    """
    Document not found.
    """
    pass


class TooMany(CouchishError):
    """
    Too may documents were found.
    """
    pass


def get_attr(prefix, parent):
    if prefix is None:
        return parent
    segments = [str(segment) for segment in prefix]
    if parent != '':
        segments += parent.split('.')
    attr = '.'.join( segments )
    return attr

def get_files(data, original=None, prefix=None):
    files = {}
    inlinefiles = {}
    original_files = {}
    if isinstance(original, dict):
        get_files_from_original(data, original, files, inlinefiles, original_files, prefix)
    if isinstance(data, dict):
        get_files_from_data(data, original, files, inlinefiles, original_files, prefix)
    return data, files, inlinefiles, original_files

def has_unmodified_signature(f):
    # do we have any data keys
    if ('file' in f or 'base64' in f or 'data' in f):
        # are the data keys None
        if f.get('file') is None and f.get('data') is None and f.get('base64') is None:
            return True
    return False

def get_with_empty_handler(d, parent):
    if parent == '':
        return d
    else:
        return d[parent]

def clear_file_data(f):
    if 'file' in f:
        del f['file']
    if 'base64' in f:
        del f['base64']
    if 'data' in f:
        del f['data']

def make_dotted_or_emptydict(d):
    if isinstance(d, dict):
        return dotted(d)
    return {}

def get_files_from_data(data, original, files, inlinefiles, original_files, prefix):
    dd = make_dotted_or_emptydict(data)
    ddoriginal = make_dotted_or_emptydict(original)
    for k in dd.dottedkeys():
        kparent, lastk = '.'.join(k.split('.')[:-1]), k.split('.')[-1]
        if lastk == '__type__' and dd[k] == 'file':
            f = get_with_empty_handler(dd, kparent)
            if has_unmodified_signature(f):
                # if we have no original data then we presume the file should remain unchanged
                if original is not None and isinstance(original, dict):
                    f = get_with_empty_handler(ddoriginal)
            else:
                # We're dealing with a new file so we create a uuid and attach it
                f['id'] = uuid.uuid4().hex
                if f.get('inline',False) is True:
                    filestore = inlinefiles
                else:
                    filestore = files
                #  add the files for attachment handling and remove the file data from document
                filestore[get_attr(prefix, kparent)] = copy(f.data)
                clear_file_data(f)

def get_files_from_original(data, original, files, inlinefiles, original_files, prefix):
    dd = make_dotted_or_emptydict(data)
    ddoriginal = make_dotted_or_emptydict(original)
    for k in ddoriginal.dottedkeys():
        kparent, lastk = '.'.join(k.split('.')[:-1]), k.split('.')[-1]
        # is the new data a new file
        if lastk == '__type__' and ddoriginal[k] == 'file':
            f = get_with_empty_handler(ddoriginal, kparent)
            new_item = get_with_empty_handler(dd, kparent)
            if not has_unmodified_signature(new_item):
                original_files[get_attr(prefix, kparent)] = f


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
        return self.session._db.put_attachment(doc, content, filename=filename, content_type=content_type)

    def delete_attachment(self, doc, filename):
        return self.session._db.delete_attachment(doc, filename)

    def doc_by_id(self, id):
        """
        Return a single document, given it's ID.
        """
        return self.session.get(id)

    def doc_by_view(self, view, key):
        results = self.session.view(view, startkey=key, endkey=key, limit=2,
                                    include_docs=True)
        rows = results.rows
        if len(rows) == 0:
            raise NotFound()
        elif len(rows) == 2:
            raise TooMany()
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
        self._parse_changes_for_files(session, deletions, additions, changes)

    def _parse_changes_for_files(self, session, deletions, additions, changes):
        additions = list(additions)
        changes = list(changes)
        deletions = list(deletions)
        all_separate_files = {}
        all_inline_files = {}
        for addition in additions:
            addition, files, inlinefiles, original_files_notused = get_files(addition)
            if files:
                all_separate_files.setdefault(addition['_id'],{}).update(files)
            if inlinefiles:
                all_inline_files.setdefault(addition['_id'],{}).update(inlinefiles)
            self._extract_inline_attachments(addition, inlinefiles)


        all_original_files = {}
        changes = list(changes)
        for n, changeset in enumerate(changes):
            d, cs = changeset
            cs = list(cs)
            for m, c in enumerate(cs):
                if c['action'] in ['edit','create','remove']:
                    c['value'], files, inlinefiles, original_files = get_files(c.get('value'), original=c.get('was'), prefix=c['path'])
                    cs[m] = c
                    if files:
                        all_separate_files.setdefault(d['_id'],{}).update(files)
                    if inlinefiles:
                        all_inline_files.setdefault(d['_id'],{}).update(inlinefiles)
                    all_original_files.setdefault(d['_id'], {}).update(original_files)
                    self._extract_inline_attachments(d, inlinefiles)
            changes[n] = (d, cs)

        self.file_deletions = all_original_files
        self.file_additions = all_separate_files

    def _extract_inline_attachments(self, doc, files):
        """
        Move the any attachment data that we've found into the _attachments attribute
        """
        for attr, f in files.items():
            if 'data' in f:
                data = base64.encodestring(f['data']).strip()
            if 'base64' in f:
                data = f['base64'].replace('\n','').strip()
            if 'file' in f:
                data = base64.encodestring(f['file'].read()).strip()
            doc.setdefault('_attachments',{})[f['id']] = {'content_type': f['mimetype'],'data': data}

    def flush(self):
        """
        Flush the session.
        """
        returnvalue =  self.session.flush()
        self._handle_separate_attachments()
        return returnvalue

    def _handle_separate_attachments(self):
        """
        add attachments that aren't inline and remove any attachments without references
        """
        # XXX This needs to cope with files moving when sequences are re-numbered. We need
        # XXX to talk to matt about what a renumbering like this looks like

        for id, attrfiles in self.file_additions.items():
            doc = self.session.get(id)
            for attr, f in attrfiles.items():
                if 'data' in f:
                    data = f['data']
                elif 'base64' in f:
                    data = base64.decodestring(f['base64'])
                else:
                    data = f['file'].read()
                self.session._db.put_attachment({'_id':doc['_id'], '_rev':doc['_rev']}, data, filename=f['id'], content_type=f['mimetype'])

        for id, attrfiles in self.file_deletions.items():
            # XXX had to use _db because delete attachment freeaked using session version. 
            doc = self.session._db.get(id)
            for attr, f in attrfiles.items():
                self.session._db.delete_attachment(doc, f['id'])

        self.file_additions = {}
        self.file_deletions = {}

    def _find_and_match_nested_item(self, ref_doc, segments, ref_data, prefix=None):
        """
        """
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

