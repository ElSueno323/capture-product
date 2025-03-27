# Interface de Capture de Produits

Cette application web permet de capturer des images de produits via une interface utilisateur. Elle est conçue pour fonctionner sur des systèmes Linux (Ubuntu) et utilise Python avec Flask pour le backend.

## Prérequis

- Python 3.x
- pip 
- OpenCV
- Système d'exploitation Ubuntu 

## Installation

1. Exécutez le script d'installation en tant que root :
   ```bash
   sudo ./install.sh
   ```

Le script d'installation va :
- Installer les dépendances système nécessaires
- Créer un environnement virtuel Python
- Installer les dépendances Python requises
- Configurer le service systemd
- Démarrer l'application

## Configuration

L'application sera installée dans `/opt/captureProductUi/` avec la structure suivante :
- `app.py` : Application principale
- `templates/` : Fichiers de template HTML
- `venv/` : Environnement virtuel Python

Le service systemd sera configuré pour démarrer automatiquement au démarrage du système.

## Utilisation

### Démarrage manuel

Si vous devez redémarrer le service manuellement, utilisez le script start.sh :
```bash
sudo ./start.sh
```

### Commandes de service

Vérifier l'état du service :
```bash
systemctl status captureproduct
```

Arrêter le service :
```bash
systemctl stop captureproduct
```

Redémarrer le service :
```bash
systemctl restart captureproduct
```

### Accès à l'interface

Une fois l'application démarrée, accédez à l'interface via votre navigateur web :
```
http://localhost:5000
```

## Support

Pour toute question ou problème, veuillez créer une issue dans le dépôt du projet.