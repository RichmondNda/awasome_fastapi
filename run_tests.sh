#!/bin/bash

# Test runner script for Awasome FastAPI
# This script runs various types of tests and provides options for different test scenarios

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_color() {
    printf "${1}${2}${NC}\n"
}

print_header() {
    echo "=================================================="
    print_color $BLUE "$1"
    echo "=================================================="
}

print_success() {
    print_color $GREEN "✅ $1"
}

print_warning() {
    print_color $YELLOW "⚠️  $1"
}

print_error() {
    print_color $RED "❌ $1"
}

# Default values
RUN_UNIT=true
RUN_INTEGRATION=false
RUN_E2E=false
RUN_SECURITY=false
RUN_PERFORMANCE=false
COVERAGE=true
VERBOSE=false
FAIL_FAST=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --unit-only)
            RUN_UNIT=true
            RUN_INTEGRATION=false
            RUN_E2E=false
            shift
            ;;
        --integration)
            RUN_INTEGRATION=true
            shift
            ;;
        --e2e)
            RUN_E2E=true
            shift
            ;;
        --all)
            RUN_UNIT=true
            RUN_INTEGRATION=true
            RUN_E2E=true
            shift
            ;;
        --security)
            RUN_SECURITY=true
            shift
            ;;
        --performance)
            RUN_PERFORMANCE=true
            shift
            ;;
        --no-coverage)
            COVERAGE=false
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --fail-fast)
            FAIL_FAST=true
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --unit-only      Run only unit tests (default)"
            echo "  --integration    Run integration tests (requires external services)"
            echo "  --e2e           Run end-to-end tests"
            echo "  --all           Run all test types"
            echo "  --security      Run security tests"
            echo "  --performance   Run performance tests"
            echo "  --no-coverage   Skip coverage report"
            echo "  --verbose       Verbose output"
            echo "  --fail-fast     Stop on first failure"
            echo "  --help          Show this help message"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Check if we're in the right directory
if [[ ! -f "requirements.txt" ]] || [[ ! -d "app" ]]; then
    print_error "Please run this script from the project root directory"
    exit 1
fi

print_header "🚀 Running Awasome FastAPI Tests"

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    print_error "pytest is not installed. Installing dependencies..."
    pip install -r requirements.txt
fi

# Build pytest command
PYTEST_CMD="python -m pytest"

# Add coverage options
if [[ "$COVERAGE" == true ]]; then
    PYTEST_CMD="$PYTEST_CMD --cov=app --cov-report=term-missing --cov-report=html:coverage_html"
fi

# Add verbose option
if [[ "$VERBOSE" == true ]]; then
    PYTEST_CMD="$PYTEST_CMD -v"
fi

# Add fail fast option
if [[ "$FAIL_FAST" == true ]]; then
    PYTEST_CMD="$PYTEST_CMD -x"
fi

# Function to run specific test types
run_tests() {
    local test_type="$1"
    local marker="$2"
    local description="$3"
    
    print_header "$description"
    
    if [[ -n "$marker" ]]; then
        CMD="$PYTEST_CMD -m $marker"
    else
        CMD="$PYTEST_CMD"
    fi
    
    print_color $YELLOW "Running: $CMD"
    
    if eval $CMD; then
        print_success "$description completed successfully"
        return 0
    else
        print_error "$description failed"
        return 1
    fi
}

# Track overall success
OVERALL_SUCCESS=true

# Run unit tests
if [[ "$RUN_UNIT" == true ]]; then
    if ! run_tests "unit" "unit" "🧪 Unit Tests"; then
        OVERALL_SUCCESS=false
        if [[ "$FAIL_FAST" == true ]]; then
            exit 1
        fi
    fi
fi

# Run integration tests
if [[ "$RUN_INTEGRATION" == true ]]; then
    print_warning "Integration tests require running CouchDB and Redis services"
    print_warning "Make sure Docker services are up: docker-compose up -d"
    
    if ! run_tests "integration" "integration" "🔗 Integration Tests"; then
        OVERALL_SUCCESS=false
        if [[ "$FAIL_FAST" == true ]]; then
            exit 1
        fi
    fi
fi

# Run end-to-end tests
if [[ "$RUN_E2E" == true ]]; then
    print_warning "E2E tests require the full application stack to be running"
    
    if ! run_tests "e2e" "e2e" "🌐 End-to-End Tests"; then
        OVERALL_SUCCESS=false
        if [[ "$FAIL_FAST" == true ]]; then
            exit 1
        fi
    fi
fi

# Run security tests
if [[ "$RUN_SECURITY" == true ]]; then
    if ! run_tests "security" "security" "🔒 Security Tests"; then
        OVERALL_SUCCESS=false
        if [[ "$FAIL_FAST" == true ]]; then
            exit 1
        fi
    fi
fi

# Run performance tests
if [[ "$RUN_PERFORMANCE" == true ]]; then
    if ! run_tests "performance" "performance" "⚡ Performance Tests"; then
        OVERALL_SUCCESS=false
        if [[ "$FAIL_FAST" == true ]]; then
            exit 1
        fi
    fi
fi

# If no specific test type was selected, run all non-integration tests
if [[ "$RUN_UNIT" == false && "$RUN_INTEGRATION" == false && "$RUN_E2E" == false && "$RUN_SECURITY" == false && "$RUN_PERFORMANCE" == false ]]; then
    if ! run_tests "all" "not integration and not e2e and not slow" "🧪 All Tests (except integration/e2e)"; then
        OVERALL_SUCCESS=false
    fi
fi

# Show coverage report location if coverage was enabled
if [[ "$COVERAGE" == true ]]; then
    echo ""
    print_color $BLUE "📊 Coverage Report"
    echo "HTML Coverage report: coverage_html/index.html"
    if command -v xdg-open &> /dev/null; then
        echo "Open with: xdg-open coverage_html/index.html"
    elif command -v open &> /dev/null; then
        echo "Open with: open coverage_html/index.html"
    fi
fi

# Final result
echo ""
print_header "📋 Test Results Summary"

if [[ "$OVERALL_SUCCESS" == true ]]; then
    print_success "All tests passed! 🎉"
    exit 0
else
    print_error "Some tests failed. Check the output above for details."
    exit 1
fi