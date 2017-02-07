from flask import abort, redirect, request, url_for
from flask_admin import Admin, helpers as admin_helpers
from flask_admin.contrib.peewee import ModelView
from flask_admin.contrib.peewee.form import CustomModelConverter
from flask_security import current_user
from wtforms import fields
from app import app
from security import security
from models import User, Problem, Solution, Toolbox, Dependency, SolutionToolbox, SolutionDependency, ToolboxToolbox, ToolboxDependency, Var, JsonField

admin = Admin(app)


class VarValuesConverter(CustomModelConverter):
    def __init__(self, view, additional=None):
        super().__init__(view, additional)
        self.converters[JsonField] = self.handle_json

    def handle_json(self, model, field, **kwargs):
        return field.name, fields.TextField(**kwargs)


class ProtectedModelView(ModelView):
    """Require login to access the admin views."""
    def is_accessible(self):
        return current_user.is_active and current_user.is_authenticated

    def _handle_view(self, name, **kwargs):
        """Override builtin _handle_view to redirect users when a view is not accessible."""
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
    inline_models = (SolutionDependency, SolutionToolbox, Var)


class ToolboxAdmin(ProtectedModelView):
    inline_models = (ToolboxDependency, ToolboxToolbox)


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
