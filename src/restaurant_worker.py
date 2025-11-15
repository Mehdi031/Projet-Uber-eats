# restaurant_worker.py
import os, msgspec
from redis import Redis
from dotenv import load_dotenv; load_dotenv()

dec = msgspec.json.Decoder()

# ID de ce restaurant (à changer pour simuler un autre resto)
RESTAURANT_ID = "R55"

def main():
    host = os.getenv("REDIS_HOST", "127.0.0.1")
    port = int(os.getenv("REDIS_PORT", "6379"))
    r = Redis(host=host, port=port, decode_responses=False)

    # S'abonner au canal DÉDIÉ à ce restaurant
    restaurant_channel = f"orders:restaurant:{RESTAURANT_ID}"
    p = r.pubsub(ignore_subscribe_messages=True)
    p.subscribe(restaurant_channel)

    print(f"🍕 Restaurant {RESTAURANT_ID} (Pizzeria Roma) en attente de commandes sur '{restaurant_channel}'...")

    for msg in p.listen():
        try:
            order = dec.decode(msg["data"])
            order_id = order.get("order_id")
            articles = order.get("articles", [])
            print(f"\n🔔 NOUVELLE COMMANDE: {order_id}")
            for item in articles:
                print(f"  - {item['qte']}x {item['nom']}")
            print("En préparation...")
        except Exception as e:
            print(f"Erreur de décodage: {e}")

if __name__ == "__main__":
    main()