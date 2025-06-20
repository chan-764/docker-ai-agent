import os
import requests
from dotenv import load_dotenv
from dg.crew import GitHubRepoScannerCrew

load_dotenv()

def fetch_all_paths(owner, repo, path, branch="terraform-test"):
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={branch}"
    headers = {
        "Authorization": f"Bearer {os.getenv('GITHUB_TOKEN')}",
        "Accept": "application/vnd.github.v3+json"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        contents = response.json()
        paths = []
        for item in contents:
            if item["type"] == "file":
                paths.append(item["path"])
            elif item["type"] == "dir":
                paths.extend(fetch_all_paths(owner, repo, item["path"], branch))
        return paths
    else:
        print(f"GitHub API error: {response.status_code} - {response.text}")
        return []

def run():
    repo_url = "https://github.com/chan-764/pyhtondeployment"
    owner = "chan-764"
    repo = "pyhtondeployment"
    branch = "terraform-test"

    repo_files = fetch_all_paths(owner, repo, "", branch)
    
    print("📂 Files in repo:")
    for f in repo_files:
        print(f" - {f}")

    # Kick off the CrewAI workflow
    crew = GitHubRepoScannerCrew()
    crew.kickoff()

if __name__ == "__main__":
    run()
