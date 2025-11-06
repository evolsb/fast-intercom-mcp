# Fresh Intercom MCP - Implementation Plan

## Overview
Complete rewrite of Intercom MCP server learning from 100+ issues. Focus on simplicity, reliability, and clear deployment.

## Architecture Summary
- **Single service** combining sync + MCP server
- **Dual transport** (stdio for dev, HTTP for production)
- **Single repo** with dev/prod profiles
- **Analytics-focused** for ask-intercom queries
- **Background sync** every 30 minutes
- **6-month default** data retention

## Project Structure
```
fresh-intercom-mcp/
├── src/
│   ├── __init__.py
│   ├── main.py           # Entry point
│   ├── mcp_server.py     # MCP protocol implementation
│   ├── intercom_api.py   # Intercom API client
│   ├── database.py       # SQLite with SQLAlchemy
│   ├── sync_worker.py    # Background sync logic
│   └── config.py         # Bulletproof configuration
├── data_dev/             # Git-ignored dev data
├── data_prod/            # Git-ignored prod data
├── tests/
│   └── test_integration.py
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── .env.example
├── .gitignore
├── requirements.txt
├── pyproject.toml
└── README.md
```

## Core Requirements

### Environment & Dependencies
- Python 3.11 ONLY (no version matrix)
- Key dependencies:
  - mcp==1.0.0
  - httpx==0.27.0
  - sqlalchemy==2.0.0
  - pydantic==2.0.0
  - python-dotenv==1.0.0
  - click==8.0.0
  - fastapi==0.104.0 (for HTTP transport)

### Configuration (Bulletproof)
```python
# Multiple .env locations with clear failure
env_locations = [
    Path.cwd() / '.env',
    Path(__file__).parent.parent / '.env',
    Path.home() / '.fresh-intercom-mcp' / '.env'
]
# FAIL FAST if INTERCOM_TOKEN not found
```

### Logging
- Single file: `data_*/intercom.log`
- Format: `2024-01-20 15:30:45|module|LEVEL|message`
- Structured for grep/tail
- Examples:
  - `SYNC_START|conversations=1000|period=2024-01-20`
  - `API_ERROR|endpoint=/conversations|status=429`

### Database Schema
```sql
-- Analytics-optimized, denormalized
CREATE TABLE conversations (
    id TEXT PRIMARY KEY,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    state TEXT,
    customer_email TEXT,
    customer_name TEXT,
    assignee_email TEXT,
    assignee_name TEXT,
    first_response_at TIMESTAMP,
    resolved_at TIMESTAMP,
    response_time_seconds INTEGER,
    total_messages INTEGER,
    tags TEXT,  -- JSON array
    source_type TEXT,
    source_url TEXT,
    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT,
    created_at TIMESTAMP,
    author_type TEXT,
    author_email TEXT,
    author_name TEXT,
    body TEXT,  -- FULL text, no truncation
    attachments TEXT,  -- JSON
    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);

-- Indexes for common queries
CREATE INDEX idx_conv_created ON conversations(created_at);
CREATE INDEX idx_conv_state ON conversations(state);
CREATE INDEX idx_msg_created ON messages(created_at);
```

### Sync Strategy
1. On startup: Sync last 6 months (newest to oldest)
2. Background: Every 30 minutes, sync updates
3. Order: Most recent first (today, yesterday, etc.)
4. Pagination: Handle Intercom's cursor-based pagination
5. Rate limiting: Respect Intercom's limits

### MCP Tools
```python
tools = [
    {
        "name": "search_conversations",
        "description": "Search by text, customer, timeframe, state",
        "parameters": {
            "query": "Text search in messages",
            "customer_email": "Filter by customer",
            "state": "open, closed, snoozed",
            "timeframe": "last 7 days, this month",
            "unanswered": "bool - no admin response"
        }
    },
    {
        "name": "get_analytics",
        "description": "Get metrics for time period",
        "parameters": {
            "timeframe": "last 7 days, this week",
            "metrics": ["response_time", "volume", "unanswered"]
        }
    },
    {
        "name": "get_conversation",
        "description": "Get full conversation with messages",
        "parameters": {
            "conversation_id": "Intercom conversation ID"
        }
    }
]
```

### Docker Configuration
```yaml
# docker-compose.yml
services:
  intercom-mcp-dev:
    profiles: ["dev"]
    build: .
    volumes:
      - ./src:/app/src  # Hot reload
      - ./data_dev:/app/data
      - ./.env.development:/app/.env
    environment:
      - TRANSPORT=stdio
      
  intercom-mcp-prod:
    profiles: ["prod"]
    image: fresh-intercom-mcp:latest
    volumes:
      - ./data_prod:/app/data
      - ./.env.production:/app/.env
    ports:
      - "8000:8000"
    environment:
      - TRANSPORT=http
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
```

## Implementation Steps

### Phase 1: Core Infrastructure (Day 1)
1. Create project structure
2. Implement config.py with bulletproof env handling
3. Set up logging system
4. Create database.py with schema
5. Basic Dockerfile

### Phase 2: Intercom Integration (Day 2)
1. Implement intercom_api.py with pagination
2. Create sync_worker.py
3. Implement 6-month initial sync
4. Test with real API

### Phase 3: MCP Server (Day 3)
1. Implement mcp_server.py with dual transport
2. Create all three tools
3. Add health endpoint
4. Integration testing

### Phase 4: Production Ready (Day 4)
1. Complete docker-compose.yml
2. Write accurate README
3. Test full deployment flow
4. Railway deployment guide

## Testing Strategy
- Integration tests only (no unit test complexity)
- Test with real Intercom API in dev
- Verify all analytics queries work
- Test both transports (stdio and HTTP)

## Success Criteria
- [ ] Syncs 6 months of data successfully
- [ ] All three MCP tools work correctly
- [ ] Single log file is debuggable
- [ ] Environment setup never fails silently
- [ ] Can deploy to Railway for team access
- [ ] Response time <100ms for all queries

## Non-Goals (Avoiding Past Mistakes)
- NO complex sync strategies
- NO multiple Python versions
- NO extensive linting configs
- NO unit tests for everything
- NO configuration complexity
- NO silent failures

## Key Decisions
1. SQLAlchemy over raw SQLite (better for complex queries)
2. FastAPI for HTTP transport (standard, well-supported)
3. Single service (simpler than separate sync/server)
4. Newest-first sync (most relevant data first)
5. Fail fast everywhere (easier debugging)

## Repository Setup
```bash
# Create fresh repo
mkdir ~/Developer/fresh-intercom-mcp
cd ~/Developer/fresh-intercom-mcp
git init

# Copy this plan
cp /path/to/FRESH_MCP_IMPLEMENTATION_PLAN.md .

# Create .gitignore
cat > .gitignore << EOF
__pycache__/
*.pyc
.env*
!.env.example
data_dev/
data_prod/
*.db
*.log
.DS_Store
EOF

# Initial commit
git add .
git commit -m "Initial commit: Implementation plan for fresh Intercom MCP"

# Create GitHub repo and push
gh repo create fresh-intercom-mcp --private
git push -u origin main
```

## Next Agent Instructions
When implementing, follow these principles:
1. Start with Phase 1 completely before moving on
2. Test each component before integrating
3. Use the exact schema provided
4. Follow the logging format exactly
5. Fail fast with clear error messages
6. Keep it simple - if something seems complex, it probably is

Ready to implement!