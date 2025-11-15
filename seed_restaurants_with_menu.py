import os
from pymongo import MongoClient, GEOSPHERE
from dotenv import load_dotenv

load_dotenv()
uri = os.getenv("MONGO_URI_ATLAS") or os.getenv("MONGODB_URI")
client = MongoClient(uri)
db = client[os.getenv("MONGO_DB", "ubereats_poc")]
restaurants = db.restaurants

# Définition de nos restaurants (similaire au dict de la version Redis)
RESTAURANTS_DB = {
    "R55": {
        "id_restaurant": "R55",
        "nom": "Pizzeria Roma",
        "location": { "type": "Point", "coordinates": [2.3048, 48.8708] }, # Champs-Élysées
        "menu": [
            {"id": "A1", "nom": "Pizza Margherita", "price": 11.5},
            {"id": "A2", "nom": "Pizza 4 Saisons", "price": 14.0},
            {"id": "A9", "nom": "Tiramisu", "price": 4.9}
        ]
    },
    "R22": {
        "id_restaurant": "R22",
        "nom": "Sushi Tokyo",
        "location": { "type": "Point", "coordinates": [2.3522, 48.8566] }, # Hôtel de Ville
        "menu": [
            {"id": "B1", "nom": "Maki Saumon (x6)", "price": 6.0},
            {"id": "B2", "nom": "California Rolls (x6)", "price": 7.5},
            {"id": "B5", "nom": "Soupe Miso", "price": 3.0}
        ]
    }
}

print("Mise à jour des restaurants avec les menus...")
# Upsert (insert or update)
for resto_id, data in RESTAURANTS_DB.items():
    restaurants.update_one(
        {"id_restaurant": resto_id},
        {"$set": data},
        upsert=True
    )

# Assurer l'index géospatial (déjà fait dans vos playgrounds)
restaurants.create_index([("location", GEOSPHERE)])
print("Restaurants OK.")
client.close()