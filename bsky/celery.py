import os

import django
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bsky.settings')
django.setup()

app = Celery(
    'tasks',
    broker='redis://bsky-redis:6379/0',
    backend='redis://bsky-redis:6379/0'
)
