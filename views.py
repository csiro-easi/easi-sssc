from flask import (Blueprint, request, render_template, url_for, jsonify,
                   make_response, json, abort)
from flask.views import MethodView
from markdown import markdown
from app import app
from models import db, Toolbox, Entry, Problem, Solution, text_search, User
from werkzeug.exceptions import NotAcceptable
from peewee import SelectQuery
from rdflib import Graph, URIRef, Namespace
from rdflib.namespace import RDF

PROV = Namespace("http://www.w3.org/ns/prov#")

site = Blueprint('site', __name__, template_folder='templates')


# Connect to the database now to catch any errors here
@app.before_first_request
def first_setup():
    print("Setting up")
    db.connect()


_model_endpoint = {
    Toolbox: 'site.toolbox_id',
    Solution: 'site.solution_id',
    Problem: 'site.problem_id',
    User: 'site.user'
}


_jsonld_context = {
    "prov": "http://www.w3.org/ns/prov#"
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


def prov_url(entry):
    """Return the prov URL for entry."""
    if entry:
        if isinstance(entry, dict):
            entry_id = entry['id']
            entry_type = entry['type']
        else:
            entry_id = entry.id
            entry_type = type(entry).__name__.lower()
        endpoint = "site.{}_prov".format(entry_type)
        return url_for(endpoint, _external=True, entry_id=entry_id)


def entry_term(entry):
    """Return the rdflib term referring to entry."""
    return URIRef(entry_url(entry))


@app.template_filter('markdown')
def markdown_filter(md):
    return markdown(md)


def entry_type(entry):
    return type(entry).__name__


@site.context_processor
def entry_processor():
    return dict(entry_url=entry_url,
                entry_type=entry_type)


def add_context(response, context=_jsonld_context, embed=True):
    """Add the default jsonld context object to response.

    If response already has a @context entry, merge the default into it if it's
    an object, or leave it alone if it's a string (URI).

    Keys in the default context will not override corresponding entries that
    already exist in response.

    """
    if isinstance(response, dict):
        if '@context' in response:
            context = response['@context']
            if embed and isinstance(context, dict):
                for k, v in _jsonld_context:
                    if k not in context:
                        context[k] = v
            # else assume @context is aleady a URL, and do not override it.
        else:
            # No existing @context, so add one pointing to the default
            if embed:
                response['@context'] = _jsonld_context
            else:
                response['@context'] = url_for('site.default_context',
                                               _external=True)
    return response


def jsonldify(x, context=_jsonld_context, embed=True):
    """Return a JSON-LD response from x, including the default context.

    If embed is True, embed the context object, otherwise link to the
    default context document.

    """
    resp = jsonify(add_context(x, context, embed))
    resp.mimetype = 'application/ld+json'
    return resp


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
                if isinstance(val, list):
                    val = [getattr(v, prop) for v in val]
                else:
                    val = getattr(val, prop)
                if isinstance(val, SelectQuery):
                    val = [v for v in val]
            if val is not None:
                d[destp] = val
        except:
            pass
    return d


class EntryView(MethodView):
    detail_template = 'entries/detail.html'

    """Handle a single entry."""
    def get(self, entry_id):
        try:
            entry = self.query(entry_id)
        except:
            abort(404)
        best = request.accept_mimetypes.best_match(["application/json",
                                                    "text/html"])
        if best == "application/json":
            return jsonldify(self.for_api(entry))
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
                               'version', 'keywords', ('author.name', 'author')])
        d['uri'] = entry_url(entry)
        d['@id'] = entry_url(entry)
        if 'depends_on' in vars(entry):
            d['dependencies'] = [properties(dep, ['type', 'name', 'version',
                                                  'path'])
                                 for dep in entry.depends_on]
        else:
            d['dependencies'] = []

        # Add prov info and return
        d['@type'] = ['prov:Entity']
        d['prov:has_provenance'] = prov_url(entry)
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
        problem = properties(entry.problem, ['id', 'name', 'description'])
        problem.update({'uri': entry_url(entry.problem)})
        problem.update({'@id': entry_url(entry.problem)})
        toolboxes = [entry_url(t.dependency) for t in entry.toolboxes]
        dependencies = [properties(d.dependency, ['type', 'identifier',
                                                  'version', 'repository'])
                        for d in entry.dependencies]
        d.update({
            'problem': problem,
            'toolboxes': toolboxes,
            'template': entry.template,
            'variables': [properties(v, ['name', 'type', 'label',
                                         'description', 'optional',
                                         'default', 'min', 'max',
                                         'step', 'values'])
                          for v in entry.variables],
            'dependencies': [properties(dep, [
                'type',
                'name',
                'version',
                'path'])
                for dep in entry.depends_on],
            # Include prov info
            '@type': 'prov:Plan'
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
                                                'exec']),
            'images': [properties(img, ['provider', 'image_id', 'sc_path'])
                       for img in entry.images],
            'variables': [properties(v, ['name', 'type', 'label',
                                         'description', 'optional',
                                         'default', 'min', 'max',
                                         'step', 'values'])
                          for v in entry.variables],
            'puppet': entry.puppet,
            'toolboxes': [entry_url(t.dependency) for t in entry.toolboxes],
            'dependencies': [properties(d.dependency, ['type', 'identifier',
                                                       'version', 'repository'])
                             for d in entry.dependencies]
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
    prov_type = 'prov:Entity'

    def get(self, format=None):
        """Handle all entries."""
        best = request.accept_mimetypes.best_match(["application/json",
                                                    "text/html"])
        entries = self.query()
        if best == "application/json":
            j = self.for_api(entries)
            return jsonldify(j)
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
                               'created_at', 'keywords', ('author.name', 'author')])
        d.update({
            'type': self.entry_type,
            'uri': entry_url(entry),
            '@id': entry_url(entry),
            '@type': self.prov_type,
            'prov:has_provenance': prov_url(entry)
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
    prov_type = 'prov:Plan'

    def get(self):
        """Check for a problem query arg."""
        self.problem_id = request.args.get("problem")
        return super().get(self)

    def query(self):
        """Return a list of Solutions, optionally filtered by Problem."""
        solutions = Solution.select()
        if self.problem_id is not None:
            solutions = solutions.where(Solution.problem == self.problem_id)
        return solutions

    def listing(self, entry):
        problem = properties(entry.problem, ['id', 'name', 'description'])
        problem.update({'uri': entry_url(entry.problem)})
        problem.update({'@id': entry_url(entry.problem)})
        toolboxes = [entry_url(t.dependency) for t in entry.toolboxes]
        d = super().listing(entry)
        d.update({
            'problem': problem,
            'toolboxes': toolboxes
        })
        return d


class ProvView(MethodView):
    model = Entry

    prov_context = {
        "Entity": "http://www.w3.org/ns/prov#Entity",
        "Plan": "http://www.w3.org/ns/prov#Plan",
        "wasDerivedFrom": {
            "@id": "http://www.w3.org/ns/prov#wasDerivedFrom",
            "@type": "@id"
        },
        "toolboxes": {
            "@type": "@id"
        }
    }

    def get(self, entry_id):
        """Return the PROV info for entry_id."""
        # Retrieve a single entry
        try:
            entry = self.model.get(self.model.id == entry_id)
        except:
            abort(404)
        # Build the RDF prov graph
        g = Graph()
        for t in self.triples(entry):
            g.add(t)
        # Return the appropriate serialization
        matchable = ["application/ld+json",
                     "application/json",
                     "text/turtle",
                     "application/rdf+xml"]
        best = request.accept_mimetypes.best_match(matchable, default=None)
        if best is None:
            return NotAcceptable
        serialize_args = dict(format=best)
        mimetype = best
        if best == "application/json":
            best = "application/ld+json"
            serialize_args = dict(format=best)
        if best == "application/ld+json":
            serialize_args.update(context=self.prov_context,
                                  indent=4)
        resp = make_response(g.serialize(**serialize_args))
        resp.mimetype = mimetype
        return resp

    def triples(self, entry):
        triples = [(entry_term(entry), RDF.type, PROV.Entity)]
        return triples

    def query(self, entry_id):
        raise NotImplemented


class ProblemProvView(ProvView):
    model = Problem


class SolutionProvView(ProvView):
    model = Solution

    def triples(self, entry):
        triples = super().triples(entry)
        solution = entry_term(entry)
        triples.append((solution, RDF.type, PROV.Plan))
        triples.extend([(solution, PROV.wasDerivedFrom, entry_term(t))
                        for t in [entry.toolbox]])
        triples.append((solution, PROV.wasDerivedFrom, entry_term(entry.problem)))
        return triples


class ToolboxProvView(ProvView):
    model = Toolbox


# Dispatch to json/html views
site.add_url_rule('/toolboxes',
                  view_func=ToolboxesView.as_view('toolboxes'))
site.add_url_rule('/toolboxes/<int:entry_id>',
                  view_func=ToolboxView.as_view('toolbox'))
site.add_url_rule('/toolbox/',
                  view_func=ToolboxesView.as_view('toolbox_list'))
site.add_url_rule('/toolbox/<int:entry_id>',
                  view_func=ToolboxView.as_view('toolbox_id'))
site.add_url_rule('/solutions',
                  view_func=SolutionsView.as_view('solutions'))
site.add_url_rule('/solutions/<int:entry_id>',
                  view_func=SolutionView.as_view('solution'))
site.add_url_rule('/solution/',
                  view_func=SolutionsView.as_view('solution_list'))
site.add_url_rule('/solution/<int:entry_id>',
                  view_func=SolutionView.as_view('solution_id'))
site.add_url_rule('/problems',
                  view_func=ProblemsView.as_view('problems'))
site.add_url_rule('/problems/<int:entry_id>',
                  view_func=ProblemView.as_view('problem'))
site.add_url_rule('/problem/',
                  view_func=ProblemsView.as_view('problem_list'))
site.add_url_rule('/problem/<int:entry_id>',
                  view_func=ProblemView.as_view('problem_id'))
site.add_url_rule('/users/<int:entry_id>',
                  view_func=UserView.as_view('user'))
# Prov endpoints
site.add_url_rule('/problem/<int:entry_id>/prov',
                  view_func=ProblemProvView.as_view('problem_prov'))
site.add_url_rule('/solution/<int:entry_id>/prov',
                  view_func=SolutionProvView.as_view('solution_prov'))
site.add_url_rule('/toolbox/<int:entry_id>/prov',
                  view_func=ToolboxProvView.as_view('toolbox_prov'))
                 


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


@site.route('/sssc.jsonld')
def default_context():
    return jsonldify({}, True)


@site.route('/')
def index():
    return render_template('index.html')


# Main site
app.register_blueprint(site)
