#!/usr/bin/env python3
"""
Simple migration runner script
Usage: python migrate.py [status|migrate]
"""
import sys
from migrations.migration_runner import main
import asyncio

if __name__ == "__main__":
    asyncio.run(main())
