# Projet-Uber-eats
Projet de Dispatching NoSQL (Uber Eats) - Redis vs. MongoDBCe dépôt contient le code source d'un projet universitaire comparant deux implémentations d'un système de dispatching de livraison (type "Uber Eats"). L'objectif est de comparer une approche "full Redis" et une approche "full MongoDB".Les deux systèmes sont totalement indépendants et gèrent un écosystème concurrent multi-acteurs :Client : Passe une commande interactive.Restaurant : Reçoit la commande et la prépare.Livreur : Met à jour sa position GPS et attend des missions.Dispatcher : Assigne les nouvelles commandes au livreur disponible le plus proche.La logique de dispatching est géo-spatiale (GEOSEARCH dans Redis, $geoNear dans MongoDB) et capable de gérer plusieurs livreurs en parallèle.⚙️ 1. Prérequis et InstallationAvant de lancer les applications, vous devez configurer votre environnement.a. Cloner le dépôtgit clone [URL_DE_VOTRE_DEPOT]
cd [NOM_DU_DOSSIER]
b. Installer les dépendancesAssurez-vous d'avoir Python 3.10+ installé.# Créez un environnement virtuel (recommandé)
python -m venv venv
source venv/bin/activate  # Sur macOS/Linux
# venv\Scripts\activate   # Sur Windows

# Installez les paquets requis
pip install -r requirements.txt
c. Fichier d'Environnement (.env)Créez un fichier nommé .env à la racine du projet. Il doit contenir vos clés de connexion.Copiez ce modèle dans votre fichier .env :# --- MongoDB Atlas ---
# Remplacez par votre propre URI de connexion
MONGO_URI_ATLAS="mongodb+srv://user:pass@cluster.mongodb.net/..."
MONGODB_URI="mongodb+srv://user:pass@cluster.mongodb.net/..."

# Nom de votre base de données
MONGO_DB="ubereats_poc"

# --- Redis (en local) ---
REDIS_HOST="127.0.0.1"
REDIS_PORT="6379"
🚀 2. Lancement de l'Application "Full Redis" (Architecture 1)Cette version utilise Redis pour tout : Pub/Sub pour la messagerie, GEOADD/GEOSEARCH pour la localisation, et HASH pour l'état des livreurs.Vous aurez besoin de 4 terminaux ouverts dans le dossier du projet.Ordre de lancement : Lancez les workers (Resto, Livreur, Dispatcher) d'abord, puis le Client en dernier.Terminal 1 : Le RestaurantCe worker s'abonne à son canal privé et attend les commandes.python restaurant_worker.py
Sortie attendue : 🍕 Restaurant R55 en attente de commandes sur 'orders:restaurant:R55'...(Note : Pour tester le "Sushi Tokyo", modifiez la variable RESTAURANT_ID dans le script et lancez-le dans un autre terminal.)Terminal 2 : Le(s) Livreur(s)Ce worker asynchrone met à jour son GPS et écoute les jobs. Vous pouvez en lancer plusieurs !python courier_worker_redis.py
Sortie attendue :Livreur L1234 démarré.
[L1234] En écoute de jobs sur 'notify:L1234'
[L1234] Position mise à jour (disponible).
Terminal 3 : Le Dispatcher (Cerveau)Ce worker s'abonne au canal central et assigne les commandes.python dispatcher_worker_redis.py
Sortie attendue : 🤖 Dispatcher Uber Eats (Redis) démarré. En attente sur 'orders:dispatch'...Terminal 4 : Le Client (Le Déclencheur)Une fois les 3 workers lancés, simulez un client :python create_order_interactive_redis.py
Suivez les instructions dans le terminal pour passer commande. Vous verrez les 3 autres terminaux réagir en direct.🗂️ 3. Lancement de l'Application "Full MongoDB" (Architecture 2)Cette version utilise MongoDB comme "source de vérité". La communication se fait via les Change Streams et l'état des documents (statut: "CREATED").Vous aurez besoin de 4 terminaux (plus une étape de préparation).Étape 0 : Préparation (Une seule fois)Ce script peuple la base restaurants avec les menus et crée les index géo-spatiaux.python seed_restaurants_with_menu.py
Sortie attendue : Restaurants et index OK.Étape 1 : Ouvrir 4 TerminauxLancez les workers d'abord, puis le client.Terminal 1 : Le RestaurantCe worker "observe" (.watch()) la collection ubereats pour les commandes le concernant.python restaurant_worker_mongo.py
Sortie attendue : 🍕 Restaurant R55 en attente de commandes (via Mongo Change Stream)...Terminal 2 : Le(s) Livreur(s)Ce worker utilise threading pour mettre à jour son GPS (UPDATE_ONE) et "observer" (.watch()) les assignations en parallèle. Vous pouvez en lancer plusieurs.python courier_worker_mongo.py
Sortie attendue :Livreur L5678 démarré.
[L5678] En écoute de jobs (sur la collection 'ubereats')...
[L5678] Position mise à jour (disponible).
Terminal 3 : Le Dispatcher (Cerveau)Ce worker "observe" les nouvelles commandes (statut: "CREATED") et utilise $geoNear pour trouver un livreur.python dispatcher_worker_mongo.py
Sortie attendue : 🤖 Dispatcher Uber Eats (Mongo) démarré. En attente de commandes...Terminal 4 : Le Client (Le Déclencheur)Une fois les 3 workers lancés, simulez un client :python create_order_interactive_mongo.py
Ce script va faire un INSERT_ONE dans la base, ce qui déclenchera les autres terminaux.📊 4. Scripts ComplémentairesTest Unitaire (Redis)Pour valider la logique du client interactif Redis sans le lancer :python test_redis_client.py
Analyse (MongoDB)Pour exécuter la fonctionnalité "Chiffre d'Affaires" (discutée dans le rapport) :python analytics_mongo.py
