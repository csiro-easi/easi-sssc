from app import app
from flask.ext.admin import Admin
from flask.ext.admin.contrib.peewee import ModelView
from models import User, Problem, Solution, Toolbox, Image, ToolboxImage, SolutionImage, Dependency, SolutionDependency, ToolboxDependency, Var

admin = Admin(app)


# Add admin views here
class UserAdmin(ModelView):
    pass


class ProblemAdmin(ModelView):
    pass


class SolutionAdmin(ModelView):
    inline_models = (SolutionDependency, SolutionImage, Var)


class ToolboxAdmin(ModelView):
    inline_models = (ToolboxDependency, ToolboxImage)


admin.add_view(UserAdmin(User))
admin.add_view(ProblemAdmin(Problem))
admin.add_view(SolutionAdmin(Solution))
admin.add_view(ToolboxAdmin(Toolbox))
