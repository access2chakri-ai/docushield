"""
Add image storage fields to users table
"""
from sqlalchemy import text

async def upgrade(connection):
    """Add image storage fields to users table"""
    # Check if columns already exist to avoid errors
    try:
        await connection.execute(text("""
            ALTER TABLE users 
            ADD COLUMN profile_photo_data LONGBLOB NULL,
            ADD COLUMN profile_photo_mime_type VARCHAR(100) NULL
        """))
    except Exception as e:
        # If columns already exist, that's fine
        if "Duplicate column name" in str(e):
            print("Image storage columns already exist, skipping...")
        else:
            raise e

async def downgrade(connection):
    """Remove image storage fields from users table"""
    await connection.execute(text("""
        ALTER TABLE users 
        DROP COLUMN profile_photo_data,
        DROP COLUMN profile_photo_mime_type
    """))
