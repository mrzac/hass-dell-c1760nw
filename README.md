# Dell C1760nw - Home Assistant Integration (v0.2.0)

![HACS Custom Repository](https://img.shields.io/badge/HACS-Custom-orange.svg)
![GitHub release](https://img.shields.io/github/v/release/mrzac/hass-dell-c1760nw)

Intégration personnalisée Home Assistant moderne et optimisée pour l'imprimante laser couleur **Dell C1760nw**.

## 🌟 Fonctionnalités v0.2.0

- ⚙️ **Configuration UI (`Config Flow`)** : Ajout facile et test de connexion réseau.
- 🔍 **Découverte automatique (`Zeroconf / mDNS`)** : Détection automatique des imprimantes sur le réseau.
- ⚡ **Acquisition hybride SNMP & HTTP EWS** : Résilience accrue et fallback automatique.
- 🎨 **Calcul Toner Sécurisé** : Correction du bug d'inversion des couleurs Cyan, Magenta, Jaune, Noir et gestion des valeurs MIB négatives.
- 🔋 **Gestion intelligente du mode veille** : Conservation des états pendant la veille (évite l'état *Unavailable*).
- ⏱️ **Polling dynamique** : Intervalle adapté selon l'activité de l'imprimante (30s en impression, 60s standard, 300s en veille).
- 📊 **Nouvelles entités & Capteurs binaires** :
  - **Sensors** : Tambour d'imagerie, Bac récepteur toner, Compteurs mono/couleur/total, Adresse IP, Version Firmware, N° de série.
  - **Binary Sensors** : Bourrage papier, Capot ouvert, Bac à papier vide, Toner non officiel.
  - **Buttons** : Rafraîchissement manuel et impression de page de test.

## 📦 Installation via HACS

1. Ouvrez HACS dans Home Assistant.
2. Cliquez sur les 3 points en haut à droite > **Dépôts personnalisés**.
3. Ajoutez le dépôt et sélectionnez la catégorie **Intégration**.
4. Cliquez sur **Installer** puis redémarrez Home Assistant.
