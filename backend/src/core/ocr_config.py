"""
OCR configuration and utilities.
"""
import os
import logging
from typing import Dict, List, Optional
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class OCRSettings(BaseSettings):
    """OCR configuration settings."""
    
    # OCR enablement
    ocr_enabled: bool = True
    
    # Default OCR language
    ocr_default_language: str = "eng"
    
    # Available OCR languages
    ocr_available_languages: List[str] = [
        "eng",  # English
        "spa",  # Spanish
        "fra",  # French
        "deu",  # German
        "ita",  # Italian
        "por",  # Portuguese
        "rus",  # Russian
        "chi_sim",  # Chinese Simplified
        "chi_tra",  # Chinese Traditional
        "jpn",  # Japanese
        "kor",  # Korean
        "ara",  # Arabic
        "hin",  # Hindi
    ]
    
    # OCR processing settings
    ocr_dpi: int = 300  # DPI for image rendering
    ocr_psm: int = 6    # Page segmentation mode (6 = uniform block of text)
    ocr_oem: int = 3    # OCR Engine Mode (3 = default)
    
    # Image preprocessing settings
    ocr_enhance_images: bool = True
    ocr_denoise: bool = True
    ocr_sharpen: bool = True
    
    # Performance settings
    ocr_max_image_size: int = 4096  # Max width/height for OCR processing
    ocr_timeout: int = 30  # Timeout in seconds for OCR processing
    
    class Config:
        env_prefix = "OCR_"
        case_sensitive = False


def get_ocr_config() -> Dict[str, str]:
    """
    Get OCR configuration string for pytesseract.
    
    Returns:
        Configuration string for pytesseract
    """
    settings = OCRSettings()
    
    config_parts = [
        f"--psm {settings.ocr_psm}",
        f"--oem {settings.ocr_oem}",
        f"--dpi {settings.ocr_dpi}"
    ]
    
    if settings.ocr_timeout:
        config_parts.append(f"--timeout {settings.ocr_timeout}")
    
    return " ".join(config_parts)


def validate_ocr_language(language: str) -> bool:
    """
    Validate if OCR language is supported.
    
    Args:
        language: Language code to validate
        
    Returns:
        True if language is supported
    """
    settings = OCRSettings()
    return language in settings.ocr_available_languages


def get_tesseract_languages() -> List[str]:
    """
    Get list of actually installed Tesseract languages.
    
    Returns:
        List of installed language codes
    """
    try:
        import pytesseract
        langs = pytesseract.get_languages(config='')
        logger.info(f"Available Tesseract languages: {langs}")
        return langs
    except Exception as e:
        logger.warning(f"Could not get Tesseract languages: {e}")
        return ["eng"]  # Default fallback


def check_ocr_availability() -> tuple[bool, str]:
    """
    Check if OCR is available and properly configured.
    
    Returns:
        Tuple of (is_available, error_message)
    """
    try:
        import pytesseract
        from PIL import Image
        
        # Test basic OCR functionality
        version = pytesseract.get_tesseract_version()
        logger.info(f"Tesseract version: {version}")
        
        # Test with a simple image
        test_image = Image.new('RGB', (100, 30), color='white')
        test_result = pytesseract.image_to_string(test_image)
        
        return True, f"OCR available (Tesseract {version})"
        
    except ImportError as e:
        return False, f"OCR libraries not installed: {e}"
    except Exception as e:
        return False, f"OCR not available: {e}"


# Global OCR settings instance
ocr_settings = OCRSettings()