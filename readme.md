# Dependencies

* Python 3

All python dependencies are described in setup.py, in the install_requires entry. See the [Development](#development) section below for details on managing dependency changes.

# Quickstart

To run a development server you need to install the python dependencies
(preferably into a virtual environment) using pip. The following commands assume
they are executed in the working directory.

```
pip install -e .
```

You can run the development server using the flask command line client. First set up the environment to tell flask which application to run, and that we want to use the debug mode that enables code reloading.

```
export FLASK_APP=main FLASK_DEBUG=1
```

Next you need to initialise the database.

```
flask initdb
```

Then you can run the following command each time you needd to start the threaded development server.

```
flask run --with-threads
```

# Using Docker

Instead of managing a python installation and virtual environment you can use Docker and docker-compose to run the server in a container. See the Docker documentation for details on [installing the Docker Engine](https://docs.docker.com/engine/installation/) and the documentation about [installing docker-compose](https://docs.docker.com/compose/install/).

Then, in the working directory you can build the image for the server, and run the development server in a container using docker-compose.

```
docker-compose build
docker-compose up
```

The development build will mount the working directory in the running container, so any changes you make to your local files will be reflected in the running version without having to re-build the image.

Once the image has been built, you can override the default command that is run when starting the container, e.g. for bootstrapping the database on the first run, using the following command.

```
docker-compose run --entrypoint flask --rm web initdb
```

You can run the service in a production mode locally using the following.

```
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up
```

The production version uses uwsgi as the python app server and nginx as a proxy, with no hot reloading or local files mounted, so running in that mode will not pick up local changes until you rebuild the image.

It's also possible to run (dev or prod) the container in the background by appending -d to the 'up' command, allowing you to continue to use the terminal. You can connect to a running docker system to view the logs as follows. Using the -f flag simply tells docker-compose to keep the logs open and "follow" them as they change. Leaving it off will simply dump the logs to the console and return.

```
docker-compose logs -f
```

# Development

After updating dependencies, or upgrading dependencies to new versions, you need to regenerate the requirements.txt file with the current set of frozen dependencies. This ensures that other builds and deployments can be made using the precise versions of packages that you tested.

Use the command below in the project directory to generate the new requirements.txt. Make sure to update the frozen dependencies when pushing changes to the repository, if required.

```
scripts/freeze
```

