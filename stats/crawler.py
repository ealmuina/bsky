import enum
import logging
import os
import time

import django
import requests
from dateutil import parser as date_parser
from django.utils import timezone
from tenacity import retry, stop_after_attempt, wait_exponential


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

    def _describe_repo(self, did):
        response = self._make_request(
            f"{self.base_url}/com.atproto.repo.describeRepo",
            params={
                "repo": did
            }
        )
        return response.json()

    def _get_profile(self, handle):
        response = self._make_request(
            f"{self.base_url}/app.bsky.actor.getProfile",
            params={
                "actor": handle
            },
            headers={
                "Authorization": f"Bearer {self.jwt}"
            }
        )
        return response.json()

    def _list_repos(self):
        params = {
            "limit": 1000
        }

        while True:
            response = self._make_request(
                f"{self.base_url}/com.atproto.sync.listRepos",
                params=params
            )
            result = response.json()

            for repo in result["repos"]:
                yield repo["did"]

            if next_cursor := result.get("cursor"):
                time.sleep(5)
                params["cursor"] = next_cursor
            else:
                break

    def _login(self):
        response = self._make_request(
            f"{self.base_url}/com.atproto.server.createSession",
            method="POST",
            json={
                "identifier": os.environ.get("BSKY_IDENTITY"),
                "password": os.environ.get("BSKY_PASSWORD"),
            }
        )
        self.jwt = response.json().get("accessJwt")

    @retry(
        wait=wait_exponential(min=4),
        stop=stop_after_attempt(10),
    )
    def _make_request(self, url, method="GET", expected_code=200, **kwargs):
        response = requests.request(method, url, **kwargs)

        if response.status_code != expected_code:
            if "ExpiredToken" in response.text:
                self._login()
            else:
                logging.warning(response.text)
            raise AssertionError()

        return response

    def _process_actor(self, did):
        from stats.models import Actor

        try:
            # Update
            actor = Actor.objects.get(did=did)
            actor.active = True
            actor.save()

        except Actor.DoesNotExist:
            # Create
            repo_description = self._describe_repo(did)
            actor_data = self._get_profile(repo_description["handle"])

            created_at = timezone.now()
            if actor_data.get("indexedAt"):
                created_at = date_parser.parse(created_at)

            Actor.objects.create(
                did=did,
                handle=repo_description["handle"],
                display_name=actor_data.get("displayName"),
                description=actor_data.get("description"),
                created_at=created_at,
            )

    def _pull_actors(self):
        from stats.models import Actor

        logging.info(f"PULL of Actors started")

        Actor.objects.all().update(active=False)

        for did in self._list_repos():
            try:
                self._process_actor(did)
            except:
                logging.exception(
                    f"Error processing did: '{did}'",
                    exc_info=True,
                    stack_info=True,
                )

        logging.info("PULL of Actors finished")

    def run(self):
        pull_fn = {
            Entity.ACTOR: self._pull_actors,
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
