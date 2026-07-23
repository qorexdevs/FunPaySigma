from unittest import TestCase
from unittest.mock import patch

import requests

from Utils import updater


class FakeResponse:
    def __init__(self, status_code=200, *, headers=None, url="", text="", content=b"", payload=None):
        self.status_code = status_code
        self.headers = headers or {}
        self.url = url
        self.text = text
        self.content = content
        self._payload = payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


ATOM_RELEASE = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <link rel="alternate" href="https://github.com/qorexdevs/FunPaySigma/releases/tag/v9.1.0"/>
    <content type="html">&lt;ul&gt;&lt;li&gt;Updater fallback&lt;/li&gt;&lt;/ul&gt;</content>
  </entry>
</feed>
"""


class UpdaterFallbackTests(TestCase):
    def test_atom_is_used_when_api_is_rate_limited(self):
        def fake_get(url, **kwargs):
            if url == updater.LATEST_RELEASE_URL:
                return FakeResponse(403, headers={"X-RateLimit-Remaining": "0"})
            if url == updater.RELEASES_ATOM_URL:
                return FakeResponse(content=ATOM_RELEASE)
            raise AssertionError(url)

        with patch.object(updater.requests, "get", side_effect=fake_get), \
                patch.object(updater, "_load_cache", return_value=None), \
                patch.object(updater, "_save_cache"):
            release = updater.get_latest_release(max_retries=1, force_refresh=True)

        self.assertEqual(release.tag_name, "v9.1.0")
        self.assertIn("Updater fallback", release.description)
        self.assertEqual(release.sources_link, updater._archive_url("v9.1.0"))

    def test_release_redirect_is_used_when_api_and_atom_fail(self):
        def fake_get(url, **kwargs):
            if url == updater.LATEST_RELEASE_PAGE_URL:
                return FakeResponse(
                    302,
                    headers={"Location": "https://github.com/qorexdevs/FunPaySigma/releases/tag/v9.2.0"},
                    url=url,
                )
            raise requests.ConnectionError("simulated outage")

        with patch.object(updater.requests, "get", side_effect=fake_get), \
                patch.object(updater, "_load_cache", return_value=None), \
                patch.object(updater, "_save_cache"):
            release = updater.get_latest_release(max_retries=1, force_refresh=True)

        self.assertEqual(release.tag_name, "v9.2.0")

    def test_stale_cache_is_used_during_total_outage(self):
        stale = {"tag_name": "v9.3.0", "body": "cached release"}

        def fake_cache(allow_stale=False):
            return stale if allow_stale else None

        with patch.object(updater.requests, "get", side_effect=requests.ConnectionError("offline")), \
                patch.object(updater, "_load_cache", side_effect=fake_cache), \
                patch.object(updater, "_save_cache"):
            release = updater.get_latest_release(max_retries=1, force_refresh=True)

        self.assertEqual(release.tag_name, "v9.3.0")
        self.assertEqual(release.description, "cached release")

    def test_archive_download_has_github_and_codeload_fallbacks(self):
        urls = updater._archive_download_urls(
            "https://api.github.com/repos/qorexdevs/FunPaySigma/zipball/v9.4.0"
        )

        self.assertIn(updater._archive_url("v9.4.0"), urls)
        self.assertIn(
            "https://codeload.github.com/qorexdevs/FunPaySigma/zip/refs/tags/v9.4.0",
            urls,
        )
