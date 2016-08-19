from flask.ext.security import PeeweeUserDatastore, Security
from app import app
from models import db, User, Role, UserRoles

# Security setup
user_datastore = PeeweeUserDatastore(db, User, Role, UserRoles)
security = Security(app, user_datastore)

