🍽️ Projet de Dispatching NoSQL (Uber Eats) – Redis vs MongoDB

Ce projet universitaire compare deux architectures complètes d’un système de dispatching “type Uber Eats”, l’une basée exclusivement sur Redis, l’autre sur MongoDB.

Chaque architecture simule un écosystème multi-acteurs en interaction :
	•	🧑‍💻 Client : Passe une commande interactive
	•	🍽️ Restaurant : Reçoit la commande et prépare les plats
	•	🛵 Livreur : Met à jour sa position GPS et attend des missions
	•	🤖 Dispatcher : Assigne chaque commande au livreur disponible le plus proche

La logique de dispatching est géo-spatiale :
	•	Redis → GEOSEARCH
	•	MongoDB → $geoNear

Les deux systèmes fonctionnent indépendamment et gèrent plusieurs livreurs en parallèle.

⸻

⚙️ 1. Prérequis & Installation

🔁 Cloner le dépôt

git clone [URL_DE_VOTRE_DEPOT]
cd [NOM_DU_DOSSIER]

📦 Installer les dépendances

Assurez-vous d’avoir Python 3.10+ installé.

# (Optionnel) Créer un environnement virtuel
python -m venv venv
source venv/bin/activate      # macOS/Linux
# venv\Scripts\activate       # Windows

# Installer les paquets requis
pip install -r requirements.txt

🔐 Configuration du fichier .env

Créez un fichier .env à la racine du projet et ajoutez :

# --- MongoDB Atlas ---
MONGO_URI_ATLAS="mongodb+srv://user:pass@cluster.mongodb.net/..."
MONGODB_URI="mongodb+srv://user:pass@cluster.mongodb.net/..."
MONGO_DB="ubereats_poc"

# --- Redis (local) ---
REDIS_HOST="127.0.0.1"
REDIS_PORT="6379"


⸻

🚀 2. Lancer l’Architecture “Full Redis”

Cette architecture utilise Redis pour tout :
Pub/Sub, géo-localisation (GEOADD, GEOSEARCH), gestion des états, etc.

Vous aurez besoin de 4 terminaux dans le dossier du projet.

⸻

🧩 Terminal 1 : Restaurant

python restaurant_worker.py

Sortie attendue :

🍕 Restaurant R55 en attente de commandes sur 'orders:restaurant:R55'...


⸻

🛵 Terminal 2 : Livreur(s)

Vous pouvez lancer plusieurs livreurs.

python courier_worker_redis.py

Sortie attendue :

Livreur L1234 démarré.
[L1234] En écoute de jobs sur 'notify:L1234'
[L1234] Position mise à jour (disponible).


⸻

🤖 Terminal 3 : Dispatcher (Cerveau)

python dispatcher_worker_redis.py

Sortie attendue :

🤖 Dispatcher Uber Eats (Redis) démarré. En attente sur 'orders:dispatch'...


⸻

🧑‍💻 Terminal 4 : Client

python create_order_interactive_redis.py

Vous verrez les autres terminaux réagir en temps réel.

⸻

🗂️ 3. Lancer l’Architecture “Full MongoDB”

Cette architecture utilise MongoDB comme source de vérité, avec Change Streams pour la communication.

Elle nécessite également 4 terminaux + un script de préparation.

⸻

🛠️ Étape 0 : Préparation de la base (à faire une seule fois)

python seed_restaurants_with_menu.py


⸻

🍽️ Terminal 1 : Restaurant

python restaurant_worker_mongo.py


⸻

🛵 Terminal 2 : Livreur(s)

python courier_worker_mongo.py


⸻

🤖 Terminal 3 : Dispatcher

python dispatcher_worker_mongo.py


⸻

🧑‍💻 Terminal 4 : Client

python create_order_interactive_mongo.py

Un INSERT_ONE déclenche automatiquement les autres services via Change Streams.

⸻

📊 4. Scripts Complémentaires

✔️ Tests unitaires Redis

python test_redis_client.py

📈 Analyse MongoDB (Chiffre d’affaires)

python analytics_mongo.py


⸻

🎯 Conclusion

Ce projet met en parallèle deux approches diamétralement opposées pour un système de dispatching en temps réel :
	•	Redis → rapidité, simplicité, faible latence
	•	MongoDB → robustesse, persistance, puissance de requêtage

Il illustre comment chaque technologie peut être exploitée pour répondre à des problématiques de géo-localisation et de coordination multi-acteurs.

�
