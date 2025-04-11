#!/usr/bin/env python3
"""
Polymarket Copy Trader Setup Script

This script guides you through setting up API keys for the Polymarket copy trader.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
import json
import webbrowser
import time

def main():
    print("=" * 80)
    print("POLYMARKET COPY TRADER SETUP")
    print("=" * 80)
    print("\nThis script will guide you through setting up API keys for the Polymarket copy trader.\n")
    
    # Check if .env file exists
    env_file = Path(".env")
    env_example = Path(".env.example")
    
    if not env_file.exists() and env_example.exists():
        print("Creating .env file from .env.example...")
        with open(env_example, 'r') as f:
            content = f.read()
        with open(env_file, 'w') as f:
            f.write(content)
    
    # Load current .env file
    load_dotenv()
    
    # Create config directory if it doesn't exist
    config_dir = Path("config")
    config_dir.mkdir(exist_ok=True)
    
    # Check and possibly create copy trader config
    config_file = config_dir / "copy_trader_config.json"
    if not config_file.exists():
        default_config = {
            "watched_traders": [],
            "min_amount_to_copy": 50,
            "max_amount_to_copy": 500,
            "copy_percentage": 0.1,
            "min_copy_delay": 30,
            "max_copy_delay": 300,
            "blacklisted_markets": [],
            "whitelist_only": False,
            "whitelisted_markets": [],
            "copy_buys": True,
            "copy_sells": True,
            "max_positions_per_market": 3,
            "max_daily_trades": 10,
            "max_daily_amount": 1000,
            "auto_close_positions": True,
            "trading_active": False,
            "polling_interval": 60,
            "analytics": {
                "enabled": True,
                "min_win_rate": 0.7,
                "min_pnl": 50000,
                "auto_update_traders": False,
                "max_auto_traders": 5,
                "update_interval_hours": 24
            }
        }
        with open(config_file, 'w') as f:
            json.dump(default_config, f, indent=4)
        print(f"Created default configuration in {config_file}")
    
    # Guide for API keys
    print("\n" + "=" * 80)
    print("API KEY SETUP GUIDE")
    print("=" * 80)
    
    print("\n1. POLYGON WALLET PRIVATE KEY")
    print("   You need a Polygon wallet private key to execute trades.")
    print("   If you don't have one, you can create one using MetaMask or similar wallet.")
    print("   ⚠️ IMPORTANT: Never share your private key with anyone!")
    print("   ⚠️ IMPORTANT: Make sure to fund your wallet with MATIC for gas fees and USDC for trading!")
    
    print("\n2. POLYMARKET API KEYS")
    print("   To trade on Polymarket, you need API credentials.")
    print("   Visit the Polymarket developer portal to get your API keys:")
    print("   https://docs.polymarket.com/")
    
    open_site = input("\n   Open Polymarket API documentation now? (y/n): ")
    if open_site.lower() in ('y', 'yes'):
        print("   Opening Polymarket API documentation...")
        webbrowser.open("https://docs.polymarket.com/")
        time.sleep(1)
    
    print("\n3. ANALYTICS API KEYS")
    print("   The copy trader can use third-party analytics services to find top traders.")
    print("   Currently supported services:")
    print("   - PolymarketAnalytics.com")
    print("   - PolymarketWhales.info")
    
    open_analytics = input("\n   Open PolymarketAnalytics.com now? (y/n): ")
    if open_analytics.lower() in ('y', 'yes'):
        print("   Opening PolymarketAnalytics.com...")
        webbrowser.open("https://polymarketanalytics.com/")
        time.sleep(1)
    
    open_whales = input("\n   Open PolymarketWhales.info now? (y/n): ")
    if open_whales.lower() in ('y', 'yes'):
        print("   Opening PolymarketWhales.info...")
        webbrowser.open("https://polymarketwhales.info/")
        time.sleep(1)
    
    print("\n" + "=" * 80)
    print("NEXT STEPS")
    print("=" * 80)
    
    print("\n1. Edit the .env file with your API keys:")
    print("   - POLYGON_WALLET_PRIVATE_KEY")
    print("   - CLOB_API_KEY, CLOB_SECRET, CLOB_PASS_PHRASE")
    print("   - POLYMARKET_ANALYTICS_API_KEY (if available)")
    print("   - POLYMARKET_WHALES_API_KEY (if available)")
    
    print("\n2. Run the analyze-top-traders command to find successful traders:")
    print("   python scripts/python/cli.py analyze-top-traders")
    
    print("\n3. Test the copy trader in simulation mode:")
    print("   python scripts/python/cli.py run-copy-trader")
    
    print("\n4. When ready, activate real trading by setting COPY_TRADER_ACTIVE=true in .env")
    print("   ⚠️ WARNING: Only activate real trading when you are confident in your setup!")
    
    print("\n" + "=" * 80)
    print("Thank you for setting up the Polymarket copy trader!")
    print("=" * 80)


if __name__ == "__main__":
    main() 