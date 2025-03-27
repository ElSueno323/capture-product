#!/bin/bash

# Vérification des privilèges root
if [ "$(id -u)" != "0" ]; then
   echo "Ce script doit être exécuté en tant que root" 1>&2
   exit 1
fi

# Installation des dépendances système
apt-get update
apt-get install -y python3-full python3-pip python3-venv python3-opencv

# Création du répertoire de l'application
APP_DIR="/opt/captureProductUi"
mkdir -p $APP_DIR

# Copie des fichiers de l'application
cp -r app.py templates requirements.txt $APP_DIR/

# Création et activation de l'environnement virtuel
python3 -m venv $APP_DIR/venv
. $APP_DIR/venv/bin/activate

# Installation des dépendances Python dans l'environnement virtuel
$APP_DIR/venv/bin/pip install --no-cache-dir -r $APP_DIR/requirements.txt

# Création du fichier de service systemd
cat > /etc/systemd/system/captureproduct.service << EOL
[Unit]
Description=Capture Product UI Service
After=network.target

[Service]
User=root
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/venv/bin"
ExecStart=$APP_DIR/venv/bin/python app.py
Restart=always

[Install]
WantedBy=multi-user.target
EOL

# Activation et démarrage du service
#systemctl daemon-reload
#systemctl enable captureproduct
#systemctl start captureproduct

echo "Installation terminée. Le service est maintenant actif et configuré pour démarrer au boot."
#echo "Vous pouvez vérifier le status avec: systemctl status captureproduct"