#!/usr/bin/env python3
"""
Script to search GitHub for repositories that use Kinect devices.
"""

from queryGitHub import create_github_client

def search_kinect_repositories():
    """Search for GitHub repositories that use Kinect devices"""
    client = create_github_client()
    
    print("Searching GitHub for Kinect-related repositories...\n")
    
    # Different search queries to find Kinect-related repositories
    search_queries = [
        "kinect in:name,description,readme",
        "microsoft kinect",
        "kinect SDK",
        "kinect sensor",
        "kinect v2",
        "kinect azure",
        "kinect depth camera"
    ]
    
    try:
        all_repos = []
        seen_repos = set()  # To avoid duplicates
        
        for query in search_queries:
            print(f"🔍 Searching with query: '{query}'")
            search_results = client.search_repositories(query, sort="stars", order="desc", per_page=15)
            
            if 'items' in search_results:
                new_repos = 0
                for repo in search_results['items']:
                    repo_key = f"{repo['owner']['login']}/{repo['name']}"
                    if repo_key not in seen_repos:
                        seen_repos.add(repo_key)
                        all_repos.append(repo)
                        new_repos += 1
                
                print(f"   Found {len(search_results['items'])} results, {new_repos} new unique repos")
            else:
                print(f"   No results found")
            
            # Limit to avoid too many API calls
            if len(all_repos) >= 30:
                break
        
        print(f"\n📊 Total unique Kinect-related repositories found: {len(all_repos)}")
        print("=" * 80)
        
        # Sort by stars for better results
        all_repos.sort(key=lambda x: x.get('stargazers_count', 0), reverse=True)
        
        for i, repo in enumerate(all_repos[:20]):  # Show top 20
            print(f"\n{i+1:2d}. {repo['name']} ({repo['owner']['login']})")
            print(f"    ⭐ Stars: {repo.get('stargazers_count', 0):,}")
            print(f"    🍴 Forks: {repo.get('forks_count', 0):,}")
            print(f"    💬 Language: {repo.get('language', 'Unknown')}")
            print(f"    📅 Updated: {repo.get('updated_at', 'Unknown')[:10]}")
            print(f"    🔗 URL: {repo.get('html_url', 'Unknown')}")
            
            description = repo.get('description', '')
            if description:
                # Truncate long descriptions
                if len(description) > 100:
                    description = description[:97] + "..."
                print(f"    📝 Description: {description}")
            
            # Try to get README snippet for more context
            try:
                readme = client.get_repository_readme(repo['owner']['login'], repo['name'])
                if readme and 'kinect' in readme.lower():
                    # Find the first mention of Kinect in README
                    readme_lower = readme.lower()
                    kinect_pos = readme_lower.find('kinect')
                    if kinect_pos >= 0:
                        start_pos = max(0, kinect_pos - 80)
                        end_pos = min(len(readme), kinect_pos + 120)
                        snippet = readme[start_pos:end_pos].strip()
                        # Clean up the snippet
                        snippet = snippet.replace('\n', ' ').replace('\r', ' ')
                        snippet = ' '.join(snippet.split())  # Remove extra whitespace
                        if len(snippet) > 150:
                            snippet = snippet[:147] + "..."
                        print(f"    📖 README: ...{snippet}...")
            except Exception as e:
                # Don't fail the whole search if README fetch fails
                pass
            
        print("\n" + "=" * 80)
        print("🎯 Search completed! These repositories use or mention Kinect devices.")
        
        # Categorize by programming language
        languages = {}
        for repo in all_repos[:20]:
            lang = repo.get('language', 'Unknown')
            if lang not in languages:
                languages[lang] = 0
            languages[lang] += 1
        
        print("\n📊 Programming Languages Distribution:")
        for lang, count in sorted(languages.items(), key=lambda x: x[1], reverse=True):
            print(f"    {lang}: {count} repositories")
            
    except Exception as e:
        print(f"❌ Error searching Kinect repositories: {e}")

if __name__ == "__main__":
    search_kinect_repositories()
