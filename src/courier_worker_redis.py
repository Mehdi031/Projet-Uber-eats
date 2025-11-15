# courier_worker_redis.py
import os, random, asyncio, msgspec, time
from redis.asyncio import Redis
from dotenv import load_dotenv; load_dotenv()

enc = msgspec.json.Encoder()
dec = msgspec.json.Decoder()

COURIER_ID = f"L{random.randint(1000,9999)}"
print(f"Livreur {COURIER_ID} démarré.")

# Zone de simulation (Paris)
BASE_LAT, BASE_LNG = 48.86, 2.34

async def update_location(r: Redis):
    """Tâche de fond: met à jour la position GPS toutes les 10s."""
    while True:
        # Simuler un léger mouvement
        my_lat = BASE_LAT + random.uniform(-0.03, 0.03)
        my_lng = BASE_LNG + random.uniform(-0.03, 0.03)
        
        # 1. Mettre à jour notre HASH (infos)
        await r.hset(f"courier:{COURIER_ID}", mapping={
            "status": "available",
            "lat": my_lat,
            "lng": my_lng,
            "last_update": time.time()
        })
        
        # 2. Mettre à jour notre position dans l'index GÉOSPATIAL
        # C'est la clé pour l'assignation automatique
        await r.geoadd("available_couriers", (my_lng, my_lat, COURIER_ID))
        
        print(f"[{COURIER_ID}] Position mise à jour (disponible).")
        await asyncio.sleep(10) # Signale sa position toutes les 10s

async def listen_for_jobs(r: Redis):
    """Tâche de fond: écoute son canal personnel pour les assignations."""
    notify_channel = f"notify:{COURIER_ID}"
    p = r.pubsub(ignore_subscribe_messages=True)
    await p.subscribe(notify_channel)
    print(f"[{COURIER_ID}] En écoute de jobs sur '{notify_channel}'")

    async for msg in p.listen():
        # ON A REÇU UN JOB !
        order = dec.decode(msg["data"])
        order_id = order.get("order_id")
        resto = order.get("restaurant_name")
        
        print(f"\n🎉 [{COURIER_ID}] JOB REÇU! Commande {order_id} chez {resto}")
        
        # 1. Se retirer de la liste des livreurs disponibles
        await r.zrem("available_couriers", COURIER_ID)
        
        # 2. Mettre à jour son statut
        await r.hset(f"courier:{COURIER_ID}", "status", "in_delivery")
        print(f"[{COURIER_ID}] Statut: 'in_delivery'. Je me retire du pool.")
        
        # Tâche terminée (dans la vraie vie, on attendrait la fin de la livraison)
        # Pour ce test, on se remet disponible après 30s
        await asyncio.sleep(30)
        print(f"\n[{COURIER_ID}] Livraison {order_id} terminée. Je redeviens disponible.")
        # (on ne relance pas l'update_location, car la tâche tourne toujours)

async def main():
    host = os.getenv("REDIS_HOST", "127.0.0.1")
    port = int(os.getenv("REDIS_PORT", "6379"))
    r = Redis(host=host, port=port, decode_responses=False)

    # Lancer les deux tâches en parallèle
    try:
        await asyncio.gather(
            update_location(r),
            listen_for_jobs(r)
        )
    except KeyboardInterrupt:
        pass
    finally:
        # Nettoyage
        await r.zrem("available_couriers", COURIER_ID)
        await r.delete(f"courier:{COURIER_ID}")
        await r.close()
        print(f"[{COURIER_ID}] Déconnecté et nettoyé.")

if __name__ == "__main__":
    asyncio.run(main())