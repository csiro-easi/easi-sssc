from flask import Blueprint, request, redirect, render_template, url_for, jsonify
from flask.views import MethodView
from scm.models import Entry, Toolbox, Template

entries = Blueprint('entries', __name__, template_folder='templates')


class EntriesView(MethodView):
    """Handle all entries."""
    def get(self, format=None):
        entries = Entry.objects.all()
        if format is None and "text/html" in request.accept_mimetypes:
            format = "html"
        if format == 'html':
            return render_template('entries/list.html', entries=entries)
        else:
            return jsonify(entries=entries)

    def post(self):
        """Add a new entry."""
        pass


class EntryView(MethodView):
    """Handle a single entry."""
    def get(self, name, format=None):
        entry = Entry.objects.get_or_404(name=name)
        if format is None and "text/html" in request.accept_mimetypes:
            format = "html"
        if format == 'html':
            return render_template('entries/detail.html', entry=entry)
        else:
            return jsonify(entry=entry)

    def put(self, name):
        """Update an entry."""
        pass

    def delete(self, name):
        """Delete an entry."""
        id = None
        entry = Entry.objects.get_or_404(name=name)
        if entry:
            id = entry._id
            entry.delete()
        return id


# Dispatch to json/html views
entries_view = EntriesView.as_view('list')
entry_view = EntryView.as_view('detail')
entries.add_url_rule('/entries/',
                     view_func=entries_view)
entries.add_url_rule('/entries.<string:format>',
                     view_func=entries_view,
                     methods=['GET',])
entries.add_url_rule('/entries/<string:name>/', view_func=entry_view)
entries.add_url_rule('/entries/<string:name>.<string:format>',
                     view_func=entry_view,
                     methods=['GET',])
