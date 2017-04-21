from flask import Flask
from flask_cors import CORS
from flask_mail import Mail
import hashlib

app = Flask(__name__)
app.config.from_pyfile('scm.config')

# CORS support
app.config['CORS_HEADERS'] = ['Content-Type', 'X-Requested-With']
cors = CORS(app)

# Mail setup
mail = Mail(app)

# Hashing and signing
entry_hash = getattr(hashlib, app.config['ENTRY_HASH_FUNCTION'])
resource_hash = getattr(hashlib, app.config['RESOURCE_HASH_FUNCTION'])

