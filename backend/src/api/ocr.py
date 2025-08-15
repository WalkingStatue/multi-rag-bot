"""
OCR management API endpoints.
"""
import logging
from typing import Dict, List, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ..core.dependencies import get_current_user
from ..core.ocr_config import (
    ocr_settings, 
    check_ocr_availability, 
    get_tesseract_languages,
    validate_ocr_language,
    get_ocr_config
)
from ..models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ocr", tags=["OCR"])


class OCRStatusResponse(BaseModel):
    """OCR status response model."""
    available: bool
    enabled: bool
    message: str
    version_info: str
    installed_languages: List[str]
    available_languages: List[str]
    default_language: str
    config: str


class OCRSettingsUpdate(BaseModel):
    """OCR settings update model."""
    enabled: bool = None
    default_language: str = None


@router.get("/status", response_model=OCRStatusResponse)
async def get_ocr_status(
    current_user: User = Depends(get_current_user)
) -> OCRStatusResponse:
    """
    Get OCR availability and configuration status.
    
    Returns:
        OCR status information
    """
    try:
        # Check OCR availability
        is_available, message = check_ocr_availability()
        
        # Get installed languages
        installed_languages = get_tesseract_languages() if is_available else []
        
        # Get OCR configuration
        config_str = get_ocr_config() if is_available else ""
        
        return OCRStatusResponse(
            available=is_available,
            enabled=ocr_settings.ocr_enabled,
            message=message,
            version_info=message if is_available else "Not available",
            installed_languages=installed_languages,
            available_languages=ocr_settings.ocr_available_languages,
            default_language=ocr_settings.ocr_default_language,
            config=config_str
        )
        
    except Exception as e:
        logger.error(f"Error getting OCR status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get OCR status: {str(e)}"
        )


@router.get("/languages")
async def get_ocr_languages(
    current_user: User = Depends(get_current_user)
) -> Dict[str, List[str]]:
    """
    Get available and installed OCR languages.
    
    Returns:
        Dictionary with available and installed languages
    """
    try:
        installed_languages = get_tesseract_languages()
        
        return {
            "installed": installed_languages,
            "available": ocr_settings.ocr_available_languages,
            "default": ocr_settings.ocr_default_language
        }
        
    except Exception as e:
        logger.error(f"Error getting OCR languages: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get OCR languages: {str(e)}"
        )


@router.post("/test")
async def test_ocr(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Test OCR functionality with a sample image.
    
    Returns:
        Test results
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
        import pytesseract
        from io import BytesIO
        
        # Create a test image with text
        img = Image.new('RGB', (400, 100), color='white')
        draw = ImageDraw.Draw(img)
        
        # Try to use a default font, fallback to default if not available
        try:
            font = ImageFont.load_default()
        except:
            font = None
        
        # Draw test text
        test_text = "OCR Test: Hello World! 123"
        draw.text((10, 30), test_text, fill='black', font=font)
        
        # Convert to bytes
        img_bytes = BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        # Run OCR
        ocr_result = pytesseract.image_to_string(
            Image.open(img_bytes),
            lang=ocr_settings.ocr_default_language,
            config=get_ocr_config()
        ).strip()
        
        # Calculate accuracy (simple comparison)
        accuracy = 0.0
        if ocr_result:
            # Simple word-based accuracy
            original_words = test_text.lower().split()
            ocr_words = ocr_result.lower().split()
            
            correct_words = sum(1 for word in original_words if word in ocr_words)
            accuracy = (correct_words / len(original_words)) * 100 if original_words else 0
        
        return {
            "success": True,
            "original_text": test_text,
            "ocr_result": ocr_result,
            "accuracy_percent": round(accuracy, 2),
            "language_used": ocr_settings.ocr_default_language,
            "config_used": get_ocr_config()
        }
        
    except ImportError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"OCR libraries not available: {str(e)}"
        )
    except Exception as e:
        logger.error(f"OCR test failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OCR test failed: {str(e)}"
        )


@router.get("/config")
async def get_ocr_configuration(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get current OCR configuration settings.
    
    Returns:
        OCR configuration
    """
    return {
        "enabled": ocr_settings.ocr_enabled,
        "default_language": ocr_settings.ocr_default_language,
        "available_languages": ocr_settings.ocr_available_languages,
        "dpi": ocr_settings.ocr_dpi,
        "psm": ocr_settings.ocr_psm,
        "oem": ocr_settings.ocr_oem,
        "enhance_images": ocr_settings.ocr_enhance_images,
        "denoise": ocr_settings.ocr_denoise,
        "sharpen": ocr_settings.ocr_sharpen,
        "max_image_size": ocr_settings.ocr_max_image_size,
        "timeout": ocr_settings.ocr_timeout
    }