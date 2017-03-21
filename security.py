from flask_security import PeeweeUserDatastore, Security, current_user
from app import app
from models import db, create_database, User, Role, UserRoles

# Security setup
user_datastore = PeeweeUserDatastore(db, User, Role, UserRoles)
security = Security(app, user_datastore)

# Create the database and roles
admin_role = 'admin'
user_role = 'user'


def initialise_db():
    create_database(db)
    Role.get_or_create(name='admin', description='Administrator')
    Role.get_or_create(name='user', description='User')


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
