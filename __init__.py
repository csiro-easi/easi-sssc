from flask import Flask
from flask.ext.pymongo import PyMongo
from flask.ext.cors import CORS

app = Flask(__name__)
app.config["MONGO_DBNAME"] = "scm"

# CORS support
app.config['CORS_HEADERS'] = ['Content-Type', 'X-Requested-With']
cors = CORS(app)

mongo = PyMongo(app)

# Views via blueprints
def register_blueprints(app):
    # Prevents circular imports
    from scm.views import site
    app.register_blueprint(site)

register_blueprints(app)


if __name__ == '__main__':
    app.run()
