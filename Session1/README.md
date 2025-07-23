# GitHub API Query Module

A Python module for querying the GitHub API to retrieve information about organizations and repositories. This module is designed to be hosted in Azure Function Apps with proper error handling and security practices.

## Features

The module provides the following functionality:

1. **Get Organization Repositories** - Retrieve all repositories for a specific organization
2. **Get Repository README** - Fetch the README.md content for a specific repository
3. **Get Repository Issues** - List issues for a repository (open, closed, or all)
4. **Get Repository Pull Requests** - List pull requests for a repository (open, closed, or all)
5. **Get Repository Contributors** - List contributors for a repository

## Key Features

- **Azure-Ready**: Designed for deployment in Azure Function Apps
- **Error Handling**: Comprehensive error handling with custom exceptions
- **Rate Limiting**: Automatic handling of GitHub API rate limits
- **Retry Logic**: Exponential backoff retry mechanism for transient failures
- **Security**: Uses environment variables for authentication (never hardcoded credentials)
- **Logging**: Comprehensive logging for monitoring and debugging
- **Pagination**: Automatic handling of paginated API responses

## Installation

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Set up your GitHub token (optional but recommended):
```bash
# Windows
set GITHUB_TOKEN=your_github_token_here

# Linux/Mac
export GITHUB_TOKEN=your_github_token_here
```

Note: Without a GitHub token, you'll be limited to 60 requests per hour. With a token, you get 5,000 requests per hour.

## Usage

### Basic Usage

```python
from query_github import GitHubAPIClient, create_github_client

# Create a client
client = create_github_client()

# Get repositories for an organization
repos = client.get_organization_repositories("microsoft")
print(f"Found {len(repos)} repositories")

# Get README for a specific repository
readme = client.get_repository_readme("microsoft", "vscode")
if readme:
    print(f"README length: {len(readme)} characters")

# Get open issues for a repository
issues = client.get_repository_issues("microsoft", "vscode", state="open")
print(f"Found {len(issues)} open issues")

# Get open pull requests for a repository
prs = client.get_repository_pull_requests("microsoft", "vscode", state="open")
print(f"Found {len(prs)} open pull requests")

# Get contributors for a repository
contributors = client.get_repository_contributors("microsoft", "vscode")
print(f"Found {len(contributors)} contributors")
```

### Advanced Usage

```python
# Initialize with a specific token
client = GitHubAPIClient(token="your_github_token")

# Get all issues (open, closed, and pull requests are filtered out)
all_issues = client.get_repository_issues("owner", "repo", state="all")

# Get closed pull requests
closed_prs = client.get_repository_pull_requests("owner", "repo", state="closed")

# Limit results per page (useful for large repositories)
limited_repos = client.get_organization_repositories("microsoft", per_page=50)
```

## API Methods

### `get_organization_repositories(org_name, per_page=100)`
Returns a list of all repositories for the specified organization.

**Parameters:**
- `org_name` (str): Name of the GitHub organization
- `per_page` (int): Number of repositories per page (max 100)

**Returns:** List of repository dictionaries

### `get_repository_readme(owner, repo_name)`
Returns the README.md content for the specified repository.

**Parameters:**
- `owner` (str): Repository owner (organization or user)
- `repo_name` (str): Repository name

**Returns:** README content as string, or None if not found

### `get_repository_issues(owner, repo_name, state="open", per_page=100)`
Returns a list of issues for the specified repository.

**Parameters:**
- `owner` (str): Repository owner
- `repo_name` (str): Repository name
- `state` (str): Issue state ('open', 'closed', or 'all')
- `per_page` (int): Number of issues per page (max 100)

**Returns:** List of issue dictionaries

### `get_repository_pull_requests(owner, repo_name, state="open", per_page=100)`
Returns a list of pull requests for the specified repository.

**Parameters:**
- `owner` (str): Repository owner
- `repo_name` (str): Repository name
- `state` (str): PR state ('open', 'closed', or 'all')
- `per_page` (int): Number of PRs per page (max 100)

**Returns:** List of pull request dictionaries

### `get_repository_contributors(owner, repo_name, per_page=100)`
Returns a list of contributors for the specified repository.

**Parameters:**
- `owner` (str): Repository owner
- `repo_name` (str): Repository name
- `per_page` (int): Number of contributors per page (max 100)

**Returns:** List of contributor dictionaries

## Error Handling

The module includes comprehensive error handling:

- `GitHubAPIError`: Base exception for GitHub API errors
- `RateLimitError`: Raised when rate limit is exceeded
- Automatic retry with exponential backoff for transient failures
- Proper logging of all errors and warnings

## Rate Limiting

The module automatically handles GitHub API rate limiting:

- Monitors rate limit headers
- Warns when approaching rate limits
- Automatically retries with appropriate delays when rate limited
- Uses exponential backoff for retry logic

## Azure Function App Integration

This module is designed for Azure Function Apps and follows Azure best practices:

- Environment variable configuration
- Comprehensive logging
- Proper error handling
- Security considerations
- Performance optimizations

To use in an Azure Function App:

1. Upload the module files
2. Install dependencies via requirements.txt
3. Set the GITHUB_TOKEN environment variable in Azure Function App settings
4. Import and use the `create_github_client()` function

## Security Considerations

- Never hardcode GitHub tokens in your code
- Use environment variables or Azure Key Vault for token storage
- Implement proper access controls in your Azure Function App
- Monitor API usage to detect unusual patterns
- Regularly rotate GitHub tokens

## Examples

See `example_usage.py` for comprehensive examples of how to use each method.

Run the examples:
```bash
python example_usage.py
```

## Dependencies

- `requests`: HTTP library for API calls
- `typing`: Type hints (Python 3.5+)
- `functools`: For decorators
- `base64`: For decoding README content
- `logging`: For comprehensive logging
- `os`: For environment variable access
- `time`: For retry delays

## License

This code is provided as an example for educational purposes.
