"""
Couchish configuration.
"""

from couchish.couchish_jsonbuilder import get_views


class Config(object):

    def __init__(self, types, views):
        self.types = types
        self.views = views
        self.viewdata = get_views(types, views)

    @classmethod
    def from_yaml(cls, types, views):
        """
        Load config from a set of YAML config files.
        """
        import yaml
        types = dict((name,yaml.load(file(filename)))
                     for (name, filename) in types.iteritems())
        views = yaml.load(file(views))
        return cls(types, views)

