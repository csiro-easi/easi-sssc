import datetime
from mongoengine import *

# Valid source repositories
SOURCE_TYPES = (('git', 'GIT repository'),
                ('svn', 'Subversion repository'))

# Types of dependencies we can resolve
DEPENDENCY_TYPES = (('system', 'System package'),
                    ('python', 'Python package from pypi'))

# Variable types for solutions
VARIABLE_TYPES = (('int', 'Integer'),
                  ('double', 'Floating point'),
                  ('string', 'String'),
                  ('random-int', 'Random Integer'))


def text_search(text):
    """Search for entries that match text.

    Performs a basic text search for text. Equivalent to calling:

    pymongo_find({"$text": {"$search": text}})

    Drops to PyMongo for text search support while MongoEngine doesn't
    support it. Wraps the dict results from pymongo in model
    instances.

    """
    return pymongo_find({"$text": {"$search": text}})


def pymongo_find(query):
    """Performs a find(query) using the PyMongo connection directly.

    Wraps the dict results in model instances before returning them.

    """
    results = Entry._get_collection().find(query, fields="_id")
    if results:
        return Entry.objects(id__in=[result['_id'] for result in results])


class User(Document):
    """Catalogue user."""
    email = EmailField(primary_key=True)
    name = StringField()


class Metadata(EmbeddedDocument):
    """Metadata for all catalogue entries."""
    created_at = DateTimeField(default=datetime.datetime.now)
    author = ReferenceField(User)  # , required=True)
    version = IntField(default=1)


class Entry(Document):
    """Base information shared by all entries.

    name -- Short name
    description -- Longer description
    metadata -- Catalogue metadata

    """
    name = StringField(required=True)
    description = StringField()
    metadata = EmbeddedDocumentField(Metadata, required=True)

    meta = {
        # MongoEngine on pip doesn't support text indexes yet
        # 'indexes': [('$name', '$description')],
        'allow_inheritance': True
    }

    def type(self):
        return self._cls.split('.')[-1]


class License(EmbeddedDocument):
    name = StringField()
    url = URLField()


class Source(EmbeddedDocument):
    """Source for a scientific code.

    type -- Repository type (git, svn)
    url -- Repository url
    checkout -- Branch/tag to checkout (default 'master' for git)
    exec -- Optional setup script

    """
    type = StringField(choices=SOURCE_TYPES, required=True)
    url = URLField(required=True)
    checkout = StringField()
    exec = StringField()


class Dependency(EmbeddedDocument):
    """Dependency on an external package."""
    type = StringField(choices=DEPENDENCY_TYPES, required=True)
    name = StringField()
    version = StringField()
    path = StringField()


class Var(EmbeddedDocument):
    """Variable in a Solution template.

    name -- Placeholder name in the template
    label -- User friendly label
    description -- Additional help text
    type -- Variable type (int, double, string, random-int)
    values -- List of valid values
    min -- Minimum value
    max -- Maximum value
    step -- Increment between min and max

    """
    name = StringField(required=True)
    type = StringField(choices=VARIABLE_TYPES)
    label = StringField(max_length=50)
    description = StringField()
    optional = BooleanField(default=False)
    default = DynamicField()
    min = FloatField()
    max = FloatField()
    step = FloatField()
    values = ListField()


class Problem(Entry):
    """A problem to be solved.

    Requires nothing extra over Entry.

    """
    pass


class Toolbox(Entry):
    homepage = URLField()
    license = EmbeddedDocumentField(License)
    source = EmbeddedDocumentField(Source, required=True)
    dependencies = ListField(EmbeddedDocumentField(Dependency))


class Solution(Entry):
    problem = ReferenceField(Problem, required=True)
    toolbox = ReferenceField(Toolbox)
    template = StringField(required=True)
    variables = ListField(EmbeddedDocumentField(Var), required=True)
    depedencies = ListField(EmbeddedDocumentField(Dependency))
