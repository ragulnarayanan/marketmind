"""
Run this locally to test the pipeline without deploying to GCP.
Uses your local .env for all credentials.
"""
import asyncio
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from pipeline.run_daily import fetch_news_batch, main


async def test_small():
    """Test with just 3 tickers to verify everything works."""
    print("Testing with AAPL, NVDA, MSFT...")
    results = await fetch_news_batch(["AAPL", "NVDA", "MSFT"],
                                     batch_size=3, delay=0.5)
    for ticker, count in results.items():
        print(f"  {ticker}: {count} articles")


async def test_full():
    """Run the complete pipeline."""
    await main()


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "small"
    if mode == "full":
        asyncio.run(test_full())
    else:
        asyncio.run(test_small())
