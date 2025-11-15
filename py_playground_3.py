# py_playground_3.py
import os
from pymongo import MongoClient, DESCENDING
from dotenv import load_dotenv
from datetime import datetime
from pprint import pprint

# 1. Connexion
load_dotenv()
uri = os.getenv("MONGO_URI_ATLAS")
client = MongoClient(uri)
db = client[os.getenv("MONGO_DB", "ubereats_poc")]
ubereats = db.ubereats
print(f"Connecté à la base '{db.name}'")

# 2. Trouver toutes les commandes non assignées avec des bids
print("Lancement du batch d'assignation...")
cursor = ubereats.find(
  { "id_livreur": None, "dispatch.bids.0": { "$exists": True } },
  projection={ "id_commande": 1, "dispatch.bids": 1 }
)

examined = 0
assigned = 0

# 3. Boucler et assigner
for doc in cursor:
    examined += 1
    
    bids = doc.get("dispatch", {}).get("bids", [])
    if not bids:
        continue

    # Choisir la meilleure bid: ETA asc, puis note desc
    best = sorted(bids, key=lambda b: (b.get("eta", 99), -b.get("note", 0)))[0]

    # Assignation atomique
    res = ubereats.update_one(
      { "_id": doc["_id"], "id_livreur": None }, # Condition atomique
      {
        "$set": {
          "id_livreur": best["id_livreur"],
          "dispatch.assigned_at": datetime.now(),
          "statut": "IN_DELIVERY"
        }
      }
    )

    if res.modified_count == 1:
        assigned += 1
        print(f"  > Assigné {doc['id_commande']} -> {best['id_livreur']}")

print(f"\nTerminé. Examiné: {examined}, Assigné: {assigned}")

# 4. Readback (comme dans playground-3.js)
print("\n--- Dernières commandes assignées ---")
assigned_docs = ubereats.find(
  { "id_livreur": { "$ne": None } },
  { "_id": 0, "id_commande": 1, "id_livreur": 1, "statut": 1, "dispatch.assigned_at": 1 }
).sort("dispatch.assigned_at", DESCENDING).limit(10)
pprint(list(assigned_docs))

# 5. Histogramme des statuts
print("\n--- Histogramme des Statuts ---")
pipeline = [
  { "$group": { "_id": "$statut", "count": { "$sum": 1 } } },
  { "$sort": { "count": -1 } }
]
pprint(list(ubereats.aggregate(pipeline)))

client.close()