import os
import time
import json
import datetime
import random
from typing import List, Dict, Any, Optional
from pathlib import Path

import httpx
from dotenv import load_dotenv

from py_clob_client.client import ClobClient
from py_clob_client.clob_types import TradeParams, OrderArgs, OrderType
from py_clob_client.order_builder.constants import BUY, SELL

from agents.polymarket.polymarket import Polymarket
from agents.polymarket.analytics import PolymarketAnalytics, TraderInfo
from agents.utils.objects import Trade, SimpleMarket


class PolymarketCopyTrader:
    """
    A class for copy trading on Polymarket.
    Track top traders and mirror their trades.
    """
    
    def __init__(self, config_path: str = "config/copy_trader_config.json"):
        """
        Initialize the copy trader.
        
        Args:
            config_path: Path to the configuration file
        """
        load_dotenv()
        self.polymarket = Polymarket()
        self.analytics = PolymarketAnalytics()
        self.config_path = config_path
        self.config = self._load_config(config_path)
        
        # Override config with environment variables if provided
        env_trading_active = os.getenv("COPY_TRADER_ACTIVE", "").lower()
        if env_trading_active in ("true", "1", "yes"):
            print("Trading activated via environment variable")
            self.config["trading_active"] = True
        elif env_trading_active in ("false", "0", "no"):
            print("Trading deactivated via environment variable")
            self.config["trading_active"] = False
        
        self.watched_traders = self.config.get("watched_traders", [])
        self.trade_history = {}
        self.last_check_time = {}
        
        # Initialize check times for each watched trader
        for trader in self.watched_traders:
            self.last_check_time[trader] = datetime.datetime.now() - datetime.timedelta(minutes=60)
        
        # Create data directory for storing trade history
        self.data_dir = Path("data/copy_trader")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Load existing trade history if it exists
        self._load_trade_history()
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """
        Load configuration from JSON file.
        If file doesn't exist, create a default configuration.
        
        Args:
            config_path: Path to the configuration file
            
        Returns:
            Dict containing configuration settings
        """
        config_file = Path(config_path)
        
        # Create config directory if it doesn't exist
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        if config_file.exists():
            with open(config_file, 'r') as f:
                return json.load(f)
        else:
            # Default configuration
            default_config = {
                "watched_traders": [],
                "min_amount_to_copy": 50,  # Minimum amount in USD to copy
                "max_amount_to_copy": 500,  # Maximum amount in USD to copy
                "copy_percentage": 0.1,  # Copy 10% of the trader's amount
                "min_copy_delay": 30,  # Minimum delay in seconds before copying
                "max_copy_delay": 300,  # Maximum delay in seconds before copying
                "blacklisted_markets": [],  # Markets to ignore
                "whitelist_only": False,  # If True, only copy trades for whitelisted markets
                "whitelisted_markets": [],  # Markets to specifically copy
                "copy_buys": True,  # Whether to copy buy trades
                "copy_sells": True,  # Whether to copy sell trades
                "max_positions_per_market": 3,  # Maximum positions to take per market
                "max_daily_trades": 10,  # Maximum trades to execute per day
                "max_daily_amount": 1000,  # Maximum amount to trade per day in USD
                "auto_close_positions": True,  # Whether to automatically close positions when original trader closes
                "trading_active": False,  # Whether to execute trades or just track
                "polling_interval": 60,  # How often to check for new trades in seconds
                "analytics": {
                    "enabled": True,  # Whether to use analytics to find top traders
                    "min_win_rate": 0.7,  # Minimum win rate for recommended traders
                    "min_pnl": 50000,  # Minimum PnL for recommended traders
                    "auto_update_traders": False,  # Whether to automatically update watched traders list
                    "max_auto_traders": 5,  # Maximum number of traders to auto-add
                    "update_interval_hours": 24  # How often to update the traders list
                }
            }
            
            # Save default configuration
            with open(config_file, 'w') as f:
                json.dump(default_config, f, indent=4)
            
            return default_config
    
    def _save_config(self) -> None:
        """Save configuration to disk"""
        config_file = Path(self.config_path)
        with open(config_file, 'w') as f:
            json.dump(self.config, f, indent=4)
    
    def _load_trade_history(self) -> None:
        """Load existing trade history from disk"""
        history_file = self.data_dir / "trade_history.json"
        if history_file.exists():
            with open(history_file, 'r') as f:
                self.trade_history = json.load(f)
    
    def _save_trade_history(self) -> None:
        """Save trade history to disk"""
        history_file = self.data_dir / "trade_history.json"
        with open(history_file, 'w') as f:
            json.dump(self.trade_history, f, indent=4)
    
    def add_watched_trader(self, trader_address: str) -> None:
        """
        Add a trader to the watch list.
        
        Args:
            trader_address: The Ethereum address of the trader to watch
        """
        if trader_address not in self.watched_traders:
            self.watched_traders.append(trader_address)
            self.last_check_time[trader_address] = datetime.datetime.now() - datetime.timedelta(minutes=60)
            self.config["watched_traders"] = self.watched_traders
            
            # Save updated configuration
            self._save_config()
            
            print(f"Added trader {trader_address} to watch list")
    
    def remove_watched_trader(self, trader_address: str) -> None:
        """
        Remove a trader from the watch list.
        
        Args:
            trader_address: The Ethereum address of the trader to remove
        """
        if trader_address in self.watched_traders:
            self.watched_traders.remove(trader_address)
            if trader_address in self.last_check_time:
                del self.last_check_time[trader_address]
            
            self.config["watched_traders"] = self.watched_traders
            
            # Save updated configuration
            self._save_config()
            
            print(f"Removed trader {trader_address} from watch list")
    
    def update_traders_from_analytics(self) -> None:
        """
        Update the watched traders list using analytics recommendations
        """
        if not self.config.get("analytics", {}).get("enabled", False):
            print("Analytics-based trader updates are disabled in config")
            return
        
        min_win_rate = self.config.get("analytics", {}).get("min_win_rate", 0.7)
        min_pnl = self.config.get("analytics", {}).get("min_pnl", 50000)
        max_traders = self.config.get("analytics", {}).get("max_auto_traders", 5)
        
        print(f"Updating traders from analytics (min win rate: {min_win_rate:.1%}, min PnL: ${min_pnl})")
        
        # Get recommended traders from analytics
        recommended = self.analytics.get_recommended_traders(
            min_win_rate=min_win_rate, 
            min_pnl=min_pnl
        )
        
        # Add recommended traders to watch list (up to max_traders)
        added_count = 0
        for trader in recommended:
            if trader.address not in self.watched_traders and added_count < max_traders:
                self.add_watched_trader(trader.address)
                added_count += 1
                print(f"Auto-added trader {trader.address} (PnL: ${trader.pnl:.2f}, Win Rate: {trader.win_rate:.2%})")
        
        print(f"Added {added_count} new traders to watch list")
    
    def should_update_traders(self) -> bool:
        """
        Check if it's time to update the traders list from analytics
        
        Returns:
            True if it's time to update, False otherwise
        """
        if not self.config.get("analytics", {}).get("auto_update_traders", False):
            return False
        
        # Check when traders were last updated
        last_update_file = self.data_dir / "last_traders_update.txt"
        
        if not last_update_file.exists():
            # Never updated, so yes, update now
            return True
        
        with open(last_update_file, 'r') as f:
            last_update_str = f.read().strip()
            last_update = datetime.datetime.fromisoformat(last_update_str)
        
        # Check if enough time has passed
        update_interval = self.config.get("analytics", {}).get("update_interval_hours", 24)
        next_update = last_update + datetime.timedelta(hours=update_interval)
        
        return datetime.datetime.now() >= next_update
    
    def mark_traders_updated(self) -> None:
        """Mark that traders list has been updated"""
        last_update_file = self.data_dir / "last_traders_update.txt"
        with open(last_update_file, 'w') as f:
            f.write(datetime.datetime.now().isoformat())
    
    def get_recent_trades(self, trader_address: str) -> List[Dict[str, Any]]:
        """
        Get recent trades for a specific trader.
        
        Args:
            trader_address: The Ethereum address of the trader
            
        Returns:
            List of trades by the trader
        """
        try:
            # Use last check time to only get recent trades
            last_check = self.last_check_time.get(trader_address, 
                                                datetime.datetime.now() - datetime.timedelta(minutes=60))
            
            # Convert to Unix timestamp
            after_timestamp = int(last_check.timestamp())
            
            # Get trades where the trader is the maker
            trades_as_maker = self.polymarket.client.get_trades(
                TradeParams(
                    maker_address=trader_address,
                    after=str(after_timestamp)
                )
            )
            
            # Get trades where the trader is the taker
            trades_as_taker = self.polymarket.client.get_trades(
                TradeParams(
                    taker=trader_address,
                    after=str(after_timestamp)
                )
            )
            
            # Update the last check time for this trader
            self.last_check_time[trader_address] = datetime.datetime.now()
            
            # Combine and return all trades
            return trades_as_maker + trades_as_taker
            
        except Exception as e:
            print(f"Error getting recent trades for {trader_address}: {e}")
            return []
    
    def analyze_trade(self, trade: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a trade to determine if it should be copied.
        
        Args:
            trade: The trade to analyze
            
        Returns:
            Dict with analysis results and copy decision
        """
        # Check if the trade meets the minimum amount requirement
        size = float(trade.get("size", 0))
        price = float(trade.get("price", 0))
        side = trade.get("side", "")
        market_id = trade.get("market", "")
        asset_id = trade.get("asset_id", "")
        
        # Calculate trade value in USD
        trade_value = size * price if side == "SELL" else size
        
        # Check if the trade meets our copying criteria
        should_copy = (
            trade_value >= self.config.get("min_amount_to_copy", 0) and
            (market_id not in self.config.get("blacklisted_markets", [])) and
            (not self.config.get("whitelist_only", False) or 
             market_id in self.config.get("whitelisted_markets", [])) and
            ((side == "BUY" and self.config.get("copy_buys", True)) or
             (side == "SELL" and self.config.get("copy_sells", True)))
        )
        
        # Calculate the amount to copy based on percentage
        copy_percentage = self.config.get("copy_percentage", 0.1)
        copy_amount = trade_value * copy_percentage
        
        # Apply min/max bounds
        max_amount = self.config.get("max_amount_to_copy", 500)
        copy_amount = min(copy_amount, max_amount)
        
        return {
            "original_trade": trade,
            "should_copy": should_copy,
            "copy_amount": copy_amount,
            "market_id": market_id,
            "asset_id": asset_id,
            "side": side,
            "price": price
        }
    
    def execute_copy_trade(self, trade_analysis: Dict[str, Any]) -> Optional[str]:
        """
        Execute a copy of the analyzed trade.
        
        Args:
            trade_analysis: The analyzed trade data
            
        Returns:
            Trade ID if successful, None otherwise
        """
        # Check if trading is active in the configuration
        if not self.config.get("trading_active", False):
            print("Trading is not active. Set 'trading_active' to True in the config to execute trades.")
            return None
        
        try:
            # Prepare order parameters
            asset_id = trade_analysis["asset_id"]
            side = BUY if trade_analysis["side"] == "BUY" else SELL
            price = trade_analysis["price"]
            
            # Calculate size to buy
            copy_amount = trade_analysis["copy_amount"]
            size = copy_amount if side == SELL else copy_amount / price
            
            # Execute the order
            trade_id = self.polymarket.execute_order(
                price=price,
                size=size,
                side=side,
                token_id=asset_id
            )
            
            # Record this trade in our history
            self._record_copy_trade(trade_analysis, trade_id)
            
            print(f"Successfully copied trade with ID: {trade_id}")
            return trade_id
            
        except Exception as e:
            print(f"Error executing copy trade: {e}")
            return None
    
    def _record_copy_trade(self, trade_analysis: Dict[str, Any], trade_id: str) -> None:
        """
        Record a copied trade in the trade history.
        
        Args:
            trade_analysis: The analyzed trade data
            trade_id: The ID of the executed trade
        """
        timestamp = datetime.datetime.now().isoformat()
        
        # Create record
        record = {
            "timestamp": timestamp,
            "original_trade": trade_analysis["original_trade"],
            "copied_trade_id": trade_id,
            "copy_amount": trade_analysis["copy_amount"],
            "market_id": trade_analysis["market_id"],
            "asset_id": trade_analysis["asset_id"],
            "side": trade_analysis["side"],
            "price": trade_analysis["price"]
        }
        
        # Add to trade history
        if trade_analysis["market_id"] not in self.trade_history:
            self.trade_history[trade_analysis["market_id"]] = []
        
        self.trade_history[trade_analysis["market_id"]].append(record)
        
        # Save updated trade history
        self._save_trade_history()
    
    def monitor_traders(self) -> None:
        """
        Main monitoring loop that checks for new trades by watched traders
        and copies them according to the configuration.
        """
        print(f"Starting to monitor {len(self.watched_traders)} traders.")
        
        # Check if we need to update traders from analytics first
        if self.should_update_traders():
            print("Auto-update of traders is enabled. Updating watched traders...")
            self.update_traders_from_analytics()
            self.mark_traders_updated()
        
        while True:
            try:
                # Check if we should update the traders list
                if self.should_update_traders():
                    print("Auto-update interval reached. Updating watched traders...")
                    self.update_traders_from_analytics()
                    self.mark_traders_updated()
                
                # If we have no traders to watch, sleep and retry
                if not self.watched_traders:
                    print("No traders in watch list. Please add traders or enable auto-update.")
                    time.sleep(60)
                    continue
                
                # Shuffle the list of traders to avoid always checking in the same order
                traders_to_check = self.watched_traders.copy()
                random.shuffle(traders_to_check)
                
                for trader in traders_to_check:
                    print(f"Checking for new trades by {trader}...")
                    
                    # Get recent trades for this trader
                    recent_trades = self.get_recent_trades(trader)
                    print(f"Found {len(recent_trades)} recent trades.")
                    
                    # Process each trade
                    for trade in recent_trades:
                        # Analyze the trade
                        analysis = self.analyze_trade(trade)
                        
                        # If we should copy it, execute the trade
                        if analysis["should_copy"]:
                            print(f"Copying trade: {trade['id']}")
                            
                            # Add random delay before copying
                            min_delay = self.config.get("min_copy_delay", 30)
                            max_delay = self.config.get("max_copy_delay", 300)
                            delay = min_delay + (max_delay - min_delay) * random.random()
                            print(f"Waiting {delay:.2f} seconds before executing copy...")
                            time.sleep(delay)
                            
                            # Execute the copy trade
                            trade_id = self.execute_copy_trade(analysis)
                            
                            if trade_id:
                                print(f"Successfully copied trade as {trade_id}")
                            else:
                                print("Failed to copy trade.")
                        else:
                            print(f"Skipping trade {trade['id']}: does not meet copy criteria")
                
                # Sleep for the configured polling interval
                interval = self.config.get("polling_interval", 60)
                print(f"Sleeping for {interval} seconds...")
                time.sleep(interval)
                
            except Exception as e:
                print(f"Error in monitoring loop: {e}")
                # Sleep for a bit before retrying
                time.sleep(30)
    
    def show_statistics(self) -> Dict[str, Any]:
        """
        Generate and return statistics about copied trades.
        
        Returns:
            Dict with statistics
        """
        # Count total trades
        total_trades = sum(len(trades) for trades in self.trade_history.values())
        
        # Calculate total amount traded
        total_amount = sum(
            trade["copy_amount"] 
            for market_trades in self.trade_history.values() 
            for trade in market_trades
        )
        
        # Count markets
        markets_count = len(self.trade_history)
        
        # Get most recent trade
        most_recent = None
        most_recent_time = None
        for market_trades in self.trade_history.values():
            for trade in market_trades:
                trade_time = datetime.datetime.fromisoformat(trade["timestamp"])
                if most_recent_time is None or trade_time > most_recent_time:
                    most_recent = trade
                    most_recent_time = trade_time
        
        # Get trader analytics if available
        trader_stats = {}
        for trader in self.watched_traders:
            try:
                info = self.analytics.analyze_trader_performance(trader)
                if info:
                    trader_stats[trader] = {
                        "pnl": info.pnl,
                        "win_rate": info.win_rate,
                        "positions": info.total_positions
                    }
            except Exception as e:
                print(f"Error getting analytics for {trader}: {e}")
        
        return {
            "total_trades": total_trades,
            "total_amount_traded": total_amount,
            "markets_count": markets_count,
            "most_recent_trade": most_recent,
            "traders_watched": len(self.watched_traders),
            "trader_stats": trader_stats
        }


def main():
    """Main entry point to run the copy trader"""
    copy_trader = PolymarketCopyTrader()
    
    # Example: Add some watched traders manually
    # copy_trader.add_watched_trader("0x1234567890abcdef1234567890abcdef12345678")
    
    # Example: Update traders based on analytics
    # copy_trader.update_traders_from_analytics()
    
    # Start monitoring
    try:
        copy_trader.monitor_traders()
    except KeyboardInterrupt:
        print("Copy trader stopped.")
        
        # Show statistics on exit
        stats = copy_trader.show_statistics()
        print("\nTrading Statistics:")
        print(f"Total Trades: {stats['total_trades']}")
        print(f"Total Amount Traded: ${stats['total_amount_traded']:.2f}")
        print(f"Markets Traded: {stats['markets_count']}")
        print(f"Traders Watched: {stats['traders_watched']}")
        
        if stats["trader_stats"]:
            print("\nWatched Trader Performance:")
            for addr, info in stats["trader_stats"].items():
                print(f"  {addr} - PnL: ${info['pnl']:.2f}, Win Rate: {info['win_rate']:.2%}")


if __name__ == "__main__":
    main() 