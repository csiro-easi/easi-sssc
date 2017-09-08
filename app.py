from flask import Flask
from flask_cors import CORS
from flask_mail import Mail


app = Flask(__name__)

# Load default settings from local config file, then override values from
# config file passed in the environment.
app.config.from_pyfile('scm.config')
loaded = app.config.from_envvar('SSSC_CONFIG', silent=True)
if not loaded:
    import os
    cfile = os.environ.get('SSSC_CONFIG')
    if cfile:
        app.logger.error('Configuration could not be loaded from "%s"', cfile)

# CORS support
app.config['CORS_HEADERS'] = ['Content-Type', 'X-Requested-With']
cors = CORS(app)

# Mail setup
mail = Mail(app)
