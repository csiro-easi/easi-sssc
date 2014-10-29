from flask import Blueprint, request, render_template, url_for, jsonify, make_response, json, abort
from flask.views import MethodView
from markdown import markdown
from app import app
from models import Toolbox, Entry, Problem, Solution, Metadata, text_search
from werkzeug.exceptions import NotAcceptable
from bson import ObjectId

site = Blueprint('site', __name__, template_folder='templates')


_model_endpoint = {
    'Toolbox': 'site.toolbox',
    'Solution': 'site.solution',
    'Problem': 'site.problem'
}


def entry_endpoint(entry):
    if entry:
        return _model_endpoint.get(type(entry).__name__)


def entry_url(entry):
    """Return the URL for entry."""
    if entry:
        return url_for(entry_endpoint(entry),
                       _external=True,
                       entry_id=entry.id)


def id_url(object_id):
    """Return an absolute URL for the object with object_id."""
    if isinstance(object_id, ObjectId):
        return entry_url(Entry.get(_id=object_id))


@app.template_filter('markdown')
def markdown_filter(md):
    return markdown(md)


@site.context_processor
def entry_processor():
    return dict(entry_url=entry_url, id_url=id_url)


def get_or_404(*args, **kwargs):
    """Return the Entry matching the query or call abort(404) if not found."""
    entry = Entry.objects.get(*args, **kwargs)
    if not entry:
        abort(404)
    else:
        return entry


def pluralise(name):
    """Return the pluralised form of name."""
    ES_ENDS = ['j', 's', 'x']
    suffix = "es" if name[-1] in ES_ENDS else "s"
    return "{}{}".format(name, suffix)


def fix_ids(entry):
    """Return a copy of entry with ObjectIds replaced with URLs. """
    if isinstance(entry, ObjectId):
        return id_url(entry)
    elif isinstance(entry, dict):
        return dict(map(fix_ids, entry.items()))
    elif isinstance(entry, tuple):
        k, v = entry
        return (k, fix_ids(v))
    elif isinstance(entry, list):
        return list(map(fix_ids, entry))
    else:
        return entry


def for_api(entry):
    """Return a copy of entry suitable for returning from the API.

    Add an '@id' entry with the ObjectId, and replace '_id' with a
    string version of the ObjectId. Remove other internal
    attributes (like '_cls'). Fix ids for external use.

    """
    # Copy the entry
    entry = dict(entry)

    # Rename the _cls field
    if '_cls' in entry:
        entry['type'] = entry['_cls']
        del entry['_cls']

    # Update the id field
    entry['@id'] = entry['_id']
    entry['_id'] = str(entry['_id'])

    # Render markdown in descriptions
    entry['description'] = markdown(entry['description'])

    # Replace ObjectIds with URIs
    return fix_ids(entry)


class EntryView(MethodView):
    list_keys = ['_id', 'name', 'description',
                 'homepage', 'license', 'metadata']
    detail_template = 'entries/detail.html'

    """Handle a single entry."""
    def get(self, entry_id):
        entry = Entry.objects().get(id=entry_id)
        best = request.accept_mimetypes.best_match(["application/json",
                                                    "text/html"])
        if best == "application/json":
            return jsonify(entry)
        elif best == "text/html":
            return render_template(self.detail_template,
                                   **self.detail_template_args(entry))
        else:
            return NotAcceptable

    def delete(self, entry_id):
        """Delete an entry."""
        id = None
        entry = get_or_404(id=entry_id)
        if entry:
            id = entry.id
            entry.delete()
        return id

    def detail_template_args(self, entry):
        return dict(entry=entry,
                    entry_type=type(entry).__name__,
                    entry_json=json.dumps(entry, indent=4))


class ProblemView(EntryView):
    detail_template = 'entries/problem_detail.html'

    def detail_template_args(self, entry):
        solutions = Solution.objects(problem=entry)
        return dict(super().detail_template_args(entry),
                    solutions=solutions)


class SolutionView(EntryView):
    detail_template = 'entries/solution_detail.html'


class ToolboxView(EntryView):
    detail_template = 'entries/toolbox_detail.html'

    def detail_template_args(self, entry):
        dependents = Solution.objects(toolbox=entry)
        return dict(super().detail_template_args(entry),
                    dependents=dependents)


class EntriesView(MethodView):
    model = Entry

    """Handle all entries."""
    def get(self, format=None):
        best = request.accept_mimetypes.best_match(["application/json",
                                                    "text/html"])
        entries = self.model.objects
        if best == "application/json":
            return jsonify(dict(entries=entries))
        elif best == "text/html":
            return render_template(
                'entries/list.html',
                entry_type=pluralise(self.model.__name__),
                entries=entries,
            )
        else:
            return NotAcceptable

    def post(self):
        """Adds the new entry."""
        entry = self.model.from_json(request.data.decode())
        if entry:
            # Add the metadata
            entry.metadata = Metadata()
            tbox = request.args.get('tbox')
            if tbox:
                tbox = get_or_404(id=tbox)
                entry.toolbox = tbox
            problem = request.args.get('problem')
            if problem:
                problem = get_or_404(id=problem)
                entry.problem = problem
            entry.save()
            resp = make_response(str(entry.id), 201)
            resp.location = entry_url(entry)
            return resp


class ProblemsView(EntriesView):
    model = Problem


class ToolboxesView(EntriesView):
    model = Toolbox


class SolutionsView(EntriesView):
    model = Solution

    def _find_toolbox(self, tbox_id):
        """Return the short description of a toolbox."""
        toolbox = Toolbox.objects.get(_id=tbox_id).only("name",
                                                        "description",
                                                        "homepage")
        return toolbox


# Dispatch to json/html views
site.add_url_rule('/toolboxes',
                  view_func=ToolboxesView.as_view('toolboxes'))
site.add_url_rule('/toolboxes/<ObjectId:entry_id>',
                  view_func=ToolboxView.as_view('toolbox'))
site.add_url_rule('/solutions',
                  view_func=SolutionsView.as_view('solutions'))
site.add_url_rule('/solutions/<ObjectId:entry_id>',
                  view_func=SolutionView.as_view('solution'))
site.add_url_rule('/problems',
                  view_func=ProblemsView.as_view('problems'))
site.add_url_rule('/problems/<ObjectId:entry_id>',
                  view_func=ProblemView.as_view('problem'))


@site.route('/add/problem')
def new_problem():
    pass


@site.route('/add/solution')
def new_solution():
    pass


@site.route('/add/toolbox')
def new_toolbox():
    pass


@site.route('/search')
def search():
    results = []
    if request.method == 'POST':
        search = request.form.get("search")
    else:
        search = request.args.get("search")
    if search:
        results = text_search(search)
    return render_template('search_results.html',
                           search=search,
                           results=list(results))


@site.route('/')
def index():
    return render_template('index.html')


# Main site
app.register_blueprint(site)
