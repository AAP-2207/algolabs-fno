import os
import sys
from datetime import date

# Add backend directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.bhavcopy import get_banknifty_options, supabase_client

# Dates we want to backfill
DATES = [
    date(2024, 1, 3),
    date(2024, 1, 10),
    date(2024, 1, 17),
    date(2024, 1, 25),
    date(2024, 1, 31),
    date(2024, 2, 7),
    date(2024, 2, 14),
    date(2024, 2, 21),
]

def main():
    if supabase_client is None:
        print("ERROR: Supabase client is not initialized. Check your backend/.env variables.")
        sys.exit(1)

    # Verify if the table exists
    try:
        supabase_client.table("bhavcopy_cache").select("trade_date").limit(1).execute()
    except Exception as e:
        print("=" * 80)
        print("DATABASE SETUP REQUIRED:")
        print("The 'bhavcopy_cache' table does not exist in Supabase yet.")
        print("Please run the following SQL command in your Supabase SQL Editor first:")
        print()
        print("create table bhavcopy_cache (")
        print("  trade_date date primary key,")
        print("  data jsonb not null,")
        print("  created_at timestamptz default now()")
        print(");")
        print("=" * 80)
        sys.exit(1)

    print(f"Starting backfill for {len(DATES)} dates...")
    success_count = 0
    
    for d in DATES:
        print(f"Processing {d}...")
        try:
            # This calls the method, which internally hits the live site and stores in Supabase cache
            df = get_banknifty_options(d)
            print(f"  Success: Loaded and cached {len(df)} BANKNIFTY contracts.")
            success_count += 1
        except Exception as e:
            print(f"  FAILED for {d}: {e}")

    print()
    print(f"Backfill complete! Succeeded: {success_count}/{len(DATES)}")

if __name__ == "__main__":
    main()
