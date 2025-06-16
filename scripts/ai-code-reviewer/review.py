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
import json
import re

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
        # Get PR information
        repo_name, pr_number = get_pr_info()

        if repo_name and pr_number:
            g = Github(GITHUB_TOKEN)
            repo = g.get_repo(repo_name)
            pr = repo.get_pull(pr_number)

            target_branch = pr.base.ref
            current_branch = pr.head.ref

            return subprocess.check_output(['git', 'diff', f'origin/{target_branch}...origin/{current_branch}', '--', '*.java']).decode('utf-8')
        else:
            # Local environment
            checkout_commit = subprocess.check_output(['git', 'rev-parse', 'ORIG_HEAD']).decode('utf-8').strip()
            current_commit = subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode('utf-8').strip()
            return subprocess.check_output(['git', 'diff', f'{checkout_commit}...{current_commit}', '--', '*.java']).decode('utf-8')
    except subprocess.CalledProcessError as e:
        print(f"Error executing git command: {e}")
        print("Detailed exception information:")
        traceback.print_exc()
        sys.exit(1)

def summarize_multi_file_diff(diff_text):
    results, file_path, old_lines, new_lines = [], None, [], []
    old_num = new_num = None

    def flush():
        if file_path:
            results.append(f"filePath: {file_path}")
            if old_lines:
                results.append("old_hunk (before change):")
                results.extend(old_lines)
            if new_lines:
                results.append("\nnew_hunk (after change):")
                results.extend(new_lines)
            results.append("")  # blank line

    for line in diff_text.splitlines():
        if line.startswith('diff --git'):
            flush()
            old_lines, new_lines = [], []
            continue
        if line.startswith('+++ b/'):
            file_path = line[6:].strip()
        elif line.startswith('@@'):
            m = re.match(r'^@@ -(\d+).* \+(\d+).* @@', line)
            if m:
                old_num, new_num = int(m[1]), int(m[2])
        elif line.startswith('-') and not line.startswith('---'):
            old_lines.append(f'-{old_num:4} | {line[1:]}')
            old_num += 1
        elif line.startswith('+') and not line.startswith('+++'):
            new_lines.append(f'+{new_num:4} | {line[1:]}')
            new_num += 1
        elif line.startswith(' '):
            old_lines.append(f' {old_num:4} | {line[1:]}')
            new_lines.append(f' {new_num:4} | {line[1:]}')
            new_num += 1
            old_num += 1

    flush()  # flush last file
    return '\n'.join(results)

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
        prompt_path = Path("scripts/ai-code-reviewer/prompt.toml")
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

def wrap_suggestion_code(code):
    """Wrap the suggestion code in the GitHub suggestion format."""
    if not code:
        return ""
    return f"```suggestion\n{code}\n```"

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
                start_line = int(comment["startLine"]) if comment["startLine"] else None
                line = int(comment["line"])
                body = f"{comment['guideline']}\n{comment['explanation']}\n{wrap_suggestion_code(comment['suggestionCode'])}"
                if start_line:
                    pr.create_review_comment(
                        body=body,
                        commit=latest_commit,
                        path=comment["file"],
                        line=line,
                        start_line=start_line,
                        side='RIGHT'
                    )
                else:
                    pr.create_review_comment(
                        body=body,
                        commit=latest_commit,
                        path=comment["file"],
                        line=line,
                        side='RIGHT'
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
        raw_diff = get_git_diff()
        diff = summarize_multi_file_diff(raw_diff)

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
