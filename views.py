from flask import (Blueprint, request, render_template, url_for, jsonify,
                   make_response, json, abort)
from flask.views import MethodView
from markdown import markdown
from app import app
from models import Toolbox, Entry, Problem, Solution, text_search, User
from werkzeug.exceptions import NotAcceptable
from peewee import SelectQuery
# from bson import ObjectId
# from mongoengine import QuerySet, EmbeddedDocument

site = Blueprint('site', __name__, template_folder='templates')


_model_endpoint = {
    'Toolbox': 'site.toolbox',
    'Solution': 'site.solution',
    'Problem': 'site.problem',
    'User': 'site.user'
}


def entry_endpoint(entry):
    if entry:
        if isinstance(entry, dict):
            entry_type = entry.get('type')
        else:
            entry_type = type(entry).__name__
        return _model_endpoint.get(entry_type)


def entry_url(entry):
    """Return the URL for entry."""
    if entry:
        if isinstance(entry, dict):
            entry_id = entry['id']
        else:
            entry_id = entry.id
        return url_for(entry_endpoint(entry),
                       _external=True,
                       entry_id=entry_id)


@app.template_filter('markdown')
def markdown_filter(md):
    return markdown(md)


@site.context_processor
def entry_processor():
    return dict(entry_url=entry_url)


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


def _fixup(entry):
    """Return entry dict modified for the API.

    Insert '@id' entries with URLs.
    Remove internal fields (id on non-Entries).
    Remove User details

    """
    def f(d):
        if d['type'] in _model_endpoint:
            d['@id'] = entry_url(d)
        elif 'id' in d:
            del d['id']
        if d['type'] == 'User':
            d = dict(name=d['name'])
        for k, v in d.items():
            if isinstance(v, dict):
                d[k] = f(v)
        return d
    return f(entry.to_dict())


def for_api(entry):
    """Return a copy of entry suitable for returning from the API.

    Add an '@id' entry with the ObjectId, and replace '_id' with a
    string version of the ObjectId. Remove other internal
    attributes (like '_cls'). Fix ids for external use.

    If entry is a list of entries, return a dict where entries = a
    list of api entries.

    """
    if isinstance(entry, list) or isinstance(entry, SelectQuery):
        return dict(entries=[_fixup(e) for e in entry])
    return _fixup(entry)


class EntryView(MethodView):
    list_keys = ['_id', 'name', 'description',
                 'homepage', 'license', 'metadata']
    detail_template = 'entries/detail.html'

    """Handle a single entry."""
    def get(self, entry_id):
        entry = self.query(entry_id)
        best = request.accept_mimetypes.best_match(["application/json",
                                                    "text/html"])
        if best == "application/json":
            return jsonify(self.for_api(entry))
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
                    api_json=json.dumps(self.for_api(entry), indent=4))

    def query(self, entry_id):
        return Entry.get(Entry.id == entry_id)

    def for_api(self, entry):
        return for_api(entry)


class ProblemView(EntryView):
    detail_template = 'entries/problem_detail.html'

    def query(self, entry_id):
        return Problem.get(Problem.id == entry_id)


class SolutionView(EntryView):
    detail_template = 'entries/solution_detail.html'

    def query(self, entry_id):
        return Solution.get(Solution.id == entry_id)


class ToolboxView(EntryView):
    detail_template = 'entries/toolbox_detail.html'

    def query(self, entry_id):
        return Toolbox.get(Toolbox.id == entry_id)


class UserView(MethodView):
    def get(self, entry_id):
        user = User.get(User.id == entry_id)
        if not user:
            abort(404)
        return render_template(
            'user_detail.html',
            user=user,
            problems=(Problem
                      .select()
                      .join(Entry)
                      .where(Entry.author == user)),
            solutions=(Solution
                       .select()
                       .join(Entry)
                       .where(Entry.author == user)),
            toolboxes=(Toolbox
                       .select()
                       .join(Entry)
                       .where(Entry.author == user)))


class EntriesView(MethodView):
    model = Entry

    """Handle all entries."""
    def get(self, format=None):
        best = request.accept_mimetypes.best_match(["application/json",
                                                    "text/html"])
        entries = self.query()
        if best == "application/json":
            return jsonify(self.for_api(entries))
        elif best == "text/html":
            return render_template(
                'entries/list.html',
                entry_type=pluralise(self.model.__name__),
                entries=entries,
                api_json=json.dumps(self.for_api(entries), indent=4)
            )
        else:
            return NotAcceptable

    def post(self):
        """Adds the new entry."""
        # entry = self.model.from_json(request.data.decode())
        entry = self.model.from_json(request.get_json())
        if entry:
            # Add the metadata
            entry.entry.author = User.get(User.email == "fred@example.org")
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

    def query(self):
        """Return a SelectQuery instance with results for this view."""
        return Entry.select()

    def for_api(self, entries):
        # Strip out extra details
        entries = for_api(entries)
        for entry in entries['entries']:
            keys = list(entry.keys())
            for k in keys:
                if k not in ['id', '@id', 'name', 'description', 'created_at',
                             'author', 'version']:
                    del entry[k]
        return entries


class ProblemsView(EntriesView):
    model = Problem

    def query(self):
        return Problem.select()


class ToolboxesView(EntriesView):
    model = Toolbox

    def query(self):
        return Toolbox.select()


class SolutionsView(EntriesView):
    model = Solution

    def query(self):
        #solutions = Solution.objects.exclude("dependencies", "template", "variables")
        # for s in solutions:
        #     s.toolbox = Toolbox.objects(id=s.toolbox).only("name", "description", "homepage").get()
        solutions = Solution.select()
        return solutions


# Dispatch to json/html views
site.add_url_rule('/toolboxes',
                  view_func=ToolboxesView.as_view('toolboxes'))
site.add_url_rule('/toolboxes/<int:entry_id>',
                  view_func=ToolboxView.as_view('toolbox'))
site.add_url_rule('/solutions',
                  view_func=SolutionsView.as_view('solutions'))
site.add_url_rule('/solutions/<int:entry_id>',
                  view_func=SolutionView.as_view('solution'))
site.add_url_rule('/problems',
                  view_func=ProblemsView.as_view('problems'))
site.add_url_rule('/problems/<int:entry_id>',
                  view_func=ProblemView.as_view('problem'))
site.add_url_rule('/users/<int:entry_id>',
                  view_func=UserView.as_view('user'))


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
    print("Index!")
    return render_template('index.html')


# Main site
app.register_blueprint(site)
