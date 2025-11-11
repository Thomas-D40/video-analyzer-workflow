# 🔧 Activer l'environnement virtuel

## Dans PowerShell (Windows)

```powershell
# Activer l'environnement virtuel
.\venv\Scripts\Activate.ps1
```

Si vous avez une erreur de politique d'exécution, exécutez d'abord :
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## Installer les dépendances dans l'environnement virtuel

Une fois activé, installez les dépendances :

```powershell
python -m pip install -r requirements_minimal.txt
```

## Désactiver l'environnement virtuel

Pour sortir de l'environnement virtuel :

```powershell
deactivate
```

## Créer un nouvel environnement virtuel (si nécessaire)

Si vous voulez créer un nouvel environnement virtuel :

```powershell
# Créer l'environnement
python -m venv venv

# Activer
.\venv\Scripts\Activate.ps1

# Installer les dépendances
python -m pip install -r requirements_minimal.txt
```

