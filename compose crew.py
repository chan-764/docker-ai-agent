import os
import subprocess
import yaml
from crewai import Agent, Task, Crew


def clone_repo_if_needed(repository_url, local_path):
    if not os.path.exists(local_path):
        print(f"📥 Cloning repository: {repository_url}")
        subprocess.run(["git", "clone", repository_url, local_path], check=True)
    else:
        print("✅ Repository already cloned.")


def docker_login(username, password):
    print("🔐 Logging into DockerHub...")
    try:
        subprocess.run(
            ["docker", "login", "-u", username, "--password-stdin"],
            input=password.encode(),
            check=True,
            capture_output=True
        )
        print("✅ Docker login successful.")
    except subprocess.CalledProcessError as e:
        print("❌ Docker login failed:", e.stderr.decode())
        raise


def docker_build_run_push(image_name, dockerfile_path, port=None):
    print(f"🐳 Building Docker image: {image_name}")
    subprocess.run(["docker", "build", "-t", image_name, dockerfile_path], check=True)

    if port:
        print(f"🚀 Running Docker container for {image_name} on port {port}...")
        try:
            subprocess.run(["docker", "run", "-d", "-p", f"{port}:{port}", image_name], check=True)
        except subprocess.CalledProcessError as e:
            print(f"⚠️ Docker run failed for {image_name}:", e.stderr.decode())

    print(f"📤 Pushing Docker image to DockerHub: {image_name}")
    subprocess.run(["docker", "push", image_name], check=True)


def create_docker_compose_file(path):
    compose_content = {
        "version": "3.8",
        "services": {
            "quotes-api": {
                "image": "chandanuikey97/k8s-eks-image-api:latest",
                "ports": ["5001:5001"],
                "depends_on": ["quotes-db"],
                "environment": {
                    "MONGO_URI": "mongodb://quotes-db:27017/"
                }
            },
            "quotes-db": {
                "image": "chandanuikey97/k8s-eks-image-db:latest",
                "ports": ["27017:27017"]
            },
            "quotes-frontend": {
                "image": "chandanuikey97/k8s-eks-image-app:latest",
                "ports": ["5002:5002"],
                "depends_on": ["quotes-api"]
            }
        }
    }

    compose_file_path = os.path.join(path, "docker-compose.yml")
    with open(compose_file_path, "w") as f:
        yaml.dump(compose_content, f)
    print(f"📝 Docker Compose file created at: {compose_file_path}")
    return compose_file_path


def free_up_ports(ports):
    print("🔍 Checking for containers using ports:", ports)
    result = subprocess.run(
        ['docker', 'ps', '--format', '{{.ID}} {{.Ports}}'],
        capture_output=True, text=True, check=True
    )
    lines = result.stdout.strip().split('\n')
    for line in lines:
        if not line.strip():
            continue
        parts = line.split(' ', 1)
        if len(parts) < 2:
            continue
        container_id, container_ports = parts
        for port in ports:
            if f"0.0.0.0:{port}->" in container_ports or f"::{port}->" in container_ports:
                print(f"🛑 Stopping container {container_id} using port {port}")
                subprocess.run(['docker', 'stop', container_id], check=True)


def run_docker_compose(path):
    free_up_ports(["5001", "5002", "27017"])
    print("📦 Running docker-compose up...")
    subprocess.run(["docker-compose", "up", "-d"], cwd=path, check=True)


def GitHubRepoScannerCrew():
    github_token = os.getenv("GITHUB_TOKEN")
    dockerhub_user = os.getenv("DOCKERHUB_USERNAME")
    dockerhub_pass = os.getenv("DOCKERHUB_PASSWORD")
    repository_url = "https://github.com/chan-764/pyhtondeployment"
    local_repo_path = "../pyhtondeployment"

    # 1. Clone repo
    clone_repo_if_needed(repository_url, local_repo_path)

    # 2. Check Dockerfile (any one as example)
    dockerfile_exists = os.path.exists(os.path.join(local_repo_path, "app/Dockerfile"))
    scan_result = "Dockerfile found ✅" if dockerfile_exists else "No Dockerfile found ❌"

    # 3. Docker login
    docker_login(dockerhub_user, dockerhub_pass)

    # 4. Build, run, and push all 3 images
    docker_build_run_push(f"{dockerhub_user}/k8s-eks-image-api:latest", os.path.join(local_repo_path, "api"), port=5001)
    docker_build_run_push(f"{dockerhub_user}/k8s-eks-image-db:latest", os.path.join(local_repo_path, "db"))
    docker_build_run_push(f"{dockerhub_user}/k8s-eks-image-app:latest", os.path.join(local_repo_path, "app"), port=5002)

    # 5. Create docker-compose.yml
    compose_file_path = create_docker_compose_file(local_repo_path)

    # 6. Run Docker Compose
    run_docker_compose(local_repo_path)

    # Crew Agents and Tasks
    scanner = Agent(role="Scanner", goal="Check Dockerfile", backstory="Dockerfile validator", verbose=True)
    builder = Agent(role="Builder", goal="Build Images", backstory="Handles Docker builds", verbose=True)
    pusher = Agent(role="Pusher", goal="Push Images", backstory="Pushes to DockerHub", verbose=True)
    composer = Agent(role="Composer", goal="Orchestrate containers", backstory="Uses Docker Compose", verbose=True)

    scan_task = Task(description="Check Dockerfile exists", expected_output=scan_result, agent=scanner)
    build_task = Task(description="Build 3 Docker images", expected_output="All images built ✅", agent=builder)
    run_task = Task(description="Run containers locally", expected_output="Containers running ✅", agent=builder)
    push_task = Task(description="Push images to DockerHub", expected_output="Images pushed ✅", agent=pusher)
    compose_task = Task(description="Run docker-compose up", expected_output="Services up ✅", agent=composer)

    return Crew(
        agents=[scanner, builder, pusher, composer],
        tasks=[scan_task, build_task, run_task, push_task, compose_task],
        verbose=True
    )


if __name__ == "__main__":
    crew = GitHubRepoScannerCrew()
    crew.kickoff()
