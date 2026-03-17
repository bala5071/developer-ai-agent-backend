"""GitHub Tasks - Split into repository creation and code deployment"""
from crewai import Task
from typing import Optional, List


def create_github_repository_task(
    agent,
    repo_name: str,
    description: str,
    github_username: str,
    local_path: str,  # Add this parameter
    visibility: str = "public",
    license_type: str = "MIT",
    context_tasks: Optional[List] = None
):
    """Task to create GitHub repository and clone it locally."""
    
    return Task(
        description=f"""Create a new GitHub repository and clone it to local directory for development.

REPOSITORY NAME: {repo_name}
GITHUB USERNAME: {github_username}
LOCAL PATH: {local_path}
DESCRIPTION: {description}
VISIBILITY: {visibility}
LICENSE: {license_type}

═══════════════════════════════════════════════════════════════════════════════
YOUR RESPONSIBILITIES:
═══════════════════════════════════════════════════════════════════════════════

STEP 1: CREATE GITHUB REPOSITORY
───────────────────────────────────────────────────────────────────────────────
□ Use Create GitHub repository tool
□ Repository settings:
  - Name: {repo_name}
  - Description: {description}
  - Visibility: {visibility}
  - Initialize: YES (with README) - THIS IS IMPORTANT FOR CLONING
  - Add .gitignore: NO (developer will create appropriate one)
  - License: {license_type}
  - Has issues: YES
  - Has wiki: NO
  - Has projects: NO

IMPORTANT: Initialize the repository with a README so it has an initial commit.
This makes cloning and pushing easier.

STEP 2: CLONE REPOSITORY LOCALLY
───────────────────────────────────────────────────────────────────────────────
□ Use Clone GitHub repository tool
□ Clone URL: https://github.com/{github_username}/{repo_name}.git
□ Local path: {local_path}
□ Branch: main
□ Verify clone was successful
□ Confirm local directory exists with README.md

═══════════════════════════════════════════════════════════════════════════════
TOOLS TO USE (IN ORDER):
═══════════════════════════════════════════════════════════════════════════════

1. Create GitHub repository - Create empty repo on GitHub
2. Clone GitHub repository - Clone repo to {local_path}
3. Get repository status - Verify everything is ready

═══════════════════════════════════════════════════════════════════════════════
SUCCESS CRITERIA:
═══════════════════════════════════════════════════════════════════════════════

Setup is successful when:
✅ Repository exists on GitHub: https://github.com/{github_username}/{repo_name}
✅ Repository cloned to: {local_path}
✅ Local .git directory exists
✅ README.md exists locally
✅ Git remote 'origin' configured
✅ Working tree is clean
✅ Ready for development team to write code

═══════════════════════════════════════════════════════════════════════════════
IMPORTANT NOTES:
═══════════════════════════════════════════════════════════════════════════════

⚠ The repository MUST be initialized with a README
⚠ Clone must succeed before proceeding
⚠ All subsequent work will happen in: {local_path}
⚠ Developer, Tester will work in the cloned directory
⚠ Final deployment will push from this local directory back to GitHub

This creates a proper git workflow:
1. Create remote repository (GitHub)
2. Clone to local (this task)
3. Develop locally (Developer agent)
4. Test locally (Tester agent)
5. Commit and push (Deployment agent)
""",
        
        agent=agent,
        context=context_tasks,
        expected_output="""Repository creation and clone report:

1. ✅ GitHub Repository Created
   - Name: {repo_name}
   - URL: https://github.com/{github_username}/{repo_name}
   - Clone URL: https://github.com/{github_username}/{repo_name}.git
   - Visibility: {visibility}
   - Status: Initialized with README

2. ✅ Repository Cloned Locally
   - Local path: {local_path}
   - Branch: main
   - Remote: origin → https://github.com/{github_username}/{repo_name}.git
   - Files: README.md, .git/

3. ✅ Git Status
   - Working tree: Clean
   - Branch: main
   - Tracking: origin/main
   - Ready for development

**Status**: ✅ REPOSITORY READY FOR DEVELOPMENT

**Next Steps**:
- Developer agent will write code in: {local_path}
- Tester agent will test code in: {local_path}
- Deployment agent will commit and push from: {local_path}

**Important**: All agents must work in {local_path} directory."""
    )


def create_github_deployment_task(
    agent,
    project_dir: str,
    repo_name: str,
    github_username: str,
    context_tasks: Optional[List] = None
):
    """Task to commit and push code to the already-cloned repository."""
    
    return Task(
        description=f"""Commit and push all code to GitHub. Follow these EXACT steps in order.

PROJECT DIRECTORY: {project_dir}
REPOSITORY: https://github.com/{github_username}/{repo_name}

═══════════════════════════════════════════════════════════════════════════════
⚠️ EXECUTE THESE STEPS IN EXACT ORDER - DO NOT SKIP OR REPEAT
═══════════════════════════════════════════════════════════════════════════════

STEP 1: Check Repository Status (DO THIS ONCE ONLY)
───────────────────────────────────────────────────────────────────────────────
Tool Name: "Get repository status"
Arguments:
{{
  "directory": "{project_dir}",
  "verbose": true
}}

After executing: Read the output and move to STEP 2. DO NOT run this tool again.

STEP 2: List All Files (DO THIS ONCE ONLY)
───────────────────────────────────────────────────────────────────────────────
Tool Name: "List directory contents"
Arguments:
{{
  "directory": "{project_dir}",
  "recursive": true
}}

After executing: Verify files exist and move to STEP 3. DO NOT run this tool again.

STEP 3: Create CHANGELOG.md (DO THIS ONCE ONLY)
───────────────────────────────────────────────────────────────────────────────
Tool Name: "Write content to a file"
Arguments:
{{
  "file_path": "{project_dir}/CHANGELOG.md",
  "content": "# Changelog\\n\\n## [1.0.0] - Initial Release\\n\\n### Added\\n- Complete project implementation\\n- Comprehensive tests\\n- Full documentation\\n",
  "mode": "w"
}}

After executing: File created. Move to STEP 4. DO NOT run this tool again.

STEP 4: Commit ALL Changes (DO THIS ONCE ONLY)
───────────────────────────────────────────────────────────────────────────────
Tool Name: "Add and commit changes"
Arguments:
{{
  "directory": "{project_dir}",
  "message": "Complete project implementation with tests and documentation",
  "add_all": true
}}

After executing: Changes committed. Move to STEP 5. DO NOT run this tool again.

STEP 5: Push to GitHub (DO THIS ONCE ONLY)
───────────────────────────────────────────────────────────────────────────────
Tool Name: "Push to remote repository"
Arguments:
{{
  "directory": "{project_dir}",
  "remote": "origin",
  "branch": "main",
  "force": false,
  "set_upstream": true
}}

After executing: Code pushed to GitHub. Move to STEP 6. DO NOT run this tool again.

STEP 6: Create Version Tag (DO THIS ONCE ONLY)
───────────────────────────────────────────────────────────────────────────────
Tool Name: "Create and push tag"
Arguments:
{{
  "directory": "{project_dir}",
  "tag_name": "v1.0.0",
  "message": "Initial release - fully functional project",
  "push": true,
  "remote": "origin"
}}

After executing: Tag created and pushed. Move to STEP 7. DO NOT run this tool again.

STEP 7: Final Verification (DO THIS ONCE ONLY)
───────────────────────────────────────────────────────────────────────────────
Tool Name: "Get repository status"
Arguments:
{{
  "directory": "{project_dir}",
  "verbose": true
}}

After executing: Verify working tree is clean. Move to STEP 8. DO NOT run this tool again.

STEP 8: Create Deployment Report (DO THIS ONCE ONLY - FINAL STEP)
───────────────────────────────────────────────────────────────────────────────
Tool Name: "Write content to a file"
Arguments:
{{
  "file_path": "{project_dir}/DEPLOYMENT_REPORT.md",
  "content": "# Deployment Report\\n\\n## Status\\n✅ SUCCESSFUL\\n\\n## Repository\\nhttps://github.com/{github_username}/{repo_name}\\n\\n## Summary\\n- All files committed\\n- Pushed to main branch\\n- Tag v1.0.0 created\\n- Deployment complete\\n",
  "mode": "w"
}}

After executing: Report created. YOU ARE DONE. STOP HERE.

═══════════════════════════════════════════════════════════════════════════════
⚠️ CRITICAL RULES:
═══════════════════════════════════════════════════════════════════════════════

1. Execute steps 1-8 in EXACT order
2. Do each step ONLY ONCE
3. Do NOT repeat "Get repository status" multiple times
4. Do NOT go back to previous steps
5. After step 8, you are DONE - provide your final answer

If a tool fails:
- Read the error message
- Fix the arguments for THAT tool only
- Try that ONE tool again
- Then continue to the next step

DO NOT:
❌ Run "Get repository status" more than twice (steps 1 and 7 only)
❌ Skip steps
❌ Repeat steps unnecessarily
❌ Get stuck in a loop

═══════════════════════════════════════════════════════════════════════════════
PROGRESS TRACKING:
═══════════════════════════════════════════════════════════════════════════════

After each step, say: "✅ Completed Step X, moving to Step Y"

This helps you track progress and prevents loops.

═══════════════════════════════════════════════════════════════════════════════
BEGIN WITH STEP 1 NOW!
═══════════════════════════════════════════════════════════════════════════════
""",
        
        agent=agent,
        context=context_tasks,
        expected_output=f"""Deployment completion report with steps executed:

✅ Step 1: Get repository status - Verified git setup
✅ Step 2: List directory contents - Confirmed all files present
✅ Step 3: Write CHANGELOG.md - Created changelog
✅ Step 4: Add and commit changes - All files committed
✅ Step 5: Push to remote repository - Pushed to GitHub
✅ Step 6: Create and push tag - Tag v1.0.0 created
✅ Step 7: Get repository status - Final verification complete
✅ Step 8: Write DEPLOYMENT_REPORT.md - Report created

**Repository**: https://github.com/{github_username}/{repo_name}
**Status**: ✅ DEPLOYMENT SUCCESSFUL
**All 8 steps completed successfully**"""
    )