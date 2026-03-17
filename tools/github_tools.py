from github import Github, GithubException
from git import Repo, GitCommandError
from pathlib import Path
from typing import List
from datetime import datetime
from crewai.tools import tool
from config import GITHUB_TOKEN, GITHUB_USERNAME


# Comprehensive .gitignore templates by language/framework
GITIGNORE_TEMPLATES = {
    'python': '''# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class
*.so

# Distribution / packaging
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
venv/
env/
ENV/
.venv

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/
.hypothesis/

# IDEs
.vscode/
.idea/
*.swp
*.swo
*~

# Environment
.env
.env.local
*.log

# OS
.DS_Store
Thumbs.db
''',
    'javascript': '''# Dependencies
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*
.npm
.yarn-integrity

# Build output
dist/
build/
out/
.next/
.nuxt/

# Testing
coverage/
.nyc_output/

# Cache
.cache/
.eslintcache
*.tsbuildinfo

# Environment
.env
.env.local
.env.development.local
.env.test.local
.env.production.local

# IDEs
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db
''',
    'typescript': '''# Dependencies
node_modules/
npm-debug.log*
yarn-debug.log*
.npm

# Build output
dist/
build/
lib/
*.tsbuildinfo

# Testing
coverage/

# Cache
.cache/
.eslintcache

# Environment
.env
.env.local

# IDEs
.vscode/
.idea/
*.swp

# OS
.DS_Store
Thumbs.db
''',
    'java': '''# Compiled files
*.class
*.jar
*.war
*.ear
target/
build/

# IDE
.idea/
*.iml
.project
.classpath
.settings/
*.swp

# Gradle
.gradle/
gradle-app.setting

# Maven
dependency-reduced-pom.xml

# Logs
*.log

# OS
.DS_Store
Thumbs.db
''',
    'go': '''# Binaries
*.exe
*.exe~
*.dll
*.so
*.dylib
*.test

# Output
bin/
dist/

# Dependencies
vendor/

# IDEs
.vscode/
.idea/
*.swp

# OS
.DS_Store
Thumbs.db

# Go workspace
go.work
''',
    'rust': '''# Build output
target/
Cargo.lock  # Remove if library

# Backup files
*.rs.bk
*.swp

# IDEs
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db
''',
    'csharp': '''# Build results
[Dd]ebug/
[Rr]elease/
x64/
x86/
[Bb]in/
[Oo]bj/

# User-specific files
*.suo
*.user
*.userosscache
*.sln.docstates

# Visual Studio
.vs/
*.nupkg

# ReSharper
_ReSharper*/
*.DotSettings.user

# OS
.DS_Store
Thumbs.db
''',
    'ruby': '''# Gems
*.gem
Gemfile.lock

# Bundler
.bundle/
vendor/bundle/

# Testing
coverage/

# IDEs
.vscode/
.idea/
*.swp

# OS
.DS_Store
Thumbs.db
''',
    'php': '''# Dependencies
vendor/
composer.lock

# Laravel
/storage/*.key
/public/storage
/public/hot
.env

# Testing
coverage/

# IDEs
.vscode/
.idea/
*.swp

# OS
.DS_Store
Thumbs.db
''',
    'swift': '''# Xcode
xcuserdata/
*.xcworkspace
!*.xcworkspace/contents.xcworkspacedata
*.xcodeproj/*
!*.xcodeproj/project.pbxproj
!*.xcodeproj/xcshareddata/

# CocoaPods
Pods/

# Carthage
Carthage/Build/

# Swift Package Manager
.build/
.swiftpm/

# IDEs
.vscode/
*.swp

# OS
.DS_Store
''',
    'web': '''# Dependencies
node_modules/

# Build
dist/
build/
.cache/

# Environment
.env
.env.local

# IDEs
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db
''',
}


def detect_project_type(directory: str) -> str:
    """Detect project type/language from directory structure"""
    path = Path(directory)
    
    # Check for specific files
    if (path / 'requirements.txt').exists() or (path / 'setup.py').exists():
        return 'python'
    elif (path / 'package.json').exists():
        if (path / 'tsconfig.json').exists():
            return 'typescript'
        return 'javascript'
    elif (path / 'pom.xml').exists() or (path / 'build.gradle').exists():
        return 'java'
    elif (path / 'go.mod').exists():
        return 'go'
    elif (path / 'Cargo.toml').exists():
        return 'rust'
    elif list(path.glob('*.csproj')) or list(path.glob('*.sln')):
        return 'csharp'
    elif (path / 'Gemfile').exists():
        return 'ruby'
    elif (path / 'composer.json').exists():
        return 'php'
    elif (path / 'Package.swift').exists():
        return 'swift'
    
    return 'general'


def generate_gitignore(project_type: str) -> str:
    """Generate appropriate .gitignore content"""
    # Base ignores for all projects
    base_ignore = '''# Editor directories and files
.vscode/
.idea/
*.swp
*.swo
*~

# OS files
.DS_Store
Thumbs.db
desktop.ini

# Environment variables
.env
.env.local

# Logs
*.log
logs/

# Temporary files
tmp/
temp/
*.tmp
'''
    
    # Get language-specific template
    specific = GITIGNORE_TEMPLATES.get(project_type, '')
    
    return (specific + '\n' + base_ignore).strip()


@tool("Create GitHub repository")
def create_github_repo(repo_name: str, description: str = "", private: bool = False,
                       has_issues: bool = True, has_wiki: bool = False,
                       has_projects: bool = False, auto_init: bool = False,
                       license_template: str = None) -> str:
    """
    Creates a new GitHub repository with comprehensive options.
    
    Args:
        repo_name: Repository name
        description: Repository description
        private: Make repository private (default: False)
        has_issues: Enable issues (default: True)
        has_wiki: Enable wiki (default: False)
        has_projects: Enable projects (default: False)
        auto_init: Initialize with README (default: False)
        gitignore_template: GitHub gitignore template (e.g., 'Python', 'Node')
        license_template: License template (e.g., 'mit', 'apache-2.0')
    
    Returns:
        Success message with repository URL or error message
    """
    try:
        if not GITHUB_TOKEN:
            return "✗ Error: GitHub token not configured.\n" \
                   "Set GITHUB_TOKEN in .env file or environment variables."
        
        g = Github(GITHUB_TOKEN)
        user = g.get_user()
        
        # Create repository with options
        repo = user.create_repo(
            name=repo_name,
            description=description,
            private=private,
            has_issues=has_issues,
            has_wiki=has_wiki,
            has_projects=has_projects,
            auto_init=auto_init,
            license_template=license_template
        )
        
        output = "✓ Repository created successfully\n"
        output += "═" * 70 + "\n"
        output += f"Name: {repo.name}\n"
        output += f"URL: {repo.html_url}\n"
        output += f"Clone (HTTPS): {repo.clone_url}\n"
        output += f"Clone (SSH): {repo.ssh_url}\n"
        output += f"Visibility: {'Private' if private else 'Public'}\n"
        output += f"Issues: {'Enabled' if has_issues else 'Disabled'}\n"
        
        return output
        
    except GithubException as e:
        return f"✗ GitHub API Error: {e.data.get('message', str(e))}"
    except Exception as e:
        return f"✗ Error creating repository: {str(e)}"


@tool("Initialize Git repository")
def init_git(directory: str, initial_branch: str = "main",
             create_gitignore: bool = False, project_type: str = None) -> str:
    """
    Initializes a Git repository with best practices.
    
    Args:
        directory: Directory path to initialize
        initial_branch: Name of initial branch (default: 'main')
        create_gitignore: Create .gitignore file (default: True)
        project_type: Project type for .gitignore (auto-detected if None)
    
    Returns:
        Success message or error message
    """
    try:
        path = Path(directory)
        
        if not path.exists():
            return f"✗ Error: Directory does not exist: {directory}"
        
        # Check if already a git repository
        try:
            existing_repo = Repo(directory)
            return f"⚠ Directory is already a Git repository\n" \
                   f"Current branch: {existing_repo.active_branch.name}"
        except:
            pass  # Not a repo, continue with initialization
        
        # Initialize repository
        repo = Repo.init(directory)
        
        # Set initial branch name (for newer git versions)
        try:
            # Try to rename master to main if needed
            if repo.active_branch.name != initial_branch:
                repo.git.branch('-M', initial_branch)
        except:
            # For older git versions or if branch already exists
            pass
        
        output = "✓ Git repository initialized\n"
        output += "═" * 70 + "\n"
        output += f"Directory: {directory}\n"
        output += f"Branch: {initial_branch}\n"
        
        # Create .gitignore if requested
        if create_gitignore:
            if not project_type:
                project_type = detect_project_type(directory)
            
            gitignore_path = path / '.gitignore'
            
            if not gitignore_path.exists():
                gitignore_content = generate_gitignore(project_type)
                gitignore_path.write_text(gitignore_content, encoding='utf-8')
                output += f"✓ Created .gitignore ({project_type} template)\n"
            else:
                output += "⚠ .gitignore already exists (not modified)\n"
        
        # Configure git user if not set
        try:
            repo.config_reader().get_value('user', 'name')
        except:
            output += "\n⚠ Git user not configured. Set with:\n"
            output += "  git config user.name 'Your Name'\n"
            output += "  git config user.email 'your.email@example.com'\n"
        
        return output
        
    except GitCommandError as e:
        return f"✗ Git Command Error: {str(e)}"
    except Exception as e:
        return f"✗ Error initializing Git repository: {str(e)}"


@tool("Add and commit changes")
def commit_changes(directory: str, message: str, add_all: bool = True,
                  files: List[str] = None) -> str:
    """
    Commits changes to Git repository.
    
    Args:
        directory: Repository directory
        message: Commit message
        add_all: Add all changes (default: True)
        files: Specific files to add (if add_all is False)
    
    Returns:
        Success message with commit details or error message
    """
    try:
        path = Path(directory)
        
        # Check if directory exists
        if not path.exists():
            return f"✗ Error: Directory does not exist: {directory}"
        
        # Check if it's a git repository
        try:
            repo = Repo(directory)
        except:
            return f"✗ Error: Not a Git repository. Initialize with 'git init' first.\n" \
                   f"Directory: {directory}"
        
        if repo.bare:
            return "✗ Error: Repository is bare (no working directory)"
        
        # Validate commit message
        if not message or not message.strip():
            return "✗ Error: Commit message cannot be empty"
        
        # Check for git user configuration
        try:
            user_name = repo.config_reader().get_value('user', 'name')
            user_email = repo.config_reader().get_value('user', 'email')
        except:
            return "✗ Error: Git user not configured.\n" \
                   "Configure with:\n" \
                   "  git config user.name 'Your Name'\n" \
                   "  git config user.email 'your.email@example.com'\n" \
                   "Or set globally with --global flag"
        
        # Check if there are changes
        is_dirty = repo.is_dirty(untracked_files=True)
        has_untracked = len(repo.untracked_files) > 0
        
        if not is_dirty and not has_untracked:
            return "⚠ No changes to commit (working tree clean)"
        
        # Stage changes
        try:
            if add_all:
                # Add all files including untracked
                repo.git.add(A=True)
                staged_info = "All changes"
            elif files:
                # Add specific files
                repo.index.add(files)
                staged_info = f"{len(files)} file(s): {', '.join(files[:3])}"
                if len(files) > 3:
                    staged_info += f" and {len(files) - 3} more"
            else:
                return "✗ Error: No files specified and add_all is False"
        except GitCommandError as e:
            return f"✗ Error staging files: {str(e)}"
        
        # Verify something is staged
        if not repo.index.diff("HEAD") and not has_untracked:
            return "⚠ No changes staged for commit"
        
        # Commit
        try:
            commit = repo.index.commit(message)
        except GitCommandError as e:
            return f"✗ Error creating commit: {str(e)}"
        
        # Get stats
        try:
            if len(list(repo.iter_commits())) > 1:
                stats = repo.git.diff('HEAD~1', '--shortstat')
            else:
                # First commit, show file count
                stats = f"{len(repo.tree().traverse())} file(s) in first commit"
        except:
            stats = "Statistics unavailable"
        
        output = "✓ Changes committed successfully\n"
        output += "═" * 70 + "\n"
        output += f"Commit: {commit.hexsha[:8]}\n"
        output += f"Author: {commit.author.name} <{commit.author.email}>\n"
        output += f"Date: {datetime.fromtimestamp(commit.committed_date).strftime('%Y-%m-%d %H:%M:%S')}\n"
        output += f"Message: {message}\n"
        output += f"Staged: {staged_info}\n"
        
        if stats:
            output += f"Stats: {stats}\n"
        
        # Show current branch
        try:
            output += f"Branch: {repo.active_branch.name}\n"
        except:
            output += "Branch: (detached HEAD)\n"
        
        return output
        
    except GitCommandError as e:
        return f"✗ Git Command Error: {str(e)}"
    except Exception as e:
        return f"✗ Error committing changes: {str(e)}\n" \
               f"Directory: {directory}"


# Also update the deploy_to_github function with better error handling:
@tool("Complete GitHub deployment")
def deploy_to_github(directory: str, repo_name: str, description: str = "",
                    commit_message: str = "Initial commit", private: bool = False,
                    branch: str = "main", create_readme: bool = False,
                    license_type: str = None) -> str:
    """
    Complete GitHub deployment workflow: init, gitignore, commit, create repo, and push.
    
    Performs these steps:
    1. Initializes Git repository (if not already initialized)
    2. Creates appropriate .gitignore file
    3. Optionally creates README.md
    4. Commits all changes
    5. Creates GitHub repository
    6. Adds remote and pushes code
    7. Creates initial release tag
    
    Args:
        directory: Project directory
        repo_name: GitHub repository name
        description: Repository description
        commit_message: Initial commit message
        private: Make repository private (default: False)
        branch: Branch name (default: 'main')
        create_readme: Create README.md if not exists (default: False)
        license_type: License template (e.g., 'mit', 'apache-2.0')
    
    Returns:
        Detailed deployment report or error message
    """
    try:
        if not GITHUB_TOKEN or not GITHUB_USERNAME:
            return "✗ Error: GitHub credentials not configured.\n" \
                   "Set GITHUB_TOKEN and GITHUB_USERNAME in .env file."
        
        path = Path(directory)
        if not path.exists():
            return f"✗ Error: Directory does not exist: {directory}"
        
        results = []
        
        # Step 1: Initialize Git (if not already)
        try:
            repo = Repo(directory)
            results.append("✓ Using existing Git repository")
        except:
            repo = Repo.init(directory)
            # Set branch to main
            try:
                repo.git.branch('-M', branch)
            except:
                pass
            results.append(f"✓ Git repository initialized (branch: {branch})")
        
        # Configure git user if not set (use GitHub credentials)
        try:
            repo.config_reader().get_value('user', 'name')
        except:
            try:
                # Try to set from GitHub
                g = Github(GITHUB_TOKEN)
                user = g.get_user()
                repo.config_writer().set_value('user', 'name', user.name or GITHUB_USERNAME).release()
                repo.config_writer().set_value('user', 'email', user.email or f'{GITHUB_USERNAME}@users.noreply.github.com').release()
                results.append("✓ Git user configured from GitHub")
            except:
                results.append("⚠ Git user not configured (may cause issues)")
        
        # Step 2: Detect project type and create .gitignore
        project_type = detect_project_type(directory)
        gitignore_path = path / '.gitignore'
        
        if not gitignore_path.exists():
            gitignore_content = generate_gitignore(project_type)
            gitignore_path.write_text(gitignore_content, encoding='utf-8')
            results.append(f"✓ Created .gitignore ({project_type} template)")
        else:
            results.append("✓ Using existing .gitignore")
        
        # Step 3: Create README if requested
        readme_path = path / 'README.md'
        if create_readme and not readme_path.exists():
            readme_content = f"# {repo_name}\n\n{description}\n\n## Installation\n\nTBD\n\n## Usage\n\nTBD\n"
            readme_path.write_text(readme_content, encoding='utf-8')
            results.append("✓ Created README.md")
        
        # Step 4: Commit all changes
        try:
            if repo.is_dirty(untracked_files=True) or len(repo.untracked_files) > 0:
                repo.git.add(A=True)
                commit = repo.index.commit(commit_message)
                results.append(f"✓ Changes committed ({commit.hexsha[:8]}): {commit_message}")
            else:
                results.append("⚠ No changes to commit")
        except GitCommandError as e:
            results.append(f"⚠ Commit warning: {str(e)}")
        
        # Step 5: Create GitHub repository
        g = Github(GITHUB_TOKEN)
        user = g.get_user()
        
        try:
            gh_repo = user.create_repo(
                name=repo_name,
                description=description,
                private=private,
                has_issues=True,
                has_wiki=False,
                has_projects=False,
                auto_init=False,
                license_template=license_type
            )
            results.append(f"✓ GitHub repository created")
            repo_url = gh_repo.html_url
        except GithubException as e:
            if e.status == 422 and 'already exists' in str(e.data):
                # Repository already exists, try to use it
                gh_repo = user.get_repo(repo_name)
                results.append(f"⚠ Using existing GitHub repository")
                repo_url = gh_repo.html_url
            else:
                raise
        
        # Step 6: Add remote and push
        remote_url = f"https://{GITHUB_TOKEN}@github.com/{GITHUB_USERNAME}/{repo_name}.git"
        
        # Add remote if doesn't exist
        try:
            if 'origin' not in [r.name for r in repo.remotes]:
                repo.create_remote('origin', remote_url)
                results.append("✓ Remote 'origin' added")
            else:
                # Update remote URL
                repo.remote('origin').set_url(remote_url)
                results.append("✓ Remote 'origin' updated")
        except Exception as e:
            results.append(f"⚠ Remote setup warning: {str(e)}")
        
        # Ensure we're on the correct branch
        try:
            if repo.active_branch.name != branch:
                repo.git.checkout('-b', branch)
        except:
            pass
        
        # Push to GitHub
        try:
            origin = repo.remote('origin')
            push_info = origin.push(refspec=f'{branch}:{branch}', set_upstream=True, force=True)
            
            # Check push result
            has_error = False
            for info in push_info:
                if info.flags & info.ERROR:
                    results.append(f"✗ Push error: {info.summary}")
                    has_error = True
                elif info.flags & info.REJECTED:
                    results.append(f"⚠ Push rejected: {info.summary}")
            
            if not has_error:
                results.append(f"✓ Code pushed to GitHub ({branch} branch)")
        except GitCommandError as e:
            results.append(f"⚠ Push warning: {str(e)}")
        
        # Step 7: Create initial tag
        try:
            tag_name = "v1.0.0"
            if tag_name not in repo.tags:
                repo.create_tag(tag_name, message="Initial release")
                origin.push(tag_name)
                results.append(f"✓ Created and pushed tag: {tag_name}")
            else:
                results.append("⚠ Tag v1.0.0 already exists")
        except Exception as e:
            results.append(f"⚠ Tag creation skipped: {str(e)}")
        
        # Generate final report
        output = "GitHub Deployment Complete\n"
        output += "═" * 70 + "\n\n"
        output += "Deployment Steps:\n"
        for i, result in enumerate(results, 1):
            output += f"{i}. {result}\n"
        
        output += "\n" + "═" * 70 + "\n"
        output += "Repository Information:\n"
        output += f"  Name: {repo_name}\n"
        output += f"  URL: {repo_url}\n"
        output += f"  Clone (HTTPS): {gh_repo.clone_url}\n"
        output += f"  Clone (SSH): {gh_repo.ssh_url}\n"
        output += f"  Visibility: {'Private' if private else 'Public'}\n"
        output += f"  Branch: {branch}\n"
        output += f"  Project Type: {project_type}\n"
        
        output += "\n" + "═" * 70 + "\n"
        output += "Next Steps:\n"
        output += "  1. Visit repository: " + repo_url + "\n"
        output += "  2. Configure repository settings (branch protection, etc.)\n"
        output += "  3. Add collaborators if needed\n"
        output += "  4. Set up GitHub Actions workflows\n"
        output += "  5. Enable GitHub Pages (if applicable)\n"
        
        return output
        
    except GithubException as e:
        return f"✗ GitHub API Error: {e.data.get('message', str(e))}"
    except GitCommandError as e:
        return f"✗ Git Command Error: {str(e)}"
    except Exception as e:
        return f"✗ Error in GitHub deployment: {str(e)}"


@tool("Push to remote repository")
def push_to_remote(directory: str, remote: str = "origin", branch: str = None,
                  force: bool = False, set_upstream: bool = True) -> str:
    """
    Pushes commits to remote repository.
    
    Args:
        directory: Repository directory
        remote: Remote name (default: 'origin')
        branch: Branch name (default: current branch)
        force: Force push (default: False)
        set_upstream: Set upstream tracking (default: True)
    
    Returns:
        Success message or error message
    """
    try:
        repo = Repo(directory)
        
        # Get branch
        if not branch:
            branch = repo.active_branch.name
        
        # Check if remote exists
        if remote not in [r.name for r in repo.remotes]:
            return f"✗ Error: Remote '{remote}' not found.\n" \
                   f"Available remotes: {', '.join([r.name for r in repo.remotes])}"
        
        remote_obj = repo.remote(remote)
        
        # Build push arguments
        push_args = {}
        if force:
            push_args['force'] = True
        if set_upstream:
            push_args['set_upstream'] = True
        
        # Push
        refspec = f"{branch}:{branch}"
        push_info = remote_obj.push(refspec=refspec, **push_args)
        
        output = "✓ Successfully pushed to remote\n"
        output += "═" * 70 + "\n"
        output += f"Remote: {remote}\n"
        output += f"Branch: {branch}\n"
        output += f"URL: {remote_obj.url}\n"
        
        # Check push results
        for info in push_info:
            if info.flags & info.ERROR:
                output += f"✗ Error: {info.summary}\n"
            elif info.flags & info.REJECTED:
                output += f"✗ Rejected: {info.summary}\n"
            elif info.flags & info.UP_TO_DATE:
                output += f"⚠ Already up to date\n"
            else:
                output += f"✓ Push successful: {info.summary}\n"
        
        return output
        
    except GitCommandError as e:
        return f"✗ Git Error: {e.stderr}"
    except Exception as e:
        return f"✗ Error pushing to remote: {str(e)}"


@tool("Add remote repository")
def add_remote(directory: str, name: str, url: str, fetch: bool = False) -> str:
    """
    Adds a remote repository.
    
    Args:
        directory: Repository directory
        name: Remote name (e.g., 'origin', 'upstream')
        url: Remote URL (HTTPS or SSH)
        fetch: Fetch from remote after adding (default: False)
    
    Returns:
        Success message or error message
    """
    try:
        repo = Repo(directory)
        
        # Check if remote already exists
        if name in [r.name for r in repo.remotes]:
            return f"✗ Error: Remote '{name}' already exists.\n" \
                   f"Use a different name or remove the existing remote first."
        
        # Add remote
        remote = repo.create_remote(name, url)
        
        output = f"✓ Remote '{name}' added successfully\n"
        output += "═" * 70 + "\n"
        output += f"Name: {name}\n"
        output += f"URL: {url}\n"
        
        # Fetch if requested
        if fetch:
            remote.fetch()
            output += "✓ Fetched from remote\n"
        
        return output
        
    except Exception as e:
        return f"✗ Error adding remote: {str(e)}"


@tool("Create and push tag")
def create_tag(directory: str, tag_name: str, message: str = None,
              push: bool = True, remote: str = "origin") -> str:
    """
    Creates a Git tag and optionally pushes it.
    
    Args:
        directory: Repository directory
        tag_name: Tag name (e.g., 'v1.0.0', 'release-1.0')
        message: Tag message (creates annotated tag if provided)
        push: Push tag to remote (default: True)
        remote: Remote to push to (default: 'origin')
    
    Returns:
        Success message or error message
    """
    try:
        repo = Repo(directory)
        
        # Create tag
        if message:
            tag = repo.create_tag(tag_name, message=message)
            tag_type = "Annotated"
        else:
            tag = repo.create_tag(tag_name)
            tag_type = "Lightweight"
        
        output = f"✓ Tag '{tag_name}' created successfully\n"
        output += "═" * 70 + "\n"
        output += f"Type: {tag_type}\n"
        output += f"Tag: {tag_name}\n"
        
        if message:
            output += f"Message: {message}\n"
        
        # Push if requested
        if push and remote in [r.name for r in repo.remotes]:
            remote_obj = repo.remote(remote)
            remote_obj.push(tag_name)
            output += f"✓ Tag pushed to {remote}\n"
        
        return output
        
    except Exception as e:
        return f"✗ Error creating tag: {str(e)}"


@tool("Get repository status")
def get_repo_status(directory: str, verbose: bool = True) -> str:
    """
    Gets the status of a Git repository.
    
    Args:
        directory: Repository directory
        verbose: Show detailed status (default: True)
    
    Returns:
        Repository status information
    """
    try:
        repo = Repo(directory)
        
        output = "Git Repository Status\n"
        output += "═" * 70 + "\n"
        
        # Current branch
        try:
            current_branch = repo.active_branch.name
            output += f"Branch: {current_branch}\n"
        except TypeError:
            output += "Branch: (detached HEAD)\n"
            current_branch = None
        
        # Remote tracking
        if current_branch:
            try:
                tracking = repo.active_branch.tracking_branch()
                if tracking:
                    output += f"Tracking: {tracking.name}\n"
                    
                    # Count commits ahead/behind
                    ahead = list(repo.iter_commits(f'{tracking.name}..{current_branch}'))
                    behind = list(repo.iter_commits(f'{current_branch}..{tracking.name}'))
                    
                    if ahead:
                        output += f"Ahead: {len(ahead)} commit(s)\n"
                    if behind:
                        output += f"Behind: {len(behind)} commit(s)\n"
                    if not ahead and not behind:
                        output += "Status: Up to date with remote\n"
            except:
                output += "Tracking: Not set\n"
        
        # Working tree status
        output += "\n"
        if repo.is_dirty(untracked_files=True):
            output += "Working Tree: Modified\n"
            
            if verbose:
                # Modified files
                modified = [item.a_path for item in repo.index.diff(None)]
                if modified:
                    output += f"\nModified files ({len(modified)}):\n"
                    for file in modified[:10]:  # Show first 10
                        output += f"  M {file}\n"
                    if len(modified) > 10:
                        output += f"  ... and {len(modified) - 10} more\n"
                
                # Staged files
                staged = [item.a_path for item in repo.index.diff("HEAD")]
                if staged:
                    output += f"\nStaged files ({len(staged)}):\n"
                    for file in staged[:10]:
                        output += f"  A {file}\n"
                    if len(staged) > 10:
                        output += f"  ... and {len(staged) - 10} more\n"
                
                # Untracked files
                untracked = repo.untracked_files
                if untracked:
                    output += f"\nUntracked files ({len(untracked)}):\n"
                    for file in untracked[:10]:
                        output += f"  ? {file}\n"
                    if len(untracked) > 10:
                        output += f"  ... and {len(untracked) - 10} more\n"
        else:
            output += "Working Tree: Clean\n"
        
        # Last commit
        try:
            last_commit = repo.head.commit
            output += f"\nLast Commit:\n"
            output += f"  Hash: {last_commit.hexsha[:8]}\n"
            output += f"  Author: {last_commit.author.name}\n"
            output += f"  Date: {datetime.fromtimestamp(last_commit.committed_date).strftime('%Y-%m-%d %H:%M:%S')}\n"
            output += f"  Message: {last_commit.message.strip()}\n"
        except:
            pass
        
        # Remotes
        remotes = list(repo.remotes)
        if remotes:
            output += f"\nRemotes ({len(remotes)}):\n"
            for remote in remotes:
                output += f"  {remote.name}: {remote.url}\n"
        
        return output
        
    except Exception as e:
        return f"✗ Error getting repository status: {str(e)}"

@tool("Clone GitHub repository")
def clone_repository(repo_url: str, local_path: str, branch: str = "main") -> str:
    """
    Clones a GitHub repository to local directory.
    
    Args:
        repo_url: Repository URL (HTTPS or SSH)
        local_path: Local directory path to clone into
        branch: Branch to checkout (default: 'main')
    
    Returns:
        Success message or error message
    """
    try:
        local_path = Path(local_path)
        
        # Check if directory already exists
        if local_path.exists():
            # Check if it's already a git repo
            try:
                repo = Repo(local_path)
                return f"⚠ Directory already exists and is a Git repository\n" \
                       f"Path: {local_path}\n" \
                       f"Current branch: {repo.active_branch.name}"
            except:
                return f"✗ Error: Directory already exists but is not a Git repository: {local_path}"
        
        # Clone the repository
        print(f"Cloning {repo_url} to {local_path}...")
        repo = Repo.clone_from(repo_url, local_path, branch=branch)
        
        output = "✓ Repository cloned successfully\n"
        output += "═" * 70 + "\n"
        output += f"Repository URL: {repo_url}\n"
        output += f"Local path: {local_path}\n"
        output += f"Branch: {branch}\n"
        output += f"Remote: {repo.remote().url}\n"
        
        # List files
        files = list(local_path.rglob("*"))
        file_count = len([f for f in files if f.is_file()])
        output += f"Files: {file_count}\n"
        
        return output
        
    except GitCommandError as e:
        return f"✗ Git Error: {str(e)}"
    except Exception as e:
        return f"✗ Error cloning repository: {str(e)}"
