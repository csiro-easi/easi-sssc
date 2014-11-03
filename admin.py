from app import app
from flask.ext.admin import Admin
from flask.ext.admin.contrib.peewee import ModelView
from models import User, Problem, Solution, Toolbox

admin = Admin(app)


# Add admin views here
class UserAdmin(ModelView):
    pass


class ProblemAdmin(ModelView):
    pass


class SolutionAdmin(ModelView):
    pass


class ToolboxAdmin(ModelView):
    pass


admin.add_view(UserAdmin(User))
admin.add_view(ProblemAdmin(Problem))
admin.add_view(ProblemAdmin(Solution))
admin.add_view(ProblemAdmin(Toolbox))
