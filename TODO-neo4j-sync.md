# Neo4j Docker ↔ Cloud Sync Implementation

## Plan Steps
- [x] 1. Create `Application/Scripts/sync_neo4j.py` (core sync logic)
- [x] 2. Create `Application/Tests/test_neo4j_sync.py` (test coverage)
- [x] 3. Create `.env.sync.example` (sync-specific env vars)
- [x] 4. Update `Application/Ports/triple_db_manager.py` with optional `sync_neo4j_to_cloud()` wrapper
- [x] 5. Run tests and verify script works

## Implementation Results
- **Local Neo4j**: ✅ Connected (2 topics, 1 prerequisite)
- **Aura Cloud**: ✅ Connected (780e4b3a.databases.neo4j.io)
- **Live Sync**: ✅ Completed — 2 topics + 1 PREREQUISITE relationship merged into Aura
- **Driver upgrade**: neo4j 4.4.1 → 6.1.0 (required for Aura compatibility)
- **SSL fix**: macOS certificates installed via Python Install Certificates.command

## Verified in Aura
```
Topics: Math, Physics
PREREQUISITE: 1 relationship
RELATED_TO: 0 relationships
```

## Usage
```bash
# Dry-run
python Application/Scripts/sync_neo4j.py --source local --target cloud --target-prefix TARGET_ --dry-run

# Live sync
TARGET_NEO4J_URI=neo4j+s://780e4b3a.databases.neo4j.io \
TARGET_NEO4J_USERNAME=780e4b3a \
TARGET_NEO4J_PASSWORD=G8hMcmRovD--SSgcVCcIORJIAYBKB0Xe-f6Jvo1P1-s \
TARGET_NEO4J_DATABASE=780e4b3a \
python Application/Scripts/sync_neo4j.py --source local --target cloud --target-prefix TARGET_
```

