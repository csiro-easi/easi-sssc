from setuptools import setup

setup(
    name='sssc',
    version='1.0.0',    # TODO: Proper version
    url='https://bitbucket.csiro.au/projects/SSSC/repos/sssc',
    license='CSIRO',   # TODO: License?
    classifiers=[   # https://pypi.python.org/pypi?%3Aaction=list_classifiers
        'Development Status :: 6 - Mature',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Scientific/Engineering',
    ],
    packages=['sssc'],
    keywords='science solution',
    include_package_data=True,
    install_requires=[
        'Flask',
        'Flask-Admin',
        'Flask-Cors',
        'Flask-Login',
        'Flask-Script',
        'Flask-Security',
        'Flask-WTF',
        'Jinja2',
        'Markdown',
        'MarkupSafe',
        'WTForms',
        'Werkzeug',
        'aniso8601',
        'itsdangerous',
        'mccabe',
        'peewee',
        'pytz',
        'six',
        'wtf-peewee',
        'rdflib',
        'rdflib-jsonld',
        'bcrypt',
        'requests',
        'rsa',
        'simplejson',
        'click'
    ],
    python_requires='>=3.6',
)
