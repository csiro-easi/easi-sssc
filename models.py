from flask import json
from peewee import BooleanField, BlobField, CharField, DateTimeField, \
    DoubleField, ForeignKeyField, IntegerField, PrimaryKeyField, \
    TextField, Model
# Use the ext database to get FTS support
# from peewee import SqliteDatabase
from playhouse.sqlite_ext import FTSModel, SqliteExtDatabase
from flask_security import UserMixin, RoleMixin, current_user
from datetime import datetime
import importlib
import hashlib
import requests
from app import app

# Import the configured hash function from hashlib
hash_fn = getattr(hashlib, app.config['ENTRY_HASH_FUNCTION'])

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


def clone_model(model):
    """Create and return a clone of model.

    Save a clone of entry in the database, including all reverse relations
    (Vars, Deps etc).

    """
    # Copy current data
    data = dict(model._data)
    # clear the primary key
    data.pop(model._meta.primary_key.name)
    # Create the new entry
    # TODO handle unique id/entry combo!
    copy = type(model).create(**data)
    # Update references in copied relations to point to the clone
    for n, f in copy._meta.reverse_rel.items():
        for x in getattr(copy, n):
            setattr(x, f.name, copy)
    copy.save()
    return copy


class BaseModel(Model):
    def _include_in_hash(self, f):
        """Return True if f is the name of a field that should be included in the hash."""
        return True

    def _hash_data(self):
        """Return a sequence of hashable data."""
        data = self._data.copy()
        # Sort by field name so we have a deterministic order
        hashable = [repr(data.get(f)).encode()
                    for f in sorted(filter(self._include_in_hash, data))]
        # Then add fields from child entities
        for f in sorted(self._meta.reverse_rel):
            if self._include_in_hash(f):
                child = getattr(self, f)
                if child:
                    hashable += child._hash_data()
        return hashable

    class Meta:
        database = db


class Role(BaseModel, RoleMixin):
    """Auth role"""
    id = PrimaryKeyField()
    name = CharField(unique=True)
    description = TextField(null=True)

    def __unicode__(self):
        return self.name


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


class Signature(BaseModel):
    """Stores signed digests for entries.

    If a digest has been signed, the entry in this table must include the
    user_id of the user that signed it, and the key they used.

    """
    digest = BlobField()
    created_at = DateTimeField(default=datetime.now)
    user_id = ForeignKeyField(User, null=True)
    user_key = CharField(null=True)


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
    created_at = DateTimeField(default=datetime.now)
    version = IntegerField(default=1)
    keywords = TextField(null=True)
    entry_hash = BlobField()

    def _include_in_hash(self, f):
        # Don't include versions, signatures or self references (latest)
        return f not in ('versions', 'signatures', 'latest', 'entry_hash')

    def _check_resources(self, resources=None):
        """Check any resources, update any that have changed.

        Returns a list of (field, url) for any resources that have changed
        since they were last checked.

        """
        changed = []
        if resources:
            for rfield, hfield in resources:
                url = getattr(self, rfield)
                old_hash = getattr(self, hfield)
                r = requests.get(url)
                new_hash = hash_fn(r.content).digest()
                if new_hash != old_hash:
                    changed.append((rfield, url))
                    setattr(self, rfield, new_hash)
        return changed

    def update_metadata(self, is_created=False):
        """Update metadata for this model, including versioning and authorship.

        """
        # If we have no id, or is_created = True, just set the author.
        if is_created or self.id is None:
            self.author = current_user.id
        else:
            # Find the old state of entry in the db
            E = self._meta.model_class
            old_entry = E.get(E.id == self.id)
            # Clone the old state into a historical version, and link it back to
            # the latest entry.
            clone = clone_model(old_entry)
            clone.latest = self.id
            clone.save()
            # Increment the version on the latest entry, and the timestamp
            self.version = self.version + 1
            self.created_at = datetime.now()
            # Compute and set the new hash for this entry
            entry_hash = hash_fn()
            for data in self._hash_data():
                entry_hash.update(data)
            self.entry_hash = entry_hash.digest()
        # Check resources at this point
        self._check_resources()

    def __unicode__(self):
        return "entry ({})".format(self.name)


class License(BaseModel):
    name = CharField(unique=True)
    url = CharField(null=True)
    text = TextField(null=True)

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
    author = ForeignKeyField(User)
    latest = ForeignKeyField('self', null=True, related_name='versions')


class ProblemSignature(BaseModel):
    """Signatures for Problems."""
    problem = ForeignKeyField(Problem, related_name="signatures")
    signature = ForeignKeyField(Signature, unique=True)


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
    author = ForeignKeyField(User)
    latest = ForeignKeyField('self', null=True, related_name='versions')
    homepage = CharField(null=True)
    license = ForeignKeyField(License, related_name="toolboxes")
    source = ForeignKeyField(Source, null=True, related_name="toolboxes")
    command = CharField(
        null=True,
        help_text=("Command line template for executing a Solution using this"
                   " Toolbox.")
    )
    puppet = CharField(
        null=True,
        help_text="Puppet module that instantiates this Toolbox."
    )
    puppet_hash = BlobField()

    def _include_in_hash(self, f):
        if f == 'puppet_hash':
            return False
        return super()._include_in_hash(f)


class ToolboxSignature(BaseModel):
    """Signatures for Toolboxs."""
    toolbox = ForeignKeyField(Toolbox, related_name="signatures")
    signature = ForeignKeyField(Signature, unique=True)


class ToolboxDependency(Dependency):
    """External dependencies for Toolboxes."""
    toolbox = ForeignKeyField(Toolbox, related_name="deps")


class ToolboxImage(Image):
    """Image/snapshot published at a provider that instantiates a Toolbox.

    toolbox -- Toolbox that this Image provides
    """
    toolbox = ForeignKeyField(Toolbox, related_name="images")


class Solution(Entry):
    author = ForeignKeyField(User)
    latest = ForeignKeyField('self', null=True, related_name='versions')
    problem = ForeignKeyField(Problem, related_name="solutions")
    runtime = CharField(choices=RUNTIME_CHOICES, default="python")
    template = CharField(help_text="URL of template that implements this Solution.")
    template_hash = BlobField()

    def _include_in_hash(self, f):
        if f == 'template_hash':
            return False
        return super()._include_in_hash(f)


class SolutionSignature(BaseModel):
    """Signatures for Solutions."""
    solution = ForeignKeyField(Solution, related_name="signatures")
    signature = ForeignKeyField(Signature, unique=True)


class SolutionDependency(Dependency):
    solution = ForeignKeyField(Solution, related_name="deps")


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
