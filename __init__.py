from flask import Flask
app = Flask(__name__)

if __name__ == '__main__':
    app.run()


# from flask import Flask, jsonify
# from flask.ext.pymongo import PyMongo
# from bson.objectid import ObjectId
# import datetime

# app = Flask(__name__)
# mongo = PyMongo(app)


# @app.route("/toolboxes")
# def get_toolboxes():
#     return jsonify(toolboxes=[fix_ids(t) for t in mongo.db.toolbox.find()])


# @app.route("/toolboxes/<ObjectId:toolbox_id>")
# def get_toolbox(toolbox_id):
#     toolbox = mongo.db.toolbox.find_one_or_404(toolbox_id)
#     return jsonify(fix_ids(toolbox))


# @app.route("/templates")
# def get_templates():
#     return jsonify(templates=[fix_ids(t) for t in mongo.db.template.find()])


# @app.route("/templates/<ObjectId:template_id>")
# def get_template(template_id):
#     template = mongo.db.template.find_one_or_404(template_id)
#     return jsonify(fix_ids(template))


# def fix_ids(t):
#     "Replace ObjectIds in t with urls."
#     def fix(v):
#         if isinstance(v, ObjectId):
#             return str(v)
#         elif isinstance(v, dict):
#             return fix_ids(v)
#         else:
#             return v
#     return dict([(k, fix(v)) for k, v in t.items()])


# if __name__ == "__main__":
#     app.run()
