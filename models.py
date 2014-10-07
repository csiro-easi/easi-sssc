import datetime
from flask import url_for
from scm import db

# Valid source repositories
SOURCE_TYPES = (('git', 'GIT repository'),
                ('svn', 'Subversion repository'))

# Types of dependencies we can resolve
DEPENDENCY_TYPES = (('system', 'System package'),
                    ('python', 'Python package from pypi'))

# Variable types for templates
VARIABLE_TYPES = (('int', 'Integer'),
                  ('dbl', 'Floating point'),
                  ('str', 'String'))


class Entry(db.Document):
    """A generic entry in the catalogue."""
    name = db.StringField(max_length=255, required=True)
    description = db.StringField()
    homepage = db.URLField()
    license = db.URLField()
    dependencies = db.ListField(db.EmbeddedDocumentField('Dependency'))
    created_at = db.DateTimeField(default=datetime.datetime.now, required=True)
    author = db.StringField(required=True, max_length=255)

    def get_absolute_url(self):
        return url_for('entry')

    def __unicode__(self):
        return self.name

    meta = {
        'allow_inheritance': True,
        'indexes': ['-created_at', 'name'],
        'ordering': ['-created_at']
    }


class Source(db.EmbeddedDocument):
    """Source for an entry."""
    type = db.StringField(required=True, choices=SOURCE_TYPES)
    url = db.URLField(required=True)
    branch = db.StringField(max_length=255, default="master")


class Dependency(db.EmbeddedDocument):
    """Dependency for an entry."""
    type = db.StringField(required=True, choices=DEPENDENCY_TYPES)
    name = db.StringField(max_length=255)
    version = db.StringField(max_length=20)
    path = db.StringField(max_length=255)


class Variable(db.EmbeddedDocument):
    name = db.StringField(required=True, max_length=255)
    type = db.StringField(required=True, choices=VARIABLE_TYPES)
    min = db.FloatField()
    max = db.FloatField()
    step = db.FloatField()
    values = db.ListField()


class Toolbox(Entry):
    """An entry for a scientific code package.

    Adds a source repository where the code can be retrieved.

    """
    source = db.EmbeddedDocumentField('Source')


class Template(Entry):
    """A template entry that runs a specific workflow.

    Depends on a Toolbox to provide the base application. Also
    includes the template script, and a description of the variables
    required to instantiate it correctly.

    """
    toolbox = db.ReferenceField('Toolbox')
    template = db.StringField(required=True)
    variables = db.ListField(db.EmbeddedDocumentField('Variable'))
