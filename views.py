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

cls_endpoint = {
    'toolbox': 'entries.toolbox',
    'template': 'entries.template'
}


def id_url(object_id):
    """Return an absolute URL for the object with object_id."""
    if isinstance(object_id, ObjectId):
        o = mongo.db.entry.find(object_id)
        if o:
            return url_for(cls_endpoint[o['_cls']],
                           _external=True,
                           entry_id=object_id)


def keep_keys(keys=[]):
    """Returns predicate fn to filter entries where key in keys."""
    if keys is not None:
        def f(k, v):
            return k in keys
        return f


def drop_keys(keys=[]):
    """Return predicate fn that drops entries where key in keys."""
    if keys is not None:
        def f(k, v):
            return k not in keys
    else:
        # If keys is None we want to drop everything
        def f(k, v):
            return False
    return f


class APIView(MethodView):
    """Common base class for all API views.

    Handles id transformations.

    """
    def for_api(self, entry):
        """Return an entry dict with fixed ids.

        Replace ObjectId entries with urls, except '_id' which is
        replaced with a '@id' url entry.

        """
        if isinstance(entry, dict):
            items = entry.items()
        else:
            items = entry
        def fix_ids(k, v):
            if isinstance(v, ObjectId):
                if k == '_id':
                    k = '@id'
                return k, id_url(v)
            elif isinstance(v, dict):
                return k, self.for_api(v)
            return k, v
        return dict(map(fix_ids, items)


class EntryView(MethodView):

    list_keys = ['_id', 'name', 'description',
                 'homepage', 'license', 'metadata']

    """Handle a single entry."""
    def get(self, entry_id):
        entry = mongo.db.entry.find_one_or_404(entry_id)
        if not self.model.is_model_for(entry):
            abort(404)
        entry = self.for_api(self.detail_view(entry))
        best = request.accept_mimetypes.best_match(["application/json",
                                                    "text/html"])
        if best == "application/json":
            return jsonify(entry)
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
    def for_api(cls, entry):
        """Return entry dict prepared for use in the api.

        Entry should be a list of (key, value) tuples.

        The '_id' entry will be stringified, and an '@id' entry added
        with the corresponding url. Other ObjectId entries will be
        transformed into urls.

        """
        e['@id'] = id_url(entry['_id'])
        return e

    @classmethod
    def list_view(cls, entry):
        """Return a (list of tuples) view of an Entry suitable for a list.

        Default is to only keep the '@id', 'name', 'description', 'homepage',
        'license' and 'metadata' entries.

        """
        return filter(keep_keys(list_keys), entry.items())

    @classmethod
    def detail_view(cls, entry):
        """Return a detailed view (list of tuples) of the entry.

        Default is to return all entries except '_cls', with fixed
        ids.

        """
        return filter(drop_keys(['_cls']), entry.items())


class TemplateView(EntryView):
    model = Template
    endpoint = 'entries.template'

    @classmethod
    def for_api(cls, entry):
        """Turn any toolbox references into urls."""
        entry = cls.for_api(entry)
        return entry


class ToolboxView(EntryView):
    model = Toolbox
    endpoint = 'entries.toolbox'


class EntriesView(MethodView):

    model = Entry
    entry_view = EntryView

    """Handle all entries."""
    def get(self, format=None):
        best = request.accept_mimetypes.best_match(["application/json",
                                                    "text/html"])
        entries = [self.for_api(self.list_view(e)) for e in self.query()]
        if best == "application/json":
            return jsonify(dict([(e.get('_id'), e) for e in entries]))
        elif best == "text/html":
            return render_template('entries/list.html', entries=entries)
        else:
            return NotAcceptable

    def post(self):
        """Adds the new entry."""
        entry = request.get_json()
        if entry:
            entry = self.model.create(entry)
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
                resp.location = id_url(new_id)
                return resp

    def query(self):
        return mongo.db.entry.find(dict(request.args.items(),
                                        **self.model.query))

    @classmethod
    def for_api(cls, entry):
        """Filter entry for returning from the api.
        """
        return Entry.for_api(entry)


class ToolboxesView(EntriesView):
    model = Toolbox
    entry_view = ToolboxView


class TemplatesView(EntriesView):
    model = Template
    entry_view = TemplateView


def _fix_ids(endpoint, entry):
    if entry['type'] == 'toolbox':
        return dict(entry, uri=id_url(entry['uri']))
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
