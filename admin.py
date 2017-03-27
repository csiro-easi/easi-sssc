from flask import abort, redirect, request, url_for
from flask_admin import Admin, helpers as admin_helpers
from flask_admin.contrib.peewee import ModelView
from flask_admin.contrib.peewee.form import CustomModelConverter
from flask_security import current_user
from wtforms import fields
from app import app
from security import security, is_admin, is_user
from models import Problem, Solution, Toolbox, User, \
    SolutionDependency, ToolboxDependency, \
    SolutionImage, ToolboxImage, \
    SolutionVar, ToolboxVar, JsonField

admin = Admin(app)


class VarValuesConverter(CustomModelConverter):
    def __init__(self, view, additional=None):
        super().__init__(view, additional)
        self.converters[JsonField] = self.handle_json

    def handle_json(self, model, field, **kwargs):
        return field.name, fields.TextField(**kwargs)


class ProtectedModelView(ModelView):
    """Limit access the admin views.

    Require user to be authenticated to access these views at all.

    Restrict the entries available for admin by a regular user to their own,
    while allowing admin users to administer everything.

    """
    # Restrict access generally to active and authenticated users
    def is_accessible(self):
        return (current_user.is_active and
                current_user.is_authenticated and
                is_user())

    def _handle_view(self, name, **kwargs):
        """Override to redirect users when a view is not accessible."""
        if not self.is_accessible():
            if current_user.is_authenticated:
                # permission denied
                abort(403)
            else:
                # login
                return redirect(url_for('security.login', next=request.url))


# Add admin views here
class UserAdmin(ProtectedModelView):
    # Only allow admins to access the User admin views
    def is_accessible(self):
        return is_admin()


def _clone_model(model):
    """Create and return a clone of model.

    Save a clone of entry in the database, including all reverse relations
    (Vars, Deps etc).

    """
    # Copy current data
    data = dict(model._data)
    # clear the primary key
    data.pop(model._meta.primary_key.name)
    # Create the new entry
    # TODO handle unique id/entry combo!
    copy = type(model).create(**data)
    # Update references in copied relations to point to the clone
    for n, f in copy._meta.reverse_rel.items():
        for x in getattr(copy, n):
            setattr(x, f.name, copy)
    copy.save()
    return copy


def _update_entry_history(entry):
    """Capture the current state of entry before it's updated.

    Then increment the version number for entry.

    """
    # Find the old state of entry in the db
    E = type(entry)
    old_entry = E.get(E.id == entry.id)
    _clone_model(old_entry)
    entry.version = entry.version + 1


class EntryModelView(ProtectedModelView):
    """View for administering all Entries.

    Control access to entries based on user authorisation.

    Handles versioning of entries as they are created and modified.

    TODO: Decide on whether/how to limit deletion

    """
    form_excluded_columns = ['author', 'version']

    # If user does not have the 'admin' role, only allow them to administer
    # their own views.
    def get_query(self):
        # Start with the default query
        query = super().get_query()

        # Limit results to those owned by a regular users
        if not is_admin():
            query = query.where(self.model._meta.fields['author'] ==
                                current_user.id)

        return query

    def get_one(self, id):
        # Default is to try to retrieve entry with id.
        it = super().get_one(id)

        # If we found the entry, throw not authorized if it's not for the
        # current user and they're not at admin
        if not is_admin() and (it.author.id != current_user.id):
            abort(403)

        return it

    def on_model_change(self, form, model, is_created):
        """Maintain model metadata."""
        if is_created:
            model.author = current_user.id
        else:
            _update_entry_history(model)


class ProblemAdmin(EntryModelView):
    pass


class SolutionAdmin(EntryModelView):
    model_form_converter = VarValuesConverter
    inline_models = (SolutionDependency, SolutionImage, SolutionVar)


class ToolboxAdmin(EntryModelView):
    inline_models = (ToolboxDependency, ToolboxImage, ToolboxVar)


admin.add_view(UserAdmin(User))
admin.add_view(ProblemAdmin(Problem))
admin.add_view(SolutionAdmin(Solution))
admin.add_view(ToolboxAdmin(Toolbox))


# Integrate flask-admin and flask-security
@security.context_processor
def security_context_processor():
    return dict(
        admin_base_template=admin.base_template,
        admin_view=admin.index_view,
        h=admin_helpers,
        get_url=url_for
    )
