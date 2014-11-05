from flask import Flask
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
db = SqliteExtDatabase(app.config['SQLITE_DB_FILE'],
                       threadlocals=True)
#                       journal_mode='WAL')

@app.before_first_request
def first_setup():
    print("Setting up")
    db.connect()
