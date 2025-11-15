# create_order_interactive_redis.py
import os, uuid, msgspec, random
from redis import Redis
from dotenv import load_dotenv; load_dotenv()

enc = msgspec.json.Encoder()

# --- Notre base de données "fictive" de restaurants et menus ---
RESTAURANTS_DB = {
    "R55": {
        "name": "Pizzeria Roma",
        "pickup_geo": {"lng": 2.3048, "lat": 48.8708}, # Champs-Élysées
        "menu": [
            {"id": "A1", "name": "Pizza Margherita", "price": 11.5},
            {"id": "A2", "name": "Pizza 4 Saisons", "price": 14.0},
            {"id": "A9", "name": "Tiramisu", "price": 4.9}
        ]
    },
    "R22": {
        "name": "Sushi Tokyo",
        "pickup_geo": {"lng": 2.3522, "lat": 48.8566}, # Hôtel de Ville
        "menu": [
            {"id": "B1", "name": "Maki Saumon (x6)", "price": 6.0},
            {"id": "B2", "name": "California Rolls (x6)", "price": 7.5},
            {"id": "B5", "name": "Soupe Miso", "price": 3.0}
        ]
    }
}

# --- Infos client (simplifié) ---
CLIENT_INFO = {
    "client_id": "C103-Interactive",
    "dropoff_geo": {"lng": 2.3630, "lat": 48.8674} # Place de la République
}
# -----------------------------------------------------------------

def choose_restaurant():
    """Affiche la liste des restos et demande un choix."""
    print("--- 1. Choisissez un restaurant ---")
    
    # Transforme le dict en liste pour un choix facile
    resto_list = list(RESTAURANTS_DB.items()) # [ ('R55', {...}), ('R22', {...}) ]
    
    for i, (resto_id, details) in enumerate(resto_list):
        print(f"  [{i+1}] {details['name']}")
    
    while True:
        try:
            choice = int(input("Votre choix (ex: 1) : "))
            if 1 <= choice <= len(resto_list):
                # Retourne l'ID et les détails du resto choisi
                return resto_list[choice - 1] 
            else:
                print(f"Choix invalide. Entrez un nombre entre 1 et {len(resto_list)}.")
        except ValueError:
            print("Entrée invalide. Veuillez entrer un nombre.")

def choose_articles(menu):
    """Affiche un menu et demande d'ajouter des articles."""
    print("\n--- 2. Choisissez vos articles ---")
    
    for i, item in enumerate(menu):
        print(f"  [{i+1}] {item['name']} - {item['price']}€")
    print("  [0] J'ai terminé ma commande")
    
    order_articles = []
    
    while True:
        try:
            choice = int(input("Ajouter un article (0 pour finir) : "))
            if choice == 0:
                if not order_articles:
                    print("Votre panier est vide. Veuillez ajouter au moins un article.")
                    continue
                return order_articles # Terminé
            elif 1 <= choice <= len(menu):
                chosen_item = menu[choice - 1]
                # Simule l'ajout de qte=1
                order_articles.append({"nom": chosen_item['name'], "qte": 1})
                print(f"  > Ajouté: {chosen_item['name']}")
            else:
                print(f"Choix invalide. Entrez un nombre entre 0 et {len(menu)}.")
        except ValueError:
            print("Entrée invalide. Veuillez entrer un nombre.")

def main():
    host = os.getenv("REDIS_HOST", "127.0.0.1")
    port = int(os.getenv("REDIS_PORT", "6379"))
    r = Redis(host=host, port=port, decode_responses=False)

    # --- Processus de commande interactif ---
    resto_id, resto_details = choose_restaurant()
    chosen_articles = choose_articles(resto_details['menu'])
    # ----------------------------------------
    
    order_id = str(uuid.uuid4())[:8]
    
    # On construit la commande finale
    order_data = {
        "order_id": order_id,
        "client_id": CLIENT_INFO['client_id'],
        "restaurant_id": resto_id,
        "restaurant_name": resto_details['name'],
        "pickup_geo": resto_details['pickup_geo'],
        "dropoff_geo": CLIENT_INFO['dropoff_geo'],
        "articles": chosen_articles,
        "offer_pay": round(random.uniform(5.0, 10.0), 2) # Paiement simulé
    }

    print(f"\n--- 3. Passage de la commande {order_id} ---")

    # 1. Publier la commande au RESTAURANT
    restaurant_channel = f"orders:restaurant:{order_data['restaurant_id']}"
    r.publish(restaurant_channel, enc.encode(order_data))
    print(f"-> Commande envoyée au restaurant ({resto_details['name']})")

    # 2. Publier la commande au DISPATCHER (Uber Eats)
    dispatcher_channel = "orders:dispatch"
    r.publish(dispatcher_channel, enc.encode(order_data))
    print(f"-> Commande envoyée au dispatcher (recherche de livreur)")
    
    print("\nClient: Commande passée. ✅")

if __name__ == "__main__":
    main()