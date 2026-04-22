#!/usr/bin/env python3
"""Coordinated DB startup for development.
Handles Docker + health polls, or local fallbacks.
Usage: python Application/Scripts/start_dbs.py [--docker] [--populate]
"""
import os
import sys
import time
import subprocess
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

HERE = Path(__file__).resolve().parent

def run_cmd(cmd, cwd=None, check=True):
    """Run shell command, stream output."""
    proc = subprocess.Popen(cmd, shell=True, cwd=cwd, text=True, bufsize=1,
                           universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for line in iter(proc.stdout.readline, ''):
        print(line, end='')
    proc.stdout.close()
    if check:
        proc.wait()
        if proc.returncode != 0:
            raise RuntimeError(f'Command failed: {cmd}')
    return proc.returncode

def poll_postgres(max_tries=30, interval=5):
    """Poll postgres health."""
    for i in range(max_tries):
        try:
            if os.getenv('POSTGRES_HOST', 'postgres') == 'postgres':
                result = subprocess.run(['docker', 'exec', 'course_builder_db', 'pg_isready', '-U', 'postgres'], capture_output=True, text=True)
            else:
                result = subprocess.run(['pg_isready', '-h', 'localhost', '-p', '5433', '-U', 'postgres'], capture_output=True, text=True)
            if 'accepting' in result.stdout:
                print('✅ Postgres ready')
                return True
        except:
            pass
        print(f'⏳ Postgres check {i+1}/{max_tries}...')
        time.sleep(interval)
    return False

def poll_neo4j(max_tries=30, interval=5):
    """Poll neo4j health."""
    for i in range(max_tries):
        try:
            cmd = 'docker exec course_neo4j cypher-shell -u neo4j -p password neo4j "RETURN 1;" || exit 1'
            if run_cmd(cmd, check=False) == 0:
                print('✅ Neo4j ready')
                return True
        except:
            pass
        print(f'⏳ Neo4j check {i+1}/{max_tries}...')
        time.sleep(interval)
    return False

def main():
    docker = '--docker' in sys.argv
    populate = '--populate' in sys.argv
    
    print('🚀 Starting databases...')
    
    if docker:
        print('🐳 Docker mode')
        docker_yml = HERE.parent.parent / 'Docker' / 'docker-compose.yml'
        run_cmd(f'cd {docker_yml.parent} && docker compose up -d postgres neo4j', check=True)
        
        if not poll_postgres():
            print('❌ Postgres failed')
            return 1
        if not poll_neo4j():
            print('❌ Neo4j failed')
            return 1
    else:
        print('🏠 Local dev mode (assumes Docker running or local installs)')
        # Local fallback polls
        if not poll_postgres():
            print('⚠️ Postgres not ready - start manually')
        if not poll_neo4j():
            print('⚠️ Neo4j not ready')
    
    # Astra optional
    if os.getenv('ASTRA_DB_APPLICATION_TOKEN'):
        subprocess.run([sys.executable, HERE / 'init_astra.py', 'syllabus_chunks'])
        print('✅ Astra initialized')
    
    if populate:
        subprocess.run([sys.executable, HERE / 'populate_all_dbs.py'])
    
    print('''
✅ Databases ready!

Next:
- API: uvicorn Application.API.Main:app --reload --port 8000
- Test: curl http://localhost:8000/health
- Frontend: open Pages/dashboard.html
    ''')

if __name__ == '__main__':
    sys.exit(main() or 0)
