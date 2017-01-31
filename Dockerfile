# Dockerize the SSSC website
FROM tiangolo/uwsgi-nginx:python3.5

MAINTAINER Geoff Squire <geoffrey.squire@csiro.au>

# Add app configuration to Nginx
COPY nginx.conf /etc/nginx/conf.d/

# Expose the server ports
EXPOSE 80 443

# Remove any sample app and copy my app over
RUN rm -rf /app
COPY . /app/

WORKDIR /app

RUN pip install -r requirements.txt

# Don't run the dev server by default! Let supervisord/nginx/uwsgi do the work.
# For debugging, run the image and pass the commandline "python main.py".
# ENTRYPOINT ["python"]
# CMD  ["main.py"]
