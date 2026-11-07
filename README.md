# Dell C1760nw - Home Assistant Integration

![HACS Custom Repository](https://img.shields.io/badge/HACS-Custom-orange.svg)
![GitHub release](https://img.shields.io/github/v/release/mrzac/hass-dell-c1760nw)

Intégration personnalisée Home Assistant moderne pour l'imprimante laser couleur **Dell C1760nw**.

## 🌟 Fonctionnalités

- ⚙️ **Configuration UI (`Config Flow`)** : Ajout facile sans toucher à `configuration.yaml`.
- 🔍 **Découverte automatique (`Zeroconf / mDNS`)** : Détection réseau automatique.
- ⚡ **Acquisition optimisée (`DataUpdateCoordinator`)** : Polling SNMP centralisé et efficace.
- 🎨 **Capteurs complets** : Niveaux de toner (Noir, Cyan, Magenta, Jaune), statut et compteur de pages.
- 🔄 **Bouton d'action** : Bouton pour forcer le rafraîchissement manuel des états.
- 🌍 **Internationalisation** : Support du Français et de l'Anglais.
- 🤖 **CI/CD** : Workflows d'intégration continue validés via Hassfest et HACS Action.

## 📦 Installation via HACS

1. Ouvrez HACS dans Home Assistant.
2. Cliquez sur les 3 points en haut à droite > **Dépôts personnalisés**.
3. Ajoutez le lien de votre dépôt GitHub et sélectionnez la catégorie **Intégration**.
4. Cliquez sur **Installer**.
5. Redémarrez Home Assistant.

## 🔧 Configuration

1. Allez dans **Paramètres** > **Appareils et services**.
2. Cliquez sur **Ajouter une intégration** et cherchez `Dell C1760nw`.
3. Entrez l'adresse IP de votre imprimante.
