import enum
import logging
import os
import string
import sys
import time

import django
import requests
from dateutil import parser as date_parser
from django.utils import timezone
from tqdm import tqdm


class Entity(enum.IntEnum):
    ACTOR = 0
    FOLLOW = 1


class Crawler:
    def __init__(self, entities):
        self.entities = entities
        self.base_url = os.environ.get(
            "BSKY_XRPC_URL",
            default="https://bsky.social/xrpc"
        )

        self.jwt = None
        self._login()

    def _login(self):
        resp = requests.post(
            f"{self.base_url}/com.atproto.server.createSession",
            json={
                "identifier": "ealmuina.xyz",
                "password": "hgpz-h3ll-mb77-bkdw",
            }
        )
        self.jwt = resp.json().get("accessJwt")

    def _get_actors(self, query):
        params = {
            "term": query,
            "limit": 100,
        }

        while True:
            response = requests.get(
                f"{self.base_url}/app.bsky.actor.searchActors",
                params=params,
                headers={
                    "Authorization": f"Bearer {self.jwt}"
                }
            )
            result = response.json()

            if response.status_code != requests.codes.OK:
                if result.get("error") == "ExpiredToken":
                    self._login()
                    continue
                else:
                    logging.error(result)
                    sys.exit()

            for actor_data in result["actors"]:
                yield actor_data

            if next_cursor := result.get("cursor"):
                time.sleep(5)
                params["cursor"] = next_cursor
            else:
                break

    def _get_follows(self, actor):
        params = {
            "actor": actor.handle,
            "limit": 100,
        }

        while True:
            response = requests.get(
                f"{self.base_url}/app.bsky.graph.getFollows",
                params=params,
                headers={
                    "Authorization": f"Bearer {self.jwt}"
                }
            )
            result = response.json()

            if response.status_code != requests.codes.OK:
                if result.get("error") == "ExpiredToken":
                    self._login()
                    continue
                else:
                    logging.error(result)
                    sys.exit()

            for follow_data in result["follows"]:
                yield follow_data

            if next_cursor := result.get("cursor"):
                time.sleep(5)
                params["cursor"] = next_cursor
            else:
                break

    def _pull_actors(self):
        from stats.models import Actor

        Actor.objects.all().update(active=False)

        for q in tqdm(string.ascii_lowercase):
            for actor_data in tqdm(self._get_actors(q)):
                try:
                    self._process_actor(actor_data)
                except:
                    logging.exception(
                        f"Error processing @{actor_data.get('handle')}",
                        exc_info=True,
                        stack_info=True,
                    )

    def _pull_follows(self):
        from stats.models import Actor, Follow

        Follow.objects.all().update(active=False)

        for actor in tqdm(Actor.objects.all().iterator()):
            for follow_data in tqdm(self._get_follows(actor)):
                try:
                    self._process_follow(actor, follow_data)
                except:
                    logging.exception(
                        f"Error processing follow @{actor.handle} -> @{follow_data.get('handle')}",
                        exc_info=True,
                        stack_info=True,
                    )

    def _process_actor(self, actor_data):
        from stats.models import Actor

        defaults = {
            "handle": actor_data.get("handle"),
            "display_name": actor_data.get("displayName"),
            "description": actor_data.get("description"),
            "active": True,
        }
        if indexed_at := actor_data.get("indexedAt"):
            defaults["indexed_at"] = date_parser.parse(indexed_at)

        Actor.objects.update_or_create(
            did=actor_data.get("did"),
            defaults=defaults,
        )

    def _process_follow(self, from_actor, follow_data):
        from stats.models import Actor, Follow

        to_actor = Actor.objects.filter(
            handle=follow_data.get("handle")
        ).first()

        if to_actor:
            Follow.objects.update_or_create(
                from_actor=from_actor,
                to_actor=to_actor,
                defaults={
                    "active": True,
                    "last_seen": timezone.now(),
                }
            )

    def run(self):
        pull_fn = {
            Entity.ACTOR: self._pull_actors,
            Entity.FOLLOW: self._pull_follows,
        }

        for entity in self.entities:
            pull_fn[entity]()


if __name__ == '__main__':
    logging.basicConfig(level=logging.WARNING)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bsky.settings")
    django.setup()

    crawler = Crawler([Entity.ACTOR])
    while True:
        crawler.run()
