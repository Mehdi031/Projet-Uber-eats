import os, uuid, asyncio, time, msgspec
from redis.asyncio import Redis
from dotenv import load_dotenv; load_dotenv()

enc = msgspec.json.Encoder()
dec = msgspec.json.Decoder()

async def gather_bids_with_deadline(psub, timeout_s=5.0):
    """Collect bids until the deadline (no early break on first None)."""
    bids = []
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        remaining = max(0.01, deadline - time.monotonic())
        msg = await psub.get_message(ignore_subscribe_messages=True, timeout=remaining)
        if msg is None:
            # no message right now; loop again until deadline
            continue
        bids.append(dec.decode(msg["data"]))
    return bids

async def main():
    host = os.getenv("REDIS_HOST", "127.0.0.1")
    port = int(os.getenv("REDIS_PORT", "6379"))
    print(f"→ Redis manager connecting to {host}:{port}")
    r = Redis(host=host, port=port, decode_responses=False)

    order_id = str(uuid.uuid4())
    bids_channel = f"bids:{order_id}"
    offer = {
        "order_id": order_id,
        "pickup": {"lat":48.8708,"lng":2.3048,"address":"Champs-Élysées"},
        "dropoff":{"lat":48.8566,"lng":2.3522,"address":"Hôtel de Ville"},
        "offer_pay": 8.5
    }

    # NOUVEAU: Créer un enregistrement initial pour la commande dans un Hash
    order_key = f"order:{order_id}"
    await r.hset(order_key, mapping={
        "status": "BIDDING",
        "offer_pay": offer["offer_pay"],
        "pickup_address": offer["pickup"]["address"],
        "dropoff_address": offer["dropoff"]["address"]
    })
    print(f"Order {order_id} saved to Redis with status BIDDING")


    # 1) S'abonner d'abord au canal de réponses pour éviter la course (pub/sub est éphémère)
    psub = r.pubsub()
    await psub.subscribe(bids_channel)
    print(f"Subscribed to {bids_channel}")

    # 2) Petite pause pour s'assurer que l'abonnement est pris en compte
    await asyncio.sleep(0.05)

    # 3) Publier l'offre
    await r.publish("offers", enc.encode(offer))
    print(f"Offer published: {order_id} (collecting bids for 5s)")

    # 4) Collecter les bids jusqu'à l'échéance
    bids = await gather_bids_with_deadline(psub, timeout_s=5.0)
    print(f"Received {len(bids)} bids")

    # 5) Nettoyage de l'abonnement
    await psub.unsubscribe(bids_channel)

    if not bids:
        print("No bids. (Vérifie qu'au moins un courier tourne et qu'il n'a pas été lancé APRÈS le publish)")
        # NOUVEAU: Mettre à jour le statut en cas d'échec
        await r.hset(order_key, "status", "NO_BIDS")
        return

    # NOUVEAU: Stocker les bids reçus (encodés en JSON)
    bids_json_list = [enc.encode(b) for b in bids]
    await r.hset(order_key, "bids_received", msgspec.json.encode(bids_json_list))

    # 6) Choisir le meilleur
    chosen = min(bids, key=lambda b: (b.get("eta_minutes", 999), -b.get("rating", 0)))
    notif = {"order_id": order_id, "status":"assigned"}

    # 7) Notifier le livreur choisi
    await r.publish(f"notify:{chosen['courier_id']}", enc.encode(notif))
    print("Assigned ->", chosen["courier_id"])

    # NOUVEAU: Mettre à jour la commande avec le gagnant
    await r.hset(order_key, mapping={
        "status": "ASSIGNED",
        "courier_id": chosen['courier_id'],
        "courier_eta": chosen['eta_minutes'],
        "courier_rating": chosen['rating']
    })
    print(f"Order {order_id} updated to ASSIGNED (Courier: {chosen['courier_id']})")


if __name__ == "__main__":
    asyncio.run(main())