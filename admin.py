from flask import abort, redirect, request, url_for
from flask_admin import Admin, helpers as admin_helpers
from flask_admin.contrib.peewee import ModelView
from flask_admin.contrib.peewee.form import CustomModelConverter
from flask_security import current_user
from wtforms import fields
from app import app
from security import security, is_admin, is_user
from models import Problem, Solution, Toolbox, \
    SolutionDependency, ToolboxDependency, \
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
    pass


class ProblemAdmin(ProtectedModelView):
    pass


class SolutionAdmin(ProtectedModelView):
    model_form_converter = VarValuesConverter
    inline_models = (SolutionDependency, SolutionVar)


class ToolboxAdmin(ProtectedModelView):
    inline_models = (ToolboxDependency, ToolboxVar)


# admin.add_view(UserAdmin(User))
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
