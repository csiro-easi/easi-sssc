from datetime import datetime, date, time
from flask import (Blueprint, request, render_template, url_for,
                   jsonify, make_response, abort, redirect, flash)
from flask.json import JSONEncoder
from flask.views import MethodView
from flask_security import current_user
from flask_security.decorators import auth_required, roles_accepted
from functools import wraps
from markdown import markdown
from peewee import SelectQuery, DoesNotExist
from rdflib import BNode, URIRef
from rdflib.namespace import RDF
from urllib.parse import parse_qs, urlparse
from werkzeug.exceptions import BadRequest, InternalServerError, NotAcceptable
from werkzeug.routing import RequestRedirect, MethodNotAllowed, NotFound

from api import get_exposed
from app import app, attachments
import models
from models import db, Toolbox, Entry, Problem, Solution, text_search, \
    is_latest, is_unpublished, User, clone_model, \
    License, BaseModel, Role, Dependency, Signature, PublicKey, \
    ProblemSignature, ToolboxSignature, SolutionSignature, Review, \
    UploadedResource, ProblemAttachment, ToolboxAttachment, SolutionAttachment
from security import is_admin, PublishEntryPermission, \
    ViewUnpublishedPermission
from signatures import verify_signature
from namespaces import PROV

site = Blueprint('site', __name__, template_folder='templates')


class SSSCJSONEncoder(JSONEncoder):
    """Override default flask JSON encoder with SSSC API defaults.

    1. Serialise dates and times as iso8601 strings
    2. Sort dictionary entries by key

    """
    # Sort keys by default
    def __init__(self, skipkeys=False, ensure_ascii=True,
                 check_circular=True, allow_nan=True, sort_keys=True,
                 indent=None, separators=None, encoding='utf-8', default=None,
                 use_decimal=True, namedtuple_as_object=True,
                 tuple_as_array=True, bigint_as_string=False,
                 item_sort_key=None, for_json=False, ignore_nan=False,
                 int_as_string_bitcount=None, iterable_as_array=False):
        super().__init__(skipkeys=skipkeys, ensure_ascii=ensure_ascii,
                         check_circular=check_circular, allow_nan=allow_nan,
                         sort_keys=sort_keys, indent=indent,
                         separators=separators, encoding=encoding,
                         default=default, use_decimal=use_decimal,
                         namedtuple_as_object=namedtuple_as_object,
                         tuple_as_array=tuple_as_array,
                         bigint_as_string=bigint_as_string,
                         item_sort_key=item_sort_key, for_json=for_json,
                         ignore_nan=ignore_nan,
                         int_as_string_bitcount=int_as_string_bitcount,
                         iterable_as_array=iterable_as_array)

    def default(self, o):
        if (isinstance(o, datetime) or
            isinstance(o, date) or
            isinstance(o, time)):
            return o.isoformat()

        return JSONEncoder.default(self, o)


# Configure the app to use our encoder by default
app.json_encoder = SSSCJSONEncoder


# Connect to the database now to catch any errors here
@app.before_first_request
def first_setup():
    print("Setting up")
    db.connect()


# These will be updated with model views after those are defined.
#
# Keys are model classes.
# Values are tuples (endpoint, url, pk, pk_type)
_model_api = {}


_jsonld_context = {
    "prov": "http://www.w3.org/ns/prov#"
}


boolean_true_strings = frozenset({
    'yes',
    'true',
    '1',
    'y',
    't'
})

boolean_false_strings = frozenset({
    'no',
    'false',
    '0',
    'n',
    'f'
})


def parse_boolean_param(value):
    """Parse query parameter value as a boolean."""
    if value is not None:
        if isinstance(value, str):
            if value in boolean_true_strings:
                return True
            elif value in boolean_false_strings:
                return False
        else:
            return bool(value)

    # Could not determine a boolean value.
    return None


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
        pk_id = (model.entry_id
                 if hasattr(model, 'entry_id')
                 else model.id)
        model_class = type(model)
        model_version = (model.version if hasattr(model, 'version')
                         else None)
        args = {model_pk(model_class): pk_id}
        # Is it an Entry?
        if issubclass(model_class, Entry):
            if version is not None:
                args['version'] = version
            elif pinned or not is_latest(model):
                args['version'] = model_version

        # Determine endpoint to use
        if endpoint is None:
            endpoint = model_endpoint(model_class)

        # Flask appears to use the url defaults associated with the current
        # request context, so urls generated while serving a POST request will
        # use the POSTing style (e.g. /problems/?entry_id=42). Use GET method
        # defaults for generated URLs unless explicitly overridden in the call
        # to this function.
        _method = kwargs.pop('_method', 'GET')
        args.update(_method=_method, **kwargs)

        # Generate and return the URL
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


def action_url(action, entry):
    """Return the URL for action on entry."""
    if entry and action:
        endpoint = "site.{}_entry".format(action)
        return url_for(endpoint, _external=True, entry=model_url(entry))


def file_url(attachment):
    """Return the url for an attached file."""
    return attachments.url(attachment.filename)


# These fields should *never* be returned to clients
_hidden_fields = set([
    User.password,
    Problem.problemindex_set,
    Solution.solutionindex_set,
    Toolbox.toolboxindex_set,
    Signature.problemsignature_set,
    Signature.toolboxsignature_set,
    Signature.solutionsignature_set,
    Review.problemreview_set,
    Review.toolboxreview_set,
    Review.solutionreview_set,
    Problem.problemreview_set,
    Toolbox.toolboxreview_set,
    Solution.solutionreview_set,
    UploadedResource.problemattachment_set,
    UploadedResource.toolboxattachment_set,
    UploadedResource.solutionattachment_set
])

_internal_identifiers = set([
    User.id,
    Role.id,
    Problem.id,
    Toolbox.id,
    Solution.id,
    License.id,
    Dependency.id,
    PublicKey.id,
    UploadedResource.id
])

# These fields should usually be returned as refs, not nested
_default_refs = set([
    Problem.latest,
    Problem.solutions,
    Problem.versions,
    Problem.signatures,
    Toolbox.latest,
    Toolbox.versions,
    Toolbox.signatures,
    Solution.latest,
    Solution.problem,
    Solution.versions,
    Solution.signatures,
    UploadedResource.user
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
    User.toolboxes,
    User.public_keys
])


def _clone_set(s, default=None):
    if s:
        return set(s)
    elif default is not None:
        return set(default)
    return set()


def model_to_dict(model, seen=None, exclude=None, extra=None, refs=None,
                  max_depth=None, include_nulls=False, include_ids=False):
    """Return a dict view of model, suitable for the API. """
    max_depth = -1 if max_depth is None else max_depth

    # Set up fields to extract, include some sensible defaults for the API
    refs = _clone_set(refs, _default_refs)
    exclude = _clone_set(exclude, _default_exclude)
    seen = _clone_set(seen)

    # Never expose certain fields!
    exclude |= _hidden_fields
    exclude |= seen
    if not include_ids:
        exclude |= _internal_identifiers

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
        # Carsten: Needs to be sorted to guarantee deterministic JSON for hashing
        data['@type'] = sorted(t.n3(g.namespace_manager)
                               for t in g.objects(subject=subject,
                                                  predicate=RDF.type))

    # Include exposed fields for the api
    for k, v in get_exposed(model, parent_handler=model_url).items():
        if isinstance(v, BaseModel):
            v = model_to_dict(v,
                              seen=seen,
                              exclude=exclude,
                              extra=extra,
                              refs=refs,
                              max_depth=max_depth - 1,
                              include_nulls=include_nulls,
                              include_ids=include_ids)
        elif isinstance(v, list) or isinstance(v, tuple):
            v = [model_to_dict(x,
                               seen=seen,
                               exclude=exclude,
                               extra=extra,
                               refs=refs,
                               max_depth=max_depth - 1,
                               include_nulls=include_nulls,
                               include_ids=include_ids)
                 for x in v]
        data[k] = v

    # Iterate over fields of model
    foreign = set(model._meta.rel.values())
    for f in model._meta.declared_fields:
        # Exclude specified fields. Don't include 'id' fields unless explicitly
        # requested.
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
                        extra=extra,
                        refs=refs,
                        max_depth=max_depth - 1,
                        include_nulls=include_nulls,
                        include_ids=include_ids
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
                    extra=extra,
                    refs=refs,
                    max_depth=max_depth - 1,
                    include_nulls=include_nulls,
                    include_ids=include_ids
                ))
        data[related_name] = accum

    # Add any extra fields
    if extra:
        for prop in extra:
            value = getattr(model, prop, None)
            if value is not None:
                if isinstance(value, BaseModel):
                    # Should this be a reference?
                    if prop in refs:
                        value = model_url(value)
                    else:
                        # If it's got any references to model, exclude them
                        ref = value._meta.rel_for_model(model_class)
                        if not ref:
                            ref = value._meta.reverse_rel_for_model(model_class)
                        if ref:
                            seen.add(ref)
                        value = model_to_dict(value,
                                              seen=seen,
                                              exclude=exclude,
                                              extra=extra,
                                              refs=refs,
                                              max_depth=max_depth - 1,
                                              include_nulls=include_nulls,
                                              include_ids=include_ids)
                data[prop] = value

    return data


def entry_type(entry):
    return type(entry).__name__


def parse_review_request(request):
    """Parse review data in request and return data and any errors."""
    errors = None

    # Extract the data from json or a form
    if request.is_json:
        data = request.get_json()
    else:
        form = request.form
        data = dict()
        if 'comment' in form:
            data['comment'] = form['comment'].strip()
        if 'rating' in form:
            data['rating'] = int(form['rating'])

    # Make sure we have the required fields
    if not data.get('comment') and not data.get('rating'):
        errors = dict(
            rating='Review submission requires at least a comment or rating.',
            comment='Review submission requires at least a comment or rating.'
        )

    return data, errors


def save_review(data, entry):
    """Save review instance and associate it with entry."""
    rel = None

    # Create a new <Entry>Review instance
    rel_class_name = "{}Review".format(entry_type(entry))
    try:
        # Make sure we have the rel class
        rel_class = getattr(models, rel_class_name)
        if not rel_class:
            raise ValueError(
                '{} is not a valid entry-review relation class name.'
                .format(rel_class_name)
            )

        # Create and return the review instance.
        review = Review.create(reviewer=current_user.id, **data)

        # Associate review with entry
        rel = rel_class.create(review=review, entry=entry)
    except Exception as ex:
        raise InternalServerError('Failed to save review: {}'.format(str(ex)))

    return review


@app.template_filter('markdown')
def markdown_filter(md):
    return markdown(md)


@app.template_filter('latest_only')
def latest_only(entries):
    """Return a new list consisting of only the latest versions of entries."""
    if entries:
        return filter(is_latest, entries)


def can_publish(entry):
    """Return True if the current user can publish entry."""
    return PublishEntryPermission(entry.id).can()


@site.context_processor
def entry_processor():
    return dict(entry_type=entry_type,
                model_url=model_url,
                edit_url=edit_url,
                action_url=action_url,
                file_url=file_url,
                can_publish=can_publish)


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
                for k, v in _jsonld_context.items():
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


def require_mimetypes(*mimetypes):
    """Decorator that specifies valid mimetypes for view func.

    Abort with a 415 error if an invalid content-type is requested.

    """
    def wrapper(fn):
        @wraps(fn)
        def decorated_view(*args, **kwargs):
            if request.content_type not in mimetypes:
                abort(415)
            return fn(*args, **kwargs)
        return decorated_view
    return wrapper


def best_mimetype(*mimetypes, default=None, request_obj=None):
    """Return best content type to return for request.

    If request_obj is None, must be called in the context of a request handler,
    where a request variable is available.

    """
    if request_obj is None:
        request_obj = request
    # Is there an explicit request?
    #
    # This is a temporary fix to allow an explicit 'mimetype' parameter in the
    # request arguments. This shouldn't be required once explicit api endpoints
    # are created, and the main URLs can redirect to them using standard content
    # negotiation.
    best = request_obj.args.get('mimetype')
    if not best:
        # Do the usual content negotiation dance.
        best = request_obj.accept_mimetypes.best_match(mimetypes,
                                                       default=default)
    return best


def get_view_func(url, method='GET'):
    """Return the view function and arguments matching url, or None."""
    adapter = app.url_map.bind(app.config['SERVER_NAME'])

    try:
        match = adapter.match(url, method=method)
    except RequestRedirect as e:
        # Recursively match redirects
        return get_view_func(e.new_url, method)
    except (MethodNotAllowed, NotFound):
        # no match
        return None

    try:
        # return the view function and arguments
        return app.view_functions[match[0]], match[1]
    except KeyError:
        # No view is associated with the endpoint
        return None


def get_models_for_url(url, method='GET'):
    """Return the model(s) identified by url, or None.

    Match url to a view function, then call the corresponding getter on the
    view class with the url and query parameters.

    """
    # Parse url to extract the path and query components.
    parsed_url = urlparse(url)
    # Strip singleton query param values out of the lists that parse_qs returns
    # them in, e.g. {'foo': ['bar']} => {'foo': 'bar'}.
    query = {k: v[0] if len(v) == 1 else v
             for k, v in parse_qs(parsed_url.query).items()}

    # Look for view function matching url path
    match = get_view_func(parsed_url.path, method=method)
    if not match:
        return None
    view_func, view_args = match

    # Merge any query params with view_args
    query.update(view_args)

    # Find the view class and call the model lookup function for view_func.
    return view_func.view_class.get_models(**query)


def ensure_entry(uri):
    """Ensure uri identifies an existing entry, and return Entry.

    Raise NotFound if no entry exists for uri.

    """
    entry = get_models_for_url(uri)
    if entry:
        if isinstance(entry, Entry):
            return entry
        else:
            raise NotFound('URI does not identify a unique Entry ({})'
                           .format(uri))
    raise NotFound('Entry not found for uri ({})'.format(uri))


# ======================================================================
#
# Resources API
#
# ======================================================================

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

    api_fields = {}

    def prov_view(self, entry):
        # Build the RDF prov graph
        g, subject = self.graph(entry)
        # Return the appropriate serialization
        best = best_mimetype("application/ld+json",
                             "application/json",
                             "text/turtle",
                             "application/rdf+xml")
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
        """Return the RDF graph for this resource, and the subject reference.

        If it's an identified object, use its URI as the subject (a URIRef) for
        the graph, otherwise create a new BNode to represent it.

        Either way return a tuple (graph, subject).

        """
        subject = model_url(entry)
        if subject:
            subject = URIRef(subject)
        else:
            subject = BNode()
        return entry.semantic_types(subject), subject

    def is_update_allowed(resource, key):
        """Return True if current user can update key for resource.

        Base requirement is for an authenticated admin user.

        """
        return (current_user.is_active and
                current_user.is_authenticated and
                is_admin())

    def update_resource(self, resource, data):
        """Update resource instance using entries in data dict.

        Default behaviour is to match keys in data to fields on resource, and
        update with the corresponding values from data.

        For field specific handling, or to implement an API field that does not
        directly correspond to a model field, subclasses can provide a method
        named "_handle_update_<key>". If such a method exists, it will be
        called as self._handle_update_<key>(resource, data, key) instead of the
        default behaviour.

        """
        if resource is None:
            app.logger.warn('Null resource passed to ResourceView.update_resource')
            return
        if not data:
            return

        for key in data:
            if self.is_update_allowed(resource, key):
                # Check for handler or use default
                handler = getattr(self, '_handle_update_' + key, None)
                if handler is None:
                    handler = self._handle_update
                handler(resource, data, key)

        # No exceptions raised? Save the resource.
        resource.save()

    def _handle_update(self, resource, data, key):
        """Default handler for updating key on resource using data.

        Find field on resource with name == key, then set value of that field
        on resource to data[key].

        """
        if key in resource._meta.fields:
            # If it's a foreign key, find the corresponding resource, otherwise
            # update the value.
            if key in resource._meta.rel:
                raise NotImplementedError
            else:
                setattr(resource, key, data[key])
        elif key in resource._meta.reverse_rel:
            # Merge in values for keys
            raise NotImplementedError
        else:
            raise KeyError('Unknown field "{}" in {} API.'
                           .format(key, type(resource).__name__))


class EntryView(ResourceView):
    detail_template = 'entries/detail.html'
    model = None

    """Handle a single entry."""
    def get(self, entry_id=None):
        best = best_mimetype("application/json", "text/html")
        if entry_id is None:
            entries = self.get_list()
            if best == "application/json":
                key = pluralise(self.model.__name__)
                return jsonldify({
                    key: [model_to_dict(entry) for entry in entries]
                })
            elif best == "text/html":
                entries_url = url_for(model_endpoint(self.model),
                                      _external=True,
                                      mimetype='application/json')
                return render_template(
                    'entries/list.html',
                    entry_type=pluralise(self.model.__name__),
                    entries_url=entries_url,
                    entries=entries
                )
            else:
                return NotAcceptable
                pass
        else:
            version = request.args.get('version')
            entry = self.get_one(entry_id, version)
            if not entry:
                abort(404)
            if request.url.endswith('/prov'):
                return self.prov_view(entry)
            elif best == "application/json":
                # Do *not* include internal ids, except if requested using the
                # undocumented API.
                if request.args.get('_include_ids'):
                    entry_dict = model_to_dict(entry, include_ids=True)
                else:
                    entry_dict = model_to_dict(entry)
                return jsonldify(entry_dict)
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

    @auth_required('token', 'session', 'basic')
    @roles_accepted('user', 'moderator', 'admin')
    def patch(self, entry_id):
        """Update a single entry."""
        # Check entry is valid
        version = request.args.get('version')
        entry = self.get_one(entry_id, version=version)
        if not entry:
            abort(404)

        # Ensure the user has the correct permissions for the current configuration
        if not PublishEntryPermission(entry_id).can():
            abort(403)

        # Get the request payload
        data = request.get_json()
        if not data:
            return 'No JSON content found in request.', 400, None

        # Support updating published field only for now
        if len(data) != 1 or 'published' not in data:
            return 'The "published" field is the only one that can be updated using PATCH on an entry.', 400, None

        # Update the entry
        published = parse_boolean_param(data.get('published'))
        if published is not None:
            entry.published = published
            entry.save()
            return jsonldify(model_to_dict(entry))

        # Failed to update
        abort(422)

    def delete(self, entry_id):
        """Delete an entry."""
        id = None
        version = request.args.get('version')
        entry = self.get_one(entry_id, version=version)
        if entry:
            id = entry.id
            entry.delete()
        else:
            abort(404)
        return id

    def detail_template_args(self, entry):
        return dict(entry=entry,
                    entry_type=type(entry).__name__)

    @classmethod
    def get_one(cls, entry_id, version=None, **kwargs):
        """Query model for the entry with id and optionally a version.

        If a version is specified, return the corresponding entry. If no
        version is specified, return the entry with id *as long as it's the
        latest version*.

        """
        model = cls.model
        try:
            if version is None:
                entry = model.get(
                    (model.id == entry_id) &
                    (model.latest == None)
                )
            else:
                entry = model.get(
                    (model.version == version) &
                    ((model.latest == entry_id) |
                     (model.latest == None))
                )
        except DoesNotExist:
            return None

        if entry and not entry.published:
            if (current_user.is_anonymous or
                (entry.author.id != current_user.id and
                 not ViewUnpublishedPermission.can())):

                return None

        return entry

    @classmethod
    def get_list(cls, **kwargs):
        """Return a list of latest entries for this model.

        Does not include unpublished entries unless the current user has
        permission to view unpublished entries, or they belong to the current
        user.

        """
        model = cls.model
        constraints = (model.latest == None)

        # Only return published entries, and those belonging to the current
        # user, unless the user has permission to view unpublished ones.
        if not ViewUnpublishedPermission.can():
            published_or_owned = (model.published == True)
            if not current_user.is_anonymous:
                published_or_owned = (published_or_owned |
                                      (model.author == current_user.id))
            constraints = constraints & published_or_owned

        return model.select().where(constraints)

    @classmethod
    def get_models(cls, entry_id=None, **kwargs):
        """Return the model(s) for entry_id and version."""
        if id is None:
            return cls.get_list(**kwargs)
        else:
            return cls.get_one(entry_id, **kwargs)


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
        g, solution = super().graph(entry)
        for t in entry.deps:
            if isinstance(t, Toolbox):
                g.add((solution, PROV.wasDerivedFrom, URIRef(model_url(t))))
        g.add((solution,
               PROV.wasDerivedFrom,
               URIRef(model_url(entry.problem))))
        return g, solution


class ToolboxView(EntryView):
    detail_template = 'entries/toolbox_detail.html'
    model = Toolbox


class UserView(ResourceView):
    modifiable_fields = ['name', 'email', 'public_key']

    def get(self, user_id):
        best = best_mimetype("application/json", "text/html")
        if user_id is None:
            # Return a list of users
            # TODO: restrict this based on user authorisation?
            users = User.select()
            if best == "application/json":
                return jsonldify(dict(
                    users=[model_to_dict(user) for user in users]
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
                return jsonldify(model_to_dict(user, extra=['public_key']))
            elif best == "text/html":
                return render_template(
                    'user_detail.html',
                    user=user,
                    entries=sorted(entries,
                                   key=lambda e: e.created_at,
                                   reverse=True)
                )
            else:
                return NotAcceptable

    def post(self):
        """Register a new user."""
        pass

    @auth_required('token', 'session', 'basic')
    @require_mimetypes('application/json',
                       'application/merge-patch+json')
    def patch(self, user_id):
        """Update an existing user.

        Can only be used to update name or public key.

        """
        # Make sure they specified a user...
        if user_id is None:
            return 'PUT request is invalid for /users collection', 400, None

        # ...that exists.
        user = User.get(User.id == user_id)
        if not user:
            abort(404)

        # Make sure we have json, and parse request data for updates
        data = request.get_json()
        if not data:
            return 'No JSON content found in request.', 400, None

        # Update the resource
        self.update_resource(user, data)
        return self.get(user_id=user_id)

    @auth_required('token', 'session', 'basic')
    @roles_accepted('admin', 'user')
    @require_mimetypes('application/json', 'text/plain')
    def put(self, user_id, prop=None):
        """Set a new public key for user."""
        if user_id is None:
            abort(400)

        if prop != 'public_key':
            raise NotImplementedError

        user = User.get(User.id == user_id)
        if not user:
            abort(404)

        if not self.is_update_allowed(user, prop):
            abort(403)

        if request.is_json:
            data = request.get_json()
            if not data:
                return 'No JSON content found in request.', 400, None
            key_data = data.get('key')
        else:
            key_data = request.data

        new_key = PublicKey(user=user, key=key_data)
        new_key.save()
        return self.get(user_id=user_id)

    def is_update_allowed(self, user, key):
        """Only the user themselves (or an admin) can update some fields"""
        return (current_user.is_authenticated and
                current_user.is_active and
                (is_admin() or current_user.id == user.id) and
                key in self.modifiable_fields)

    def _handle_update_public_key(self, user, data, key):
        """Create new PublicKey resource as the current key for user."""
        if key != 'public_key':
            raise ValueError('Invalid key () used to invoke UserView._handle_'
                             'update_public_key'.format(key))

        key_data = data[key]
        if not key_data:
            raise ValueError('Empty public key in user PATCH request.')

        new_key = PublicKey(user=user, key=key_data)
        new_key.save()


class LicenseView(ResourceView):
    def get(self, license_id):
        if license_id is None:
            licenses = License.select()
            return jsonldify(dict(
                licenses=[model_to_dict(license) for license in licenses]
            ))
        else:
            license = License.get(License.id == license_id)
            if not license:
                abort(404)
            return jsonldify(model_to_dict(license))


def signature_relation(entry):
    """Return the signature relation for entry and fk."""
    fk = entry._meta.reverse_rel.get('signatures')
    if fk:
        return fk.model_class, fk.name


class SignatureView(ResourceView):
    def get(self, signature_id):
        if signature_id is None:
            signatures = Signature.select()
            return jsonldify(dict(
                signatures=[model_to_dict(s) for s in signatures]
            ))
        else:
            signature = Signature.get(Signature.id == signature_id)
            if not signature:
                abort(404)
            best = best_mimetype('application/json', 'text/html')
            if best == 'text/html':
                return render_template('signature_detail.html',
                                       signature=signature)
            else:
                return jsonldify(model_to_dict(signature,
                                               extra=['entry'],
                                               refs=['entry']))

    @auth_required('token', 'session', 'basic')
    def post(self):
        data = request.get_json()
        signed_string = data.get('signed_string')
        signature = data.get('signature')
        uri = data.get('entry_id')
        if signed_string is None or signature is None or uri is None:
            return "Request parameter(s) missing", 400
        # Find the Entry to link it to
        entry = get_models_for_url(uri)
        if not entry:
            return "Entry for signature could not be found", 404

        sig_fields = signed_string.split('$')

        if len(sig_fields) != 2:
            return "Signable string not of correct form 'hash$date'", 400

        now = datetime.utcnow()
        sign_time = datetime.strptime(sig_fields[1], "%Y-%m-%d %H:%M:%S")

        delta_t = now- sign_time

        if delta_t.total_seconds() > 5*60:
            return "Signature older than 5 minutes", 400

        entry_hash = sig_fields[0]

        # Make sure their hash is the same as our hash for the requested entry.
        # if entry_hash != entry_dict['entry_hash']:
        if entry_hash != entry.entry_hash:
            return "Client hash does not match saved hash.", 400
        # Verify the signature using the user's current public key
        public_key = current_user.public_key
        verified, verify_msg = verify_signature(signature,
                                                signed_string,
                                                public_key.key)
        if verified:
            rel_class, rel_field = signature_relation(entry)
            if rel_class:
                sig_instance = Signature(signature=signature,
                                         public_key=public_key,
                                         signed_string=signed_string)
                # Add the metadata
                sig_instance.user_id = User.get(User.id == current_user.id)
                sig_instance.save()
                # Link signature to entry
                rel = rel_class(signature=sig_instance)
                setattr(rel, rel_field, entry.id)
                rel.save()
                url = model_url(sig_instance)
                resp = make_response(url, 201)
                resp.location = url
                return resp

        return "Failed to verify signature with public key.", 400

    @auth_required('token', 'session', 'basic')
    @roles_accepted('admin')
    def delete(self, signature_id):
        """Delete the signature."""
        if signature_id is not None:
            signature = Signature.get(Signature.id == signature_id)
            if not signature:
                abort(404)

            # Clean up entry relation first
            # TODO: Push delete cascades into the db schema
            entry_rel = signature.get_entry_rel()
            entry_rel.delete_instance()
            rows = signature.delete_instance()
            return "Deleted {} entry".format(rows), 200

        return "Invalid signature_id ({})".format(signature_id), 400


# Dispatch to json/html views
def register_api(model, view, endpoint, url, pk='id', pk_type='int'):
    """Register the rules for a model api."""
    # Store model-to-endpoint mappings for later lookup
    if isinstance(model, list):
        models = model
    else:
        models = [model]
    for m in models:
        _model_api[m] = (endpoint, url, pk, pk_type)

    # Create standard REST endpoints
    view_func = view.as_view(endpoint)
    site.add_url_rule(url, defaults={pk: None},
                      view_func=view_func, methods=['GET'])
    site.add_url_rule(url, view_func=view_func, methods=['POST'])
    site.add_url_rule('{}<{}:{}>'.format(url, pk_type, pk),
                      view_func=view_func, methods=['GET', 'PATCH', 'DELETE'])
    site.add_url_rule('{}<{}:{}>/<{}:{}>'.format(url, pk_type, pk, 'string', 'prop'),
                      view_func=view_func, methods=['PUT'])

    # Prov endpoint
    prov_view_func = view.as_view(endpoint + '_prov')
    site.add_url_rule('{}<{}:{}>/prov'.format(url, pk_type, pk),
                      view_func=prov_view_func, methods=['GET'])


register_api(Toolbox, ToolboxView, 'toolbox_api', '/toolboxes/', pk='entry_id')
register_api(Problem, ProblemView, 'problem_api', '/problems/', pk='entry_id')
register_api(Solution, SolutionView, 'solution_api', '/solutions/', pk='entry_id')
register_api(User, UserView, 'user_api', '/users/', pk='user_id')
register_api(License, LicenseView, 'license_api', '/licenses/', pk='license_id')
register_api([ProblemSignature, ToolboxSignature, SolutionSignature, Signature],
             SignatureView, 'signature_api', '/signatures/', pk='signature_id')


# ======================================================================
#
# Actions API
#
# ======================================================================

@roles_accepted('admin', 'user')
@site.route('/edit/users/<int:user_id>')
def edit_user(user_id):
    """Editable user profile."""
    user = User.get(User.id == user_id)
    if not user:
        abort(404)

    if user.id != current_user.id and not current_user.has_role('admin'):
        abort(403)

    return render_template('edit_user_profile.html', user=user)


@site.route('/publish', methods=['GET'])
@auth_required('token', 'session', 'basic')
def publish_entry():
    """Publish an entry identified by uri.

    If the entry has already been published, do nothing but succeed.

    If it was a JSON request, return the entry data on success.

    For an HTML request redirect to the entry info page, with a success or
    error flash message as appropriate.

    """
    # Ensure the uri is a valid entry identifier, and retrieve the entry
    # instance.
    uri = request.args.get('entry')
    entry = get_models_for_url(uri)
    if not entry:
        abort(404)
    elif not isinstance(entry, Entry):
        return 'URI ({}) does not identify a unique entry.'.format(uri), 400

    # Make sure we have permission to publish the entry.
    if not PublishEntryPermission(entry.id).can():
        abort(403)

    # Publish the entry (if required), and return the current status of the
    # entry.
    try:
        if not entry.published:
            entry.published = True
            entry.save()
    except Exception as ex:
        flash('Failed to publish entry: {}'.format(str(ex)), 'error')
    else:
        flash('Entry was published successfully.')

    best = best_mimetype('application/json', 'text/html')
    if best == 'text/html':
        return redirect(model_url(entry))
    else:
        return jsonify(model_to_dict(entry))


@site.route('/review', methods=['GET', 'POST'])
@auth_required('token', 'session', 'basic')
def review_entry():
    """Review an entry.

    Takes a single query parameter 'entry' that is the URI for the entry to be
    reviewed.

    On GET, return the review submission page. On POST, submit a new review of
    entry.

    """
    uri = request.args.get('entry')
    entry = get_models_for_url(uri)
    if not entry:
        abort(404)
    elif not isinstance(entry, Entry):
        return "URI ({}) does not identify a unique entry.".format(uri), 400

    # Make sure we have permission to review the entry. Any registered user can
    # review a published entry, but only certain users can review an
    # unpublished entry.
    if (is_unpublished(entry) and
        not ViewUnpublishedPermission.can()):
        abort(403)

    # Dispatch on request type
    if request.method == 'GET':
        # Return the review form
        return render_template('entries/review.html',
                               entry=entry,
                               data={},
                               errors={})
    else:
        # Parse and save the review.
        data, errors = parse_review_request(request)
        if not errors:
            save_review(data, entry)

        # Redirect to the entry page or return the updated entry as
        # appropriate.
        best = best_mimetype('application/json', 'text/html')
        if best == 'text/html':
            if not errors:
                flash('Review added successfully')
                return redirect(model_url(entry))
            else:
                flash('Please fix the issue(s) with your review submission and try again.', 'error')
                return render_template('entries/review.html',
                                       entry=entry,
                                       data=data,
                                       errors=errors)
        else:
            if not errors:
                return jsonify(model_to_dict(entry))
            else:
                resp = jsonify(errors)
                resp.status_code = 400
                return resp


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


@site.route('/clone')
@auth_required('token', 'session', 'basic')
def clone_entry():
    """Create a clone of an Entry.

    Takes a single query parameter 'entry' that is the uri of the entry to be
    cloned. Creates a new entry that is almost identical to the original (does
    not have the same id, or associated signatures or version history) in the
    database.

    On success returns the uri of the new entry, or for an HTML request
    redirects to the edit page for the newly created entry.

    """
    # Ensure the uri is a valid entry identifier, and retrieve the entry
    # instance.
    uri = request.args.get('entry')
    entry = get_models_for_url(uri)
    if not entry:
        abort(404)
    elif not isinstance(entry, Entry):
        return 'URI ({}) does not identify a unique entry.'.format(uri), 400

    # Clone the entry, and return new entry on success.
    try:
        # Create the clone instance
        clone = clone_model(entry)

        # Reset the version info and metadata
        clone.author = current_user.id
        clone.created_at = datetime.now()
        clone.latest = None
        clone.version = 1
        clone.save()
    except Exception as ex:
        result = dict(message='Failed to clone entry: {}'.format(str(ex)),
                      category='error')
    else:
        result = dict(message='Successfully cloned entry.',
                      category='info',
                      uri=model_url(clone))

    best = best_mimetype('application/json', 'text/html')
    if best == 'text/html':
        flash(result['message'], result['category'])
        return redirect(edit_url(clone, url=result['uri']))
    else:
        response = jsonify(result)
        if result['category'] == 'error':
            response.status_code = 500
        return response


@site.route('/attach', methods=['GET', 'POST'])
@auth_required('token', 'session', 'basic')
def attach_files():
    """Upload attachment(s) for an entry.

    Expects a single parameter 'entry' that is the uri of the entry to attach
    the file(s) to.

    On success, returns the url of the uploaded file, or redirects to the
    attachments page for entry for an HTML request.

    """
    if request.method == 'POST' and 'file' in request.files:
        entry = ensure_entry(request.form.get('entry'))
        filestore = request.files['file']
        filename = attachments.save(filestore)

        # Use the original filename as the name for now
        name = filestore.filename

        # Create the upload object
        attachment = UploadedResource(filename=filename,
                                      name=name,
                                      user=current_user.id)
        attachment.save()
        flash('Attachment saved as {}'.format(name))

        # Store the association with entry.
        rel_class_name = '{}Attachment'.format(entry_type(entry))
        rel_class = getattr(models, rel_class_name)
        rel = rel_class.create(attachment=attachment, entry=entry)

        # Return or redirect as required
        best = best_mimetype('application/json', 'text/html')
        if best == 'text/html':
            return redirect(model_url(entry))
        else:
            return jsonify(attachment=attachments.url(attachment.filename))
    else:
        entry = ensure_entry(request.args.get('entry'))
        return render_template('attach.html', entry=entry)


@site.route('/')
def index():
    return render_template('index.html')


# Main site
app.register_blueprint(site)
