# Dockerize the SSSC website
FROM tiangolo/uwsgi-nginx:python3.5

MAINTAINER Geoff Squire <geoffrey.squire@csiro.au>

# Remove any sample app and work in the /app directory
RUN rm -rf /app
WORKDIR /app

# Install requirements first to avoid busting the docker cache
COPY requirements.txt /app
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Add app configuration to Nginx
COPY nginx.conf /etc/nginx/conf.d/

# Expose the server ports
EXPOSE 80 443

# Finally copy the app files into place
COPY . /app/

# Don't run the dev server by default! Let supervisord/nginx/uwsgi do the work.
# For debugging, run the image and pass the commandline "python main.py".
# ENTRYPOINT ["python"]
# CMD  ["main.py"]
