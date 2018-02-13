from datetime import datetime
from functools import partial
import hashlib
import importlib
import requests
from flask import json
from peewee import BooleanField, CharField, DateTimeField, \
    DoubleField, ForeignKeyField, IntegerField, PrimaryKeyField, \
    TextField, Model
# Use the ext database to get FTS support
# from peewee import SqliteDatabase
from playhouse.sqlite_ext import FTSModel, SqliteExtDatabase, \
    SearchField
from flask_security import UserMixin, RoleMixin, current_user
from sssc import api
from .app import app

# Valid source repositories
SOURCE_TYPES = (('git', 'GIT repository'),
                ('svn', 'Subversion repository'))

# Types of external dependencies we can resolve
DEPENDENCY_TYPES = (('puppet', 'Puppet module from forge-style repository'),
                    ('requirements',
                     'Requirements file with python packages from pypi'),
                    ('python', 'Python package from pypi'),
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


def text_search(text, latest_only=True):
    """Search for entries that match text.

    Returns a dict of entries that matched text. By default only the latest
    versions that match are returned. If latest_only is False then all matching
    versions will be returned.

    """
    def constraint(cls, index):
        c = index.match(text)
        if latest_only:
            c = c & cls.latest.is_null()
        return c

    results = dict(problems=[], toolboxes=[], solutions=[])

    if text:
        results["problems"] = (Problem
                               .select()
                               .join(ProblemIndex,
                                     on=(Problem.id == ProblemIndex.docid))
                               .where(constraint(Problem, ProblemIndex))
                               .order_by(ProblemIndex.bm25()))
        results["toolboxes"] = (Toolbox
                                .select()
                                .join(ToolboxIndex,
                                      on=(Toolbox.id == ToolboxIndex.docid))
                                .where(constraint(Toolbox, ToolboxIndex))
                                .order_by(ToolboxIndex.bm25()))
        results["solutions"] = (Solution
                                .select()
                                .join(SolutionIndex,
                                      on=(Solution.id == SolutionIndex.docid))
                                .where(constraint(Solution, SolutionIndex))
                                .order_by(SolutionIndex.bm25()))
    return results


_rels_ignored_for_cloning = frozenset({
    'versions',
    'problemindex_set',
    'solutionindex_set',
    'toolboxindex_set',
    'signatures',
    'solutions'
})


def clone_model(model):
    """Create and return a clone of model.

    Save a clone of entry in the database, including all reverse relations
    (Vars, Deps etc).

    """
    # Copy current data and clean the primary key and creation time so new ones
    # are assigned.
    data = dict(model._data)
    data.pop(model._meta.primary_key.name)

    # Create the new entry
    # TODO handle unique id/entry combo!
    copy = type(model).create(**data)

    # Copy all child instances and point the copies at the clone.
    for rel_name, fk_field in model._meta.reverse_rel.items():
        # Ignore known relations.
        if rel_name not in _rels_ignored_for_cloning:
            for rel_instance in getattr(model, rel_name):
                child = clone_model(rel_instance)
                setattr(child, fk_field.name, copy)
                child.save()

    # Return the copy
    return copy


def user_entries(user):
    """Return a list of all entries created by user."""
    entries = []
    entries.extend(p for p in user.problems)
    entries.extend(t for t in user.toolboxes)
    entries.extend(s for s in user.solutions)
    return entries


def is_latest(entry):
    """Return True if entry is the latest version.

    Latest field should be NULL for the latest version, but old instances might
    have the latest field set to their own id instead, so check for that.

    """
    return entry.latest is None or entry.latest.id == entry.id


def is_unpublished(entry):
    """Return True if entry is unpublished."""
    if entry:
        return not entry.published


class BaseModel(Model):
    """Base of all application models.

    Sets database connection.
    """
    class Meta:
        database = db


class Role(BaseModel, RoleMixin):
    """Auth role"""
    id = PrimaryKeyField()
    name = CharField(unique=True)
    description = TextField(null=True)

    def __unicode__(self):
        return self.name

    def __str__(self):
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

    def _get_public_key(self):
        """Return the current (most recent) public key."""
        try:
            return self.public_keys.order_by(
                PublicKey.registered_at.desc()
            ).get()
        except Exception:
            return None

    def __unicode__(self):
        return self.name

    def __str__(self):
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
    icon -- URL of an image suitable for use as an icon

    """
    id = PrimaryKeyField()
    name = CharField()
    description = TextField()
    created_at = DateTimeField(default=datetime.now)
    version = IntegerField(default=1)
    entry_hash = CharField(null=True)
    published = BooleanField(default=app.config['PUBLISH_DEFAULT'])
    icon = CharField(null=True)

    entry_id = property(
        lambda self: self.id if self.latest is None else self.latest.id
    )

    @api.expose(sense='child')
    @property
    def reviews(self):
        """Return reviews for this Entry."""
        query = []
        if (hasattr(self, 'problemreview_set') and
            self.problemreview_set.count() > 0):
            query = self.problemreview_set
        elif (hasattr(self, 'toolboxreview_set') and
              self.toolboxreview_set.count() > 0):
            query = self.toolboxreview_set
        elif (hasattr(self, 'solutionreview_set') and
              self.solutionreview_set.count() > 0):
            query = self.solutionreview_set
        return [rel.review for rel in query]

    # Fields that do not cause a version change when they are changed.
    _ignored_dirty_fields = frozenset({
        'published'
    })

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

    def is_version_bump_required(self):
        """Return True if a new version of this entry must be created.

        Depends on checking for dirty fields for pending changes to this model,
        so must be called before the model is saved.

        """
        return not self._dirty.issubset(self._ignored_dirty_fields)

    def update_metadata(self, is_created=False):
        """Update metadata for a new entry.

        """
        # If it's a new entry, just set the author.
        if is_created or self.id is None:
            self.author = current_user.id
        elif self.is_version_bump_required():
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

    def __str__(self):
        return "entry ({})".format(self.name)


class UploadedResource(BaseModel):
    """Store, and serve, an uploaded file."""
    filename = CharField()
    name = CharField()
    uploaded_at = DateTimeField(default=datetime.now)
    published = BooleanField(default=app.config['PUBLISH_DEFAULT'])
    user = ForeignKeyField(User, related_name="uploads")


class Tag(BaseModel):
    tag = CharField()


class License(BaseModel):
    name = CharField(unique=True)
    url = CharField(null=True)
    text = TextField(null=True)

    def __unicode__(self):
        return self.name if self.name else self.url

    def __str__(self):
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

    def __str__(self):
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

    def __str__(self):
        return "source ({}, {})".format(self.type, self.url)


class Image(BaseModel):
    """Image/snapshot at a provider.

    provider -- Cloud (or other) provider of this image
    image_id -- Identifier for this image
    command -- Optional wrapper command required when running on this image
    """
    provider = CharField()
    image_id = CharField()
    command = CharField(
        null=True,
        help_text=("When running on this Image, override the command-line "
                   "template (if any) for executing a Solution using this "
                   "Toolbox.")
    )


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


class Application(Entry):
    """An application that can implement a Solution.

    This is a generic concept, used to represent both bespoke applications that
    are the implementation of a specific Solution and applications that are
    clients for the SSSC and are able to run arbitrary solutions (e.g. the
    Virtual Geophysics Laboratory).

    homepage -- The URL to the home or landing page for the application, which
    could open the app itself, be the place to download it, or otherwise
    provide information about how to access it.

    url_template -- Template that can be used to invoke a web-based application
    with a specific solution. This should be a string containing a single
    instance of the substring '%s' where the solution URI should be
    substituted. Note that the url template should not be url encoded before
    being stored.

    """
    author = ForeignKeyField(User, related_name='applications')
    homepage = CharField(
        help_text='URL to the home/landing page for the application.'
    ),
    url_template = CharField(
        null=True,
        help_text='URL template for invoking app with a specific solution'
    )
    latest = ForeignKeyField('self', null=True, related_name='versions')


class ApplicationSolution(BaseModel):
    """Many-to-many relation between Applications and Solutions."""
    app = ForeignKeyField(Application, related_name='solutions')
    solution = ForeignKeyField(Solution)


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

    def __str__(self):
        return "var {} ({})".format(self.name, self.type)


class SolutionVar(Var):
    """Variable in a Solution."""
    solution = ForeignKeyField(Solution, related_name="variables")


class ToolboxVar(Var):
    """Variable in a Toolbox"""
    toolbox = ForeignKeyField(Toolbox, related_name="variables")


class Review(BaseModel):
    """Review of an Entry."""
    reviewer = ForeignKeyField(User, related_name="reviews")
    comment = TextField()
    rating = IntegerField(default=0)
    created_at = DateTimeField(default=datetime.now)

    @property
    @api.expose(sense='parent')
    def entry(self):
        """Return the entry this review is for."""
        rel = None
        if self.problemreview_set.count() > 0:
            rel = self.problemreview_set.get()
        elif self.toolboxreview_set.count() > 0:
            rel = self.toolboxreview_set.get()
        elif self.solutionreview_set.count() > 0:
            rel = self.solutionreview_set.get()
        if rel:
            return rel.entry
        return None


def get_through_model(model):
    """Return the through model for model."""
    if model:
        return getattr(model, '_through_model', None)


def get_through_instance(model):
    """Return the through instance for model.

    Return None if model is not an instance of a through relation.

    """
    through_model = get_through_model(model)
    if through_model:
        # Find the fk field in cls to the through model.
        through_field = model._meta.rel_for_model(through_model).name
        # Retrieve the through model instance.
        return getattr(model, through_field)


def get_through_field(model, field):
    """Return the value for field from through model of model."""
    through_instance = get_through_instance(model)
    if through_instance:
        return getattr(through_instance, field)


def through_model(model_class):
    """Wrapper for a through relation class providing property accessors."""
    def wrapper(cls):
        # Add the through model class as a field
        cls._through_model = model_class

        # Provide convenience properties to access through model fields where
        # they don't clash with the fields of cls.
        cls_dir = dir(cls)
        for f in model_class._meta.fields:
            if f not in cls_dir:
                setattr(cls, f, property(partial(get_through_field, field=f)))
        return cls
    return wrapper


def is_through_model(cls):
    """Return True if cls is a through model relation."""
    return get_through_model(cls)


@through_model(Review)
class ProblemReview(BaseModel):
    review = ForeignKeyField(Review, primary_key=True)
    entry = ForeignKeyField(Problem)


@through_model(Review)
class ToolboxReview(BaseModel):
    review = ForeignKeyField(Review, primary_key=True)
    entry = ForeignKeyField(Toolbox)


@through_model(Review)
class SolutionReview(BaseModel):
    review = ForeignKeyField(Review, primary_key=True)
    entry = ForeignKeyField(Solution)


class BaseIndexModel(FTSModel):
    name = SearchField()
    description = SearchField()

    class Meta:
        database = db


class ProblemIndex(BaseIndexModel):
    """Store text content from other entries for searching."""
    pass


class SolutionIndex(BaseIndexModel):
    """Store text content from other entries for searching."""
    pass


class ToolboxIndex(BaseIndexModel):
    """Store text content from other entries for searching."""
    pass


def entry_type(entry):
    return type(entry).__name__


def index_entry(entry):
    """Add entry to the appropriate text index."""
    et = entry_type(entry)
    cls = getattr(importlib.import_module(__name__),
                  et + 'Index')
    if cls:
        obj = cls(name=entry.name,
                  description=entry.description,
                  docid=entry.id)
        obj.save()


_TABLES = [User, Role, UserRoles, License, Problem, Toolbox, Signature,
           ToolboxDependency, Solution, SolutionDependency, PublicKey,
           ToolboxVar, SolutionVar, Source, SolutionImage,
           ToolboxImage, ProblemSignature, ToolboxSignature, SolutionSignature,
           ProblemTag, ToolboxTag, SolutionTag,
           Review, ProblemReview, SolutionReview, ToolboxReview,
           Application, ApplicationSolution, UploadedResource]
_INDEX_TABLES = [ProblemIndex, SolutionIndex, ToolboxIndex]


def create_database(db, safe=True):
    """Create the database for our models."""
    db.create_tables(_TABLES, safe=safe)
    db.create_tables(_INDEX_TABLES, safe=safe)


def drop_tables(db):
    """Drop the model tables."""
    db.drop_tables(_INDEX_TABLES, safe=True)
    db.drop_tables(_TABLES, safe=True)


def update_index():
    """Update the text index for the current database."""
    db.drop_tables(_INDEX_TABLES, safe=True)
    db.create_tables(_INDEX_TABLES)
    for cls, index in [(Problem, ProblemIndex),
                       (Toolbox, ToolboxIndex),
                       (Solution, SolutionIndex)]:
        records = [
            {index.docid: t[0], index.name: t[1], index.description: t[2]}
            for t in cls.select(cls.id, cls.name, cls.description).tuples()
        ]
        with db.atomic():
            index.insert_many(records).execute()
