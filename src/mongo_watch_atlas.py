import os
import time
from pymongo import MongoClient
from dotenv import load_dotenv

# Charger les variables d'environnement (.env)
load_dotenv()

# Connexion à Atlas
client = MongoClient(os.getenv("MONGO_URI_ATLAS"))
db = client[os.getenv("MONGO_DB", "ubereats_poc")]
ubereats = db.ubereats

# Pipeline : on écoute les insertions et mises à jour
pipeline = [
    {"$match": {
        "operationType": {"$in": ["insert", "update"]}
    }}
]

if __name__ == "__main__":
    print("👂 Watching MongoDB Atlas collection: ubereats_poc.ubereats ...")
    print("(Appuie sur Ctrl+C pour arrêter)\n")

    # Le watch() garde une connexion ouverte et affiche tout changement
    with ubereats.watch(pipeline, full_document="updateLookup") as stream:
        while True:
            change = stream.try_next()
            if not change:
                time.sleep(0.05)
                continue

            op_type = change["operationType"]
            doc = change.get("fullDocument", {})
            print(f"→ {op_type.upper()} détecté : id_commande={doc.get('id_commande')}, statut={doc.get('statut')}")