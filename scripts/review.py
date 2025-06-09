#!/usr/bin/env python3
"""
Code Review Script using Gemini LLM

This script fetches current git changes and requests a code review from the Gemini LLM model,
focusing only on violations of the guidelines in docs/code-guidelines.md.
"""

import os
import sys
import subprocess
import toml
import traceback
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
        print("Detailed exception information:")
        traceback.print_exc()
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
        print("Detailed exception information:")
        traceback.print_exc()
        sys.exit(1)

def load_prompt_template():
    """Load the prompt template from the TOML file."""
    try:
        prompt_path = Path("scripts/prompt.toml")
        if not prompt_path.exists():
            print("Error: Prompt template file not found at scripts/prompt.toml")
            sys.exit(1)

        with open(prompt_path, "r", encoding="utf-8") as f:
            prompt_data = toml.load(f)
            return prompt_data["prompt"]["content"]
    except Exception as e:
        print(f"Error loading prompt template: {e}")
        print("Detailed exception information:")
        traceback.print_exc()
        sys.exit(1)

def review_code(prompt):
    """Use Gemini to review the code changes against the guidelines."""
    try:
        # Initialize the Gemini model
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Error generating review with Gemini: {e}")
        print("Detailed exception information:")
        traceback.print_exc()
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
                print("Detailed exception information:")
                traceback.print_exc()

    if not github_repository or not pr_number_str:
        print("Could not determine PR information from environment variables.")
        return None, None

    try:
        pr_number = int(pr_number_str)
        return github_repository, pr_number
    except ValueError:
        print(f"Invalid PR number: {pr_number_str}")
        print("Detailed exception information:")
        traceback.print_exc()
        return None, None

def parse_review_comments(review):
    """Parse the review JSON to extract violations and convert them to comments."""
    import json
    import re

    try:
        clean_str = re.sub(r"^```json\s*|\s*```$", "", review.strip(), flags=re.DOTALL)
        review_data = json.loads(clean_str)
        violations = review_data.get("violations", [])
        return violations
    except json.JSONDecodeError as e:
        print(f"Error parsing review JSON: {e}")
        return []
    except Exception as e:
        print(f"Error processing review data: {e}")
        print("Detailed exception information:")
        traceback.print_exc()
        return []

def post_review_comments(comments):
    """Post the review as line comments on the PR."""
    if not GITHUB_TOKEN:
        print("Skipping PR comments: GITHUB_TOKEN not set.")
        return False

    repo_name, pr_number = get_pr_info()
    if not repo_name or not pr_number:
        print("Skipping PR comments: Could not determine PR information.")
        return False

    try:
        # Initialize GitHub client
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(repo_name)
        pr = repo.get_pull(pr_number)

        if not comments:
            print("No specific violations found to comment on.")
            return True

        # Get the latest commit in the PR
        commits = list(pr.get_commits())
        if not commits:
            print("No commits found in the PR.")
            return False

        latest_commit = commits[-1]

        # Post each comment
        for comment in comments:
            try:
                body = f"{comment['guideline']}\n{comment['explanation']}\n{comment['suggestionCode']}"
                pr.create_review_comment(
                    body=body,
                    commit=latest_commit,
                    path=comment["file"],
                    line=comment["endLine"],
                    start_line=comment["startLine"],
                    side=comment["side"]
                )
            except Exception as e:
                print(comment)
                traceback.print_exc()

        return True
    except Exception as e:
        print(f"Error posting comments to PR: {e}")
        print("Detailed exception information:")
        traceback.print_exc()
        return False

def main():
    """Main function to run the code review."""
    try:
        print("Fetching git changes...")
        diff = get_git_diff()

        print("Reading code guidelines...")
        guidelines = get_code_guidelines()

        print("Loading prompt template...")
        prompt_template = load_prompt_template()
        prompt = prompt_template.format(guidelines=guidelines, diff=diff)

        print("Requesting code review from Gemini...")
        review = review_code(prompt)

        # Parse the review to get comments for specific files and lines
        print("\nParsing review comments...")
        comments = parse_review_comments(review)

        # Post review as line-specific PR comments
        print("\nPosting review as line-specific PR comments...")
        post_review_comments(comments)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        print("Detailed exception information:")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
