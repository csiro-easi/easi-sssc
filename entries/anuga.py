from models import (Problem, Solution, Toolbox, Dependency, Var, Source,
                    ToolboxDependency, SolutionDependency, ToolboxToolbox, SolutionToolbox,
                    License)

def create(user):
    anuga_problem = Problem.create(
        name="Regional Inundation modelling (storm-surge or tsunamis)",
        description="Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.",
        author=user
    )
    index_entry(anuga_problem)

    anuga_toolbox = Toolbox.create(
        name="ANUGA",
        description="ANUGA is a tool which can simulate events and their effects as they ‘progress’ or travel through a scenario in a model. You can model the ‘wave’ or storm surge to measure the impact and risk for known locations.",
        author=user,
        homepage="https://anuga.anu.edu.au",
        license=License.create(url="https://anuga.anu.edu.au/svn/anuga/trunk/anuga_core/source/anuga/LICENSE.txt"),
        source=Source.create(
            type="svn",
            url="https://anuga.anu.edu.au/svn/anuga/trunk/anuga_core/"
        ),
        puppet="http://localhost:5000/static/puppet/anuga.pp"
    )

    index_entry(anuga_toolbox)

    anuga_solution = Solution.create(
        name="ANUGA Busselton example",
        description="This template contains a pre-canned event (a wave) entering on the WEST of the grid, heading east, designed for coastal simulations of the Busselton-Bunbury area.\n\nThe implemented solver (Parallel finite volume method for hydrodynamic inundation modelling) is [described here](http://journal.austms.org.au/ojs/index.php/ANZIAMJ/article/view/153/)\n\nAn overview of the solver is [available here](http://www.ga.gov.au/corporate_data/69370/Rec2009_036.pdf).\n\nInputs:\n\nThe template can be customised in a variety of ways \n\n\tXxxx\n\n\tYyyy\n\n\tZzzz\n\nAnd is paired with a DEM of the area in question.\n\n\n\nOutputs:\n\n\tScreenshots of xxx\n\n\tCustom ANUGA SSW (database) of the simulation",
        author=user,
        problem=anuga_problem,
        homepage="https://github.com/GeoscienceAustralia/tcrm",
        template="http://localhost:5000/static/templates/anuga.py"
        )

    Var.create(type="int",
               name="base_scale",
               label="Base Scale",
               default=400000,
               min=1,
               solution=anuga_solution)

    Var.create(type="double",
               name="tide",
               label="Tide",
               default=0.0,
               min=0.0,
               step=0.1,
               solution=anuga_solution)

    Var.create(type="string",
               name="name_stem",
               label="File Name",
               default="busselton",
               solution=anuga_solution)

    Var.create(type="file",
               name="input_dataset",
               label="Input dataset (NetCDF)",
               solution=anuga_solution)

    index_entry(anuga_solution)

    SolutionToolbox.create(solution=anuga_solution, dependency=anuga_toolbox)

    tcrm_problem = Problem.create(
        name="Understanding cyclone risk",
        description="Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.",
        author=user
    )
    index_entry(tcrm_problem)

    tcrm_toolbox = Toolbox.create(
        name="Tropical Cyclone Risk Model",
        description="The Tropical Cyclone Risk Model is a stochastic tropical cyclone model developed by [Geoscience Australia](http://www.ga.gov.au) for estimating the wind hazard from tropical cyclones.",
        author=user,
        homepage="https://github.com/GeoscienceAustralia/tcrm",
        license=License.create(url="https://github.com/GeoscienceAustralia/tcrm/blob/master/LICENSE"),
        source=Source.create(type="git",
                         url="https://github.com/GeoscienceAustralia/tcrm.git",
                         checkout="v1.0rc1",
                             exec="python installer/setup.py build_ext -i"),
        puppet="http://localhost:5000/static/test/tcrm.pp"
    )

    tcrm_reqs = Dependency.create(
        type="requirements",
        identifier="https://github.com/GeoscienceAustralia/tcrm/raw/master/requirements.txt"
    )

    ToolboxDependency.create(toolbox=tcrm_toolbox, dependency=tcrm_reqs)

    index_entry(tcrm_toolbox)

    tcrm_solution = Solution.create(
        name="TCRM example",
        description="""The template allows for numerous fake events (generated from real events) to occur on a target area, allowing us to compute statistics about the likelihood, size, and patterns arising from generating thousands of years worth of events.


Inputs:



Outputs:

	Track files for each cyclone

	Statistics about risk areas""",
        author=user,
        homepage="https://github.com/GeoscienceAustralia/tcrm",
        problem=tcrm_problem,
        template="http://localhost:5000/static/test/tcrm.py"
    )

    SolutionToolbox.create(solution=tcrm_solution, dependency=tcrm_toolbox)

    Var.create(
        name="east-bound-lon",
        label="East Bound Longitude",
        type="double",
        default=124.0,
        solution=tcrm_solution)
    Var.create(
        name="west-bound-lon",
        label="West Bound Longitude",
        type="double",
        default=113.0,
        solution=tcrm_solution)
    Var.create(
        name="north-bound-lat",
        label="North Bound Latitude",
        type="double",
        default=-15.0,
        solution=tcrm_solution)
    Var.create(
        name="south-bound-lat",
        label="South Bound Latitude",
        type="double",
        default=-26.0,
        solution=tcrm_solution)
    Var.create(
        name="locality-id",
        label="Locality ID",
        type="int",
        values=[250913860],
        solution=tcrm_solution)
    Var.create(
        name="locality-name",
        label="Locality Name",
        type="string",
        values=["Port Hedland"],
        solution=tcrm_solution)
    Var.create(
        name="num-simulations",
        label="Number of simulations",
        type="int",
        default=1000,
        solution=tcrm_solution)
    Var.create(
        name="years-per-simulation",
        label="Years per simulation",
        type="int",
        default=1,
        solution=tcrm_solution)
    Var.create(
        name="season-seed",
        label="Random seed for season",
        type="random-int",
        min=1,
        max=10000000,
        solution=tcrm_solution)
    Var.create(
        name="track-seed",
        label="Random seed for track",
        type="random-int",
        min=1,
        max=10000000,
        solution=tcrm_solution)
    Var.create(
        name="windfield-interface-resolution",
        label="Windfield Resolution",
        type="double",
        default=0.05,
        min=0.02,
        max=0.5,
        step=0.01,
        solution=tcrm_solution)
    Var.create(
        name="n-threads",
        label="Max threads",
        type="int",
        min=1,
        solution=tcrm_solution)

    index_entry(tcrm_solution)

