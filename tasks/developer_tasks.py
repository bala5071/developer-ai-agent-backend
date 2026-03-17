from crewai import Task


def create_development_task(agent, project_dir: str, project_type: str, context_tasks: list = None):
    dev_description =f"""Based on the technical plan, implement the complete project with production-ready code:

                    PROJECT DIRECTORY: {project_dir}
                    PROJECT TYPE: {project_type}

                    ═══════════════════════════════════════════════════════════════════════════════
                    🎯 CRITICAL: FILE LOCATION
                    ═══════════════════════════════════════════════════════════════════════════════

                    ALL FILES MUST BE CREATED IN THIS EXACT DIRECTORY:
                    {project_dir}

                    DO NOT create files anywhere else!
                    DO NOT use relative paths!
                    DO NOT create a subdirectory with the project name!

                    When using "Write content to a file" tool, ALWAYS use full paths like:
                    - {project_dir}/main.py
                    - {project_dir}/README.md
                    - {project_dir}/tests/test_main.py
                    - {project_dir}/.gitignore

                    based on the project directory given implement the project as the directory has been already created.

                    ═══════════════════════════════════════════════════════════════════════════════
                    YOUR IMPLEMENTATION RESPONSIBILITIES:
                    ═══════════════════════════════════════════════════════════════════════════════

                    📁 PHASE 1: PROJECT STRUCTURE
                    ───────────────────────────────────────────────────────────────────────────────
                    1. Create the complete directory structure appropriate for the {project_type}:
                    - Follow language/framework conventions (src/, lib/, components/, etc.)
                    - Set up test directories (test/, tests/, __tests__)
                    - Create config/settings directories
                    - Set up asset/resource directories (if applicable)
                    - Create documentation directories (docs/)
                    
                    2. Initialize package/module files:
                    - Python: __init__.py files
                    - JavaScript/Node: package.json, index.js
                    - Java: package structure with appropriate directories
                    - Go: go.mod and package declarations
                    - C#: .csproj files and namespace structure
                    - Rust: Cargo.toml and lib.rs/main.rs

                    💻 PHASE 2: SOURCE CODE IMPLEMENTATION
                    ───────────────────────────────────────────────────────────────────────────────
                    3. Implement ALL source code files with complete functionality:
                    - Core business logic and algorithms
                    - Data models/entities/schemas
                    - API endpoints/routes/controllers (if applicable)
                    - Service layers and business logic
                    - Database access/repository layers (if applicable)
                    - UI components/views (if applicable)
                    - Utility functions and helpers
                    - Configuration and settings management
                    - Entry points (main.py, index.js, Main.java, etc.)

                    4. Code quality requirements:
                    - Write production-ready, fully functional code (NO placeholders!)
                    - Follow language-specific best practices and idioms
                    - Use appropriate design patterns
                    - Implement proper error handling and validation
                    - Add comprehensive inline comments for complex logic
                    - Include docstrings/JSDoc/Javadoc for all public APIs
                    - Use type hints/annotations where supported
                    - Ensure proper resource management (memory, files, connections)
                    - Write secure code following OWASP guidelines
                    - Make code testable with clear separation of concerns

                    📚 PHASE 3: COMPREHENSIVE DOCUMENTATION
                    ───────────────────────────────────────────────────────────────────────────────
                    5. Create a detailed README.md including:
                    - Project title and description (what it does and why)
                    - Key features and capabilities (with emojis for readability)
                    - Technology stack and dependencies with versions
                    - System requirements and prerequisites
                    - Step-by-step installation instructions:
                        * Platform-specific steps (Windows, macOS, Linux, iOS, Android)
                        * Package manager commands
                        * Build instructions
                        * Environment setup
                    - Configuration guide:
                        * Environment variables
                        * Config file examples
                        * API keys and credentials setup (without exposing secrets)
                    - Usage examples and tutorials:
                        * Quick start guide
                        * Code examples with expected output
                        * CLI command examples (if applicable)
                        * API endpoint examples (if applicable)
                        * Screenshots or GIFs (describe where they should go)
                    - API/Library reference documentation
                    - Architecture overview (for complex projects)
                    - Testing instructions
                    - Deployment guide
                    - Troubleshooting section with common issues
                    - Contributing guidelines (if open source)
                    - License information
                    - Credits and acknowledgments

                    6. Create additional documentation files:
                    - API.md: Detailed API documentation (if applicable)
                    - ARCHITECTURE.md: System architecture and design decisions (for complex projects)
                    - CONTRIBUTING.md: Guidelines for contributors (if open source)
                    - CHANGELOG.md: Version history and changes
                    - CODE_OF_CONDUCT.md: Community guidelines (if open source)

                    📦 PHASE 4: DEPENDENCY & CONFIGURATION MANAGEMENT
                    ───────────────────────────────────────────────────────────────────────────────
                    7. Create dependency manifests with PINNED VERSIONS:
                    
                    Python projects:
                    - requirements.txt (with exact versions: package==X.Y.Z)
                    - setup.py or pyproject.toml (for packages/libraries)
                    - dev-requirements.txt (for development dependencies)
                    
                    JavaScript/Node projects:
                    - package.json (with dependencies and scripts)
                    - package-lock.json or yarn.lock
                    - tsconfig.json (for TypeScript)
                    
                    Java projects:
                    - pom.xml (Maven) or build.gradle (Gradle)
                    - application.properties or application.yml
                    
                    C#/.NET projects:
                    - .csproj or .sln files
                    - NuGet package references
                    - appsettings.json
                    
                    Go projects:
                    - go.mod and go.sum
                    - Makefile for build tasks
                    
                    Rust projects:
                    - Cargo.toml and Cargo.lock
                    
                    Mobile projects:
                    - iOS: Podfile, Package.swift, Info.plist
                    - Android: build.gradle files, AndroidManifest.xml

                    8. Create configuration files:
                    - .env.example: Template for environment variables (NO SECRETS!)
                    - config.yml/config.json: Application configuration templates
                    - .gitignore: Exclude generated files, secrets, dependencies
                    - .dockerignore: For Docker builds
                    - .editorconfig: Consistent coding styles across editors
                    - Linter configs: .eslintrc, .pylintrc, etc.
                    - Formatter configs: .prettierrc, .black.toml, etc.
                    - CI/CD configs: .github/workflows, .gitlab-ci.yml, Jenkinsfile

                    🎯 PHASE 5: EXAMPLES & DEMONSTRATIONS
                    ───────────────────────────────────────────────────────────────────────────────
                    9. Create example/demo files:
                    - example.py/example.js/Example.java: Basic usage examples
                    - examples/ directory: Multiple use case demonstrations
                    - Sample data files: test.json, sample.csv, etc.
                    - Tutorial scripts: step-by-step walkthroughs
                    - Integration examples: Show how to use with other tools/services

                    🔧 PHASE 6: BUILD & DEPLOYMENT FILES
                    ───────────────────────────────────────────────────────────────────────────────
                    10. Create build and deployment configurations:
                        - Dockerfile: Container image definition
                        - docker-compose.yml: Multi-container setup
                        - Makefile: Build automation tasks
                        - Scripts: build.sh, deploy.sh, start.sh
                        - CI/CD pipelines: GitHub Actions, GitLab CI, Jenkins
                        - Cloud deployment configs: Kubernetes manifests, Terraform, CloudFormation
                        - Web server configs: nginx.conf, apache.conf (if applicable)

                    🧪 PHASE 7: TESTING SETUP (if specified in plan)
                    ───────────────────────────────────────────────────────────────────────────────
                    11. Create test infrastructure:
                        - Test configuration files (pytest.ini, jest.config.js, etc.)
                        - Test fixtures and mock data
                        - Sample test files demonstrating test patterns
                        - Test utilities and helpers
                        - Integration test setup

                    🛠️ PHASE 8: PROJECT-SPECIFIC FILES
                    ───────────────────────────────────────────────────────────────────────────────
                    12. Create additional files based on project type:
                        
                        Web Applications:
                        - HTML templates and layouts
                        - CSS/SCSS stylesheets
                        - JavaScript frontend code
                        - Static assets structure
                        - Webpack/Vite/Rollup configs
                        
                        Mobile Applications:
                        - Screen/View components
                        - Navigation setup
                        - Asset catalogs
                        - Platform-specific code
                        - Build configurations
                        
                        CLI Applications:
                        - Command definitions
                        - Argument parsing setup
                        - Help text and documentation
                        - Shell completion scripts
                        
                        Libraries/Packages:
                        - Public API definitions
                        - Type definitions (.d.ts, .pyi)
                        - Usage examples
                        - API documentation
                        
                        APIs/Services:
                        - OpenAPI/Swagger specification
                        - Postman/Insomnia collections
                        - API documentation
                        - Request/response examples
                        
                        Desktop Applications:
                        - UI layouts and components
                        - Menu definitions
                        - Application icons
                        - Installer configs

                    ═══════════════════════════════════════════════════════════════════════════════
                    CRITICAL IMPLEMENTATION RULES:
                    ═══════════════════════════════════════════════════════════════════════════════

                    ✅ YOU MUST:
                    ───────────────────────────────────────────────────────────────────────────────
                    ✓ Use the File Writer tool to create EVERY file
                    ✓ Use the Directory Creator tool to create ALL folders
                    ✓ Validate syntax using Code Validator tool after EACH file
                    ✓ Install required dependencies using the Dependency Installer tool
                    ✓ Write COMPLETE, WORKING, production-ready code
                    ✓ Implement FULL functionality for every feature
                    ✓ Follow the technical plan exactly
                    ✓ Use language-appropriate naming conventions
                    ✓ Add comprehensive error handling
                    ✓ Write secure code (validate inputs, sanitize outputs)
                    ✓ Document every public function/method/class
                    ✓ Include usage examples in code documentation
                    ✓ Create working configuration examples
                    ✓ Test that imports/dependencies are correct
                    ✓ Ensure code is formatted according to language standards
                    ✓ Make code maintainable and extensible
                    ✓ Follow DRY (Don't Repeat Yourself) principle
                    ✓ Apply SOLID principles where appropriate

                    ❌ YOU MUST NEVER:
                    ───────────────────────────────────────────────────────────────────────────────
                    ✗ Leave TODO comments or placeholder code
                    ✗ Write "implement later" or "coming soon" comments
                    ✗ Use generic variable names (x, temp, data, thing)
                    ✗ Skip error handling or validation
                    ✗ Omit documentation or docstrings
                    ✗ Hardcode sensitive data (passwords, API keys, tokens)
                    ✗ Hardcode file paths or URLs
                    ✗ Copy-paste code instead of creating reusable functions
                    ✗ Write functions longer than 50-75 lines
                    ✗ Nest code more than 4 levels deep
                    ✗ Ignore the technical specification
                    ✗ Assume inputs are valid without validation
                    ✗ Use deprecated APIs or libraries
                    ✗ Leave debugging print/console.log statements
                    ✗ Commit generated files or dependencies to version control
                    ✗ Skip platform-specific considerations
                    ✗ Write code that only works in your environment

                    ═══════════════════════════════════════════════════════════════════════════════
                    QUALITY CHECKLIST - VERIFY BEFORE COMPLETION:
                    ═══════════════════════════════════════════════════════════════════════════════

                    Structure:
                    □ All directories created with proper organization
                    □ Files placed in correct locations per language conventions
                    □ Initialization files present (package.json, __init__.py, etc.)

                    Code:
                    □ All features from technical plan implemented
                    □ No placeholders or TODO comments remain
                    □ All functions have documentation
                    □ Error handling implemented throughout
                    □ Input validation on all user inputs
                    □ Type hints/annotations added where supported
                    □ Code follows language style guidelines
                    □ No hardcoded credentials or sensitive data
                    □ Resource cleanup implemented (files, connections, memory)

                    Documentation:
                    □ README.md is comprehensive and clear
                    □ Installation instructions are complete and tested
                    □ Usage examples are accurate and helpful
                    □ All configuration options documented
                    □ API/library reference is complete

                    Configuration:
                    □ Dependency manifest created with pinned versions
                    □ .env.example includes all required variables
                    □ .gitignore excludes appropriate files
                    □ Configuration templates are complete
                    □ Build/deployment configs are present

                    Testing:
                    □ Code is testable (proper separation of concerns)
                    □ Test configuration files present (if tests included)
                    □ Examples demonstrate main features

                    Validation:
                    □ All files pass syntax validation
                    □ Imports are correct and available
                    □ Dependencies are installable
                    □ Build process completes successfully
                    □ No linter errors or warnings

                    ═══════════════════════════════════════════════════════════════════════════════
                    OUTPUT REQUIREMENTS:
                    ═══════════════════════════════════════════════════════════════════════════════

                    Generate actual, working code that:
                    1. Solves the problem described in the technical plan
                    2. Runs successfully without modifications
                    3. Handles errors gracefully
                    4. Is secure and follows best practices
                    5. Is well-documented and maintainable
                    6. Can be deployed to production
                    7. Works across platforms (when applicable)
                    8. Follows language/framework conventions
                    9. Includes all necessary configuration
                    10. Provides clear examples and documentation

                    The project should be immediately usable by another developer who:
                    - Can read the README and understand what it does
                    - Can follow installation steps and get it running
                    - Can read the code and understand how it works
                    - Can extend and modify it easily
                    - Can deploy it to production with confidence

                    ═══════════════════════════════════════════════════════════════════════════════
                    BEGIN IMPLEMENTATION NOW - CREATE PRODUCTION-READY CODE!
                    ═══════════════════════════════════════════════════════════════════════════════
                    """
    return Task(
        description=dev_description,
        agent=agent,
        context=context_tasks,
        expected_output="""A complete, working project with:
                            - All source code files implemented
                            - README.md with comprehensive documentation
                            - requirements.txt with dependencies
                            - Proper project structure
                            - Example usage files
                            - All code validated and functional"""
    )