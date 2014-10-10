import datetime
import inspect
from flask import url_for
from scm import mongo

# Valid source repositories
SOURCE_TYPES = (('git', 'GIT repository'),
                ('svn', 'Subversion repository'))

# Types of dependencies we can resolve
DEPENDENCY_TYPES = (('system', 'System package'),
                    ('python', 'Python package from pypi'),
                    ('toolbox', 'A toolbox from the SCM'))

# Variable types for templates
VARIABLE_TYPES = (('int', 'Integer'),
                  ('dbl', 'Floating point'),
                  ('str', 'String'))


def _filter_fields(spec, entry):
    """Filter entries in entry according to spec."""
    def f(k, v):
        if k in spec:
            g = spec.get(k)
            if callable(g):
                g = g(k, v)
            if g is None:
                return None
            elif isinstance(g, tuple):
                return g
            else:
                return k, g
        else:
            return k, v

    return dict(filter(None, [f(k, v) for k, v in entry.items()]))


def model_for(entry):
    """Return the model for entry."""
    for cls in inspect.getmembers(scm.models, inspect.isclass):
        if isinstance(cls, Entry) and cls.entry_type == entry.get('_cls'):
            return cls


class Entry(object):

    entry_type = None

    @classmethod
    def create(cls, entry):
        """Add a new entry to the catalogue and return it.

        TODO: Validate input data!

        PARAMETERS

        entry -- dict containing the parsed json entry

        """
        # Make sure we know what we're adding
        if cls.entry_type is None:
            raise TypeError("_create_exception must be called for a specific entry type.")
        # Copy the input
        entry = dict(entry)
        # Update metadata
        entry['metadata'] = {
            'author': 'S. C. Marketplace',
            'created_at': datetime.datetime.now(),
            'version': 1
        }
        entry['_cls'] = cls.entry_type
        entry_id = mongo.db.entry.insert(entry)
        return mongo.db.entry.find_one(entry_id)

    @classmethod
    def is_model_for(cls, entry):
        """Return True if this class is the model for entry."""
        return cls.entry_type == entry.get('_cls')

    @classmethod
    def for_api(cls, entry, endpoint):
        """Filter entry for returning from the api."""
        api_fields = {
            '_id': ('@id', entry_url(entry)),
            '_cls': None,
            'toolbox': lambda _, v: id_url('', v)
        }
        return _filter_fields(api_fields, entry)


class Toolbox(Entry):
    entry_type = 'toolbox'
    query = {'_cls': entry_type}


class Template(Entry):
    entry_type = 'template'
    query = {'_cls': entry_type}


# class Variable(db.EmbeddedDocument):
#     name = db.StringField(required=True, max_length=255)
#     type = db.StringField(required=True, choices=VARIABLE_TYPES)
#     min = db.FloatField()
#     max = db.FloatField()
#     step = db.FloatField()
#     values = db.ListField()
