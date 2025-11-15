import os, random, asyncio, msgspec
from redis.asyncio import Redis
from dotenv import load_dotenv; load_dotenv()

enc = msgspec.json.Encoder()
dec = msgspec.json.Decoder()

COURIER_ID = f"L{random.randint(1000,9999)}"
print(f"COURIER_ID={COURIER_ID}")

CURRENT_STATE = "AVAILABLE"

# Fonction pour simuler la course (AVEC DÉLAIS RÉDUITS)
async def perform_delivery(r: Redis, order_id: str):
    global CURRENT_STATE
    
    updates_channel = f"order_updates:{order_id}"
    
    try:
        # 1. Mettre à jour l'état et notifier le manager
        CURRENT_STATE = "BUSY"
        await r.set(f"courier_status:{COURIER_ID}", CURRENT_STATE)
        await r.publish(updates_channel, enc.encode({"status": "CONFIRMED", "courier_id": COURIER_ID}))
        print(f"[{COURIER_ID}] State set to BUSY. Course CONFIRMED: {order_id}")

        # 2. Simuler l'arrivée au restaurant (plus rapide)
        await asyncio.sleep(random.randint(1, 2)) # NOUVEAU: Délai réduit
        await r.publish(updates_channel, enc.encode({"status": "PICKED_UP"}))
        print(f"[{COURIER_ID}] Food PICKED_UP.")

        # 3. Simuler la livraison (plus rapide)
        await asyncio.sleep(random.randint(1, 2)) # NOUVEAU: Délai réduit
        await r.publish(updates_channel, enc.encode({"status": "DROPPED_OFF"}))
        print(f"[{COURIER_ID}] Food DROPPED_OFF. Delivery complete.")

    finally:
        # 4. Se remettre disponible
        CURRENT_STATE = "AVAILABLE"
        await r.set(f"courier_status:{COURIER_ID}", CURRENT_STATE)
        print(f"[{COURIER_ID}] State set back to AVAILABLE.")
        
async def main():
    global CURRENT_STATE
    
    host = os.getenv("REDIS_HOST", "127.0.0.1")
    port = int(os.getenv("REDIS_PORT", "6379"))
    r = Redis(host=host, port=port, decode_responses=False)

    await r.set(f"courier_status:{COURIER_ID}", CURRENT_STATE)

    sub = r.pubsub()
    await sub.subscribe("offers")
    print(f"Courier {COURIER_ID} listening on 'offers' (state={CURRENT_STATE})...")

    async for msg in sub.listen():
        if msg["type"] != "message" or CURRENT_STATE != "AVAILABLE":
            continue
            
        offer = msgspec.json.decode(msg["data"])
        order_id = offer.get("order_id")
        print(f"[{COURIER_ID}] Offer received: {order_id}")

        bid = {
            "courier_id": COURIER_ID,
            "eta_minutes": random.randint(3, 12),
            "rating": round(random.uniform(3.5, 5.0), 1)
        }
        await r.publish(f"bids:{order_id}", enc.encode(bid))
        print(f"[{COURIER_ID}] Bid sent: {bid}")

        # Attendre l'assignation
        p = r.pubsub()
        await p.subscribe(f"notify:{COURIER_ID}")
        resp = await p.get_message(ignore_subscribe_messages=True, timeout=5.0) # Garde le timeout de 5s
        
        if resp:
            notif = dec.decode(resp["data"])
            if notif.get("order_id") == order_id:
                print(f"[{COURIER_ID}] Assigned 🎉 {notif}")
                
                # Lancer la livraison (rapide) en tâche de fond
                asyncio.create_task(perform_delivery(r, order_id))

        await p.unsubscribe(f"notify:{COURIER_ID}")

if __name__ == "__main__":
    asyncio.run(main())