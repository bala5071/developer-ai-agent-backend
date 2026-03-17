import subprocess
import sys
import shutil
import re
from pathlib import Path
from typing import Dict, Optional
from crewai.tools import tool


# Testing framework configuration by language
TEST_FRAMEWORKS = {
    'python': {
        'frameworks': ['pytest', 'unittest', 'nose2'],
        'test_patterns': ['test_*.py', '*_test.py'],
        'test_dirs': ['tests', 'test'],
        'commands': {
            'pytest': ['pytest', '-v', '--tb=short'],
            'unittest': [sys.executable, '-m', 'unittest', 'discover', '-v'],
            'nose2': ['nose2', '-v']
        },
        'coverage': ['pytest', '--cov=.', '--cov-report=html', '--cov-report=term']
    },
    'javascript': {
        'frameworks': ['jest', 'mocha', 'ava', 'tape'],
        'test_patterns': ['*.test.js', '*.spec.js'],
        'test_dirs': ['tests', 'test', '__tests__'],
        'commands': {
            'jest': ['npm', 'test', '--', '--verbose'],
            'mocha': ['mocha', '--reporter', 'spec'],
            'ava': ['ava', '--verbose'],
            'npm': ['npm', 'test']
        },
        'coverage': ['npm', 'test', '--', '--coverage']
    },
    'typescript': {
        'frameworks': ['jest', 'mocha', 'vitest'],
        'test_patterns': ['*.test.ts', '*.spec.ts'],
        'test_dirs': ['tests', 'test', '__tests__'],
        'commands': {
            'jest': ['npm', 'test', '--', '--verbose'],
            'mocha': ['mocha', '--require', 'ts-node/register', '**/*.test.ts'],
            'vitest': ['vitest', '--run'],
            'npm': ['npm', 'test']
        },
        'coverage': ['npm', 'test', '--', '--coverage']
    },
    'java': {
        'frameworks': ['junit', 'testng'],
        'test_patterns': ['*Test.java', 'Test*.java'],
        'test_dirs': ['src/test/java', 'test'],
        'commands': {
            'maven': ['mvn', 'test'],
            'gradle': ['gradle', 'test', '--info']
        },
        'coverage': ['mvn', 'test', 'jacoco:report']
    },
    'go': {
        'frameworks': ['testing'],
        'test_patterns': ['*_test.go'],
        'test_dirs': ['.'],
        'commands': {
            'go': ['go', 'test', '-v', './...']
        },
        'coverage': ['go', 'test', '-v', '-coverprofile=coverage.out', './...']
    },
    'rust': {
        'frameworks': ['cargo'],
        'test_patterns': ['tests/*.rs'],
        'test_dirs': ['tests', 'src'],
        'commands': {
            'cargo': ['cargo', 'test', '--verbose']
        },
        'coverage': ['cargo', 'tarpaulin', '--out', 'Html']
    },
    'csharp': {
        'frameworks': ['xunit', 'nunit', 'mstest'],
        'test_patterns': ['*Tests.cs', '*Test.cs'],
        'test_dirs': ['Tests', 'Test'],
        'commands': {
            'dotnet': ['dotnet', 'test', '--verbosity', 'normal']
        },
        'coverage': ['dotnet', 'test', '--collect:"XPlat Code Coverage"']
    },
    'ruby': {
        'frameworks': ['rspec', 'minitest'],
        'test_patterns': ['*_spec.rb', '*_test.rb'],
        'test_dirs': ['spec', 'test'],
        'commands': {
            'rspec': ['rspec', '--format', 'documentation'],
            'minitest': ['ruby', '-Itest', '-e', 'Dir["test/**/*_test.rb"].each {|f| require f}']
        },
        'coverage': ['rspec', '--require', 'simplecov']
    },
    'php': {
        'frameworks': ['phpunit'],
        'test_patterns': ['*Test.php'],
        'test_dirs': ['tests', 'Tests'],
        'commands': {
            'phpunit': ['./vendor/bin/phpunit', '--verbose']
        },
        'coverage': ['./vendor/bin/phpunit', '--coverage-html', 'coverage']
    },
    'swift': {
        'frameworks': ['xctest'],
        'test_patterns': ['*Tests.swift'],
        'test_dirs': ['Tests'],
        'commands': {
            'swift': ['swift', 'test', '--verbose']
        },
        'coverage': ['swift', 'test', '--enable-code-coverage']
    }
}


def detect_test_framework(project_dir: str, language: str) -> Optional[str]:
    """Detect which test framework is being used"""
    path = Path(project_dir)
    
    if language == 'python':
        if (path / 'pytest.ini').exists() or (path / 'pyproject.toml').exists():
            return 'pytest'
        elif any(path.rglob('test_*.py')):
            return 'pytest'
        else:
            return 'unittest'
    
    elif language in ['javascript', 'typescript']:
        if (path / 'package.json').exists():
            try:
                import json
                with open(path / 'package.json', 'r') as f:
                    pkg = json.load(f)
                    deps = {**pkg.get('dependencies', {}), **pkg.get('devDependencies', {})}
                    if 'jest' in deps:
                        return 'jest'
                    elif 'mocha' in deps:
                        return 'mocha'
                    elif 'vitest' in deps:
                        return 'vitest'
            except:
                pass
        return 'npm'
    
    elif language == 'java':
        if (path / 'pom.xml').exists():
            return 'maven'
        elif (path / 'build.gradle').exists() or (path / 'build.gradle.kts').exists():
            return 'gradle'
    
    elif language == 'go':
        return 'go'
    
    elif language == 'rust':
        return 'cargo'
    
    elif language == 'csharp':
        return 'dotnet'
    
    elif language == 'ruby':
        if (path / 'spec').exists():
            return 'rspec'
        else:
            return 'minitest'
    
    elif language == 'php':
        return 'phpunit'
    
    elif language == 'swift':
        return 'swift'
    
    return None


def detect_project_language(project_dir: str) -> Optional[str]:
    """Detect programming language from project structure"""
    path = Path(project_dir)
    
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
    
    return None


@tool("Run tests")
def run_tests(directory: str = ".", language: str = None, framework: str = None,
              pattern: str = None, verbose: bool = True, timeout: int = 300) -> str:
    """
    Runs tests for any programming language with auto-detection.
    
    Supported languages and frameworks:
    - Python: pytest, unittest, nose2
    - JavaScript/TypeScript: Jest, Mocha, Vitest, npm test
    - Java: JUnit (Maven/Gradle)
    - Go: go test
    - Rust: cargo test
    - C#: xUnit, NUnit, MSTest (dotnet test)
    - Ruby: RSpec, Minitest
    - PHP: PHPUnit
    - Swift: XCTest
    
    Args:
        directory: Project directory (default: current directory)
        language: Force specific language (auto-detected if not provided)
        framework: Force specific framework (auto-detected if not provided)
        pattern: Test file pattern (uses language defaults if not provided)
        verbose: Verbose output (default: True)
        timeout: Test timeout in seconds (default: 300)
    
    Returns:
        Test results with pass/fail status and details
    """
    try:
        path = Path(directory)
        
        # Detect language
        if not language:
            language = detect_project_language(directory)
            if not language:
                return "✗ Error: Could not detect project language. Please specify language parameter."
        
        if language not in TEST_FRAMEWORKS:
            return f"✗ Error: Testing not supported for {language}"
        
        # Detect framework
        if not framework:
            framework = detect_test_framework(directory, language)
            if not framework:
                framework = list(TEST_FRAMEWORKS[language]['commands'].keys())[0]
        
        # Get test command
        config = TEST_FRAMEWORKS[language]
        if framework not in config['commands']:
            return f"✗ Error: Unknown framework '{framework}' for {language}"
        
        command = config['commands'][framework].copy()
        
        # Add pattern if specified
        if pattern:
            command.append(pattern)
        
        # Check if test tool is available
        if not shutil.which(command[0]):
            return f"✗ Error: {command[0]} is not installed or not in PATH.\n" \
                   f"Install it first to run tests."
        
        # Run tests
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=directory
        )
        
        # Format output
        output = f"Test Results - {language.capitalize()} ({framework})\n"
        output += "═" * 70 + "\n"
        output += f"Command: {' '.join(command)}\n"
        output += f"Directory: {directory}\n"
        output += "─" * 70 + "\n\n"
        
        if result.stdout:
            output += result.stdout + "\n"
        
        if result.stderr and verbose:
            output += "\nStderr:\n"
            output += result.stderr + "\n"
        
        output += "\n" + "═" * 70 + "\n"
        
        # Parse test results
        if result.returncode == 0:
            output += "✓ All tests passed!\n"
        else:
            output += "✗ Some tests failed\n"
        
        # Extract test statistics if available
        stats = extract_test_stats(result.stdout + result.stderr, language, framework)
        if stats:
            output += f"\nTest Statistics:\n"
            output += f"  Total: {stats.get('total', 'N/A')}\n"
            output += f"  Passed: {stats.get('passed', 'N/A')}\n"
            output += f"  Failed: {stats.get('failed', 'N/A')}\n"
            if 'skipped' in stats:
                output += f"  Skipped: {stats.get('skipped')}\n"
            if 'duration' in stats:
                output += f"  Duration: {stats.get('duration')}\n"
        
        return output
        
    except subprocess.TimeoutExpired:
        return f"✗ Tests timed out after {timeout} seconds"
    except Exception as e:
        return f"✗ Error running tests: {str(e)}"


@tool("Run tests with coverage")
def run_tests_with_coverage(directory: str = ".", language: str = None,
                            coverage_threshold: float = 80.0) -> str:
    """
    Runs tests with code coverage analysis.
    
    Generates coverage reports for:
    - Python: pytest-cov, coverage.py
    - JavaScript/TypeScript: Jest, nyc, c8
    - Java: JaCoCo
    - Go: go test -cover
    - Rust: tarpaulin
    - C#: coverlet
    - Ruby: SimpleCov
    
    Args:
        directory: Project directory (default: current directory)
        language: Force specific language (auto-detected if not provided)
        coverage_threshold: Minimum coverage percentage (default: 80%)
    
    Returns:
        Test results with coverage report
    """
    try:
        # Detect language
        if not language:
            language = detect_project_language(directory)
            if not language:
                return "✗ Error: Could not detect project language"
        
        if language not in TEST_FRAMEWORKS:
            return f"✗ Error: Coverage not supported for {language}"
        
        config = TEST_FRAMEWORKS[language]
        command = config.get('coverage')
        
        if not command:
            return f"⚠ Coverage reporting not configured for {language}"
        
        # Check if coverage tool is available
        if not shutil.which(command[0]):
            return f"✗ Error: {command[0]} is not installed.\n" \
                   f"Install coverage tools first."
        
        # Run tests with coverage
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=300,
            cwd=directory
        )
        
        output = f"Coverage Report - {language.capitalize()}\n"
        output += "═" * 70 + "\n"
        output += f"Command: {' '.join(command)}\n"
        output += "─" * 70 + "\n\n"
        
        if result.stdout:
            output += result.stdout + "\n"
        
        if result.stderr:
            output += "\nAdditional Info:\n"
            output += result.stderr + "\n"
        
        # Extract coverage percentage
        coverage_pct = extract_coverage_percentage(result.stdout + result.stderr, language)
        
        if coverage_pct is not None:
            output += "\n" + "═" * 70 + "\n"
            output += f"Coverage: {coverage_pct:.2f}%\n"
            output += f"Threshold: {coverage_threshold}%\n"
            
            if coverage_pct >= coverage_threshold:
                output += f"✓ Coverage meets threshold ({coverage_pct:.2f}% >= {coverage_threshold}%)\n"
            else:
                output += f"✗ Coverage below threshold ({coverage_pct:.2f}% < {coverage_threshold}%)\n"
        
        # Check for coverage report files
        coverage_files = {
            'python': ['htmlcov/index.html', 'coverage.xml', '.coverage'],
            'javascript': ['coverage/index.html', 'coverage/lcov.info'],
            'typescript': ['coverage/index.html', 'coverage/lcov.info'],
            'java': ['target/site/jacoco/index.html'],
            'go': ['coverage.out'],
            'rust': ['tarpaulin-report.html'],
            'csharp': ['TestResults/*/coverage.cobertura.xml']
        }
        
        if language in coverage_files:
            found_reports = []
            for pattern in coverage_files[language]:
                matches = list(Path(directory).glob(pattern))
                found_reports.extend(matches)
            
            if found_reports:
                output += f"\nCoverage Reports Generated:\n"
                for report in found_reports:
                    output += f"  📊 {report}\n"
        
        return output
        
    except subprocess.TimeoutExpired:
        return "✗ Coverage analysis timed out after 300 seconds"
    except Exception as e:
        return f"✗ Error running coverage: {str(e)}"


@tool("Format code")
def format_code(directory: str = ".", language: str = None, 
                check_only: bool = False) -> str:
    """
    Formats code according to language style guidelines.
    
    Formatters by language:
    - Python: Black, autopep8
    - JavaScript/TypeScript: Prettier
    - Java: google-java-format
    - Go: gofmt
    - Rust: rustfmt
    - C#: dotnet format
    - Ruby: RuboCop
    - PHP: PHP-CS-Fixer
    - Swift: SwiftFormat
    
    Args:
        directory: Directory to format (default: current directory)
        language: Force specific language (auto-detected if not provided)
        check_only: Only check formatting without applying changes (default: False)
    
    Returns:
        Formatting result message
    """
    try:
        # Detect language
        if not language:
            language = detect_project_language(directory)
            if not language:
                return "✗ Error: Could not detect project language"
        
        # Language-specific format commands
        format_commands = {
            'python': ['black', '--check' if check_only else '', directory],
            'javascript': ['prettier', '--check' if check_only else '--write', '.'],
            'typescript': ['prettier', '--check' if check_only else '--write', '.'],
            'java': ['google-java-format', '-i' if not check_only else '', '-r', directory],
            'go': ['gofmt', '-l' if check_only else '-w', directory],
            'rust': ['cargo', 'fmt', '--check' if check_only else ''],
            'csharp': ['dotnet', 'format', '--verify-no-changes' if check_only else ''],
            'ruby': ['rubocop', '-a' if not check_only else '', directory],
            'php': ['php-cs-fixer', 'fix', '--dry-run' if check_only else '', directory],
            'swift': ['swiftformat', '--lint' if check_only else '', directory]
        }
        
        if language not in format_commands:
            return f"⚠ Code formatting not configured for {language}"
        
        command = [c for c in format_commands[language] if c]  # Remove empty strings
        
        # Check if formatter is available
        if not shutil.which(command[0]):
            return f"✗ Error: {command[0]} is not installed.\n" \
                   f"Install it to format {language} code."
        
        # Run formatter
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=directory
        )
        
        output = f"Code Formatting - {language.capitalize()}\n"
        output += "═" * 70 + "\n"
        output += f"Tool: {command[0]}\n"
        output += f"Mode: {'Check Only' if check_only else 'Format'}\n"
        output += "─" * 70 + "\n\n"
        
        if result.stdout:
            output += result.stdout + "\n"
        
        if result.returncode == 0:
            if check_only:
                output += "✓ Code is properly formatted\n"
            else:
                output += "✓ Code formatted successfully\n"
        else:
            if check_only:
                output += "⚠ Formatting issues found:\n"
                output += result.stderr if result.stderr else result.stdout
            else:
                output += "✗ Formatting errors:\n"
                output += result.stderr if result.stderr else result.stdout
        
        return output
        
    except subprocess.TimeoutExpired:
        return "✗ Formatting timed out after 60 seconds"
    except Exception as e:
        return f"✗ Error formatting code: {str(e)}"


@tool("Lint code")
def lint_code(directory: str = ".", language: str = None, 
              strict: bool = False, fix: bool = False) -> str:
    """
    Lints code for style and quality issues.
    
    Linters by language:
    - Python: flake8, pylint, ruff
    - JavaScript/TypeScript: ESLint
    - Java: Checkstyle, PMD
    - Go: golangci-lint
    - Rust: clippy
    - C#: Roslyn analyzers
    - Ruby: RuboCop
    - PHP: PHPCS
    - Swift: SwiftLint
    
    Args:
        directory: Directory to lint (default: current directory)
        language: Force specific language (auto-detected if not provided)
        strict: Enable strict linting rules (default: False)
        fix: Auto-fix issues where possible (default: False)
    
    Returns:
        Linting results with issues found
    """
    try:
        # Detect language
        if not language:
            language = detect_project_language(directory)
            if not language:
                return "✗ Error: Could not detect project language"
        
        # Language-specific lint commands
        lint_commands = {
            'python': ['flake8', '--max-line-length=120', directory],
            'javascript': ['eslint', '--fix' if fix else '', '.'],
            'typescript': ['eslint', '--fix' if fix else '', '--ext', '.ts,.tsx', '.'],
            'java': ['checkstyle', '-c', 'checkstyle.xml', directory],
            'go': ['golangci-lint', 'run', './...'],
            'rust': ['cargo', 'clippy', '--', '-D', 'warnings' if strict else ''],
            'csharp': ['dotnet', 'build', '/p:EnforceCodeStyleInBuild=true'],
            'ruby': ['rubocop', '-a' if fix else '', directory],
            'php': ['phpcs', directory],
            'swift': ['swiftlint', 'lint', '--strict' if strict else '', directory]
        }
        
        if language not in lint_commands:
            return f"⚠ Code linting not configured for {language}"
        
        command = [c for c in lint_commands[language] if c]
        
        # Check if linter is available
        if not shutil.which(command[0]):
            return f"✗ Error: {command[0]} is not installed.\n" \
                   f"Install it to lint {language} code."
        
        # Run linter
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=directory
        )
        
        output = f"Code Linting - {language.capitalize()}\n"
        output += "═" * 70 + "\n"
        output += f"Tool: {command[0]}\n"
        output += f"Strict Mode: {strict}\n"
        output += f"Auto-fix: {fix}\n"
        output += "─" * 70 + "\n\n"
        
        if result.stdout:
            output += result.stdout + "\n"
        
        if result.stderr:
            output += result.stderr + "\n"
        
        output += "\n" + "═" * 70 + "\n"
        
        if result.returncode == 0:
            output += "✓ No linting issues found\n"
        else:
            issue_count = count_lint_issues(result.stdout + result.stderr, language)
            output += f"⚠ Linting issues found"
            if issue_count:
                output += f": {issue_count} issues"
            output += "\n"
        
        return output
        
    except subprocess.TimeoutExpired:
        return "✗ Linting timed out after 120 seconds"
    except Exception as e:
        return f"✗ Error linting code: {str(e)}"


@tool("Generate test file")
def generate_test_file(file_path: str, module_name: str, language: str = None,
                       framework: str = None, include_examples: bool = True) -> str:
    """
    Creates a test file template for any language.
    
    Args:
        file_path: Path for the test file
        module_name: Name of the module/class being tested
        language: Programming language (auto-detected if not provided)
        framework: Test framework (auto-detected if not provided)
        include_examples: Include example test cases (default: True)
    
    Returns:
        Success message or error
    """
    try:
        # Detect language from file extension if not provided
        if not language:
            ext = Path(file_path).suffix
            language_map = {
                '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
                '.java': 'java', '.go': 'go', '.rs': 'rust', '.cs': 'csharp',
                '.rb': 'ruby', '.php': 'php', '.swift': 'swift'
            }
            language = language_map.get(ext, 'python')
        
        # Detect framework if not provided
        if not framework:
            framework = detect_test_framework(str(Path(file_path).parent), language)
        
        # Generate test template based on language and framework
        templates = {
            ('python', 'pytest'): generate_pytest_template,
            ('python', 'unittest'): generate_unittest_template,
            ('javascript', 'jest'): generate_jest_template,
            ('typescript', 'jest'): generate_jest_typescript_template,
            ('java', 'junit'): generate_junit_template,
            ('go', 'testing'): generate_go_test_template,
            ('rust', 'cargo'): generate_rust_test_template,
            ('csharp', 'xunit'): generate_xunit_template,
            ('ruby', 'rspec'): generate_rspec_template,
            ('php', 'phpunit'): generate_phpunit_template,
            ('swift', 'xctest'): generate_xctest_template
        }
        
        template_func = templates.get((language, framework))
        if not template_func:
            # Use default pytest template
            template_func = generate_pytest_template
        
        content = template_func(module_name, include_examples)
        
        # Create test file
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return f"✓ Test file created: {file_path}\n" \
               f"  Language: {language}\n" \
               f"  Framework: {framework}\n" \
               f"  Examples included: {include_examples}"
        
    except Exception as e:
        return f"✗ Error creating test file: {str(e)}"


# Template generation functions
def generate_pytest_template(module_name: str, include_examples: bool) -> str:
    template = f'''"""Tests for {module_name}"""
import pytest
from {module_name} import *


class Test{module_name.capitalize()}:
    """Test suite for {module_name}"""
    
    @pytest.fixture
    def sample_data(self):
        """Provide sample test data"""
        return {{"key": "value", "number": 42}}
    
'''
    if include_examples:
        template += '''    def test_example_valid_input(self, sample_data):
        """Test with valid input"""
        # Arrange
        expected = "expected_result"
        
        # Act
        result = function_to_test(sample_data)
        
        # Assert
        assert result == expected
    
    def test_example_invalid_input(self):
        """Test with invalid input"""
        with pytest.raises(ValueError):
            function_to_test(None)
    
    @pytest.mark.parametrize("input_val,expected", [
        ("test1", "result1"),
        ("test2", "result2"),
    ])
    def test_example_parameterized(self, input_val, expected):
        """Test with multiple inputs"""
        assert function_to_test(input_val) == expected
'''
    else:
        template += '''    def test_placeholder(self):
        """Add your test cases here"""
        assert True
'''
    
    return template


def generate_junit_template(module_name: str, include_examples: bool) -> str:
    class_name = module_name.capitalize()
    template = f'''/**
 * Tests for {module_name}
 */

import org.junit.jupiter.api.*;
import static org.junit.jupiter.api.Assertions.*;

class {class_name}Test {{
    
    private Object sampleData;
    
    @BeforeEach
    void setUp() {{
        sampleData = new Object();
    }}
    
    @AfterEach
    void tearDown() {{
        // Clean up
    }}
    
'''
    if include_examples:
        template += '''    @Test
    @DisplayName("Should handle valid input")
    void testValidInput() {
        // Arrange
        String expected = "expected";
        
        // Act
        String result = functionToTest(sampleData);
        
        // Assert
        assertEquals(expected, result);
    }
    
    @Test
    @DisplayName("Should throw exception on invalid input")
    void testInvalidInput() {
        assertThrows(IllegalArgumentException.class, () -> {
            functionToTest(null);
        });
    }
    
    @ParameterizedTest
    @CsvSource({
        "input1, expected1",
        "input2, expected2"
    })
    void testParameterized(String input, String expected) {
        assertEquals(expected, functionToTest(input));
    }
'''
    else:
        template += '''    @Test
    void testPlaceholder() {
        assertTrue(true, "Add your test cases here");
    }
'''
    
    template += '}\n'
    return template


def generate_go_test_template(module_name: str, include_examples: bool) -> str:
    template = f'''package {module_name}

import "testing"

'''
    if include_examples:
        template += '''func TestFunctionName(t *testing.T) {
    tests := []struct {
        name     string
        input    string
        expected string
        wantErr  bool
    }{
        {
            name:     "valid input",
            input:    "test",
            expected: "expected",
            wantErr:  false,
        },
        {
            name:     "invalid input",
            input:    "",
            expected: "",
            wantErr:  true,
        },
    }
    
    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            result, err := FunctionName(tt.input)
            
            if (err != nil) != tt.wantErr {
                t.Errorf("FunctionName() error = %v, wantErr %v", err, tt.wantErr)
                return
            }
            
            if result != tt.expected {
                t.Errorf("FunctionName() = %v, want %v", result, tt.expected)
            }
        })
    }
}
'''
    else:
        template += '''func TestPlaceholder(t *testing.T) {
    // Add your test cases here
    if false {
        t.Error("Test not implemented")
    }
}
'''
    
    return template


def generate_rust_test_template(module_name: str, include_examples: bool) -> str:
    template = f'''#[cfg(test)]
mod tests {{
    use super::*;
    
'''
    if include_examples:
        template += '''    #[test]
    fn test_valid_input() {
        let input = "test";
        let result = function_name(input);
        assert_eq!(result, "expected");
    }
    
    #[test]
    #[should_panic(expected = "invalid input")]
    fn test_invalid_input() {
        function_name("");
    }
    
    #[test]
    fn test_error_handling() {
        let result = function_name_result("invalid");
        assert!(result.is_err());
    }
'''
    else:
        template += '''    #[test]
    fn test_placeholder() {
        // Add your test cases here
        assert!(true);
    }
'''
    
    template += '}\n'
    return template


def generate_xunit_template(module_name: str, include_examples: bool) -> str:
    class_name = module_name.capitalize()
    template = f'''using Xunit;

namespace {class_name}.Tests
{{
    public class {class_name}Tests
    {{
        private readonly object _sampleData;
        
        public {class_name}Tests()
        {{
            _sampleData = new object();
        }}
        
'''
    if include_examples:
        template += '''        [Fact]
        public void TestValidInput()
        {
            // Arrange
            var expected = "expected";
            
            // Act
            var result = FunctionToTest(_sampleData);
            
            // Assert
            Assert.Equal(expected, result);
        }
        
        [Fact]
        public void TestInvalidInput()
        {
            // Act & Assert
            Assert.Throws<ArgumentException>(() => FunctionToTest(null));
        }
        
        [Theory]
        [InlineData("input1", "expected1")]
        [InlineData("input2", "expected2")]
        public void TestParameterized(string input, string expected)
        {
            // Act
            var result = FunctionToTest(input);
            
            // Assert
            Assert.Equal(expected, result);
        }
'''
    else:
        template += '''        [Fact]
        public void TestPlaceholder()
        {
            // Add your test cases here
            Assert.True(true);
        }
'''
    
    template += '    }\n}\n'
    return template


def generate_rspec_template(module_name: str, include_examples: bool) -> str:
    template = f'''require 'spec_helper'
require '{module_name}'

RSpec.describe {module_name.capitalize} do
  let(:sample_data) {{ {{ key: 'value' }} }}
  
'''
    if include_examples:
        template += '''  describe '#function_name' do
    context 'with valid input' do
      it 'returns expected result' do
        result = subject.function_name(sample_data)
        expect(result).to eq('expected')
      end
    end
    
    context 'with invalid input' do
      it 'raises an error' do
        expect { subject.function_name(nil) }.to raise_error(ArgumentError)
      end
    end
    
    context 'with various inputs' do
      [
        ['input1', 'expected1'],
        ['input2', 'expected2']
      ].each do |input, expected|
        it "handles #{input} correctly" do
          expect(subject.function_name(input)).to eq(expected)
        end
      end
    end
  end
'''
    else:
        template += '''  it 'placeholder test' do
    # Add your test cases here
    expect(true).to be true
  end
'''
    
    template += 'end\n'
    return template


def generate_phpunit_template(module_name: str, include_examples: bool) -> str:
    class_name = module_name.capitalize()
    template = f'''<?php

use PHPUnit\\Framework\\TestCase;

class {class_name}Test extends TestCase
{{
    private $sampleData;
    
    protected function setUp(): void
    {{
        $this->sampleData = ['key' => 'value'];
    }}
    
    protected function tearDown(): void
    {{
        // Clean up
    }}
    
'''
    if include_examples:
        template += '''    public function testValidInput()
    {
        $result = functionToTest($this->sampleData);
        $this->assertEquals('expected', $result);
    }
    
    public function testInvalidInput()
    {
        $this->expectException(InvalidArgumentException::class);
        functionToTest(null);
    }
    
    /**
     * @dataProvider inputProvider
     */
    public function testParameterized($input, $expected)
    {
        $result = functionToTest($input);
        $this->assertEquals($expected, $result);
    }
    
    public function inputProvider()
    {
        return [
            ['input1', 'expected1'],
            ['input2', 'expected2']
        ];
    }
'''
    else:
        template += '''    public function testPlaceholder()
    {
        // Add your test cases here
        $this->assertTrue(true);
    }
'''
    
    template += '}\n'
    return template


def generate_xctest_template(module_name: str, include_examples: bool) -> str:
    class_name = module_name.capitalize()
    template = f'''import XCTest
@testable import {class_name}

final class {class_name}Tests: XCTestCase {{
    
    var sampleData: [String: Any]!
    
    override func setUp() {{
        super.setUp()
        sampleData = ["key": "value"]
    }}
    
    override func tearDown() {{
        sampleData = nil
        super.tearDown()
    }}
    
'''
    if include_examples:
        template += '''    func testValidInput() {
        // Given
        let expected = "expected"
        
        // When
        let result = functionToTest(sampleData)
        
        // Then
        XCTAssertEqual(result, expected)
    }
    
    func testInvalidInput() {
        // When/Then
        XCTAssertThrowsError(try functionToTest(nil))
    }
    
    func testPerformance() {
        measure {
            _ = functionToTest(sampleData)
        }
    }
'''
    else:
        template += '''    func testPlaceholder() {
        // Add your test cases here
        XCTAssertTrue(true)
    }
'''
    
    template += '}\n'
    return template


# Helper functions for parsing test output
def extract_test_stats(output: str, language: str, framework: str) -> Dict[str, any]:
    """Extract test statistics from test output"""
    stats = {}
    
    if language == 'python' and framework == 'pytest':
        # pytest format: "5 passed, 2 failed in 1.23s"
        passed = re.search(r'(\d+) passed', output)
        failed = re.search(r'(\d+) failed', output)
        skipped = re.search(r'(\d+) skipped', output)
        duration = re.search(r'in ([\d.]+)s', output)
        
        if passed:
            stats['passed'] = int(passed.group(1))
        if failed:
            stats['failed'] = int(failed.group(1))
        if skipped:
            stats['skipped'] = int(skipped.group(1))
        if duration:
            stats['duration'] = f"{duration.group(1)}s"
        
        if 'passed' in stats or 'failed' in stats:
            stats['total'] = stats.get('passed', 0) + stats.get('failed', 0) + stats.get('skipped', 0)
    
    elif language in ['javascript', 'typescript'] and framework == 'jest':
        # Jest format: "Tests: 5 passed, 2 failed, 7 total"
        passed = re.search(r'(\d+) passed', output)
        failed = re.search(r'(\d+) failed', output)
        total = re.search(r'(\d+) total', output)
        duration = re.search(r'Time:\s+([\d.]+)\s*s', output)
        
        if passed:
            stats['passed'] = int(passed.group(1))
        if failed:
            stats['failed'] = int(failed.group(1))
        if total:
            stats['total'] = int(total.group(1))
        if duration:
            stats['duration'] = f"{duration.group(1)}s"
    
    elif language == 'go':
        # Go format: "PASS" or "FAIL"
        passed = len(re.findall(r'--- PASS:', output))
        failed = len(re.findall(r'--- FAIL:', output))
        
        if passed or failed:
            stats['passed'] = passed
            stats['failed'] = failed
            stats['total'] = passed + failed
    
    return stats


def extract_coverage_percentage(output: str, language: str) -> Optional[float]:
    """Extract coverage percentage from coverage output"""
    
    # Common pattern: "TOTAL 1234 567 85%"
    match = re.search(r'TOTAL.*?(\d+)%', output)
    if match:
        return float(match.group(1))
    
    # Python coverage.py: "TOTAL 1234 567 85%"
    match = re.search(r'TOTAL\s+\d+\s+\d+\s+(\d+)%', output)
    if match:
        return float(match.group(1))
    
    # Jest: "Coverage: 85.5%"
    match = re.search(r'Coverage:\s+([\d.]+)%', output)
    if match:
        return float(match.group(1))
    
    # Go: "coverage: 85.5% of statements"
    match = re.search(r'coverage:\s+([\d.]+)%', output)
    if match:
        return float(match.group(1))
    
    # Generic percentage pattern
    match = re.search(r'(\d+\.?\d*)%\s*coverage', output, re.IGNORECASE)
    if match:
        return float(match.group(1))
    
    return None


def count_lint_issues(output: str, language: str) -> Optional[int]:
    """Count linting issues from linter output"""
    
    # Count lines with error/warning patterns
    if language == 'python':
        # Flake8: "file.py:10:1: E501 line too long"
        issues = len(re.findall(r':\d+:\d+:\s+[A-Z]\d+', output))
        return issues if issues > 0 else None
    
    elif language in ['javascript', 'typescript']:
        # ESLint: "✖ 5 problems (3 errors, 2 warnings)"
        match = re.search(r'(\d+)\s+problems?', output)
        if match:
            return int(match.group(1))
    
    elif language == 'go':
        # Count lines that look like errors
        issues = len([line for line in output.split('\n') if '.go:' in line])
        return issues if issues > 0 else None
    
    # Generic: count lines with "error:" or "warning:"
    issues = len(re.findall(r'(error|warning):', output, re.IGNORECASE))
    return issues if issues > 0 else None


def generate_unittest_template(module_name: str, include_examples: bool) -> str:
    template = f'''"""Tests for {module_name}"""
import unittest
from {module_name} import *


class Test{module_name.capitalize()}(unittest.TestCase):
    """Test suite for {module_name}"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.sample_data = {{"key": "value"}}
    
    def tearDown(self):
        """Clean up after tests"""
        pass
    
'''
    if include_examples:
        template += '''    def test_example_valid_input(self):
        """Test with valid input"""
        result = function_to_test(self.sample_data)
        self.assertEqual(result, "expected")
    
    def test_example_invalid_input(self):
        """Test with invalid input"""
        with self.assertRaises(ValueError):
            function_to_test(None)


if __name__ == '__main__':
    unittest.main()
'''
    else:
        template += '''    def test_placeholder(self):
        """Add your test cases here"""
        self.assertTrue(True)


if __name__ == '__main__':
    unittest.main()
'''
    
    return template


def generate_jest_template(module_name: str, include_examples: bool) -> str:
    template = f'''/**
 * Tests for {module_name}
 */

const {{ functionToTest }} = require('./{module_name}');

describe('{module_name}', () => {{
  let sampleData;
  
  beforeEach(() => {{
    sampleData = {{ key: 'value', number: 42 }};
  }});
  
'''
    if include_examples:
        template += '''  test('should handle valid input', () => {
    const result = functionToTest(sampleData);
    expect(result).toBe('expected');
  });
  
  test('should throw error on invalid input', () => {
    expect(() => functionToTest(null)).toThrow();
  });
  
  test.each([
    ['input1', 'expected1'],
    ['input2', 'expected2'],
  ])('should handle %s and return %s', (input, expected) => {
    expect(functionToTest(input)).toBe(expected);
  });
'''
    else:
        template += '''  test('placeholder test', () => {
    expect(true).toBe(true);
  });
'''
    
    template += '});\n'
    return template


def generate_jest_typescript_template(module_name: str, include_examples: bool) -> str:
    return generate_jest_template(module_name, include_examples).replace(
        "const { functionToTest } = require",
        "import { functionToTest } from"
    ).replace("');", ";")