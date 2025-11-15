# src/mongo_assigner_atlas.py
import os, time
from pymongo import MongoClient
from dotenv import load_dotenv; load_dotenv()

client = MongoClient(os.getenv("MONGO_URI_ATLAS"))
db = client[os.getenv("MONGO_DB", "ubereats_poc")]
ubereats = db.ubereats

def pick_best(bids):
    return sorted(bids, key=lambda b: (b.get("eta", 9999), -b.get("note", 0)))[0]

def assign_latest_unassigned():
    # Dernière commande non assignée
    doc = ubereats.find_one({"id_livreur": None}, sort=[("_id",-1)], projection={"id_commande":1,"dispatch.bids":1})
    if not doc or not doc.get("dispatch",{}).get("bids"):
        print("No unassigned order with bids."); return

    order_id = doc["id_commande"]
    best = pick_best(doc["dispatch"]["bids"])
    now = time.time()

    res = ubereats.update_one(
        {"id_commande": order_id, "id_livreur": None},
        {"$set": {"id_livreur": best["id_livreur"], "dispatch.assigned_at": now, "statut":"IN_DELIVERY"}}
    )
    if res.modified_count == 1:
        print("Assigned on Atlas:", order_id, "->", best["id_livreur"])
    else:
        print("Race lost (already assigned).")

if __name__ == "__main__":
    assign_latest_unassigned()