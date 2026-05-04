#!/usr/bin/env python3
import os
os.environ['POSTGRES_HOST'] = 'localhost'
os.environ['POSTGRES_PORT'] = '5433'
os.environ['POSTGRES_DBNAME'] = 'ai_gen_db'
os.environ['POSTGRES_USER'] = 'postgres'
os.environ['POSTGRES_PASSWORD'] = 'password123'

from Application.Infrastructure.relationalDB.postgres_repo import PostgresRepository

repo = PostgresRepository('ai_gen_db', 'postgres', 'password123', 'localhost', 5433)

try:
    course_id = repo.create_course(
        title='Test Raw SQL Schema Fix',
        audience='general',
        description='Raw SQL test',
        created_by=None
    )
    print(f'✅ SUCCESS Raw SQL: Created course ID {course_id}')
except Exception as e:
    print(f'❌ Raw SQL ERROR: {e}')
