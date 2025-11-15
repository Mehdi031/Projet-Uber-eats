# dispatcher_worker_redis.py
import os, msgspec, asyncio
from redis.asyncio import Redis
from dotenv import load_dotenv; load_dotenv()

enc = msgspec.json.Encoder()
dec = msgspec.json.Decoder()

async def main():
    host = os.getenv("REDIS_HOST", "127.0.0.1")
    port = int(os.getenv("REDIS_PORT", "6379"))
    r = Redis(host=host, port=port, decode_responses=False)

    # S'abonner au canal des NOUVELLES COMMANDES
    dispatcher_channel = "orders:dispatch"
    p = r.pubsub(ignore_subscribe_messages=True)
    await p.subscribe(dispatcher_channel)
    
    print(f"🤖 Dispatcher Uber Eats démarré. En attente de commandes sur '{dispatcher_channel}'...")

    async for msg in p.listen():
        try:
            order = dec.decode(msg["data"])
            order_id = order.get("order_id")
            pickup = order.get("pickup_geo")
            
            if not pickup:
                print(f"Erreur: Commande {order_id} sans 'pickup_geo'.")
                continue

            print(f"\nNouvelle commande à dispatcher : {order_id}")
            
            # 1. TROUVER LE LIVREUR LE PLUS PROCHE
            # GEORADIUS (ancienne cmd) ou GEOSEARCH (nouvelle cmd)
            # On cherche le livreur le plus proche dans un rayon de 5km
            # 'ASC' = trier par distance croissante, 'COUNT 1' = ne renvoyer que le premier
            nearest_courier = await r.geosearch(
                "available_couriers",
                longitude=pickup['lng'],
                latitude=pickup['lat'],
                radius=5000, # 5000 mètres
                unit="m",
                sort="ASC",
                count=1
            )
            
            if not nearest_courier:
                print(f"Aucun livreur disponible à proximité pour {order_id}. (Ré-essai bientôt...)")
                # Dans une vraie app, on remettrait la commande en file d'attente
                continue
                
            chosen_courier_id = nearest_courier[0].decode('utf-8') # ex: "L1234"
            
            # 2. ASSIGNATION ATOMIQUE
            # On essaie de retirer le livreur du pool.
            # S'il a déjà été pris par un autre process, zrem renverra 0.
            removed_count = await r.zrem("available_couriers", chosen_courier_id)
            
            if removed_count == 1:
                # C'est gagné ! On a réservé ce livreur.
                print(f"-> Livreur {chosen_courier_id} trouvé (le plus proche).")
                
                # 3. NOTIFIER LE LIVREUR
                await r.hset(f"courier:{chosen_courier_id}", "status", "assigned")
                await r.publish(f"notify:{chosen_courier_id}", enc.encode(order))
                
                print(f"✅ Commande {order_id} assignée à {chosen_courier_id}.")
            else:
                # Race condition: un autre dispatcher a pris ce livreur 
                # juste avant nous (entre GEOSEARCH et ZREM).
                print(f"Livreur {chosen_courier_id} déjà pris. (Ré-essai bientôt...)")

        except Exception as e:
            print(f"Erreur de dispatching: {e}")

if __name__ == "__main__":
    asyncio.run(main())