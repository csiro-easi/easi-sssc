# Dockerize the SSSC website
FROM tiangolo/uwsgi-nginx:python3.6

MAINTAINER Geoff Squire <geoffrey.squire@csiro.au>

# Remove any sample app and work in the /app directory
RUN rm -rf /app
WORKDIR /app

# Add app configuration to Nginx
COPY nginx.conf /etc/nginx/conf.d/

# Expose the server ports
EXPOSE 80 443

# Use a volume for the database file and uploads
VOLUME /var/lib/scm

# Make sure we have an up to date pip
RUN pip install --upgrade pip wheel

# Install frozen requirements before copying app files to avoid busting the
# cache when the sources change.
COPY requirements.txt /app/
RUN pip install -r requirements.txt

# Finally copy the app files into place, and install the package
COPY setup.py /app/
COPY MANIFEST.in /app/
COPY uwsgi.ini /app/
COPY sssc /app/sssc/
RUN pip install .

# Flask App
ENV FLASK_APP=sssc

# Make the flask development entrypoint script available, but not the default
# option.
COPY scripts/flask_dev_entrypoint /usr/local/bin
RUN chmod +x /usr/local/bin/flask_dev_entrypoint

# Run the package install to create an 'sssc' package
#RUN python /app/setup.py develop

# Don't run the dev server by default! Let supervisord/nginx/uwsgi do the work.
# For debugging, run the image and pass the commandline "python main.py".
# ENTRYPOINT ["python"]
# CMD  ["main.py"]
