from flask import Blueprint, request, render_template, url_for, jsonify, make_response, abort, json
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
        o = mongo.db.entry.find_one(object_id)
        if o:
            return url_for(cls_endpoint[o['_cls']],
                           _external=True,
                           entry_id=object_id)


class APIView(MethodView):
    """Common base class for all API views.

    Handles id transformations.

    """
    def fix_ids(self, entry):
        """Return a copy of entry with ObjectIds replaced with URLs. """
        if isinstance(entry, ObjectId):
            return id_url(entry)
        elif isinstance(entry, dict):
            return dict(map(self.fix_ids, entry.items()))
        elif isinstance(entry, tuple):
            k, v = entry
            return (k, self.fix_ids(v))
        elif isinstance(entry, list):
            return list(map(self.fix_ids, entry))
        else:
            return entry

    def for_api(self, entry):
        """Return a copy of entry suitable for returning from the API.

        Add an '@id' entry with the ObjectId, and replace '_id' with a
        string version of the ObjectId. Remove other internal
        attributes (like '_cls'). Fix ids for external use.

        """
        print("APIView.for_api()")
        # Copy the entry
        entry = dict(entry)

        # Drop internal fields
        for d in ['_cls']:
            if d in entry:
                del entry[d]

        # Update the id field
        entry['@id'] = entry['_id']
        entry['_id'] = str(entry['_id'])

        # Replace ObjectIds with URIs
        return self.fix_ids(entry)


class EntryView(APIView):

    list_keys = ['_id', 'name', 'description',
                 'homepage', 'license', 'metadata']

    """Handle a single entry."""
    def get(self, entry_id):
        entry = mongo.db.entry.find_one_or_404(entry_id)
        if not self.model.is_model_for(entry):
            abort(404)
        entry = self.for_api(entry)
        best = request.accept_mimetypes.best_match(["application/json",
                                                    "text/html"])
        if best == "application/json":
            return jsonify(entry)
        elif best == "text/html":
            return render_template('entries/detail.html',
                                   entry=entry,
                                   entry_json = json.dumps(entry, indent=4))
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


class EntriesView(APIView):

    model = Entry
    entry_view = EntryView

    """Handle all entries."""
    def get(self, format=None):
        best = request.accept_mimetypes.best_match(["application/json",
                                                    "text/html"])
        entries = dict([(e['_id'], e) for e in map(self.for_api, self.query())])
        if best == "application/json":
            return jsonify(entries)
        elif best == "text/html":
            return render_template('entries/list.html',
                                   entry_type="{}s".format(self.model.__name__),
                                   entries=entries,
                                   entries_js=json.dumps(entries, indent=4))
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

    def for_api(self, entry):
        """Only keep generic fields (metadata etc) for a list of entries."""
        print("EntriesView.for_api()")
        # Keep generic fields
        e = dict([(k, v)
                  for k, v in entry.items()
                  if k in ['_id', 'name', 'description',
                           'homepage', 'license', 'metadata']])
        print("keys={}".format(e.keys()))
        # Default processing
        return super().for_api(e)


class ToolboxesView(EntriesView):
    model = Toolbox
    entry_view = ToolboxView


class TemplatesView(EntriesView):
    model = Template
    entry_view = TemplateView

    def for_api(self, entry):
        """Keep toolbox dependencies as well as generic fields."""
        print("TemplatesView.for_api()")
        toolboxes = self.fix_ids([d for d in entry['dependencies']
                                  if d['type'] == 'toolbox'])
        entry = super().for_api(entry)
        entry['dependencies'] = toolboxes
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
