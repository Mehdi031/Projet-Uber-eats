# src/mongo_bootstrap.py
import os, json
from pymongo import MongoClient, ASCENDING # type: ignore
from dotenv import load_dotenv # type: ignore
load_dotenv()

client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("MONGO_DB")]

# Collections
ubereats = db.ubereats      # commandes dénormalisées
clients = db.clients
restaurants = db.restaurants
livreurs = db.livreurs

# Index géo & requêtes courantes
ubereats.create_index([("statut", ASCENDING), ("date_commande", ASCENDING)])
ubereats.create_index([("id_livreur", ASCENDING)])
ubereats.create_index([("client.geo_livraison", "2dsphere")])
ubereats.create_index([("restaurant.geo_retrait", "2dsphere")])

restaurants.create_index([("location", "2dsphere")])
livreurs.create_index([("zone", "2dsphere")])
livreurs.create_index([("statut", ASCENDING), ("note_moyenne", ASCENDING)])

print("OK: indexes created")