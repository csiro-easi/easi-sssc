from flask import json
from peewee import *
from playhouse.sqlite_ext import FTSModel
from app import db
import datetime
import importlib


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

    Returns a list of entries that matched text.

    """
    matches = [r.problem for r in ProblemIndex.select().where(ProblemIndex.match(text))]
    matches.extend([r.solution for r in SolutionIndex.select().where(SolutionIndex.match(text))])
    matches.extend([r.toolbox for r in ToolboxIndex.select().where(ToolboxIndex.match(text))])
    return matches


class BaseModel(Model):
    class Meta:
        database = db


class User(BaseModel):
    """Catalogue user."""
    id = PrimaryKeyField()
    email = CharField(unique=True)
    name = CharField()

    def __unicode__(self):
        return self.name


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
    author = ForeignKeyField(User)
    version = IntegerField(default=1)

    def __unicode__(self):
        return "entry ({})".format(self.name)


class License(BaseModel):
    name = CharField(null=True)
    url = CharField(null=True)

    def __unicode__(self):
        return self.name if self.name else self.url


class Dependency(BaseModel):
    """Dependency on an external package."""
    type = CharField(choices=DEPENDENCY_TYPES)
    name = CharField(null=True)
    version = CharField(null=True)
    path = CharField(null=True)

    def __unicode__(self):
        return "({}) {}".format(self.type, self.name if self.name else self.path)


class Problem(Entry):
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

    def __unicode__(self):
        return "source ({}, {})".format(self.type, self.url)


class Toolbox(Entry):
    homepage = CharField(null=True)
    license = ForeignKeyField(License, related_name="toolboxes")
    source = ForeignKeyField(Source, related_name="toolboxes")


class ToolboxDependency(Dependency):
    entry = ForeignKeyField(Toolbox, related_name='dependencies')


class Image(BaseModel):
    provider = CharField()
    image_id = CharField()


class ToolboxImage(Image):
    toolbox = ForeignKeyField(Toolbox, related_name='images')
    sc_path = CharField(null=True)


class Solution(Entry):
    problem = ForeignKeyField(Problem, related_name="solutions")
    toolbox = ForeignKeyField(Toolbox, related_name="solutions")
    template = TextField()


class SolutionDependency(Dependency):
    entry = ForeignKeyField(Solution, related_name='dependencies')


class SolutionImage(Image):
    solution = ForeignKeyField(Solution, related_name='images')
    sc_path = CharField(null=True)


class JsonField(CharField):
    """Store JSON strings."""
    def db_value(self, value):
        """Return database value from python data structure."""
        if value is not None:
            return json.dumps(value)

    def python_value(self, value):
        """Return python data structure from json string in the db."""
        if value is not None:
            return json.loads(value)


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
    solution = ForeignKeyField(Solution, related_name="variables")

    def __unicode__(self):
        return "var {} ({})".format(self.name, self.type)


class VarValue(BaseModel):
    """Valid values for a variable.

    Values are serialized as json strings in the database.

    """
    var = ForeignKeyField(Var, related_name='values')
    value = JsonField()


class BaseIndexModel(FTSModel):
    name = TextField()
    description = TextField()

    class Meta:
        database = db


class ProblemIndex(BaseIndexModel):
    """Store text content from other entries for searching."""
    problem = ForeignKeyField(Problem)


class SolutionIndex(BaseIndexModel):
    """Store text content from other entries for searching."""
    solution = ForeignKeyField(Solution)


class ToolboxIndex(BaseIndexModel):
    """Store text content from other entries for searching."""
    toolbox = ForeignKeyField(Toolbox)


def index_entry(entry):
    """Add entry to the appropriate text index."""
    entry_type = type(entry).__name__
    cls = getattr(importlib.import_module(__name__),
                  entry_type + 'Index')
    if cls:
        obj = cls(name=entry.name, description=entry.description)
        field = entry_type[0].lower() + entry_type[1:]
        setattr(obj, field, entry)
        obj.save()


_TABLES = [User, License, Problem, Toolbox, ToolboxDependency, Solution,
           SolutionDependency, Var, VarValue, Source, ToolboxImage,
           SolutionImage]
_INDEX_TABLES = [ProblemIndex, SolutionIndex, ToolboxIndex]


def create_database(db, safe=True):
    """Create the database for our models."""
    db.create_tables(_TABLES, safe=safe)
    db.create_tables(_INDEX_TABLES, safe=safe)


def drop_tables(db):
    """Drop the model tables."""
    db.drop_tables(_INDEX_TABLES, safe=True)
    db.drop_tables(_TABLES, safe=True)
