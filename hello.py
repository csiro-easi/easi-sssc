from flask import Flask, jsonify
from flask.ext.pymongo import PyMongo
from bson.objectid import ObjectId
import datetime

app = Flask(__name__)
mongo = PyMongo(app)


@app.route("/")
def hello():
    x = [fix_ids(t) for t in mongo.db.toolbox.find()]
    print(x)
    return jsonify(toolboxes=x)
    # toolboxes = mongo.db.toolbox.find({})
    # return jsonify(toolboxes)


@app.route("/<ObjectId:toolbox_id>")
def get_toolbox(toolbox_id):
    toolbox = mongo.db.toolbox.find_one_or_404(toolbox_id)
    return jsonify(toolbox)


def fix_ids(t):
    "Replace ObjectIds in t with id strings."
    def fix(v):
        if isinstance(v, ObjectId):
            return str(v)
        elif isinstance(v, dict):
            return fix_ids(v)
        else:
            return v
    return dict([(k, fix(v)) for k, v in t.items()])


if __name__ == "__main__":
    app.run()
