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

# Finally copy the app files into place
COPY sssc /app/sssc/
COPY setup.py /app/

# Install requirements
RUN pip install --upgrade pip && \
    pip install -e .

# Flask App
ENV FLASK_APP=sssc

# Run the package install to create an 'sssc' package
#RUN python /app/setup.py develop

# Don't run the dev server by default! Let supervisord/nginx/uwsgi do the work.
# For debugging, run the image and pass the commandline "python main.py".
# ENTRYPOINT ["python"]
# CMD  ["main.py"]
