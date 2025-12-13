"""
Comprehensive test suite for all research services.

Tests API connectivity and validates that services return expected data formats.
Run this after configuring API keys to verify everything works.

Usage:
    python tests/test_research_services.py
    python tests/test_research_services.py --service newsapi
    python tests/test_research_services.py --verbose
"""
import sys
import argparse
from typing import List, Dict, Callable
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.research import (
    # Scientific
    search_arxiv,
    search_semantic_scholar,
    search_crossref,
    search_core,
    search_doaj,
    # Medical
    search_pubmed,
    search_europepmc,
    # Statistical
    search_oecd_data,
    search_world_bank_data,
    # News
    search_newsapi,
    search_gnews,
    # Fact-Check
    search_google_factcheck,
    search_claimbuster,
)

# ============================================================================
# TEST CONFIGURATION
# ============================================================================

# Test queries for each service
TEST_QUERIES = {
    # Scientific
    "arxiv": "machine learning",
    "semantic_scholar": "artificial intelligence",
    "crossref": "climate change",
    "core": "neural networks",
    "doaj": "renewable energy",

    # Medical
    "pubmed": "cancer treatment",
    "europepmc": "vaccine efficacy",

    # Statistical
    "oecd": "GDP growth",
    "world_bank": "poverty rate",

    # News
    "newsapi": "artificial intelligence",
    "gnews": "climate policy",

    # Fact-Check
    "google_factcheck": "climate change",
    "claimbuster": "The unemployment rate has decreased significantly.",
}

# Service functions
SERVICES = {
    "arxiv": search_arxiv,
    "semantic_scholar": search_semantic_scholar,
    "crossref": search_crossref,
    "core": search_core,
    "doaj": search_doaj,
    "pubmed": search_pubmed,
    "europepmc": search_europepmc,
    "oecd": search_oecd_data,
    "world_bank": search_world_bank_data,
    "newsapi": search_newsapi,
    "gnews": search_gnews,
    "google_factcheck": search_google_factcheck,
    "claimbuster": search_claimbuster,
}

# Service categories
CATEGORIES = {
    "scientific": ["arxiv", "semantic_scholar", "crossref", "core", "doaj"],
    "medical": ["pubmed", "europepmc"],
    "statistical": ["oecd", "world_bank"],
    "news": ["newsapi", "gnews"],
    "factcheck": ["google_factcheck", "claimbuster"],
}

# Required fields in response
REQUIRED_FIELDS = ["title", "url", "source"]

# ============================================================================
# TEST FUNCTIONS
# ============================================================================

def validate_result(result: Dict, service_name: str) -> bool:
    """
    Validate that a result has required fields.

    Args:
        result: Single result dictionary from service
        service_name: Name of service being tested

    Returns:
        True if valid, False otherwise
    """
    for field in REQUIRED_FIELDS:
        if field not in result:
            print(f"  ❌ Missing required field: {field}")
            return False
    return True


def test_service(
    name: str,
    service_func: Callable,
    query: str,
    verbose: bool = False
) -> dict:
    """
    Test a single research service.

    Args:
        name: Service name
        service_func: Service function to test
        query: Test query string
        verbose: Print detailed output

    Returns:
        Dict with test results: {success, count, error}
    """
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"Query: '{query}'")
    print(f"{'='*60}")

    try:
        # Call service
        results = service_func(query, max_results=3)

        if not results:
            print(f"⚠️  No results returned (API key missing or query failed)")
            return {"success": False, "count": 0, "error": "No results"}

        # Validate results
        all_valid = True
        for i, result in enumerate(results, 1):
            is_valid = validate_result(result, name)
            if not is_valid:
                all_valid = False

            if verbose:
                print(f"\nResult {i}:")
                print(f"  Title: {result.get('title', 'N/A')[:80]}")
                print(f"  URL: {result.get('url', 'N/A')[:80]}")
                print(f"  Source: {result.get('source', 'N/A')}")

        if all_valid:
            print(f"✅ SUCCESS: Found {len(results)} valid results")
            return {"success": True, "count": len(results), "error": None}
        else:
            print(f"❌ FAILED: Some results invalid")
            return {"success": False, "count": len(results), "error": "Invalid results"}

    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return {"success": False, "count": 0, "error": str(e)}


def print_summary(results: Dict[str, dict]):
    """
    Print test summary.

    Args:
        results: Dict mapping service name to test results
    """
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    for category, services in CATEGORIES.items():
        print(f"\n{category.upper()}:")
        for service in services:
            result = results.get(service, {})
            success = result.get("success", False)
            count = result.get("count", 0)
            error = result.get("error", "")

            status = "✅" if success else ("⚠️" if count == 0 else "❌")
            msg = f"  {status} {service:20s}"

            if success:
                msg += f" - {count} results"
            elif count == 0:
                msg += " - No results (check API key)"
            else:
                msg += f" - {error}"

            print(msg)

    # Overall stats
    total = len(results)
    successful = sum(1 for r in results.values() if r.get("success"))
    failed = sum(1 for r in results.values() if not r.get("success") and r.get("count") > 0)
    no_results = sum(1 for r in results.values() if r.get("count") == 0)

    print(f"\n{'='*60}")
    print(f"TOTAL: {total} services")
    print(f"  ✅ Successful: {successful}")
    print(f"  ❌ Failed: {failed}")
    print(f"  ⚠️  No results: {no_results} (likely missing API keys)")
    print(f"{'='*60}\n")


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Run tests based on command line arguments."""
    parser = argparse.ArgumentParser(
        description="Test research services API connectivity"
    )
    parser.add_argument(
        "--service",
        help="Test specific service only",
        choices=list(SERVICES.keys())
    )
    parser.add_argument(
        "--category",
        help="Test specific category only",
        choices=list(CATEGORIES.keys())
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Print detailed results"
    )

    args = parser.parse_args()

    # Determine which services to test
    if args.service:
        services_to_test = [args.service]
    elif args.category:
        services_to_test = CATEGORIES[args.category]
    else:
        services_to_test = list(SERVICES.keys())

    # Run tests
    results = {}
    for service_name in services_to_test:
        service_func = SERVICES[service_name]
        query = TEST_QUERIES[service_name]

        result = test_service(service_name, service_func, query, args.verbose)
        results[service_name] = result

    # Print summary
    print_summary(results)


if __name__ == "__main__":
    main()
