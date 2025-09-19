#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="awasome-fastapi"
DOCKER_IMAGE="awasome-api"
DOCKER_TAG="latest"

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_requirements() {
    log_info "Checking requirements..."
    
    # Check if Docker is installed and running
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        log_error "Docker is not running. Please start Docker first."
        exit 1
    fi
    
    # Check if Docker Compose is available
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    log_info "Requirements check passed!"
}

build_image() {
    log_info "Building Docker image..."
    docker build -t ${DOCKER_IMAGE}:${DOCKER_TAG} .
    log_info "Docker image built successfully!"
}

start_development() {
    log_info "Starting development environment..."
    
    # Create logs directory if it doesn't exist
    mkdir -p logs
    
    # Start services
    if command -v docker-compose &> /dev/null; then
        docker-compose up -d
    else
        docker compose up -d
    fi
    
    log_info "Development environment started!"
    log_info "API will be available at: http://localhost:8000"
    log_info "CouchDB will be available at: http://localhost:5984"
    log_info "API Documentation: http://localhost:8000/docs"
    log_info "Health Check: http://localhost:8000/api/v1/system/health/live"
}

stop_development() {
    log_info "Stopping development environment..."
    
    if command -v docker-compose &> /dev/null; then
        docker-compose down
    else
        docker compose down
    fi
    
    log_info "Development environment stopped!"
}

start_production() {
    log_info "Starting production environment with Nginx..."
    
    if command -v docker-compose &> /dev/null; then
        docker-compose --profile production up -d
    else
        docker compose --profile production up -d
    fi
    
    log_info "Production environment started!"
    log_info "API will be available at: http://localhost"
    log_info "HTTPS will be available at: https://localhost (if SSL configured)"
}

deploy_kubernetes() {
    log_info "Deploying to Kubernetes..."
    
    # Check if kubectl is available
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed. Please install kubectl first."
        exit 1
    fi
    
    # Apply Kubernetes manifests
    log_info "Applying Kubernetes manifests..."
    kubectl apply -f k8s/
    
    log_info "Waiting for deployment to be ready..."
    kubectl wait --for=condition=available --timeout=300s deployment/awasome-api -n awasome-api
    
    # Get service information
    kubectl get services -n awasome-api
    
    log_info "Kubernetes deployment completed!"
    log_info "Check the status with: kubectl get pods -n awasome-api"
}

run_tests() {
    log_info "Running tests..."
    
    # Build test image
    docker build -t ${DOCKER_IMAGE}:test .
    
    # Run tests in container
    docker run --rm \
        -v $(pwd)/app:/app/app \
        -v $(pwd)/tests:/app/tests \
        ${DOCKER_IMAGE}:test \
        python -m pytest tests/ -v --cov=app --cov-report=term-missing
    
    log_info "Tests completed!"
}

show_logs() {
    log_info "Showing application logs..."
    
    if command -v docker-compose &> /dev/null; then
        docker-compose logs -f api
    else
        docker compose logs -f api
    fi
}

cleanup() {
    log_info "Cleaning up..."
    
    # Stop and remove containers
    if command -v docker-compose &> /dev/null; then
        docker-compose down -v
    else
        docker compose down -v
    fi
    
    # Remove images
    docker rmi ${DOCKER_IMAGE}:${DOCKER_TAG} 2>/dev/null || true
    docker rmi ${DOCKER_IMAGE}:test 2>/dev/null || true
    
    # Clean up unused Docker resources
    docker system prune -f
    
    log_info "Cleanup completed!"
}

show_status() {
    log_info "System Status:"
    echo ""
    
    # Check if services are running
    if command -v docker-compose &> /dev/null; then
        docker-compose ps
    else
        docker compose ps
    fi
    
    echo ""
    log_info "Health Checks:"
    
    # Check API health
    if curl -s http://localhost:8000/api/v1/system/health/live > /dev/null 2>&1; then
        echo -e "API: ${GREEN}✓ Healthy${NC}"
    else
        echo -e "API: ${RED}✗ Unhealthy${NC}"
    fi
    
    # Check CouchDB health
    if curl -s http://localhost:5984/_up > /dev/null 2>&1; then
        echo -e "CouchDB: ${GREEN}✓ Healthy${NC}"
    else
        echo -e "CouchDB: ${RED}✗ Unhealthy${NC}"
    fi
}

show_usage() {
    echo "Usage: $0 {build|dev|prod|stop|k8s|test|logs|status|cleanup|help}"
    echo ""
    echo "Commands:"
    echo "  build    - Build Docker image"
    echo "  dev      - Start development environment"
    echo "  prod     - Start production environment with Nginx"
    echo "  stop     - Stop all services"
    echo "  k8s      - Deploy to Kubernetes"
    echo "  test     - Run tests"
    echo "  logs     - Show application logs"
    echo "  status   - Show system status and health"
    echo "  cleanup  - Clean up containers and images"
    echo "  help     - Show this help message"
}

# Main script
case "$1" in
    build)
        check_requirements
        build_image
        ;;
    dev)
        check_requirements
        build_image
        start_development
        ;;
    prod)
        check_requirements
        build_image
        start_production
        ;;
    stop)
        stop_development
        ;;
    k8s)
        check_requirements
        build_image
        deploy_kubernetes
        ;;
    test)
        check_requirements
        run_tests
        ;;
    logs)
        show_logs
        ;;
    status)
        show_status
        ;;
    cleanup)
        cleanup
        ;;
    help)
        show_usage
        ;;
    *)
        show_usage
        exit 1
        ;;
esac