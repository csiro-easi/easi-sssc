from flask import Blueprint, request, render_template, url_for, jsonify, make_response
from flask.views import MethodView
from scm import mongo
from scm.models import Toolbox, Template, Entry
from werkzeug.exceptions import NotAcceptable
from bson import ObjectId

entries = Blueprint('entries', __name__, template_folder='templates')

model_endpoint = {
    'Toolbox': 'entries.toolbox',
    'Template': 'entries.template'
}


def id_url(endpoint, value):
    """Return an absolute URL for endpoint and id value."""
    return url_for(endpoint, _external=True, entry_id=value)


class EntryView(MethodView):

    """Handle a single entry."""
    @classmethod
    def get(cls, entry_id):
        entry = mongo.db.entry.find_one_or_404(entry_id)
        if not cls.model.is_model_for(entry):
            abort(404)
        best = request.accept_mimetypes.best_match(["application/json",
                                                    "text/html"])
        if best == "application/json":
            return jsonify(cls.model.for_api(entry))
        elif best == "text/html":
            return render_template('entries/detail.html', entry=entry)
        else:
            return NotAcceptable

    def delete(self, entry_id):
        """Delete an entry."""
        entry = self._find_entry(entry_id)
        if entry:
            entry.delete()
        return id

    @classmethod
    def for_api(cls, entry, endpoint):
        """Filter entry for returning from the api."""
        api_fields = {
            '_id': ('@id', id_url(cls.endpoint, entry['_id'])),
            '_cls': None,
            'toolbox': lambda _, v: id_url('entries.toolbox', v)
        }
        return _filter_fields(api_fields, entry)


class TemplateView(EntryView):
    model = Template
    endpoint = 'entries.template'


class ToolboxView(EntryView):
    model = Toolbox
    endpoint = 'entries.toolbox'


class EntriesView(MethodView):

    model = Entry
    entry_view = EntryView

    """Handle all entries."""
    @classmethod
    def get(cls, format=None):
        entries = cls.query()
        best = request.accept_mimetypes.best_match(["application/json",
                                                    "text/html"])
        if best == "application/json":
            return jsonify(dict([(str(e.get('_id')),
                                  cls.for_api(e, cls.entry_view.endpoint))
                                 for e in entries]))
        elif best == "text/html":
            return render_template('entries/list.html', entries=entries)
        else:
            return NotAcceptable

    @classmethod
    def post(cls):
        """Adds the new entry."""
        entry = request.get_json()
        if entry:
            entry = cls.model.create(entry)
            if entry:
                new_id = entry['_id']
                tbox = request.args.get('tbox')
                if tbox:
                    mongo.db.entry.update(
                        { '_id': new_id },
                        { '$addToSet': {
                            'dependencies': {
                                'type': 'toolbox',
                                'uri': ObjectId(tbox)
                            }
                        }}
                    )
                resp = make_response(str(new_id), 201)
                resp.location = id_url(cls.entry_view.endpoint, new_id)
                return resp

    @classmethod
    def query(cls):
        return mongo.db.entry.find(dict(request.args.items(),
                                        **cls.model.query))

    @classmethod
    def for_api(cls, entry, endpoint):
        """Filter entry for returning from the api."""
        api_fields = {
            '_id': ('@id', id_url(cls.entry_view.endpoint, entry['_id'])),
            '_cls': None,
            'dependencies': lambda _, v: [_fix_ids('entries.toolbox', d)
                                          for d in v]
        }
        return _filter_fields(api_fields, entry)


class ToolboxesView(EntriesView):
    model = Toolbox
    entry_view = ToolboxView


class TemplatesView(EntriesView):
    model = Template
    entry_view = TemplateView


def _filter_fields(spec, entry):
    """Filter entries in entry according to spec."""
    def f(k, v):
        if k in spec:
            g = spec.get(k)
            if callable(g):
                g = g(k, v)
            if g is None:
                return None
            elif isinstance(g, tuple):
                return g
            else:
                return k, g
        else:
            return k, v

    return dict(filter(None, [f(k, v) for k, v in entry.items()]))


def _fix_ids(endpoint, entry):
    if entry['type'] == 'toolbox':
        return dict(entry, uri=id_url(endpoint, entry['uri']))
    else:
        return entry

# Dispatch to json/html views
entries.add_url_rule('/toolboxes',
                     view_func=ToolboxesView.as_view('list_toolboxes'))
entries.add_url_rule('/toolboxes/<ObjectId:entry_id>',
                     view_func=ToolboxView.as_view('toolbox'))
entries.add_url_rule('/templates',
                     view_func=TemplatesView.as_view('list_templates'))
entries.add_url_rule('/templates/<ObjectId:entry_id>',
                     view_func=TemplateView.as_view('template'))
