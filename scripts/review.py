#!/usr/bin/env python3
"""
Code Review Script using Gemini LLM

This script fetches current git changes and requests a code review from the Gemini LLM model,
focusing only on violations of the guidelines in docs/code-guidelines.md.
"""

import os
import sys
import subprocess
import google.generativeai as genai
from pathlib import Path
from github import Github

# Check if GOOGLE_API_KEY is set
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    print("Error: GOOGLE_API_KEY environment variable is not set.")
    print("Please set it with: export GOOGLE_API_KEY='your-api-key'")
    sys.exit(1)

# Check if GITHUB_TOKEN is set
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    print("Warning: GITHUB_TOKEN environment variable is not set.")
    print("PR comments will not be posted without a GitHub token.")
    print("Please set it with: export GITHUB_TOKEN='your-github-token'")

# Configure the Gemini API
genai.configure(api_key=GOOGLE_API_KEY)

def get_git_diff():
    """Get the current git diff for Java files only."""
    try:
        # Filter to only include Java files
        return subprocess.check_output(['git', 'diff', 'origin/main...HEAD', '--', '*.java']).decode('utf-8')
    except subprocess.CalledProcessError as e:
        print(f"Error executing git command: {e}")
        sys.exit(1)

def get_code_guidelines():
    """Read the code guidelines from docs/code-guidelines.md."""
    try:
        guidelines_path = Path("docs/code-guidelines.md")
        if not guidelines_path.exists():
            print("Error: Code guidelines file not found at docs/code-guidelines.md")
            sys.exit(1)

        with open(guidelines_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"Error reading code guidelines: {e}")
        sys.exit(1)

def review_code(diff, guidelines):
    """Use Gemini to review the code changes against the guidelines."""
    try:
        # Initialize the Gemini model
        model = genai.GenerativeModel('gemini-2.0-flash')

        # Prepare the prompt
        prompt = f"""
        You are a code reviewer for a Spring Boot project. Review the following git diff and identify ONLY violations of the code guidelines.

        CODE GUIDELINES:
        {guidelines}

        GIT DIFF:
        {diff}

        INSTRUCTIONS:
        1. Answer in Korean.
        2. Only report violations of the code guidelines provided above.
        3. If there are no violations, simply respond with "No violations of the code guidelines were found."
        4. For each violation, specify:
           - The file and line number
           - Which guideline is violated
           - A brief explanation of the violation
           - A suggested fix
        5. Be concise and focus only on actual violations, not style preferences or other issues not covered by the guidelines.
        """

        # Generate the review
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Error generating review with Gemini: {e}")
        sys.exit(1)

def get_pr_info():
    """Get PR information from GitHub Actions environment variables."""
    # In GitHub Actions, these environment variables are available
    github_repository = os.environ.get("GITHUB_REPOSITORY")
    pr_number_str = None

    # Get PR number from GITHUB_REF (for pull request events)
    github_ref = os.environ.get("GITHUB_REF")
    if github_ref and github_ref.startswith("refs/pull/") and github_ref.endswith("/merge"):
        pr_number_str = github_ref.split("/")[2]

    # Alternatively, get from github.event.pull_request.number via GITHUB_EVENT_PATH
    if not pr_number_str:
        event_path = os.environ.get("GITHUB_EVENT_PATH")
        if event_path:
            import json
            try:
                with open(event_path, 'r') as f:
                    event = json.load(f)
                    if 'pull_request' in event and 'number' in event['pull_request']:
                        pr_number_str = str(event['pull_request']['number'])
            except Exception as e:
                print(f"Error reading event file: {e}")

    if not github_repository or not pr_number_str:
        print("Could not determine PR information from environment variables.")
        return None, None

    try:
        pr_number = int(pr_number_str)
        return github_repository, pr_number
    except ValueError:
        print(f"Invalid PR number: {pr_number_str}")
        return None, None

def post_pr_comment(review):
    """Post the review as a comment on the PR."""
    if not GITHUB_TOKEN:
        print("Skipping PR comment: GITHUB_TOKEN not set.")
        return False

    repo_name, pr_number = get_pr_info()
    if not repo_name or not pr_number:
        print("Skipping PR comment: Could not determine PR information.")
        return False

    try:
        # Initialize GitHub client
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(repo_name)
        pr = repo.get_pull(pr_number)

        # Post comment
        pr.create_issue_comment(review)
        print(f"Successfully posted review comment to PR #{pr_number}")
        return True
    except Exception as e:
        print(f"Error posting comment to PR: {e}")
        return False

def main():
    """Main function to run the code review."""
    print("Fetching git changes...")
    diff = get_git_diff()

    print("Reading code guidelines...")
    guidelines = get_code_guidelines()

    print("Requesting code review from Gemini...")
    review = review_code(diff, guidelines)

    print("\n=== CODE REVIEW RESULTS ===\n")
    print(review)

    # Post review as PR comment
    print("\nPosting review as PR comment...")
    post_pr_comment(review)

if __name__ == "__main__":
    main()
