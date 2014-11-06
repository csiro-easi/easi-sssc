from app import app
from flask.ext.admin import Admin
from flask.ext.admin.contrib.peewee import ModelView
from flask.ext.admin.contrib.peewee.form import CustomModelConverter
from models import User, Problem, Solution, Toolbox, Image, ToolboxImage, SolutionImage, Dependency, SolutionDependency, ToolboxDependency, Var, JsonField
from wtforms import fields

admin = Admin(app)


class VarValuesConverter(CustomModelConverter):
    def __init__(self, view, additional=None):
        super().__init__(view, additional)
        self.converters[JsonField] = self.handle_json

    def handle_json(self, model, field, **kwargs):
        return field.name, fields.TextField(**kwargs)


# Add admin views here
class UserAdmin(ModelView):
    pass


class ProblemAdmin(ModelView):
    pass


class SolutionAdmin(ModelView):
    model_form_converter = VarValuesConverter
    inline_models = (SolutionDependency, SolutionImage, Var)


class ToolboxAdmin(ModelView):
    inline_models = (ToolboxDependency, ToolboxImage)


admin.add_view(UserAdmin(User))
admin.add_view(ProblemAdmin(Problem))
admin.add_view(SolutionAdmin(Solution))
admin.add_view(ToolboxAdmin(Toolbox))
