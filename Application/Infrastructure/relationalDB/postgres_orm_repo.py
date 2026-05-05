import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session as OrmSession
from sqlalchemy.exc import SQLAlchemyError
from contextlib import contextmanager
from typing import List, Dict, Any, Optional, Generator
from sqlalchemy import func
from pathlib import Path
from dotenv import load_dotenv
from .models import Base, Course, Chapter, Syllabus, Run, Log, Approval, Review, Metric, Cost, Artifact, Export, Session as SessionModel, User

load_dotenv(Path(__file__).resolve().parents[4] / '.env')

class PostgresORMRepository:
    def __init__(self):
        host = os.getenv('POSTGRES_HOST', 'localhost').strip()
        port = os.getenv('POSTGRES_PORT', '5432').strip()
        dbname = os.getenv('POSTGRES_DBNAME', 'ai_gen_db')
        user = os.getenv('POSTGRES_USER', 'postgres')
        password = os.getenv('POSTGRES_PASSWORD', 'password123')
        
        engine_url = f'postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}'
        self.engine = create_engine(engine_url, pool_pre_ping=True, pool_size=20, max_overflow=0)
        Base.metadata.create_all(self.engine)  # Create tables if not exist
        
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    @contextmanager
    def get_session(self) -> Generator[OrmSession, None, None]:
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def init_schema(self) -> None:
        # Schema already created via Base.metadata.create_all()
        pass
    
    def create_course(self, title: str, audience: str, description: Optional[str] = None, created_by: Optional[int] = None) -> int:
        with self.get_session() as session:
            # Check if course already exists by title
            existing_course = session.query(Course).filter_by(title=title).first()
            if existing_course:
                # Update existing course
                existing_course.description = description
                existing_course.audience = audience
                existing_course.updated_at = func.current_timestamp()  # type: ignore[assignment]
                return existing_course.course_id
            else:
                course = Course(title=title, description=description, audience=audience, created_by_id=created_by)
                session.add(course)
                session.flush()  # Flush to get ID
                return course.course_id
    
    def get_chapters(self, course_id: int) -> List[Dict[str, Any]]:
        with self.get_session() as session:
            chapters = session.query(Chapter).filter(Chapter.course_id == course_id).order_by(Chapter.chapter_order).all()
            return [{'chapter_id': c.chapter_id, 'title': c.title, 'content': c.content, 
                     'chapter_order': c.chapter_order, 'status': c.status} for c in chapters]
    
    def create_course_from_template(self, template: Dict[str, Any]) -> int:
        import json
        status = template.get('status', 'draft')
        with self.get_session() as session:
            # Check if course already exists by title
            existing_course = session.query(Course).filter_by(title=template['title']).first()
            if existing_course:
                course = existing_course
                course.description = str(template.get('learning_objectives', []))
                course.audience = template.get('level', 'general')
                course.status = status
                course.updated_at = func.current_timestamp()  # type: ignore[assignment]
                # Clear existing chapters to prevent UniqueViolation when rebuilding a course
                session.query(Chapter).filter_by(course_id=course.course_id).delete()
            else:
                course = Course(title=template['title'], description=str(template.get('learning_objectives', [])), 
                                audience=template.get('level', 'general'), status=status)
            session.add(course)
            session.flush()
            course_id = course.course_id
            
            for i, ch in enumerate(template.get('chapters', [])):
                title = ch['title'] if isinstance(ch, dict) else str(ch)
                # Use ON CONFLICT for chapters to handle potential duplicates gracefully
                # Note: SQLAlchemy's ORM doesn't directly support ON CONFLICT DO UPDATE for add()
                # For simplicity and to avoid re-fetching, we'll rely on the UniqueConstraint
                # and let it raise if a true conflict occurs, or ensure titles are unique.
                # For this specific case, we're creating new chapters for a new course,
                # so a conflict is less likely unless the template itself has duplicates.
                chapter = Chapter(course_id=course_id, title=title, content='', chapter_order=i+1, status='pending')
                session.add(chapter)
            
            syllabus = Syllabus(course_id=course_id, content=json.dumps(template), status='draft')
            session.add(syllabus)
            return course_id
    
    def create_run(self, course_id: int, workflow_name: str) -> int:
        with self.get_session() as session:
            run = Run(course_id=course_id, workflow_name=workflow_name, status='running')
            session.add(run)
            session.flush()
            return run.run_id
    
    def update_course_template(self, course_id: int, template: Dict[str, Any]) -> None:
        import json
        with self.get_session() as session:
            session.query(Chapter).filter(Chapter.course_id == course_id, Chapter.status == 'draft').delete()
            
            # Update syllabus
            syllabus = session.query(Syllabus).filter(Syllabus.course_id == course_id).order_by(Syllabus.syllabus_id.desc()).first()
            if syllabus:
                syllabus.content = json.dumps(template)
                syllabus.updated_at = func.current_timestamp()  # type: ignore[assignment]
            else:
                syllabus = Syllabus(course_id=course_id, content=json.dumps(template))
                session.add(syllabus)
            
            # Add new draft chapters
            for i, chapter_title in enumerate(template.get('chapters', [])):
                chapter = Chapter(course_id=course_id, title=chapter_title, content='', chapter_order=i+1, status='draft')
                session.add(chapter)
    
    def update_run_status(self, run_id: int, status: str) -> None:
        with self.get_session() as session:
            run = session.query(Run).filter(Run.run_id == run_id).first()
            if run:
                run.status = status
                if status in ('completed', 'failed'):
                    run.completed_at = func.current_timestamp()  # type: ignore[assignment]
    
    def get_course_status(self, course_id: int) -> Dict[str, Any]:
        with self.get_session() as session:
            course = session.query(Course).filter(Course.course_id == course_id).first()
            if not course:
                return {'error': 'Course not found', 'course_id': course_id}
            return {'course_id': course.course_id, 'title': course.title, 'status': course.status,
                    'created_at': course.created_at, 'updated_at': course.updated_at}
    
    def get_course_review(self, course_id: int) -> Dict[str, Any]:
        with self.get_session() as session:
            course = session.query(Course).filter(Course.course_id == course_id).first()
            if not course:
                raise ValueError(f"Course {course_id} not found")
            
            syllabus = session.query(Syllabus).filter(Syllabus.course_id == course_id).order_by(Syllabus.syllabus_id.desc()).first()
            template = syllabus.content if syllabus else {}
            
            chapters = self.get_chapters(course_id)
            
            return {
                'course_id': course_id,
                'course': {'course_id': course.course_id, 'title': course.title, 'status': course.status,
                          'created_at': course.created_at, 'updated_at': course.updated_at},
                'template': template,
                'metadata': {'chapters_count': len(chapters)},
                'chapters': chapters
            }
    
    def create_approval(self, course_id: int, approved: bool, comments: Optional[str] = None) -> int:
        with self.get_session() as session:
            run = session.query(Run).filter(Run.course_id == course_id).order_by(Run.run_id.desc()).first()
            if not run:
                run = Run(course_id=course_id, workflow_name='approval', status='running')
                session.add(run)
                session.flush()
                run_id = run.run_id
            else:
                run_id = run.run_id
            
            status = 'approved' if approved else 'rejected'
            approval = Approval(run_id=run_id, status=status, comments=comments)
            session.add(approval)
            session.flush()
            return approval.approval_id
    
    def update_course_status(self, course_id: int, status: str) -> None:
        with self.get_session() as session:
            course = session.query(Course).filter(Course.course_id == course_id).first()
            if course:
                course.status = status
                course.updated_at = func.current_timestamp()  # type: ignore[assignment]
    
    def get_latest_error(self, course_id: int) -> Optional[str]:
        with self.get_session() as session:
            log = (session.query(Log.message)
                   .join(Run)
                   .filter(Run.course_id == course_id, Log.level == 'error')
                   .order_by(Log.created_at.desc())
                   .first())
            return log[0] if log else None
    
    def log_message(self, run_id: int, agent_name: str, message: str, level: str = 'info') -> None:
        if not run_id or run_id <= 0:
            return
        with self.get_session() as session:
            log = Log(run_id=run_id, agent_name=agent_name, message=message, level=level)
            session.add(log)
    
    def get_logs_for_run(self, run_id: int) -> List[Dict[str, Any]]:
        with self.get_session() as session:
            logs = session.query(Log).filter(Log.run_id == run_id).order_by(Log.log_id).all()
            return [{'log_id': l.log_id, 'agent_name': l.agent_name, 'message': l.message,
                     'level': l.level, 'created_at': l.created_at.isoformat()} for l in logs]
    
    def search_courses(self, query: str) -> List[Dict[str, Any]]:
        with self.get_session() as session:
            courses = session.query(Course).filter(Course.title.ilike(f'%{query}%')).order_by(Course.course_id).all()
            return [{'course_id': c.course_id, 'title': c.title, 'status': c.status} for c in courses]
    
    def get_metrics_for_run(self, run_id: int) -> List[Dict[str, Any]]:
        with self.get_session() as session:
            metrics = session.query(Metric).filter(Metric.run_id == run_id).order_by(Metric.metric_id).all()
            return [{'metric_id': m.metric_id, 'agent_name': m.agent_name, 'metric_name': m.metric_name,
                     'value': m.value, 'created_at': m.created_at.isoformat()} for m in metrics]
    
    def save_full_course_chapters(self, course_id: int, chapters: List[Dict[str, Any]]) -> None:
        with self.get_session() as session:
            session.query(Chapter).filter(Chapter.course_id == course_id, Chapter.status == 'generated').delete()
            for i, ch in enumerate(chapters):
                chapter = Chapter(course_id=course_id, title=ch['title'], content=ch['content'],
                                chapter_order=i+1, status='generated')
                session.add(chapter)
    
    def get_logs_after(self, run_id: int, last_log_id: int = 0) -> List[Dict[str, Any]]:
        with self.get_session() as session:
            logs = (session.query(Log).filter(Log.run_id == run_id, Log.log_id > last_log_id)
                    .order_by(Log.log_id).all())
            return [{'log_id': l.log_id, 'agent_name': l.agent_name, 'message': l.message,
                     'level': l.level} for l in logs]
    
    def cleanup_expired_sessions(self) -> int:
        with self.get_session() as session:
            count = session.query(SessionModel).filter(SessionModel.expires_at < func.now()).delete()
            return count

    def get_training_chapters(self, min_length: int = 500) -> List[tuple]:
        """Retrieve high-quality chapters for fine-tuning."""
        with self.get_session() as session:
            chapters = session.query(Chapter.title, Chapter.content)\
                              .filter(Chapter.status == 'generated', func.length(Chapter.content) > min_length)\
                              .all()
            return [(ch.title, ch.content) for ch in chapters]


    
    def close(self):
        self.engine.dispose()
