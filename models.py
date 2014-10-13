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


def model_for(entry):
    """Return the model for entry."""
    for cls in inspect.getmembers(scm.models, inspect.isclass):
        if isinstance(cls, Entry) and cls.entry_type == entry.get('_cls'):
            return cls


class Entry(object):

    entry_type = None
    query = {}

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


class Toolbox(Entry):
    entry_type = 'toolbox'
    query = dict(Entry.query, _cls=entry_type)


class Template(Entry):
    entry_type = 'template'
    query = dict(Entry.query, _cls=entry_type)


# class Variable(db.EmbeddedDocument):
#     name = db.StringField(required=True, max_length=255)
#     type = db.StringField(required=True, choices=VARIABLE_TYPES)
#     min = db.FloatField()
#     max = db.FloatField()
#     step = db.FloatField()
#     values = db.ListField()
