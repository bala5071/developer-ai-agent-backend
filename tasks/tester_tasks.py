from crewai import Task


def create_testing_task(agent, project_dir: str, project_type: str, context_tasks: list = None):
    return Task(
         description=f"""Test, validate, and quality-assure the implemented project:

         PROJECT DIRECTORY: {project_dir}
         PROJECT TYPE: {project_type}
         ══════════════════════════════════════════════════════════════════
         YOUR QUALITY ASSURANCE RESPONSIBILITIES:
         ═══════════════════════════════════════════════════════════════════════════════

         🔍 PHASE 1: COMPREHENSIVE CODE REVIEW
         ───────────────────────────────────────────────────────────────────────────────
         1. Review ALL source code files for quality and correctness:
            
            Syntax & Compilation:
            □ Check for syntax errors using language-specific validators
            □ Verify code compiles/transpiles without errors
            □ Ensure all imports/includes are valid and available
            □ Check for undefined variables or functions
            □ Verify type safety (TypeScript, typed Python, Java, C#, Go, Rust)
            
            Code Structure & Organization:
            □ Verify proper file and directory organization
            □ Check module/package structure follows conventions
            □ Ensure separation of concerns (business logic, data access, UI)
            □ Verify appropriate use of design patterns
            □ Check for proper layering (presentation, business, data)
            
            Logic & Correctness:
            □ Review algorithms for correctness
            □ Check for logical errors and edge cases
            □ Verify mathematical calculations
            □ Review conditional logic (if/else, switch statements)
            □ Check loop conditions and termination
            □ Verify state management and transitions
            □ Review async/concurrent operations for race conditions
            
            Best Practices Compliance:
            □ Verify adherence to language-specific idioms
            □ Check SOLID principles application
            □ Ensure DRY (Don't Repeat Yourself) principle
            □ Verify proper abstraction levels
            □ Check for appropriate use of inheritance vs composition
            □ Review dependency injection usage
            □ Verify proper interface/contract definitions
            
            Code Quality Metrics:
            □ Function/method length (should be < 50-75 lines)
            □ Class size (should be < 300 lines)
            □ Cyclomatic complexity (should be < 10 per function)
            □ Nesting depth (should be < 4 levels)
            □ Code duplication (identify repeated code blocks)
            □ Naming conventions (descriptive, not generic)
            
            Error Handling:
            □ Verify comprehensive error handling throughout
            □ Check appropriate exception types are used
            □ Ensure helpful error messages with context
            □ Verify proper resource cleanup (try/finally, using, defer)
            □ Check for bare except/catch blocks
            □ Verify errors are logged appropriately
            
            Security Review:
            □ Check input validation and sanitization
            □ Verify no hardcoded credentials or secrets
            □ Review SQL queries for injection vulnerabilities
            □ Check XSS prevention in web apps
            □ Verify CSRF protection in web apps
            □ Review authentication and authorization logic
            □ Check for insecure deserialization
            □ Verify secure random number generation
            □ Review cryptographic implementations
            
            Documentation:
            □ Verify all public APIs have documentation
            □ Check docstrings/JSDoc/Javadoc are comprehensive
            □ Ensure complex logic has inline comments
            □ Verify usage examples in documentation
            □ Check README completeness and accuracy
            
            Resource Management:
            □ Verify proper memory management
            □ Check for memory leaks (unreleased resources)
            □ Review file handle management
            □ Check database connection handling
            □ Verify proper thread/goroutine cleanup
            □ Review network connection management

         🧪 PHASE 2: COMPREHENSIVE TEST SUITE CREATION
         ───────────────────────────────────────────────────────────────────────────────
         2. Create thorough test files covering all scenarios:

            A. UNIT TESTS (Test individual functions/methods/classes):
            
            For EACH function/method, create tests for:
            □ Happy path: Valid inputs produce expected outputs
            □ Empty inputs: Empty strings, empty arrays, null/nil/None
            □ Invalid types: Wrong type inputs (string vs number, etc.)
            □ Boundary values: Min, max, zero, negative values
            □ Edge cases: Very large inputs, unicode characters, special chars
            □ Default parameters: Test with and without optional arguments
            □ Exception cases: Invalid inputs raise appropriate errors
            □ State changes: Verify object state after operations (for stateful classes)
            
            For EACH class, create tests for:
            □ Initialization: Valid and invalid constructor parameters
            □ All public methods: Test complete public API
            □ State management: Verify state transitions
            □ Resource cleanup: Test destructors/disposal methods
            □ Thread safety: Test concurrent access (if applicable)
            
            Test Structure by Language:
            
            Python (pytest):
            - tests/test_<module>.py for each module
            - Use fixtures for reusable test data
            - Use @pytest.mark.parametrize for multiple scenarios
            - Use pytest.raises for exception testing
            - Mock external dependencies with unittest.mock
            
            JavaScript/TypeScript (Jest/Mocha/Vitest):
            - __tests__/<module>.test.js/ts for each module
            - Use describe/it blocks for organization
            - Use beforeEach/afterEach for setup/teardown
            - Use jest.mock() for mocking
            - Use test.each() for parameterized tests
            
            Java (JUnit):
            - src/test/java matching package structure
            - Use @Test, @BeforeEach, @AfterEach annotations
            - Use @ParameterizedTest for multiple scenarios
            - Use Mockito for mocking
            - Use AssertJ for fluent assertions
            
            C# (xUnit/NUnit):
            - Separate test project
            - Use [Fact] and [Theory] attributes
            - Use xUnit fixtures or NUnit SetUp/TearDown
            - Use Moq for mocking
            - Use FluentAssertions
            
            Go (testing package):
            - _test.go files alongside source
            - Use table-driven tests
            - Use t.Run() for subtests
            - Use testify/assert for assertions
            - Mock interfaces with generated mocks
            
            Rust (built-in testing):
            - #[cfg(test)] modules in source files
            - tests/ directory for integration tests
            - Use #[test] attribute
            - Use assert!, assert_eq! macros
            - Use mockall for mocking
            
            B. INTEGRATION TESTS (Test component interactions):
            
            □ Module/component interactions
            □ Database operations (with test database)
            □ API endpoint testing (request/response validation)
            □ File I/O operations (with temp files)
            □ External service integrations (with mocks)
            □ Message queue operations
            □ Cache operations
            □ Authentication flows
            □ Multi-step workflows
            
            C. FUNCTIONAL/E2E TESTS (Test complete workflows):
            
            For Web Applications:
            □ User registration and login flows
            □ CRUD operations through UI
            □ Form validation and submission
            □ Navigation and routing
            □ Session management
            □ Browser compatibility (Chrome, Firefox, Safari, Edge)
            □ Responsive design on different screen sizes
            
            For APIs:
            □ All endpoint methods (GET, POST, PUT, DELETE, PATCH)
            □ Request validation (required params, types, formats)
            □ Response codes (200, 201, 400, 401, 403, 404, 500)
            □ Response schemas and data validation
            □ Authentication and authorization
            □ Rate limiting
            □ CORS headers
            
            For CLI Applications:
            □ All commands with valid arguments
            □ Help text and documentation
            □ Error messages for invalid usage
            □ Exit codes
            □ Input/output redirection
            □ Environment variable handling
            
            For Mobile Applications:
            □ Screen navigation flows
            □ Form inputs and validation
            □ Offline functionality
            □ Background/foreground transitions
            □ Push notification handling
            □ Deep linking
            □ Different device sizes and orientations
            
            D. PERFORMANCE TESTS (if applicable):
            
            □ Response time benchmarks
            □ Load testing (concurrent users/requests)
            □ Stress testing (breaking points)
            □ Memory usage profiling
            □ CPU usage monitoring
            □ Database query performance
            □ Large dataset handling
            
            E. SECURITY TESTS (if applicable):
            
            □ SQL injection attempts
            □ XSS attack prevention
            □ CSRF token validation
            □ Authentication bypass attempts
            □ Authorization checks
            □ Rate limiting enforcement
            □ Input validation effectiveness
            □ Session security

         🎯 PHASE 3: TEST EXECUTION & VALIDATION
         ───────────────────────────────────────────────────────────────────────────────
         3. Run comprehensive testing based on technology stack:

            Execute Tests:
            □ Run unit tests: pytest / npm test / mvn test / dotnet test / go test / cargo test
            □ Run integration tests with test databases/services
            □ Run E2E tests (Selenium, Playwright, Cypress, Puppeteer)
            □ Generate coverage reports (aim for 80%+ line coverage)
            □ Check coverage gaps and add missing tests
            
            Test Results:
            □ Verify 100% test pass rate (all tests must pass)
            □ Document any test failures with details
            □ Identify flaky tests (inconsistent results)
            □ Measure test execution time
            □ Check for test pollution (tests affecting each other)
            
            Coverage Analysis:
            □ Line coverage: Percentage of code lines executed
            □ Branch coverage: Percentage of decision branches taken
            □ Function coverage: Percentage of functions called
            □ Identify untested code paths
            □ Prioritize critical path coverage

         ✨ PHASE 4: CODE FORMATTING & STYLE
         ───────────────────────────────────────────────────────────────────────────────
         4. Format and style check code using language-specific tools:

            Python:
            □ Format with Black: black {project_dir}
            □ Sort imports with isort: isort {project_dir}
            □ Check with Flake8: flake8 {project_dir}
            □ Type check with mypy: mypy {project_dir}
            
            JavaScript/TypeScript:
            □ Format with Prettier: prettier --write .
            □ Lint with ESLint: eslint src/
            □ Type check TypeScript: tsc --noEmit
            
            Java:
            □ Format with Google Java Format or Spotless
            □ Check style with Checkstyle
            □ Run SpotBugs for bug detection
            □ Run PMD for code analysis
            
            C#:
            □ Format with dotnet format
            □ Run Roslyn analyzers
            □ Check with StyleCop
            
            Go:
            □ Format with go fmt
            □ Run go vet for correctness
            □ Lint with golangci-lint
            
            Rust:
            □ Format with cargo fmt
            □ Lint with cargo clippy
            
            Style Checks:
            □ Line length compliance
            □ Indentation consistency
            □ Naming conventions
            □ Import organization
            □ Whitespace consistency
            □ Comment formatting

         🚀 PHASE 5: EXECUTION & FUNCTIONAL VERIFICATION
         ───────────────────────────────────────────────────────────────────────────────
         5. Execute and verify the application works correctly:

            Build Process:
            □ Verify build completes without errors
            □ Check for build warnings
            □ Verify all dependencies resolve
            □ Check build artifacts are generated correctly
            
            Execution Tests:
            
            For CLI Applications:
            □ Run with --help flag to verify help text
            □ Execute main commands with sample inputs
            □ Test with valid and invalid arguments
            □ Verify exit codes are appropriate
            □ Check error messages are helpful
            
            For Web Applications:
            □ Start development server successfully
            □ Access home page and verify loading
            □ Navigate through main routes
            □ Test key user interactions
            □ Check browser console for errors
            □ Verify API responses
            
            For APIs/Services:
            □ Start server successfully
            □ Check health/status endpoint
            □ Test main API endpoints with sample data
            □ Verify response formats
            □ Check logging output
            
            For Desktop Applications:
            □ Launch application
            □ Test main window/UI loads correctly
            □ Verify menu items work
            □ Test key features
            
            For Mobile Applications:
            □ Build for target platform (iOS/Android)
            □ Run in simulator/emulator
            □ Test main screens and navigation
            □ Verify no crashes on startup
            
            For Libraries/Packages:
            □ Import/require in test script
            □ Call main public APIs
            □ Verify documented examples work
            □ Check no runtime errors

         🔒 PHASE 6: SECURITY SCAN
         ───────────────────────────────────────────────────────────────────────────────
         6. Perform security analysis:

            Dependency Security:
            □ Scan for known vulnerabilities:
            - Python: safety check / pip-audit
            - JavaScript: npm audit / yarn audit
            - Java: OWASP Dependency-Check
            - C#: dotnet list package --vulnerable
            - Go: nancy or govulncheck
            - Rust: cargo audit
            □ Check for outdated dependencies
            □ Verify no dependencies with critical CVEs
            
            Code Security:
            □ Check for hardcoded secrets (credentials, API keys, tokens)
            □ Verify environment variables are used for sensitive data
            □ Review authentication implementations
            □ Check authorization logic
            □ Verify input validation and sanitization
            □ Review cryptographic usage
            □ Check for insecure random number generation
            □ Verify secure communication (HTTPS/TLS)

         📊 PHASE 7: PERFORMANCE ANALYSIS (if applicable)
         ───────────────────────────────────────────────────────────────────────────────
         7. Analyze performance characteristics:

            □ Profile memory usage
            □ Measure CPU utilization
            □ Check response times
            □ Analyze database query performance
            □ Review algorithm efficiency
            □ Identify bottlenecks
            □ Check for N+1 query problems
            □ Verify caching effectiveness
            □ Test with large datasets
            □ Measure startup time

         📝 PHASE 8: DOCUMENTATION VERIFICATION
         ───────────────────────────────────────────────────────────────────────────────
         8. Verify documentation completeness and accuracy:

            README.md:
            □ Verify installation instructions work
            □ Test all code examples provided
            □ Check links are not broken
            □ Verify screenshots/diagrams are present (if mentioned)
            □ Check prerequisites are accurate
            □ Verify configuration examples are correct
            
            API Documentation:
            □ Check all endpoints are documented
            □ Verify request/response examples are accurate
            □ Test that examples actually work
            □ Check parameter descriptions are clear
            
            Code Documentation:
            □ Verify all public APIs have docstrings/comments
            □ Check examples in docstrings are correct
            □ Verify type annotations are accurate

         📋 PHASE 9: COMPREHENSIVE TEST REPORT
         ───────────────────────────────────────────────────────────────────────────────
         9. Create detailed TEST_REPORT.md including:

            Report Structure:
            
            # Test Report - [Project Name]
            
            ## Executive Summary
            - Overall Status: ✅ PASS / ❌ FAIL / ⚠️ PARTIAL
            - Test Coverage: XX%
            - Tests Executed: XX
            - Tests Passed: XX (XX%)
            - Tests Failed: XX (XX%)
            - Code Quality: Excellent / Good / Needs Improvement
            - Deployment Risk: LOW / MEDIUM / HIGH
            
            ## Test Coverage Report
            - Module/component coverage breakdown
            - Overall coverage percentage
            - Uncovered lines and why
            - Branch coverage statistics
            
            ## Test Results
            - Unit Tests: Detailed breakdown by module
            - Integration Tests: Results for each integration point
            - E2E Tests: Results for each workflow
            - Performance Tests: Benchmarks and measurements
            - Security Tests: Vulnerability findings
            
            ## Code Quality Analysis
            - Syntax Validation: Pass/Fail
            - Code Formatting: Issues found and fixed
            - Linting Results: Warnings and errors
            - Type Checking: Type errors found
            - Security Scan: Vulnerabilities discovered
            - Complexity Metrics: Functions exceeding thresholds
            
            ## Execution Tests
            - Build process results
            - Application startup results
            - Main feature testing results
            - Error handling verification
            
            ## Issues Found
            - 🔴 Critical Issues: Must fix before deployment
            - 🟠 Major Issues: Should fix soon
            - 🟡 Minor Issues: Nice to fix
            - 🔵 Suggestions: Future improvements
            
            ## Performance Analysis (if applicable)
            - Response time measurements
            - Memory usage statistics
            - CPU utilization data
            - Scalability assessment
            
            ## Security Assessment
            - Vulnerability scan results
            - Security best practices compliance
            - Risk areas identified
            
            ## Risk Assessment
            - Deployment readiness
            - Known issues and workarounds
            - Recommendations
            
            ## Recommendations
            - Immediate actions required
            - Future enhancements
            - Code refactoring suggestions
            - Performance optimization opportunities
            
            ## Test Environment
            - Operating System
            - Language/Runtime version
            - Test framework version
            - Dependency versions
            - Test duration
            
            ## Conclusion
            - Final verdict: ✅ APPROVED / ⚠️ CONDITIONAL / ❌ REJECTED
            - Overall quality assessment
            - Production readiness statement

         ═══════════════════════════════════════════════════════════════════════════════
         TOOLS TO USE:
         ═══════════════════════════════════════════════════════════════════════════════

         Required Tools:
         □ File Reader: Read all source code files
         □ Syntax Validator: Validate code syntax for each language
         □ Test Generator: Create comprehensive test files
         □ Test Runner: Execute test suites
         □ Code Formatter: Format code (Black, Prettier, etc.)
         □ Linter: Check code style (Flake8, ESLint, etc.)
         □ Type Checker: Verify types (mypy, tsc, etc.)
         □ Code Executor: Run main program
         □ Dependency Installer: Install test dependencies
         □ Coverage Reporter: Generate coverage reports

         ═══════════════════════════════════════════════════════════════════════════════
         LANGUAGE-SPECIFIC TESTING COMMANDS:
         ═══════════════════════════════════════════════════════════════════════════════

         Python:
         Tests: pytest tests/ -v --cov={project_dir} --cov-report=html
         Format: black {project_dir}
         Lint: flake8 {project_dir}
         Type: mypy {project_dir}
         Security: safety check

         JavaScript/TypeScript:
         Tests: npm test -- --coverage
         Format: prettier --write .
         Lint: eslint src/
         Type: tsc --noEmit
         Security: npm audit

         Java:
         Tests: mvn test  OR  ./gradlew test
         Format: mvn spotless:apply
         Lint: mvn checkstyle:check
         Security: mvn dependency-check:check

         C#:
         Tests: dotnet test --collect:"XPlat Code Coverage"
         Format: dotnet format
         Lint: dotnet build /p:EnforceCodeStyleInBuild=true
         Security: dotnet list package --vulnerable

         Go:
         Tests: go test ./... -v -cover
         Format: go fmt ./...
         Lint: golangci-lint run
         Security: govulncheck ./...

         Rust:
         Tests: cargo test
         Format: cargo fmt
         Lint: cargo clippy
         Security: cargo audit

         ═══════════════════════════════════════════════════════════════════════════════
         CRITICAL QUALITY GATES:
         ═══════════════════════════════════════════════════════════════════════════════

         The project MUST meet these criteria to be approved:

         ✅ MANDATORY (Must Pass):
         □ No syntax errors
         □ All tests pass (100% pass rate)
         □ No critical security vulnerabilities
         □ No hardcoded secrets or credentials
         □ Code builds/compiles successfully
         □ Main program executes without errors
         □ README installation instructions work

         ⚠️ STRONGLY RECOMMENDED (Should Pass):
         □ Test coverage ≥ 80%
         □ No major linting errors
         □ All public APIs documented
         □ No memory leaks detected
         □ Response times within acceptable limits
         □ No high or critical dependency vulnerabilities

         🎯 NICE TO HAVE (Bonus):
         □ Test coverage ≥ 90%
         □ Zero linting warnings
         □ Cyclomatic complexity < 10 for all functions
         □ Performance benchmarks documented
         □ Accessibility compliance (for UI)

         ═══════════════════════════════════════════════════════════════════════════════
         EXPECTED DELIVERABLES:
         ═══════════════════════════════════════════════════════════════════════════════

         1. Complete test suite in tests/ or __tests__/ directory
         2. TEST_REPORT.md with comprehensive results
         3. Coverage report (HTML format if available)
         4. Fixed/formatted code (if formatting issues found)
         5. List of identified issues with severity levels
         6. Recommendations for improvements
         7. Security scan results
         8. Performance analysis (if applicable)
         9. Final approval/rejection decision with justification

         ═══════════════════════════════════════════════════════════════════════════════
         SUCCESS CRITERIA:
         ═══════════════════════════════════════════════════════════════════════════════

         The project is considered PRODUCTION-READY if:
         ✅ All mandatory quality gates pass
         ✅ All tests execute and pass
         ✅ Code is properly formatted and linted
         ✅ Documentation is complete and accurate
         ✅ No critical security issues
         ✅ Application runs without errors
         ✅ Test coverage meets minimum threshold
         ✅ Performance is acceptable for intended use case

         ═══════════════════════════════════════════════════════════════════════════════
         BEGIN COMPREHENSIVE TESTING AND QUALITY ASSURANCE NOW!
         ═══════════════════════════════════════════════════════════════════════════════
         """,
         agent=agent,
         context=context_tasks,
         expected_output="""Complete testing report including:
                           - Test file creation summary
                           - Test execution results
                           - Code formatting results
                           - Linting results
                           - Main program execution output
                           - List of any issues found
                           - Overall quality assessment
                           - TEST_REPORT.md file"""
    )