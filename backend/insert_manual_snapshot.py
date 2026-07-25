import os
import sys
import json
import logging
from dotenv import load_dotenv
from supabase import create_client, Client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("insert_manual_snapshot")

current_dir = os.path.dirname(os.path.abspath(__file__))

def main():
    env_path = os.path.join(current_dir, ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path)
    else:
        load_dotenv()

    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_service_key = os.environ.get("SUPABASE_SERVICE_KEY")

    if not supabase_url or not supabase_service_key:
        logger.error("SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables must be set.")
        sys.exit(1)

    if supabase_url and (supabase_url.endswith("/rest/v1/") or supabase_url.endswith("/rest/v1")):
        supabase_url = supabase_url.replace("/rest/v1/", "").replace("/rest/v1", "")

    json_path = os.path.join(current_dir, "real_nse_snapshot.json")
    if not os.path.exists(json_path):
        logger.error(f"File not found: {json_path}")
        sys.exit(1)

    with open(json_path, "r", encoding="utf-8") as f:
        snapshot_file_data = json.load(f)

    records = snapshot_file_data.get("records")
    if not records:
        logger.error("No 'records' key found in real_nse_snapshot.json")
        sys.exit(1)

    wrapped_data = {
        "source": "live",
        "records": records
    }

    symbol = "NIFTY"
    logger.info("Initializing Supabase client...")
    supabase: Client = create_client(supabase_url, supabase_service_key)

    logger.info("Inserting row into Supabase option_chain_snapshots table...")
    row = {
        "symbol": symbol,
        "data": wrapped_data
    }

    response = supabase.table("option_chain_snapshots").insert(row).execute()
    
    if response.data and len(response.data) > 0:
        inserted_row = response.data[0]
        row_id = inserted_row.get("id")
        fetched_at = inserted_row.get("fetched_at")
        print(f"Insertion successful!")
        print(f"Row ID: {row_id}")
        print(f"Fetched At: {fetched_at}")
    else:
        logger.error(f"Failed to insert row or empty response returned: {response}")
        sys.exit(1)

if __name__ == "__main__":
    main()
