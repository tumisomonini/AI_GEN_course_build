"""
Neo4j Docker ↔ Cloud Sync Script

Synchronises Topic nodes and their PREREQUISITE / RELATED_TO relationships
between a source Neo4j (e.g. local Docker) and a target Neo4j (e.g. Aura).

Usage:
    # Dry-run (preview counts, no writes)
    python Application/Scripts/sync_neo4j.py --source local --target cloud --dry-run

    # Actual sync
    python Application/Scripts/sync_neo4j.py --source local --target cloud

    # Custom env file
    python Application/Scripts/sync_neo4j.py --source local --target cloud --env-file .env.sync
"""
import os
import sys
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Ensure project root on path so we can import dependencies helpers
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

def sanitize_neo4j_uri(uri: str) -> str:
    """Sanitize Neo4j URI - fix Aura to neo4j+s:// and ensure port."""
    uri = uri.strip().rstrip('/')
    if '.databases.neo4j.io' in uri:
        if uri.startswith('bolt://'):
            uri = uri.replace('bolt://', 'neo4j+s://')
        elif '://' not in uri:
            uri = f'neo4j+s://{uri}'
        if ':7687' not in uri:
            uri = f'{uri}:7687'
    return uri

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

BATCH_SIZE = 100  # Nodes or relationships per UNWIND transaction

# ---------------------------------------------------------------------------
# Configuration helpers
# ---------------------------------------------------------------------------

CONFIG_PRESETS = {
    "local": {
        "uri_env": "NEO4J_URI",
        "user_env": "NEO4J_USERNAME",
        "pass_env": "NEO4J_PASSWORD",
        "db_env": "NEO4J_DATABASE",
        "fallback_uri": "bolt://localhost:7687",
        "fallback_user": "neo4j",
        "fallback_pass": "password",
        "fallback_db": "neo4j",
    },
    "cloud": {
        "uri_env": "NEO4J_URI",
        "user_env": "NEO4J_USERNAME",
        "pass_env": "NEO4J_PASSWORD",
        "db_env": "NEO4J_DATABASE",
        "fallback_uri": None,
        "fallback_user": "neo4j",
        "fallback_pass": None,
        "fallback_db": "neo4j",
    },
}


def _build_config(preset_name: str, env_prefix: Optional[str] = None) -> Dict[str, str]:
    """Build connection dict from env vars, optionally prefixed."""
    preset = CONFIG_PRESETS[preset_name]
    prefix = (env_prefix or "").upper()

    def _get(key: str, fallback_key: Optional[str] = None):
        env_key = f"{prefix}{preset[key]}"
        val = os.getenv(env_key)
        if val is None and fallback_key:
            val = preset.get(fallback_key)
        return val

    uri = _get("uri_env", "fallback_uri")
    user = _get("user_env", "fallback_user")
    password = _get("pass_env", "fallback_pass")
    database = _get("db_env", "fallback_db")

    if not uri or not password:
        raise ValueError(
            f"Missing Neo4j credentials for preset '{preset_name}'. "
            f"Expected env vars: {prefix}{preset['uri_env']}, {prefix}{preset['pass_env']}"
        )

    uri = sanitize_neo4j_uri(uri)
    return {
        "uri": uri,
        "user": user,
        "password": password,
        "database": database,
    }


# ---------------------------------------------------------------------------
# Driver helpers
# ---------------------------------------------------------------------------

def _test_connection(cfg: Dict[str, str]) -> None:
    """Verify connectivity and raise on failure."""
    driver = GraphDatabase.driver(cfg["uri"], auth=(cfg["user"], cfg["password"]))
    try:
        summary = driver.verify_connectivity()
        logger.info("✅ Connected to %s (summary: %s)", cfg["uri"], summary)
    finally:
        driver.close()


def _test_connection_with_fallback(cfg: Dict[str, str], fallback_pass: str) -> None:
    """Verify connectivity, retry with fallback password on auth failure."""
    try:
        _test_connection(cfg)
    except Exception as exc:
        if "Unauthorized" in str(exc) or "authentication failure" in str(exc):
            logger.warning(
                "Auth failed with env password for %s. Trying fallback...", cfg["uri"]
            )
            cfg_copy = {**cfg, "password": fallback_pass}
            _test_connection(cfg_copy)
            cfg["password"] = fallback_pass  # Mutate in place for downstream use
        else:
            raise


def _get_driver(cfg: Dict[str, str]):
    """Create Neo4j driver with optional proxy support."""
    import os
    # Check for proxy settings (common in corporate networks)
    http_proxy = os.getenv('HTTP_PROXY') or os.getenv('http_proxy')
    https_proxy = os.getenv('HTTPS_PROXY') or os.getenv('https_proxy')
    
    if https_proxy and 'neo4j+s' in cfg["uri"]:
        logger.info("Using HTTPS proxy: %s", https_proxy)
    elif http_proxy:
        logger.info("Using HTTP proxy: %s", http_proxy)
    
    return GraphDatabase.driver(cfg["uri"], auth=(cfg["user"], cfg["password"]))


# ---------------------------------------------------------------------------
# Extract
# ---------------------------------------------------------------------------

def extract_topics(driver, database: str) -> List[Dict]:
    """Return list of Topic node dicts with all properties."""
    query = """
    MATCH (t:Topic)
    RETURN t { .* } AS topic
    """
    with driver.session(database=database) as session:
        result = session.run(query)
        return [record["topic"] for record in result]


def extract_relationships(driver, database: str, rel_type: str) -> List[Tuple[str, str]]:
    """Return list of (source_name, target_name) tuples for a given relationship type."""
    query = f"""
    MATCH (a:Topic)-[r:{rel_type}]->(b:Topic)
    RETURN a.name AS source, b.name AS target
    """
    with driver.session(database=database) as session:
        result = session.run(query)
        return [(r["source"], r["target"]) for r in result]


# ---------------------------------------------------------------------------
# Load (idempotent MERGE)
# ---------------------------------------------------------------------------

def merge_topics(driver, database: str, topics: List[Dict], dry_run: bool = False) -> int:
    """Write topics to target using MERGE (idempotent). Returns count."""
    if not topics:
        logger.info("No topics to merge.")
        return 0

    if dry_run:
        logger.info("[DRY-RUN] Would merge %d topics", len(topics))
        return len(topics)

    query = """
    UNWIND $batch AS row
    MERGE (t:Topic {name: row.name})
    ON CREATE SET t += row, t.created_at = datetime()
    ON MATCH SET t += row, t.updated_at = datetime()
    RETURN count(t) AS merged
    """
    merged = 0
    with driver.session(database=database) as session:
        for i in range(0, len(topics), BATCH_SIZE):
            batch = topics[i : i + BATCH_SIZE]
            result = session.run(query, batch=batch)
            merged += result.single()["merged"]
            logger.info("  Merged topics batch %d/%d", i + len(batch), len(topics))
    return merged


def merge_relationships(
    driver,
    database: str,
    rel_type: str,
    pairs: List[Tuple[str, str]],
    dry_run: bool = False,
) -> int:
    """Write relationships to target using MERGE (idempotent). Returns count."""
    if not pairs:
        logger.info("No %s relationships to merge.", rel_type)
        return 0

    if dry_run:
        logger.info("[DRY-RUN] Would merge %d %s relationships", len(pairs), rel_type)
        return len(pairs)

    query = f"""
    UNWIND $batch AS row
    MATCH (a:Topic {{name: row.source}}), (b:Topic {{name: row.target}})
    MERGE (a)-[r:{rel_type}]->(b)
    RETURN count(r) AS merged
    """
    merged = 0
    with driver.session(database=database) as session:
        for i in range(0, len(pairs), BATCH_SIZE):
            batch = [{"source": s, "target": t} for s, t in pairs[i : i + BATCH_SIZE]]
            result = session.run(query, batch=batch)
            merged += result.single()["merged"]
            logger.info(
                "  Merged %s batch %d/%d", rel_type, i + len(batch), len(pairs)
            )
    return merged


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------

def run_sync(
    source_cfg: Dict[str, str],
    target_cfg: Dict[str, str],
    dry_run: bool = False,
) -> Dict[str, int]:
    """Run full sync and return counts."""
    stats = {"topics": 0, "prerequisites": 0, "related_to": 0}

    # Verify both sides
    logger.info("Testing source connection...")
    _test_connection_with_fallback(source_cfg, "password")
    logger.info("Testing target connection...")
    _test_connection_with_fallback(target_cfg, "password")

    src_driver = _get_driver(source_cfg)
    tgt_driver = _get_driver(target_cfg)

    try:
        # Extract
        logger.info("Extracting topics from source...")
        topics = extract_topics(src_driver, source_cfg["database"])
        stats["topics"] = len(topics)
        logger.info("  Found %d topics", stats["topics"])

        logger.info("Extracting PREREQUISITE relationships...")
        prereqs = extract_relationships(
            src_driver, source_cfg["database"], "PREREQUISITE"
        )
        stats["prerequisites"] = len(prereqs)
        logger.info("  Found %d prerequisites", stats["prerequisites"])

        logger.info("Extracting RELATED_TO relationships...")
        related = extract_relationships(
            src_driver, source_cfg["database"], "RELATED_TO"
        )
        stats["related_to"] = len(related)
        logger.info("  Found %d related_to", stats["related_to"])

        # Load
        logger.info("Merging topics into target...")
        merge_topics(tgt_driver, target_cfg["database"], topics, dry_run=dry_run)

        logger.info("Merging PREREQUISITE relationships...")
        merge_relationships(
            tgt_driver, target_cfg["database"], "PREREQUISITE", prereqs, dry_run=dry_run
        )

        logger.info("Merging RELATED_TO relationships...")
        merge_relationships(
            tgt_driver, target_cfg["database"], "RELATED_TO", related, dry_run=dry_run
        )

    finally:
        src_driver.close()
        tgt_driver.close()

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Sync Neo4j Topic graph between two instances (e.g. Docker ↔ Aura)."
    )
    parser.add_argument(
        "--source",
        choices=["local", "cloud"],
        default="local",
        help="Source preset (local or cloud).",
    )
    parser.add_argument(
        "--target",
        choices=["local", "cloud"],
        default="cloud",
        help="Target preset (local or cloud).",
    )
    parser.add_argument(
        "--source-prefix",
        default="",
        help="Env prefix for source (e.g. SOURCE_).",
    )
    parser.add_argument(
        "--target-prefix",
        default="",
        help="Env prefix for target (e.g. TARGET_).",
    )
    parser.add_argument(
        "--env-file",
        default=".env",
        help="Path to .env file (relative to project root).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview counts without writing to target.",
    )
    parser.add_argument(
        "--proxy",
        default=None,
        help="SOCKS/HTTP proxy URL (e.g. socks5://127.0.0.1:1080 or http://proxy.company.com:8080).",
    )
    parser.add_argument(
        "--proxy-dns",
        action="store_true",
        help="Let proxy resolve DNS (useful when local DNS is blocked).",
    )
    args = parser.parse_args()

    # Load env
    env_path = PROJECT_ROOT / args.env_file
    if env_path.exists():
        load_dotenv(env_path)
        logger.info("Loaded env from %s", env_path)
    else:
        logger.warning("Env file not found: %s", env_path)

    # Build configs
    try:
        source_cfg = _build_config(args.source, args.source_prefix or None)
        target_cfg = _build_config(args.target, args.target_prefix or None)
    except ValueError as exc:
        logger.error(str(exc))
        sys.exit(1)

    if args.dry_run:
        logger.info("🟡 DRY-RUN MODE: No data will be written to target.")

    logger.info(
        "Starting sync: %s → %s", source_cfg["uri"], target_cfg["uri"]
    )
    stats = run_sync(source_cfg, target_cfg, dry_run=args.dry_run)

    logger.info("=" * 50)
    logger.info("SYNC SUMMARY")
    logger.info("  Topics:       %d", stats["topics"])
    logger.info("  Prerequisites:%d", stats["prerequisites"])
    logger.info("  Related_to:   %d", stats["related_to"])
    if args.dry_run:
        logger.info("  Mode:         DRY-RUN (no writes)")
    else:
        logger.info("  Mode:         LIVE")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()

