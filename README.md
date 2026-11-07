# Dell C1760nw pour Home Assistant

Intégration dédiée (SNMP v2c, aucune dépendance externe), basée sur un relevé SNMP réel de l'imprimante.

## Entités
- 4 toners en % (`sensor.dell_c1760nw_toner_cyan|magenta|yellow|black`), avec attributs `pages_restantes` et `capacite_pages`
- Compteur de pages total, pages noir, pages couleur
- État (Prêt / Impression / ...) + message de l'afficheur
- Alerte (ex. « Replace the Cyan Cartridge soon. », attribut `code` = 093-425)
- Capot arrière (ouvert / fermé)
- Appareil : numéro de série et firmware (Net / Engine)

## Installation
1. Copier `custom_components/dell_c1760nw` dans `/config/custom_components/` (ou dépôt personnalisé HACS).
2. Redémarrer Home Assistant.
3. Paramètres → Appareils et services → Ajouter une intégration → « Dell C1760nw ».
4. IP de l'imprimante, communauté `public`, port 161.

Exemples : `examples/lovelace_card.yaml`, `examples/automations.yaml`.

## Calcul des toners
`niveau (43.11.1.1.9.1.N) / capacité (43.11.1.1.8.1.N) × 100`. L'imprimante exprime ces valeurs en pages : cyan 105/700 = 15 %.
