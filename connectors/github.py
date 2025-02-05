import requests
from datetime import datetime
from typing import Dict, List, Optional
from time import sleep

class GitHubConnector:
    def __init__(self):
        self.base_url = "https://api.github.com"

    def get_github_account_type(self, account_name: str) -> Optional[str]:
        """
        Determine if the account is a user or organization.
        
        Args:
            account_name: GitHub account name
            
        Returns:
            'user' or 'org' or None if account doesn't exist
        """
        try:
            response = requests.get(f"{self.base_url}/users/{account_name}")
            if response.status_code == 200:
                return response.json().get("type", "").lower()
            return None
        except requests.RequestException:
            return None

    def get_github_repos_info(self, account_name: str) -> Optional[List[Dict]]:
        """
        Fetch information about all repositories for a given GitHub user or organization.
        
        Args:
            account_name: GitHub username or organization name
            
        Returns:
            List of dictionaries containing repo information or None if request fails
        """
        # Determine if account is user or organization
        account_type = self.get_github_account_type(account_name)
        if not account_type:
            print(f"Account {account_name} not found")
            return None
            
        if account_type == "organization":
            repos_url = f"{self.base_url}/orgs/{account_name}/repos"
        else:
            repos_url = f"{self.base_url}/users/{account_name}/repos"
        
        repos_info = []
        page = 1
        
        try:
            while True:
                response = requests.get(
                    repos_url,
                    params={
                        "page": page,
                        "per_page": 100,
                        "sort": "updated",
                        "direction": "desc",
                        "type": "all"
                    }
                )
                response.raise_for_status()
                
                repos = response.json()
                if not repos:
                    break
                    
                for repo in repos:
                    if repo.get("archived", False):
                        continue
                        
                    commits_url = f"{self.base_url}/repos/{account_name}/{repo['name']}/commits"
                    commits_response = requests.get(
                        commits_url,
                        params={
                            "per_page": 1,
                            "sha": repo.get("default_branch", "master")
                        }
                    )
                    
                    if commits_response.status_code == 200:
                        latest_commit = commits_response.json()[0]
                        
                        repos_info.append({
                            "name": repo["name"],
                            "full_name": repo["full_name"],
                            "stars": repo["stargazers_count"],
                            "last_commit_date": datetime.strptime(
                                latest_commit["commit"]["committer"]["date"],
                                "%Y-%m-%dT%H:%M:%SZ"
                            ),
                            "description": repo["description"],
                            "language": repo["language"],
                            "is_fork": repo["fork"],
                            "visibility": repo.get("visibility", "public"),
                            "default_branch": repo.get("default_branch", "master")
                        })
                    
                    sleep(0.1)
                
                page += 1
                
            repos_info.sort(key=lambda x: x["last_commit_date"], reverse=True)
            return repos_info
            
        except requests.RequestException as e:
            print(f"Error fetching repos info: {e}")
            return None

    @staticmethod
    def format_repo_info(repos_info: List[Dict]) -> str:
        """
        Format repository information into a readable string.
        """
        if not repos_info:
            return "No repositories found."
            
        result = []
        for repo in repos_info:
            result.append(
                f"Repository: {repo['full_name']}\n"
                f"Last commit: {repo['last_commit_date'].strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"Description: {repo['description'] or 'No description'}\n"
                f"{'=' * 50}"
            )
        
        return "\n".join(result)
