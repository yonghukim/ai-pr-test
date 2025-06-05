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

# Check if GOOGLE_API_KEY is set
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    print("Error: GOOGLE_API_KEY environment variable is not set.")
    print("Please set it with: export GOOGLE_API_KEY='your-api-key'")
    sys.exit(1)

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

if __name__ == "__main__":
    main()
