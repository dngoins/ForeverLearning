# Context:
Python Script for querying GitHub API

# Input:
This script queries the GitHub API to retrieve information about a specific organizations and their repositories. It will create multiple functions to handle the API requests and process the responses.

# Main Objective:
The main goal is to take in text queries/requests and return text responses about information dealing with the organization and repositories.  The code will evenuatlly be used hosted in an Azure Function App, for querying information about a specific repo using the Repo's ReadMe.md found in the root of the repo.

# Directions:
1. Create a python script that can first take in the name of an organization and return the list of repositories for that organization.
2. Create a function that can take in the name of a repository and return the ReadMe.md file for that repository.
3. Create a function that can take in the name of a repository and return the list of issues for that repository.
4. Create a function that can take in the name of a repository and return the list of pull requests for that repository.
5. Create a function that can take in the name of a repository and return the list of contributors for that repository.

# Output:
Python script that can be used in an Azure Function App.

