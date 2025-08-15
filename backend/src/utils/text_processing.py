"""
Text processing utilities for document chunking and extraction with OCR support.
"""
import re
import logging
from typing import List, Dict, Any, Optional, Tuple, Union
from pathlib import Path
from io import BytesIO
import tempfile
import os
from dataclasses import dataclass, asdict
from enum import Enum

# PDF processing with OCR support
import fitz  # PyMuPDF
import pytesseract
from PIL import Image

# Try to import python-magic, fall back to mimetypes if not available
try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    import mimetypes
    MAGIC_AVAILABLE = False

logger = logging.getLogger(__name__)


class ChunkingStrategy(Enum):
    """Enumeration of available chunking strategies."""
    LEGACY = "legacy"
    SEMANTIC = "semantic"
    ADAPTIVE = "adaptive"
    CUSTOM = "custom"


class DocumentFormat(Enum):
    """Enumeration of supported document formats."""
    PLAIN = "plain"
    MARKDOWN = "markdown"
    CODE = "code"
    STRUCTURED = "structured"
    AUTO_DETECT = "auto_detect"


@dataclass
class ChunkingConfig:
    """Configuration class for text chunking parameters."""
    
    # Basic parameters
    chunk_size: int = 1000
    chunk_overlap: int = 200
    
    # Semantic chunking parameters
    respect_structure: bool = True
    semantic_coherence_priority: bool = True
    format_specific_chunking: bool = True
    max_size_deviation: float = 0.3
    
    # Strategy and format
    strategy: ChunkingStrategy = ChunkingStrategy.ADAPTIVE
    document_format: DocumentFormat = DocumentFormat.AUTO_DETECT
    
    # Advanced parameters
    min_chunk_size: Optional[int] = None
    max_chunk_size: Optional[int] = None
    preserve_code_blocks: bool = True
    preserve_tables: bool = True
    split_long_sentences: bool = True
    sentence_split_threshold: int = 300
    
    # Quality thresholds
    min_coherence_score: float = 0.3
    target_coherence_score: float = 0.8
    
    def __post_init__(self):
        """Validate and set derived parameters after initialization."""
        # Set min/max chunk sizes if not provided
        if self.min_chunk_size is None:
            self.min_chunk_size = int(self.chunk_size * (1 - self.max_size_deviation))
        if self.max_chunk_size is None:
            self.max_chunk_size = int(self.chunk_size * (1 + self.max_size_deviation))
        
        # Validate parameters
        self._validate_parameters()
    
    def _validate_parameters(self):
        """Validate configuration parameters."""
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("Chunk overlap must be less than chunk size")
        if self.chunk_size <= 0:
            raise ValueError("Chunk size must be positive")
        if self.chunk_overlap < 0:
            raise ValueError("Chunk overlap must be non-negative")
        if not 0 <= self.max_size_deviation <= 1:
            raise ValueError("Max size deviation must be between 0 and 1")
        if not 0 <= self.min_coherence_score <= 1:
            raise ValueError("Min coherence score must be between 0 and 1")
        if not 0 <= self.target_coherence_score <= 1:
            raise ValueError("Target coherence score must be between 0 and 1")
        if self.min_chunk_size >= self.max_chunk_size:
            raise ValueError("Min chunk size must be less than max chunk size")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        config_dict = asdict(self)
        # Convert enums to strings
        config_dict['strategy'] = self.strategy.value
        config_dict['document_format'] = self.document_format.value
        return config_dict
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'ChunkingConfig':
        """Create configuration from dictionary."""
        # Convert string enums back to enum objects
        if 'strategy' in config_dict:
            config_dict['strategy'] = ChunkingStrategy(config_dict['strategy'])
        if 'document_format' in config_dict:
            config_dict['document_format'] = DocumentFormat(config_dict['document_format'])
        
        return cls(**config_dict)
    
    @classmethod
    def get_optimized_config(
        cls,
        content_type: str = "general",
        document_length: int = 10000,
        target_use_case: str = "rag"
    ) -> 'ChunkingConfig':
        """
        Get optimized configuration based on content characteristics.
        
        Args:
            content_type: Type of content ('code', 'academic', 'technical', 'general')
            document_length: Length of document in characters
            target_use_case: Target use case ('rag', 'summarization', 'qa')
            
        Returns:
            Optimized ChunkingConfig
        """
        # Base configuration
        config = cls()
        
        # Adjust based on content type
        if content_type == "code":
            config.chunk_size = 800
            config.chunk_overlap = 100
            config.preserve_code_blocks = True
            config.format_specific_chunking = True
            config.document_format = DocumentFormat.CODE
            
        elif content_type == "academic":
            config.chunk_size = 1200
            config.chunk_overlap = 300
            config.respect_structure = True
            config.semantic_coherence_priority = True
            config.preserve_tables = True
            
        elif content_type == "technical":
            config.chunk_size = 1000
            config.chunk_overlap = 250
            config.respect_structure = True
            config.preserve_tables = True
            config.format_specific_chunking = True
            
        # Adjust based on document length
        if document_length < 5000:
            # Short documents - smaller chunks for better granularity
            config.chunk_size = int(config.chunk_size * 0.8)
            config.chunk_overlap = int(config.chunk_overlap * 0.8)
        elif document_length > 50000:
            # Long documents - larger chunks for efficiency
            config.chunk_size = int(config.chunk_size * 1.2)
            config.chunk_overlap = int(config.chunk_overlap * 1.1)
        
        # Adjust based on use case
        if target_use_case == "summarization":
            config.chunk_size = int(config.chunk_size * 1.5)
            config.chunk_overlap = int(config.chunk_overlap * 0.8)
        elif target_use_case == "qa":
            config.chunk_overlap = int(config.chunk_overlap * 1.2)
            config.semantic_coherence_priority = True
        
        return config


@dataclass
class ChunkingMetrics:
    """Metrics for evaluating chunking quality and performance."""
    
    total_chunks: int = 0
    avg_chunk_size: float = 0.0
    min_chunk_size: int = 0
    max_chunk_size: int = 0
    size_variance: float = 0.0
    size_consistency: float = 0.0
    
    avg_coherence_score: float = 0.0
    min_coherence_score: float = 0.0
    max_coherence_score: float = 0.0
    
    structure_preservation: float = 0.0
    semantic_boundary_respect: float = 0.0
    
    processing_time_ms: float = 0.0
    chunks_per_second: float = 0.0
    
    chunk_type_distribution: Dict[str, int] = None
    quality_score: float = 0.0
    
    def __post_init__(self):
        """Initialize default values."""
        if self.chunk_type_distribution is None:
            self.chunk_type_distribution = {}


class ChunkingOptimizer:
    """Optimizer for chunking configuration based on content analysis."""
    
    def __init__(self):
        """Initialize the chunking optimizer."""
        self.performance_history: List[Dict[str, Any]] = []
    
    def analyze_content_characteristics(self, text: str) -> Dict[str, Any]:
        """
        Analyze content to determine optimal chunking parameters.
        
        Args:
            text: Text content to analyze
            
        Returns:
            Dictionary with content characteristics
        """
        characteristics = {
            "length": len(text),
            "word_count": len(text.split()),
            "line_count": len(text.splitlines()),
            "paragraph_count": len(re.split(r'\n\s*\n', text)),
            "sentence_count": len(re.split(r'[.!?]+', text)),
            "avg_sentence_length": 0,
            "avg_paragraph_length": 0,
            "has_code_blocks": False,
            "has_tables": False,
            "has_headers": False,
            "has_lists": False,
            "structure_density": 0.0,
            "complexity_score": 0.0
        }
        
        # Calculate averages
        if characteristics["sentence_count"] > 0:
            characteristics["avg_sentence_length"] = characteristics["length"] / characteristics["sentence_count"]
        if characteristics["paragraph_count"] > 0:
            characteristics["avg_paragraph_length"] = characteristics["length"] / characteristics["paragraph_count"]
        
        # Detect structural elements
        characteristics["has_code_blocks"] = bool(re.search(r'```|`[^`]+`', text))
        characteristics["has_tables"] = bool(re.search(r'\|.*\|', text))
        characteristics["has_headers"] = bool(re.search(r'^#{1,6}\s+|^[A-Z][A-Z\s]+:?\s*$', text, re.MULTILINE))
        characteristics["has_lists"] = bool(re.search(r'^\s*[-*•]\s+|^\s*\d+\.\s+', text, re.MULTILINE))
        
        # Calculate structure density
        structure_elements = sum([
            characteristics["has_code_blocks"],
            characteristics["has_tables"],
            characteristics["has_headers"],
            characteristics["has_lists"]
        ])
        characteristics["structure_density"] = structure_elements / 4.0
        
        # Calculate complexity score
        complexity_factors = [
            min(characteristics["avg_sentence_length"] / 100, 1.0),  # Sentence complexity
            min(characteristics["structure_density"], 1.0),  # Structure complexity
            min(characteristics["paragraph_count"] / (characteristics["length"] / 1000), 1.0)  # Organization complexity
        ]
        characteristics["complexity_score"] = sum(complexity_factors) / len(complexity_factors)
        
        return characteristics
    
    def recommend_configuration(
        self,
        text: str,
        current_config: Optional[ChunkingConfig] = None,
        target_metrics: Optional[Dict[str, float]] = None
    ) -> Tuple[ChunkingConfig, Dict[str, Any]]:
        """
        Recommend optimal chunking configuration based on content analysis.
        
        Args:
            text: Text content to analyze
            current_config: Current configuration (if any)
            target_metrics: Target quality metrics
            
        Returns:
            Tuple of (recommended_config, analysis_report)
        """
        # Analyze content characteristics
        characteristics = self.analyze_content_characteristics(text)
        
        # Determine content type
        content_type = self._classify_content_type(characteristics)
        
        # Get base optimized configuration
        recommended_config = ChunkingConfig.get_optimized_config(
            content_type=content_type,
            document_length=characteristics["length"],
            target_use_case="rag"
        )
        
        # Fine-tune based on specific characteristics
        recommended_config = self._fine_tune_config(recommended_config, characteristics)
        
        # Generate analysis report
        analysis_report = {
            "content_characteristics": characteristics,
            "detected_content_type": content_type,
            "configuration_changes": self._compare_configs(current_config, recommended_config) if current_config else {},
            "expected_improvements": self._predict_improvements(characteristics, recommended_config),
            "recommendations": self._generate_recommendations(characteristics, recommended_config)
        }
        
        return recommended_config, analysis_report
    
    def _classify_content_type(self, characteristics: Dict[str, Any]) -> str:
        """Classify content type based on characteristics."""
        if characteristics["has_code_blocks"] and characteristics["structure_density"] > 0.5:
            return "code"
        elif characteristics["avg_sentence_length"] > 150 and characteristics["structure_density"] > 0.3:
            return "academic"
        elif characteristics["has_tables"] or characteristics["structure_density"] > 0.4:
            return "technical"
        else:
            return "general"
    
    def _fine_tune_config(self, config: ChunkingConfig, characteristics: Dict[str, Any]) -> ChunkingConfig:
        """Fine-tune configuration based on specific content characteristics."""
        # Adjust chunk size based on sentence length
        if characteristics["avg_sentence_length"] > 200:
            config.chunk_size = int(config.chunk_size * 1.2)
        elif characteristics["avg_sentence_length"] < 50:
            config.chunk_size = int(config.chunk_size * 0.8)
        
        # Adjust overlap based on complexity
        if characteristics["complexity_score"] > 0.7:
            config.chunk_overlap = int(config.chunk_overlap * 1.3)
        elif characteristics["complexity_score"] < 0.3:
            config.chunk_overlap = int(config.chunk_overlap * 0.8)
        
        # Enable specific features based on content
        if characteristics["has_code_blocks"]:
            config.preserve_code_blocks = True
            config.format_specific_chunking = True
        
        if characteristics["has_tables"]:
            config.preserve_tables = True
        
        if characteristics["structure_density"] > 0.5:
            config.respect_structure = True
            config.semantic_coherence_priority = True
        
        return config
    
    def _compare_configs(self, old_config: ChunkingConfig, new_config: ChunkingConfig) -> Dict[str, Any]:
        """Compare two configurations and highlight changes."""
        changes = {}
        
        old_dict = old_config.to_dict()
        new_dict = new_config.to_dict()
        
        for key, new_value in new_dict.items():
            old_value = old_dict.get(key)
            if old_value != new_value:
                changes[key] = {
                    "old": old_value,
                    "new": new_value,
                    "change_type": "modified" if old_value is not None else "added"
                }
        
        return changes
    
    def _predict_improvements(self, characteristics: Dict[str, Any], config: ChunkingConfig) -> Dict[str, str]:
        """Predict expected improvements from the recommended configuration."""
        improvements = []
        
        if config.semantic_coherence_priority:
            improvements.append("Better semantic coherence in chunks")
        
        if config.respect_structure:
            improvements.append("Improved preservation of document structure")
        
        if config.format_specific_chunking:
            improvements.append("Format-aware chunking for better context")
        
        if characteristics["complexity_score"] > 0.5 and config.chunk_overlap > 200:
            improvements.append("Enhanced context preservation for complex content")
        
        return {"expected_improvements": improvements}
    
    def _generate_recommendations(self, characteristics: Dict[str, Any], config: ChunkingConfig) -> List[str]:
        """Generate specific recommendations based on analysis."""
        recommendations = []
        
        if characteristics["avg_sentence_length"] > 300:
            recommendations.append("Consider enabling sentence splitting for very long sentences")
        
        if characteristics["structure_density"] > 0.6:
            recommendations.append("High structure density detected - semantic chunking will provide better results")
        
        if characteristics["has_code_blocks"]:
            recommendations.append("Code blocks detected - enable code-specific chunking strategies")
        
        if characteristics["length"] > 100000:
            recommendations.append("Large document detected - consider increasing chunk size for efficiency")
        
        if not recommendations:
            recommendations.append("Configuration appears optimal for this content type")
        
        return recommendations
    
    def track_performance(self, config: ChunkingConfig, metrics: ChunkingMetrics, content_characteristics: Dict[str, Any]):
        """Track performance of chunking configurations for future optimization."""
        performance_record = {
            "timestamp": "now",  # In real implementation, use datetime
            "config": config.to_dict(),
            "metrics": asdict(metrics),
            "content_characteristics": content_characteristics,
            "quality_score": metrics.quality_score
        }
        
        self.performance_history.append(performance_record)
        
        # Keep only recent history (last 100 records)
        if len(self.performance_history) > 100:
            self.performance_history = self.performance_history[-100:]
    
    def get_performance_insights(self) -> Dict[str, Any]:
        """Get insights from performance history."""
        if not self.performance_history:
            return {"message": "No performance history available"}
        
        # Analyze trends
        recent_records = self.performance_history[-10:]
        avg_quality = sum(record["quality_score"] for record in recent_records) / len(recent_records)
        
        # Find best performing configurations
        best_record = max(self.performance_history, key=lambda x: x["quality_score"])
        
        return {
            "recent_avg_quality": avg_quality,
            "best_quality_score": best_record["quality_score"],
            "best_config": best_record["config"],
            "total_evaluations": len(self.performance_history),
            "trends": self._analyze_trends()
        }
    
    def _analyze_trends(self) -> Dict[str, Any]:
        """Analyze performance trends from history."""
        if len(self.performance_history) < 5:
            return {"message": "Insufficient data for trend analysis"}
        
        # Simple trend analysis
        recent_scores = [record["quality_score"] for record in self.performance_history[-10:]]
        older_scores = [record["quality_score"] for record in self.performance_history[-20:-10]] if len(self.performance_history) >= 20 else []
        
        if older_scores:
            recent_avg = sum(recent_scores) / len(recent_scores)
            older_avg = sum(older_scores) / len(older_scores)
            trend = "improving" if recent_avg > older_avg else "declining" if recent_avg < older_avg else "stable"
        else:
            trend = "insufficient_data"
        
        return {
            "quality_trend": trend,
            "recent_avg": sum(recent_scores) / len(recent_scores),
            "score_variance": sum((score - sum(recent_scores) / len(recent_scores)) ** 2 for score in recent_scores) / len(recent_scores)
        }


class TextChunk:
    """Represents a chunk of text with metadata."""
    
    def __init__(
        self,
        content: str,
        chunk_index: int,
        start_char: int,
        end_char: int,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.content = content
        self.chunk_index = chunk_index
        self.start_char = start_char
        self.end_char = end_char
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert chunk to dictionary representation."""
        return {
            "content": self.content,
            "chunk_index": self.chunk_index,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "metadata": self.metadata
        }


class DocumentExtractor:
    """Handles text extraction from various document formats with OCR support and security checks."""
    
    ALLOWED_MIME_TYPES = {
        'application/pdf': 'pdf',
        'text/plain': 'txt',
        'text/x-python': 'txt',  # Python files as text
        'application/x-empty': 'txt',  # Empty files
        'image/jpeg': 'image',
        'image/png': 'image',
        'image/tiff': 'image',
        'image/bmp': 'image'
    }
    
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    
    def __init__(self, enable_ocr: bool = True, ocr_language: str = 'eng'):
        """
        Initialize document extractor.
        
        Args:
            enable_ocr: Whether to enable OCR for scanned PDFs and images
            ocr_language: Language code for OCR (e.g., 'eng', 'spa', 'fra')
        """
        self.enable_ocr = enable_ocr
        self.ocr_language = ocr_language
        
        # Test OCR availability
        if self.enable_ocr:
            try:
                # Test pytesseract installation
                pytesseract.get_tesseract_version()
                logger.info(f"OCR enabled with language: {ocr_language}")
            except Exception as e:
                logger.warning(f"OCR not available, disabling: {e}")
                self.enable_ocr = False
    
    @classmethod
    def validate_file(cls, file_path: Path, file_content: bytes) -> Tuple[bool, str, str]:
        """
        Validate file type and size with security checks.
        
        Args:
            file_path: Path to the file
            file_content: File content as bytes
            
        Returns:
            Tuple of (is_valid, mime_type, error_message)
        """
        try:
            # Check file size
            if len(file_content) > cls.MAX_FILE_SIZE:
                return False, "", f"File size exceeds maximum allowed size of {cls.MAX_FILE_SIZE} bytes"
            
            # Check file extension
            file_extension = file_path.suffix.lower()
            allowed_extensions = ['.pdf', '.txt', '.py', '.md', '.jpg', '.jpeg', '.png', '.tiff', '.bmp']
            if file_extension not in allowed_extensions:
                return False, "", f"Unsupported file extension: {file_extension}"
            
            # Detect MIME type
            if MAGIC_AVAILABLE:
                try:
                    mime_type = magic.from_buffer(file_content, mime=True)
                except Exception as e:
                    logger.warning(f"python-magic failed, falling back to mimetypes: {e}")
                    mime_type, _ = mimetypes.guess_type(str(file_path))
                    mime_type = mime_type or "application/octet-stream"
            else:
                # Fallback to mimetypes module
                mime_type, _ = mimetypes.guess_type(str(file_path))
                if not mime_type:
                    # Basic detection based on file extension
                    if file_extension == '.pdf':
                        mime_type = 'application/pdf'
                    elif file_extension in ['.txt', '.py', '.md']:
                        mime_type = 'text/plain'
                    elif file_extension in ['.jpg', '.jpeg']:
                        mime_type = 'image/jpeg'
                    elif file_extension == '.png':
                        mime_type = 'image/png'
                    elif file_extension in ['.tiff', '.tif']:
                        mime_type = 'image/tiff'
                    elif file_extension == '.bmp':
                        mime_type = 'image/bmp'
                    else:
                        mime_type = 'application/octet-stream'
            
            # Validate MIME type
            if mime_type not in cls.ALLOWED_MIME_TYPES:
                return False, mime_type, f"Unsupported MIME type: {mime_type}"
            
            return True, mime_type, ""
            
        except Exception as e:
            logger.error(f"Error validating file {file_path}: {e}")
            return False, "", f"File validation error: {str(e)}"
    
    def extract_text(self, file_content: bytes, mime_type: str, filename: str) -> Tuple[str, Dict[str, Any]]:
        """
        Extract text from file content based on MIME type.
        
        Args:
            file_content: File content as bytes
            mime_type: MIME type of the file
            filename: Original filename
            
        Returns:
            Tuple of (extracted_text, metadata)
        """
        try:
            if mime_type == 'application/pdf':
                return self._extract_pdf_text(file_content, filename)
            elif mime_type in ['text/plain', 'text/x-python', 'application/x-empty']:
                return self._extract_text_file(file_content, filename)
            elif mime_type.startswith('image/'):
                return self._extract_image_text(file_content, filename)
            else:
                raise ValueError(f"Unsupported MIME type for extraction: {mime_type}")
                
        except Exception as e:
            logger.error(f"Error extracting text from {filename}: {e}")
            raise ValueError(f"Text extraction failed: {str(e)}")
    
    def _extract_pdf_text(self, file_content: bytes, filename: str) -> Tuple[str, Dict[str, Any]]:
        """Extract text from PDF file with OCR fallback for scanned documents."""
        pdf_document = None
        try:
            # Open PDF with PyMuPDF
            pdf_document = fitz.open(stream=file_content, filetype="pdf")
            
            text_parts = []
            page_metadata = []
            ocr_pages = []
            total_images_processed = 0
            total_pages = len(pdf_document)
            
            for page_num in range(total_pages):
                try:
                    page = pdf_document[page_num]
                    
                    # First, try to extract text directly
                    page_text = page.get_text()
                    
                    # If no text or very little text, try OCR on the page
                    if self.enable_ocr and (not page_text.strip() or len(page_text.strip()) < 50):
                        logger.info(f"Page {page_num + 1} has little/no text, attempting OCR")
                        
                        try:
                            # Render page as image
                            mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for better OCR
                            pix = page.get_pixmap(matrix=mat)
                            img_data = pix.tobytes("png")
                            
                            # Clean up pixmap immediately
                            pix = None
                            
                            # Convert to PIL Image and run OCR
                            image = Image.open(BytesIO(img_data))
                            ocr_text = pytesseract.image_to_string(
                                image, 
                                lang=self.ocr_language,
                                config='--psm 6'  # Uniform block of text
                            )
                            
                            # Clean up image
                            image.close()
                            
                            if ocr_text.strip():
                                page_text = ocr_text
                                ocr_pages.append(page_num + 1)
                                logger.info(f"OCR extracted {len(ocr_text)} characters from page {page_num + 1}")
                            
                        except Exception as e:
                            logger.warning(f"OCR failed for page {page_num + 1}: {e}")
                    
                    # Also extract text from images within the page
                    if self.enable_ocr:
                        try:
                            image_list = page.get_images()
                            for img_index, img in enumerate(image_list):
                                try:
                                    xref = img[0]
                                    pix = fitz.Pixmap(pdf_document, xref)
                                    
                                    if pix.n - pix.alpha < 4:  # GRAY or RGB
                                        img_data = pix.tobytes("png")
                                        image = Image.open(BytesIO(img_data))
                                        
                                        # Run OCR on the image
                                        img_text = pytesseract.image_to_string(
                                            image,
                                            lang=self.ocr_language,
                                            config='--psm 6'
                                        )
                                        
                                        # Clean up image
                                        image.close()
                                        
                                        if img_text.strip():
                                            page_text += f"\n[Image {img_index + 1} text]: {img_text}"
                                            total_images_processed += 1
                                    
                                    # Clean up pixmap immediately
                                    pix = None
                                    
                                except Exception as e:
                                    logger.warning(f"Failed to extract text from image {img_index + 1} on page {page_num + 1}: {e}")
                        except Exception as e:
                            logger.warning(f"Failed to process images on page {page_num + 1}: {e}")
                    
                    if page_text.strip():
                        text_parts.append(page_text)
                        page_metadata.append({
                            "page_number": page_num + 1,
                            "char_start": len("\n".join(text_parts[:-1])) + (1 if text_parts[:-1] else 0),
                            "char_end": len("\n".join(text_parts)),
                            "used_ocr": (page_num + 1) in ocr_pages,
                            "image_count": len(page.get_images()) if hasattr(page, 'get_images') else 0
                        })
                
                except Exception as e:
                    logger.warning(f"Error processing page {page_num + 1}: {e}")
                    continue
            
            full_text = "\n".join(text_parts)
            
            metadata = {
                "total_pages": total_pages,
                "extracted_pages": len(page_metadata),
                "ocr_pages": ocr_pages,
                "ocr_enabled": self.enable_ocr,
                "images_processed": total_images_processed,
                "page_metadata": page_metadata,
                "extraction_method": "PyMuPDF + OCR" if ocr_pages else "PyMuPDF"
            }
            
            return full_text, metadata
            
        except Exception as e:
            logger.error(f"PDF extraction failed for {filename}: {e}")
            raise ValueError(f"PDF extraction failed: {str(e)}")
        finally:
            # Ensure PDF document is properly closed
            if pdf_document is not None:
                try:
                    pdf_document.close()
                except:
                    pass
    
    def _extract_image_text(self, file_content: bytes, filename: str) -> Tuple[str, Dict[str, Any]]:
        """Extract text from image file using OCR."""
        if not self.enable_ocr:
            raise ValueError("OCR is disabled, cannot extract text from images")
        
        try:
            # Open image with PIL
            image = Image.open(BytesIO(file_content))
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Run OCR
            extracted_text = pytesseract.image_to_string(
                image,
                lang=self.ocr_language,
                config='--psm 6'  # Uniform block of text
            )
            
            # Get image info
            width, height = image.size
            
            metadata = {
                "image_width": width,
                "image_height": height,
                "image_mode": image.mode,
                "ocr_language": self.ocr_language,
                "extraction_method": "OCR (pytesseract)",
                "char_count": len(extracted_text)
            }
            
            return extracted_text, metadata
            
        except Exception as e:
            logger.error(f"Image OCR extraction failed for {filename}: {e}")
            raise ValueError(f"Image OCR extraction failed: {str(e)}")
    
    def _extract_text_file(self, file_content: bytes, filename: str) -> Tuple[str, Dict[str, Any]]:
        """Extract text from plain text file."""
        try:
            # Try different encodings
            encodings = ['utf-8', 'utf-16', 'latin-1', 'cp1252']
            
            for encoding in encodings:
                try:
                    text = file_content.decode(encoding)
                    metadata = {
                        "encoding": encoding,
                        "line_count": len(text.splitlines()),
                        "char_count": len(text)
                    }
                    return text, metadata
                except UnicodeDecodeError:
                    continue
            
            # If all encodings fail, use utf-8 with error handling
            text = file_content.decode('utf-8', errors='replace')
            metadata = {
                "encoding": "utf-8 (with errors replaced)",
                "line_count": len(text.splitlines()),
                "char_count": len(text)
            }
            
            return text, metadata
            
        except Exception as e:
            logger.error(f"Text file extraction failed for {filename}: {e}")
            raise ValueError(f"Text file extraction failed: {str(e)}")


class SemanticTextChunker:
    """Handles semantic-aware text chunking with document structure preservation."""
    
    # Document structure patterns
    SECTION_PATTERNS = [
        r'^#{1,6}\s+.+$',  # Markdown headers
        r'^[A-Z][A-Z\s]+:?\s*$',  # ALL CAPS headers
        r'^\d+\.\s+[A-Z].+$',  # Numbered sections
        r'^[IVX]+\.\s+[A-Z].+$',  # Roman numeral sections
        r'^Chapter\s+\d+',  # Chapter headers
        r'^Section\s+\d+',  # Section headers
        r'^Part\s+[IVX\d]+',  # Part headers
    ]
    
    # Sentence ending patterns
    SENTENCE_ENDINGS = [
        r'[.!?]+\s+[A-Z]',  # Standard sentence endings
        r'[.!?]+\s*\n',  # Sentence ending with newline
        r'[.!?]+\s*$',  # Sentence ending at end of text
    ]
    
    # Paragraph patterns
    PARAGRAPH_PATTERNS = [
        r'\n\s*\n',  # Double newlines
        r'\n\s*[-*•]\s+',  # List items
        r'\n\s*\d+\.\s+',  # Numbered lists
    ]
    
    def __init__(
        self,
        config: Optional[ChunkingConfig] = None,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        respect_structure: Optional[bool] = None,
        semantic_coherence_priority: Optional[bool] = None,
        format_specific_chunking: Optional[bool] = None,
        max_size_deviation: Optional[float] = None
    ):
        """
        Initialize semantic text chunker with configuration support.
        
        Args:
            config: ChunkingConfig object (preferred method)
            chunk_size: Target size for each chunk in characters (legacy)
            chunk_overlap: Number of characters to overlap between chunks (legacy)
            respect_structure: Whether to respect document structure (legacy)
            semantic_coherence_priority: Whether to prioritize semantic coherence over size (legacy)
            format_specific_chunking: Whether to use format-specific strategies (legacy)
            max_size_deviation: Maximum allowed deviation from chunk_size for semantic coherence (legacy)
        """
        # Use provided config or create from legacy parameters
        if config is not None:
            self.config = config
        else:
            # Create config from legacy parameters
            self.config = ChunkingConfig(
                chunk_size=chunk_size or 1000,
                chunk_overlap=chunk_overlap or 200,
                respect_structure=respect_structure if respect_structure is not None else True,
                semantic_coherence_priority=semantic_coherence_priority if semantic_coherence_priority is not None else True,
                format_specific_chunking=format_specific_chunking if format_specific_chunking is not None else True,
                max_size_deviation=max_size_deviation or 0.3
            )
        
        # Set convenience properties for backward compatibility
        self.chunk_size = self.config.chunk_size
        self.chunk_overlap = self.config.chunk_overlap
        self.respect_structure = self.config.respect_structure
        self.semantic_coherence_priority = self.config.semantic_coherence_priority
        self.format_specific_chunking = self.config.format_specific_chunking
        self.max_size_deviation = self.config.max_size_deviation
        self.min_chunk_size = self.config.min_chunk_size
        self.max_chunk_size = self.config.max_chunk_size
        
        # Initialize optimizer
        self.optimizer = ChunkingOptimizer()
    
    def validate_chunking_parameters(self) -> Dict[str, Any]:
        """
        Validate chunking parameters and provide optimization recommendations.
        
        Returns:
            Dictionary with validation results and recommendations
        """
        validation_result = {
            "is_valid": True,
            "warnings": [],
            "recommendations": [],
            "parameter_analysis": {}
        }
        
        # Analyze chunk size
        if self.chunk_size < 200:
            validation_result["warnings"].append("Very small chunk size may lead to fragmented context")
            validation_result["recommendations"].append("Consider increasing chunk_size to at least 200 characters")
        elif self.chunk_size > 2000:
            validation_result["warnings"].append("Large chunk size may exceed model context limits")
            validation_result["recommendations"].append("Consider reducing chunk_size to under 2000 characters")
        
        # Analyze overlap
        overlap_ratio = self.chunk_overlap / self.chunk_size
        if overlap_ratio < 0.1:
            validation_result["warnings"].append("Low overlap may cause context loss between chunks")
            validation_result["recommendations"].append("Consider increasing overlap to at least 10% of chunk size")
        elif overlap_ratio > 0.5:
            validation_result["warnings"].append("High overlap may cause excessive redundancy")
            validation_result["recommendations"].append("Consider reducing overlap to under 50% of chunk size")
        
        # Analyze semantic coherence settings
        if not self.semantic_coherence_priority:
            validation_result["recommendations"].append("Enable semantic_coherence_priority for better context preservation")
        
        if not self.respect_structure:
            validation_result["recommendations"].append("Enable respect_structure for better document organization")
        
        validation_result["parameter_analysis"] = {
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "overlap_ratio": overlap_ratio,
            "size_bounds": (self.min_chunk_size, self.max_chunk_size),
            "semantic_features_enabled": self.semantic_coherence_priority and self.respect_structure
        }
        
        return validation_result
    
    def optimize_for_content(self, text: str) -> Tuple[ChunkingConfig, Dict[str, Any]]:
        """
        Optimize chunking configuration for specific content.
        
        Args:
            text: Text content to optimize for
            
        Returns:
            Tuple of (optimized_config, optimization_report)
        """
        return self.optimizer.recommend_configuration(text, self.config)
    
    def apply_optimized_config(self, optimized_config: ChunkingConfig):
        """
        Apply an optimized configuration to this chunker.
        
        Args:
            optimized_config: The optimized configuration to apply
        """
        self.config = optimized_config
        
        # Update convenience properties
        self.chunk_size = self.config.chunk_size
        self.chunk_overlap = self.config.chunk_overlap
        self.respect_structure = self.config.respect_structure
        self.semantic_coherence_priority = self.config.semantic_coherence_priority
        self.format_specific_chunking = self.config.format_specific_chunking
        self.max_size_deviation = self.config.max_size_deviation
        self.min_chunk_size = self.config.min_chunk_size
        self.max_chunk_size = self.config.max_chunk_size
    
    def chunk_with_adaptive_optimization(
        self,
        text: str,
        document_metadata: Optional[Dict[str, Any]] = None,
        document_format: Optional[str] = None,
        auto_optimize: bool = True
    ) -> Tuple[List[TextChunk], ChunkingMetrics, Dict[str, Any]]:
        """
        Chunk text with adaptive optimization based on content analysis.
        
        Args:
            text: Text to chunk
            document_metadata: Optional metadata to include in chunks
            document_format: Document format hint
            auto_optimize: Whether to automatically optimize configuration
            
        Returns:
            Tuple of (chunks, metrics, optimization_report)
        """
        import time
        start_time = time.time()
        
        optimization_report = {}
        
        # Optimize configuration if requested
        if auto_optimize:
            optimized_config, opt_report = self.optimize_for_content(text)
            optimization_report = opt_report
            
            # Apply optimization if it's significantly better
            if self._should_apply_optimization(optimized_config, opt_report):
                original_config = self.config
                self.apply_optimized_config(optimized_config)
                optimization_report["config_applied"] = True
                optimization_report["original_config"] = original_config.to_dict()
                optimization_report["optimized_config"] = optimized_config.to_dict()
            else:
                optimization_report["config_applied"] = False
                optimization_report["reason"] = "Optimization did not meet improvement threshold"
        
        # Perform chunking
        chunks = self.chunk_text(text, document_metadata, document_format)
        
        # Calculate metrics
        processing_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        metrics = self._calculate_chunking_metrics(chunks, processing_time)
        
        # Track performance for future optimization
        if hasattr(self, 'optimizer'):
            content_characteristics = self.optimizer.analyze_content_characteristics(text)
            self.optimizer.track_performance(self.config, metrics, content_characteristics)
        
        return chunks, metrics, optimization_report
    
    def _should_apply_optimization(self, optimized_config: ChunkingConfig, optimization_report: Dict[str, Any]) -> bool:
        """
        Determine if an optimized configuration should be applied.
        
        Args:
            optimized_config: The proposed optimized configuration
            optimization_report: Report from the optimization process
            
        Returns:
            True if optimization should be applied
        """
        # Apply optimization if there are significant changes that could improve quality
        changes = optimization_report.get("configuration_changes", {})
        
        # Check for meaningful changes
        meaningful_changes = [
            "chunk_size", "chunk_overlap", "respect_structure",
            "semantic_coherence_priority", "format_specific_chunking"
        ]
        
        has_meaningful_changes = any(key in changes for key in meaningful_changes)
        
        # Apply if there are meaningful changes and expected improvements
        expected_improvements = optimization_report.get("expected_improvements", {}).get("expected_improvements", [])
        
        return has_meaningful_changes and len(expected_improvements) > 0
    
    def _calculate_chunking_metrics(self, chunks: List[TextChunk], processing_time_ms: float) -> ChunkingMetrics:
        """
        Calculate comprehensive metrics for chunking results.
        
        Args:
            chunks: List of text chunks
            processing_time_ms: Processing time in milliseconds
            
        Returns:
            ChunkingMetrics object
        """
        if not chunks:
            return ChunkingMetrics()
        
        # Basic size metrics
        chunk_sizes = [len(chunk.content) for chunk in chunks]
        coherence_scores = [chunk.metadata.get("coherence_score", 0.5) for chunk in chunks]
        
        # Calculate metrics
        avg_chunk_size = sum(chunk_sizes) / len(chunk_sizes)
        size_variance = sum((size - avg_chunk_size) ** 2 for size in chunk_sizes) / len(chunk_sizes)
        size_consistency = max(0, 1 - (size_variance / (self.chunk_size ** 2)))
        
        avg_coherence = sum(coherence_scores) / len(coherence_scores)
        
        # Structure preservation metrics
        has_headers_count = sum(1 for chunk in chunks if chunk.metadata.get("has_headers", False))
        structure_preservation = has_headers_count / len(chunks)
        
        # Semantic boundary respect (based on chunk types)
        semantic_chunks = sum(1 for chunk in chunks 
                            if chunk.metadata.get("semantic_type", "").endswith(("section", "paragraph_group")))
        semantic_boundary_respect = semantic_chunks / len(chunks)
        
        # Chunk type distribution
        chunk_type_distribution = {}
        for chunk in chunks:
            chunk_type = chunk.metadata.get("semantic_type", "unknown")
            chunk_type_distribution[chunk_type] = chunk_type_distribution.get(chunk_type, 0) + 1
        
        # Overall quality score
        quality_score = (
            size_consistency * 0.25 +
            avg_coherence * 0.35 +
            structure_preservation * 0.20 +
            semantic_boundary_respect * 0.20
        )
        
        # Performance metrics
        chunks_per_second = len(chunks) / (processing_time_ms / 1000) if processing_time_ms > 0 else 0
        
        return ChunkingMetrics(
            total_chunks=len(chunks),
            avg_chunk_size=avg_chunk_size,
            min_chunk_size=min(chunk_sizes),
            max_chunk_size=max(chunk_sizes),
            size_variance=size_variance,
            size_consistency=size_consistency,
            avg_coherence_score=avg_coherence,
            min_coherence_score=min(coherence_scores),
            max_coherence_score=max(coherence_scores),
            structure_preservation=structure_preservation,
            semantic_boundary_respect=semantic_boundary_respect,
            processing_time_ms=processing_time_ms,
            chunks_per_second=chunks_per_second,
            chunk_type_distribution=chunk_type_distribution,
            quality_score=quality_score
        )
    
    def get_performance_insights(self) -> Dict[str, Any]:
        """Get performance insights from the optimizer."""
        if hasattr(self, 'optimizer'):
            return self.optimizer.get_performance_insights()
        else:
            return {"message": "Optimizer not available"}
    
    def chunk_text(
        self,
        text: str,
        document_metadata: Optional[Dict[str, Any]] = None,
        document_format: Optional[str] = None
    ) -> List[TextChunk]:
        """
        Split text into semantically coherent chunks with structure preservation.
        
        Args:
            text: Text to chunk
            document_metadata: Optional metadata to include in chunks
            document_format: Document format hint (e.g., 'markdown', 'plain', 'code')
            
        Returns:
            List of TextChunk objects with semantic boundaries
        """
        if not text or not text.strip():
            return []
        
        # Clean and normalize text
        text = self._normalize_text(text)
        
        # Detect document format if not provided
        if document_format is None:
            document_format = self._detect_document_format(text)
        
        # Apply format-specific chunking strategy
        if self.format_specific_chunking:
            chunks = self._chunk_by_format(text, document_format)
        else:
            chunks = self._chunk_semantic_hierarchical(text)
        
        # Create TextChunk objects with enhanced metadata
        text_chunks = []
        current_pos = 0
        
        for i, chunk_info in enumerate(chunks):
            chunk_content = chunk_info["content"]
            chunk_metadata_extra = chunk_info.get("metadata", {})
            
            # Find the actual position of this chunk in the original text
            chunk_start = text.find(chunk_content, current_pos)
            if chunk_start == -1:
                chunk_start = current_pos
            
            chunk_end = chunk_start + len(chunk_content)
            
            # Create comprehensive metadata for this chunk
            chunk_metadata = {
                "chunk_size": len(chunk_content),
                "word_count": len(chunk_content.split()),
                "sentence_count": self._count_sentences(chunk_content),
                "paragraph_count": self._count_paragraphs(chunk_content),
                "document_format": document_format,
                "semantic_type": chunk_metadata_extra.get("semantic_type", "content"),
                "structure_level": chunk_metadata_extra.get("structure_level", 0),
                "has_headers": chunk_metadata_extra.get("has_headers", False),
                "coherence_score": chunk_metadata_extra.get("coherence_score", 1.0),
                **(document_metadata or {})
            }
            
            text_chunk = TextChunk(
                content=chunk_content,
                chunk_index=i,
                start_char=chunk_start,
                end_char=chunk_end,
                metadata=chunk_metadata
            )
            
            text_chunks.append(text_chunk)
            current_pos = chunk_start + len(chunk_content) - self.chunk_overlap
        
        return text_chunks
    
    def _detect_document_format(self, text: str) -> str:
        """
        Detect document format based on content patterns.
        
        Args:
            text: Text to analyze
            
        Returns:
            Detected format string
        """
        # Check for markdown patterns
        markdown_patterns = [
            r'^#{1,6}\s+',  # Headers
            r'\*\*.*?\*\*',  # Bold
            r'\*.*?\*',  # Italic
            r'```.*?```',  # Code blocks
            r'^\s*[-*+]\s+',  # Lists
        ]
        
        markdown_score = sum(1 for pattern in markdown_patterns 
                           if re.search(pattern, text, re.MULTILINE))
        
        # Check for code patterns
        code_patterns = [
            r'^\s*(def|class|function|var|let|const)\s+',  # Function/class definitions
            r'[{}();]',  # Code punctuation
            r'^\s*import\s+',  # Import statements
            r'^\s*#include\s+',  # C/C++ includes
        ]
        
        code_score = sum(1 for pattern in code_patterns 
                        if re.search(pattern, text, re.MULTILINE))
        
        # Check for structured document patterns
        structured_patterns = [
            r'^[A-Z][A-Z\s]+:?\s*$',  # Section headers
            r'^\d+\.\s+[A-Z]',  # Numbered sections
            r'^Chapter\s+\d+',  # Chapters
        ]
        
        structured_score = sum(1 for pattern in structured_patterns 
                             if re.search(pattern, text, re.MULTILINE))
        
        # Determine format based on scores
        if markdown_score >= 2:
            return "markdown"
        elif code_score >= 3:
            return "code"
        elif structured_score >= 2:
            return "structured"
        else:
            return "plain"
    
    def _chunk_by_format(self, text: str, document_format: str) -> List[Dict[str, Any]]:
        """
        Apply format-specific chunking strategy.
        
        Args:
            text: Text to chunk
            document_format: Document format
            
        Returns:
            List of chunk dictionaries with content and metadata
        """
        if document_format == "markdown":
            return self._chunk_markdown(text)
        elif document_format == "code":
            return self._chunk_code(text)
        elif document_format == "structured":
            return self._chunk_structured_document(text)
        else:
            return self._chunk_semantic_hierarchical(text)
    
    def _chunk_markdown(self, text: str) -> List[Dict[str, Any]]:
        """
        Chunk markdown text respecting headers and structure.
        
        Args:
            text: Markdown text to chunk
            
        Returns:
            List of chunk dictionaries
        """
        chunks = []
        lines = text.split('\n')
        current_chunk = []
        current_header_level = 0
        current_size = 0
        
        for line in lines:
            line_with_newline = line + '\n'
            line_size = len(line_with_newline)
            
            # Check if this is a header
            header_match = re.match(r'^(#{1,6})\s+(.+)$', line)
            
            if header_match:
                header_level = len(header_match.group(1))
                
                # If we have content and this is a major header break, finalize chunk
                if (current_chunk and 
                    (header_level <= current_header_level or 
                     current_size + line_size > self.max_chunk_size)):
                    
                    chunk_content = ''.join(current_chunk).strip()
                    if chunk_content:
                        chunks.append({
                            "content": chunk_content,
                            "metadata": {
                                "semantic_type": "section",
                                "structure_level": current_header_level,
                                "has_headers": True,
                                "coherence_score": 0.9
                            }
                        })
                    
                    current_chunk = []
                    current_size = 0
                
                current_header_level = header_level
            
            # Add line to current chunk
            current_chunk.append(line_with_newline)
            current_size += line_size
            
            # Check if chunk is getting too large
            if current_size > self.max_chunk_size:
                # Try to find a good break point
                break_point = self._find_semantic_break_point(current_chunk)
                if break_point > 0:
                    chunk_content = ''.join(current_chunk[:break_point]).strip()
                    if chunk_content:
                        chunks.append({
                            "content": chunk_content,
                            "metadata": {
                                "semantic_type": "partial_section",
                                "structure_level": current_header_level,
                                "has_headers": current_header_level > 0,
                                "coherence_score": 0.7
                            }
                        })
                    
                    current_chunk = current_chunk[break_point - self._calculate_overlap_lines(current_chunk[:break_point]):]
                    current_size = sum(len(line) for line in current_chunk)
        
        # Add final chunk
        if current_chunk:
            chunk_content = ''.join(current_chunk).strip()
            if chunk_content:
                chunks.append({
                    "content": chunk_content,
                    "metadata": {
                        "semantic_type": "section",
                        "structure_level": current_header_level,
                        "has_headers": current_header_level > 0,
                        "coherence_score": 0.9
                    }
                })
        
        return chunks
    
    def _chunk_code(self, text: str) -> List[Dict[str, Any]]:
        """
        Chunk code text respecting function and class boundaries.
        
        Args:
            text: Code text to chunk
            
        Returns:
            List of chunk dictionaries
        """
        chunks = []
        lines = text.split('\n')
        current_chunk = []
        current_size = 0
        indent_level = 0
        in_function = False
        
        for i, line in enumerate(lines):
            line_with_newline = line + '\n'
            line_size = len(line_with_newline)
            
            # Detect function/class definitions
            is_definition = re.match(r'^\s*(def|class|function|var|let|const)\s+', line)
            current_indent = len(line) - len(line.lstrip())
            
            # If we're starting a new function/class and chunk is getting large
            if (is_definition and current_chunk and 
                current_size + line_size > self.chunk_size):
                
                chunk_content = ''.join(current_chunk).strip()
                if chunk_content:
                    chunks.append({
                        "content": chunk_content,
                        "metadata": {
                            "semantic_type": "code_block",
                            "structure_level": indent_level,
                            "has_headers": in_function,
                            "coherence_score": 0.8
                        }
                    })
                
                current_chunk = []
                current_size = 0
            
            # Track function/class context
            if is_definition:
                in_function = True
                indent_level = current_indent
            
            current_chunk.append(line_with_newline)
            current_size += line_size
            
            # Check if chunk is too large
            if current_size > self.max_chunk_size:
                # Find a good break point (end of function, empty line, etc.)
                break_point = self._find_code_break_point(current_chunk)
                if break_point > 0:
                    chunk_content = ''.join(current_chunk[:break_point]).strip()
                    if chunk_content:
                        chunks.append({
                            "content": chunk_content,
                            "metadata": {
                                "semantic_type": "code_block",
                                "structure_level": indent_level,
                                "has_headers": in_function,
                                "coherence_score": 0.7
                            }
                        })
                    
                    overlap_lines = self._calculate_overlap_lines(current_chunk[:break_point])
                    current_chunk = current_chunk[break_point - overlap_lines:]
                    current_size = sum(len(line) for line in current_chunk)
        
        # Add final chunk
        if current_chunk:
            chunk_content = ''.join(current_chunk).strip()
            if chunk_content:
                chunks.append({
                    "content": chunk_content,
                    "metadata": {
                        "semantic_type": "code_block",
                        "structure_level": indent_level,
                        "has_headers": in_function,
                        "coherence_score": 0.8
                    }
                })
        
        return chunks
    
    def _chunk_structured_document(self, text: str) -> List[Dict[str, Any]]:
        """
        Chunk structured documents respecting sections and hierarchies.
        
        Args:
            text: Structured document text to chunk
            
        Returns:
            List of chunk dictionaries
        """
        chunks = []
        lines = text.split('\n')
        current_chunk = []
        current_size = 0
        current_section_level = 0
        
        for line in lines:
            line_with_newline = line + '\n'
            line_size = len(line_with_newline)
            
            # Check for section headers
            section_level = self._detect_section_level(line)
            
            if section_level > 0:
                # If we have content and this is a major section break
                if (current_chunk and 
                    (section_level <= current_section_level or 
                     current_size + line_size > self.max_chunk_size)):
                    
                    chunk_content = ''.join(current_chunk).strip()
                    if chunk_content:
                        chunks.append({
                            "content": chunk_content,
                            "metadata": {
                                "semantic_type": "document_section",
                                "structure_level": current_section_level,
                                "has_headers": True,
                                "coherence_score": 0.9
                            }
                        })
                    
                    current_chunk = []
                    current_size = 0
                
                current_section_level = section_level
            
            current_chunk.append(line_with_newline)
            current_size += line_size
            
            # Check size limits
            if current_size > self.max_chunk_size:
                break_point = self._find_semantic_break_point(current_chunk)
                if break_point > 0:
                    chunk_content = ''.join(current_chunk[:break_point]).strip()
                    if chunk_content:
                        chunks.append({
                            "content": chunk_content,
                            "metadata": {
                                "semantic_type": "partial_section",
                                "structure_level": current_section_level,
                                "has_headers": current_section_level > 0,
                                "coherence_score": 0.7
                            }
                        })
                    
                    overlap_lines = self._calculate_overlap_lines(current_chunk[:break_point])
                    current_chunk = current_chunk[break_point - overlap_lines:]
                    current_size = sum(len(line) for line in current_chunk)
        
        # Add final chunk
        if current_chunk:
            chunk_content = ''.join(current_chunk).strip()
            if chunk_content:
                chunks.append({
                    "content": chunk_content,
                    "metadata": {
                        "semantic_type": "document_section",
                        "structure_level": current_section_level,
                        "has_headers": current_section_level > 0,
                        "coherence_score": 0.9
                    }
                })
        
        return chunks
    
    def _chunk_semantic_hierarchical(self, text: str) -> List[Dict[str, Any]]:
        """
        Chunk text using semantic hierarchy (paragraphs, sentences, words).
        
        Args:
            text: Text to chunk
            
        Returns:
            List of chunk dictionaries
        """
        chunks = []
        
        # First, try to split by paragraphs
        paragraphs = re.split(r'\n\s*\n', text)
        current_chunk = []
        current_size = 0
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            
            paragraph_size = len(paragraph)
            
            # If adding this paragraph would exceed size limits
            if current_chunk and current_size + paragraph_size > self.chunk_size:
                # Finalize current chunk
                chunk_content = '\n\n'.join(current_chunk)
                if chunk_content:
                    chunks.append({
                        "content": chunk_content,
                        "metadata": {
                            "semantic_type": "paragraph_group",
                            "structure_level": 1,
                            "has_headers": False,
                            "coherence_score": 0.8
                        }
                    })
                
                current_chunk = []
                current_size = 0
            
            # If single paragraph is too large, split by sentences
            if paragraph_size > self.max_chunk_size:
                sentence_chunks = self._split_paragraph_by_sentences(paragraph)
                chunks.extend(sentence_chunks)
            else:
                current_chunk.append(paragraph)
                current_size += paragraph_size + 2  # +2 for \n\n
        
        # Add final chunk
        if current_chunk:
            chunk_content = '\n\n'.join(current_chunk)
            if chunk_content:
                chunks.append({
                    "content": chunk_content,
                    "metadata": {
                        "semantic_type": "paragraph_group",
                        "structure_level": 1,
                        "has_headers": False,
                        "coherence_score": 0.8
                    }
                })
        
        return chunks
    
    def _split_paragraph_by_sentences(self, paragraph: str) -> List[Dict[str, Any]]:
        """
        Split a large paragraph by sentences while maintaining coherence.
        
        Args:
            paragraph: Paragraph to split
            
        Returns:
            List of chunk dictionaries
        """
        chunks = []
        
        # Split by sentences using multiple patterns
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', paragraph)
        current_chunk = []
        current_size = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            sentence_size = len(sentence)
            
            # If adding this sentence would exceed limits
            if current_chunk and current_size + sentence_size > self.chunk_size:
                chunk_content = ' '.join(current_chunk)
                if chunk_content:
                    chunks.append({
                        "content": chunk_content,
                        "metadata": {
                            "semantic_type": "sentence_group",
                            "structure_level": 2,
                            "has_headers": False,
                            "coherence_score": 0.6
                        }
                    })
                
                current_chunk = []
                current_size = 0
            
            # If single sentence is still too large, split by words
            if sentence_size > self.max_chunk_size:
                word_chunks = self._split_sentence_by_words(sentence)
                chunks.extend(word_chunks)
            else:
                current_chunk.append(sentence)
                current_size += sentence_size + 1  # +1 for space
        
        # Add final chunk
        if current_chunk:
            chunk_content = ' '.join(current_chunk)
            if chunk_content:
                chunks.append({
                    "content": chunk_content,
                    "metadata": {
                        "semantic_type": "sentence_group",
                        "structure_level": 2,
                        "has_headers": False,
                        "coherence_score": 0.6
                    }
                })
        
        return chunks
    
    def _split_sentence_by_words(self, sentence: str) -> List[Dict[str, Any]]:
        """
        Split a very long sentence by words as a last resort.
        
        Args:
            sentence: Sentence to split
            
        Returns:
            List of chunk dictionaries
        """
        chunks = []
        words = sentence.split()
        current_chunk = []
        current_size = 0
        
        for word in words:
            word_size = len(word)
            
            if current_chunk and current_size + word_size > self.chunk_size:
                chunk_content = ' '.join(current_chunk)
                if chunk_content:
                    chunks.append({
                        "content": chunk_content,
                        "metadata": {
                            "semantic_type": "word_group",
                            "structure_level": 3,
                            "has_headers": False,
                            "coherence_score": 0.3
                        }
                    })
                
                current_chunk = []
                current_size = 0
            
            current_chunk.append(word)
            current_size += word_size + 1  # +1 for space
        
        # Add final chunk
        if current_chunk:
            chunk_content = ' '.join(current_chunk)
            if chunk_content:
                chunks.append({
                    "content": chunk_content,
                    "metadata": {
                        "semantic_type": "word_group",
                        "structure_level": 3,
                        "has_headers": False,
                        "coherence_score": 0.3
                    }
                })
        
        return chunks
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text by cleaning up whitespace and formatting."""
        # Remove excessive whitespace
        text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)  # Multiple newlines to double
        text = re.sub(r'[ \t]+', ' ', text)  # Multiple spaces/tabs to single space
        text = re.sub(r'\n ', '\n', text)  # Remove spaces after newlines
        text = re.sub(r' \n', '\n', text)  # Remove spaces before newlines
        
        return text.strip()
    
    def _detect_section_level(self, line: str) -> int:
        """
        Detect the hierarchical level of a section header.
        
        Args:
            line: Line to analyze
            
        Returns:
            Section level (0 if not a header, 1+ for header levels)
        """
        line = line.strip()
        
        # Markdown headers
        markdown_match = re.match(r'^(#{1,6})\s+', line)
        if markdown_match:
            return len(markdown_match.group(1))
        
        # Numbered sections
        if re.match(r'^\d+\.\s+[A-Z]', line):
            return 1
        
        # Roman numeral sections
        if re.match(r'^[IVX]+\.\s+[A-Z]', line):
            return 1
        
        # ALL CAPS headers
        if re.match(r'^[A-Z][A-Z\s]+:?\s*$', line) and len(line) < 100:
            return 2
        
        # Chapter/Section/Part headers
        if re.match(r'^(Chapter|Section|Part)\s+[\dIVX]+', line, re.IGNORECASE):
            return 1
        
        return 0
    
    def _find_semantic_break_point(self, lines: List[str]) -> int:
        """
        Find the best semantic break point in a list of lines.
        
        Args:
            lines: List of lines to analyze
            
        Returns:
            Index of the best break point
        """
        if len(lines) <= 1:
            return len(lines)
        
        best_break = len(lines) // 2  # Default to middle
        best_score = 0
        
        # Look for good break points in the latter half
        start_search = max(1, len(lines) // 2)
        
        for i in range(start_search, len(lines)):
            line = lines[i].strip()
            score = 0
            
            # Empty line is a great break point
            if not line:
                score += 10
            
            # Paragraph break
            if i > 0 and not lines[i-1].strip():
                score += 8
            
            # Sentence ending
            if line and line[-1] in '.!?':
                score += 5
            
            # Section header
            if self._detect_section_level(line) > 0:
                score += 15
            
            # List item
            if re.match(r'^\s*[-*•]\s+', line):
                score += 3
            
            # Numbered item
            if re.match(r'^\s*\d+\.\s+', line):
                score += 3
            
            if score > best_score:
                best_score = score
                best_break = i
        
        return best_break
    
    def _find_code_break_point(self, lines: List[str]) -> int:
        """
        Find the best break point in code text.
        
        Args:
            lines: List of code lines
            
        Returns:
            Index of the best break point
        """
        if len(lines) <= 1:
            return len(lines)
        
        best_break = len(lines) // 2
        best_score = 0
        
        start_search = max(1, len(lines) // 2)
        
        for i in range(start_search, len(lines)):
            line = lines[i].strip()
            score = 0
            
            # Empty line
            if not line:
                score += 8
            
            # End of function/class (closing brace or dedent)
            if line in ['}', '};'] or (i > 0 and len(line) - len(line.lstrip()) < len(lines[i-1]) - len(lines[i-1].lstrip())):
                score += 12
            
            # Comment line
            if line.startswith('#') or line.startswith('//') or line.startswith('/*'):
                score += 5
            
            # Function/class definition
            if re.match(r'^\s*(def|class|function|var|let|const)\s+', line):
                score += 10
            
            # Import statement
            if re.match(r'^\s*(import|from|#include)\s+', line):
                score += 6
            
            if score > best_score:
                best_score = score
                best_break = i
        
        return best_break
    
    def _calculate_overlap_lines(self, lines: List[str]) -> int:
        """
        Calculate how many lines should be included in overlap.
        
        Args:
            lines: List of lines in the chunk
            
        Returns:
            Number of lines to overlap
        """
        total_chars = sum(len(line) for line in lines)
        if total_chars == 0:
            return 0
        
        target_overlap_chars = min(self.chunk_overlap, total_chars // 2)
        overlap_lines = 0
        overlap_chars = 0
        
        # Count from the end
        for i in range(len(lines) - 1, -1, -1):
            if overlap_chars + len(lines[i]) <= target_overlap_chars:
                overlap_chars += len(lines[i])
                overlap_lines += 1
            else:
                break
        
        return min(overlap_lines, len(lines) // 2)
    
    def _count_sentences(self, text: str) -> int:
        """Count the number of sentences in text."""
        sentences = re.split(r'[.!?]+\s+', text.strip())
        return len([s for s in sentences if s.strip()])
    
    def _count_paragraphs(self, text: str) -> int:
        """Count the number of paragraphs in text."""
        paragraphs = re.split(r'\n\s*\n', text.strip())
        return len([p for p in paragraphs if p.strip()])
    
# Backward compatibility: Create TextChunker as an alias to SemanticTextChunker
class TextChunker(SemanticTextChunker):
    """
    Backward-compatible text chunker that uses semantic-aware chunking.
    
    This class maintains the same interface as the original TextChunker
    while providing enhanced semantic-aware chunking capabilities.
    """
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separator: str = "\n\n",
        secondary_separators: Optional[List[str]] = None
    ):
        """
        Initialize text chunker with backward compatibility.
        
        Args:
            chunk_size: Target size for each chunk in characters
            chunk_overlap: Number of characters to overlap between chunks
            separator: Primary separator for splitting text (legacy parameter)
            secondary_separators: Additional separators (legacy parameter)
        """
        # Validate legacy parameters first (for backward compatibility)
        if chunk_overlap >= chunk_size:
            raise ValueError("Chunk overlap must be less than chunk size")
        if chunk_size <= 0:
            raise ValueError("Chunk size must be positive")
        if chunk_overlap < 0:
            raise ValueError("Chunk overlap must be non-negative")
        
        # Initialize with semantic chunking enabled by default
        super().__init__(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            respect_structure=True,
            semantic_coherence_priority=True,
            format_specific_chunking=True
        )
        
        # Store legacy parameters for compatibility
        self.separator = separator
        self.secondary_separators = secondary_separators or ["\n", ". ", "! ", "? ", " "]
    
    def chunk_text(
        self,
        text: str,
        document_metadata: Optional[Dict[str, Any]] = None,
        document_format: Optional[str] = None
    ) -> List[TextChunk]:
        """
        Backward-compatible chunk_text method.
        
        Args:
            text: Text to chunk
            document_metadata: Optional metadata to include in chunks
            document_format: Document format hint (ignored for backward compatibility)
            
        Returns:
            List of TextChunk objects
        """
        # Call the semantic chunking method
        return super().chunk_text(text, document_metadata, document_format)
    
    # Legacy methods for backward compatibility
    def _normalize_text(self, text: str) -> str:
        """Legacy method - delegates to parent."""
        return super()._normalize_text(text)
    
    def _split_text_hierarchical(self, text: str) -> List[str]:
        """
        Legacy method that now uses semantic chunking.
        
        Args:
            text: Text to split
            
        Returns:
            List of chunk strings
        """
        # Use semantic chunking and extract content
        chunks = self._chunk_semantic_hierarchical(text)
        return [chunk["content"] for chunk in chunks]
    
    def _split_with_overlap(self, text: str, separator: str) -> List[str]:
        """Legacy method for backward compatibility."""
        if separator not in text:
            return [text]
        
        # Use semantic chunking for better results
        chunks = self._chunk_semantic_hierarchical(text)
        return [chunk["content"] for chunk in chunks]
    
    def _split_large_chunk(self, chunk: str) -> List[str]:
        """Legacy method for backward compatibility."""
        # Use semantic sentence splitting
        sentence_chunks = self._split_paragraph_by_sentences(chunk)
        return [chunk_info["content"] for chunk_info in sentence_chunks]
    
    def _split_by_character_count(self, text: str) -> List[str]:
        """Legacy method for backward compatibility."""
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            # Try to find a good breaking point near the end
            if end < len(text):
                # Look for whitespace within the last 10% of the chunk
                search_start = max(start + int(self.chunk_size * 0.9), start + 1)
                space_pos = text.rfind(' ', search_start, end)
                
                if space_pos > start:
                    end = space_pos
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # Move start position with overlap
            start = max(end - self.chunk_overlap, start + 1)
        
        return chunks
    
    def _get_overlap_text(self, text: str) -> str:
        """Legacy method for backward compatibility."""
        if len(text) <= self.chunk_overlap:
            return text
        
        overlap_start = len(text) - self.chunk_overlap
        
        # Try to find a good starting point for overlap (word boundary)
        space_pos = text.find(' ', overlap_start)
        if space_pos != -1 and space_pos < len(text) - self.chunk_overlap // 2:
            overlap_start = space_pos + 1
        
        return text[overlap_start:]


class DocumentProcessor:
    """High-level document processing pipeline with OCR support."""
    
    def __init__(
        self,
        chunking_config: Optional[ChunkingConfig] = None,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        max_file_size: int = 50 * 1024 * 1024,
        enable_ocr: bool = True,
        ocr_language: str = 'eng',
        enable_semantic_chunking: bool = True,
        chunking_strategy: str = 'adaptive',  # 'adaptive', 'semantic', 'legacy'
        auto_optimize: bool = True
    ):
        """
        Initialize document processor with enhanced chunking capabilities.
        
        Args:
            chunking_config: ChunkingConfig object (preferred method)
            chunk_size: Target chunk size in characters (legacy)
            chunk_overlap: Overlap between chunks in characters (legacy)
            max_file_size: Maximum allowed file size in bytes
            enable_ocr: Whether to enable OCR for scanned PDFs and images
            ocr_language: Language code for OCR (e.g., 'eng', 'spa', 'fra')
            enable_semantic_chunking: Whether to use semantic-aware chunking (legacy)
            chunking_strategy: Chunking strategy (legacy)
            auto_optimize: Whether to automatically optimize chunking for each document
        """
        self.extractor = DocumentExtractor(enable_ocr=enable_ocr, ocr_language=ocr_language)
        
        # Initialize chunking configuration
        if chunking_config is not None:
            self.chunking_config = chunking_config
        else:
            # Create config from legacy parameters
            strategy_map = {
                'adaptive': ChunkingStrategy.ADAPTIVE,
                'semantic': ChunkingStrategy.SEMANTIC,
                'legacy': ChunkingStrategy.LEGACY
            }
            
            self.chunking_config = ChunkingConfig(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                strategy=strategy_map.get(chunking_strategy, ChunkingStrategy.ADAPTIVE),
                respect_structure=enable_semantic_chunking,
                semantic_coherence_priority=enable_semantic_chunking,
                format_specific_chunking=(chunking_strategy == 'adaptive')
            )
        
        # Initialize chunker based on strategy
        if self.chunking_config.strategy == ChunkingStrategy.LEGACY:
            self.chunker = TextChunker(
                chunk_size=self.chunking_config.chunk_size,
                chunk_overlap=self.chunking_config.chunk_overlap
            )
        else:
            self.chunker = SemanticTextChunker(config=self.chunking_config)
        
        self.max_file_size = max_file_size
        self.auto_optimize = auto_optimize
        
        # Legacy properties for backward compatibility
        self.enable_semantic_chunking = self.chunking_config.semantic_coherence_priority
        self.chunking_strategy = self.chunking_config.strategy.value
    
    def process_document(
        self,
        file_content: bytes,
        filename: str,
        document_id: str,
        additional_metadata: Optional[Dict[str, Any]] = None,
        optimize_chunking: Optional[bool] = None
    ) -> Tuple[List[TextChunk], Dict[str, Any]]:
        """
        Process a document through the complete pipeline with optimization.
        
        Args:
            file_content: File content as bytes
            filename: Original filename
            document_id: Unique document identifier
            additional_metadata: Additional metadata to include
            optimize_chunking: Whether to optimize chunking (overrides auto_optimize)
            
        Returns:
            Tuple of (chunks, enhanced_document_metadata)
        """
        file_path = Path(filename)
        
        # Step 1: Validate file
        is_valid, mime_type, error_msg = self.extractor.validate_file(file_path, file_content)
        if not is_valid:
            raise ValueError(f"File validation failed: {error_msg}")
        
        # Step 2: Extract text
        extracted_text, extraction_metadata = self.extractor.extract_text(
            file_content, mime_type, filename
        )
        
        if not extracted_text.strip():
            raise ValueError("No text content found in document")
        
        # Step 3: Create document metadata
        document_metadata = {
            "document_id": document_id,
            "filename": filename,
            "mime_type": mime_type,
            "file_size": len(file_content),
            "text_length": len(extracted_text),
            "extraction_metadata": extraction_metadata,
            **(additional_metadata or {})
        }
        
        # Step 4: Chunk text with optimization
        should_optimize = optimize_chunking if optimize_chunking is not None else self.auto_optimize
        
        if hasattr(self.chunker, 'chunk_with_adaptive_optimization') and should_optimize:
            # Use adaptive optimization
            document_format = self._detect_document_format_from_file(filename, extracted_text)
            chunks, chunking_metrics, optimization_report = self.chunker.chunk_with_adaptive_optimization(
                extracted_text, document_metadata, document_format, auto_optimize=True
            )
            
            # Add optimization results to metadata
            document_metadata.update({
                "chunking_metrics": asdict(chunking_metrics),
                "optimization_report": optimization_report,
                "chunking_config": self.chunker.config.to_dict()
            })
            
        elif hasattr(self.chunker, '_calculate_chunking_metrics'):
            # Use semantic chunking without optimization
            document_format = self._detect_document_format_from_file(filename, extracted_text)
            chunks = self.chunker.chunk_text(extracted_text, document_metadata, document_format)
            
            # Calculate basic metrics
            import time
            start_time = time.time()
            processing_time = (time.time() - start_time) * 1000
            chunking_metrics = self.chunker._calculate_chunking_metrics(chunks, processing_time)
            
            document_metadata.update({
                "chunking_metrics": asdict(chunking_metrics),
                "chunking_config": self.chunker.config.to_dict()
            })
        else:
            # Use legacy chunking
            chunks = self.chunker.chunk_text(extracted_text, document_metadata)
            
            # Add basic metrics for legacy chunking
            document_metadata.update({
                "chunking_config": {
                    "chunk_size": self.chunker.chunk_size,
                    "chunk_overlap": self.chunker.chunk_overlap,
                    "strategy": "legacy"
                }
            })
        
        # Step 5: Add chunk-specific metadata
        for chunk in chunks:
            chunk.metadata.update({
                "total_chunks": len(chunks),
                "chunk_ratio": (chunk.chunk_index + 1) / len(chunks)
            })
        
        logger.info(f"Processed document {filename}: {len(chunks)} chunks created")
        
        return chunks, document_metadata
    
    def process_document_with_custom_config(
        self,
        file_content: bytes,
        filename: str,
        document_id: str,
        chunking_config: ChunkingConfig,
        additional_metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[TextChunk], Dict[str, Any]]:
        """
        Process a document with a custom chunking configuration.
        
        Args:
            file_content: File content as bytes
            filename: Original filename
            document_id: Unique document identifier
            chunking_config: Custom chunking configuration
            additional_metadata: Additional metadata to include
            
        Returns:
            Tuple of (chunks, document_metadata)
        """
        # Temporarily use custom config
        original_config = self.chunking_config
        original_chunker = self.chunker
        
        try:
            # Apply custom configuration
            self.chunking_config = chunking_config
            if chunking_config.strategy == ChunkingStrategy.LEGACY:
                self.chunker = TextChunker(
                    chunk_size=chunking_config.chunk_size,
                    chunk_overlap=chunking_config.chunk_overlap
                )
            else:
                self.chunker = SemanticTextChunker(config=chunking_config)
            
            # Process with custom config
            return self.process_document(file_content, filename, document_id, additional_metadata, optimize_chunking=False)
            
        finally:
            # Restore original configuration
            self.chunking_config = original_config
            self.chunker = original_chunker
    
    def _detect_document_format_from_file(self, filename: str, content: str) -> str:
        """
        Detect document format from filename and content.
        
        Args:
            filename: Original filename
            content: Document content
            
        Returns:
            Detected format string
        """
        file_ext = Path(filename).suffix.lower()
        
        # Format detection based on file extension
        if file_ext == '.md':
            return 'markdown'
        elif file_ext in ['.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', '.css', '.html', '.xml', '.json']:
            return 'code'
        elif file_ext in ['.txt', '.rtf']:
            # Analyze content for structured document patterns
            return self.chunker._detect_document_format(content) if hasattr(self.chunker, '_detect_document_format') else 'plain'
        else:
            return 'plain'
    
    def validate_chunking_configuration(self) -> Dict[str, Any]:
        """
        Validate the current chunking configuration and provide recommendations.
        
        Returns:
            Dictionary with validation results and recommendations
        """
        if hasattr(self.chunker, 'validate_chunking_parameters'):
            return self.chunker.validate_chunking_parameters()
        else:
            # Basic validation for legacy chunker
            return {
                "is_valid": True,
                "warnings": [],
                "recommendations": ["Consider upgrading to semantic chunking for better results"],
                "parameter_analysis": {
                    "chunk_size": self.chunker.chunk_size,
                    "chunk_overlap": self.chunker.chunk_overlap,
                    "chunking_type": "legacy"
                }
            }
    
    def get_chunking_quality_metrics(self, chunks: List[TextChunk]) -> Dict[str, Any]:
        """
        Calculate quality metrics for the chunking results.
        
        Args:
            chunks: List of text chunks
            
        Returns:
            Dictionary with quality metrics
        """
        if not chunks:
            return {"total_chunks": 0, "quality_score": 0.0}
        
        # Basic metrics
        chunk_sizes = [len(chunk.content) for chunk in chunks]
        coherence_scores = [chunk.metadata.get("coherence_score", 0.5) for chunk in chunks]
        
        # Size distribution analysis
        size_variance = sum((size - self.chunker.chunk_size) ** 2 for size in chunk_sizes) / len(chunk_sizes)
        size_consistency = max(0, 1 - (size_variance / (self.chunker.chunk_size ** 2)))
        
        # Semantic coherence analysis
        avg_coherence = sum(coherence_scores) / len(coherence_scores)
        
        # Structure preservation analysis
        has_headers_count = sum(1 for chunk in chunks if chunk.metadata.get("has_headers", False))
        structure_preservation = has_headers_count / len(chunks) if chunks else 0
        
        # Overall quality score
        quality_score = (size_consistency * 0.3 + avg_coherence * 0.5 + structure_preservation * 0.2)
        
        return {
            "total_chunks": len(chunks),
            "avg_chunk_size": sum(chunk_sizes) / len(chunk_sizes),
            "size_variance": size_variance,
            "size_consistency": size_consistency,
            "avg_coherence_score": avg_coherence,
            "structure_preservation": structure_preservation,
            "quality_score": quality_score,
            "chunk_types": self._analyze_chunk_types(chunks),
            "recommendations": self._generate_quality_recommendations(quality_score, size_consistency, avg_coherence)
        }
    
    def _analyze_chunk_types(self, chunks: List[TextChunk]) -> Dict[str, int]:
        """Analyze the distribution of chunk types."""
        type_counts = {}
        for chunk in chunks:
            chunk_type = chunk.metadata.get("semantic_type", "unknown")
            type_counts[chunk_type] = type_counts.get(chunk_type, 0) + 1
        return type_counts
    
    def _generate_quality_recommendations(self, quality_score: float, size_consistency: float, avg_coherence: float) -> List[str]:
        """Generate recommendations based on quality metrics."""
        recommendations = []
        
        if quality_score < 0.6:
            recommendations.append("Consider adjusting chunk size or enabling semantic chunking")
        
        if size_consistency < 0.7:
            recommendations.append("High size variance detected - consider enabling semantic coherence priority")
        
        if avg_coherence < 0.6:
            recommendations.append("Low coherence scores - enable structure-aware chunking for better results")
        
        if not recommendations:
            recommendations.append("Chunking quality is good - no immediate changes needed")
        
        return recommendations
    
    def update_chunking_config(self, new_config: ChunkingConfig):
        """
        Update the chunking configuration and reinitialize the chunker.
        
        Args:
            new_config: New chunking configuration
        """
        self.chunking_config = new_config
        
        # Reinitialize chunker with new config
        if new_config.strategy == ChunkingStrategy.LEGACY:
            self.chunker = TextChunker(
                chunk_size=new_config.chunk_size,
                chunk_overlap=new_config.chunk_overlap
            )
        else:
            self.chunker = SemanticTextChunker(config=new_config)
        
        # Update legacy properties
        self.enable_semantic_chunking = new_config.semantic_coherence_priority
        self.chunking_strategy = new_config.strategy.value
    
    def get_recommended_config_for_content_type(self, content_type: str, document_length: int = 10000) -> ChunkingConfig:
        """
        Get recommended configuration for a specific content type.
        
        Args:
            content_type: Type of content ('code', 'academic', 'technical', 'general')
            document_length: Estimated document length
            
        Returns:
            Recommended ChunkingConfig
        """
        return ChunkingConfig.get_optimized_config(
            content_type=content_type,
            document_length=document_length,
            target_use_case="rag"
        )
    
    def analyze_chunking_performance(self, chunks: List[TextChunk]) -> Dict[str, Any]:
        """
        Analyze the performance of chunking results and provide insights.
        
        Args:
            chunks: List of chunks to analyze
            
        Returns:
            Performance analysis report
        """
        if not chunks:
            return {"error": "No chunks to analyze"}
        
        # Get quality metrics
        quality_metrics = self.get_chunking_quality_metrics(chunks)
        
        # Get performance insights from chunker if available
        performance_insights = {}
        if hasattr(self.chunker, 'get_performance_insights'):
            performance_insights = self.chunker.get_performance_insights()
        
        # Generate recommendations
        recommendations = []
        
        if quality_metrics["quality_score"] < 0.6:
            recommendations.append("Consider optimizing chunking configuration for better quality")
        
        if quality_metrics["size_consistency"] < 0.7:
            recommendations.append("High size variance detected - enable semantic coherence priority")
        
        if quality_metrics["avg_coherence_score"] < 0.6:
            recommendations.append("Low coherence scores - consider format-specific chunking")
        
        return {
            "quality_metrics": quality_metrics,
            "performance_insights": performance_insights,
            "recommendations": recommendations,
            "current_config": self.chunking_config.to_dict(),
            "analysis_summary": {
                "total_chunks": len(chunks),
                "quality_rating": self._get_quality_rating(quality_metrics["quality_score"]),
                "primary_issues": self._identify_primary_issues(quality_metrics),
                "optimization_potential": self._assess_optimization_potential(quality_metrics)
            }
        }
    
    def _get_quality_rating(self, quality_score: float) -> str:
        """Get a human-readable quality rating."""
        if quality_score >= 0.8:
            return "Excellent"
        elif quality_score >= 0.7:
            return "Good"
        elif quality_score >= 0.6:
            return "Fair"
        elif quality_score >= 0.4:
            return "Poor"
        else:
            return "Very Poor"
    
    def _identify_primary_issues(self, quality_metrics: Dict[str, Any]) -> List[str]:
        """Identify primary issues with chunking quality."""
        issues = []
        
        if quality_metrics["size_consistency"] < 0.6:
            issues.append("Inconsistent chunk sizes")
        
        if quality_metrics["avg_coherence_score"] < 0.5:
            issues.append("Low semantic coherence")
        
        if quality_metrics["structure_preservation"] < 0.3:
            issues.append("Poor structure preservation")
        
        if not issues:
            issues.append("No major issues detected")
        
        return issues
    
    def _assess_optimization_potential(self, quality_metrics: Dict[str, Any]) -> str:
        """Assess the potential for optimization improvements."""
        quality_score = quality_metrics["quality_score"]
        
        if quality_score < 0.5:
            return "High - significant improvements possible"
        elif quality_score < 0.7:
            return "Medium - moderate improvements possible"
        elif quality_score < 0.85:
            return "Low - minor improvements possible"
        else:
            return "Minimal - already well optimized"
    
    def get_processing_stats(self, chunks: List[TextChunk]) -> Dict[str, Any]:
        """Get statistics about processed chunks."""
        if not chunks:
            return {"total_chunks": 0}
        
        chunk_sizes = [len(chunk.content) for chunk in chunks]
        word_counts = [len(chunk.content.split()) for chunk in chunks]
        
        return {
            "total_chunks": len(chunks),
            "avg_chunk_size": sum(chunk_sizes) / len(chunk_sizes),
            "min_chunk_size": min(chunk_sizes),
            "max_chunk_size": max(chunk_sizes),
            "avg_word_count": sum(word_counts) / len(word_counts),
            "total_words": sum(word_counts),
            "total_characters": sum(chunk_sizes)
        }