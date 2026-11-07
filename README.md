# Dell C1760nw – Intégration Home Assistant

Intégration personnalisée pour surveiller l'imprimante laser couleur **Dell C1760nw** depuis Home Assistant.

## Fonctionnalités

- Collecte SNMP basée sur la Printer-MIB (RFC 3805), avec découverte des lignes de consommables.
- Lecture complémentaire des informations de statut et d'alerte depuis l'interface EWS.
- Mesures de niveau en pourcentage uniquement lorsqu'une valeur numérique réelle et son unité/capacité sont disponibles.
- États textuels des cartouches exposés séparément des mesures en pourcentage.
- Compteur de pages, statut de l'imprimante et alertes matérielles lorsqu'ils sont fournis par l'appareil.
- Disponibilité réseau gérée par le coordinateur Home Assistant : une panne de communication ne transforme pas l'imprimante en état « veille » et ne modifie pas les dernières données valides.

## Installation

1. Installer l'intégration via HACS comme dépôt personnalisé de type **Integration**, ou copier `custom_components/dell_c1760nw` dans le dossier `custom_components` de Home Assistant.
2. Redémarrer Home Assistant.
3. Ajouter **Dell C1760nw** depuis *Paramètres → Appareils et services → Ajouter une intégration*.
4. Renseigner l'adresse IP, le port SNMP (161 par défaut) et la communauté SNMP.

SNMP doit être activé et accessible sur l'imprimante. Les valeurs non prises en charge par le modèle ou non exposées par son agent SNMP/EWS restent indisponibles.

## Toners : mesure et état

Les capteurs `Toner Noir/Cyan/Magenta/Jaune` représentent uniquement une mesure numérique exploitable. Une réponse SNMP spéciale (valeur négative), une capacité absente ou un texte EWS comme « OK » ou « Remplacer bientôt » ne sont **pas** convertis en pourcentage estimé. Les textes EWS sont publiés dans les capteurs distincts `État toner …`.

La Printer-MIB est interrogée par découverte des entrées de `prtMarkerSuppliesTable`; les index de lignes ne sont pas supposés correspondre à une couleur fixe. La disponibilité des colonnes et la façon dont l'agent Dell les remplit peuvent varier selon le firmware.

## Développement et tests

Les tests unitaires de normalisation et de parsing EWS se trouvent dans `tests/` et peuvent être exécutés avec `pytest`.
