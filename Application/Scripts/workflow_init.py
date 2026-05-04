#!/usr/bin/env python3
"""
Workflow initialization and health check script.
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from Workflows.workflow_manager import manager

async def main():
    print('Initializing workflows...')
    result = manager.init()
    print(result)
    if result['status'] == 'success':
        print('✅ All workflows ready!')
    else:
        print('❌ Initialization failed. Check dependencies.')

if __name__ == '__main__':
    asyncio.run(main())

