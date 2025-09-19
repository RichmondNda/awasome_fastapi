# 🎯 Guide Frontend Nuxt.js pour l'API FastAPI awasome_fastapi

## 📋 Informations de l'API

### Base URL
```
http://localhost:8000
```

### Documentation API
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🔗 Endpoints Disponibles

### 1. **POST /users/** - Créer un utilisateur
```typescript
// Request Body
interface CreateUserRequest {
  username: string;
  email: string; // Format email valide
}

// Response
interface UserResponse {
  id: string;
  username: string;
  email: string;
}

// Status Codes
// 200: Succès
// 422: Erreur de validation (email invalide, champs manquants)
```

### 2. **GET /users/{user_id}** - Récupérer un utilisateur
```typescript
// Path Parameter
user_id: string

// Response
interface UserResponse {
  id: string;
  username: string;
  email: string;
}

// Status Codes
// 200: Utilisateur trouvé
// 404: Utilisateur non trouvé
```

### 3. **GET /users/** - Lister les utilisateurs (avec pagination)
```typescript
// Query Parameters (optionnels)
interface ListUsersParams {
  skip?: number; // Défaut: 0
  limit?: number; // Défaut: 10
}

// Response
type UsersListResponse = UserResponse[];

// Status Codes
// 200: Succès
```

### 4. **DELETE /users/{user_id}** - Supprimer un utilisateur (soft delete)
```typescript
// Path Parameter
user_id: string

// Response
interface DeleteResponse {
  message: string; // "User marked as deleted"
}

// Status Codes
// 200: Utilisateur supprimé
// 404: Utilisateur non trouvé
// 400: Utilisateur déjà supprimé
```

### 5. **GET /users/export/json** - Exporter les utilisateurs
```typescript
// Response
type ExportResponse = UserResponse[];

// Status Codes
// 200: Succès
```

## 🛠️ Configuration Nuxt.js

### 1. Installation des dépendances recommandées

```bash
# Créer le projet Nuxt
npx nuxi@latest init awasome-fastapi-frontend
cd awasome-fastapi-frontend

# Dépendances pour les appels API
npm install @nuxtjs/axios @pinia/nuxt
# OU utiliser $fetch (intégré)

# Dépendances UI (optionnelles)
npm install @nuxtjs/tailwindcss @headlessui/vue @heroicons/vue
# OU
npm install @nuxt/ui

# Validation des formulaires
npm install @vee-validate/nuxt @vee-validate/rules
```

### 2. Configuration nuxt.config.ts

```typescript
export default defineNuxtConfig({
  devtools: { enabled: true },
  modules: [
    '@pinia/nuxt',
    '@nuxtjs/tailwindcss', // ou @nuxt/ui
    '@vee-validate/nuxt'
  ],
  
  // Configuration des variables d'environnement
  runtimeConfig: {
    public: {
      apiBase: process.env.API_BASE_URL || 'http://localhost:8000'
    }
  },
  
  // Configuration du serveur de dev (optionnel)
  nitro: {
    devProxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        prependPath: true,
      }
    }
  }
})
```

### 3. Variables d'environnement (.env)

```bash
# .env
API_BASE_URL=http://localhost:8000
```

## 📦 Types TypeScript

Créer `~/types/user.ts` :

```typescript
export interface User {
  id: string;
  username: string;
  email: string;
}

export interface CreateUserRequest {
  username: string;
  email: string;
}

export interface UpdateUserRequest {
  username?: string;
  email?: string;
}

export interface ApiError {
  error: string;
}

export interface DeleteResponse {
  message: string;
}

export interface ListUsersParams {
  skip?: number;
  limit?: number;
}
```

## 🔄 Composables API

Créer `~/composables/useApi.ts` :

```typescript
import type { User, CreateUserRequest, ListUsersParams } from '~/types/user'

export const useApi = () => {
  const config = useRuntimeConfig()
  const baseURL = config.public.apiBase

  // Créer un utilisateur
  const createUser = async (userData: CreateUserRequest): Promise<User> => {
    try {
      return await $fetch<User>('/users/', {
        baseURL,
        method: 'POST',
        body: userData
      })
    } catch (error) {
      throw error
    }
  }

  // Récupérer un utilisateur
  const getUser = async (userId: string): Promise<User> => {
    try {
      return await $fetch<User>(`/users/${userId}`, {
        baseURL,
        method: 'GET'
      })
    } catch (error) {
      throw error
    }
  }

  // Lister les utilisateurs
  const getUsers = async (params?: ListUsersParams): Promise<User[]> => {
    try {
      return await $fetch<User[]>('/users/', {
        baseURL,
        method: 'GET',
        query: params
      })
    } catch (error) {
      throw error
    }
  }

  // Supprimer un utilisateur
  const deleteUser = async (userId: string): Promise<{ message: string }> => {
    try {
      return await $fetch<{ message: string }>(`/users/${userId}`, {
        baseURL,
        method: 'DELETE'
      })
    } catch (error) {
      throw error
    }
  }

  // Exporter les utilisateurs
  const exportUsers = async (): Promise<User[]> => {
    try {
      return await $fetch<User[]>('/users/export/json', {
        baseURL,
        method: 'GET'
      })
    } catch (error) {
      throw error
    }
  }

  return {
    createUser,
    getUser,
    getUsers,
    deleteUser,
    exportUsers
  }
}
```

## 🗄️ Store Pinia

Créer `~/stores/users.ts` :

```typescript
import { defineStore } from 'pinia'
import type { User, CreateUserRequest, ListUsersParams } from '~/types/user'

export const useUsersStore = defineStore('users', () => {
  // État
  const users = ref<User[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Actions
  const api = useApi()

  const fetchUsers = async (params?: ListUsersParams) => {
    loading.value = true
    error.value = null
    try {
      users.value = await api.getUsers(params)
    } catch (err: any) {
      error.value = err.data?.error || 'Erreur lors du chargement'
    } finally {
      loading.value = false
    }
  }

  const createUser = async (userData: CreateUserRequest) => {
    loading.value = true
    error.value = null
    try {
      const newUser = await api.createUser(userData)
      users.value.push(newUser)
      return newUser
    } catch (err: any) {
      error.value = err.data?.error || 'Erreur lors de la création'
      throw err
    } finally {
      loading.value = false
    }
  }

  const deleteUser = async (userId: string) => {
    loading.value = true
    error.value = null
    try {
      await api.deleteUser(userId)
      users.value = users.value.filter(user => user.id !== userId)
    } catch (err: any) {
      error.value = err.data?.error || 'Erreur lors de la suppression'
      throw err
    } finally {
      loading.value = false
    }
  }

  return {
    users: readonly(users),
    loading: readonly(loading),
    error: readonly(error),
    fetchUsers,
    createUser,
    deleteUser
  }
})
```

## 📄 Exemples de Pages

### Page principale - `~/pages/index.vue`

```vue
<template>
  <div class="container mx-auto px-4 py-8">
    <h1 class="text-3xl font-bold mb-8">Gestion des Utilisateurs</h1>
    
    <!-- Formulaire de création -->
    <div class="mb-8 p-6 bg-gray-50 rounded-lg">
      <h2 class="text-xl font-semibold mb-4">Ajouter un utilisateur</h2>
      <form @submit.prevent="handleCreateUser" class="space-y-4">
        <div>
          <label class="block text-sm font-medium mb-2">Nom d'utilisateur</label>
          <input 
            v-model="newUser.username" 
            type="text" 
            required 
            class="w-full px-3 py-2 border rounded-md"
          >
        </div>
        <div>
          <label class="block text-sm font-medium mb-2">Email</label>
          <input 
            v-model="newUser.email" 
            type="email" 
            required 
            class="w-full px-3 py-2 border rounded-md"
          >
        </div>
        <button 
          type="submit" 
          :disabled="loading"
          class="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
        >
          {{ loading ? 'Création...' : 'Créer l\'utilisateur' }}
        </button>
      </form>
    </div>

    <!-- Affichage des erreurs -->
    <div v-if="error" class="mb-4 p-4 bg-red-100 text-red-700 rounded-md">
      {{ error }}
    </div>

    <!-- Liste des utilisateurs -->
    <div v-if="loading && users.length === 0" class="text-center py-8">
      Chargement...
    </div>

    <div v-else class="grid gap-4">
      <div 
        v-for="user in users" 
        :key="user.id"
        class="p-4 border rounded-lg flex justify-between items-center"
      >
        <div>
          <h3 class="font-semibold">{{ user.username }}</h3>
          <p class="text-gray-600">{{ user.email }}</p>
          <p class="text-xs text-gray-400">ID: {{ user.id }}</p>
        </div>
        <button 
          @click="handleDeleteUser(user.id)"
          class="px-3 py-1 bg-red-600 text-white rounded hover:bg-red-700"
        >
          Supprimer
        </button>
      </div>
    </div>

    <!-- Pagination -->
    <div class="mt-8 flex justify-center space-x-4">
      <button 
        @click="previousPage"
        :disabled="skip === 0"
        class="px-4 py-2 border rounded disabled:opacity-50"
      >
        Précédent
      </button>
      <button 
        @click="nextPage"
        :disabled="users.length < limit"
        class="px-4 py-2 border rounded disabled:opacity-50"
      >
        Suivant
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
const store = useUsersStore()
const { users, loading, error } = storeToRefs(store)

// Formulaire
const newUser = ref({
  username: '',
  email: ''
})

// Pagination
const skip = ref(0)
const limit = ref(10)

// Actions
const handleCreateUser = async () => {
  try {
    await store.createUser(newUser.value)
    newUser.value = { username: '', email: '' }
  } catch (err) {
    // L'erreur est gérée dans le store
  }
}

const handleDeleteUser = async (userId: string) => {
  if (confirm('Êtes-vous sûr de vouloir supprimer cet utilisateur ?')) {
    await store.deleteUser(userId)
  }
}

const previousPage = () => {
  if (skip.value >= limit.value) {
    skip.value -= limit.value
    store.fetchUsers({ skip: skip.value, limit: limit.value })
  }
}

const nextPage = () => {
  skip.value += limit.value
  store.fetchUsers({ skip: skip.value, limit: limit.value })
}

// Chargement initial
onMounted(() => {
  store.fetchUsers({ skip: skip.value, limit: limit.value })
})
</script>
```

## 🎨 Conseils d'Interface

### Structure recommandée :
1. **Tableau de bord** - Statistiques et aperçu
2. **Liste des utilisateurs** - Avec recherche, filtres, pagination
3. **Formulaire d'ajout** - Modal ou page dédiée
4. **Détails utilisateur** - Page dédiée avec possibilité d'édition
5. **Export de données** - Bouton de téléchargement

### Fonctionnalités UX :
- **Loading states** pour tous les appels API
- **Messages de succès/erreur** avec notifications toast
- **Confirmation** avant suppression
- **Validation en temps réel** des formulaires
- **Pagination** ou scroll infini
- **Recherche et filtres** côté client ou serveur

## 🚀 Commandes de développement

```bash
# Développement
npm run dev

# Build
npm run build

# Preview
npm run preview
```

Cette configuration vous donne une base solide pour créer un frontend Nuxt.js moderne qui interagit parfaitement avec votre API FastAPI ! 🚀