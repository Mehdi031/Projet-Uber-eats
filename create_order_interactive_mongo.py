import os, uuid, random
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
uri = os.getenv("MONGO_URI_ATLAS") or os.getenv("MONGODB_URI")
client = MongoClient(uri)
db = client[os.getenv("MONGO_DB", "ubereats_poc")]
restaurants_col = db.restaurants
ubereats_col = db.ubereats

# --- Infos client (simplifié) ---
CLIENT_INFO = {
    "id_client": "C103-Interactive",
    "nom": "Client Mongo",
    "geo_livraison": { "type": "Point", "coordinates": [2.3630, 48.8674] } # Place de la République
}
# ---------------------------------

def choose_restaurant():
    """Lit les restaurants depuis MongoDB."""
    print("--- 1. Choisissez un restaurant ---")
    
    # Récupère les restaurants depuis la base de données
    resto_list = list(restaurants_col.find())
    
    for i, details in enumerate(resto_list):
        print(f"  [{i+1}] {details['nom']}")
    
    while True:
        try:
            choice = int(input("Votre choix (ex: 1) : "))
            if 1 <= choice <= len(resto_list):
                return resto_list[choice - 1] # Retourne le document restaurant complet
            else:
                print(f"Choix invalide.")
        except ValueError:
            print("Entrée invalide.")

def choose_articles(menu):
    """Affiche un menu et demande d'ajouter des articles."""
    print("\n--- 2. Choisissez vos articles ---")
    
    for i, item in enumerate(menu):
        print(f"  [{i+1}] {item['nom']} - {item['price']}€")
    print("  [0] J'ai terminé ma commande")
    
    order_articles = []
    
    while True:
        try:
            choice = int(input("Ajouter un article (0 pour finir) : "))
            if choice == 0:
                if not order_articles:
                    print("Votre panier est vide.")
                    continue
                return order_articles # Terminé
            elif 1 <= choice <= len(menu):
                chosen_item = menu[choice - 1]
                order_articles.append({"nom": chosen_item['nom'], "qte": 1, "id_article": chosen_item['id']})
                print(f"  > Ajouté: {chosen_item['nom']}")
            else:
                print(f"Choix invalide.")
        except ValueError:
            print("Entrée invalide.")

def main():
    resto_doc = choose_restaurant()
    chosen_articles = choose_articles(resto_doc.get('menu', []))
    
    order_id = f"CMD-MONGO-{uuid.uuid4().hex[:6]}"
    
    # On construit le document de commande (dénormalisé, comme dans vos playgrounds)
    order_data = {
        "id_commande": order_id,
        "date_commande": datetime.now(),
        "statut": "CREATED", # Statut initial pour le dispatcher
        "id_livreur": None,
        "client": {
            "id_client": CLIENT_INFO['id_client'],
            "nom": CLIENT_INFO['nom'],
            "geo_livraison": CLIENT_INFO['geo_livraison']
        },
        "restaurant": {
            "id_restaurant": resto_doc['id_restaurant'],
            "nom": resto_doc['nom'],
            "geo_retrait": resto_doc['location'] # Copie du point de pickup
        },
        "articles": chosen_articles,
        "dispatch": {
            "search_started_at": datetime.now(),
            "offer_pay": round(random.uniform(5.0, 10.0), 2),
            "bids": [] # Gardé pour la compatibilité, mais non utilisé ici
        }
    }

    print(f"\n--- 3. Passage de la commande {order_id} ---")

    # ACTION PRINCIPALE: Insérer la commande dans MongoDB
    ubereats_col.insert_one(order_data)
    
    print(f"-> Commande insérée dans MongoDB (statut: CREATED).")
    print("\nClient: Commande passée. ✅")
    client.close()

if __name__ == "__main__":
    main()