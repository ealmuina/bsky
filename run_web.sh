#!/bin/bash

# migrate db, so we have the latest db schema
python manage.py migrate
echo "Migrated DB to latest version"

# start development server on public ip interface, on port 8000
python manage.py runserver 0.0.0.0:8000
