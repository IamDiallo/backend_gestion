# WaKiLiX - Gestion Commerciale Backend

Ce backend Django REST Framework fournit une API pour le système de gestion commerciale de WaKiLiX.

## Configuration requise

- Python 3.9+
- PostgreSQL 12+
- Django 4.2+
- Django REST Framework 3.14+

## Déploiement en production

### Checklist de pré-déploiement

1. Configuration
- [ ] Vérifier toutes les variables dans `.env`
- [ ] Désactiver DEBUG
- [ ] Configurer ALLOWED_HOSTS
- [ ] Configurer CORS_ALLOWED_ORIGINS
- [ ] Générer un nouveau SECRET_KEY

## Installation

1. Créer un environnement virtuel Python (recommandé)
```bash
python -m venv venv
source venv/bin/activate  # Sur Windows: venv\Scripts\activate
```

2. Installer les dépendances
```bash
pip install -r requirements.txt
```

3. Configurer la base de données PostgreSQL
   - Créer une base de données PostgreSQL nommée `WaKiLiX_db`
   - Configurer les variables d'environnement dans le fichier `.env`

4. Appliquer les migrations
```bash
python manage.py migrate
```

5. Créer un superutilisateur
```bash
python manage.py createsuperuser
```

6. Démarrer le serveur de développement
```bash
python manage.py runserver
```

## Structure du projet

Le backend est organisé selon les modules suivants:

- **Utilisateurs**: Gestion des profils et des rôles
- **Paramètres**: Configuration des catégories, devises, méthodes de paiement, etc.
- **Produits**: Gestion des produits et des catégories
- **Tiers**: Clients, fournisseurs et personnel
- **Stocks**: Approvisionnements, transferts, inventaires
- **Ventes**: Commandes et factures
- **Production**: Suivi de la production
- **Trésorerie**: Dépenses, règlements, virements

## API Endpoints

- `/api/products/` - Gestion des produits
- `/api/clients/` - Gestion des clients
- `/api/suppliers/` - Gestion des fournisseurs
- `/api/sales/` - Gestion des ventes
- `/api/orders/` - Gestion des commandes

L'interface d'administration est disponible à l'adresse `/admin/`.

## Finalisation

Après avoir effectué ces étapes, n'oubliez pas de :

- Exécuter les migrations pour mettre à jour la base de données :
  ```bash
  python manage.py migrate
  ```

- Si vous avez mis à jour les modèles, vous devrez peut-être générer de nouvelles migrations :
  ```bash
  python manage.py makemigrations gestion_api
  python manage.py migrate
  ```

- Pour appliquer les changements de relation entre utilisateurs, groupes et zones :
  ```bash
  python manage.py migrate gestion_api 0014_userprofile_model_update
  ```

- Démarrer le serveur Django pour tester les nouvelles fonctionnalités :
  ```bash
  python manage.py runserver
  ```

Si vous avez besoin d'aide pour une étape spécifique ou si vous souhaitez que je vous aide à écrire du code pour l'une de ces étapes, faites-le moi savoir !
