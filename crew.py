import os
import subprocess
import yaml
from crewai import Agent, Task, Crew
from datetime import datetime

# === Logger ===
def log(message, log_file):
    timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    line = f"{timestamp} {message}"
    print(line)
    with open(log_file, "a") as f:
        f.write(line + "\n")

# === Default Dockerfile Template ===
DOCKERFILE_TEMPLATE = """# Auto-generated Dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .  # Ensure this file exists
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "app.py"]
"""

# === Global Variables ===
dockerhub_user = os.getenv("DOCKERHUB_USERNAME")
dockerhub_pass = os.getenv("DOCKERHUB_PASSWORD")
repository_url = "https://github.com/chan-764/pyhtondeployment"
local_repo_path = "./cloned_repo"
log_file = "crew_output.log"
services = ["api", "db", "app"]

# === Agent Callback Functions ===

def scan_for_dockerfiles(_):
    if not os.path.exists(local_repo_path):
        log(f"📥 Cloning repository: {repository_url}", log_file)
        subprocess.run(["git", "clone", repository_url, local_repo_path], check=True)
    else:
        log("✅ Repository already cloned.", log_file)

    for service in services:
        dockerfile_path = os.path.join(local_repo_path, f"{service}/Dockerfile")
        if not os.path.exists(dockerfile_path):
            log(f"⚠️ Missing Dockerfile at: {dockerfile_path}", log_file)
            os.makedirs(os.path.dirname(dockerfile_path), exist_ok=True)
            with open(dockerfile_path, "w") as f:
                f.write(DOCKERFILE_TEMPLATE)
            log(f"✅ Auto-created Dockerfile for {service}", log_file)
        else:
            log(f"✅ Found Dockerfile: {dockerfile_path}", log_file)

def build_docker_images(_):
    log("🔐 Logging into DockerHub...", log_file)
    subprocess.run(
        ["docker", "login", "-u", dockerhub_user, "--password-stdin"],
        input=dockerhub_pass.encode(),
        check=True
    )

    for service in services:
        log(f"🔧 Building Docker image for {service}", log_file)
        subprocess.run(["docker", "build", "-t", f"{dockerhub_user}/k8s-{service}", service], cwd=local_repo_path, check=True)

def push_docker_images(_):
    for service in services:
        log(f"📤 Pushing image {dockerhub_user}/k8s-{service} to DockerHub", log_file)
        subprocess.run(["docker", "push", f"{dockerhub_user}/k8s-{service}"], check=True)

def launch_with_docker_compose(_):
    compose_content = {
        "version": "3.8",
        "services": {
            service: {
                "image": f"{dockerhub_user}/k8s-{service}",
                "ports": [f"500{index + 1}:500{index + 1}"]
            }
            for index, service in enumerate(services)
        }
    }

    compose_file_path = os.path.join(local_repo_path, "docker-compose.yml")
    with open(compose_file_path, "w") as f:
        yaml.dump(compose_content, f)
    log(f"📝 docker-compose.yml created at {compose_file_path}", log_file)

    log("🚀 Launching services with docker-compose...", log_file)
    subprocess.run(["docker-compose", "up", "-d"], cwd=local_repo_path, check=True)
    log("✅ docker-compose services launched", log_file)

# === Crew Setup ===

def GitHubRepoScannerCrew():
    open(log_file, "w").close()  # Clear log file

    # Define agents
    scanner = Agent(role="Scanner", goal="Check for Dockerfiles", backstory="Scans repo for Dockerfiles", verbose=True)
    builder = Agent(role="Builder", goal="Build Docker images", backstory="Builds all Docker containers", verbose=True)
    pusher = Agent(role="Pusher", goal="Push Docker images to DockerHub", backstory="Handles pushing to registry", verbose=True)
    composer = Agent(role="Composer", goal="Orchestrate services using Docker Compose", backstory="Launches containers", verbose=True)

    # Define tasks with callbacks
    scan_task = Task(description="Scan for Dockerfiles in the repo", expected_output="Dockerfiles verified", agent=scanner, callback=scan_for_dockerfiles)
    build_task = Task(description="Build Docker images for API, DB, and App", expected_output="Docker images built", agent=builder, callback=build_docker_images)
    push_task = Task(description="Push images to DockerHub", expected_output="Docker images pushed", agent=pusher, callback=push_docker_images)
    compose_task = Task(description="Run docker-compose to launch all services", expected_output="Services running", agent=composer, callback=launch_with_docker_compose)

    return Crew(
        agents=[scanner, builder, pusher, composer],
        tasks=[scan_task, build_task, push_task, compose_task],
        verbose=True
    )

# === Entry Point ===
if __name__ == "__main__":
    crew = GitHubRepoScannerCrew()
    crew.kickoff()
