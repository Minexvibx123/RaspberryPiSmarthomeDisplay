import requests


class PiHoleClient:
    def __init__(self, base_url, sid=""):
        self.base_url = base_url.rstrip("/") + "/api"
        self.headers = {"sid": sid} if sid else {}

    def stats(self):
        return self._get("stats/summary")

    def blocking(self):
        return self._get("dns/blocking")

    def set_blocking(self, enabled, timer=None):
        payload = {"blocking": enabled, "timer": timer}
        response = requests.post(f"{self.base_url}/dns/blocking", json=payload, headers=self.headers, timeout=6)
        response.raise_for_status()
        return response.json()

    def _get(self, path):
        response = requests.get(f"{self.base_url}/{path}", headers=self.headers, timeout=6)
        response.raise_for_status()
        return response.json()