# Voyage

Un petit voyage contemplatif, à relancer de temps en temps dans la journée.

À chaque lancement : un faux chargement de durée variable, une courte étape racontée, et la progression vers la destination avance de quelques pourcents. Pas de défi, pas d'échec, pas de combat. Juste le trajet.

```
 Étape 15  -  12:51

  Midi approche. Des cairns bordent le chemin, chacun posé par un voyageur
  passé. L'air est vif et sent la fin de l'été. L'eau chante sur les galets,
  sans interruption. On ramasse une pomme encore tiède.

                ~
  =  = =   = .......
    =    ... .  ~ ~~.~
   ....  .  .    ~~ .... n
  o =  ..= =            @
    = = =  = ~      ~    n
            ~ ~    ~       n
       = ===  ~    ~  n n n
   ==       ~  ~ ~~       nn

  [===============-------------------------]  38 %
  Vallée des cairns
```

## Installation

Il faut Python 3.8 ou plus récent. Aucune dépendance : le script n'utilise que la bibliothèque standard.

```bash
git clone https://github.com/<votre-compte>/voyage.git
cd voyage
python voyage.py
```

Sous Linux et macOS, utilisez `python3` si `python` n'existe pas.

## Utilisation

Au premier lancement, on choisit :

- **l'univers** : fantasy ou réaliste (d'autres peuvent s'ajouter, voir plus bas) ;
- **la durée** : trajet quotidien (~8 lancements), randonnée (~20) ou voyage par étapes (~45).

Ensuite, il suffit de relancer `python voyage.py` quand l'envie vient. La durée du chargement varie : le plus souvent quelques secondes, parfois une minute, rarement plusieurs minutes (la « longue marche »).

| Option      | Effet                                                                         |
| ----------- | ----------------------------------------------------------------------------- |
| `--journal` | affiche le journal complet du voyage en cours                                 |
| `--bilan`   | affiche un résumé : départ, destination, régions traversées, souvenirs        |
| `--carte`   | affiche la carte et la progression, sans avancer                              |
| `--export`  | écrit le bilan et le journal dans un fichier texte                            |
| `--nouveau` | archive le voyage en cours et en commence un autre                            |
| `--discret` | faux messages techniques pendant le chargement, écran effacé après une touche |
| `--rapide`  | chargement d'une seconde (pour tester)                                        |

À l'arrivée, le bilan s'affiche et le journal complet est écrit automatiquement dans un fichier texte.

## Où sont mes données ?

La sauvegarde (`etat.json`), les journaux exportés et les voyages archivés sont dans :

| Système | Dossier                                                      |
| ------- | ------------------------------------------------------------ |
| Windows | `%LOCALAPPDATA%\voyage`                                      |
| macOS   | `~/Library/Application Support/voyage`                       |
| Linux   | `$XDG_DATA_HOME/voyage` (par défaut `~/.local/share/voyage`) |

La variable d'environnement `VOYAGE_HOME` permet de choisir un autre dossier.

## Comment ça marche

- Chaque voyage a une **graine** : la destination, l'ordre des régions et la carte en découlent, donc tout reste cohérent d'un lancement à l'autre.
- Le récit de chaque étape est assemblé à partir des tableaux de données de l'univers : lieu, météo, ambiance, parfois une rencontre ou un objet ramassé. Le moment de la journée dépend de l'heure réelle.
- La carte est un chemin sinueux qui se dévoile à mesure que l'on avance, entouré du décor de la région traversée.

## Ajouter un univers

Un univers est un simple fichier JSON : **aucun code à écrire**. Copiez `data/fantasy.json`, modifiez les textes, et déposez-le :

- dans `data/` (pour le proposer au dépôt) ;
- ou dans le sous-dossier `univers/` du dossier de données ci-dessus (pour un usage personnel).

Il apparaît alors dans le menu du premier lancement. Le nom du fichier sert d'identifiant.

```jsonc
{
  "nom": "Mon univers",                    // affiché dans le menu
  "departs": ["..."],                      // « Départ : ... »
  "destinations": ["..."],                 // « Destination : ... »
  "arrivee": "Phrase finale.",
  "chargement": ["Le sentier se précise..."],   // messages du faux chargement
  "meteo": ["Phrase complète."],
  "regions": [                             // au moins 6
    {
      "nom": "Forêt ancienne",
      "glyphe": "\"",                      // 1 caractère, différent de . o @ X
      "couleur": "vert",                   // voir ci-dessous
      "entree": "Phrase quand on entre dans la région.",
      "lieux": ["Phrase complète."],
      "ambiance": ["Phrase complète."],
      "rencontres": ["Phrase complète."],
      "trouvailles": ["une plume bleue"],   // complète « On ramasse ... »
      "meteo": ["Phrase complète."]         // optionnel, pour une météo plus précise par région
    }
  ]
}
```

Couleurs possibles : `gris`, `gris_clair`, `blanc`, `vert`, `cyan`, `cyan_clair`, `jaune`, `magenta`, `bleu`, `rouge`.

Quelques conseils d'écriture : phrases complètes (majuscule, point final), sans pronom personnel (« on » ou tournure impersonnelle), et plusieurs variantes par liste pour que les étapes ne se répètent pas. Les « trouvailles » sont des groupes nominaux, sans point.

Les fichiers invalides sont ignorés avec un message qui indique ce qui manque.

### Tests

```bash
python -m unittest discover -s tests -v
```

Ils vérifient que tous les fichiers de `data/` sont bien formés et que la carte est reproductible.

## Licence

MIT, voir [LICENSE](LICENSE).
