"""
Views we can build:
    * by type, one view should be ok
    * x_by_y views, from config (optional)
    * ref and ref reversed views, one pair per relationship
"""

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

