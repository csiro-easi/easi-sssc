from flask import (Blueprint, request, render_template, url_for, jsonify,
                   make_response, json, abort)
from flask.views import MethodView
from markdown import markdown
from app import app
from models import Toolbox, Entry, Problem, Solution, text_search, User, Var, Dependency
from werkzeug.exceptions import NotAcceptable
from peewee import SelectQuery

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


def _keep_keys(obj, keep=[]):
    """Return a dict copy of obj with only the items with keys in keys."""
    def f(t):
        k, v = t
        if k in keep:
            return k, v
    return dict(filter(f, obj.items()))


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
    api_entry = get_dictionary_from_model(entry)

    def f(d):
        if 'type' in d and d['type'] in _model_endpoint:
            d['@id'] = entry_url(d)
        for k in d:
            if isinstance(d[k], dict):
                d[k] = f(d[k])
    return f(api_entry)
    # def f(d):
    #     if d['type'] in _model_endpoint:
    #         d['@id'] = entry_url(d)
    #     elif 'id' in d:
    #         del d['id']
    #     if d['type'] == 'User':
    #         d = _keep_keys(d, ['name'])
    #     keys = list(d.keys())
    #     for k in keys:
    #         if isinstance(d[k], dict):
    #             d[k] = f(d[k])
    #     return d
    # return f(to_dict(entry))
#return f(entry.to_dict(full))


def for_api(entry, fields=None, exclude=None):
    """Return a copy of entry suitable for returning from the API.

    Add an '@id' entry with the ObjectId, and replace '_id' with a
    string version of the ObjectId. Remove other internal
    attributes (like '_cls'). Fix ids for external use.

    If entry is a list of entries, return a dict where entries = a
    list of api entries.

    """
    if isinstance(entry, list) or isinstance(entry, SelectQuery):
        entries = dict(entries=[_fixup(entry, fields, exclude) for e in entry])
        return entries
    return _fixup(entry, fields, exclude)


def properties(obj, props):
    """Return a dict with entries from obj.

    Each entry of props can be a string property name, in which case
    that property of obj will be copied under a key of the same name
    on the new dict. If a 2-tuple (src_name, dest_name) is passed,
    then new_dict[dest_name] will get the value of obj.src_name. In
    any case, if a source property name contains '.' it will be
    interpreted as a series of property requests on
    obj. E.g. 'foo.bar' will result in the value of obj.foo.bar.

    If a source property is not present on obj, it will be ignored.

    obj -- Object instance to retrieve properties from
    props -- List of property names or (source, dest) names tuples

    """
    d = {}
    for p in props:
        if isinstance(p, tuple):
            srcp, destp = p
        else:
            srcp = p
            destp = p
        ps = srcp.split('.')
        val = obj
        try:
            for prop in ps:
                val = getattr(val, prop)
            if val is not None:
                d[destp] = val
        except:
            pass
    return d


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
        d = properties(entry, ['id', 'name', 'description', 'created_at',
                               'version', ('author.name', 'author')])
        return d


class ProblemView(EntryView):
    detail_template = 'entries/problem_detail.html'

    def query(self, entry_id):
        return Problem.get(Problem.id == entry_id)

    def for_api(self, entry):
        d = super().for_api(entry.entry)
        d.update({'id': entry.id, '@id': entry_url(entry)})
        return d


class SolutionView(EntryView):
    detail_template = 'entries/solution_detail.html'

    def query(self, entry_id):
        return Solution.get(Solution.id == entry_id)

    def for_api(self, entry):
        d = super().for_api(entry.entry)
        problem = properties(entry.problem, ['name', 'description'])
        problem.update({'@id': entry_url(entry.problem)})
        toolbox = properties(entry.toolbox, ['name', 'description'])
        toolbox.update({'@id': entry_url(entry.toolbox)})
        d.update({
            'id': entry.id,
            '@id': entry_url(entry),
            'problem': problem,
            'toolbox': toolbox,
            'template': entry.template,
            'variables': [properties(v, ['name', 'type', 'label', 'description',
                                         'optional', 'default', 'min', 'max',
                                         'step', 'values'])
                          for v in entry.variables]
        })
        return d


class ToolboxView(EntryView):
    detail_template = 'entries/toolbox_detail.html'

    def query(self, entry_id):
        return Toolbox.get(Toolbox.id == entry_id)

    def for_api(self, entry):
        d = super().for_api(entry.entry)
        d.update(properties(entry, ['id', 'homepage']))
        d.update({
            'id': entry.id,
            '@id': entry_url(entry),
            'homepage': entry.homepage,
            'license': properties(entry.license, ['name', 'url']),
            'source': properties(entry.source, ['type', 'url', 'checkout',
                                                'exec'])
        })
        return d


class UserView(MethodView):
    def get(self, entry_id):
        user = User.get(User.id == entry_id)
        if not user:
            abort(404)
        return render_template(
            'user_detail.html',
            user=user
        )


class EntriesView(MethodView):
    model = Entry
    entry_type = 'entry'

    """Handle all entries."""
    def get(self, format=None):
        best = request.accept_mimetypes.best_match(["application/json",
                                                    "text/html"])
        entries = self.query()
        if best == "application/json":
            j = self.for_api(entries)
            return jsonify(j)
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
        # Return a dict with entries list
        return {pluralise(self.entry_type): [self.listing(e) for e in entries]}

    def listing(self, entry):
        # Return a dict view of entry
        d = properties(entry, ['id', 'name', 'description', 'version',
                               'created_at', ('author.name', 'author')])
        d['type'] = self.entry_type
        return d


class ProblemsView(EntriesView):
    model = Problem
    entry_type = 'problem'

    def query(self):
        return Problem.select()

    def listing(self, entry):
        d = super().listing(entry.entry)
        d.update({
            'id': entry.id,
            '@id': entry_url(entry),
            'type': 'problem'
        })
        return d


class ToolboxesView(EntriesView):
    model = Toolbox
    entry_type = 'toolbox'

    def query(self):
        return Toolbox.select()

    def listing(self, entry):
        d = super().listing(entry.entry)
        d.update({
            'id': entry.id,
            '@id': entry_url(entry),
            'type': 'toolbox'
        })
        return d


class SolutionsView(EntriesView):
    model = Solution
    entry_type = 'solution'

    def query(self):
        solutions = Solution.select()
        return solutions

    def listing(self, entry):
        problem = properties(entry.problem, ['name', 'description'])
        problem.update({'@id': entry_url(entry.problem)})
        toolbox = properties(entry.toolbox, ['name', 'description'])
        toolbox.update({'@id': entry_url(entry.toolbox)})
        d = super().listing(entry.entry)
        d.update({
            'id': entry.id,
            '@id': entry_url(entry),
            'problem': problem,
            'toolbox': toolbox,
            'type': 'solution'
        })
        return d


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
        results = [result.entry for result in text_search(search)]
    return render_template('search_results.html',
                           search=search,
                           results=results)


@site.route('/')
def index():
    print("Index!")
    return render_template('index.html')


# Main site
app.register_blueprint(site)
