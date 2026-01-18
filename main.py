"""Main entry point for the AI news aggregator."""

from app.services.aggregator import run_aggregator


def main():
    """Run the news aggregator."""
    # Default: collect content from last 48 hours
    results = run_aggregator(hours=48)
    return results


if __name__ == "__main__":
    main()

