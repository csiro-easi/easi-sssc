from datetime import datetime
import hashlib
import importlib
import requests
from flask import json
from peewee import BooleanField, CharField, DateTimeField, \
    DoubleField, ForeignKeyField, IntegerField, PrimaryKeyField, \
    TextField, Model
# Use the ext database to get FTS support
# from peewee import SqliteDatabase
from playhouse.sqlite_ext import FTSModel, SqliteExtDatabase
from flask_security import UserMixin, RoleMixin, current_user
from rdflib.namespace import RDF
from app import app
from namespaces import PROV, SSSC, rdf_graph

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


resource_hash = getattr(hashlib, app.config['RESOURCE_HASH_FUNCTION'])


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


def user_entries(user):
    """Return a list of all entries created by user."""
    entries = []
    entries.extend(p for p in user.problems)
    entries.extend(t for t in user.toolboxes)
    entries.extend(s for s in user.solutions)
    return entries


def is_latest(entry):
    """Return True if entry is the latest version."""
    return entry.latest is None or entry.latest.id == entry.id


class BaseModel(Model):
    """Base of all application models.

    Sets database connection.
    Base semantic description functionality.

    """
    _semantic_types = []

    def semantic_types(self, subject):
        """Return an RDF graph describing an instnace of this model.

        Subject is a BNode or URIRef.

        """
        g = rdf_graph()
        g.add((subject, RDF.type, SSSC[type(self).__name__]))
        for t in self._semantic_types:
            g.add((subject, RDF.type, t))
        return g

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

    entries = property(user_entries)

    public_key = property(
        lambda self: self._get_public_key()
    )

    _semantic_types = [PROV.Agent, PROV.Person]

    def _get_public_key(self):
        try:
            return self.public_keys.order_by(
                PublicKey.registered_at.desc()
            ).get()
        except Exception:
            return None

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


class PublicKey(BaseModel):
    """Public keys registered with a User."""
    user = ForeignKeyField(User, related_name="public_keys")
    registered_at = DateTimeField(default=datetime.now)
    key = TextField()


class Signature(BaseModel):
    """Stores signed digests for entries.

    If a digest has been signed, the entry in this table must include the
    user_id of the user that signed it, and the key they used.

    """
    signature = CharField()
    signed_string = TextField()
    created_at = DateTimeField(default=datetime.now)
    user_id = ForeignKeyField(User, null=True, related_name='signatures')
    public_key = ForeignKeyField(PublicKey, related_name='signatures')

    entry = property(lambda self: self.get_entry_rel().entry)

    def get_entry_rel(self):
        """Return the Entry relation this is a signature for."""
        if self.problemsignature_set.count() == 1:
            return self.problemsignature_set[0]
        if self.toolboxsignature_set.count() == 1:
            return self.toolboxsignature_set[0]
        if self.solutionsignature_set.count() == 1:
            return self.solutionsignature_set[0]
        return None


class ResourceCheck(object):
    """Stores the results of a resources check for an Entry.

    Changes is a list that will contain a (field, url) pair for each field that
    has changed since it was last checked.

    Errors is a list of (field, errors) tuples for fields that caused
    exceptions when they were checked.

    """
    def __init__(self):
        self.checks = []

    def succeeded(self):
        """Return True if all checks succeeded."""
        return all(check['errors'] is None for check in self.checks)

    def add_check(self, field, url, is_changed=False, errors=None):
        """Add a check result for field/url."""
        self.checks.append(dict(field=field, url=url, is_changed=is_changed,
                                errors=errors))

    def get_changed(self):
        """Return the checks that indicated the value changed."""
        return (check for check in self.checks if check['is_changed'])

    def get_errors(self):
        """Return the checks that raised errors."""
        return (check for check in self.checks if check['errors'])


class Entry(BaseModel):
    """Base information shared by all entries.

    name -- Short name
    description -- Longer description
    created_at -- Datetime this Entry was added to the catalogue
    author -- Who created this Entry
    version -- Version number for this Entry
    entry_hash -- Auto-generated hash of entry content
    published -- Flag indicating visibility status

    """
    id = PrimaryKeyField()
    name = CharField()
    description = TextField()
    created_at = DateTimeField(default=datetime.now)
    version = IntegerField(default=1)
    entry_hash = CharField(null=True)
    published = BooleanField(default=app.config['PUBLISH_DEFAULT'])

    entry_id = property(lambda self: self.latest.id
                        if self.latest is not None
                        else None)

    _semantic_types = [PROV.Entity]

    def check_resources(self, resources=None):
        """Check any resources, update any that have changed.

        Returns a ResourceCheck object with the results of the checks.

        """
        checks = ResourceCheck()
        if resources:
            for rfield, hfield in resources:
                url = getattr(self, rfield)

                # Handle an empty resource field. Ignore it if it's nullable,
                # otherwise raise an error since validation has failed
                # somewhere.
                if not url:
                    if self._meta.fields.get(rfield).null:
                        continue
                    else:
                        raise ValueError('Required resource field {} of {} is emptry.'
                                         .format(rfield, type(self).__name__))

                old_hash = getattr(self, hfield)
                new_hash = None
                is_changed = None
                errors = None
                try:
                    req = requests.get(url, timeout=app.config['RESOURCE_TIMEOUT'])
                except requests.exceptions.RequestException as e:
                    errors = [e]
                else:
                    new_hash = resource_hash(req.content).hexdigest()
                    is_changed = new_hash != old_hash
                    if is_changed:
                        setattr(self, hfield, new_hash)
                checks.add_check(rfield, url, is_changed, errors)
        return checks

    def update_metadata(self, is_created=False):
        """Update metadata for this model, including versioning and authorship.

        """
        # If it's a new entry, just set the author.
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

    def __unicode__(self):
        return "entry ({})".format(self.name)


class Tag(BaseModel):
    tag = CharField()


class License(BaseModel):
    name = CharField(unique=True)
    url = CharField(null=True)
    text = TextField(null=True)

    _semantic_types = [PROV.Entity]

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
    author = ForeignKeyField(User, related_name='problems')
    latest = ForeignKeyField('self', null=True, related_name='versions')


class ProblemTag(Tag):
    entry = ForeignKeyField(Problem, related_name='tags')


class ProblemSignature(BaseModel):
    """Signatures for Problems."""
    problem = ForeignKeyField(Problem, related_name="signatures")
    signature = ForeignKeyField(Signature, unique=True, on_delete='CASCADE')
    entry = property(lambda self: self.problem)


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
    author = ForeignKeyField(User, related_name='toolboxes')
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
    puppet_hash = CharField(null=True)

    def check_resources(self, resources=None):
        resources = resources or [('puppet', 'puppet_hash')]
        return super().check_resources(resources)


class ToolboxTag(Tag):
    entry = ForeignKeyField(Toolbox, related_name='tags')


class ToolboxSignature(BaseModel):
    """Signatures for Toolboxs."""
    toolbox = ForeignKeyField(Toolbox, related_name="signatures")
    signature = ForeignKeyField(Signature, unique=True, on_delete='CASCADE')
    entry = property(lambda self: self.toolbox)


class ToolboxDependency(Dependency):
    """External dependencies for Toolboxes."""
    toolbox = ForeignKeyField(Toolbox, related_name="deps")


class ToolboxImage(Image):
    """Image/snapshot published at a provider that instantiates a Toolbox.

    toolbox -- Toolbox that this Image provides
    """
    toolbox = ForeignKeyField(Toolbox, related_name="images")


class Solution(Entry):
    author = ForeignKeyField(User, related_name='solutions')
    latest = ForeignKeyField('self', null=True, related_name='versions')
    problem = ForeignKeyField(Problem, related_name="solutions")
    runtime = CharField(choices=RUNTIME_CHOICES, default="python")
    template = CharField(help_text="URL of template that implements this Solution.")
    template_hash = CharField(null=True)

    _semantic_types = [PROV.Entity, PROV.Plan]

    def check_resources(self, resources=None):
        resources = resources or [('template', 'template_hash')]
        return super().check_resources(resources)


class SolutionTag(Tag):
    entry = ForeignKeyField(Solution, related_name='tags')


class SolutionSignature(BaseModel):
    """Signatures for Solutions."""
    solution = ForeignKeyField(Solution, related_name="signatures")
    signature = ForeignKeyField(Signature, unique=True, on_delete='CASCADE')
    entry = property(lambda self: self.solution)


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


_TABLES = [User, Role, UserRoles, License, Problem, Toolbox, Signature,
           ToolboxDependency, Solution, SolutionDependency, PublicKey,
           ToolboxVar, SolutionVar, Source, SolutionImage,
           ToolboxImage, ProblemSignature, ToolboxSignature, SolutionSignature,
           ProblemTag, ToolboxTag, SolutionTag]
_INDEX_TABLES = [ProblemIndex, SolutionIndex, ToolboxIndex]


def create_database(db, safe=True):
    """Create the database for our models."""
    db.create_tables(_TABLES, safe=safe)
    db.create_tables(_INDEX_TABLES, safe=safe)


def drop_tables(db):
    """Drop the model tables."""
    db.drop_tables(_INDEX_TABLES, safe=True)
    db.drop_tables(_TABLES, safe=True)
