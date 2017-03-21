from flask import json
from peewee import BooleanField, CharField, DateTimeField, CompositeKey, \
    DoubleField, ForeignKeyField, IntegerField, Model, PrimaryKeyField, \
    TextField
# Use the ext database to get FTS support
# from peewee import SqliteDatabase
from playhouse.sqlite_ext import FTSModel, SqliteExtDatabase
from flask_security import UserMixin, RoleMixin
import datetime
import importlib
from app import app


# Valid source repositories
SOURCE_TYPES = (('git', 'GIT repository'),
                ('svn', 'Subversion repository'))

# Types of external dependencies we can resolve
DEPENDENCY_TYPES = (('puppet', 'Puppet module from forge-style repository'),
                    ('requirements',
                     'Requirements file with python packages from pypi'),
                    ('python', 'Python package from pypi'),
                    ('hpc', 'HPC style module for Raijin and similar systems'),
                    ('toolbox',
                     'A Toolbox in this, or another, solution centre'))

# Variable types for solutions
VARIABLE_TYPES = (('int', 'Integer'),
                  ('double', 'Floating point'),
                  ('string', 'String'),
                  ('random-int', 'Random Integer'),
                  ('file', 'Input dataset'))

# Database set up
db = SqliteExtDatabase(app.config['SQLITE_DB_FILE'],
                       threadlocals=True)
#                       journal_mode='WAL')

# Runtime choices for solution templates
RUNTIME_CHOICES = (('python2', 'Latest Python 2.x'),
                   ('python3', 'Latest Python 3.x'),
                   ('python', 'Latest Python 2 or 3'))


def text_search(text):
    """Search for entries that match text.

    Returns a list of entries that matched text.

    """
    matches = [r.problem for r in
               ProblemIndex.select().where(ProblemIndex.match(text))]
    matches.extend([r.solution for r in
                    SolutionIndex.select().where(SolutionIndex.match(text))])
    matches.extend([r.toolbox for r in
                    ToolboxIndex.select().where(ToolboxIndex.match(text))])
    return matches


class BaseModel(Model):
    class Meta:
        database = db


class Role(BaseModel, RoleMixin):
    """Auth role"""
    id = PrimaryKeyField()
    name = CharField(unique=True)
    description = TextField(null=True)


class User(BaseModel, UserMixin):
    """Catalogue user."""
    id = PrimaryKeyField()
    email = CharField(unique=True)
    password = TextField()
    name = CharField()
    active = BooleanField(default=True)
    confirmed_at = DateTimeField(null=True)

    def __unicode__(self):
        return self.name


class UserRoles(BaseModel):
    """Many-to-many relationship between Users and Roles."""
    user = ForeignKeyField(User, related_name='roles')
    role = ForeignKeyField(Role, related_name='users')
    name = property(lambda self: self.role.name)
    description = property(lambda self: self.role.description)

    class Meta:
        indexes = (
            # user/role pairs should be unique
            (('user', 'role'), True),
        )


class Entry(BaseModel):
    """Base information shared by all entries.

    name -- Short name
    description -- Longer description
    created_at -- Datetime this Entry was added to the catalogue
    author -- Who created this Entry
    version -- Version number for this Entry
    keywords -- Space separated list of keywords describing this Entry

    """
    id = PrimaryKeyField()
    name = CharField()
    description = TextField()
    created_at = DateTimeField(default=datetime.datetime.now)
    author = ForeignKeyField(User)
    version = IntegerField(default=1)
    keywords = TextField(null=True)

    def __unicode__(self):
        return "entry ({})".format(self.name)


class License(BaseModel):
    name = CharField(null=True)
    url = CharField(null=True)

    def __unicode__(self):
        return self.name if self.name else self.url


class Dependency(BaseModel):
    """Dependency on external python packages or a puppet module.

    For types that resolve to a single endpoint (python requirements document),
    identifier is an URL. Other types (puppet module, python dependency) use
    identifier for the name of the module or package, with optional version and
    repository attached.

    """
    id = PrimaryKeyField()
    type = CharField(choices=DEPENDENCY_TYPES)
    identifier = CharField()
    version = CharField(null=True)
    repository = CharField(null=True)

    def __unicode__(self):
        return "({}) {}".format(self.type, self.identifier)


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
    setup -- Optional setup script

    """
    type = CharField(choices=SOURCE_TYPES)
    url = CharField()
    checkout = CharField(null=True)
    setup = TextField(null=True)

    def __unicode__(self):
        return "source ({}, {})".format(self.type, self.url)


class Image(BaseModel):
    """Image/snapshot at a provider.

    provider -- Cloud (or other) provider of this image
    image_id -- Identifier for this image
    """
    provider = CharField()
    image_id = CharField()


class Toolbox(Entry):
    """Environment for running a specific model or software package.

    """
    homepage = CharField(null=True)
    license = ForeignKeyField(License, related_name="toolboxes")
    source = ForeignKeyField(Source, null=True, related_name="toolboxes")
    puppet = CharField(
        null=True,
        help_text="URL of a Puppet script that will instantiate this Toolbox."
    )
    command = CharField(
        null=True,
        help_text=("Command line template for executing a Solution using this"
                   " Toolbox.")
    )


class ToolboxDependency(Dependency):
    """External dependencies for Toolboxes."""
    toolbox = ForeignKeyField(Toolbox, related_name="dependencies")


class ToolboxImage(Image):
    """Image/snapshot published at a provider that instantiates a Toolbox.

    toolbox -- Toolbox that this Image provides
    """
    toolbox = ForeignKeyField(Toolbox, related_name="images")


class Solution(Entry):
    problem = ForeignKeyField(Problem, related_name="solutions")
    template = CharField()
    runtime = CharField(choices=RUNTIME_CHOICES, default="python")


class SolutionDependency(Dependency):
    solution = ForeignKeyField(Solution, related_name="dependencies")


class SolutionImage(Image):
    """Image/snapshot that provides a pre-canned environment for a Solution.


    solution -- Solution provided by this Image
    """
    solution = ForeignKeyField(Solution, related_name="images")


class JsonField(CharField):
    """Store JSON strings."""
    def db_value(self, value):
        """Return database value from python data structure."""
        if value is not None:
            return json.dumps(value)

    def python_value(self, value):
        """Return python data structure from json string in the db."""
        if value is not None and value != '':
            return json.loads(value)


class Var(BaseModel):
    """Variable in a Solution template or Toolbox instance.

    name -- Placeholder name in the template
    label -- User friendly label
    description -- Additional help text
    type -- Variable type (int, double, string, random-int)
    optional -- True if optional
    values -- List of valid values
    min -- Minimum value
    max -- Maximum value
    step -- Increment between min and max
    solution -- Solution this Var belongs to

    """
    name = CharField()
    type = CharField(choices=VARIABLE_TYPES)
    label = CharField(null=True)
    description = TextField(null=True)
    optional = BooleanField(default=False)
    default = JsonField(null=True)
    min = DoubleField(null=True)
    max = DoubleField(null=True)
    step = DoubleField(null=True)
    values = JsonField(null=True)

    def __unicode__(self):
        return "var {} ({})".format(self.name, self.type)


class SolutionVar(Var):
    """Variable in a Solution."""
    solution = ForeignKeyField(Solution, related_name="variables")


class ToolboxVar(Var):
    """Variable in a Toolbox"""
    toolbox = ForeignKeyField(Toolbox, related_name="variables")


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
        field = entry_type.lower()
        setattr(obj, field, entry)
        obj.save()


_TABLES = [User, Role, UserRoles, License, Problem, Toolbox,
           ToolboxDependency, Solution, SolutionDependency,
           ToolboxVar, SolutionVar, Source, SolutionImage,
           ToolboxImage]
_INDEX_TABLES = [ProblemIndex, SolutionIndex, ToolboxIndex]


def create_database(db, safe=True):
    """Create the database for our models."""
    db.create_tables(_TABLES, safe=safe)
    db.create_tables(_INDEX_TABLES, safe=safe)


def drop_tables(db):
    """Drop the model tables."""
    db.drop_tables(_INDEX_TABLES, safe=True)
    db.drop_tables(_TABLES, safe=True)
