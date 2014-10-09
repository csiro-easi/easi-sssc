from flask import Blueprint, request, render_template, url_for, jsonify
from flask.views import MethodView
from scm import mongo
from werkzeug.exceptions import NotAcceptable

entries = Blueprint('entries', __name__, template_folder='templates')

endpoint_map = {
    'Entry.Toolbox': 'entries.toolbox',
    'Entry.Template': 'entries.template'
}


def api_filter(entry):
    api_fields = {
        '_id': ('@id', entry_url(entry)),
        '_cls': None,
        'toolbox': lambda _, v: id_url('entries.toolbox', v)
    }

    def f(k, v):
        if k in api_fields:
            g = api_fields.get(k)
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


def id_url(endpoint, value):
    """Return an absolute URL for endpoint and id value."""
    return url_for(endpoint, _external=True, entry_id=value)


def entry_endpoint(entry):
    """Return the endpoint for a type of entry."""
    return endpoint_map.get(entry.get('_cls'))


def entry_url(entry):
    """Return the id URL for entry at endpoint."""
    return id_url(entry_endpoint(entry), entry.get('_id'))


class EntriesView(MethodView):
    """Handle all entries."""
    def get(self, format=None):
        entries = self._query()
        best = request.accept_mimetypes.best_match(["application/json",
                                                    "text/html"])
        if best == "application/json":
            return jsonify(dict([(entry_url(e), api_filter(e))
                                 for e in entries]))
        elif best == "text/html":
            return render_template('entries/list.html', entries=entries)
        else:
            return NotAcceptable

    def post(self):
        """Add a new entry."""
        pass

    def _query(self):
        return mongo.db.entry.find(dict(request.args.items()))


class ToolboxesView(EntriesView):
    def _query(self):
        return mongo.db.entry.find(dict(request.args.items(),
                                        _cls='Entry.Toolbox'))


class TemplatesView(EntriesView):
    def _query(self):
        return mongo.db.entry.find(dict(request.args.items(),
                                        _cls='Entry.Template'))


class EntryView(MethodView):
    """Handle a single entry."""
    def get(self, entry_id):
        entry = self._find_entry(entry_id)
        best = request.accept_mimetypes.best_match(["application/json",
                                                    "text/html"])
        if best == "application/json":
            return jsonify(api_filter(entry))
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

    def put(self, entry_id):
        return NotImplemented

    def _find_entry(self, entry_id):
        return mongo.db.entry.find_one_or_404(entry_id)


class TemplateView(EntryView):
    def _find_entry(self, entry_id):
        return mongo.db.entry.find_one_or_404({'_id': entry_id,
                                               '_cls': 'Entry.Template'})


class ToolboxView(EntryView):
    def _find_entry(self, entry_id):
        return mongo.db.entry.find_one_or_404({'_id': entry_id,
                                               '_cls': 'Entry.Toolbox'})


# Dispatch to json/html views
entries.add_url_rule('/toolboxes/',
                     view_func=ToolboxesView.as_view('list_toolboxes'))
entries.add_url_rule('/toolboxes/<ObjectId:entry_id>',
                     view_func=ToolboxView.as_view('toolbox'))
entries.add_url_rule('/templates/',
                     view_func=TemplatesView.as_view('list_templates'))
entries.add_url_rule('/templates/<ObjectId:entry_id>',
                     view_func=TemplateView.as_view('template'))
entries.add_url_rule('/', view_func=EntriesView.as_view('list_all'))
