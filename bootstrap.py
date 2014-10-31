from app import db
from models import User, Entry, Problem, Solution, Toolbox, Var, Source, Dependency, License, create_database


def bootstrap():
    db.connect()
    create_database(db)

    user = User.create(name="Fred", email="fred@example.org")

    tcrm_entry = Entry.create(name="Understanding cyclone risk",
                              description="Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.",
                              author=user)
    tcrm_prob = Problem.create(entry=tcrm_entry)

    tcrm_entry = Entry.create(name="Tropical Cyclone Risk Model",
                              description="The Tropical Cyclone Risk Model is a stochastic tropical cyclone model developed by [Geoscience Australia](http://www.ga.gov.au) for estimating the wind hazard from tropical cyclones.",
                              author=user)
    tcrm_toolbox = Toolbox.create(
        entry=tcrm_entry,
        homepage="https://github.com/GeoscienceAustralia/tcrm",
        license=License.create(url="https://github.com/GeoscienceAustralia/tcrm/blob/master/LICENSE"),
        source=Source.create(type="git",
                         url="https://github.com/GeoscienceAustralia/tcrm.git",
                         checkout="v1.0rc1",
                         exec="python installer/setup.py build_ext -i")
    )

    Dependency.create(type="system", name="tk-devel", entry=tcrm_entry)
    Dependency.create(type="system", name="tkinter", entry=tcrm_entry)
    Dependency.create(type="system", name="geos-devel", entry=tcrm_entry)
    Dependency.create(type="system", name="hdf5-devel", entry=tcrm_entry)
    Dependency.create(type="python", path="requirements.txt", entry=tcrm_entry)

    tcrm_solution = Solution.create(
        entry=Entry.create(
            name="TCRM example",
            description="""The template allows for numerous fake events (generated from real events) to occur on a target area, allowing us to compute statistics about the likelihood, size, and patterns arising from generating thousands of years worth of events.


Inputs:



Outputs:

	Track files for each cyclone

	Statistics about risk areas""",
            author=user
        ),
        homepage="https://github.com/GeoscienceAustralia/tcrm",
        problem=tcrm_prob,
        toolbox=tcrm_toolbox,
        template="import glob\nimport os\nimport subprocess\nimport tempfile\nimport zipfile\n\nTCRM_DIR=\"/opt/tcrm\"\n\niniString = \"\"\"\n[Actions]\n; TCRM modules to execute\nDataProcess=True\nExecuteStat=True\nExecuteTrackGenerator=True\nExecuteWindfield=True\nExecuteHazard=True\nPlotHazard=True\nPlotData=False\nExecuteEvaluate=False\nDownloadData=True\n\n[DataProcess]\nInputFile=Allstorms.ibtracs_wmo.v03r05.csv\nSource=IBTRACS\nStartSeason=1981\nFilterSeasons=True\n\n[Region]\n; Domain for windfield and hazard calculation\ngridLimit={'xMin':${west-bound-lon},'xMax':${east-bound-lon},'yMin':${south-bound-lat},'yMax':${north-bound-lat}}\ngridSpace={'x':1.0,'y':1.0}\ngridInc={'x':1.0,'y':0.5}\npLocalityID=${locality-id}\nLocalityName=${locality-name}\n\n[StatInterface]\nkdeType=Biweight\nkde2DType=Gaussian\nkdeStep=0.2\n\n[TrackGenerator]\n; NumSimulations=1000\nNumSimulations=${num-simulations}\n; YearsPerSimulation=1\nYearsPerSimulation=${years-per-simulation}\nSeasonSeed=${season-seed}\nTrackSeed=${track-seed}\n;SeasonSeed=403943\n;TrackSeed=89333\n\n[WindfieldInterface]\n;TrackPath=./output/vl/tracks\nMargin=2.0\nResolution=${windfield-interface-resolution}\n;Resolution=0.05\nSource=TCRM\nprofileType=powell\nwindFieldType=kepert\n\n[Hazard]\n; Years to calculate return period wind speeds\n;InputPath=./output/vl/windfield\n;Resolution=0.05\nYears=5,10,20,25,50,100,200,250,500,1000,2000,2500\nMinimumRecords=10\nCalculateCI=False\n\n\n[Input]\nlandmask = input/landmask.nc\nmslpfile = MSLP/slp.day.ltm.nc\ndatasets = IBTRACS,LTMSLP\nMSLPGrid=1,2,3,4,12\n\n[Output]\nPath=./output/vl\n\n[Logging]\nLogFile=./output/vl/log/tcrm.log\nLogLevel=INFO\nVerbose=False\n\n[Process]\nExcludePastProcessed=True\nDatFile=./output/vl/process/dat/tcrm.dat\n\n[RMW]\nGetRMWDistFromInputData=False\nmean=50.0\nsigma=0.6\n\n[TCRM]\n; Output track files settings\nColumns=index,age,lon,lat,speed,bearing,pressure,penv,rmax\nFieldDelimiter=,\nNumberOfHeadingLines=1\nSpeedUnits=kph\nPressureUnits=hPa\n\n[IBTRACS]\n; Input data file settings\nurl = ftp://eclipse.ncdc.noaa.gov/pub/ibtracs/v03r05/wmo/csv/Allstorms.ibtracs_wmo.v03r05.csv.gz\npath = input\nfilename = Allstorms.ibtracs_wmo.v03r05.csv\ncolumns = tcserialno,season,num,skip,skip,skip,date,skip,lat,lon,skip,pressure\nfielddelimiter = ,\nnumberofheadinglines = 3\npressureunits = hPa\nlengthunits = km\ndateformat = %Y-%m-%d %H:%M:%S\nspeedunits = kph\n\n[LTMSLP]\n; MSLP climatology file settings\nURL = ftp://ftp.cdc.noaa.gov/Datasets/ncep.reanalysis.derived/surface/slp.day.1981-2010.ltm.nc\npath = MSLP\nfilename = slp.day.ltm.nc\n\"\"\"\n\ndef cloudUpload(inFilePath, cloudKey):\n    \"\"\"Upload inFilePath to cloud bucket with key cloudKey.\"\"\"\n    cloudBucket = os.environ[\"STORAGE_BUCKET\"]\n    cloudDir = os.environ[\"STORAGE_BASE_KEY_PATH\"]\n    queryPath = (cloudBucket + \"/\" + cloudDir + \"/\" + cloudKey).replace(\"//\", \"/\")\n    retcode = subprocess.call([\"cloud\", \"upload\", cloudKey, inFilePath, \"--set-acl=public-read\"])\n    print (\"cloudUpload: \" + inFilePath + \" to \" + queryPath + \" returned \" + str(retcode))\n\ndef cloudDownload(cloudKey, outFilePath):\n    \"\"\"Downloads the specified key from bucket and writes it to outfile.\"\"\"\n    cloudBucket = os.environ[\"STORAGE_BUCKET\"]\n    cloudDir = os.environ[\"STORAGE_BASE_KEY_PATH\"]\n    queryPath = (cloudBucket + \"/\" + cloudDir + \"/\" + cloudKey).replace(\"//\", \"/\")\n    retcode = subprocess.call([\"cloud\", \"download\",cloudBucket,cloudDir,cloudKey, outFilePath])\n    print \"cloudDownload: \" + queryPath + \" to \" + outFilePath + \" returned \" + str(retcode)\n\n# Write the config file\nini_file = tempfile.NamedTemporaryFile(mode='w',\n                                       suffix=\".ini\",\n                                       prefix=\"vhirl-tcrm\",\n                                       delete=False)\nwith ini_file as f:\n    f.write(iniString)\n\n# Execute TCRM job\nprint \"Executing TCRM in {0}\".format(TCRM_DIR)\nos.chdir(TCRM_DIR)\nsubprocess.call([\"mpirun\", \"-np\", \"${n-threads}\", \"/usr/bin/python\", \"tcrm.py\", \"-c\", ini_file.name])\n\n\n# Upload results\ndef upload_results(spec, keyfn=None):\n    \"\"\"Upload files specified by spec.\n\n    Spec will be passed to glob.glob to find files.  If keyfn is\n    supplied it should be a function that takes a filename from glob\n    and returns the corresponding cloud key to use.\n\n    \"\"\"\n    files = glob.glob(spec)\n    for f in files:\n        k = None\n        if keyfn:\n            k = keyfn(f)\n        if k is None:\n            k = f\n        cloudUpload(f, k)\n\n\n# Zip then upload results\ndef zip_upload_results(spec, name, key=None):\n    \"\"\"Zip files globbed from spec into zipfile name and upload under key.\n\n    If key is None it will default to <name>.zip.\n\n    \"\"\"\n    z = zipfile.ZipFile(name, 'w')\n    for f in glob.glob(spec):\n        z.write(f)\n    z.close()\n    cloudUpload(name, name if key is None else key)\n\n\n# Logs\nupload_results(\"output/vl/log/*\")\n# Track files\nzip_upload_results(\"output/vl/tracks/*.csv\", \"tracks.zip\")\n# Windfield files\nzip_upload_results(\"output/vl/windfield/*.nc\", \"windfields.zip\")\n# Hazard data and plots\nupload_results(\"output/vl/plots/hazard/*.png\")\nupload_results(\"output/vl/hazard/*.nc\")"
    )

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
