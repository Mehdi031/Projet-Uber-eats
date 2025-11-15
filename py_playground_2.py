# py_playground_2.py
import os
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime
from pprint import pprint

# 1. Connexion
load_dotenv()
uri = os.getenv("MONGO_URI_ATLAS")
client = MongoClient(uri)
db = client[os.getenv("MONGO_DB", "ubereats_poc")]
ubereats = db.ubereats
livreurs = db.livreurs
restaurants = db.restaurants
print(f"Connecté à la base '{db.name}'")

# 2. Assurer l'index 2dsphere sur la localisation ponctuelle des livreurs
livreurs.update_many(
  { "location": { "$exists": False } },
  {
    "$set": {
      "location": { "type": "Point", "coordinates": [2.335, 48.87] } # Position par défaut
    }
  }
)
livreurs.create_index({ "location": "2dsphere" })
print("Index 2dsphere 'location' des livreurs OK.")

# 3. Créer la commande 002 (idempotent)
print("Insertion CMD-PLAYGROUND-002...")
ubereats.update_one(
  { "id_commande": "CMD-PLAYGROUND-002" },
  {
    "$setOnInsert": {
      "id_commande": "CMD-PLAYGROUND-002",
      "date_commande": datetime.now(),
      "statut": "CREATED",
      "id_livreur": None,
      "client": {
        "geo_livraison": { "type": "Point", "coordinates": [2.3630, 48.8674] }
      },
      "restaurant": {
        "id_restaurant": "R55", "nom": "Pizzeria Roma",
        "geo_retrait": { "type": "Point", "coordinates": [2.3048, 48.8708] }
      },
      "dispatch": { "search_started_at": datetime.now(), "offer_pay": 9.2, "bids": [] }
    }
  },
  upsert=True
)
print("Commande 002 OK.")

# 4. Trouver le point de pickup (comme dans playground-2.js)
order2 = ubereats.find_one(
  { "id_commande": "CMD-PLAYGROUND-002" },
  { "restaurant.id_restaurant": 1, "restaurant.geo_retrait": 1 }
)

pickup = None
if not order2:
    print("Commande 002 introuvable")
elif order2.get("restaurant", {}).get("geo_retrait"):
    pickup = order2["restaurant"]["geo_retrait"]
else:
    # Logique de fallback (non testée, mais traduite)
    print("Fallback: recherche du point pickup dans la collection restaurants...")
    rid = order2.get("restaurant", {}).get("id_restaurant", "R55")
    resto = restaurants.find_one({ "id_restaurant": rid }, { "location": 1 })
    if resto and resto.get("location"):
        pickup = resto["location"]
        ubereats.update_one(
            { "id_commande": "CMD-PLAYGROUND-002" },
            { "$set": { "restaurant.geo_retrait": pickup } }
        )

if not pickup:
    print("⚠️ Aucun point pickup trouvé. Arrêt.")
    client.close()
    exit()

print(f"Point de pickup trouvé: {pickup['coordinates']}")

# 5. $geoNear : Trouver les livreurs les plus proches
print("\n--- Top 3 livreurs proches (via $geoNear) ---")
pipeline = [
    {
      "$geoNear": {
        "near": pickup, # Utilise le document GeoJSON "Point"
        "distanceField": "distance_m", # Nom du champ de sortie
        "spherical": True,
        "key": "location", # L'index à utiliser
        "distanceMultiplier": 1 # Pour avoir des mètres (si index en radians) -> 6378137 (si en WGS84)
        # Pymongo gère souvent cela automatiquement si l'index est 2dsphere
      }
    },
    { "$match": { "statut": "AVAILABLE" } },
    { "$project": { "_id": 0, "id_livreur": 1, "nom": 1, "vehicule": 1, "note_moyenne": 1, "distance_m": 1 } },
    { "$sort": { "distance_m": 1, "note_moyenne": -1 } },
    { "$limit": 3 }
]

near_couriers = list(livreurs.aggregate(pipeline))
pprint(near_couriers)

# 6. Simuler une bid du plus proche
if near_couriers:
    chosen = near_couriers[0]
    # rough ETA model
    eta = max(4, round(chosen.get("distance_m", 1000) / 250)) 
    
    ubereats.update_one(
      { "id_commande": "CMD-PLAYGROUND-002" },
      {
        "$addToSet": {
          "dispatch.bids": {
            "id_livreur": chosen["id_livreur"],
            "eta": eta,
            "note": chosen.get("note_moyenne"),
            "ts": datetime.now()
          }
        }
      }
    )
    print(f"\nSimulation d'une bid de {chosen['id_livreur']} (ETA: {eta} min)")

# 7. Afficher les 2 commandes
print("\n--- Résumé des commandes 001 et 002 ---")
cursor = ubereats.find(
  { "id_commande": { "$in": ["CMD-PLAYGROUND-001", "CMD-PLAYGROUND-002"] } },
  { "_id": 0, "id_commande": 1, "statut": 1, "id_livreur": 1, "dispatch.bids": { "$slice": 3 } }
)
pprint(list(cursor))

client.close()