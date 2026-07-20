"""Deploy the vespa/ application package to a running Vespa instance.

Run once after `docker compose up -d`:
    python -m app.deploy
"""
import os

from vespa.deployment import VespaDocker

from config import VESPA_CONFIG_PORT

HERE = os.path.dirname(__file__)
APP_DIR = os.path.abspath(os.path.join(HERE, "..", "vespa"))


def main():
    # Connect to the already-running container from docker-compose.yml.
    vespa_docker = VespaDocker(port=8080, container_memory="4G")
    print(f"Deploying application package from {APP_DIR} ...")
    app = vespa_docker.deploy_from_disk(application_name="docsearch", application_root=APP_DIR)
    app.wait_for_application_up(max_wait=300)
    print("Vespa is ready.")


if __name__ == "__main__":
    main()
