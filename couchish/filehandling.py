"""
Views we can build:
    * by type, one view should be ok
    * x_by_y views, from config (optional)
    * ref and ref reversed views, one pair per relationship
"""


from dottedish import dotted
from copy import copy
import base64
import uuid


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


def _parse_changes_for_files(session, deletions, additions, changes):
    """ returns deletions, additions """
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
        _extract_inline_attachments(addition, inlinefiles)

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
                _extract_inline_attachments(d, inlinefiles)
        changes[n] = (d, cs)

    return all_original_files, all_separate_files


def _extract_inline_attachments(doc, files):
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


def _handle_separate_attachments(session, deletions, additions):
    """
    add attachments that aren't inline and remove any attachments without references
    """
    # XXX This needs to cope with files moving when sequences are re-numbered. We need
    # XXX to talk to matt about what a renumbering like this looks like

    for id, attrfiles in additions.items():
        doc = session.get(id)
        for attr, f in attrfiles.items():
            if 'data' in f:
                data = f['data']
            elif 'base64' in f:
                data = base64.decodestring(f['base64'])
            else:
                data = f['file'].read()
            session._db.put_attachment({'_id':doc['_id'], '_rev':doc['_rev']}, data, filename=f['id'], content_type=f['mimetype'])

    for id, attrfiles in deletions.items():
        # XXX had to use _db because delete attachment freeaked using session version. 
        doc = session._db.get(id)
        for attr, f in attrfiles.items():
            session._db.delete_attachment(doc, f['id'])

    additions = {}
    deletions = {}

