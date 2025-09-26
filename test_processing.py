#!/usr/bin/env python3
"""
Test script to manually trigger document processing
"""
import asyncio
import sys
import os

# Add backend to path
sys.path.append('backend')

from app.database import get_operational_db
from app.models import BronzeContract, BronzeContractTextRaw
from app.services.document_processor import document_processor
from sqlalchemy import select

async def test_processing():
    """Test document processing for the latest uploaded document"""
    
    async for db in get_operational_db():
        try:
            # Get the latest contract
            result = await db.execute(
                select(BronzeContract).order_by(BronzeContract.created_at.desc()).limit(1)
            )
            contract = result.scalar_one_or_none()
            
            if not contract:
                print("❌ No contracts found")
                return
            
            print(f"📄 Found contract: {contract.contract_id} - {contract.filename}")
            print(f"   Status: {contract.status}")
            print(f"   MIME Type: {contract.mime_type}")
            print(f"   File Size: {contract.file_size} bytes")
            
            # Check if text already exists
            text_result = await db.execute(
                select(BronzeContractTextRaw).where(
                    BronzeContractTextRaw.contract_id == contract.contract_id
                )
            )
            text_raw = text_result.scalar_one_or_none()
            
            if text_raw:
                print(f"✅ Text already extracted: {len(text_raw.raw_text)} characters")
            else:
                print("❌ No text extracted yet")
                
                # Try to process manually
                print("🔄 Attempting manual processing...")
                try:
                    result = await document_processor.process_contract(
                        contract_id=contract.contract_id,
                        user_id=contract.owner_user_id,
                        trigger="manual_test"
                    )
                    print(f"✅ Processing completed: {result}")
                except Exception as e:
                    print(f"❌ Processing failed: {e}")
                    import traceback
                    traceback.print_exc()
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
        finally:
            break

if __name__ == "__main__":
    asyncio.run(test_processing())