# Dell C1760nw – Intégration Home Assistant

Intégration personnalisée pour surveiller l'imprimante laser couleur **Dell C1760nw** depuis Home Assistant.

## Fonctionnalités

- Collecte **SNMP v2c** (Printer-MIB, RFC 3805) : statut, consommables, alertes, compteurs.
- Consommables découverts **par leur description** (« Cartouche cyan », …), jamais par index fixe.
- Niveaux de toner en % uniquement quand la mesure est réelle (valeur ÷ capacité). Les valeurs spéciales SNMP (-1/-2/-3) ne deviennent jamais un pourcentage.
- Alerte courante et code d'erreur Dell (ex. `093-425`) lus dans `prtAlertTable`.
- Bourrage, capot ouvert et bac vide lus dans `hrPrinterDetectedErrorState` (bits standard) et dans les alertes.
- Compteurs de pages total / noir & blanc / couleur, numéro de série, firmware, adresse MAC.
- La page EWS (`/status/status.htm`) n'est utilisée que **de secours** si SNMP ne répond pas.
- Une panne réseau rend les entités indisponibles ; elle ne fabrique pas d'état « veille ».

## Installation

1. Installer via HACS (dépôt personnalisé, type **Integration**) ou copier `custom_components/dell_c1760nw` dans le dossier `custom_components` de Home Assistant.
2. Redémarrer Home Assistant.
3. *Paramètres → Appareils et services → Ajouter une intégration → Dell C1760nw*.
4. Renseigner l'adresse IP, le port SNMP (161) et la communauté (`public` par défaut).

SNMP doit être activé sur l'imprimante. La saisie est **testée en SNMP** : un port ou une communauté erronés sont refusés dès la configuration. Le numéro de série sert d'identifiant : si l'IP change (DHCP), l'entrée est mise à jour au lieu d'être dupliquée.

## Entités

Les identifiants suivent le nom de l'appareil, par exemple :
`sensor.dell_c1760nw_toner_noir`, `…_toner_cyan`, `…_toner_magenta`, `…_toner_jaune`,
`sensor.dell_c1760nw_statut`, `sensor.dell_c1760nw_alerte_actuelle`,
`binary_sensor.dell_c1760nw_bourrage_papier`, `button.dell_c1760nw_rafraichir_l_etat`.

Les entités déjà créées par une ancienne version gardent leur identifiant d'origine (modifiable dans l'interface).

## Ce que ce modèle n'expose pas

Le `snmpwalk` d'une C1760nw ne publie ni tambour ni bac de toner usagé dans `prtMarkerSuppliesTable` : les anciens capteurs « Tambour d'imagerie », « Bac de toner usagé » et « Toner non officiel » ont donc été retirés (ils restaient toujours vides). Le binaire « Bac récepteur toner plein » s'appuie uniquement sur les alertes standard (codes 1107/1109).

## Développement et tests

```bash
pip install pytest
pytest
```

Les tests des modules purs (`api/`, `models`) tournent sans Home Assistant. `tests/test_snmp_data.py` rejoue les valeurs d'un vrai `snmpwalk` de C1760nw.
