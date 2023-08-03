"""
base client model to create and use http endpoints
"""
import logging
import time
import urllib.parse

import requests

from pybugsnag.globals import (API_URL, LIBRARY, TEST_API_URL, TEST_TOKEN,
                               __version__)
from pybugsnag.models import Organization, Project
from pybugsnag.models.error import RateLimited


def test_client():
    """returns a test client"""
    return BugsnagDataClient(TEST_TOKEN, api_url=TEST_API_URL, debug=True)


class BugsnagDataClient:
    """client http wrapper"""

    def __init__(self, token, api_url=API_URL, cache=True, debug=False, rate_limit_retry=False):
        """creates a new client"""
        if not token:
            raise Exception("no token specified!")
        self.token = token
        self.api_url = api_url
        self.version = __version__
        self.cache = cache
        self.debug = debug
        self.rate_limit_retry = rate_limit_retry
        self.rate_limit_sleep_buffer = 10
        self.rate_limit_retry_max = 5

        # cache
        self._organizations = None

    @property
    def headers(self):
        """forms the headers required for the API calls"""
        return {
            "Accept": "application/json; version=2",
            "AcceptEncoding": "gzip, deflate",
            "Authorization": "token {}".format(self.token),
            "User-Agent": "{}/{}".format(LIBRARY, self.version),
        }

    def _log(self, *args):
        """logging method"""
        if not self.debug:
            return
        print(*args)

    def _req(self, path, method="get", rate_limit_retry=0, **kwargs):
        """requests wrapper"""
        full_path = urllib.parse.urljoin(self.api_url, path)
        self._log("[{}]: {}".format(method.upper(), full_path))
        request = requests.request(method, full_path, headers=self.headers, **kwargs)
        if request.status_code == 429:
            if self.rate_limit_retry and rate_limit_retry <= self.rate_limit_retry_max:
                sleep_sec = int(request.headers.get("Retry-After", "-1"))
                if sleep_sec != -1:
                    sleep_sec = sleep_sec + self.rate_limit_sleep_buffer
                    logging.info(
                        f"auto retry rate limit. retry count is {rate_limit_retry}. sleep ({sleep_sec} seconds)")
                    time.sleep(sleep_sec)
                    return self._req(path, method, rate_limit_retry + 1, **kwargs)
                else:
                    raise RateLimited(-1)
            else:
                raise RateLimited(int(request.headers.get("Retry-After", "-1")))

        self._log(f"retry-after:{request.headers.get('Retry-After', '')}")
        self._log(f"RateLimit-Remaining:{request.headers.get('X-RateLimit-Remaining', '')}")
        return request

    def get(self, path, raw=False, **kwargs):
        """makes a get request to the API"""
        request = self._req(path, **kwargs)
        return request if raw else request.json()

    def post(self, path, raw=False, **kwargs):
        """makes a post request to the API"""
        request = self._req(path, method="post", **kwargs)
        return request if raw else request.json()

    def put(self, path, raw=False, **kwargs):
        """makes a put request to the API"""
        request = self._req(path, method="put", **kwargs)
        return request if raw else request.json()

    @property
    def organizations(self):
        """organizations list for this access token"""
        if not self._organizations or not self.cache:
            self._organizations = [
                Organization(x, client=self) for x in self.get("user/organizations")
            ]
        return self._organizations

    def get_organization(self, organization_id):
        """get organization info by organization_id"""
        return Organization(
            self.get("organizations/{}".format(organization_id)), client=self
        )

    def get_project(self, project_id):
        """gets a project by it's id"""
        return Project(self.get("projects/{}".format(project_id)), client=self)
