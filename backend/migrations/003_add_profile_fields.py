"""
Add profile photo fields to users table
"""
from sqlalchemy import text

async def upgrade(connection):
    """Add profile photo fields to users table"""
    await connection.execute(text("""
        ALTER TABLE users 
        ADD COLUMN profile_photo_url VARCHAR(500) NULL,
        ADD COLUMN profile_photo_prompt TEXT NULL
    """))

async def downgrade(connection):
    """Remove profile photo fields from users table"""
    await connection.execute(text("""
        ALTER TABLE users 
        DROP COLUMN profile_photo_url,
        DROP COLUMN profile_photo_prompt
    """))
