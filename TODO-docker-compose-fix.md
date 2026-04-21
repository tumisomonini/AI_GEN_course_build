# Docker Compose YAML Syntax Fix

Current file broken (duplicate 'environment', misplaced 'ports').

**Quick Fix:**
Replace entire Application/Docker/docker-compose.yml with this correct version:

```yaml
services:
  api:
    build:
      context: ../..
      dockerfile: Application/Docker/Dockerfile
    container_name: course_builder_api
    restart: unless-stopped
    env_file:
      - ../../.env
    environment:
      POSTGRES_HOST: postgres
      POSTGRES_PORT: 5432
      NEO4J_URI: bolt://neo4j:7687
      NEO4J_USERNAME: neo4j
      NEO4J_PASSWORD: password
      NEO4J_DATABASE: neo4j
    ports:
      - "8000:8000"
    volumes:
      - ../../Application:/app/Application
      - ../../Domain:/app/Domain
      - ../../Pages:/app/Pages
    depends_on:
      - postgres
      - neo4j
    networks:
      - course_net

  postgres:
    image: postgres:15-alpine
    container_name: course_builder_db
    restart: always
    environment:
      POSTGRES_DB: ${POSTGRES_DBNAME:-ai_gen_db}
      POSTGRES_USER: ${POSTGRES_USER:-postgres}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-password123}
    ports:
      - "5433:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./../Infrastructure/relationalDB/schema.sql:/docker-entrypoint-initdb.d/schema.sql
    networks:
      - course_net

  redis:
    image: redis:7-alpine
    container_name: course_redis
    restart: always
    ports:
      - "6379:6379"
    networks:
      - course_net

  neo4j:
    image: neo4j:5.20.0
    container_name: course_neo4j
    restart: always
    environment:
      NEO4J_AUTH: neo4j/password
    ports:
      - "7474:7474"
      - "7687:7687"
    volumes:
      - neo4j_data:/data
    networks:
      - course_net

volumes:
  postgres_data:
  neo4j_data:

networks:
  course_net:
    driver: bridge
```

**Then:**
```bash
cd Application/Docker && docker-compose down && docker-compose up -d && cd ../..
sleep 30
curl localhost:8000/health
```

**Expected:** /health shows "healthy" or "degraded" only on Astra (optional token).
