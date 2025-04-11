import typer
from devtools import pprint

from agents.polymarket.polymarket import Polymarket
from agents.connectors.chroma import PolymarketRAG
from agents.connectors.news import News
from agents.application.trade import Trader
from agents.application.executor import Executor
from agents.application.creator import Creator
from agents.polymarket.copy_trader import PolymarketCopyTrader

app = typer.Typer()
polymarket = Polymarket()
newsapi_client = News()
polymarket_rag = PolymarketRAG()


@app.command()
def get_all_markets(limit: int = 5, sort_by: str = "spread") -> None:
    """
    Query Polymarket's markets
    """
    print(f"limit: int = {limit}, sort_by: str = {sort_by}")
    markets = polymarket.get_all_markets()
    markets = polymarket.filter_markets_for_trading(markets)
    if sort_by == "spread":
        markets = sorted(markets, key=lambda x: x.spread, reverse=True)
    markets = markets[:limit]
    pprint(markets)


@app.command()
def get_relevant_news(keywords: str) -> None:
    """
    Use NewsAPI to query the internet
    """
    articles = newsapi_client.get_articles_for_cli_keywords(keywords)
    pprint(articles)


@app.command()
def get_all_events(limit: int = 5, sort_by: str = "number_of_markets") -> None:
    """
    Query Polymarket's events
    """
    print(f"limit: int = {limit}, sort_by: str = {sort_by}")
    events = polymarket.get_all_events()
    events = polymarket.filter_events_for_trading(events)
    if sort_by == "number_of_markets":
        events = sorted(events, key=lambda x: len(x.markets), reverse=True)
    events = events[:limit]
    pprint(events)


@app.command()
def create_local_markets_rag(local_directory: str) -> None:
    """
    Create a local markets database for RAG
    """
    polymarket_rag.create_local_markets_rag(local_directory=local_directory)


@app.command()
def query_local_markets_rag(vector_db_directory: str, query: str) -> None:
    """
    RAG over a local database of Polymarket's events
    """
    response = polymarket_rag.query_local_markets_rag(
        local_directory=vector_db_directory, query=query
    )
    pprint(response)


@app.command()
def ask_superforecaster(event_title: str, market_question: str, outcome: str) -> None:
    """
    Ask a superforecaster about a trade
    """
    print(
        f"event: str = {event_title}, question: str = {market_question}, outcome (usually yes or no): str = {outcome}"
    )
    executor = Executor()
    response = executor.get_superforecast(
        event_title=event_title, market_question=market_question, outcome=outcome
    )
    print(f"Response:{response}")


@app.command()
def create_market() -> None:
    """
    Format a request to create a market on Polymarket
    """
    c = Creator()
    market_description = c.one_best_market()
    print(f"market_description: str = {market_description}")


@app.command()
def ask_llm(user_input: str) -> None:
    """
    Ask a question to the LLM and get a response.
    """
    executor = Executor()
    response = executor.get_llm_response(user_input)
    print(f"LLM Response: {response}")


@app.command()
def ask_polymarket_llm(user_input: str) -> None:
    """
    What types of markets do you want trade?
    """
    executor = Executor()
    response = executor.get_polymarket_llm(user_input=user_input)
    print(f"LLM + current markets&events response: {response}")


@app.command()
def run_autonomous_trader() -> None:
    """
    Let an autonomous system trade for you.
    """
    trader = Trader()
    trader.one_best_trade()


@app.command()
def run_copy_trader(
    config_path: str = "config/copy_trader_config.json", 
    add_trader: str = None,
    find_top_traders: bool = False,
    min_win_rate: float = 0.7,
    min_pnl: float = 50000,
    activate_trading: bool = False
) -> None:
    """
    Run the Polymarket copy trader bot.
    
    This bot monitors successful traders on Polymarket and copies their trades.
    
    Args:
        config_path: Path to the configuration file
        add_trader: Address of a trader to add to the watch list
        find_top_traders: Whether to search for and add top traders before starting
        min_win_rate: Minimum win rate for top traders (if finding top traders)
        min_pnl: Minimum profit and loss for top traders (if finding top traders)
        activate_trading: Whether to activate actual trading (default: False - just simulate)
    """
    copy_trader = PolymarketCopyTrader(config_path=config_path)
    
    # If trading activation was requested
    if activate_trading:
        print("Activating trading functionality...")
        copy_trader.config["trading_active"] = True
        copy_trader._save_config()
        print("Trading has been activated. The bot will execute real trades.")
    
    # If finding top traders was requested
    if find_top_traders:
        print(f"Finding top traders (min win rate: {min_win_rate:.1%}, min PnL: ${min_pnl:.2f})...")
        
        # Update analytics config
        copy_trader.config["analytics"]["enabled"] = True
        copy_trader.config["analytics"]["min_win_rate"] = min_win_rate
        copy_trader.config["analytics"]["min_pnl"] = min_pnl
        copy_trader._save_config()
        
        # Run the trader update
        copy_trader.update_traders_from_analytics()
    
    # If an address was provided, add it to the watch list
    if add_trader:
        copy_trader.add_watched_trader(add_trader)
        print(f"Added trader {add_trader} to watch list")
    
    # Start monitoring
    try:
        print("Starting copy trader. Press Ctrl+C to stop.")
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
        
        if stats.get("trader_stats"):
            print("\nWatched Trader Performance:")
            for addr, info in stats["trader_stats"].items():
                print(f"  {addr} - PnL: ${info['pnl']:.2f}, Win Rate: {info['win_rate']:.2%}")


@app.command()
def analyze_top_traders(count: int = 10, min_win_rate: float = 0.6, min_pnl: float = 10000) -> None:
    """
    Analyze and display top traders on Polymarket.
    
    Args:
        count: Number of top traders to display
        min_win_rate: Minimum win rate for filtering traders
        min_pnl: Minimum profit and loss for filtering traders
    """
    from agents.polymarket.analytics import PolymarketAnalytics
    
    analytics = PolymarketAnalytics()
    
    print(f"Finding top traders (min win rate: {min_win_rate:.1%}, min PnL: ${min_pnl:.2f})...")
    recommended = analytics.get_recommended_traders(min_win_rate=min_win_rate, min_pnl=min_pnl)
    
    print(f"\nFound {len(recommended)} traders matching criteria.")
    print(f"\nTop {min(count, len(recommended))} recommended traders:")
    
    for i, trader in enumerate(recommended[:count], 1):
        print(f"\n{i}. Address: {trader.address}")
        if trader.username:
            print(f"   Username: {trader.username}")
        print(f"   PnL: ${trader.pnl:.2f}")
        print(f"   Win Rate: {trader.win_rate:.2%}")
        print(f"   Total Positions: {trader.total_positions}")
        print(f"   Active Positions: {trader.active_positions}")
        
    print("\nTo add these traders to your copy trader, use:")
    for trader in recommended[:min(3, len(recommended))]:
        print(f"  python scripts/python/cli.py run-copy-trader --add-trader \"{trader.address}\"")


@app.command()
def config_copy_trader(
    config_path: str = "config/copy_trader_config.json",
    min_amount: float = None,
    max_amount: float = None, 
    copy_percentage: float = None,
    auto_update: bool = None,
    activate_trading: bool = None
) -> None:
    """
    Configure the copy trader settings.
    
    Args:
        config_path: Path to the configuration file
        min_amount: Minimum amount to copy (in USD)
        max_amount: Maximum amount to copy (in USD)
        copy_percentage: Percentage of trader's amount to copy (0.1 = 10%)
        auto_update: Whether to automatically update the traders list
        activate_trading: Whether to activate actual trading
    """
    from agents.polymarket.copy_trader import PolymarketCopyTrader
    
    # Load the current configuration
    copy_trader = PolymarketCopyTrader(config_path=config_path)
    
    # Apply changes if provided
    if min_amount is not None:
        copy_trader.config["min_amount_to_copy"] = min_amount
        print(f"Minimum amount to copy set to ${min_amount}")
        
    if max_amount is not None:
        copy_trader.config["max_amount_to_copy"] = max_amount
        print(f"Maximum amount to copy set to ${max_amount}")
        
    if copy_percentage is not None:
        copy_trader.config["copy_percentage"] = copy_percentage
        print(f"Copy percentage set to {copy_percentage:.1%}")
        
    if auto_update is not None:
        copy_trader.config["analytics"]["auto_update_traders"] = auto_update
        print(f"Auto-update traders set to {auto_update}")
        
    if activate_trading is not None:
        copy_trader.config["trading_active"] = activate_trading
        if activate_trading:
            print("Trading has been ACTIVATED. The bot will execute real trades.")
        else:
            print("Trading has been DEACTIVATED. The bot will only simulate trades.")
    
    # Save the configuration
    copy_trader._save_config()
    
    # Show current configuration summary
    print("\nCurrent configuration:")
    print(f"Minimum amount to copy: ${copy_trader.config['min_amount_to_copy']}")
    print(f"Maximum amount to copy: ${copy_trader.config['max_amount_to_copy']}")
    print(f"Copy percentage: {copy_trader.config['copy_percentage']:.1%}")
    print(f"Trading active: {copy_trader.config['trading_active']}")
    print(f"Auto-update traders: {copy_trader.config['analytics']['auto_update_traders']}")
    
    if copy_trader.watched_traders:
        print(f"\nCurrently watching {len(copy_trader.watched_traders)} traders")
    else:
        print("\nNo traders currently in watch list.")
        print("Use 'analyze-top-traders' command to find traders to copy.")


if __name__ == "__main__":
    app()
