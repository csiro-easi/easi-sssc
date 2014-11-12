from app import app
import admin
import views
import argparse


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Manage the SSC app")
    parser.add_argument('-b', '--bootstrap', action='store_true', help="Initialise a new database")
    args = parser.parse_args()

    if args.bootstrap:
        from bootstrap import bootstrap
        bootstrap()

    # Run the server
    app.run()
