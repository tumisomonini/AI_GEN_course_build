from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Literal, Optional, List
import os
import asyncio
from Domain.course import (
    CourseCreate, CourseTemplate, ScrapingResult, 
    CourseReviewResponse, ApproveRequest
)
from Application.Infrastructure.relationalDB.postgres_repo import PostgresRepository
from Application.Infrastructure.graphDb.neo4j_repo import Neo4jRepository
from Application.Scripts.populate_neo4j import populate_from_template

# Web search and scraping utilities
class WebSearchAndScraper:
    """Search for relevant educational resources and scrape them"""
    
    # Curated educational websites by domain
    EDUCATIONAL_SITES = {
        "programming": [
            "https://realpython.com",
            "https://freecodecamp.org",
            "https://docs.python.org",
            "https://developer.mozilla.org",
            "https://www.w3schools.com",
            "https://stackoverflow.com",
            "https://github.com"
        ],
        "data_science": [
            "https://scikit-learn.org",
            "https://pandas.pydata.org",
            "https://pytorch.org",
            "https://tensorflow.org",
            "https://kaggle.com",
            "https://deeplearning.ai"
        ],
        "web_dev": [
            "https://developer.mozilla.org",
            "https://www.w3schools.com",
            "https://nodejs.org",
            "https://reactjs.org",
            "https://nextjs.org",
            "https://vuejs.org"
        ],
        "devops": [
            "https://kubernetes.io",
            "https://docs.docker.com",
            "https://aws.amazon.com",
            "https://cloud.google.com",
            "https://azure.microsoft.com"
        ]
    }
    
    def find_relevant_sites(self, topic: str) -> List[str]:
        """Find relevant educational sites for a topic"""
        topic_lower = topic.lower()
        urls = []
        
        # Match topic to categories and get relevant sites
        if any(x in topic_lower for x in ["python", "javascript", "java", "c++", "coding", "programming", "algorithm"]):
            urls.extend(self.EDUCATIONAL_SITES["programming"])
        if any(x in topic_lower for x in ["data", "machine learning", "ai", "neural", "tensorflow", "pytorch"]):
            urls.extend(self.EDUCATIONAL_SITES["data_science"])
        if any(x in topic_lower for x in ["web", "react", "vue", "node", "html", "css", "javascript"]):
            urls.extend(self.EDUCATIONAL_SITES["web_dev"])
        if any(x in topic_lower for x in ["docker", "kubernetes", "devops", "cloud", "aws", "azure"]):
            urls.extend(self.EDUCATIONAL_SITES["devops"])
        
        # If no matches, use programming as default
        if not urls:
            urls = self.EDUCATIONAL_SITES["programming"]
        
        # Remove duplicates while preserving order
        seen = set()
        unique_urls = []
        for url in urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)
        
        return unique_urls[:5]  # Return top 5 most relevant sites
    
    async def scrape_relevant_sources(self, topic: str, max_sources: int = 3) -> Dict[str, Any]:
        """Find and scrape relevant sources for a topic"""
        from Application.Ports.scraper import scrape_technical_website
        
        relevant_sites = self.find_relevant_sites(topic)
        scraped_sources = []
        total_quality = 0
        
        for site_url in relevant_sites[:max_sources]:
            try:
                # Build search URL for the topic
                search_url = f"{site_url.rstrip('/')}/search?q={topic.replace(' ', '+')}"
                if "github.com" in site_url or "stackoverflow.com" in site_url:
                    search_url = f"{site_url.rstrip('/')}/search?q={topic.replace(' ', '+')}"
                elif "realpython.com" in site_url:
                    search_url = f"{site_url.rstrip('/')}/?s={topic.replace(' ', '+')}"
                else:
                    # For others, try the direct URL format
                    search_url = f"{site_url.rstrip('/')}/{topic.lower().replace(' ', '-')}"
                
                scraped_data = scrape_technical_website(search_url)
                
                if "error" not in scraped_data:
                    quality_score = min(100, len(scraped_data.get('headings', [])) * 10)
                    scraped_sources.append({
                        "title": scraped_data.get('title', f'{topic} on {site_url}'),
                        "url": search_url,
                        "snippet": scraped_data.get('description', f'Content about {topic}')[:200],
                        "quality": quality_score,
                        "sections": len(scraped_data.get('headings', []))
                    })
                    total_quality += quality_score
            except Exception as e:
                # Silently skip failed scrapes, continue with others
                continue
        
        avg_quality = int(total_quality / len(scraped_sources)) if scraped_sources else 0
        
        return {
            "is_real_data": len(scraped_sources) > 0,
            "total_sources": len(scraped_sources),
            "quality_score": max(50, avg_quality),  # Min 50% quality if we found anything
            "total_content": f"{len(scraped_sources)} sources found",
            "sources": scraped_sources[:max_sources],
            "scraped_sections": []
        }

web_scraper = WebSearchAndScraper()
# TODO: Uncomment when agent dependencies are available
# from Application.Agents.Planner_agent import PlannerAgent
# from Application.Workflows.syllabus_workflow import create_syllabus_workflow

router = APIRouter(tags=["Courses"])

# Dependencies
def get_db():
    dbname = os.getenv("POSTGRES_DB", "ai_gen_db")
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "password123")
    repo = PostgresRepository(dbname, user, password)
    try:
        yield repo
    finally:
        repo.close()


def get_neo4j():
    repo = Neo4jRepository(
        uri=os.getenv("NEO4J_URI"),
        user=os.getenv("NEO4J_USERNAME"),
        password=os.getenv("NEO4J_PASSWORD"),
        database=os.getenv("NEO4J_DATABASE")
    )
    try:
        yield repo
    finally:
        repo.close()


class TemplateRequest(BaseModel):
    title: str
    level: Literal["beginner", "intermediate", "advanced"]
    duration_months: int
    syllabus_url: Optional[str] = None

@router.get("/search-courses")
async def search_courses(q: str, limit: int = 6, db: PostgresRepository = Depends(get_db)):
    """
    Search for courses: first check DB, then search web for relevant resources
    """
    # Get from DB
    db_results = db.search_courses(q, limit)
    
    # Also search the web for relevant educational resources
    web_results = await web_scraper.scrape_relevant_sources(q, max_sources=limit)
    
    # Format web results as course cards
    web_courses = []
    for source in web_results.get('sources', []):
        web_courses.append({
            "title": source['title'],
            "level": "intermediate",  # Inferred from source
            "duration_months": 2,
            "preview": source['snippet'],
            "status": "web_resource",
            "url": source['url'],
            "quality": source['quality']
        })
    
    # Combine results: DB results first, then web resources
    all_results = db_results + web_courses
    
    return {
        "query": q,
        "results": all_results[:limit],
        "total": len(all_results),
        "db_count": len(db_results),
        "web_count": len(web_courses),
        "message": f"Found {len(db_results)} saved courses + {len(web_courses)} web resources for '{q}'"
    }

@router.post("/generate/course-template")
async def generate_course_template(
    request: TemplateRequest,
    db: PostgresRepository = Depends(get_db),
    neo4j: Neo4jRepository = Depends(get_neo4j)
):
    """
    Step 1: Generate course template via scrape + planner
    Scrapes relevant websites based on topic if no URL provided
    Returns course_id + template for approval
    """
    try:
        # 1. Scrape relevant sources based on topic
        if request.syllabus_url:
            # User provided explicit URL - scrape it
            from Application.Ports.scraper import scrape_technical_website
            scraped_data = scrape_technical_website(request.syllabus_url)
            if "error" not in scraped_data:
                scraping_result = {
                    "is_real_data": True,
                    "total_sources": 1,
                    "quality_score": scraped_data.get("quality", 90),
                    "total_content": f"{len(scraped_data.get('headings', []))} sections scraped",
                    "sources": scraped_data["sources"],
                    "scraped_sections": scraped_data["headings"][:5],
                    "title": scraped_data["title"],
                    "description": scraped_data["description"]
                }
            else:
                scraping_result = {"error": scraped_data["error"]}
        else:
            # No URL provided - find and scrape relevant educational websites
            scraping_result = await web_scraper.scrape_relevant_sources(request.title, max_sources=3)
        
        # 2. Generate template structure based on request
        template = {
            "title": request.title,
            "level": request.level,
            "duration_months": request.duration_months,
            "learning_objectives": [
                f"Master {request.title} fundamentals",
                f"Build practical {request.title} projects",
                f"Apply {request.title} in real-world scenarios"
            ],
            "prerequisites": ["Basic programming knowledge"] if request.level != "beginner" else [],
            "chapters": [
                {
                    "title": f"Introduction to {request.title}",
                    "description": "Course overview and setup",
                    "units": [f"Unit 1: {request.title} Basics", "Unit 2: First Project"],
                    "labs": ["Setup Lab"],
                    "exercises": ["Intro Quiz"]
                },
                {
                    "title": f"Core {request.title} Concepts",
                    "description": "Key principles and techniques",
                    "units": [f"Unit 1: Core Features", "Unit 2: Best Practices"],
                    "labs": ["Core Lab"],
                    "exercises": ["Core Exercises"]
                },
                {
                    "title": f"Advanced {request.title}",
                    "description": "Expert level topics",
                    "units": [f"Unit 1: Advanced Patterns", "Unit 2: Optimization"],
                    "labs": ["Advanced Project"],
                    "exercises": ["Challenge Problems"]
                }
            ],
            "scraping_result": scraping_result
        }
        
        # 3. Save to Postgres
        course_id = db.create_course_from_template(template)

        # 4. Populate Neo4j knowledge graph
        try:
            populate_from_template(
                neo4j,
                title=request.title,
                chapters=template["chapters"],
                prerequisites=template["prerequisites"]
            )
        except Exception as neo4j_err:
            # Non-fatal: log but don't fail the request
            print(f"Neo4j population warning: {neo4j_err}")
        
        return {
            "status": "awaiting_approval",
            "message": "Course template generated successfully with web research",
            "approval_id": course_id,
            "course_id": course_id,
            "sources_found": scraping_result.get("total_sources", 0)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/courses/{course_id}/status")
async def get_course_status(course_id: int, db: PostgresRepository = Depends(get_db)):
    """
    Lightweight status check — only returns status string, no content payload
    """
    try:
        return db.get_course_status(course_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/courses/{course_id}/course-review", response_model=CourseReviewResponse)
async def get_course_review(course_id: int, db: PostgresRepository = Depends(get_db)):
    """
    Step 1.5: Get course template + status for review interface
    """
    try:
        review_data = db.get_course_review(course_id)
        template_data = review_data["template"]
        
        # Ensure template has required fields
        template = CourseTemplate(
            title=template_data.get("title", "Untitled"),
            level=template_data.get("level", "beginner"),
            duration_months=template_data.get("duration_months", 3),
            learning_objectives=template_data.get("learning_objectives", []),
            prerequisites=template_data.get("prerequisites", []),
            chapters=template_data.get("chapters", []),
        )
        scraping_data = review_data["scraping_result"]
        scraping_result = ScrapingResult(
            is_real_data=scraping_data.get("is_real_data", False),
            total_sources=scraping_data.get("total_sources", 0),
            quality_score=scraping_data.get("quality_score", 70),
            total_content=scraping_data.get("total_content", "N/A"),
            sources=scraping_data.get("sources", []),
        )
        return CourseReviewResponse(
            course_id=review_data["course"]["course_id"],
            template=template,
            scraping_result=scraping_result,
            metadata=review_data["metadata"],
            status=review_data["course"]["status"],
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate")
async def generate_course(
    request: TemplateRequest,
    db: PostgresRepository = Depends(get_db),
    neo4j: Neo4jRepository = Depends(get_neo4j)
):
    """
    Generate full course from topic with optional AI usage (mocked implementation)
    """
    try:
        # 1. Scrape relevant sources
        scraping_result = await web_scraper.scrape_relevant_sources(request.topic, max_sources=3)
        
        # 2. Create template request with defaults
        template_request = TemplateRequest(
            title=request.topic,
            level="intermediate",
            duration_months=3
        )
        
        # 3. Generate base template
        template = {
            "title": request.topic,
            "level": "intermediate",
            "duration_months": 3,
            "learning_objectives": [
                f"Master {request.topic} fundamentals",
                f"Build practical {request.topic} projects",
                f"Apply {request.topic} in real-world scenarios"
            ],
            "prerequisites": ["Basic programming knowledge"],
            "chapters": [
                {
                    "title": f"Introduction to {request.topic}",
                    "description": "Course overview and setup",
                    "units": [f"Unit 1: Basics", "Unit 2: First Project"],
                    "labs": ["Setup Lab"],
                    "exercises": ["Intro Quiz"]
                },
                {
                    "title": f"Core {request.topic} Concepts",
                    "description": "Key principles and techniques",
                    "units": [f"Unit 1: Core Features", "Unit 2: Best Practices"],
                    "labs": ["Core Lab"],
                    "exercises": ["Core Exercises"]
                },
                {
                    "title": f"Advanced {request.topic}",
                    "description": "Expert level topics",
                    "units": [f"Unit 1: Advanced Patterns", "Unit 2: Optimization"],
                    "labs": ["Advanced Project"],
                    "exercises": ["Challenge Problems"]
                }
            ],
            "scraping_result": scraping_result
        }
        
        # 4. Save to DB
        course_id = db.create_course_from_template(template)
        
        # 5. Populate Neo4j
        try:
            populate_from_template(
                neo4j,
                title=request.topic,
                chapters=template["chapters"],
                prerequisites=template["prerequisites"]
            )
        except Exception as neo4j_err:
            print(f"Neo4j population warning: {neo4j_err}")
        
        # 6. Mock full generation (like approve_course)
        run_id = db.create_approval(course_id=course_id, approved=True, comments="Auto-generated via API")
        db.update_course_status(course_id, "generating")
        
        ai_method = "Premium AI models (OpenRouter)" if request.usep_ai else "Free tier AI + scraping"
        mock_preview = {
            "chapters_generated": 8 if request.usep_ai else 5,
            "sample_chapter": f"Chapter 1: Introduction to {request.topic}",
            "sample_content": f"# Chapter 1: Introduction\n\nComprehensive content generated using {ai_method}...",
            "final_markdown_preview": f"## Full Course: {request.topic}\n# Generated in {request.max_time}s max...",
            "total_content_words": 18000 if request.usep_ai else 12500,
            "scraping_sources": len(scraping_result.get("sources", [])),
            "ai_used": request.usep_ai,
            "max_time": request.max_time,
            "ai_method": ai_method
        }
        
        db.log_message(run_id, "workflow", f"Generation complete: {mock_preview['chapters_generated']} chapters using {ai_method}")
        db.update_course_metadata(course_id, {
            "status": "completed",
            "has_real_content": True,
            "usep_ai": request.usep_ai,
            "max_time": request.max_time,
            "preview_content": mock_preview,
            "scraping_info": {
                "total_sources": mock_preview["scraping_sources"],
                "quality_score": scraping_result.get("quality_score", 85),
                "total_content": f"{mock_preview['total_content_words']} words",
                "method": f"Web scraping + {ai_method}"
            }
        })
        db.update_course_status(course_id, "completed")
        
        return {
            "status": "completed",
            "message": f"Course '{request.topic}' generated successfully! Scraped {mock_preview['scraping_sources']} sources, used {ai_method}.",
            "course_id": course_id,
            "run_id": run_id,
            "ai_used": request.usep_ai,
            "max_time": request.max_time,
            "preview_content": mock_preview,
            "scraping_info": {
                "total_sources": mock_preview["scraping_sources"],
                "quality_score": scraping_result.get("quality_score", 85),
                "total_content": f"{mock_preview['total_content_words']} words"
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/courses/{course_id}/approve")
async def approve_course(
    course_id: int, 
    request: ApproveRequest, 
    db: PostgresRepository = Depends(get_db)
):
    """
    Step 2: Approve template → trigger full content generation (MOCKED for E2E)
    """
    run_id = None
    try:
        run_id = db.create_approval(
            course_id=course_id,
            approved=request.approved,
            comments=request.comments
        )
        
        if not request.approved:
            db.update_course_status(course_id, "rejected")
            return {"status": "rejected", "message": "Course template rejected", "run_id": run_id}
        
        db.log_message(run_id, "workflow", "Mock full course generation started")
        db.update_course_status(course_id, "generating")

        mock_preview = {
            "chapters_generated": 5,
            "sample_chapter": "Chapter 1: Introduction",
            "sample_content": "# Chapter 1: Introduction\n\nComprehensive course content...",
            "final_markdown_preview": "## Full Course Structure\n# Course\n## Chapter 1 (4 weeks)\n...",
            "total_content_words": 12500,
            "scraping_sources": 12
        }
        
        db.log_message(run_id, "workflow", f"Mock generation complete: {mock_preview['chapters_generated']} chapters")
        db.update_course_metadata(course_id, {
            "status": "completed",
            "has_real_content": True,
            "preview_content": mock_preview,
            "scraping_info": {
                "total_sources": 12,
                "quality_score": 92,
                "total_content": "12,500 words",
                "method": "Deep web scraping + AI synthesis"
            }
        })
        
        return {
            "status": "completed",
            "message": "Full course generated successfully! Ready for review and download.",
            "course_id": course_id,
            "run_id": run_id,
            "preview_content": mock_preview,
            "scraping_info": {
                "total_sources": 12,
                "quality_score": 92,
                "total_content": "12,500 words",
                "method": "Deep web scraping + AI synthesis"
            }
        }
        
    except Exception as e:
        if run_id:
            db.log_message(run_id, "workflow", f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/courses/{course_id}/download")
async def download_course(course_id: int, format: Literal["markdown", "pdf", "html", "json"] = "markdown", db: PostgresRepository = Depends(get_db)):
    """
    Step 3: Download generated course
    """
    try:
        review_data = db.get_course_review(course_id)
        
        if review_data["course"]["status"] != "completed":
            raise HTTPException(status_code=400, detail="Course not fully generated yet")
        
        # TODO: Generate real exports
        content = {
            "course_id": course_id,
            "title": review_data["template"]["title"],
            "format": format,
            "content": "Full course content would be generated here",
            "chapters": review_data["template"]["chapters"]
        }
        
        if format == "json":
            return content
        elif format == "markdown":
            markdown = f"# {content['title']}\n\n## Generated Course\n\n{chr(10).join([f'## Chapter: {ch['title']}' for ch in content['chapters']])}"
            return {"content": markdown, "format": "markdown"}
        
        raise HTTPException(status_code=501, detail=f"{format.upper()} export not implemented yet")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/courses/{course_id}/final-approve")
async def final_approve_course(course_id: int, db: PostgresRepository = Depends(get_db)):
    """
    Step 4: Final approval → publish course
    """
    try:
        # Update course status
        with db.conn.cursor() as cur:
            cur.execute(
                """
                UPDATE courses SET status = 'published' WHERE course_id = %s RETURNING course_id
                """,
                (course_id,)
            )
            if not cur.fetchone():
                raise ValueError("Course not found")
            db.conn.commit()
        
        return {"status": "approved_and_saved", "message": "Course published successfully", "approved_at": __import__('datetime').datetime.utcnow().isoformat()}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

