#!/bin/bash

echo "🚀 Configuration des Git hooks et changelog..."

# Installer les dépendances Python
pip install git-changelog

# Définir le dossier de hooks git
git config core.hooksPath .githooks

# Rendre les scripts exécutables
chmod +x .githooks/commit-msg
chmod +x .githooks/pre-push

echo "✅ Installation terminée !"
echo "👉 Utilise 'git-changelog --convention angular > CHANGELOG.md' pour générer ton changelog."
