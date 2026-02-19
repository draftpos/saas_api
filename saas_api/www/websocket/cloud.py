import asyncio
import websockets
import json
import os
import sys
import frappe

# --- 1. ENVIRONMENT SETUP (The "Manual Bench" way) ---
# BENCH_PATH = "/home/munyaradzi/Documents/frappe-bench"
BENCH_PATH = "/home/frappe/frappe-bench"
SITES_PATH = os.path.join(BENCH_PATH, "sites")

sys.path.append(os.path.join(BENCH_PATH, "apps", "frappe"))
sys.path.append(os.path.join(BENCH_PATH, "apps", "erpnext")) # if needed
sys.path.append(os.path.join(BENCH_PATH, "apps", "saas_api")) 

os.environ["FRAPPE_SITES_PATH"] = SITES_PATH
os.chdir(SITES_PATH) # Frappe looks for common_site_config.json here

# --- 2. THE BLOCKING FRAPPE LOGIC ---
def run_site_function(site_name, **kwargs):
    # Ensure fresh context for every call in a multi-tenant environment
    frappe.init(site=site_name)
    frappe.connect()
    frappe.set_user("Administrator")
    
    try:
        # Using get_attr to find your specific function
        fn = frappe.get_attr("saas_api.www.websocket.get_quotes.get_quotations")
        return fn(site_id=site_name, **kwargs)
    finally:
        frappe.destroy()

# --- 3. THE ASYNC WEBSOCKET HANDLER ---
async def handler(websocket):
    async for message in websocket:
        req = json.loads(message)
        if req.get("action") == "pull_quotations":
            site_id = req.get("site_id")
            
            # RUN IN THREAD to prevent blocking the websocket loop
            batch = await asyncio.to_thread(
                run_site_function, 
                site_name=site_id,
                limit=req.get("limit", 20),
                status=req.get("status")
            )

            await websocket.send(json.dumps(batch, default=str))

async def main():
    # Use the [websockets documentation](https://websockets.readthedocs.io) 
    # to configure production-grade settings
    async with websockets.serve(handler, "0.0.0.0", 8765):
        await asyncio.Future() 

if __name__ == "__main__":
    asyncio.run(main())
