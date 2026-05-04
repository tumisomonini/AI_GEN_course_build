#!/usr/bin/env python3
from Application.Infrastructure.relationalDB.postgres_orm_repo import PostgresORMRepository
from sqlalchemy.exc import IntegrityError

repo = PostgresORMRepository()

try:
    course_id = repo.create_course(
        title='Test Course Schema Fix',
        audience='general',
        description='Schema fix test',
        created_by=1  # Assume user_id=1 exists or None
    )
    print(f'✅ SUCCESS: Created course ID {course_id}')
    
    # Verify fetch
    status = repo.get_course_status(course_id)
    print(f'✅ Status: {status}')
    
except Exception as e:
    print(f'❌ ERROR: {e}')
