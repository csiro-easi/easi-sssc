from flask import Flask
from flask.ext.mongoengine import MongoEngine
from flask.ext.restful import Api

app = Flask(__name__)
app.config["MONGODB_SETTINGS"] = {
    "DB": "scm"
}

db = MongoEngine(app)


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
