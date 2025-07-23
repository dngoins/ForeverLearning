import json
import logging
import azure.functions as func

from queryGitHub import GitHubAPIClient, create_github_client

# =============================================================================
# CONSTANTS AND UTILITY CLASSES
# =============================================================================

# Constants for input property names in MCP tool definitions
# These define the expected property names for inputs to MCP tools
_GHQ_NAME_PROPERTY_NAME = "githubqueryname"  # Property name for the snippet identifier
_GHQ_PROPERTY_NAME = "githubquery"           # Property name for the snippet content
_PROJECT_ID_PROPERTY_NAME = "projectid"      # Property name for the project identifier
_CHAT_HISTORY_PROPERTY_NAME = "chathistory"  # Property name for previous chat context
_USER_QUERY_PROPERTY_NAME = "userquery"      # Property name for the user's specific question

# Utility class to define properties for MCP tools
# This creates a standardized way to document and validate expected inputs
class ToolProperty:
    """
    Defines a property for an MCP tool, including its name, data type, and description.
    
    These properties are used by AI assistants (like GitHub Copilot) to understand:
    - What inputs each tool expects
    - What data types those inputs should be
    - How to describe each input to users
    
    This helps the AI to correctly invoke the tool with appropriate parameters.
    """
    def __init__(self, property_name: str, property_type: str, description: str):
        self.propertyName = property_name    # Name of the property
        self.propertyType = property_type    # Data type (string, number, etc.)
        self.description = description       # Human-readable description
        
    def to_dict(self):
        """
        Converts the property definition to a dictionary format for JSON serialization.
        Required for MCP tool registration.
        """
        return {
            "propertyName": self.propertyName,
            "propertyType": self.propertyType,
            "description": self.description,
        }

# =============================================================================
# TOOL PROPERTY DEFINITIONS
# =============================================================================
# Each MCP tool needs a schema definition to describe its expected inputs
# This is how AI assistants know what parameters to provide when using these tools

# TODO: Lab Exercise 1 - Define the tool properties for query_github tool
# Create a list of ToolProperty objects that define the expected inputs (schema)
# Each property has a name, type, and description for the AI agent
tool_properties_github_query = [
    ToolProperty(_GHQ_NAME_PROPERTY_NAME, "string", "The unique name for the code snippet."),
    ToolProperty(_PROJECT_ID_PROPERTY_NAME, "string", "The ID of the project the snippet belongs to. Optional, defaults to 'default-project' if not provided."),
    ToolProperty(_GHQ_PROPERTY_NAME, "string", "The actual code content of the snippet."),
]

# Properties for the deep_wiki tool
# This tool generates comprehensive documentation from code snippets
tool_properties_wiki = [
    ToolProperty(_CHAT_HISTORY_PROPERTY_NAME, "string", "Optional. The preceding conversation history (e.g., user prompts and AI responses). Providing this helps contextualize the wiki content generation. Omit if no relevant history exists or if a general wiki is desired."),
    ToolProperty(_USER_QUERY_PROPERTY_NAME, "string", "Optional. The user's specific question, instruction, or topic to focus the wiki documentation on. If omitted, a general wiki covering available snippets might be generated."),
]

# Convert tool properties to JSON for MCP tool registration
# This is required format for the MCP tool trigger binding
tool_properties_github_query_json = json.dumps([prop.to_dict() for prop in tool_properties_github_query])
tool_properties_wiki_json = json.dumps([prop.to_dict() for prop in tool_properties_wiki])

app = func.FunctionApp()

@app.route(route="query-github", methods=["GET", "POST"], auth_level=func.AuthLevel.FUNCTION)
async def http_query_github(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    # the input looks like this:
#     {
#   "githubqueryname": "kinect-repositories-search",
#   "projectid": "kinect-device-projects",
#   "githubquery": "kinect in:name,description,readme"
# }

    # Get the json body for the input
    try:
        req_body = req.get_json()
    except ValueError:
        return func.HttpResponse(
            "Invalid JSON body. Please provide a valid JSON input.",
            status_code=400
        )

    # Read the githubqueryname and projectid from the request body
    # This is the name of the query to run
    githubqueryname = req_body.get('githubqueryname')
    projectid = req_body.get('projectid')
    githubquery = req_body.get('githubquery')

    if not githubqueryname or not projectid or not githubquery:
        return func.HttpResponse(
            "Missing required fields in the request body.",
            status_code=400
        )

    if githubquery:
        result = _query_repositories(githubquery)
        return func.HttpResponse(f"Repositories for '{githubqueryname}':\n{result}", status_code=200)

    else:
        return func.HttpResponse(
             "This HTTP triggered function executed successfully. Pass a name in the query string or in the request body for a personalized response.",
             status_code=200
        )

@app.route(route="search-kinect", methods=["GET", "POST"], auth_level=func.AuthLevel.FUNCTION)
async def search_kinect_repositories(req: func.HttpRequest) -> func.HttpResponse:
    """
    Search for GitHub repositories that use Kinect devices.
    """
    logging.info('Kinect repository search function processed a request.')
    
    try:
        result = _search_kinect_repositories()
        return func.HttpResponse(f"Kinect Repositories:\n{result}", status_code=200)
    except Exception as e:
        logging.error(f"Error searching Kinect repositories: {str(e)}")
        return func.HttpResponse(f"Error: {str(e)}", status_code=500)
    

@app.generic_trigger(
    arg_name="context", # Variable name for the incoming MCP data
    type="mcpToolTrigger", # Specify the trigger type
    toolName="query_github", # How the agent refers to this tool
    description="Get information about a GitHub repository.", # Description for the agent
    toolProperties=tool_properties_github_query_json, # The input schema (from Ex 1)
)
def mcp_query_github(context) -> str:
    """
    MCP tool to retrieve information about a GitHub repository.
    
    Key features:
    - Receives the repository name from an AI assistant
    - Uses the same retrieval logic as the HTTP endpoint
    - Returns the snippet as a JSON string
    
    The difference from the HTTP endpoint:
    - Receives the snippet name via the 'context' JSON string instead of URL path
    - Returns results as a JSON string instead of an HTTP response
    """
    try:
        # 1. Parse the context JSON string to extract the arguments
        mcp_data = json.loads(context)
        args = mcp_data.get("arguments", {})
        
        # 2. Extract the query from the arguments
        query = args.get(_GHQ_PROPERTY_NAME)  # Use githubquery field

        # 3. Validate the required parameter
        if not query:
            return json.dumps({"error": f"Missing essential argument: {_GHQ_PROPERTY_NAME}. Please provide the search query."})

        if query:
            result = _query_repositories(query)
        # 4. Retrieve the snippet from Cosmos DB
        # Uses the same storage function as the HTTP endpoint
        #snippet = await cosmos_ops.get_snippet_by_id(name)
       # if not snippet:
            # Return an error if the snippet doesn't exist
           # return json.dumps({"error": f"Snippet '{name}' not found"})
        
        # 5. Return the snippet as a JSON string
        return json.dumps(result)
    except json.JSONDecodeError:
        # Handle invalid context JSON
        return json.dumps({"error": "Invalid JSON received in context"})
    except Exception as e:
        # General error handling
        logging.error(f"Error in mcp_get_snippet: {str(e)}")
        return json.dumps({"error": str(e)})



def _query_repositories(query: str):
    """Search repositories based on query - can be org/user name or search query"""
    client = create_github_client()
    
    result = ""
    
    # Check if this looks like a search query (contains search operators)
    if any(operator in query.lower() for operator in ['in:', 'language:', 'topic:', 'user:', 'org:', 'repo:']):
        # This is a search query, use search API
        print(f"Performing search query: {query}")
        try:
            search_results = client.search_repositories(query, sort="stars", order="desc", per_page=15)
            
            if 'items' in search_results and search_results['items']:
                total_count = search_results.get('total_count', 0)
                result += f"Found {total_count:,} repositories matching '{query}':\n\n"
                
                for i, repo in enumerate(search_results['items'][:10]):  # Show top 10
                    result += f"{i+1}. {repo['name']} ({repo['owner']['login']})\n"
                    result += f"   Description: {repo.get('description', 'No description')}\n"
                    result += f"   Language: {repo.get('language', 'Unknown')}\n"
                    result += f"   Stars: {repo.get('stargazers_count', 0):,}\n"
                    result += f"   Forks: {repo.get('forks_count', 0):,}\n"
                    result += f"   URL: {repo.get('html_url', 'Unknown')}\n"
                    result += f"   Updated: {repo.get('updated_at', 'Unknown')[:10]}\n"
                    
                    # Try to get README snippet if it mentions the search term
                    try:
                        readme = client.get_repository_readme(repo['owner']['login'], repo['name'])
                        if readme:
                            search_term = query.split()[0].lower()  # Get first word as search term
                            if search_term in readme.lower():
                                readme_lower = readme.lower()
                                pos = readme_lower.find(search_term)
                                if pos >= 0:
                                    start_pos = max(0, pos - 50)
                                    end_pos = min(len(readme), pos + 150)
                                    snippet = readme[start_pos:end_pos].strip()
                                    # Clean up snippet
                                    snippet = ' '.join(snippet.split())
                                    if len(snippet) > 120:
                                        snippet = snippet[:117] + "..."
                                    result += f"   README: ...{snippet}...\n"
                    except Exception as e:
                        pass  # Don't fail if README fetch fails
                    
                    result += "\n"
            else:
                result += f"No repositories found matching '{query}'\n"
                
        except Exception as e:
            print(f"Error searching repositories: {e}")
            result += f"Error searching repositories: {e}\n"
    else:
        # This looks like an organization or user name, use the original logic
        org_name = query
        print(f"Fetching repositories for organization/user: {org_name}")    
        try:
            repos = client.get_repositories(query)
            print(f"Found {len(repos)} repositories\n")
            
            # Display first 3 repositories with key information
            for i, repo in enumerate(repos[:3]):
                # Now get the readme for each repository
                readme = client.get_repository_readme(repo['owner']['login'], repo['name'])
                if readme:
                    print(f"README for {repo['name']} found, length: {len(readme)} characters")
                    result += f"README for {repo['name']}:\n{readme[:1000]}...\n\n"
                else:
                    print(f"README for {repo['name']} not found")

                result += f"{i+1}. {repo['name']}\n"
                result += f"   Description: {repo.get('description', 'No description')}\n"
                result += f"   Language: {repo.get('language', 'Unknown')}\n"
                result += f"   Stars: {repo.get('stargazers_count', 0)}\n"
                result += f"   Forks: {repo.get('forks_count', 0)}\n"
                result += f"   Updated: {repo.get('updated_at', 'Unknown')}\n"
                result += "\n"
                
        except Exception as e:
            print(f"Error fetching repositories: {e}")
            result += f"Error fetching repositories: {e}\n"

    return result

def _search_kinect_repositories():
    """Search for GitHub repositories that use Kinect devices"""
    client = create_github_client()
    
    result = ""
    
    # Different search queries to find Kinect-related repositories
    search_queries = [
        "kinect in:name,description,readme",
        "kinect SDK",
        "microsoft kinect",
        "kinect sensor",
        "kinect v2",
        "kinect azure",
        "kinect depth camera",
        "kinect body tracking"
    ]
    
    try:
        all_repos = []
        seen_repos = set()  # To avoid duplicates
        
        for query in search_queries:
            print(f"Searching with query: '{query}'")
            search_results = client.search_repositories(query, sort="stars", order="desc", per_page=10)
            
            if 'items' in search_results:
                for repo in search_results['items']:
                    repo_key = f"{repo['owner']['login']}/{repo['name']}"
                    if repo_key not in seen_repos:
                        seen_repos.add(repo_key)
                        all_repos.append(repo)
            
            # Limit to avoid too many API calls
            if len(all_repos) >= 20:
                break
        
        result += f"Found {len(all_repos)} unique Kinect-related repositories:\n\n"
        
        # Sort by stars for better results
        all_repos.sort(key=lambda x: x.get('stargazers_count', 0), reverse=True)
        
        for i, repo in enumerate(all_repos[:15]):  # Show top 15
            result += f"{i+1}. {repo['name']} ({repo['owner']['login']})\n"
            result += f"   Description: {repo.get('description', 'No description')}\n"
            result += f"   Language: {repo.get('language', 'Unknown')}\n"
            result += f"   Stars: {repo.get('stargazers_count', 0)}\n"
            result += f"   Forks: {repo.get('forks_count', 0)}\n"
            result += f"   URL: {repo.get('html_url', 'Unknown')}\n"
            result += f"   Updated: {repo.get('updated_at', 'Unknown')}\n"
            
            # Try to get README snippet for more context
            try:
                readme = client.get_repository_readme(repo['owner']['login'], repo['name'])
                if readme and 'kinect' in readme.lower():
                    # Find the first mention of Kinect in README
                    readme_lower = readme.lower()
                    kinect_pos = readme_lower.find('kinect')
                    if kinect_pos >= 0:
                        start_pos = max(0, kinect_pos - 100)
                        end_pos = min(len(readme), kinect_pos + 200)
                        snippet = readme[start_pos:end_pos].strip()
                        result += f"   README snippet: ...{snippet}...\n"
            except Exception as e:
                print(f"Could not get README for {repo['name']}: {e}")
            
            result += "\n"
            
    except Exception as e:
        print(f"Error searching Kinect repositories: {e}")
        result += f"Error searching Kinect repositories: {e}\n"

    return result

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
