import importlib.util
spec = importlib.util.spec_from_file_location("docker_api", "plugins/docker/api.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
assert isinstance(module.DockerClient().containers(), list)
print("VERIFICATION PASSED")