# Correspondance avec le cahier des charges

Source : document fourni « My Social Networks API v2.0.0 », quatre pages.
Les sections ci-dessous sont celles du sujet ; les choix complémentaires sont
identifiés dans CONCEPTION.md.

| Exigence | Réalisation | Vérification |
|---|---|---|
| 0.1 API fiable, structurée, documentée | Routeurs métier, validations, transactions, erreurs HTTP, OpenAPI | Suite pytest, contrats des réponses |
| 0.1 Endpoints spécifiques | Invitations, participants, partage, résultats de sondage, disponibilité des billets | ENDPOINTS.md, parcours Postman |
| 0.1 Documentation Postman avec URL, fonctions et retours | Collection de référence de 93 opérations avec exemples et contrats de sortie | Export automatique vérifié |
| 0.1 Dépôt GitHub/GitLab | Sources, tests, documentation, Docker et CI dans le dépôt | Lien remis avec le projet |
| 0.1 URL de documentation Postman publiée | Collection prête ; publication conditionnée à la connexion Postman | PUBLICATION.md |
| 1.1 Configuration d'événement | Nom, description, début/fin, lieu, couverture, public/privé, organisateurs et participants | Modèles EventCreate/EventInput, tests CRUD |
| 1.1 Parcours en trois étapes | Configuration, options, publication | Test du brouillon et parcours complet |
| 1.2 Groupes public/privé/secret | Visibilité et contrôle d'accès | Tests des trois valeurs |
| 1.2 Invitation de tous les membres | invite_all_group_members à la création ; POST invite-group ensuite | Invitation en masse idempotente |
| 1.2 Partage social d'événement de groupe public | GET share : URL, liens X et LinkedIn | Refus hors groupe public/événement public publié |
| 1.2 Fil de discussion du groupe | Fil Général automatique, maintien d'au moins un fil | Test de suppression du dernier fil |
| 1.2 Paramètres du groupe | Nom, description, icône, couverture, type, permissions | CRUD et tests d'interdiction |
| 2.1 Utilisateurs CRUDS | Création, liste/recherche, profil, modification, suppression | Tests de cycle de vie |
| 2.1 Email unique | Normalisation et contrainte UNIQUE sans distinction de casse | Doublon avec majuscules refusé |
| 2.2 Événements CRUDS | CRUD/recherche, plusieurs participants et organisateurs | Création, publication, droits |
| 2.2 Au moins un organisateur | Créateur organisateur, transfert, dernier responsable protégé | Retrait, rétrogradation, suppression de compte |
| 2.3 Groupes CRUDS | CRUD/recherche, plusieurs membres et administrateurs | Tests des trois visibilités |
| 2.3 Au moins un membre et administrateur | Administrateurs également membres ; dernier administrateur protégé | Tests de responsabilité minimale |
| 2.4 Fil rattaché à un seul parent | XOR groupe/événement dans le modèle et en base | Deux parents ou aucun : 422 |
| 2.4 Messages et commentaires CRUDS | Sous-ressources messages/commentaires, auteur et droits du parent | Tests auteur, responsable, tiers |
| 2.5 Albums et photos CRUDS | Un album associé à un événement ; zéro ou plusieurs photos | Tests CRUD et accès participant |
| 2.5 Commentaires sur photos | CRUD/recherche réservé aux participants confirmés | Tests droits et suppression |
| 2.6 Sondages CRUDS | Création par organisateur, plusieurs sondages par événement | Refus pour simple participant |
| 2.6 Questions et options | Au moins une question et deux options distinctes | Tests de validation |
| 2.6 Une option par question/participant | Réponse complète atomique, unicité question/utilisateur, option liée à la bonne question | Votes incomplets, doublons, options étrangères refusés |
| 2.7 Billetterie publique facultative | Option réservée aux événements publics ; plusieurs tarifs | Test événement privé et options |
| 2.7 Nom, montant, stock limité | Nom, amount_cents, quantity ; sold/remaining calculés | Achat concurrent du dernier billet |
| 2.7 Un billet par personne extérieure | Sans compte ; unicité email et identité déclarée pour l'événement | Doublons sur deux tarifs refusés |
| 2.7 Données du billet acheté | Type, nom, prénom, adresse complète, date, prix conservé | Cycle complet, confidentialité |
| 2.8 Shopping list activable CRUDS | Nom, quantité, arrivée, auteur, événement | Tests activation, dates, unicité |
| 2.8 Objet unique par événement | Nom normalisé Unicode, espaces et casse ; UNIQUE par événement | Doublon « Eau minérale »/« EAU MINÉRALE » refusé |
| 3 Covoiturage bonus CRUDS | Départ, horaire, prix, places, détour maximal en minutes | CRUD, activation, valeurs positives, horaires |

CRUDS est interprété comme **Create, Read, Update, Delete, Search**.
Toutes les collections exposent une liste paginée avec recherche.
Les questions/options sont créées et remplacées dans l'agrégat sondage afin de
ne jamais laisser un sondage sans question ni une question sans options.
