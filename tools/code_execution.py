import subprocess
import sys
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from crewai.tools import tool


# Language configuration mapping
LANGUAGE_CONFIG = {
    'python': {
        'extensions': ['.py'],
        'run_command': lambda file: [sys.executable, file],
        'syntax_check': lambda file: [sys.executable, '-m', 'py_compile', file],
        'dependency_install': lambda file: [sys.executable, '-m', 'pip', 'install', '-r', file],
        'test_command': lambda: ['pytest', '-v'],
        'format_command': lambda files: ['black'] + files,
        'lint_command': lambda files: ['flake8'] + files,
        'type_check': lambda: ['mypy', '.']
    },
    'javascript': {
        'extensions': ['.js', '.mjs', '.cjs'],
        'run_command': lambda file: ['node', file],
        'syntax_check': lambda file: ['node', '--check', file],
        'dependency_install': lambda file: ['npm', 'install'],
        'test_command': lambda: ['npm', 'test'],
        'format_command': lambda files: ['prettier', '--write'] + files,
        'lint_command': lambda files: ['eslint'] + files,
        'build_command': lambda: ['npm', 'run', 'build']
    },
    'typescript': {
        'extensions': ['.ts', '.tsx'],
        'run_command': lambda file: ['ts-node', file],
        'syntax_check': lambda file: ['tsc', '--noEmit', file],
        'dependency_install': lambda file: ['npm', 'install'],
        'test_command': lambda: ['npm', 'test'],
        'format_command': lambda files: ['prettier', '--write'] + files,
        'lint_command': lambda files: ['eslint'] + files,
        'type_check': lambda: ['tsc', '--noEmit'],
        'build_command': lambda: ['npm', 'run', 'build']
    },
    'html': {
        'extensions': ['.html', '.htm'],
        'run_command': lambda file: ['open', file] if sys.platform == 'darwin' else ['xdg-open', file] if sys.platform == 'linux' else ['start', file],
        'syntax_check': lambda file: ['html5validator', file],
        'format_command': lambda files: ['prettier', '--write'] + files,
        'lint_command': lambda files: ['htmlhint'] + files,
        'build_command': lambda: ['npm', 'run', 'build'] if Path('package.json').exists() else None
    },
    'css': {
        'extensions': ['.css', '.scss', '.sass', '.less'],
        'syntax_check': lambda file: ['stylelint', file],
        'format_command': lambda files: ['prettier', '--write'] + files,
        'lint_command': lambda files: ['stylelint'] + files,
        'build_command': lambda: ['sass', 'styles.scss', 'styles.css'] if Path('styles.scss').exists() else None
    },
    'jsx': {
        'extensions': ['.jsx'],
        'run_command': lambda file: ['node', file],
        'syntax_check': lambda file: ['node', '--check', file],
        'dependency_install': lambda file: ['npm', 'install'],
        'test_command': lambda: ['npm', 'test'],
        'format_command': lambda files: ['prettier', '--write'] + files,
        'lint_command': lambda files: ['eslint'] + files,
        'build_command': lambda: ['npm', 'run', 'build']
    },
    'vue': {
        'extensions': ['.vue'],
        'dependency_install': lambda file: ['npm', 'install'],
        'test_command': lambda: ['npm', 'test'],
        'format_command': lambda files: ['prettier', '--write'] + files,
        'lint_command': lambda files: ['eslint'] + files,
        'build_command': lambda: ['npm', 'run', 'build']
    },
    'java': {
        'extensions': ['.java'],
        'run_command': lambda file: ['java', file],
        'syntax_check': lambda file: ['javac', '-Xlint', file],
        'dependency_install': lambda file: ['mvn', 'install'] if Path('pom.xml').exists() else ['gradle', 'build'],
        'test_command': lambda: ['mvn', 'test'] if Path('pom.xml').exists() else ['gradle', 'test'],
        'format_command': lambda files: ['google-java-format', '-i'] + files,
        'lint_command': lambda files: ['checkstyle', '-c', 'checkstyle.xml'] + files,
        'build_command': lambda: ['mvn', 'package'] if Path('pom.xml').exists() else ['gradle', 'build']
    },
    'go': {
        'extensions': ['.go'],
        'run_command': lambda file: ['go', 'run', file],
        'syntax_check': lambda file: ['go', 'vet', file],
        'dependency_install': lambda file: ['go', 'mod', 'download'],
        'test_command': lambda: ['go', 'test', './...', '-v'],
        'format_command': lambda files: ['go', 'fmt'] + files,
        'lint_command': lambda files: ['golangci-lint', 'run'],
        'build_command': lambda: ['go', 'build', '-v', './...']
    },
    'rust': {
        'extensions': ['.rs'],
        'run_command': lambda file: ['cargo', 'run'],
        'syntax_check': lambda file: ['cargo', 'check'],
        'dependency_install': lambda file: ['cargo', 'fetch'],
        'test_command': lambda: ['cargo', 'test'],
        'format_command': lambda files: ['cargo', 'fmt'],
        'lint_command': lambda files: ['cargo', 'clippy', '--', '-D', 'warnings'],
        'build_command': lambda: ['cargo', 'build', '--release']
    },
    'csharp': {
        'extensions': ['.cs'],
        'run_command': lambda file: ['dotnet', 'run'],
        'syntax_check': lambda file: ['dotnet', 'build', '--no-incremental'],
        'dependency_install': lambda file: ['dotnet', 'restore'],
        'test_command': lambda: ['dotnet', 'test'],
        'format_command': lambda files: ['dotnet', 'format'],
        'lint_command': lambda files: ['dotnet', 'build', '/p:EnforceCodeStyleInBuild=true'],
        'build_command': lambda: ['dotnet', 'build', '--configuration', 'Release']
    },
    'ruby': {
        'extensions': ['.rb'],
        'run_command': lambda file: ['ruby', file],
        'syntax_check': lambda file: ['ruby', '-c', file],
        'dependency_install': lambda file: ['bundle', 'install'],
        'test_command': lambda: ['rspec'] if Path('spec').exists() else ['rake', 'test'],
        'format_command': lambda files: ['rubocop', '-A'] + files,
        'lint_command': lambda files: ['rubocop'] + files
    },
    'php': {
        'extensions': ['.php'],
        'run_command': lambda file: ['php', file],
        'syntax_check': lambda file: ['php', '-l', file],
        'dependency_install': lambda file: ['composer', 'install'],
        'test_command': lambda: ['./vendor/bin/phpunit'],
        'format_command': lambda files: ['php-cs-fixer', 'fix'] + files,
        'lint_command': lambda files: ['phpcs'] + files
    },
    'swift': {
        'extensions': ['.swift'],
        'run_command': lambda file: ['swift', file],
        'syntax_check': lambda file: ['swiftc', '-parse', file],
        'dependency_install': lambda file: ['swift', 'package', 'resolve'],
        'test_command': lambda: ['swift', 'test'],
        'format_command': lambda files: ['swiftformat'] + files,
        'lint_command': lambda files: ['swiftlint', 'lint'] + files,
        'build_command': lambda: ['swift', 'build']
    },
    'kotlin': {
        'extensions': ['.kt', '.kts'],
        'run_command': lambda file: ['kotlinc', file, '-include-runtime', '-d', 'output.jar'],
        'syntax_check': lambda file: ['kotlinc', file],
        'dependency_install': lambda file: ['gradle', 'build'],
        'test_command': lambda: ['gradle', 'test'],
        'build_command': lambda: ['gradle', 'build']
    },
    'c': {
        'extensions': ['.c', '.h'],
        'run_command': lambda file: ['gcc', file, '-o', 'output', '&&', './output'],
        'syntax_check': lambda file: ['gcc', '-fsyntax-only', file],
        'format_command': lambda files: ['clang-format', '-i'] + files,
        'lint_command': lambda files: ['clang-tidy'] + files,
        'build_command': lambda: ['make'] if Path('Makefile').exists() else ['cmake', '--build', '.']
    },
    'cpp': {
        'extensions': ['.cpp', '.cc', '.cxx', '.hpp', '.hh', '.hxx'],
        'run_command': lambda file: ['g++', file, '-o', 'output', '&&', './output'],
        'syntax_check': lambda file: ['g++', '-fsyntax-only', file],
        'format_command': lambda files: ['clang-format', '-i'] + files,
        'lint_command': lambda files: ['clang-tidy'] + files,
        'build_command': lambda: ['make'] if Path('Makefile').exists() else ['cmake', '--build', '.']
    },
    'r': {
        'extensions': ['.r', '.R'],
        'run_command': lambda file: ['Rscript', file],
        'syntax_check': lambda file: ['Rscript', '-e', f'source("{file}")'],
        'dependency_install': lambda file: ['Rscript', '-e', 'install.packages()'],
        'test_command': lambda: ['Rscript', '-e', 'testthat::test_dir("tests")']
    },
    'scala': {
        'extensions': ['.scala'],
        'run_command': lambda file: ['scala', file],
        'syntax_check': lambda file: ['scalac', file],
        'dependency_install': lambda file: ['sbt', 'update'],
        'test_command': lambda: ['sbt', 'test'],
        'build_command': lambda: ['sbt', 'compile']
    },
    'dart': {
        'extensions': ['.dart'],
        'run_command': lambda file: ['dart', 'run', file],
        'syntax_check': lambda file: ['dart', 'analyze', file],
        'dependency_install': lambda file: ['dart', 'pub', 'get'],
        'test_command': lambda: ['dart', 'test'],
        'format_command': lambda files: ['dart', 'format'] + files,
        'build_command': lambda: ['dart', 'compile', 'exe', 'bin/main.dart']
    },
    'shell': {
        'extensions': ['.sh', '.bash', '.zsh'],
        'run_command': lambda file: ['bash', file],
        'syntax_check': lambda file: ['bash', '-n', file],
        'lint_command': lambda files: ['shellcheck'] + files
    },
    'sql': {
        'extensions': ['.sql'],
        'syntax_check': lambda file: ['sqlfluff', 'lint', file],
        'format_command': lambda files: ['sqlfluff', 'fix'] + files,
        'lint_command': lambda files: ['sqlfluff', 'lint'] + files
    },
    'json': {
        'extensions': ['.json'],
        'syntax_check': lambda file: ['python', '-m', 'json.tool', file],
        'format_command': lambda files: ['prettier', '--write'] + files
    },
    'yaml': {
        'extensions': ['.yaml', '.yml'],
        'syntax_check': lambda file: ['yamllint', file],
        'format_command': lambda files: ['prettier', '--write'] + files,
        'lint_command': lambda files: ['yamllint'] + files
    },
    'xml': {
        'extensions': ['.xml'],
        'syntax_check': lambda file: ['xmllint', '--noout', file],
        'format_command': lambda files: ['xmllint', '--format'] + files
    },
    'markdown': {
        'extensions': ['.md', '.markdown'],
        'format_command': lambda files: ['prettier', '--write'] + files,
        'lint_command': lambda files: ['markdownlint'] + files
    },
    'lua': {
        'extensions': ['.lua'],
        'run_command': lambda file: ['lua', file],
        'syntax_check': lambda file: ['luac', '-p', file],
        'lint_command': lambda files: ['luacheck'] + files
    },
    'perl': {
        'extensions': ['.pl', '.pm'],
        'run_command': lambda file: ['perl', file],
        'syntax_check': lambda file: ['perl', '-c', file],
        'lint_command': lambda files: ['perlcritic'] + files
    },
    'haskell': {
        'extensions': ['.hs'],
        'run_command': lambda file: ['runhaskell', file],
        'syntax_check': lambda file: ['ghc', '-fno-code', file],
        'test_command': lambda: ['stack', 'test'],
        'build_command': lambda: ['stack', 'build']
    },
    'elixir': {
        'extensions': ['.ex', '.exs'],
        'run_command': lambda file: ['elixir', file],
        'syntax_check': lambda file: ['elixir', '-c', file],
        'dependency_install': lambda file: ['mix', 'deps.get'],
        'test_command': lambda: ['mix', 'test'],
        'format_command': lambda files: ['mix', 'format'] + files
    }
}


def detect_language(file_path: str) -> Optional[str]:
    """Detect programming language from file extension"""
    ext = Path(file_path).suffix.lower()
    for lang, config in LANGUAGE_CONFIG.items():
        if ext in config['extensions']:
            return lang
    return None


def check_tool_available(command: str) -> bool:
    """Check if a command-line tool is available"""
    return shutil.which(command) is not None


@tool("Execute code file")
def execute_code(file_path: str, args: str = "", timeout: int = 30) -> str:
    """
    Executes code from any supported programming language file.
    
    Supports: Python, JavaScript, TypeScript, Java, Go, Rust, C#, Ruby, PHP, Swift, Kotlin
    
    Args:
        file_path: Path to the code file
        args: Additional command-line arguments
        timeout: Execution timeout in seconds (default: 30)
    
    Returns:
        Execution output including stdout, stderr, and return code
    """
    try:
        # Check if file exists
        if not Path(file_path).exists():
            return f"✗ Error: File not found: {file_path}"
        
        # Detect language
        language = detect_language(file_path)
        if not language:
            return f"✗ Error: Unsupported file type: {Path(file_path).suffix}"
        
        # Get language configuration
        config = LANGUAGE_CONFIG[language]
        
        # Build command
        command = config['run_command'](file_path)
        if args:
            command.extend(args.split())
        
        # Check if required tool is available
        if not check_tool_available(command[0]):
            return f"✗ Error: {command[0]} is not installed or not in PATH"
        
        # Execute
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=Path(file_path).parent
        )
        
        output = f"Language: {language.capitalize()}\n"
        output += f"File: {file_path}\n"
        output += f"Command: {' '.join(command)}\n"
        output += "─" * 60 + "\n"
        
        if result.stdout:
            output += f"STDOUT:\n{result.stdout}\n"
        if result.stderr:
            output += f"STDERR:\n{result.stderr}\n"
        
        output += f"─" * 60 + "\n"
        output += f"Return Code: {result.returncode}\n"
        
        if result.returncode == 0:
            output += "✓ Execution completed successfully"
        else:
            output += "✗ Execution failed"
        
        return output
        
    except subprocess.TimeoutExpired:
        return f"✗ Execution timed out after {timeout} seconds"
    except Exception as e:
        return f"✗ Error executing code: {str(e)}"


@tool("Validate code syntax")
def validate_syntax(file_path: str) -> str:
    """
    Validates code syntax without executing for any supported language.
    
    Supports: Python, JavaScript, TypeScript, Java, Go, Rust, C#, Ruby, PHP, Swift, Kotlin
    
    Args:
        file_path: Path to the code file
    
    Returns:
        Validation result with any syntax errors found
    """
    try:
        # Check if file exists
        if not Path(file_path).exists():
            return f"✗ Error: File not found: {file_path}"
        
        # Detect language
        language = detect_language(file_path)
        if not language:
            return f"✗ Error: Unsupported file type: {Path(file_path).suffix}"
        
        # Get language configuration
        config = LANGUAGE_CONFIG[language]
        
        # Special handling for Python (can use built-in compile)
        if language == 'python':
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    code = f.read()
                compile(code, file_path, 'exec')
                return f"✓ {language.capitalize()} syntax is valid: {file_path}"
            except SyntaxError as e:
                return f"✗ Syntax Error in {file_path}:\nLine {e.lineno}: {e.msg}\n{e.text}"
        
        # For other languages, use their syntax checking tools
        if 'syntax_check' not in config:
            return f"⚠ Syntax checking not available for {language}"
        
        command = config['syntax_check'](file_path)
        
        # Check if required tool is available
        if not check_tool_available(command[0]):
            return f"⚠ {command[0]} is not installed. Cannot validate syntax."
        
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=Path(file_path).parent
        )
        
        if result.returncode == 0:
            return f"✓ {language.capitalize()} syntax is valid: {file_path}"
        else:
            output = f"✗ Syntax errors found in {file_path}:\n"
            output += result.stderr if result.stderr else result.stdout
            return output
            
    except Exception as e:
        return f"✗ Error validating syntax: {str(e)}"


@tool("Install project dependencies")
def install_dependencies(project_dir: str = ".", language: str = None) -> str:
    """
    Installs dependencies for any supported language/framework.
    
    Auto-detects package manager from project files:
    - Python: requirements.txt, setup.py, pyproject.toml
    - JavaScript/TypeScript: package.json
    - Java: pom.xml (Maven), build.gradle (Gradle)
    - Go: go.mod
    - Rust: Cargo.toml
    - C#: .csproj, .sln
    - Ruby: Gemfile
    - PHP: composer.json
    - Swift: Package.swift
    
    Args:
        project_dir: Project directory path (default: current directory)
        language: Force specific language (optional, auto-detected if not provided)
    
    Returns:
        Installation result message
    """
    try:
        project_path = Path(project_dir)
        
        # Auto-detect language if not specified
        if not language:
            if (project_path / 'requirements.txt').exists() or (project_path / 'setup.py').exists():
                language = 'python'
            elif (project_path / 'package.json').exists():
                # Check if TypeScript
                language = 'typescript' if (project_path / 'tsconfig.json').exists() else 'javascript'
            elif (project_path / 'pom.xml').exists() or (project_path / 'build.gradle').exists():
                language = 'java'
            elif (project_path / 'go.mod').exists():
                language = 'go'
            elif (project_path / 'Cargo.toml').exists():
                language = 'rust'
            elif list(project_path.glob('*.csproj')) or list(project_path.glob('*.sln')):
                language = 'csharp'
            elif (project_path / 'Gemfile').exists():
                language = 'ruby'
            elif (project_path / 'composer.json').exists():
                language = 'php'
            elif (project_path / 'Package.swift').exists():
                language = 'swift'
            else:
                return "✗ Error: Could not detect project language. Please specify language parameter."
        
        # Get language configuration
        if language not in LANGUAGE_CONFIG:
            return f"✗ Error: Unsupported language: {language}"
        
        config = LANGUAGE_CONFIG[language]
        
        # Build installation command
        if language == 'python':
            if (project_path / 'requirements.txt').exists():
                command = config['dependency_install']('requirements.txt')
            elif (project_path / 'pyproject.toml').exists():
                command = ['pip', 'install', '-e', '.']
            else:
                return "✗ Error: No requirements.txt or pyproject.toml found"
        else:
            command = config['dependency_install'](None)
        
        # Check if required tool is available
        if not check_tool_available(command[0]):
            return f"✗ Error: {command[0]} is not installed or not in PATH"
        
        # Execute installation
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=300,
            cwd=project_path
        )
        
        output = f"Language: {language.capitalize()}\n"
        output += f"Command: {' '.join(command)}\n"
        output += "─" * 60 + "\n"
        
        if result.returncode == 0:
            output += "✓ Successfully installed dependencies\n"
            if result.stdout:
                # Show last few lines of output
                lines = result.stdout.strip().split('\n')
                output += '\n'.join(lines[-10:]) if len(lines) > 10 else result.stdout
        else:
            output += "✗ Error installing dependencies:\n"
            output += result.stderr if result.stderr else result.stdout
        
        return output
        
    except subprocess.TimeoutExpired:
        return "✗ Installation timed out after 300 seconds"
    except Exception as e:
        return f"✗ Error installing dependencies: {str(e)}"


@tool("Run project tests")
def run_tests(project_dir: str = ".", language: str = None, verbose: bool = True) -> str:
    """
    Runs tests for any supported language/framework.
    
    Auto-detects test framework and runs appropriate test command:
    - Python: pytest, unittest
    - JavaScript/TypeScript: Jest, Mocha, npm test
    - Java: JUnit (Maven/Gradle)
    - Go: go test
    - Rust: cargo test
    - C#: dotnet test
    - Ruby: RSpec, Minitest
    - PHP: PHPUnit
    - Swift: swift test
    
    Args:
        project_dir: Project directory path (default: current directory)
        language: Force specific language (optional, auto-detected)
        verbose: Show verbose output (default: True)
    
    Returns:
        Test execution results
    """
    try:
        project_path = Path(project_dir)
        
        # Auto-detect language if not specified
        if not language:
            language = _detect_project_language(project_path)
            if not language:
                return "✗ Error: Could not detect project language"
        
        # Get language configuration
        if language not in LANGUAGE_CONFIG:
            return f"✗ Error: Unsupported language: {language}"
        
        config = LANGUAGE_CONFIG[language]
        
        if 'test_command' not in config:
            return f"⚠ Testing not configured for {language}"
        
        # Build test command
        command = config['test_command']()
        if verbose and language == 'python':
            command.extend(['-v', '--tb=short'])
        
        # Check if required tool is available
        if not check_tool_available(command[0]):
            return f"⚠ {command[0]} is not installed. Cannot run tests."
        
        # Execute tests
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=project_path
        )
        
        output = f"Language: {language.capitalize()}\n"
        output += f"Command: {' '.join(command)}\n"
        output += "─" * 60 + "\n"
        
        if result.stdout:
            output += result.stdout + "\n"
        if result.stderr:
            output += result.stderr + "\n"
        
        output += "─" * 60 + "\n"
        output += f"Return Code: {result.returncode}\n"
        
        if result.returncode == 0:
            output += "✓ All tests passed"
        else:
            output += "✗ Some tests failed"
        
        return output
        
    except subprocess.TimeoutExpired:
        return "✗ Tests timed out after 120 seconds"
    except Exception as e:
        return f"✗ Error running tests: {str(e)}"


@tool("Format code")
def format_code(file_or_dir: str, language: str = None) -> str:
    """
    Formats code according to language standards.
    
    Formatters by language:
    - Python: Black
    - JavaScript/TypeScript: Prettier
    - Java: google-java-format
    - Go: go fmt
    - Rust: cargo fmt
    - C#: dotnet format
    - Ruby: RuboCop
    - PHP: php-cs-fixer
    - Swift: SwiftFormat
    
    Args:
        file_or_dir: File or directory to format
        language: Force specific language (optional, auto-detected)
    
    Returns:
        Formatting result message
    """
    try:
        path = Path(file_or_dir)
        
        # Detect language
        if not language:
            if path.is_file():
                language = detect_language(str(path))
            else:
                language = _detect_project_language(path)
        
        if not language:
            return "✗ Error: Could not detect language"
        
        # Get language configuration
        if language not in LANGUAGE_CONFIG:
            return f"✗ Error: Unsupported language: {language}"
        
        config = LANGUAGE_CONFIG[language]
        
        if 'format_command' not in config:
            return f"⚠ Code formatting not configured for {language}"
        
        # Build format command
        if path.is_file():
            command = config['format_command']([str(path)])
        else:
            command = config['format_command'](['.'])
        
        # Check if required tool is available
        if not check_tool_available(command[0]):
            return f"⚠ {command[0]} is not installed. Install it to format code."
        
        # Execute formatting
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=path if path.is_dir() else path.parent
        )
        
        if result.returncode == 0:
            return f"✓ Successfully formatted {language} code: {file_or_dir}"
        else:
            return f"✗ Error formatting code:\n{result.stderr if result.stderr else result.stdout}"
            
    except Exception as e:
        return f"✗ Error formatting code: {str(e)}"


@tool("Lint code")
def lint_code(file_or_dir: str, language: str = None) -> str:
    """
    Lints code and reports style/quality issues.
    
    Linters by language:
    - Python: Flake8, Pylint
    - JavaScript/TypeScript: ESLint
    - Java: Checkstyle
    - Go: golangci-lint
    - Rust: cargo clippy
    - C#: Roslyn analyzers
    - Ruby: RuboCop
    - PHP: PHPCS
    - Swift: SwiftLint
    
    Args:
        file_or_dir: File or directory to lint
        language: Force specific language (optional, auto-detected)
    
    Returns:
        Linting result with issues found
    """
    try:
        path = Path(file_or_dir)
        
        # Detect language
        if not language:
            if path.is_file():
                language = detect_language(str(path))
            else:
                language = _detect_project_language(path)
        
        if not language:
            return "✗ Error: Could not detect language"
        
        # Get language configuration
        if language not in LANGUAGE_CONFIG:
            return f"✗ Error: Unsupported language: {language}"
        
        config = LANGUAGE_CONFIG[language]
        
        if 'lint_command' not in config:
            return f"⚠ Code linting not configured for {language}"
        
        # Build lint command
        if path.is_file():
            command = config['lint_command']([str(path)])
        else:
            command = config['lint_command'](['.'])
        
        # Check if required tool is available
        if not check_tool_available(command[0]):
            return f"⚠ {command[0]} is not installed. Install it to lint code."
        
        # Execute linting
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=path if path.is_dir() else path.parent
        )
        
        output = f"Language: {language.capitalize()}\n"
        output += f"Command: {' '.join(command)}\n"
        output += "─" * 60 + "\n"
        
        if result.stdout:
            output += result.stdout + "\n"
        if result.stderr:
            output += result.stderr + "\n"
        
        if result.returncode == 0:
            output += "✓ No linting issues found"
        else:
            output += "⚠ Linting issues found (see above)"
        
        return output
        
    except Exception as e:
        return f"✗ Error linting code: {str(e)}"


@tool("Build project")
def build_project(project_dir: str = ".", language: str = None, release: bool = False) -> str:
    """
    Builds/compiles the project for languages that require compilation.
    
    Supports: TypeScript, Java, Go, Rust, C#, Swift, Kotlin
    
    Args:
        project_dir: Project directory path (default: current directory)
        language: Force specific language (optional, auto-detected)
        release: Build in release/production mode (default: False)
    
    Returns:
        Build result message
    """
    try:
        project_path = Path(project_dir)
        
        # Auto-detect language if not specified
        if not language:
            language = _detect_project_language(project_path)
            if not language:
                return "✗ Error: Could not detect project language"
        
        # Get language configuration
        if language not in LANGUAGE_CONFIG:
            return f"✗ Error: Unsupported language: {language}"
        
        config = LANGUAGE_CONFIG[language]
        
        if 'build_command' not in config:
            return f"⚠ Building not required for {language}"
        
        # Build command
        command = config['build_command']()
        
        # Add release flag for Rust
        if language == 'rust' and release:
            # Already included in config
            pass
        elif language == 'csharp' and release:
            # Already included in config
            pass
        
        # Check if required tool is available
        if not check_tool_available(command[0]):
            return f"✗ Error: {command[0]} is not installed or not in PATH"
        
        # Execute build
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=300,
            cwd=project_path
        )
        
        output = f"Language: {language.capitalize()}\n"
        output += f"Command: {' '.join(command)}\n"
        output += "─" * 60 + "\n"
        
        if result.stdout:
            # Show last portion of build output
            lines = result.stdout.strip().split('\n')
            output += '\n'.join(lines[-20:]) if len(lines) > 20 else result.stdout
            output += "\n"
        
        if result.stderr:
            output += result.stderr + "\n"
        
        output += "─" * 60 + "\n"
        
        if result.returncode == 0:
            output += "✓ Build completed successfully"
        else:
            output += "✗ Build failed"
        
        return output
        
    except subprocess.TimeoutExpired:
        return "✗ Build timed out after 300 seconds"
    except Exception as e:
        return f"✗ Error building project: {str(e)}"


@tool("Execute shell command")
def execute_command(command: str, working_dir: str = ".", timeout: int = 60) -> str:
    """
    Executes arbitrary shell commands in the project directory.
    
    Use with caution. Prefer specific tools (execute_code, run_tests, etc.) when available.
    
    Args:
        command: Shell command to execute
        working_dir: Working directory (default: current directory)
        timeout: Command timeout in seconds (default: 60)
    
    Returns:
        Command output including stdout, stderr, and return code
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=working_dir
        )
        
        output = f"Command: {command}\n"
        output += f"Working Directory: {working_dir}\n"
        output += "─" * 60 + "\n"
        
        if result.stdout:
            output += f"STDOUT:\n{result.stdout}\n"
        if result.stderr:
            output += f"STDERR:\n{result.stderr}\n"
        
        output += "─" * 60 + "\n"
        output += f"Return Code: {result.returncode}\n"
        
        if result.returncode == 0:
            output += "✓ Command completed successfully"
        else:
            output += "✗ Command failed"
        
        return output
        
    except subprocess.TimeoutExpired:
        return f"✗ Command timed out after {timeout} seconds"
    except Exception as e:
        return f"✗ Error executing command: {str(e)}"


# Helper function
def _detect_project_language(project_path: Path) -> Optional[str]:
    """Helper function to detect project language from directory structure"""
    if (project_path / 'requirements.txt').exists() or (project_path / 'setup.py').exists():
        return 'python'
    elif (project_path / 'package.json').exists():
        return 'typescript' if (project_path / 'tsconfig.json').exists() else 'javascript'
    elif (project_path / 'pom.xml').exists() or (project_path / 'build.gradle').exists():
        return 'java'
    elif (project_path / 'go.mod').exists():
        return 'go'
    elif (project_path / 'Cargo.toml').exists():
        return 'rust'
    elif list(project_path.glob('*.csproj')) or list(project_path.glob('*.sln')):
        return 'csharp'
    elif (project_path / 'Gemfile').exists():
        return 'ruby'
    elif (project_path / 'composer.json').exists():
        return 'php'
    elif (project_path / 'Package.swift').exists():
        return 'swift'
    return None