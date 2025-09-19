#!/bin/bash

# Script de lancement pour le microservice FastAPI
echo "🚀 Lancement du microservice FastAPI..."

# Activation de l'environnement virtuel
echo "📁 Activation de l'environnement virtuel..."
source venv/bin/activate

# Vérification que CouchDB est en cours d'exécution
echo "🔍 Vérification de CouchDB..."
if ! curl -s http://admin:password@localhost:5984/ > /dev/null; then
    echo "❌ CouchDB n'est pas accessible. Démarrage de CouchDB avec Docker..."
    docker start couchdb-awasome || docker run -d --name couchdb-awasome -e COUCHDB_USER=admin -e COUCHDB_PASSWORD=password -p 5984:5984 couchdb:3.3
    echo "⏳ Attente du démarrage de CouchDB..."
    sleep 5
fi

echo "✅ CouchDB est prêt!"

# Installation des dépendances si nécessaire
if [ ! -d "venv/lib/python*/site-packages/fastapi" ]; then
    echo "📦 Installation des dépendances..."
    pip install -r requirements.txt
fi

# Lancement de l'application FastAPI
echo "🌟 Démarrage du microservice FastAPI..."
echo ""
echo "� URLs d'accès :"
echo "   • API: http://localhost:8000"
echo "   • Documentation Swagger: http://localhost:8000/docs"
echo "   • Documentation ReDoc: http://localhost:8000/redoc"
echo "   • Health Check: http://localhost:8000/api/v1/system/health"
echo "   • CouchDB Fauxton: http://localhost:5984/_utils"
echo ""
echo "🔧 Configuration :"
echo "   • Environment: $(grep ENVIRONMENT .env 2>/dev/null || echo 'development')"
echo "   • Debug: $(grep DEBUG .env 2>/dev/null || echo 'true')"
echo "   • API Version: /api/v1"
echo ""
echo "📝 Logs disponibles dans la console"
echo "🛑 Appuyez sur Ctrl+C pour arrêter le serveur"
echo ""

# Lancement d'uvicorn avec le bon chemin
cd "$(dirname "$0")"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --log-level info