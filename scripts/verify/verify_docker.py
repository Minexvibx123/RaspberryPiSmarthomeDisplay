import importlib.util
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent.parent
spec = importlib.util.spec_from_file_location("docker_api", repo_root / "plugins" / "docker" / "api.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
assert isinstance(module.DockerClient().containers(), list)
print("VERIFICATION PASSED")