from __future__ import with_statement
from cStringIO import StringIO

import couchish


class CouchDBAttachmentSource(object):
    """
    A file source for the FileResource to use to read attachments from
    documents in a CouchDB database.
    
    Note: the application would be responsible for uploading files.
    """

    def __init__(self, couchish_store):
        self.couchish = couchish_store

    def get(self, key, cache_tag=None):
        # XXX This would be much better written using httplib2 and performing a
        # single GET to request the image directly, using the ETag as the
        # cache_tag (which is the document _rev anyway). But for now ...
        try:
            doc_id, attachment_name = key.split('/', 1)
        except ValueError:
            raise KeyError
        # Get the document with the attachment to see if we actually need to
        # fetch the whole attachment.
        try:
            with self.couchish.session() as S:
                doc = S.doc_by_id(doc_id)
        except couchish.NotFound:
            raise KeyError(key)
        # Check the attachment stub exists.
        attachment_stub = doc.get('_attachments', {}).get(attachment_name)
        if attachment_stub is None:
            raise KeyError(key)
        # See if the caller's version is up to date.
        if cache_tag and doc['_rev'] == cache_tag:
            return (doc['_rev'],  [('Content-Type',None)], None)
        # Get the attachment content.
        with self.couchish.session() as S:
            content = S.get_attachment(doc_id, attachment_name)
        return (doc['_rev'], [('Content-Type',attachment_stub['content_type'])], StringIO(content))

