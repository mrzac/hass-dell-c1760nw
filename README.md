# Dell C1760nw - Home Assistant Integration (v0.2.1)

Intégration personnalisée Home Assistant pour l'imprimante laser couleur **Dell C1760nw**, compatible avec le dépôt **Marlboro62/printers**.

## 🌟 Correction du problème de synchronisation des toners

- **Extraction Réelle EWS/SNMP** : Supression totale des valeurs fictives (mock) `80, 55, 40, 90`.
- **Parser de texte EWS** : Interprétation automatique des statuts textuels de la page Web EWS (ex. `"Cartouche cyan Niveau : Remplacer bientôt"` -> traduit en alerte et pourcentage réel ~15%).
- **Compatibilité Carte Marlboro62/printers** : Entités structurées pour être reconnues directement par la carte Lovelace `Marlboro62/printers` / `ha-printer-card`.
