from flask import Blueprint, request, render_template, url_for, jsonify, make_response
from flask.views import MethodView
from scm import mongo
from scm.models import Toolbox, Template, Entry
from werkzeug.exceptions import NotAcceptable

entries = Blueprint('entries', __name__, template_folder='templates')

model_endpoint = {
    'Toolbox': 'entries.toolbox',
    'Template': 'entries.template'
}


def id_url(endpoint, value):
    """Return an absolute URL for endpoint and id value."""
    return url_for(endpoint, _external=True, entry_id=value)


class EntriesView(MethodView):

    model = Entry

    """Handle all entries."""
    @classmethod
    def get(cls, format=None):
        entries = cls.query()
        best = request.accept_mimetypes.best_match(["application/json",
                                                    "text/html"])
        if best == "application/json":
            return jsonify(dict([(cls.entry_url(e), cls.model.for_api(e))
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
                resp = make_response(
                    "Created new {} {}".format(cls.model.entry_type,
                                               entry['_id']),
                    201)
                resp.location = cls.entry_url(entry)
                return resp

    @classmethod
    def query(cls):
        return mongo.db.entry.find(dict(request.args.items(), **cls.model.query))

    @classmethod
    def entry_url(cls):
        """Return the id URL for entry at endpoint."""
        return id_url(cls.entry_view.endpoint, entry.get('_id'))


class ToolboxesView(EntriesView):
    model = Toolbox
    entry_view = ToolboxView


class TemplatesView(EntriesView):
    model = Template
    entry_view = TemplateView


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


class TemplateView(EntryView):
    model = Template
    endpoint = 'entries.template'


class ToolboxView(EntryView):
    model = Toolbox
    endpoint = 'entries.toolbox'


# Dispatch to json/html views
entries.add_url_rule('/toolboxes',
                     view_func=ToolboxesView.as_view('list_toolboxes'))
entries.add_url_rule('/toolboxes/<ObjectId:entry_id>',
                     view_func=ToolboxView.as_view('toolbox'))
entries.add_url_rule('/templates',
                     view_func=TemplatesView.as_view('list_templates'))
entries.add_url_rule('/templates/<ObjectId:entry_id>',
                     view_func=TemplateView.as_view('template'))
entries.add_url_rule('/', view_func=EntriesView.as_view('list_all'))
