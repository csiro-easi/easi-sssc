from collections import namedtuple
from flask import g
from flask_principal import identity_loaded, Permission, RoleNeed
from flask_security import PeeweeUserDatastore, Security, current_user, \
    RegisterForm, user_confirmed
from flask_security.forms import Required
from functools import partial
import os
from wtforms import StringField
from sssc.app import app
from sssc.models import db, User, Role, UserRoles


DEFAULT_PWD_LENGTH = 13


def genpassword(length=DEFAULT_PWD_LENGTH):
    """Generate and return a new random password of length."""
    chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789+/'
    return ''.join(chars[ord(os.urandom(1)) % len(chars)]
                   for i in range(length))


class ScmRegisterForm(RegisterForm):
    """Include extra fields (name, etc) in the registration form"""
    name = StringField('Name', [Required()])


# Security setup
user_datastore = PeeweeUserDatastore(db, User, Role, UserRoles)
security = Security(app, user_datastore, confirm_register_form=ScmRegisterForm)


# Permissions and Needs for this app
EntryNeed = namedtuple('entry', ['method', 'value'])
EntryNeed.__doc__ = """Base type for needs to do with entries."""

ResourceNeed = namedtuple('resource', ['method', 'value'])
ResourceNeed.__doc__ = """Base type for needs to do with resources."""

EditEntryNeed = partial(EntryNeed, 'edit')
EditEntryNeed.__doc__ = """Needed to modify a specific entry."""

EditResourceNeed = partial(ResourceNeed, 'edit')
EditResourceNeed.__doc__ = """Needed to modify a specific resource."""

PublishEntryNeed = partial(EntryNeed, 'publish')
PublishEntryNeed.__doc__ = """Needed to publish a specific entry."""

PublishResourceNeed = partial(ResourceNeed, 'publish')
PublishResourceNeed.__doc__ = """Needed to publish a specific resource."""


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


class EditResourcePermission(Permission):
    """Permission to edit an resource.

    A regular user has permission to edit their own entries, and an admin user
    can edit any resource.

    """
    def __init__(self, resource_id):
        super().__init__(
            EditResourceNeed(resource_id),
            RoleNeed('admin')
        )


class PublishResourcePermission(Permission):
    """Permission to publish an resource.

    Permission to publish is granted to a user based on their roles and the
    publishing configuration.

    If PUBLISH_OWN is True then a regular user can publish their own resources.
    A user with one of the PUBLISH_MODERATORS roles can publish any resource.
    An admin user has full control.

    """
    def __init__(self, resource_id):
        # Admin always has permission
        needs = [RoleNeed('admin')]

        # Moderator roles
        for role in app.config['PUBLISH_MODERATOR_ROLES']:
            needs.append(RoleNeed(role))

        # Publish entry permission required
        needs.append(PublishResourceNeed(resource_id))

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


@app.before_first_request
def initialise_db():
    """Initialise the database with default roles and users.

    Ensures all of the default roles are available in the database. If a
    default admin user is configured, ensure that user exists in the database
    too. Note that they will need to run through the forgotten password process
    before they can be used.

    """
    for role in _default_roles:
        Role.get_or_create(name=role['name'], description=role['description'])
    admin_email = app.config.get('DEFAULT_ADMIN_EMAIL')
    if admin_email:
        app.logger.info('Ensuring default admin user account ({}) exists.'
                        .format(admin_email))
        admin = user_datastore.get_user(admin_email)
        if admin:
            # Check that it is an admin, but just warn if it's not.
            app.logger.info('Default admin user account already exists.')
            if not admin.has_role(admin_role):
                app.logger.warn(
                    'Default admin account does *not* belong to an admin role.'
                )
            if not admin.is_active:
                app.logger.warn('Default admin account is inactive.')
        else:
            admin = user_datastore.create_user(email=admin_email,
                                               name='Admin User',
                                               password=genpassword())
            user_datastore.add_role_to_user(admin, admin_role)
            app.logger.info('New admin account was created, but still needs to'
                            ' be confirmed and have its password reset.')


def refresh_user_permissions(user, identity):
    """Refresh the permissions granted to user.

    Refreshes the user's permissions based on the resources they currently own.

    """
    # Allow a user to edit their own entries and uploads
    entries = list(user.entries)
    resources = list(user.uploads)
    for entry in entries:
        identity.provides.add(EditEntryNeed(entry.id))
    for resource in resources:
            identity.provides.add(EditResourceNeed(resource.id))

    # If PUBLISH_OWN is True then give user publishing permission
    if app.config['PUBLISH_OWN']:
        for entry in entries:
            identity.provides.add(PublishEntryNeed(entry.id))
        for resource in resources:
            identity.provides.add(PublishResourceNeed(resource.id))


def refresh_current_permissions():
    """Refresh the permissions for the current user."""
    refresh_user_permissions(current_user, g.identity)


@identity_loaded.connect_via(app)
def on_identity_loaded(sender, identity):
    """Add the Needs for the authenticated user to their Identity."""
    # set the identity user object
    identity.user = current_user

    # Catch anonymous user logged in
    if not current_user.is_anonymous:

        # Flask-security makes sure we already have the appropriate
        # {User,Role}Needs, so don't add them again.
        refresh_user_permissions(current_user, identity)


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
