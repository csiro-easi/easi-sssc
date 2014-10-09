#===============================================================================
# Unused attempt at flask-restful based API.
#
#===============================================================================
from flask import abort, url_for, request, make_response, render_template, redirect
from flask.ext.restful import Api, Resource, fields, marshal, marshal_with
from scm import app, mongo
from bson.objectid import ObjectId

api = Api(app)

endpoint_map = {
    'Entry.Toolbox': 'toolbox',
    'Entry.Template': 'template'
}


def id_url(endpoint, value):
    """Return an absolute URL for endpoint and id value."""
    return url_for(endpoint, _external=True, entry_id=value)


def entry_endpoint(entry):
    """Return the endpoint for a type of entry."""
    return endpoint_map.get(entry.get('_cls'))


def entry_url(entry):
    """Return the id URL for entry at endpoint."""
    return id_url(entry_endpoint(entry), entry.get('_id'))


class IdUrl(fields.String):
    def __init__(self, endpoint=None, **kwargs):
        self.endpoint = endpoint
        self.obj = None
        super(IdUrl, self).__init__(**kwargs)

    def output(self, key, obj):
        # Cache the obj
        self.obj = obj
        return super(IdUrl, self).output(key, obj)

    def format(self, value):
        endpoint = (entry_endpoint(self.obj) if self.endpoint is None
                    else self.endpoint)
        return id_url(endpoint, value)


entry_fields = {
    '@id': IdUrl(attribute='_id'),
    'name': fields.String,
    'description': fields.String,
    'author': fields.String,
    'created_at': fields.DateTime,
    'dependencies': fields.Raw
}

toolbox_fields = dict(entry_fields, **{
    'source': fields.Raw
})

template_fields = dict(entry_fields, **{
    'toolbox': IdUrl('toolbox')
})


class Toolbox(Resource):
    @marshal_with(toolbox_fields)
    def get(self, entry_id):
        entry = mongo.db.entry.find_one_or_404({'_id': entry_id,
                                                '_cls': 'Entry.Toolbox'})
        return entry

    def put(self, entry_id):
        return NotImplemented

    def delete(self, entry_id):
        return NotImplemented


class ToolboxList(Resource):
    def get(self):
        print(request.args)
        q = dict(request.args.items(), _cls='Entry.Toolbox')
        print("q = {}".format(q))
        entries = mongo.db.entry.find(q)
        return dict([(entry_url(e), marshal(e, toolbox_fields))
                     for e in entries])

    def post(self):
        pass


class Template(Resource):
    @marshal_with(template_fields)
    def get(self, entry_id):
        entry = mongo.db.entry.find_one_or_404({'_id': entry_id,
                                                '_cls': 'Entry.Template'})
        return entry

    def put(self, entry_id):
        return NotImplemented

    def delete(self, entry_id):
        return NotImplemented


class TemplateList(Resource):
    def get(self):
        print(request.args)
        q = dict(request.args.items(), _cls='Entry.Template')
        print("q = {}".format(q))
        entries = mongo.db.entry.find(q)
        return dict([(entry_url(e), marshal(e, template_fields))
                     for e in entries])

    def post(self):
        pass


@api.representation('text/html')
def html(data, code, headers=None):
    print("data={}".format(data))
    if '@id' in data:
        return render_template('entries/detail.html', entry=data)
    else:
        return render_template('entries/list.html', entries=data.values())


api.add_resource(ToolboxList, '/toolboxes/')
api.add_resource(Toolbox, '/toolboxes/<ObjectId:entry_id>')
api.add_resource(TemplateList, '/templates/')
api.add_resource(Template, '/templates/<ObjectId:entry_id>')
