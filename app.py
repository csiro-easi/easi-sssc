from flask import Flask
from flask_cors import CORS
from flask_mail import Mail
from flask_uploads import configure_uploads, patch_request_class, AllExcept, \
    UploadSet, EXECUTABLES

app = Flask(__name__)
app.config.from_pyfile('scm.config')

# CORS support
app.config['CORS_HEADERS'] = ['Content-Type', 'X-Requested-With']
cors = CORS(app)

# Mail setup
mail = Mail(app)

# Uploads
attachments = UploadSet('ATTACHMENTS', AllExcept(EXECUTABLES))
configure_uploads(app, (attachments,))

# Patch our request class to limit upload file size (default 16MB)
patch_request_class(app, app.config.get('MAX_UPLOAD_SIZE', 16 * 1024 * 1024))
