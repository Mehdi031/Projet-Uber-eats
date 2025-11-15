import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()
uri = os.getenv("MONGO_URI_ATLAS") or os.getenv("MONGODB_URI")
client = MongoClient(uri)
db = client[os.getenv("MONGO_DB", "ubereats_poc")]
ubereats_col = db.ubereats

# ID de ce restaurant (à changer pour simuler un autre resto)
RESTAURANT_ID = "R55"

# Pipeline pour le Change Stream:
# On ne veut que les insertions (nouvelles commandes)
# ET seulement celles pour notre restaurant
pipeline = [
    {"$match": {
        "operationType": "insert",
        "fullDocument.restaurant.id_restaurant": RESTAURANT_ID
    }}
]

def main():
    print(f"🍕 Restaurant {RESTAURANT_ID} en attente de commandes (via Mongo Change Stream)...")
    # full_document='updateLookup' est nécessaire pour avoir le doc complet
    with ubereats_col.watch(pipeline, full_document='updateLookup') as stream:
        for change in stream:
            order = change.get("fullDocument", {})
            order_id = order.get("id_commande")
            articles = order.get("articles", [])
            
            print(f"\n🔔 NOUVELLE COMMANDE: {order_id}")
            for item in articles:
                print(f"  - {item['qte']}x {item['nom']}")
            print("En préparation...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nArrêt du restaurant.")
        client.close()