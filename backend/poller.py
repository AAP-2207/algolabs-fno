import os
import sys
import logging
from dotenv import load_dotenv
from supabase import create_client, Client

# Set up logging to stdout
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("nse_poller")

# Add the parent directory (backend) to the Python path to import services correctly
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from services import nse_client

def main():
    # Load environment variables
    # (Optional) load from backend/.env if it exists locally
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

    # Standardize the Supabase URL to remove trailing /rest/v1 or /rest/v1/ path segments if present
    if supabase_url and (supabase_url.endswith("/rest/v1/") or supabase_url.endswith("/rest/v1")):
        supabase_url = supabase_url.replace("/rest/v1/", "").replace("/rest/v1", "")

    symbol = "NIFTY"
    logger.info(f"Starting option chain poll for symbol: {symbol}")

    try:
        data = nse_client.get_option_chain(symbol)
        source = data.get("source")
        
        logger.info(f"Fetched option chain data. Source is: '{source}'")

        if source == "live":
            logger.info("Live data fetched successfully. Initializing Supabase client...")
            supabase: Client = create_client(supabase_url, supabase_service_key)
            
            logger.info("Writing live snapshot to Supabase 'option_chain_snapshots' table...")
            row = {
                "symbol": symbol,
                "data": data
            }
            
            response = supabase.table("option_chain_snapshots").insert(row).execute()
            logger.info(f"Successfully wrote snapshot to Supabase option_chain_snapshots table. Response: {response}")
            
        elif source == "mock":
            logger.warning("Fetched data is MOCK (live fetch failed). Skipping write to Supabase.")
        else:
            logger.warning(f"Unexpected source field value: '{source}'. Skipping write to Supabase.")

    except Exception as e:
        logger.error(f"Error during polling execution: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
