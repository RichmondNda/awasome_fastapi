#!/bin/bash
set -e

# Colors for output  
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Wait for CouchDB to be ready
wait_for_couchdb() {
    local max_attempts=30
    local attempt=1
    local couchdb_url="http://${COUCHDB_HOST}:${COUCHDB_PORT}"
    
    log_info "Waiting for CouchDB to be ready..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s "${couchdb_url}/_up" > /dev/null 2>&1; then
            log_info "CouchDB is ready!"
            return 0
        fi
        
        log_warn "Attempt $attempt/$max_attempts: CouchDB not ready yet..."
        sleep 2
        ((attempt++))
    done
    
    log_error "CouchDB failed to start after $max_attempts attempts"
    return 1
}

# Initialize database
initialize_database() {
    log_info "Database initialization will be handled by the application..."
    log_info "Auto-creation enabled: ${COUCHDB_CREATE_DB_IF_NOT_EXISTS:-true}"
}

# Main execution
main() {
    log_info "Starting FastAPI application..."
    
    # Wait for CouchDB
    if wait_for_couchdb; then
        initialize_database
        log_info "Starting uvicorn server..."
        if [ "$ENVIRONMENT" = "production" ]; then
            exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
        else
            exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1 --reload
        fi
    else
        log_error "Failed to connect to CouchDB. Exiting."
        exit 1
    fi
}

# Run main function
main