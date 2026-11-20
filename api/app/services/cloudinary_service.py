import requests
import logging
from typing import Dict, Any
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

CLOUDINARY_CLOUD_NAME = "yrkeqdag"
CLOUDINARY_UPLOAD_PRESET = "rxbridge_reports"
CLOUDINARY_UPLOAD_URL = f"https://api.cloudinary.com/v1_1/{CLOUDINARY_CLOUD_NAME}/auto/upload"

def upload_to_cloudinary(file_bytes: bytes, filename: str, folder: str = "rxbridge") -> Dict[str, Any]:
    """
    Uploads a file buffer (image or PDF) directly to Cloudinary using an unsigned upload preset.
    Returns metadata containing the permanent secure HTTPS URL and public ID.
    """
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot upload empty file to cloud storage"
        )

    try:
        files = {
            "file": (filename, file_bytes)
        }
        data = {
            "upload_preset": CLOUDINARY_UPLOAD_PRESET,
            "folder": folder
        }
        
        response = requests.post(
            CLOUDINARY_UPLOAD_URL,
            files=files,
            data=data,
            timeout=30
        )
        
        if response.status_code != 200:
            logger.error(f"Cloudinary upload failed ({response.status_code}): {response.text}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Cloud storage upload failed: {response.text}"
            )
            
        result = response.json()
        return {
            "secure_url": result.get("secure_url"),
            "public_id": result.get("public_id"),
            "format": result.get("format"),
            "bytes": result.get("bytes")
        }
    except requests.RequestException as e:
        logger.error(f"Cloudinary network connection error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Cloud storage connection error: {str(e)}"
        )
