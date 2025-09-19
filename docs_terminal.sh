#!/bin/bash

# Documentation Terminal pour Awasome FastAPI
# Usage: ./docs_terminal.sh [endpoint]

BASE_URL="http://localhost:8000"
API_URL="$BASE_URL/api/v1"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_header() {
    printf "${BLUE}📚 $1${NC}\n"
    echo "================================================"
}

print_section() {
    printf "${GREEN}$1${NC}\n"
}

print_endpoint() {
    printf "${YELLOW}$1${NC}\n"
}

show_api_info() {
    print_header "Informations API"
    curl -s "$API_URL/openapi.json" | jq '.info'
}

show_all_endpoints() {
    print_header "Tous les Endpoints"
    endpoints=$(curl -s "$API_URL/openapi.json" | jq -r '.paths | keys[]')
    
    echo "$endpoints" | while read endpoint; do
        methods=$(curl -s "$API_URL/openapi.json" | jq -r ".paths[\"$endpoint\"] | keys[]")
        for method in $methods; do
            summary=$(curl -s "$API_URL/openapi.json" | jq -r ".paths[\"$endpoint\"].$method.summary // \"No summary\"")
            printf "${YELLOW}%-8s${NC} ${BLUE}%-40s${NC} %s\n" "$(echo $method | tr '[:lower:]' '[:upper:]')" "$endpoint" "$summary"
        done
    done
}

show_endpoint_details() {
    local endpoint="$1"
    print_header "Détails de l'endpoint: $endpoint"
    
    curl -s "$API_URL/openapi.json" | jq ".paths[\"$endpoint\"]"
}

show_schemas() {
    print_header "Schémas de Données"
    curl -s "$API_URL/openapi.json" | jq '.components.schemas | keys[]'
}

show_schema_details() {
    local schema="$1"
    print_header "Détails du schéma: $schema"
    curl -s "$API_URL/openapi.json" | jq ".components.schemas[\"$schema\"]"
}

show_user_examples() {
    print_header "Exemples d'Utilisation - Utilisateurs"
    
    print_section "1. Créer un utilisateur:"
    echo 'curl -X POST "http://localhost:8000/api/v1/users/" \'
    echo '  -H "Content-Type: application/json" \'
    echo '  -d '"'"'{
    "username": "john_doe",
    "email": "john@example.com",
    "first_name": "John",
    "last_name": "Doe", 
    "password": "SecurePass123!",
    "confirm_password": "SecurePass123!"
  }'"'"''
    
    echo ""
    print_section "2. Lister les utilisateurs:"
    echo 'curl "http://localhost:8000/api/v1/users/"'
    
    echo ""
    print_section "3. Récupérer un utilisateur:"
    echo 'curl "http://localhost:8000/api/v1/users/{user_id}"'
    
    echo ""
    print_section "4. Mettre à jour un utilisateur:"
    echo 'curl -X PUT "http://localhost:8000/api/v1/users/{user_id}" \'
    echo '  -H "Content-Type: application/json" \'
    echo '  -d '"'"'{"bio": "Updated bio"}'"'"''
    
    echo ""
    print_section "5. Supprimer un utilisateur:"
    echo 'curl -X DELETE "http://localhost:8000/api/v1/users/{user_id}"'
}

show_health_examples() {
    print_header "Exemples - Health Checks"
    
    print_section "1. Health check complet:"
    echo 'curl "http://localhost:8000/api/v1/system/health" | jq'
    
    echo ""
    print_section "2. Liveness probe:"
    echo 'curl "http://localhost:8000/api/v1/system/health/live"'
    
    echo ""
    print_section "3. Informations système:"
    echo 'curl "http://localhost:8000/api/v1/system/info" | jq'
}

show_help() {
    print_header "Aide - Documentation Terminal"
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  info              - Afficher les informations de l'API"
    echo "  endpoints         - Lister tous les endpoints"
    echo "  endpoint <path>   - Détails d'un endpoint spécifique"
    echo "  schemas           - Lister tous les schémas"
    echo "  schema <name>     - Détails d'un schéma spécifique"
    echo "  examples-users    - Exemples d'utilisation des endpoints utilisateurs"
    echo "  examples-health   - Exemples de health checks"
    echo "  help              - Afficher cette aide"
    echo ""
    echo "Exemples:"
    echo "  $0 info"
    echo "  $0 endpoints"
    echo "  $0 endpoint '/api/v1/users/'"
    echo "  $0 schema UserCreate"
    echo "  $0 examples-users"
}

# Main logic
case "$1" in
    "info")
        show_api_info
        ;;
    "endpoints")
        show_all_endpoints
        ;;
    "endpoint")
        if [ -z "$2" ]; then
            echo "Usage: $0 endpoint <endpoint_path>"
            exit 1
        fi
        show_endpoint_details "$2"
        ;;
    "schemas")
        show_schemas
        ;;
    "schema")
        if [ -z "$2" ]; then
            echo "Usage: $0 schema <schema_name>"
            exit 1
        fi
        show_schema_details "$2"
        ;;
    "examples-users")
        show_user_examples
        ;;
    "examples-health")
        show_health_examples
        ;;
    "help"|"--help"|"-h")
        show_help
        ;;
    "")
        show_help
        ;;
    *)
        echo "Commande inconnue: $1"
        show_help
        exit 1
        ;;
esac