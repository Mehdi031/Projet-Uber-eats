import os, random, time, threading
from pymongo import MongoClient, GEOSPHERE
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
uri = os.getenv("MONGO_URI_ATLAS") or os.getenv("MONGODB_URI")
client = MongoClient(uri)
db = client[os.getenv("MONGO_DB", "ubereats_poc")]
livreurs_col = db.livreurs
ubereats_col = db.ubereats

COURIER_ID = f"L{random.randint(1000,9999)}"
print(f"Livreur {COURIER_ID} démarré.")

# Zone de simulation (Paris)
BASE_LAT, BASE_LNG = 48.86, 2.34
CURRENT_STATUS = "AVAILABLE" # Statut local

def update_location_loop():
    """Tâche de fond: met à jour la position GPS toutes les 10s."""
    my_geo_point = { "type": "Point", "coordinates": [BASE_LNG, BASE_LAT] }
    
    while True:
        if CURRENT_STATUS == "AVAILABLE":
            my_geo_point['coordinates'] = [
                BASE_LNG + random.uniform(-0.03, 0.03),
                BASE_LAT + random.uniform(-0.03, 0.03)
            ]
            
            # Action: Met à jour son propre document
            livreurs_col.update_one(
                {"id_livreur": COURIER_ID},
                {
                    "$set": {
                        "statut": "AVAILABLE",
                        "location": my_geo_point, # C'est l'équivalent de GEOADD
                        "last_update": datetime.now()
                    },
                    "$setOnInsert": { # Au cas où c'est un nouveau livreur
                         "id_livreur": COURIER_ID,
                         "nom": f"Livreur Auto {COURIER_ID[-2:]}",
                         "vehicule": "SCOOTER",
                         "note_moyenne": 4.5
                    }
                },
                upsert=True # Crée le document s'il n'existe pas
            )
            print(f"[{COURIER_ID}] Position mise à jour (disponible).")
        
        time.sleep(10)

def listen_for_jobs_loop():
    """Tâche principale: écoute les assignations via Change Stream."""
    global CURRENT_STATUS
    
    # Pipeline: On écoute les MISES A JOUR
    # où on est le nouveau id_livreur
    pipeline = [
        {"$match": {
            "operationType": "update",
            "fullDocument.id_livreur": COURIER_ID,
            # Vérifie que le champ 'id_livreur' est bien celui qui a changé
            "updateDescription.updatedFields.id_livreur": COURIER_ID 
        }}
    ]
    
    print(f"[{COURIER_ID}] En écoute de jobs (sur la collection 'ubereats')...")
    with ubereats_col.watch(pipeline, full_document='updateLookup') as stream:
        for change in stream:
            order = change.get("fullDocument", {})
            order_id = order.get("id_commande")
            resto = order.get("restaurant", {}).get("nom")
            
            print(f"\n🎉 [{COURIER_ID}] JOB REÇU! Commande {order_id} chez {resto}")
            
            # Mettre à jour son statut local et dans la DB
            CURRENT_STATUS = "IN_DELIVERY"
            livreurs_col.update_one(
                {"id_livreur": COURIER_ID},
                {"$set": {"statut": "IN_DELIVERY"}}
            )
            print(f"[{COURIER_ID}] Statut: 'IN_DELIVERY'.")
            
            # Simuler la livraison
            time.sleep(30)
            
            print(f"\n[{COURIER_ID}] Livraison {order_id} terminée. Je redeviens disponible.")
            CURRENT_STATUS = "AVAILABLE"
            # La boucle update_location() reprendra la mise à jour GPS

if __name__ == "__main__":
    # Assurer l'index 2dsphere (déjà fait dans vos playgrounds)
    livreurs_col.create_index([("location", GEOSPHERE)])
    
    # Lancer la mise à jour de la localisation en arrière-plan
    location_thread = threading.Thread(target=update_location_loop, daemon=True)
    location_thread.start()
    
    # Lancer l'écoute des jobs dans le thread principal
    try:
        listen_for_jobs_loop()
    except KeyboardInterrupt:
        print(f"\n[{COURIER_ID}] Arrêt.")
        client.close()