from models import (Problem, Solution, Toolbox, Dependency, Var, Source,
                    ToolboxDependency, SolutionDependency, ToolboxToolbox, SolutionToolbox,
                    License)
from bootstrap import (create_problem, create_toolbox, create_solution,
                       solution_dep, toolbox_dep)

def create(user):
    hwproblem = create_problem(
        name="Say Hello",
        description="We need to say hello",
        author=user
    )
    hwtoolbox = create_toolbox(
        name="Python",
        description="A basic Python environment.",
        license=License.get_or_create(
            name="Apache License, version 2.0",
            url="http://www.apache.org/licenses/LICENSE-2.0"
        ),
        author=user
    )
    hwsolution = create_solution(
        name="Print with Python",
        description="Print something using Python",
        author=user,
        template="http://localhost:5000/scm/static/test/helloworld.py",
        problem=hwproblem
    )
    Var.create(solution=hwsolution,
               type="string",
               name="test1",
               label="Test Variable",
               default="World")
    SolutionToolbox.create(solution=hwsolution, dependency=hwtoolbox)
