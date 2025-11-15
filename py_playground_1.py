# py_playground_1.py
import os
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.operations import UpdateOne
from dotenv import load_dotenv
from datetime import datetime
from pprint import pprint # Pour un affichage plus joli

# 1. Connexion (comme dans test_atlas.py)
# ... (ligne 9)
load_dotenv()
# LIGNE MODIFIÉE : vérifie l'un OU l'autre
uri = os.getenv("MONGO_URI_ATLAS") or os.getenv("MONGODB_URI")
if not uri:
    # LIGNE MODIFIÉE : mentionne les deux
    raise Exception("Variable MONGO_URI_ATLAS ou MONGODB_URI non trouvée dans .env")

client = MongoClient(uri)
db = client[os.getenv("MONGO_DB", "ubereats_poc")]

try:
    db.command('ping')
    print("Ping MongoDB OK!")
except Exception as e:
    print(f"Erreur de connexion: {e}")
    exit(1)

# Collections
ubereats = db.ubereats
clients = db.clients
restaurants = db.restaurants
livreurs = db.livreurs

print(f"Connecté à la base '{db.name}'")

# 2. Création des indexes (idempotent)
print("Création des indexes...")
ubereats.create_index([("statut", ASCENDING), ("date_commande", DESCENDING)])
ubereats.create_index([("id_livreur", ASCENDING)])
ubereats.create_index([("client.geo_livraison", "2dsphere")])
restaurants.create_index([("location", "2dsphere")])
livreurs.create_index([("zone", "2dsphere")])
livreurs.create_index([("statut", ASCENDING), ("note_moyenne", DESCENDING)])
print("Indexes OK.")

# 3. Seed des référentiels (idempotent avec upsert=True)
print("Seeding référentiels...")
clients.update_one(
  { "id_client": "C102" },
  { "$setOnInsert": { "id_client": "C102", "nom": "Aya", "tel": "+33 6 00 00 00 01", "email": "aya@example.com" } },
  upsert=True
)

restaurants.update_one(
  { "id_restaurant": "R55" },
  {
    "$setOnInsert": {
      "id_restaurant": "R55",
      "nom": "Pizzeria Roma",
      "adresse": "1 Av. des Champs-Élysées, Paris",
      "location": { "type": "Point", "coordinates": [2.3048, 48.8708] },
      "type_cuisine": "Italienne",
      "note_moyenne": 4.7
    }
  },
  upsert=True
)

livreurs.update_one(
  { "id_livreur": "L8830" },
  {
    "$setOnInsert": {
      "id_livreur": "L8830", "nom": "Sara", "vehicule": "SCOOTER", "note_moyenne": 4.6, "statut": "AVAILABLE"
    }
  },
  upsert=True
)
livreurs.update_one(
  { "id_livreur": "L3958" },
  {
    "$setOnInsert": {
      "id_livreur": "L3958", "nom": "Samir", "vehicule": "BIKE", "note_moyenne": 4.8, "statut": "AVAILABLE"
    }
  },
  upsert=True
)
print("Référentiels OK.")

# 4. Insertion de la commande 001 (idempotent)
print("Insertion CMD-PLAYGROUND-001...")
ubereats.update_one(
  { "id_commande": "CMD-PLAYGROUND-001" },
  {
    "$setOnInsert": {
      "id_commande": "CMD-PLAYGROUND-001",
      "date_commande": datetime.now(),
      "statut": "CREATED",
      "montant_total": 25.50,
      "id_livreur": None,
      "client": { "id_client": "C102", "nom": "Aya", "geo_livraison": { "type": "Point", "coordinates": [2.3774, 48.8646] } },
      "restaurant": { "id_restaurant": "R55", "nom": "Pizzeria Roma", "geo_retrait": { "type": "Point", "coordinates": [2.3048, 48.8708] } },
      "dispatch": { "search_started_at": datetime.now(), "offer_pay": 8.5, "bids": [] }
    }
  },
  upsert=True
)
print("Commande 001 OK.")

# 5. Simulation des 2 bids ($addToSet)
print("Ajout des bids...")
now_ts = datetime.now()
ubereats.update_one(
  { "id_commande": "CMD-PLAYGROUND-001" },
  {
    "$addToSet": {
      "dispatch.bids": { "id_livreur": "L3958", "eta": 6, "note": 4.8, "ts": now_ts }
    }
  }
)
ubereats.update_one(
  { "id_commande": "CMD-PLAYGROUND-001" },
  {
    "$addToSet": {
      "dispatch.bids": { "id_livreur": "L8830", "eta": 5, "note": 4.6, "ts": now_ts }
    }
  }
)
print("Bids OK.")

# 6. Assignation atomique (logique copiée de playground-1.js et seed_atlas.py)
print("Assignation atomique...")
order_doc = ubereats.find_one(
  { "id_commande": "CMD-PLAYGROUND-001" },
  { "dispatch": 1, "id_livreur": 1 }
)

if order_doc and not order_doc.get("id_livreur") and order_doc.get("dispatch", {}).get("bids"):
    bids = order_doc["dispatch"]["bids"]
    # Tri: ETA croissant, puis Note décroissante
    best = sorted(bids, key=lambda b: (b.get("eta", 99), -b.get("note", 0)))[0]

    res = ubereats.update_one(
      { "id_commande": "CMD-PLAYGROUND-001", "id_livreur": None }, # Condition atomique
      { "$set": { "id_livreur": best["id_livreur"], "dispatch.assigned_at": datetime.now(), "statut": "IN_DELIVERY" } }
    )

    if res.modified_count == 1:
        print(f"Assigné → {best['id_livreur']}")
    else:
        print("Déjà assigné par un autre process.")
else:
    print("Pas de bids ou déjà assigné.")

# 7. Lecture des résultats
print("\n--- Résultat Final (Commande 001) ---")
result_doc = ubereats.find_one(
  { "id_commande": "CMD-PLAYGROUND-001" },
  { "_id": 0, "id_commande": 1, "statut": 1, "id_livreur": 1, "dispatch.bids": { "$slice": 5 }, "dispatch.assigned_at": 1 }
)
pprint(result_doc)

print("\n--- Histogramme des Statuts ---")
pipeline = [
  { "$group": { "_id": "$statut", "count": { "$sum": 1 } } },
  { "$sort": { "count": -1 } }
]
pprint(list(ubereats.aggregate(pipeline)))

client.close()