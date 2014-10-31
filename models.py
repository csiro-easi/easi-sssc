import datetime
# from mongoengine import *
from peewee import *
from playhouse.sqlite_ext import FTSModel
from app import db


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

    Returns instances of TextContent (entry, name, description) that
    matched.

    """
    return TextContent.select().where(TextContent.match(text))


# def pymongo_find(query):
#     """Performs a find(query) using the PyMongo connection directly.

#     Wraps the dict results in model instances before returning them.

#     """
#     results = Entry._get_collection().find(query, fields="_id")
#     if results:
#         return Entry.objects(id__in=[result['_id'] for result in results])


class BaseModel(Model):
    class Meta:
        database = db

    def to_dict(self):
        j = dict()
        for k in self._data.keys():
            v = getattr(self, k)
            if isinstance(v, BaseModel):
                v = v.to_dict()
            j[k] = v
        if 'type' not in j:
            j['type'] = self.type()
        return j

    def type(self):
        return type(self).__name__


class User(BaseModel):
    """Catalogue user."""
    id = PrimaryKeyField()
    email = CharField(unique=True)
    name = CharField()


# class Metadata(EmbeddedDocument):
#     """Metadata for all catalogue entries."""


class Entry(BaseModel):
    """Base information shared by all entries.

    name -- Short name
    description -- Longer description
    metadata -- Catalogue metadata

    """
    id = PrimaryKeyField()
    name = CharField()
    description = TextField()
    created_at = DateTimeField(default=datetime.datetime.now)
    author = ForeignKeyField(User, related_name="entries")  # , required=True)
    version = IntegerField(default=1)

    def specific_entry(self):
        """Return the instance for the specific entry for this Entry."""
        # Look for the EntryMixin
        for cls in EntryMixin.__subclasses__():
            try:
                return cls.get(cls.entry == self)
            except DoesNotExist:
                continue


class EntryMixin(BaseModel):
    entry = ForeignKeyField(Entry)

    def to_dict(self):
        d = super().to_dict()
        for x in ['name', 'description', 'author', 'version', 'created_at',
                  'dependencies']:
            if x in d['entry']:
                d[x] = d['entry'][x]
        del d['entry']
        return d

    def specific_entry(self):
        """Return this instance."""
        return self

    """Delegate Entry property access to the entry field instance."""
    def getName(self):
        return self.entry.name

    def setName(self, name):
        self.entry.name = name

    name = property(getName, setName)

    def getDescription(self):
        return self.entry.description

    def setDescription(self, description):
        self.entry.description = description

    description = property(getDescription, setDescription)

    def getCreated_At(self):
        return self.entry.created_at

    def setCreated_At(self, created_at):
        self.entry.created_at = created_at

    created_at = property(getCreated_At, setCreated_At)

    def getAuthor(self):
        return self.entry.author

    def setAuthor(self, author):
        self.entry.author = author

    author = property(getAuthor, setAuthor)

    def getVersion(self):
        return self.entry.version

    def setVersion(self, version):
        self.entry.version = version

    version = property(getVersion, setVersion)

    def getDependencies(self):
        return self.entry.dependencies

    def setDependencies(self, dependencies):
        self.entry.dependencies = dependencies

    dependencies = property(getDependencies, setDependencies)


class License(BaseModel):
    name = CharField(null=True)
    url = CharField(null=True)


class Dependency(BaseModel):
    """Dependency on an external package."""
    type = CharField(choices=DEPENDENCY_TYPES)
    name = CharField(null=True)
    version = CharField(null=True)
    path = CharField(null=True)
    entry = ForeignKeyField(Entry, related_name="dependencies")


class Problem(EntryMixin):
    """A problem to be solved.

    Requires nothing extra over Entry.

    """
    pass


class Source(BaseModel):
    """Source for a scientific code.

    type -- Repository type (git, svn)
    url -- Repository url
    checkout -- Branch/tag to checkout (default 'master' for git)
    exec -- Optional setup script

    """
    type = CharField(choices=SOURCE_TYPES)
    url = CharField()
    checkout = CharField(null=True)
    exec = TextField(null=True)


class Toolbox(EntryMixin):
    homepage = CharField(null=True)
    license = ForeignKeyField(License, related_name="toolboxes")
    source = ForeignKeyField(Source, related_name="toolboxes")


class Solution(EntryMixin):
    problem = ForeignKeyField(Problem, related_name="solutions")
    toolbox = ForeignKeyField(Toolbox, related_name="solutions")
    template = TextField()


class Var(BaseModel):
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
    name = CharField()
    type = CharField(choices=VARIABLE_TYPES)
    label = CharField(null=True)
    description = TextField(null=True)
    optional = BooleanField(default=False)
    default = CharField(null=True)
    min = DoubleField(null=True)
    max = DoubleField(null=True)
    step = DoubleField(null=True)
    values = CharField(null=True)
    solution = ForeignKeyField(Solution, related_name="variables")


class TextContent(FTSModel):
    """Store text content from other entries for searching."""
    name = TextField()
    description = TextField()
    entry = ForeignKeyField(Entry)

    class Meta:
        database = db

    def add_entry(entry):
        """Add the text index for entry."""
        TextContent.create(
            name=entry.name,
            description=entry.description,
            entry=entry
        )


_TABLES = [User, Entry, License, Dependency, Problem, Toolbox, Solution, Var,
           Source]


def create_database(db, safe=True):
    """Create the database for our models."""
    db.create_tables(_TABLES, safe=safe)
    TextContent.create_table()

def drop_tables(db):
    """Drop the model tables."""
    db.drop_tables(_TABLES, safe=True)
    TextContent.drop_table(fail_silently=True)
