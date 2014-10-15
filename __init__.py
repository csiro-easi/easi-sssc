from flask import Flask
from flask.ext.pymongo import PyMongo
from flask.ext.cors import CORS

app = Flask(__name__)
app.config["MONGO_DBNAME"] = "scm"

# CORS support
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

mongo = PyMongo(app)

# # API via flask-restful
# def register_api(app):
#     # Prevent circular imports
#     import scm.api

# register_api(app)


# Views via blueprints
def register_blueprints(app):
    # Prevents circular imports
    from scm.views import entries
    app.register_blueprint(entries)

register_blueprints(app)


if __name__ == '__main__':
    app.run()
