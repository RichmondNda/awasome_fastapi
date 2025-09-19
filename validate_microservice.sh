#!/bin/bash

# Awasome FastAPI - Validation Complete du Microservice
# Ce script effectue une validation complète de toutes les fonctionnalités

set -e

# Couleurs
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() {
    echo "=================================================="
    printf "${BLUE}🚀 $1${NC}\n"
    echo "=================================================="
}

print_success() {
    printf "${GREEN}✅ $1${NC}\n"
}

print_warning() {
    printf "${YELLOW}⚠️  $1${NC}\n"
}

print_error() {
    printf "${RED}❌ $1${NC}\n"
}

# Variables globales
BASE_URL="http://localhost:8000"
API_URL="$BASE_URL/api/v1"
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Function to test endpoint
test_endpoint() {
    local method="$1"
    local endpoint="$2"
    local expected_status="$3"
    local description="$4"
    local data="$5"
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    if [[ -n "$data" ]]; then
        response=$(curl -s -w "%{http_code}" -X "$method" "$endpoint" \
                   -H "Content-Type: application/json" \
                   -d "$data")
    else
        response=$(curl -s -w "%{http_code}" -X "$method" "$endpoint")
    fi
    
    # Extract HTTP status code
    status_code=${response: -3}
    response_body=${response%???}
    
    if [[ "$status_code" == "$expected_status" ]]; then
        print_success "$description (Status: $status_code)"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    else
        print_error "$description (Expected: $expected_status, Got: $status_code)"
        echo "Response: $response_body"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi
}

# Function to test database auto-creation
test_database_auto_creation() {
    print_header "🗄️ Validation de la Création Automatique de Base de Données"
    
    # Check if database exists
    db_response=$(curl -s -u admin:password "http://localhost:5984/_all_dbs")
    
    if echo "$db_response" | grep -q "awasome_db"; then
        print_success "Base de données 'awasome_db' créée automatiquement"
    else
        print_error "Base de données non trouvée: $db_response"
    fi
    
    # Test database info
    db_info=$(curl -s -u admin:password "http://localhost:5984/awasome_db")
    if echo "$db_info" | grep -q "db_name"; then
        print_success "Informations de la base de données accessibles"
    else
        print_error "Impossible d'accéder aux informations de la base"
    fi
}

# Function to test health endpoints
test_health_endpoints() {
    print_header "🏥 Test des Endpoints de Santé"
    
    test_endpoint "GET" "$BASE_URL/" "200" "Endpoint racine"
    test_endpoint "GET" "$API_URL/system/health" "200" "Health check principal" 
    test_endpoint "GET" "$API_URL/system/health/live" "200" "Liveness probe"
    test_endpoint "GET" "$API_URL/system/health/ready" "200" "Readiness probe" 
    test_endpoint "GET" "$API_URL/system/info" "200" "Informations système"
}

# Function to test user CRUD operations
test_user_crud() {
    print_header "👥 Test des Opérations CRUD Utilisateur"
    
    # Create user
    user_data='{
        "username": "validation_user",
        "email": "validation@example.com", 
        "first_name": "Validation",
        "last_name": "User",
        "password": "ValidPassword123!",
        "confirm_password": "ValidPassword123!"
    }'
    
    create_response=$(curl -s -X POST "$API_URL/users/" \
                     -H "Content-Type: application/json" \
                     -d "$user_data")
    
    if echo "$create_response" | grep -q "validation_user"; then
        print_success "Création d'utilisateur"
        user_id=$(echo "$create_response" | jq -r '.id')
        
        # Get user
        test_endpoint "GET" "$API_URL/users/$user_id" "200" "Récupération d'utilisateur"
        
        # Update user  
        update_data='{"bio": "Updated validation bio"}'
        test_endpoint "PUT" "$API_URL/users/$user_id" "200" "Mise à jour d'utilisateur" "$update_data"
        
        # List users
        test_endpoint "GET" "$API_URL/users/" "200" "Liste des utilisateurs"
        
        # Delete user
        test_endpoint "DELETE" "$API_URL/users/$user_id" "200" "Suppression d'utilisateur"
        
    else
        print_error "Échec de création d'utilisateur: $create_response"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
}

# Function to test swagger documentation
test_documentation() {
    print_header "📚 Test de la Documentation"
    
    test_endpoint "GET" "$BASE_URL/docs" "200" "Documentation Swagger UI"
    test_endpoint "GET" "$BASE_URL/redoc" "200" "Documentation ReDoc"
    test_endpoint "GET" "$API_URL/openapi.json" "200" "Schéma OpenAPI"
}

# Function to test security features
test_security() {
    print_header "🔒 Test des Fonctionnalités de Sécurité"
    
    # Test validation errors
    invalid_user='{
        "username": "a",
        "email": "invalid-email",
        "password": "weak"
    }'
    
    test_endpoint "POST" "$API_URL/users/" "422" "Validation des données invalides" "$invalid_user"
    
    # Test duplicate user
    duplicate_user='{
        "username": "duplicate_test",
        "email": "duplicate@example.com",
        "password": "ValidPassword123!",
        "confirm_password": "ValidPassword123!"
    }'
    
    # Create first user
    curl -s -X POST "$API_URL/users/" \
         -H "Content-Type: application/json" \
         -d "$duplicate_user" > /dev/null
    
    # Try to create duplicate
    test_endpoint "POST" "$API_URL/users/" "409" "Prévention des doublons" "$duplicate_user"
}

# Function to test performance
test_performance() {
    print_header "⚡ Test de Performance Basique"
    
    start_time=$(date +%s.%N)
    curl -s "$BASE_URL/" > /dev/null
    end_time=$(date +%s.%N)
    
    response_time=$(echo "$end_time - $start_time" | bc)
    response_time_ms=$(echo "$response_time * 1000" | bc)
    
    if (( $(echo "$response_time < 1.0" | bc -l) )); then
        print_success "Temps de réponse acceptable: ${response_time_ms}ms"
    else
        print_warning "Temps de réponse élevé: ${response_time_ms}ms"
    fi
}

# Function to check environment configuration
check_environment() {
    print_header "🌍 Vérification de la Configuration Environnement"
    
    # Check if services are running
    if curl -s "$BASE_URL/" > /dev/null 2>&1; then
        print_success "API FastAPI accessible"
    else
        print_error "API FastAPI non accessible"
        exit 1
    fi
    
    if curl -s "http://localhost:5984" > /dev/null 2>&1; then
        print_success "CouchDB accessible"
    else
        print_error "CouchDB non accessible"
        exit 1
    fi
    
    if redis-cli -p 6379 ping > /dev/null 2>&1; then
        print_success "Redis accessible"
    else
        print_warning "Redis non accessible (optionnel)"
    fi
}

# Main execution
print_header "🧪 Validation Complète du Microservice Awasome FastAPI"

# Check prerequisites
if ! command -v curl &> /dev/null; then
    print_error "curl n'est pas installé"
    exit 1
fi

if ! command -v jq &> /dev/null; then
    print_error "jq n'est pas installé"
    exit 1
fi

# Run all tests
check_environment
test_database_auto_creation
test_health_endpoints
test_user_crud
test_documentation
test_security
test_performance

# Final report
echo ""
print_header "📊 Rapport Final de Validation"

echo "Tests totaux: $TOTAL_TESTS"
print_success "Tests réussis: $PASSED_TESTS"
print_error "Tests échoués: $FAILED_TESTS"

if [[ $FAILED_TESTS -eq 0 ]]; then
    echo ""
    print_success "🎉 TOUS LES TESTS SONT PASSÉS! Le microservice est pleinement fonctionnel!"
    
    echo ""
    echo "✨ Fonctionnalités validées:"
    echo "   • 🗄️ Création automatique de base de données avec paramètre d'environnement"
    echo "   • 🏥 Endpoints de santé et monitoring"
    echo "   • 👥 CRUD complet des utilisateurs" 
    echo "   • 📚 Documentation Swagger et ReDoc"
    echo "   • 🔒 Validation et sécurité des données"
    echo "   • ⚡ Performance acceptable"
    
    echo ""
    echo "🌐 Accès aux ressources:"
    echo "   • API: $BASE_URL"
    echo "   • Documentation: $BASE_URL/docs"
    echo "   • Alternative Doc: $BASE_URL/redoc"
    echo "   • Health Check: $API_URL/system/health"
    
    exit 0
else
    echo ""
    print_error "❌ QUELQUES TESTS ONT ÉCHOUÉ. Vérifiez les détails ci-dessus."
    exit 1
fi