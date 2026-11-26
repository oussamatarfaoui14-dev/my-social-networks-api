# Modèle relationnel

Le script exécutable est [app/schema.sql](../app/schema.sql).
Toutes les tables ont une clé primaire entière id.

~~~mermaid
erDiagram
  users ||--o{ sessions : ouvre
  users ||--o{ group_members : rejoint
  groups ||--|{ group_members : contient
  groups ||--o{ events : accueille
  users ||--o{ event_members : participe
  events ||--|{ event_members : reunit
  groups |o--o{ threads : possede
  events |o--o{ threads : possede
  threads ||--o{ messages : contient
  users ||--o{ messages : ecrit
  messages ||--o{ message_comments : recoit
  events ||--o{ albums : possede
  albums ||--o{ photos : contient
  photos ||--o{ photo_comments : recoit
  events ||--o{ polls : propose
  polls ||--|{ questions : contient
  questions ||--|{ options : propose
  questions ||--o{ answers : recoit
  options ||--o{ answers : selectionnee
  users ||--o{ answers : vote
  events ||--o{ ticket_types : propose
  ticket_types ||--o{ tickets : vend
  events ||--o{ shopping_items : rassemble
  events ||--o{ carpools : organise
~~~

Le diagramme simplifie les auteurs des photos, albums, commentaires et
contributions : ils référencent tous users via author_id.
Un fil possède **exactement un** des deux parents possibles.

| Table | Champs et rôle |
|---|---|
| users | email unique, prénom, nom, password_hash, biographie, avatar, date |
| sessions | user_id, empreinte du jeton unique, expiration Unix |
| groups | nom, description, icône, couverture, visibilité, permissions |
| group_members | group_id, user_id, rôle admin/member ; paire unique |
| events | configuration, dates UTC, groupe éventuel, état, options |
| event_members | event_id, user_id, rôle, statut invited/accepted |
| threads | titre, group_id OU event_id ; contrainte XOR |
| messages | thread_id, author_id, contenu, date |
| message_comments | message_id, author_id, contenu, date |
| albums | event_id, author_id, nom, description |
| photos | album_id, author_id, URL, légende |
| photo_comments | photo_id, author_id, contenu, date |
| polls | event_id, titre, fermé/ouvert |
| questions | poll_id, texte |
| options | question_id, texte ; texte unique dans une question |
| answers | question_id, user_id, option_id ; une réponse par question/utilisateur |
| ticket_types | event_id, nom, montant en centimes, quantité |
| tickets | event_id, ticket_type_id, identité/adresse/email, date, montant, empreinte du secret |
| shopping_items | event_id, author_id, nom, clé normalisée, quantité, arrivée |
| carpools | event_id, author_id, lieu/heure de départ, prix, places, détour maximal |

## Invariants

- Administrateurs membres ; organisateurs participants acceptés.
- Dernier responsable protégé dans la transaction d'écriture.
- Un fil référence un seul parent : contrainte CHECK.
- Fin postérieure au début : modèle et contrainte CHECK.
- Vote lié à une option de la même question : clé étrangère composite.
- Billet lié à un tarif du même événement : clé étrangère composite.
- Billet unique par email et identité déclarée pour un événement : contraintes UNIQUE.
- Stock disponible : quantité moins le nombre de billets, sans compteur dupliqué.
- Nom de contribution normalisé unique par événement.
- Au moins un fil par groupe ; au moins une question par sondage et deux options
  par question. Les opérations sur ces ensembles sont atomiques.

La version initiale est PRAGMA user_version = 1. Les évolutions ultérieures
nécessiteront des migrations explicites ; ce n'est pas un moteur de migration.
