from __future__ import annotations
import json
import subprocess


class DockerClient:
    def containers(self):
        result = subprocess.run(["docker", "ps", "-a", "--format", "{{json .}}"], capture_output=True, text=True, timeout=5, check=True)
        return [json.loads(line) for line in result.stdout.splitlines() if line]

    def stats(self, container: str):
        result = subprocess.run(["docker", "stats", "--no-stream", "--format", "{{json .}}", container], capture_output=True, text=True, timeout=8, check=True)
        return json.loads(result.stdout)

    def start(self, container: str):
        return self._action("start", container)

    def stop(self, container: str):
        return self._action("stop", container)

    def restart(self, container: str):
        return self._action("restart", container)

    @staticmethod
    def _action(action: str, container: str) -> str:
        return subprocess.run(["docker", action, container], capture_output=True, text=True, timeout=30, check=True).stdout.strip()