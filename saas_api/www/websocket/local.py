import asyncio
import websockets
import json

# Config
URI = "ws://localhost:8765"  # Cloud WebSocket server
# SITE_ID = "pharoah"          
SITE_ID = "labmaster.local" 
DEFAULT_MODIFIED = "1970-01-01T00:00:00"  # initial sync timestamp

async def pull_batches(websocket, modified_since, batch_size=3):
    while True:
        try:
            # Send pull request for batch
            request = json.dumps({
                "action": "pull_quotations",
                "site_id": SITE_ID,
                "modified_since": modified_since,
                "limit": batch_size
            })
            await websocket.send(request)

            # Receive batch
            response = await websocket.recv()
            data = json.loads(response)
            batch = data.get("quotations", [])

            if not batch:
                print("No new quotations, waiting before next pull...")
                await asyncio.sleep(10)
                continue

            # Process batch (replace with Frappe ORM insert later)
            for quotation in batch:
                print(f"Processing quotation: {quotation}")

            # Update modified_since to last item's timestamp
            modified_since = batch[-1]["modified"]

            # Pause 10 seconds after each batch
            await asyncio.sleep(10)

        except websockets.exceptions.ConnectionClosed:
            print("Connection closed, reconnecting in 5 seconds...")
            await asyncio.sleep(5)
            break  # exit loop to reconnect
        except Exception as e:
            print("Error during batch pull:", e)
            await asyncio.sleep(5)

async def connect():
    modified_since = DEFAULT_MODIFIED

    while True:  # reconnect loop
        try:
            async with websockets.connect(URI) as websocket:
                print(f"Connected to Cloud ERP for site {SITE_ID}")

                # Send initial connect message with site_id
                await websocket.send(json.dumps({"site_id": SITE_ID}))

                # Start pulling batches
                await pull_batches(websocket, modified_since)
        except Exception as e:
            print("Failed to connect, retrying in 5 seconds:", e)
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(connect())
