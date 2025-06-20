from crewai import Agent, Task, Crew
import os
import subprocess


def clone_repo_if_needed(repository_url, local_path):
    if not os.path.exists(local_path):
        print(f"📥 Cloning repository: {repository_url}")
        subprocess.run(["git", "clone", repository_url, local_path])
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


def docker_build_run_push(image_name, dockerfile_path):
    print("🐳 Building Docker image...")
    subprocess.run(["docker", "build", "-t", image_name, dockerfile_path], check=True)

    print("🚀 Running Docker container...")
    try:
        subprocess.run(["docker", "run", "-d", "-p", "5002:5002", image_name], check=True)
    except subprocess.CalledProcessError as e:
        print("⚠️ Docker run failed:", e.stderr.decode())
        print("⚠️ It’s likely that port 5002 is already in use.")

    print("📤 Pushing Docker image to DockerHub...")
    subprocess.run(["docker", "push", image_name], check=True)


def GitHubRepoScannerCrew():
    github_token = os.getenv("GITHUB_TOKEN")
    dockerhub_user = os.getenv("DOCKERHUB_USERNAME")
    dockerhub_pass = os.getenv("DOCKERHUB_PASSWORD")
    repository_url = "https://github.com/chan-764/pyhtondeployment"
    local_repo_path = "../pyhtondeployment"
    dockerfile_path = os.path.join(local_repo_path, "app")
    image_name = f"{dockerhub_user}/my-flask-app:latest"

    # 1. Clone repo
    clone_repo_if_needed(repository_url, local_repo_path)

    # 2. Check Dockerfile
    dockerfile_exists = os.path.exists(os.path.join(dockerfile_path, "Dockerfile"))
    scan_result = "Dockerfile found ✅" if dockerfile_exists else "No Dockerfile found ❌"

    # 3. Docker login
    docker_login(dockerhub_user, dockerhub_pass)

    # 4. Build, run, and push
    docker_build_run_push(image_name, dockerfile_path)

    # Agents
    scanner = Agent(
        role="GitHub Repository Scanner",
        goal="Check if the repo contains a Dockerfile",
        backstory="You are a GitHub expert specializing in DevOps practices.",
        verbose=True
    )

    builder = Agent(
        role="Docker Image Builder",
        goal="Build and run Docker containers for Python applications",
        backstory="You are an expert in Docker image creation and running Flask apps.",
        verbose=True
    )

    pusher = Agent(
        role="DockerHub Image Pusher",
        goal="Push Docker images to DockerHub",
        backstory="You handle DockerHub login, tagging, and secure pushing.",
        verbose=True
    )

    # Tasks
    scan_task = Task(
        description=f"Check if the Dockerfile exists at: {dockerfile_path}/Dockerfile",
        expected_output=scan_result,
        agent=scanner
    )

    build_task = Task(
        description=f"""Build the Docker image using:
  docker build -t {image_name} {dockerfile_path}

Then verify the image exists with:
  docker images
""",
        expected_output="Docker image built and verified with `docker images` ✅",
        agent=builder
    )

    run_task = Task(
        description=f"""Run the container using:
  docker run -d -p 5002:5002 {image_name}

Then check if container is running using:
  docker ps
""",
        expected_output="Docker container is running and verified with `docker ps` ✅",
        agent=builder
    )

    test_task = Task(
        description="Confirm the Flask app is responding using:\n  curl http://localhost:5002",
        expected_output="App is live and responded to curl ✅",
        agent=builder
    )

    push_task = Task(
        description=f"""Log into DockerHub as {dockerhub_user}, then:
  docker push {image_name}
""",
        expected_output="Docker image pushed to DockerHub ✅",
        agent=pusher
    )

    return Crew(
        agents=[scanner, builder, pusher],
        tasks=[scan_task, build_task, run_task, test_task, push_task],
        verbose=True
    )


if __name__ == "__main__":
    crew = GitHubRepoScannerCrew()
    crew.kickoff()
