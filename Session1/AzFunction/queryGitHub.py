"""
GitHub API Query Module

This module provides functions to query the GitHub API for organization and repository information.
Designed to be hosted in Azure Function Apps with proper error handling and security practices.

Author: GitHub Copilot
Date: July 20, 2025
"""

import os
import logging
import requests
import time
from typing import Dict, List, Optional, Any
from functools import wraps
import base64
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

#loadenv()
# Load environment variables from .env file if present

class GitHubAPIError(Exception):
    """Custom exception for GitHub API errors"""
    pass

class RateLimitError(GitHubAPIError):
    """Exception raised when rate limit is exceeded"""
    pass

def retry_with_exponential_backoff(max_retries: int = 3, base_delay: float = 1.0):
    """
    Decorator to implement retry logic with exponential backoff for transient failures.
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds between retries
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except (requests.exceptions.RequestException, RateLimitError) as e:
                    if attempt == max_retries:
                        logger.error(f"Max retries exceeded for {func.__name__}: {str(e)}")
                        raise
                    
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {str(e)}. Retrying in {delay}s")
                    time.sleep(delay)
            
            return func(*args, **kwargs)
        return wrapper
    return decorator

class GitHubAPIClient:
    """
    GitHub API client with proper error handling, rate limiting, and security practices.
    
    This client is designed for Azure Function Apps and follows Azure development best practices:
    - Uses environment variables for configuration (never hardcoded credentials)
    - Implements proper error handling and retry logic
    - Includes comprehensive logging for monitoring
    - Handles rate limiting appropriately
    """
    
    def __init__(self, token: Optional[str] = None):
        """
        Initialize the GitHub API client.
        
        Args:
            token: GitHub personal access token. If not provided, will try to get from environment.
        """
        # Security: Get token from environment variable or Azure Key Vault in production
        self.token = token or os.getenv('GITHUB_TOKEN')
        
        if not self.token:
            logger.warning("No GitHub token provided. API requests will be rate-limited.")
        
        self.base_url = "https://api.github.com"
        self.session = requests.Session()
        
        # Set headers for authentication and API version
        self.session.headers.update({
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'Azure-Function-GitHub-Query-Client/1.0'
        })
        
        if self.token:
            self.session.headers['Authorization'] = f'token {self.token}'
    
    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """
        Handle API response with proper error checking and rate limit handling.
        
        Args:
            response: The HTTP response object
            
        Returns:
            Parsed JSON response data
            
        Raises:
            RateLimitError: When rate limit is exceeded
            GitHubAPIError: For other API errors
        """
        # Check rate limit headers
        if 'X-RateLimit-Remaining' in response.headers:
            remaining = int(response.headers['X-RateLimit-Remaining'])
            if remaining < 10:
                reset_time = int(response.headers.get('X-RateLimit-Reset', 0))
                current_time = int(time.time())
                wait_time = max(0, reset_time - current_time)
                logger.warning(f"Rate limit nearly exceeded. {remaining} requests remaining. Reset in {wait_time}s")
        
        if response.status_code == 403 and 'rate limit exceeded' in response.text.lower():
            reset_time = int(response.headers.get('X-RateLimit-Reset', 0))
            current_time = int(time.time())
            wait_time = max(0, reset_time - current_time)
            raise RateLimitError(f"Rate limit exceeded. Try again in {wait_time} seconds.")
        
        if response.status_code == 404:
            raise GitHubAPIError(f"Resource not found: {response.url}")
        
        if not response.ok:
            error_msg = f"GitHub API error {response.status_code}: {response.text}"
            logger.error(error_msg)
            raise GitHubAPIError(error_msg)
        
        try:
            return response.json()
        except ValueError as e:
            raise GitHubAPIError(f"Invalid JSON response: {str(e)}")
    
    @retry_with_exponential_backoff(max_retries=3)
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Make a request to the GitHub API with proper error handling.
        
        Args:
            endpoint: API endpoint (relative to base URL)
            params: Query parameters
            
        Returns:
            Parsed JSON response
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            logger.info(f"Making request to: {url}")
            response = self.session.get(url, params=params, timeout=30)
            return self._handle_response(response)
        except requests.exceptions.Timeout:
            raise GitHubAPIError("Request timeout")
        except requests.exceptions.ConnectionError:
            raise GitHubAPIError("Connection error")
    
    def get_repositories(self, owner_name: str, owner_type: str = "auto", per_page: int = 100) -> List[Dict[str, Any]]:
        """
        Get all repositories for a specific organization or user.
        
        Args:
            owner_name: Name of the GitHub organization or user
            owner_type: Type of owner ('org', 'user', or 'auto' to detect automatically)
            per_page: Number of repositories per page (max 100)
            
        Returns:
            List of repository information dictionaries
            
        Raises:
            GitHubAPIError: If the API request fails
        """
        if not owner_name or not owner_name.strip():
            raise ValueError("Owner name cannot be empty")
        
        owner_name = owner_name.strip()
        
        # Auto-detect owner type if not specified
        if owner_type == "auto":
            owner_type = self._detect_owner_type(owner_name)
        
        if owner_type not in ['org', 'user']:
            raise ValueError("Owner type must be 'org', 'user', or 'auto'")
        
        logger.info(f"Fetching repositories for {owner_type}: {owner_name}")
        
        repositories = []
        page = 1
        
        # Use appropriate endpoint based on owner type
        endpoint = f"orgs/{owner_name}/repos" if owner_type == "org" else f"users/{owner_name}/repos"
        
        while True:
            params = {
                'per_page': min(per_page, 100),  # GitHub API max is 100
                'page': page,
                'sort': 'updated',
                'direction': 'desc'
            }
            
            data = self._make_request(endpoint, params)
            
            if not data:  # Empty response means no more pages
                break
                
            repositories.extend(data)
            
            # If we got less than the requested per_page, we're on the last page
            if len(data) < params['per_page']:
                break
                
            page += 1
            
            # Safety check to prevent infinite loops
            if page > 100:  # Arbitrary limit
                logger.warning(f"Stopping pagination after 100 pages for {owner_type} {owner_name}")
                break
        
        logger.info(f"Found {len(repositories)} repositories for {owner_type} {owner_name}")
        return repositories
    
    def _detect_owner_type(self, owner_name: str) -> str:
        """
        Detect if the owner is an organization or user by making API calls.
        
        Args:
            owner_name: Name of the GitHub owner
            
        Returns:
            'org' if it's an organization, 'user' if it's a user
            
        Raises:
            GitHubAPIError: If neither org nor user exists
        """
        try:
            # Try organization endpoint first
            self._make_request(f"orgs/{owner_name}")
            return "org"
        except GitHubAPIError:
            try:
                # Try user endpoint
                self._make_request(f"users/{owner_name}")
                return "user"
            except GitHubAPIError:
                raise GitHubAPIError(f"Owner '{owner_name}' not found as organization or user")
    
    def get_organization_repositories(self, org_name: str, per_page: int = 100) -> List[Dict[str, Any]]:
        """
        Get all repositories for a specific organization.
        
        Args:
            org_name: Name of the GitHub organization
            per_page: Number of repositories per page (max 100)
            
        Returns:
            List of repository information dictionaries
            
        Raises:
            GitHubAPIError: If the API request fails
            
        Note:
            This method is deprecated. Use get_repositories() instead.
        """
        logger.warning("get_organization_repositories() is deprecated. Use get_repositories() instead.")
        return self.get_repositories(org_name, owner_type="org", per_page=per_page)
    
    def get_user_repositories(self, username: str, per_page: int = 100) -> List[Dict[str, Any]]:
        """
        Get all repositories for a specific user.
        
        Args:
            username: Name of the GitHub user
            per_page: Number of repositories per page (max 100)
            
        Returns:
            List of repository information dictionaries
            
        Raises:
            GitHubAPIError: If the API request fails
        """
        return self.get_repositories(username, owner_type="user", per_page=per_page)
    
    def get_repository_readme(self, owner: str, repo_name: str) -> Optional[str]:
        """
        Get the README.md content for a specific repository.
        
        Args:
            owner: Repository owner (organization or user)
            repo_name: Repository name
            
        Returns:
            README content as string, or None if not found
            
        Raises:
            GitHubAPIError: If the API request fails
        """
        if not owner or not repo_name:
            raise ValueError("Owner and repository name cannot be empty")
        
        owner = owner.strip()
        repo_name = repo_name.strip()
        
        logger.info(f"Fetching README for repository: {owner}/{repo_name}")
        
        try:
            data = self._make_request(f"repos/{owner}/{repo_name}/readme")
            
            # README content is base64 encoded
            if 'content' in data:
                content = base64.b64decode(data['content']).decode('utf-8')
                logger.info(f"Successfully retrieved README for {owner}/{repo_name}")
                return content
            else:
                logger.warning(f"No content found in README response for {owner}/{repo_name}")
                return None
                
        except GitHubAPIError as e:
            if "not found" in str(e).lower():
                logger.info(f"README not found for repository {owner}/{repo_name}")
                return None
            raise
    
    def get_repository_issues(self, owner: str, repo_name: str, state: str = "open", per_page: int = 100) -> List[Dict[str, Any]]:
        """
        Get issues for a specific repository.
        
        Args:
            owner: Repository owner (organization or user)
            repo_name: Repository name
            state: Issue state ('open', 'closed', or 'all')
            per_page: Number of issues per page (max 100)
            
        Returns:
            List of issue information dictionaries
            
        Raises:
            GitHubAPIError: If the API request fails
        """
        if not owner or not repo_name:
            raise ValueError("Owner and repository name cannot be empty")
        
        if state not in ['open', 'closed', 'all']:
            raise ValueError("State must be 'open', 'closed', or 'all'")
        
        owner = owner.strip()
        repo_name = repo_name.strip()
        
        logger.info(f"Fetching {state} issues for repository: {owner}/{repo_name}")
        
        issues = []
        page = 1
        
        while True:
            params = {
                'state': state,
                'per_page': min(per_page, 100),
                'page': page,
                'sort': 'updated',
                'direction': 'desc'
            }
            
            data = self._make_request(f"repos/{owner}/{repo_name}/issues", params)
            
            if not data:
                break
            
            # Filter out pull requests (GitHub API includes PRs in issues endpoint)
            filtered_issues = [issue for issue in data if 'pull_request' not in issue]
            issues.extend(filtered_issues)
            
            if len(data) < params['per_page']:
                break
                
            page += 1
            
            if page > 100:  # Safety check
                logger.warning(f"Stopping pagination after 100 pages for issues in {owner}/{repo_name}")
                break
        
        logger.info(f"Found {len(issues)} {state} issues for repository {owner}/{repo_name}")
        return issues
    
    def get_repository_pull_requests(self, owner: str, repo_name: str, state: str = "open", per_page: int = 100) -> List[Dict[str, Any]]:
        """
        Get pull requests for a specific repository.
        
        Args:
            owner: Repository owner (organization or user)
            repo_name: Repository name
            state: PR state ('open', 'closed', or 'all')
            per_page: Number of PRs per page (max 100)
            
        Returns:
            List of pull request information dictionaries
            
        Raises:
            GitHubAPIError: If the API request fails
        """
        if not owner or not repo_name:
            raise ValueError("Owner and repository name cannot be empty")
        
        if state not in ['open', 'closed', 'all']:
            raise ValueError("State must be 'open', 'closed', or 'all'")
        
        owner = owner.strip()
        repo_name = repo_name.strip()
        
        logger.info(f"Fetching {state} pull requests for repository: {owner}/{repo_name}")
        
        pull_requests = []
        page = 1
        
        while True:
            params = {
                'state': state,
                'per_page': min(per_page, 100),
                'page': page,
                'sort': 'updated',
                'direction': 'desc'
            }
            
            data = self._make_request(f"repos/{owner}/{repo_name}/pulls", params)
            
            if not data:
                break
            
            pull_requests.extend(data)
            
            if len(data) < params['per_page']:
                break
                
            page += 1
            
            if page > 100:  # Safety check
                logger.warning(f"Stopping pagination after 100 pages for PRs in {owner}/{repo_name}")
                break
        
        logger.info(f"Found {len(pull_requests)} {state} pull requests for repository {owner}/{repo_name}")
        return pull_requests
    
    def get_repository_contributors(self, owner: str, repo_name: str, per_page: int = 100) -> List[Dict[str, Any]]:
        """
        Get contributors for a specific repository.
        
        Args:
            owner: Repository owner (organization or user)
            repo_name: Repository name
            per_page: Number of contributors per page (max 100)
            
        Returns:
            List of contributor information dictionaries
            
        Raises:
            GitHubAPIError: If the API request fails
        """
        if not owner or not repo_name:
            raise ValueError("Owner and repository name cannot be empty")
        
        owner = owner.strip()
        repo_name = repo_name.strip()
        
        logger.info(f"Fetching contributors for repository: {owner}/{repo_name}")
        
        contributors = []
        page = 1
        
        while True:
            params = {
                'per_page': min(per_page, 100),
                'page': page
            }
            
            data = self._make_request(f"repos/{owner}/{repo_name}/contributors", params)
            
            if not data:
                break
            
            contributors.extend(data)
            
            if len(data) < params['per_page']:
                break
                
            page += 1
            
            if page > 100:  # Safety check
                logger.warning(f"Stopping pagination after 100 pages for contributors in {owner}/{repo_name}")
                break
        
        logger.info(f"Found {len(contributors)} contributors for repository {owner}/{repo_name}")
        return contributors

    def search_repositories(self, query: str, sort: str = "updated", order: str = "desc", per_page: int = 30) -> Dict[str, Any]:
        """
        Search for repositories using GitHub's search API.
        
        Args:
            query: Search query string (supports GitHub search syntax)
            sort: Sort field ('stars', 'forks', 'help-wanted-issues', 'updated')
            order: Sort order ('asc' or 'desc')
            per_page: Number of results per page (max 100)
            
        Returns:
            Dictionary containing search results with 'total_count' and 'items'
            
        Raises:
            GitHubAPIError: If the API request fails
            
        Examples:
            - search_repositories("kinect language:C#")
            - search_repositories("kinect topic:computer-vision")
            - search_repositories("kinect in:name,description,readme")
        """
        if not query or not query.strip():
            raise ValueError("Search query cannot be empty")
        
        if sort not in ['stars', 'forks', 'help-wanted-issues', 'updated']:
            raise ValueError("Sort must be one of: stars, forks, help-wanted-issues, updated")
        
        if order not in ['asc', 'desc']:
            raise ValueError("Order must be 'asc' or 'desc'")
        
        query = query.strip()
        logger.info(f"Searching repositories with query: '{query}'")
        
        params = {
            'q': query,
            'sort': sort,
            'order': order,
            'per_page': min(per_page, 100)
        }
        
        data = self._make_request("search/repositories", params)
        
        if 'total_count' in data and 'items' in data:
            logger.info(f"Search found {data['total_count']} repositories matching '{query}'")
            return data
        else:
            logger.warning(f"Unexpected search response format for query '{query}'")
            return {'total_count': 0, 'items': []}

    def search_repositories_paginated(self, query: str, sort: str = "updated", order: str = "desc", 
                                    max_results: int = 100) -> List[Dict[str, Any]]:
        """
        Search for repositories with pagination support.
        
        Args:
            query: Search query string
            sort: Sort field ('stars', 'forks', 'help-wanted-issues', 'updated')
            order: Sort order ('asc' or 'desc')
            max_results: Maximum number of results to return
            
        Returns:
            List of repository dictionaries
            
        Raises:
            GitHubAPIError: If the API request fails
        """
        repositories = []
        page = 1
        per_page = min(100, max_results)  # GitHub search API max is 100 per page
        
        while len(repositories) < max_results:
            remaining = max_results - len(repositories)
            current_per_page = min(per_page, remaining)
            
            params = {
                'q': query,
                'sort': sort,
                'order': order,
                'per_page': current_per_page,
                'page': page
            }
            
            try:
                data = self._make_request("search/repositories", params)
                
                if 'items' not in data or not data['items']:
                    break
                
                repositories.extend(data['items'])
                
                # If we got less than requested, we're on the last page
                if len(data['items']) < current_per_page:
                    break
                
                page += 1
                
                # GitHub search API only returns first 1000 results
                if page > 10:  # 10 pages * 100 per page = 1000 max
                    logger.warning("Reached GitHub search API limit of 1000 results")
                    break
                    
            except GitHubAPIError as e:
                if "rate limit" in str(e).lower():
                    logger.warning("Rate limit exceeded during search pagination")
                    break
                raise
        
        logger.info(f"Retrieved {len(repositories)} repositories from search")
        return repositories


# Convenience functions for Azure Function App integration
def create_github_client() -> GitHubAPIClient:
    """
    Create a GitHub API client with token from environment variables.
    
    Returns:
        Configured GitHubAPIClient instance
    """
    return GitHubAPIClient()


# Example usage and testing functions
def main():
    """
    Example usage of the GitHub API client.
    This function demonstrates how to use each method.
    """
    # Initialize client
    client = create_github_client()
    
    try:
        # Example 1: Get repositories using auto-detection (organization or user)
        print("=== Getting repositories for 'dngoins' (auto-detect) ===")
        repos = client.get_repositories("dngoins")  # Will auto-detect if it's org or user
        print(f"Found {len(repos)} repositories")
        for repo in repos[:5]:  # Show first 5
            print(f"- {repo['name']}: {repo.get('description', 'No description')}")
        
        # Example 1b: Explicitly get user repositories
        print("\n=== Getting repositories for user 'dngoins' ===")
        user_repos = client.get_user_repositories("dngoins")
        print(f"Found {len(user_repos)} user repositories")
        
        # # Example 1c: Get organization repositories (Microsoft as example)
        # print("\n=== Getting repositories for organization 'microsoft' ===")
        # org_repos = client.get_repositories("microsoft", owner_type="org", per_page=10)  # Limit to 10 for demo
        # print(f"Found {len(org_repos)} organization repositories")
        # for repo in org_repos[:3]:  # Show first 3
        #     print(f"- {repo['name']}: {repo.get('description', 'No description')}")
        
        # Example 2: Get README for a specific repository
        print("\n=== Getting README for dngoins repository ===")
        if repos:  # Use first repo from dngoins
            first_repo = repos[0]
            readme = client.get_repository_readme("dngoins", first_repo['name'])
            if readme:
                print(f"README length: {len(readme)} characters")
                print("First 200 characters:")
                print(readme[:200] + "...")
            else:
                print("No README found")
        
        # Example 3: Get issues for a repository
        print("\n=== Getting open issues for dngoins/CTI-Course ===")
        issues = client.get_repository_issues("dngoins", "CTI-Course", state="open")
        print(f"Found {len(issues)} open issues")
        for issue in issues[:3]:  # Show first 3
            print(f"- #{issue['number']}: {issue['title']}")
        
        # Example 4: Get pull requests for a repository
        print("\n=== Getting open pull requests for dngoins/CTI-Course ===")
        prs = client.get_repository_pull_requests("dngoins", "CTI-Course", state="open")
        print(f"Found {len(prs)} open pull requests")
        for pr in prs[:3]:  # Show first 3
            print(f"- #{pr['number']}: {pr['title']}")
        
        # Example 5: Get contributors for a repository
        print("\n=== Getting contributors for dngoins/CTI-Course ===")
        contributors = client.get_repository_contributors("dngoins", "CTI-Course")
        print(f"Found {len(contributors)} contributors")
        for contributor in contributors[:5]:  # Show first 5
            print(f"- {contributor['login']}: {contributor['contributions']} contributions")
    
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        print(f"Error: {str(e)}")


if __name__ == "__main__":
    main()



