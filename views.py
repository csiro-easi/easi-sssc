from collections.abc import Iterable
from flask import (Blueprint, request, render_template, url_for, jsonify,
                   make_response, abort)
from flask.views import MethodView
from markdown import markdown
from app import app, entry_hash
import models
from models import db, Toolbox, Entry, Problem, Solution, text_search, User, \
    License, BaseModel
from namespaces import PROV, SSSC
from werkzeug.exceptions import NotAcceptable
from peewee import SelectQuery, DoesNotExist
from rdflib import BNode, Graph, URIRef, Namespace
from rdflib.namespace import RDF

site = Blueprint('site', __name__, template_folder='templates')


# Connect to the database now to catch any errors here
@app.before_first_request
def first_setup():
    print("Setting up")
    db.connect()


# These will be updated with model views after those are defined.
_model_api = {}


_jsonld_context = {
    "prov": "http://www.w3.org/ns/prov#"
}


def model_endpoint(model_class):
    return 'site.{}'.format(_model_api[model_class][0])


def model_pk(model_class):
    return _model_api[model_class][2]


def model_url(model, version=None, pinned=False, endpoint=None, **kwargs):
    """Return URL for the model instance.

    If model is an Entry, then version and pinned can be used to specify what
    version to create the url for (default is latest), and optionally whether
    to create an URL that specifies the current version of the latest (default
    is not).

    If endpoint is specified it will override the default endpoint for the
    model class.

    """
    if model and type(model) in _model_api:
        model_id = (model.entry_id
                    if hasattr(model, 'entry_id')
                    else model.id)
        if not hasattr(model, 'latest') or model.latest is None:
            latest_id = None
        else:
            latest_id = model.latest.id
        model_class = type(model)
        model_version = (model.version if hasattr(model, 'version')
                         else None)
        # Is it an external model?
        if model_class not in _model_api:
            return None
        args = {model_pk(model_class): model_id}
        # Is it an Entry?
        if issubclass(model_class, Entry):
            if version is not None:
                args['version'] = version
            elif pinned or (latest_id is not None and latest_id != model_id):
                args['version'] = model_version
        args.update(**kwargs)
        # Determine endpoint to use
        if endpoint is None:
            endpoint = model_endpoint(model_class)
        return url_for(endpoint,
                       _external=True,
                       **args)


def prov_url(entry):
    """Return the prov URL for entry."""
    endpoint = model_endpoint(type(entry)) + '_prov'
    return model_url(entry, endpoint=endpoint)


def edit_url(entry, url=None):
    """Return the URL for editing entry.

    If url is specified, it will be used as the URL to return to after editing
    the entry.

    """
    if entry:
        endpoint = "{}.edit_view".format(type(entry).__name__.lower())
        return url_for(endpoint,
                       _external=True,
                       id=entry.id,
                       url=url)


# These fields should *never* be returned to clients
_hidden_fields = set([
    User.id,
    Problem.id,
    Toolbox.id,
    Solution.id,
    License.id,
    User.password,
    Problem.problemindex_set,
    Solution.solutionindex_set,
    Toolbox.toolboxindex_set
])

# These fields should usually be returned as refs, not nested
_default_refs = set([
    Problem.latest,
    Problem.solutions,
    Problem.versions,
    Toolbox.latest,
    Toolbox.versions,
    Solution.latest,
    Solution.problem,
    Solution.versions
])

# User details shouldn't be included in most client interactions.
_default_exclude = set([
    User.active,
    User.confirmed_at,
    User.email,
    User.roles,
    User.signatures,
    User.problems,
    User.solutions,
    User.toolboxes
])


def _clone_set(s, default=None):
    if s:
        return set(s)
    elif default is not None:
        return set(default)
    return set()


def model_to_dict(model, seen=None, exclude=None, refs=None,
                  max_depth=None, include_nulls=False):
    """Return a dict view of model, suitable for the API. """
    max_depth = -1 if max_depth is None else max_depth

    # Set up fields to extract, include some sensible defaults for the API
    refs = _clone_set(refs, _default_refs)
    exclude = _clone_set(exclude, _default_exclude)
    seen = _clone_set(seen)

    # Never expose certain fields!
    exclude |= _hidden_fields
    exclude |= seen

    data = {}

    # Always include semantic markup, plus an @id attribute if we have one
    uri = model_url(model)
    if uri:
        data['@id'] = uri
        prov = prov_url(model)
        if prov:
            data['prov:has_provenance'] = prov
        subject = URIRef(uri)
    else:
        subject = BNode()
    if isinstance(model, BaseModel):
        g = model.semantic_types(subject)
        data['@type'] = [t.n3(g.namespace_manager)
                         for t in g.objects(subject=subject,
                                            predicate=RDF.type)]

    # Iterate over fields of model
    foreign = set(model._meta.rel.values())
    for f in model._meta.declared_fields:
        if f in exclude:
            continue

        f_data = model._data.get(f.name)
        if f in foreign:
            if f_data is not None:
                rel_obj = getattr(model, f.name)
                if f not in refs and max_depth != 0:
                    # extract the related model data
                    seen.add(f)
                    f_data = model_to_dict(
                        rel_obj,
                        seen=seen,
                        exclude=exclude,
                        refs=refs,
                        max_depth=max_depth - 1
                    )
                else:
                    # Replace with external reference
                    f_data = model_url(rel_obj)

        if include_nulls or f_data is not None:
            data[f.name] = f_data

    # Iterate over reverse relations, and embed the data
    model_class = type(model)
    for related_name, fk in model._meta.reverse_rel.items():
        descriptor = getattr(model_class, related_name)
        if descriptor in exclude or fk in exclude:
            continue

        exclude.add(fk)
        related_query = getattr(
            model,
            related_name + '_prefetch',
            getattr(model, related_name)
        )

        accum = []
        for rel_obj in related_query:
            if descriptor in refs:
                accum.append(model_url(rel_obj))
            else:
                accum.append(model_to_dict(
                    rel_obj,
                    seen=seen,
                    exclude=exclude,
                    refs=refs,
                    max_depth=max_depth - 1
                ))
        data[related_name] = accum

    return data


ignored_fields_for_hash = [
    'id',
    'entry_hash',
    'signatures',
    'latest',
    'versions',
    'images'
]


def hashable_data(obj):
    """Return a list of the hashable strings from obj.

    Transforms obj into the canonical form required for hashing, extracts the
    strings corresponding to the hashable data, and returns the resulting list.

    """
    data = []
    for k, v in sorted(obj.items()):
        if v is None or k in ignored_fields_for_hash:
            # Check for fields to ignore and null values
            continue
        elif isinstance(v, dict):
            # Recurse
            data.extend(hashable_data(v))
        elif isinstance(v, list) or isinstance(v, tuple):
            # Sort by id, then recurse into each
            for x in sorted(v, key=lambda element: element.get('id')):
                data.extend(hashable_data(x))
        else:
            # Include the string value.
            data.append(str(v))
    return data


def hash_entry(entry):
    """Return the hex encoded digest for entry."""
    if entry is not None:
        data = hashable_data(model_to_dict(entry))
        hash = entry_hash()
        for d in data:
            hash.update(d.encode())
        return hash.hexdigest()


@app.template_filter('markdown')
def markdown_filter(md):
    return markdown(md)


def entry_type(entry):
    return type(entry).__name__


@site.context_processor
def entry_processor():
    return dict(entry_type=entry_type,
                model_url=model_url,
                edit_url=edit_url)


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


def checked_field(entry, field, hash_field=None):
    """Return a dict with the field value and checksum from entry.

    Assumes the checksum field is field_hash unless specified otherwise.

    """
    return {
        'url': getattr(entry, field),
        'checksum': getattr(
            entry,
            hash_field if hash_field is not None else "{}_hash".format(field)
        )
    }


class ResourceView(MethodView):
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

    def prov_view(self, entry):
        # Build the RDF prov graph
        g = Graph()
        for t in self.graph(entry):
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

    def graph(self, entry):
        return entry.semantic_types(model_url(entry))


class EntryView(ResourceView):
    detail_template = 'entries/detail.html'
    model = None

    """Handle a single entry."""
    def get(self, entry_id=None):
        best = request.accept_mimetypes.best_match(["application/json",
                                                    "text/html"])
        if entry_id is None:
            entries = self.get_list()
            if best == "application/json":
                key = pluralise(entry_type(self.model))
                return jsonldify({
                    key: [self.summary(entry) for entry in entries]
                })
            elif best == "text/html":
                return render_template(
                    'entries/list.html',
                    entry_type=pluralise(self.model.__name__),
                    entries=entries
                )
            else:
                return NotAcceptable
                pass
        else:
            version = request.args.get('version')
            try:
                entry = self.get_one(entry_id, version)
            except:
                abort(404)
            if request.url.endswith('/prov'):
                return self.prov_view(entry)
            elif best == "application/json":
                return jsonldify(self.for_api(entry))
            elif best == "text/html":
                return render_template(self.detail_template,
                                       **self.detail_template_args(entry))
            else:
                return NotAcceptable

    def post(self):
        """Add the new entry."""
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
            resp.location = model_url(entry)
            return resp

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
                    entry_type=type(entry).__name__)

    def summary(self, entry):
        """Return a dict view summarizing entry (e.g. for listings)."""
        return model_to_dict(entry)

    def for_api(self, entry):
        """Return a dict view of entry suitable for JSON."""
        return self.summary(entry)

    def get_one(self, entry_id, version=None):
        """Query model for the entry with id and optionally a version.

        If a version is specified, return the corresponding entry. If no
        version is specified, return the entry with id *as long as it's the
        latest version*.

        """
        if version is None:
            entry = self.model.get((self.model.id == entry_id))
            if entry and entry.latest.id != entry.id:
                raise DoesNotExist
        else:
            entry = self.model.get((self.model.latest == entry_id) &
                                   (self.model.version == version))
        return entry

    def get_list(self):
        """Return a list of latest entries for this model."""
        return self.model.select().where(self.model.id == self.model.latest)


class ProblemView(EntryView):
    detail_template = 'entries/problem_detail.html'
    model = Problem


class SolutionView(EntryView):
    detail_template = 'entries/solution_detail.html'
    model = Solution

    def get(self, entry_id=None):
        self.problem_id = request.args.get("problem")
        return super().get(entry_id)

    def get_list(self):
        """Optionally filter by problem."""
        query = super().get_list()
        if self.problem_id is not None:
            query = query.where(Solution.problem == self.problem_id)
        return query

    def graph(self, entry):
        g = super().graph(entry)
        solution = URIRef(model_url(entry))
        for t in entry.deps:
            if isinstance(t, Toolbox):
                g.add((solution, PROV.wasDerivedFrom, URIRef(model_url(t))))
        g.add((solution,
               PROV.wasDerivedFrom,
               URIRef(model_url(entry.problem))))
        return g


class ToolboxView(EntryView):
    detail_template = 'entries/toolbox_detail.html'
    model = Toolbox


class UserView(ResourceView):
    def get(self, user_id):
        best = request.accept_mimetypes.best_match(["application/json",
                                                    "text/html"])
        if user_id is None:
            # Return a list of users
            # TODO: restrict this based on user authorisation?
            users = User.select()
            if best == "application/json":
                return jsonldify(dict(
                    users=[self.for_api(user) for user in users]
                ))
            elif best == "text/html":
                return render_template('user_list.html', users=users)
            else:
                return NotAcceptable
        else:
            user = User.get(User.id == user_id)
            if not user:
                abort(404)
            entries = []
            entries.extend(Problem
                           .select()
                           .join(User)
                           .where(User.id == user.id))
            entries.extend(Solution
                           .select()
                           .join(User)
                           .where(User.id == user.id))
            entries.extend(Toolbox
                           .select()
                           .join(User)
                           .where(User.id == user.id))
            if best == "application/json":
                return jsonldify(self.for_api(user))
            elif best == "text/html":
                return render_template(
                    'user_detail.html',
                    user=user,
                    entries=entries
                )
            else:
                return NotAcceptable


class LicenseView(ResourceView):
    def get(self, license_id):
        if license_id is None:
            licenses = License.select()
            return jsonldify(dict(
                licenses=[self.for_api(license) for license in licenses]
            ))
        else:
            license = License.get(License.id == license_id)
            if not license:
                abort(404)
            return jsonldify(self.for_api(license))


# Dispatch to json/html views
def register_api(model, view, endpoint, url, pk='id', pk_type='int'):
    """Register the rules for a model api."""
    _model_api[model] = (endpoint, url, pk, pk_type)
    view_func = view.as_view(endpoint)
    site.add_url_rule(url, defaults={pk: None},
                      view_func=view_func, methods=['GET'])
    site.add_url_rule(url, view_func=view_func, methods=['POST'])
    site.add_url_rule('{}<{}:{}>'.format(url, pk_type, pk),
                      view_func=view_func, methods=['GET', 'PUT', 'DELETE'])
    prov_view_func = view.as_view(endpoint + '_prov')
    site.add_url_rule('{}<{}:{}>/prov'.format(url, pk_type, pk),
                      view_func=prov_view_func, methods=['GET'])


register_api(Toolbox, ToolboxView, 'toolbox_api', '/toolboxes/', pk='entry_id')
register_api(Problem, ProblemView, 'problem_api', '/problems/', pk='entry_id')
register_api(Solution, SolutionView, 'solution_api', '/solutions/', pk='entry_id')
register_api(User, UserView, 'user_api', '/users/', pk='user_id')
register_api(License, LicenseView, 'license_api', '/licenses/', pk='license_id')


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
