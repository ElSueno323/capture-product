#!/bin/bash

# Vérification des privilèges root
if [ "$(id -u)" != "0" ]; then
   echo "Ce script doit être exécuté en tant que root" 1>&2
   exit 1
fi

# Installation des dépendances nécessaires si non présentes
apt-get update
apt-get install -y chromium-browser xdotool

# Démarrage du service backend
systemctl daemon-reload
systemctl enable captureproduct
systemctl start captureproduct

# Fonction pour lancer Chromium en mode kiosk
launch_chromium() {
    # Attendre que le service soit complètement démarré
    sleep 5
    
    # Lancer Chromium en mode kiosk
    chromium-browser --kiosk --noerrdialogs --disable-translate --no-first-run \
                    --disable-infobars --disable-suggestions-service \
                    --disable-save-password-bubble --disable-session-crashed-bubble \
                    http://localhost:5000 &
    
    # Attendre que Chromium soit lancé
    sleep 2
    
    # Forcer le focus sur la fenêtre Chromium
    xdotool search --onlyvisible --class "chromium" windowactivate
}

# Boucle de surveillance pour relancer Chromium si fermé
while true; do
    if ! pgrep -f "chromium-browser.*kiosk" > /dev/null; then
        launch_chromium
    fi
    sleep 5
done