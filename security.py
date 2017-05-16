from collections import namedtuple
from flask_principal import identity_loaded, Permission, RoleNeed, UserNeed
from flask_security import PeeweeUserDatastore, Security, current_user, \
    RegisterForm, user_confirmed
from flask_security.forms import Required
from functools import partial
from wtforms import StringField
from app import app
from models import db, create_database, User, Role, UserRoles


class ScmRegisterForm(RegisterForm):
    """Include extra fields (name, etc) in the registration form"""
    name = StringField('Name', [Required()])


# Security setup
user_datastore = PeeweeUserDatastore(db, User, Role, UserRoles)
security = Security(app, user_datastore, confirm_register_form=ScmRegisterForm)


# Permissions and Needs for this app
EntryNeed = namedtuple('entry', ['method', 'value'])
EntryNeed.__doc__ = """Base type for needs to do with entries."""

EditEntryNeed = partial(EntryNeed, 'edit')
EditEntryNeed.__doc__ = """Needed to modify a specific entry."""

PublishEntryNeed = partial(EntryNeed, 'publish')
PublishEntryNeed.__doc__ = """Needed to publish a specific entry."""


CreateEntryPermission = Permission(RoleNeed('user'),
                                   RoleNeed('admin'))
CreateEntryPermission.__doc__ = """Permission to create an entry.

    Any authenticated user can create an entry.
"""

DeleteEntryPermission = Permission(RoleNeed('admin'))
DeleteEntryPermission.__doc__ = """Only admin users can delete entries."""

ViewUnpublishedPermission = Permission(
    RoleNeed('admin'),
    *[RoleNeed(role) for role in app.config['PUBLISH_MODERATOR_ROLES']]
)
ViewUnpublishedPermission.__doc__ = """Permission to view unpublished entries.

Admins and moderators can view unpublished entries.
"""


class EditEntryPermission(Permission):
    """Permission to edit an entry.

    A regular user has permission to edit their own entries, and an admin user
    can edit any entry.

    """
    def __init__(self, entry_id):
        super().__init__(
            EditEntryNeed(entry_id),
            RoleNeed('admin')
        )


class PublishEntryPermission(Permission):
    """Permission to publish an entry.

    Permission to publish is granted to a user based on their roles and the
    publishing configuration.

    If PUBLISH_OWN is True then a regular user can publish their own entries.
    A user with one of the PUBLISH_MODERATORS roles can publish any entry.
    An admin user has full control.

    """
    def __init__(self, entry_id):
        # Admin always has permission
        needs = [RoleNeed('admin')]

        # Moderator roles
        for role in app.config['PUBLISH_MODERATOR_ROLES']:
            needs.append(RoleNeed(role))

        # Publish entry permission required 
        needs.append(PublishEntryNeed(entry_id))

        super().__init__(*needs)


_default_roles = []


def _define_role(name, description):
    _default_roles.append(dict(name=name, description=description))
    return name


# Create the database and roles
admin_role = _define_role('admin', 'Administrators')
user_role = _define_role('user', 'Regular users')
moderator_role = _define_role('moderator',
                              'Can approve submissions for publication')


@user_confirmed.connect_via(app)
def on_user_confirmed(sender, user):
    """Add the default user role to a newly confirmed user."""
    user_datastore.add_role_to_user(user, user_role)


def initialise_db():
    """Initialise the database with default roles."""
    create_database(db)
    for role in _default_roles:
        Role.get_or_create(name=role['name'], description=role['description'])


@identity_loaded.connect_via(app)
def on_identity_loaded(sender, identity):
    """Add the Needs for the authenticated user to their Identity."""
    # set the identity user object
    identity.user = current_user

    # Add the UserNeed
    identity.provides.add(UserNeed(current_user.id))

    # Update with roles the user provides
    for role in current_user.roles:
        identity.provides.add(RoleNeed(role.name))

    entries = list(current_user.entries)

    # Allow a user to edit their own entries
    for entry in entries:
        identity.provides.add(EditEntryNeed(entry.id))

    # If PUBLISH_OWN is True then give user publishing permission
    if app.config['PUBLISH_OWN']:
        for entry in entries:
            identity.provides.add(PublishEntryNeed(entry.id))


def is_admin(user=None):
    """Return True if the user is authenticated as an admin.

    Default to checking the current user if none supplied.

    """
    if user is None:
        user = current_user
    return user.has_role(admin_role)


def is_user(user=None):
    """Return True if user is authenticated as a user.

    Default to checking the current user if none supplied.

    """
    if user is None:
        user = current_user
    return user.has_role(user_role)


def is_regular_user(user=None):
    """Return True if the current user is a regular user and not admin.

    Default to checking the current user if none supplied.

    """
    if user is None:
        user = current_user
    return is_user(user) and not is_admin(user)
