from flask_security import PeeweeUserDatastore, Security, current_user, \
    RegisterForm, user_confirmed
from flask_security.forms import Required
from wtforms import StringField
from app import app
from models import db, create_database, User, Role, UserRoles


class ScmRegisterForm(RegisterForm):
    """Include extra fields (name, etc) in the registration form"""
    name = StringField('Name', [Required()])


# Security setup
user_datastore = PeeweeUserDatastore(db, User, Role, UserRoles)
security = Security(app, user_datastore, confirm_register_form=ScmRegisterForm)

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
    create_database(db)
    for role in _default_roles:
        Role.get_or_create(name=role['name'], description=role['description'])


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
