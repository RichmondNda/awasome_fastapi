#!/bin/bash

# Script d'arrêt pour l'application FastAPI
echo "🛑 Arrêt de l'application FastAPI..."

# Arrêt des processus uvicorn
echo "⏹️ Arrêt du serveur FastAPI..."
pkill -f "uvicorn app.main:app" || echo "Aucun processus FastAPI en cours"

# Optionnel : arrêt de CouchDB (décommentez si souhaité)
# echo "🗄️ Arrêt de CouchDB..."
# docker stop couchdb-awasome || echo "CouchDB n'était pas en cours d'exécution"

echo "✅ Arrêt terminé!"