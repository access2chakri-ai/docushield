"""
Google Drive Integration Service for DocuShield
Automated document ingestion from Google Drive with real-time monitoring
"""
import os
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import asyncio

import httpx

# Optional Google dependencies - handle gracefully if not installed
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_DRIVE_AVAILABLE = True
except ImportError:
    GOOGLE_DRIVE_AVAILABLE = False
    Request = None
    Credentials = None
    InstalledAppFlow = None
    build = None
    HttpError = Exception

from app.core.config import settings
from app.agents import agent_orchestrator

logger = logging.getLogger(__name__)

# Google Drive API scopes
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

class GoogleDriveService:
    """
    Google Drive integration service for automated document ingestion
    """
    
    def __init__(self):
        self.service = None
        self.credentials = None
        self.last_sync = None
        
        if not GOOGLE_DRIVE_AVAILABLE:
            logger.warning("⚠️ Google Drive dependencies not available. Install with: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")
        
    async def authenticate(self) -> bool:
        """Authenticate with Google Drive API"""
        if not GOOGLE_DRIVE_AVAILABLE:
            logger.error("Google Drive dependencies not available - install required packages")
            return False
            
        try:
            creds = None
            
            # Load existing token
            if os.path.exists(settings.google_token_path):
                creds = Credentials.from_authorized_user_file(settings.google_token_path, SCOPES)
            
            # If no valid credentials, get new ones
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    if not os.path.exists(settings.google_credentials_path):
                        logger.error("Google credentials file not found. Please set up OAuth2 credentials.")
                        return False
                    
                    flow = InstalledAppFlow.from_client_secrets_file(
                        settings.google_credentials_path, SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                
                # Save credentials for next run
                with open(settings.google_token_path, 'w') as token:
                    token.write(creds.to_json())
            
            self.credentials = creds
            self.service = build('drive', 'v3', credentials=creds)
            logger.info("Successfully authenticated with Google Drive")
            return True
            
        except Exception as e:
            logger.error(f"Failed to authenticate with Google Drive: {e}")
            return False
    
    async def list_documents(self, folder_id: Optional[str] = None, modified_since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        List documents from Google Drive folder
        """
        if not GOOGLE_DRIVE_AVAILABLE:
            logger.error("Google Drive dependencies not available - install required packages")
            return []
            
        try:
            if not self.service:
                if not await self.authenticate():
                    return []
            
            # Build query
            query_parts = []
            
            # Filter by folder
            if folder_id:
                query_parts.append(f"'{folder_id}' in parents")
            elif settings.google_drive_folder_id:
                query_parts.append(f"'{settings.google_drive_folder_id}' in parents")
            
            # Filter by supported file types
            mime_types = [
                "application/pdf",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "text/plain",
                "text/markdown"
            ]
            mime_query = " or ".join([f"mimeType='{mime}'" for mime in mime_types])
            query_parts.append(f"({mime_query})")
            
            # Filter by modification date
            if modified_since:
                timestamp = modified_since.isoformat() + 'Z'
                query_parts.append(f"modifiedTime > '{timestamp}'")
            
            # Exclude trashed files
            query_parts.append("trashed=false")
            
            query = " and ".join(query_parts)
            
            # Execute query
            results = self.service.files().list(
                q=query,
                pageSize=100,
                fields="nextPageToken, files(id, name, mimeType, size, modifiedTime, webViewLink, parents)"
            ).execute()
            
            documents = results.get('files', [])
            logger.info(f"Found {len(documents)} documents in Google Drive")
            
            return documents
            
        except HttpError as e:
            logger.error(f"Google Drive API error: {e}")
            return []
        except Exception as e:
            logger.error(f"Failed to list documents: {e}")
            return []
    
    async def download_document(self, file_id: str) -> Optional[bytes]:
        """Download document content from Google Drive"""
        if not GOOGLE_DRIVE_AVAILABLE:
            logger.error("Google Drive dependencies not available - install required packages")
            return None
            
        try:
            if not self.service:
                if not await self.authenticate():
                    return None
            
            # Get file metadata
            file_metadata = self.service.files().get(fileId=file_id).execute()
            mime_type = file_metadata.get('mimeType')
            
            # Download file content
            if mime_type == 'application/pdf':
                request = self.service.files().get_media(fileId=file_id)
            elif mime_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
                request = self.service.files().get_media(fileId=file_id)
            elif mime_type in ['text/plain', 'text/markdown']:
                request = self.service.files().get_media(fileId=file_id)
            else:
                # Try to export as plain text for other formats
                request = self.service.files().export_media(fileId=file_id, mimeType='text/plain')
            
            content = request.execute()
            return content
            
        except HttpError as e:
            logger.error(f"Failed to download file {file_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error downloading document: {e}")
            return None
    
    async def sync_documents(self, user_id: str, force_full_sync: bool = False) -> Dict[str, Any]:
        """
        Sync documents from Google Drive to DocuShield
        """
        if not GOOGLE_DRIVE_AVAILABLE:
            logger.error("Google Drive dependencies not available - install required packages")
            return {
                "total_found": 0,
                "processed": 0,
                "skipped": 0,
                "errors": 1,
                "new_documents": [],
                "error_details": ["Google Drive dependencies not available"]
            }
            
        try:
            sync_start = datetime.utcnow()
            
            # Determine sync window
            if force_full_sync or not self.last_sync:
                modified_since = None
                logger.info("Performing full sync of Google Drive documents")
            else:
                # Sync documents modified since last sync (with 5-minute buffer)
                modified_since = self.last_sync - timedelta(minutes=5)
                logger.info(f"Syncing documents modified since {modified_since}")
            
            # Get documents from Google Drive
            documents = await self.list_documents(modified_since=modified_since)
            
            sync_results = {
                "total_found": len(documents),
                "processed": 0,
                "skipped": 0,
                "errors": 0,
                "new_documents": [],
                "error_details": []
            }
            
            for doc in documents:
                try:
                    # Check file size
                    file_size = int(doc.get('size', 0))
                    max_size = settings.max_file_size_mb * 1024 * 1024
                    
                    if file_size > max_size:
                        logger.warning(f"Skipping large file: {doc['name']} ({file_size} bytes)")
                        sync_results["skipped"] += 1
                        continue
                    
                    # Download document content
                    content = await self.download_document(doc['id'])
                    if not content:
                        sync_results["errors"] += 1
                        sync_results["error_details"].append(f"Failed to download: {doc['name']}")
                        continue
                    
                    # Determine file type
                    mime_type = doc.get('mimeType', '')
                    if 'pdf' in mime_type:
                        file_type = 'pdf'
                    elif 'wordprocessingml' in mime_type:
                        file_type = 'docx'
                    elif 'text' in mime_type:
                        file_type = 'txt'
                    else:
                        file_type = 'unknown'
                    
                    # Extract text content based on file type
                    if file_type == 'pdf':
                        text_content = await self._extract_pdf_text(content)
                    elif file_type == 'docx':
                        text_content = await self._extract_docx_text(content)
                    elif file_type == 'txt':
                        text_content = content.decode('utf-8', errors='ignore')
                    else:
                        text_content = content.decode('utf-8', errors='ignore')
                    
                    if not text_content.strip():
                        logger.warning(f"No text content found in: {doc['name']}")
                        sync_results["skipped"] += 1
                        continue
                    
                    # Create contract record directly (similar to document upload)
                    from app.models import BronzeContract, BronzeContractTextRaw
                    from app.database import get_operational_db
                    import hashlib
                    import uuid
                    
                    # Calculate file hash
                    content_bytes = text_content.encode('utf-8')
                    file_hash = hashlib.sha256(content_bytes).hexdigest()
                    
                    async for db in get_operational_db():
                        # Create bronze contract
                        contract = BronzeContract(
                            filename=doc['name'],
                            mime_type=mime_type,
                            file_size=len(content_bytes),
                            file_hash=file_hash,
                            raw_bytes=content_bytes,
                            owner_user_id=user_id,
                            source="google_drive",
                            source_metadata={
                                "google_drive_id": doc['id'],
                                "modified_time": doc.get('modifiedTime'),
                                "web_view_link": doc.get('webViewLink')
                            },
                            status="uploaded"
                        )
                        db.add(contract)
                        await db.flush()
                        
                        # Create text raw record
                        text_raw = BronzeContractTextRaw(
                            contract_id=contract.contract_id,
                            raw_text=text_content,
                            extraction_method="google_drive_api",
                            extraction_confidence=1.0
                        )
                        db.add(text_raw)
                        await db.commit()
                        
                        doc_id = contract.contract_id
                    
                    sync_results["processed"] += 1
                    sync_results["new_documents"].append({
                        "id": doc_id,
                        "name": doc['name'],
                        "google_drive_id": doc['id'],
                        "size": file_size,
                        "modified": doc.get('modifiedTime')
                    })
                    
                    logger.info(f"Successfully ingested: {doc['name']}")
                    
                except Exception as e:
                    logger.error(f"Error processing document {doc['name']}: {e}")
                    sync_results["errors"] += 1
                    sync_results["error_details"].append(f"Error processing {doc['name']}: {str(e)}")
            
            # Update last sync time
            self.last_sync = sync_start
            
            logger.info(f"Sync completed: {sync_results['processed']} processed, {sync_results['skipped']} skipped, {sync_results['errors']} errors")
            
            return sync_results
            
        except Exception as e:
            logger.error(f"Sync failed: {e}")
            return {
                "total_found": 0,
                "processed": 0,
                "skipped": 0,
                "errors": 1,
                "new_documents": [],
                "error_details": [f"Sync failed: {str(e)}"]
            }
    
    async def _extract_pdf_text(self, content: bytes) -> str:
        """Extract text from PDF bytes"""
        try:
            import io
            import PyPDF2
            
            pdf_file = io.BytesIO(content)
            reader = PyPDF2.PdfReader(pdf_file)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text.strip()
        except Exception as e:
            logger.error(f"Failed to extract PDF text: {e}")
            return ""
    
    async def _extract_docx_text(self, content: bytes) -> str:
        """Extract text from DOCX bytes"""
        try:
            import io
            import docx
            
            docx_file = io.BytesIO(content)
            doc = docx.Document(docx_file)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text.strip()
        except Exception as e:
            logger.error(f"Failed to extract DOCX text: {e}")
            return ""
    
    async def setup_webhook(self) -> Optional[str]:
        """
        Set up Google Drive webhook for real-time updates
        Note: This requires a publicly accessible webhook endpoint
        """
        if not GOOGLE_DRIVE_AVAILABLE:
            logger.error("Google Drive dependencies not available - install required packages")
            return None
            
        try:
            if not self.service:
                if not await self.authenticate():
                    return None
            
            # This would require a webhook endpoint
            # For now, we'll use polling instead
            logger.info("Webhook setup not implemented - using polling for updates")
            return None
            
        except Exception as e:
            logger.error(f"Failed to setup webhook: {e}")
            return None

# Global Google Drive service instance
google_drive_service = GoogleDriveService()

# Background sync task
async def periodic_sync():
    """Periodic sync task for Google Drive documents"""
    while True:
        try:
            if settings.enable_real_time_monitoring:
                logger.info("Starting periodic Google Drive sync")
                results = await google_drive_service.sync_documents()
                
                if results["processed"] > 0:
                    logger.info(f"Synced {results['processed']} new/updated documents from Google Drive")
                
        except Exception as e:
            logger.error(f"Periodic sync failed: {e}")
        
        # Wait for next sync interval
        await asyncio.sleep(settings.monitoring_interval_minutes * 60)
