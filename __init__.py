from flask import Flask
from flask.ext.pymongo import PyMongo, pymongo
from flask.ext.cors import CORS

app = Flask(__name__)
app.config["MONGO_DBNAME"] = "scm"

# CORS support
app.config['CORS_HEADERS'] = ['Content-Type', 'X-Requested-With']
cors = CORS(app)

# Set up the database
mongo = PyMongo(app)


@app.before_first_request
def setup_db():
    print("Ensuring text indexes")
    mongo.db.entry.ensure_index([("name", pymongo.TEXT),
                                 ("description", pymongo.TEXT)])
    print("Ensured text indexes")


# Views via blueprints
def register_blueprints(app):
    # Prevents circular imports
    from scm.views import site
    app.register_blueprint(site)

register_blueprints(app)


if __name__ == '__main__':
    app.run()
