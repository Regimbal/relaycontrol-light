✅ 1. Où installer ton projet dans OpenWrt
Recommandé :

/usr/share/relaycontrol-light/

    /usr/share/ est l’emplacement standard pour les fichiers applicatifs,

    évite /root/, /home/ ou /tmp/ pour les scripts persistants.

Tu peux copier ton projet comme suit :

scp -r relaycontrol-light/ root@openwrt:/usr/share/relaycontrol-light/

✅ 2. Créer un script shell de lancement

Dans /usr/share/relaycontrol-light/start.sh :

#!/bin/sh
. /etc/profile
cd /usr/share/relaycontrol-light/
. .venv/bin/activate
exec python3 src/main.py

Rends-le exécutable :

chmod +x /usr/share/relaycontrol-light/start.sh

✅ 3. Créer un service procd

Fichier à créer : /etc/init.d/relaycontrol

#!/bin/sh /etc/rc.common

START=99
STOP=10

USE_PROCD=1

start_service() {
    procd_open_instance
    procd_set_param command /usr/share/relaycontrol-light/start.sh
    procd_set_param respawn
    procd_close_instance
}

Rends-le exécutable :

chmod +x /etc/init.d/relaycontrol

✅ 4. Activer et démarrer le service

/etc/init.d/relaycontrol enable
/etc/init.d/relaycontrol start

✅ 5. Vérifier que ça tourne

logread -f

Et/ou :

ps | grep main.py