from pymongo import TEXT
from flask import Flask
# from flask.ext.mongoengine import MongoEngine
# from bson import ObjectId
# from werkzeug.routing import BaseConverter
from flask.ext.cors import CORS
# Use the ext database to get FTS support
# from peewee import SqliteDatabase
from playhouse.sqlite_ext import SqliteExtDatabase

app = Flask(__name__)
app.config.from_pyfile('scm.config')

# CORS support
app.config['CORS_HEADERS'] = ['Content-Type', 'X-Requested-With']
cors = CORS(app)

# Connect to the database now to catch any errors here
db = SqliteExtDatabase('scm.db')


@app.before_first_request
def first_setup():
    print("Setting up")
    db.connect()

# # Set up the database, and register ObjectId converter
# class ObjectIdConverter(BaseConverter):
#     def to_python(self, value):
#         return ObjectId(value)

#     def to_url(self, value):
#         return str(value)

# app.url_map.converters['ObjectId'] = ObjectIdConverter
# db = MongoEngine(app)


# # Setup the text indexes through PyMongo for now
# @app.before_first_request
# def setup_db():
#     print("Ensuring text indexes")
#     from models import Entry
#     Entry._get_collection().ensure_index([("name", TEXT),
#                                           ("description", TEXT)])
#     print("Ensured text indexes")


# mongo = PyMongo(app)
#
#
