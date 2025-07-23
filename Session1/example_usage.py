"""
Example usage of the GitHub API Query Module

This script demonstrates how to use the GitHubAPIClient to query GitHub repositories.
"""

from query_github import GitHubAPIClient, create_github_client
import json

def example_query_organization():
    """Example: Query repositories for an organization"""
    client = create_github_client()
    
    # Replace 'microsoft' with any organization name you want to query
    org_name = "dngoins"
    print(f"Fetching repositories for organization: {org_name}")
    
    try:
        repos = client.get_organization_repositories(org_name)
        print(f"Found {len(repos)} repositories\n")
        
        # Display first 3 repositories with key information
        for i, repo in enumerate(repos[:3]):
            print(f"{i+1}. {repo['name']}")
            print(f"   Description: {repo.get('description', 'No description')}")
            print(f"   Language: {repo.get('language', 'Unknown')}")
            print(f"   Stars: {repo.get('stargazers_count', 0)}")
            print(f"   Forks: {repo.get('forks_count', 0)}")
            print(f"   Updated: {repo.get('updated_at', 'Unknown')}")
            print()
            
    except Exception as e:
        print(f"Error fetching repositories: {e}")

def example_query_readme():
    """Example: Get README for a specific repository"""
    client = create_github_client()
    
    owner = "microsoft"
    repo_name = "vscode"
    
    print(f"Fetching README for {owner}/{repo_name}")
    
    try:
        readme = client.get_repository_readme(owner, repo_name)
        if readme:
            print(f"README length: {len(readme)} characters")
            print("First 300 characters:")
            print(readme[:300] + "...\n")
        else:
            print("README not found\n")
            
    except Exception as e:
        print(f"Error fetching README: {e}")

def example_query_issues():
    """Example: Get issues for a repository"""
    client = create_github_client()
    
    owner = "microsoft"
    repo_name = "vscode"
    
    print(f"Fetching open issues for {owner}/{repo_name}")
    
    try:
        issues = client.get_repository_issues(owner, repo_name, state="open")
        print(f"Found {len(issues)} open issues\n")
        
        # Display first 3 issues
        for i, issue in enumerate(issues[:3]):
            print(f"{i+1}. #{issue['number']}: {issue['title']}")
            print(f"   Author: {issue['user']['login']}")
            print(f"   Created: {issue['created_at']}")
            print(f"   Labels: {', '.join([label['name'] for label in issue.get('labels', [])])}")
            print()
            
    except Exception as e:
        print(f"Error fetching issues: {e}")

def example_query_pull_requests():
    """Example: Get pull requests for a repository"""
    client = create_github_client()
    
    owner = "microsoft"
    repo_name = "vscode"
    
    print(f"Fetching open pull requests for {owner}/{repo_name}")
    
    try:
        prs = client.get_repository_pull_requests(owner, repo_name, state="open")
        print(f"Found {len(prs)} open pull requests\n")
        
        # Display first 3 PRs
        for i, pr in enumerate(prs[:3]):
            print(f"{i+1}. #{pr['number']}: {pr['title']}")
            print(f"   Author: {pr['user']['login']}")
            print(f"   Created: {pr['created_at']}")
            print(f"   Base: {pr['base']['ref']} ← Head: {pr['head']['ref']}")
            print()
            
    except Exception as e:
        print(f"Error fetching pull requests: {e}")

def example_query_contributors():
    """Example: Get contributors for a repository"""
    client = create_github_client()
    
    owner = "microsoft"
    repo_name = "vscode"
    
    print(f"Fetching contributors for {owner}/{repo_name}")
    
    try:
        contributors = client.get_repository_contributors(owner, repo_name)
        print(f"Found {len(contributors)} contributors\n")
        
        # Display top 5 contributors
        for i, contributor in enumerate(contributors[:5]):
            print(f"{i+1}. {contributor['login']}")
            print(f"   Contributions: {contributor['contributions']}")
            print(f"   Profile: {contributor['html_url']}")
            print()
            
    except Exception as e:
        print(f"Error fetching contributors: {e}")

if __name__ == "__main__":
    print("GitHub API Query Examples")
    print("=" * 40)
    
    # Run all examples
    example_query_organization()
    example_query_readme()
    example_query_issues()
    example_query_pull_requests()
    example_query_contributors()
    
    print("Examples completed!")
