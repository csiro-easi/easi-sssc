from models import SolutionVar, SolutionDependency, Source, License, \
    ToolboxDependency
from bootstrap import create_problem, create_toolbox, create_solution


def create(user):
    """Create the catalogue entries for escript with user."""
    # Main entries
    escript_problem = create_problem(
        name="Magnetic Inversion ",
        description="Perform a magnetic inversion",
        author=user
    )
    escript_toolbox = create_toolbox(
        name="escript",
        description="Escript is a programming tool for implementing mathematical models (based on non-linear, coupled, time-dependent partial differential equations) in Python using the finite element method (FEM).",
        author=user,
        license=License.get_or_create(
            name="Apache License, version 2.0",
            url="http://www.apache.org/licenses/LICENSE-2.0"
        )[0],
        source=Source.get_or_create(
            type="svn",
            url="https://svn.geocomp.uq.edu.au/svn/esys13"
        )[0],
        puppet="http://localhost:5000/static/puppet/escript.pp"
    )
    escript_solution = create_solution(
        name="escript magnetic",
        description="3D magnetic inversion example using netCDF data.",
        author=user,
        problem=escript_problem,
        template="http://localhost:5000/static/templates/escript.py"
    )
    # Solution variables
    SolutionVar.create(
        solution=escript_solution,
        type="file",
        name="inversion-file",
        label="Inversion file",
        description="Input dataset"
    )
    SolutionVar.create(
        solution=escript_solution,
        default=29800,
        description="Background magnetic flux density in nano Tesla. Values for Australia can be calculated at the <a href=\"http://www.ga.gov.au/oracle/geomag/agrfform.jsp\" target=\"_blank\">Geoscience Australia website</a>'",
        label="B_north (nT)",
        name="bb-north",
        optional=False,
        type="int"
    )
    SolutionVar.create(
        solution=escript_solution,
        default=2780,
        description="Background magnetic flux density in nano Tesla. Values for Australia can be calculated at the <a href=\"http://www.ga.gov.au/oracle/geomag/agrfform.jsp\" target=\"_blank\">Geoscience Australia website</a>'",
        label="B_east (nT)",
        name="bb-east",
        optional=False,
        type="int"
    )
    SolutionVar.create(
        solution=escript_solution,
        default=-44000,
        description="Background magnetic flux density in nano Tesla. Values for Australia can be calculated at the <a href=\"http://www.ga.gov.au/oracle/geomag/agrfform.jsp\" target=\"_blank\">Geoscience Australia website</a>'",
        label="B_vertical (nT)",
        name="bb-vertical",
        optional=False,
        type="int"
    )
    SolutionVar.create(
        solution=escript_solution,
        default=40000,
        description="Maximum depth of the inversion, in meters.",
        label="Max depth (m)",
        name="max-depth",
        optional=False,
        type="double"
    )
    SolutionVar.create(
        solution=escript_solution,
        default=6000,
        description="Buffer zone above data, in meters, 6-10km recommended.",
        label="Buffer above (m)",
        name="air-buffer",
        optional=False,
        type="double"
    )
    SolutionVar.create(
        solution=escript_solution,
        default=25,
        description="Number of mesh elements in vertical direction (~1 element per 2km recommended).",
        label="Number of vertical mesh elements",
        name="vertical-mesh-elements",
        optional=False,
        type="int"
    )
    SolutionVar.create(
        solution=escript_solution,
        default=0.2,
        description="Amount of horizontal padding in the x-direction. This affects end result, about 20% recommended.",
        label="Horizontal padding in x",
        max=1.0,
        min=0.0,
        name="x-padding",
        optional=False,
        step=0.1,
        type="double"
    )
    SolutionVar.create(
        solution=escript_solution,
        default=0.2,
        description="Amount of horizontal padding in the y-direction. This affects end result, about 20% recommended.",
        label="Horizontal padding in y",
        max=1.0,
        min=0.0,
        name="y-padding",
        optional=False,
        step=0.1,
        type="double"
    )
    SolutionVar.create(
        solution=escript_solution,
        default=1,
        description="Maximum threads (min. 1).",
        label="Max threads",
        min=1.0,
        name="n-threads",
        optional=False,
        type="int"
    )
    # Dependencies
    SolutionDependency.create(solution=escript_solution,
                              type="toolbox",
                              identifier="http://localhost:5000/toolbox/1")
    ToolboxDependency.create(toolbox=escript_toolbox,
                             type="puppet",
                             identifier="stahnma/epel")
    ToolboxDependency.create(toolbox=escript_toolbox,
                             type="puppet",
                             identifier="example42/puppi")
    ToolboxDependency.create(toolbox=escript_toolbox,
                             type="puppet",
                             identifier="jhoblitt/autofsck")
    ToolboxDependency.create(toolbox=escript_toolbox,
                             type="puppet",
                             identifier="puppetlabs/stdlib")
