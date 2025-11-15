import os, time
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
uri = os.getenv("MONGO_URI_ATLAS") or os.getenv("MONGODB_URI")
client = MongoClient(uri)
db = client[os.getenv("MONGO_DB", "ubereats_poc")]
ubereats_col = db.ubereats
livreurs_col = db.livreurs

# Pipeline: Écouter les NOUVELLES commandes
pipeline = [
    {"$match": {
        "operationType": "insert",
        "fullDocument.statut": "CREATED"
    }}
]

def find_and_assign(order):
    order_id = order["id_commande"]
    pickup = order.get("restaurant", {}).get("geo_retrait")
    
    if not pickup:
        print(f"Erreur: Commande {order_id} sans 'geo_retrait'.")
        return

    print(f"\nNouvelle commande à dispatcher : {order_id}")
    
    # 1. TROUVER LE LIVREUR LE PLUS PROCHE (logique de py_playground_2.py)
    geo_pipeline = [
        {
          "$geoNear": {
            "near": pickup,
            "distanceField": "distance_m",
            "spherical": True,
            "query": { "statut": "AVAILABLE" }, # Ne chercher que les livreurs libres
            "key": "location"
          }
        },
        { "$limit": 1 } # On ne veut que le plus proche
    ]
    
    nearest_couriers = list(livreurs_col.aggregate(geo_pipeline))
    
    if not nearest_couriers:
        print(f"Aucun livreur DISPONIBLE à proximité pour {order_id}. (Ré-essai bientôt...)")
        # Idéalement, on mettrait le statut à "SEARCHING_AGAIN"
        return
        
    chosen_courier = nearest_couriers[0]
    chosen_courier_id = chosen_courier['id_livreur']
    distance = chosen_courier['distance_m']
    
    print(f"-> Livreur {chosen_courier_id} trouvé (le plus proche: {distance:.0f}m).")
    
    # 2. ASSIGNATION ATOMIQUE (logique de py_playground_3.py)
    # On met à jour la commande SEULEMENT si elle n'est pas déjà prise
    res = ubereats_col.update_one(
        { "_id": order["_id"], "id_livreur": None }, # Condition atomique
        {
            "$set": {
                "id_livreur": chosen_courier_id,
                "dispatch.assigned_at": datetime.now(),
                "statut": "IN_DELIVERY"
            }
        }
    )
    
    if res.modified_count == 1:
        # C'est gagné ! On prévient le livreur en changeant son statut
        livreurs_col.update_one(
            {"id_livreur": chosen_courier_id},
            {"$set": {"statut": "ASSIGNED"}} # Le livreur verra ce changement
        )
        print(f"✅ Commande {order_id} assignée à {chosen_courier_id}.")
    else:
        # Race condition: un autre dispatcher a pris cette commande
        print(f"Race condition : {order_id} a été assigné par un autre process.")

def main():
    print(f"🤖 Dispatcher Uber Eats démarré (Mongo). En attente de commandes...")
    with ubereats_col.watch(pipeline, full_document='updateLookup') as stream:
        for change in stream:
            order = change.get("fullDocument")
            if order:
                find_and_assign(order)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nArrêt du dispatcher.")
        client.close()