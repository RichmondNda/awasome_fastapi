#!/bin/bash

# Awasome FastAPI Complete Setup Script
# Sets up development environment with comprehensive tooling

set -e

echo "🚀 Setting up Awasome FastAPI Development Environment"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_step() {
    echo -e "${BLUE}▶ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check prerequisites
print_step "Checking prerequisites..."

# Check Docker
if ! command -v docker &> /dev/null; then
    print_error "Docker is required but not installed"
    exit 1
fi
print_success "Docker found"

# Check Docker Compose
if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is required but not installed"
    exit 1
fi
print_success "Docker Compose found"

# Check Python
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is required but not installed"
    exit 1
fi
print_success "Python found"

# Check pip
if ! command -v pip3 &> /dev/null; then
    print_error "pip3 is required but not installed"
    exit 1
fi
print_success "pip found"

# Create virtual environment if it doesn't exist
print_step "Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    print_success "Virtual environment created"
else
    print_warning "Virtual environment already exists"
fi

# Activate virtual environment
source venv/bin/activate
print_success "Virtual environment activated"

# Install Python dependencies
print_step "Installing Python dependencies..."
pip install -r requirements.txt
print_success "Python dependencies installed"

# Set up environment file
print_step "Setting up environment configuration..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    print_success "Environment file created from template"
    print_warning "Please update .env with your specific configuration"
else
    print_warning ".env file already exists"
fi

# Start Docker services
print_step "Starting Docker services..."
docker-compose up -d
print_success "Docker services started"

# Wait for services to be ready
print_step "Waiting for services to be ready..."
sleep 10

# Check services health
print_step "Checking services health..."

# Check CouchDB
if curl -s http://localhost:5984/_up > /dev/null; then
    print_success "CouchDB is running"
else
    print_error "CouchDB is not responding"
fi

# Check Redis
if docker exec awasome_redis redis-cli ping > /dev/null 2>&1; then
    print_success "Redis is running"
else
    print_warning "Redis ping failed (might not be accessible)"
fi

# Make terminal docs executable
print_step "Setting up terminal documentation..."
if [ -f "terminal_docs.py" ]; then
    chmod +x terminal_docs.py
    print_success "Terminal documentation CLI ready"
else
    print_warning "terminal_docs.py not found"
fi

# Create useful aliases
print_step "Creating helpful development aliases..."
cat > scripts/dev-aliases.sh << 'EOF'
#!/bin/bash
# Helpful aliases for development

alias docs-terminal="python terminal_docs.py"
alias docs-interactive="python terminal_docs.py interactive"
alias api-info="python terminal_docs.py info"
alias api-endpoints="python terminal_docs.py endpoints"
alias api-test="curl -s http://localhost:8000/api/v1/system/health | jq"
alias api-cache-info="curl -s http://localhost:8000/api/v1/system/cache/info | jq"
alias api-cache-test="curl -s http://localhost:8000/api/v1/system/cache/test | jq"
alias api-perf="curl -s http://localhost:8000/api/v1/system/cache/performance | jq"

echo "🚀 Development aliases loaded:"
echo "  docs-terminal       - Terminal documentation"
echo "  docs-interactive    - Interactive docs browser"
echo "  api-info           - API information"
echo "  api-endpoints      - List all endpoints"
echo "  api-test           - Quick health check"
echo "  api-cache-info     - Cache information"
echo "  api-cache-test     - Test cache functionality"
echo "  api-perf           - Cache performance test"
EOF

chmod +x scripts/dev-aliases.sh
print_success "Development aliases created"

# Create development startup script
print_step "Creating development startup script..."
cat > start-dev.sh << 'EOF'
#!/bin/bash
echo "🚀 Starting Awasome FastAPI Development Environment"

# Activate virtual environment
source venv/bin/activate

# Load development aliases
source scripts/dev-aliases.sh

# Start the FastAPI application
echo "Starting FastAPI server..."
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
EOF

chmod +x start-dev.sh
print_success "Development startup script created"

# Final summary
echo ""
echo "🎉 Setup completed successfully!"
echo ""
echo "📋 Next Steps:"
echo "   1. Review and update .env file with your configuration"
echo "   2. Start development server: ./start-dev.sh"
echo "   3. Or manually: source venv/bin/activate && uvicorn app.main:app --reload"
echo "   4. Access terminal docs: python terminal_docs.py interactive"
echo ""
echo "📖 Available endpoints:"
echo "   • API Documentation: http://localhost:8000/docs"
echo "   • Health Check: http://localhost:8000/api/v1/system/health"
echo "   • Cache Info: http://localhost:8000/api/v1/system/cache/info"
echo "   • Cache Test: http://localhost:8000/api/v1/system/cache/test"
echo "   • Performance: http://localhost:8000/api/v1/system/cache/performance"
echo "   • CouchDB Admin: http://localhost:5984/_utils"
echo ""
echo "🔧 Development tools:"
echo "   • Terminal docs: python terminal_docs.py --help"
echo "   • Interactive docs: python terminal_docs.py interactive"
echo "   • Load aliases: source scripts/dev-aliases.sh"
echo "   • Run tests: pytest"
echo "   • Code formatting: black ."
echo ""

print_success "Development environment ready! 🚀"
echo "💡 Tip: Run './start-dev.sh' to start development server with all tools loaded"