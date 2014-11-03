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
    Toolbox: 'site.toolbox',
    Solution: 'site.solution',
    Problem: 'site.problem',
    User: 'site.user'
}


def entry_url(entry):
    """Return the URL for entry."""
    if entry:
        if isinstance(entry, dict):
            entry_id = entry['id']
        else:
            entry_id = entry.id
        return url_for(_model_endpoint[type(entry)],
                       _external=True,
                       entry_id=entry_id)


@app.template_filter('markdown')
def markdown_filter(md):
    return markdown(md)


def entry_type(entry):
    return type(entry).__name__


@site.context_processor
def entry_processor():
    return dict(entry_url=entry_url,
                entry_type=entry_type)


def pluralise(name):
    """Return the pluralised form of name."""
    ES_ENDS = ['j', 's', 'x']
    suffix = "es" if name[-1] in ES_ENDS else "s"
    return "{}{}".format(name, suffix)


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
        entry = self.query(entry_id)
        if entry:
            id = entry.id
            entry.delete()
        else:
            abort(404)
        return id

    def detail_template_args(self, entry):
        return dict(entry=entry,
                    entry_type=type(entry).__name__,
                    api_json=json.dumps(self.for_api(entry), indent=4))

    def query(self, entry_id):
        raise NotImplemented

    def for_api(self, entry):
        d = properties(entry, ['id', 'name', 'description', 'created_at',
                               'version', ('author.name', 'author')])
        d['@id'] = entry_url(entry)
        return d


class ProblemView(EntryView):
    detail_template = 'entries/problem_detail.html'

    def query(self, entry_id):
        return Problem.get(Problem.id == entry_id)


class SolutionView(EntryView):
    detail_template = 'entries/solution_detail.html'

    def query(self, entry_id):
        return Solution.get(Solution.id == entry_id)

    def for_api(self, entry):
        d = super().for_api(entry)
        problem = properties(entry.problem, ['name', 'description'])
        problem.update({'@id': entry_url(entry.problem)})
        toolbox = properties(entry.toolbox, ['name', 'description'])
        toolbox.update({'@id': entry_url(entry.toolbox)})
        d.update({
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
        d = super().for_api(entry)
        d.update({
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
        entries = []
        entries.extend(Problem.select().join(User).where(User.id == user.id))
        entries.extend(Solution.select().join(User).where(User.id == user.id))
        entries.extend(Toolbox.select().join(User).where(User.id == user))
        return render_template(
            'user_detail.html',
            user=user,
            entries=entries
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
            entry.author = User.get(User.email == "fred@example.org")
            tbox = request.args.get('tbox')
            if tbox:
                tbox = Toolbox.get(Toolbox.id == tbox)
                entry.toolbox = tbox
            problem = request.args.get('problem')
            if problem:
                problem = Problem.get(Problem.id == problem)
                entry.problem = problem
            entry.save()
            resp = make_response(str(entry.id), 201)
            resp.location = entry_url(entry)
            return resp

    def query(self):
        """Return a SelectQuery instance with results for this view."""
        return self.model.select()

    def for_api(self, entries):
        # Return a dict with entries list
        return {pluralise(self.entry_type): [self.listing(e) for e in entries]}

    def listing(self, entry):
        # Return a dict view of entry
        d = properties(entry, ['id', 'name', 'description', 'version',
                               'created_at', ('author.name', 'author')])
        d.update({
            'type': self.entry_type,
            '@id': entry_url(entry)
        })
        return d


class ProblemsView(EntriesView):
    model = Problem
    entry_type = 'problem'


class ToolboxesView(EntriesView):
    model = Toolbox
    entry_type = 'toolbox'


class SolutionsView(EntriesView):
    model = Solution
    entry_type = 'solution'

    def listing(self, entry):
        problem = properties(entry.problem, ['name', 'description'])
        problem.update({'@id': entry_url(entry.problem)})
        toolbox = properties(entry.toolbox, ['name', 'description'])
        toolbox.update({'@id': entry_url(entry.toolbox)})
        d = super().listing(entry)
        d.update({
            'problem': problem,
            'toolbox': toolbox
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
        results = text_search(search)
    return render_template('search_results.html',
                           search=search,
                           results=results)


@site.route('/')
def index():
    return render_template('index.html')


# Main site
app.register_blueprint(site)
