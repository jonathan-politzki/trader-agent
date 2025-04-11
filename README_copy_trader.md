# Polymarket Copy Trader Bot

A bot for automatically tracking and copying the most successful traders on Polymarket.

## Overview

This bot helps you:

1. Identify top-performing traders on Polymarket using analytics services
2. Monitor their trades in real-time
3. Automatically execute similar trades with configurable parameters
4. Track performance and statistics

## Features

- **Analytics Integration**: Find top traders based on win rate and PnL
- **Flexible Configuration**: Set minimum/maximum trade amounts, delay timings, etc.
- **Trade Filtering**: Choose which trades to copy based on various criteria
- **Market Filtering**: Focus on specific markets with whitelist/blacklist support
- **Safety Limits**: Set daily trade limits and maximum position sizes
- **Performance Tracking**: Review detailed statistics on copied trades

## Installation

This bot is part of the Polymarket Agents framework. Follow the main installation instructions in the main README.md file, then:

1. Run the setup script to configure your API keys:
   ```bash
   python scripts/python/setup_copy_trader.py
   ```

2. Edit your `.env` file to add the required API keys:
   ```
   # Polygon wallet private key (required for trading)
   POLYGON_WALLET_PRIVATE_KEY=0xYourPrivateKeyHere

   # Polymarket CLOB API keys
   CLOB_API_KEY=your_api_key_here
   CLOB_SECRET=your_api_secret_here
   CLOB_PASS_PHRASE=your_passphrase_here

   # Analytics service API keys (for the copy trader)
   POLYMARKET_ANALYTICS_API_KEY=your_polymarket_analytics_api_key
   POLYMARKET_WHALES_API_KEY=your_polymarket_whales_api_key

   # Copy trader settings
   # Set to true to activate real trading (use with caution!)
   COPY_TRADER_ACTIVE=false
   ```

3. Configure your trading parameters in `config/copy_trader_config.json`

## API Key Setup

To use the copy trader with real data and trading capability, you'll need:

1. **Polygon Wallet**: A cryptocurrency wallet on the Polygon network with:
   - MATIC tokens for gas fees
   - USDC tokens for trading

2. **Polymarket API Keys**: Required for trading access
   - Sign up at [Polymarket Developer Portal](https://docs.polymarket.com/)
   - Follow their authorization procedures
   - Add the keys to your `.env` file

3. **Analytics API Keys** (optional but recommended):
   - [PolymarketAnalytics.com](https://polymarketanalytics.com/) - Provides trader performance data
   - [PolymarketWhales.info](https://polymarketwhales.info/) - Tracks high-value traders

Without analytics API keys, the system will still work but will use the subgraph directly or placeholder data.

## Usage

### Finding Top Traders

To analyze and display top traders on Polymarket:

```bash
python scripts/python/cli.py analyze-top-traders --count 10 --min-win-rate 0.7 --min-pnl 50000
```

### Configuring the Bot

To configure the copy trader settings:

```bash
python scripts/python/cli.py config-copy-trader --min-amount 50 --max-amount 500 --copy-percentage 0.1
```

Parameters:
- `--min-amount`: Minimum amount to copy (in USD)
- `--max-amount`: Maximum amount to copy (in USD) 
- `--copy-percentage`: Percentage of trader's amount to copy (0.1 = 10%)
- `--auto-update`: Whether to automatically update the traders list (true/false)
- `--activate-trading`: Whether to activate actual trading (true/false)

### Running the Bot

To start the copy trader bot:

```bash
python scripts/python/cli.py run-copy-trader
```

Additional options:
- `--add-trader "0x123..."`: Add a specific trader to watch list
- `--find-top-traders`: Automatically find and add top traders before starting
- `--min-win-rate 0.7`: Minimum win rate for auto-added traders
- `--min-pnl 50000`: Minimum profit and loss for auto-added traders
- `--activate-trading`: Enable actual trading (default is simulation mode)

To run the bot in the background:

```bash
nohup python scripts/python/cli.py run-copy-trader > copy_trader.log 2>&1 &
```

## Configuration

Edit the `config/copy_trader_config.json` file to customize your bot. Key settings include:

```json
{
    "watched_traders": ["0x123..."],
    "min_amount_to_copy": 50,
    "max_amount_to_copy": 500,
    "copy_percentage": 0.1,
    "min_copy_delay": 30,
    "max_copy_delay": 300,
    "blacklisted_markets": [],
    "whitelist_only": false,
    "whitelisted_markets": [],
    "copy_buys": true,
    "copy_sells": true,
    "max_positions_per_market": 3,
    "max_daily_trades": 10,
    "max_daily_amount": 1000,
    "auto_close_positions": true,
    "trading_active": false,
    "polling_interval": 60,
    "analytics": {
        "enabled": true,
        "min_win_rate": 0.7,
        "min_pnl": 50000,
        "auto_update_traders": false,
        "max_auto_traders": 5,
        "update_interval_hours": 24
    }
}
```

## Important Notes

- **Always start in simulation mode** (trading_active = false) to test your settings
- The bot initially runs without executing actual trades - set `trading_active` to `true` to enable real trading
- Be aware of Polymarket's Terms of Service - ensure you're in an eligible jurisdiction
- Past performance of traders does not guarantee future results

## How It Works

1. The bot monitors specified top traders at regular intervals
2. When a trader makes a trade, the bot analyzes it against your criteria
3. If the trade meets your requirements, the bot copies it with a random delay
4. All trades are recorded and statistics are maintained for review

## Troubleshooting

### Common Issues:

1. **No traders found**: Make sure your API keys are valid and/or lower the minimum requirements for traders.

2. **API request failures**: Check your network connection and API key validity.

3. **Trading not activating**: Verify that `trading_active` is set to `true` in your config or set `COPY_TRADER_ACTIVE=true` in your `.env` file.

4. **Insufficient funds**: Ensure your wallet has enough USDC for trading and MATIC for gas fees.

### Debug Mode:

Run the bot with debug logging for more detailed output:

```bash
LOGLEVEL=DEBUG python scripts/python/cli.py run-copy-trader
```

## Data Sources

The copy trader can get top trader information from:

1. PolymarketAnalytics.com - Frontend analytics service
2. PolymarketWhales.info - Whale watching service
3. Polymarket Subgraph - Direct subgraph queries for historical performance

## Support

If you encounter any issues, please open an issue on the GitHub repository. 