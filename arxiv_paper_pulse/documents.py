# arxiv_paper_pulse/documents.py
"""
Documents module for processing PDF documents with Gemini API.
Comprehensive input/output schemas for document processing.
"""

from typing import List, Optional, Union, Literal
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, field_validator
from enum import Enum
import os


# ============================================================================
# INPUT SCHEMAS
# ============================================================================

class DocumentSource(BaseModel):
    """Base schema for document input source"""
    model_config = ConfigDict(extra='forbid')


class DocumentFromURL(DocumentSource):
    """Document source from URL"""
    source_type: Literal["url"] = "url"
    url: str = Field(description="URL to fetch PDF from")
    display_name: Optional[str] = Field(None, description="Optional display name for the document")


class DocumentFromPath(DocumentSource):
    """Document source from local file path"""
    source_type: Literal["path"] = "path"
    file_path: Union[str, Path] = Field(description="Path to local PDF file")
    display_name: Optional[str] = Field(None, description="Optional display name for the document")

    @field_validator('file_path')
    @classmethod
    def validate_path_exists(cls, v):
        if isinstance(v, str):
            v = Path(v)
        if not v.exists():
            raise ValueError(f"File path does not exist: {v}")
        if not v.is_file():
            raise ValueError(f"Path is not a file: {v}")
        return v


class DocumentFromBytes(DocumentSource):
    """Document source from bytes (inline processing, <20MB)"""
    source_type: Literal["bytes"] = "bytes"
    data: bytes = Field(description="PDF file as bytes")
    display_name: Optional[str] = Field(None, description="Optional display name for the document")
    mime_type: str = Field(default="application/pdf", description="MIME type of the document")

    @field_validator('data')
    @classmethod
    def validate_size(cls, v):
        max_size = 20 * 1024 * 1024  # 20MB
        if len(v) > max_size:
            raise ValueError(f"Document size ({len(v)} bytes) exceeds inline limit ({max_size} bytes). Use File API instead.")
        return v


class DocumentFromBase64(DocumentSource):
    """Document source from base64 encoded string (inline processing, <20MB)"""
    source_type: Literal["base64"] = "base64"
    data: str = Field(description="PDF file as base64 encoded string")
    display_name: Optional[str] = Field(None, description="Optional display name for the document")
    mime_type: str = Field(default="application/pdf", description="MIME type of the document")

    @field_validator('data')
    @classmethod
    def validate_size(cls, v):
        import base64
        try:
            decoded = base64.b64decode(v)
            max_size = 20 * 1024 * 1024  # 20MB
            if len(decoded) > max_size:
                raise ValueError(f"Document size exceeds inline limit ({max_size} bytes). Use File API instead.")
        except Exception as e:
            raise ValueError(f"Invalid base64 data: {e}")
        return v


class DocumentInput(BaseModel):
    """Single document input - supports multiple source types"""
    model_config = ConfigDict(extra='forbid')

    source: Union[DocumentFromURL, DocumentFromPath, DocumentFromBytes, DocumentFromBase64] = Field(
        description="Document source (URL, path, bytes, or base64)"
    )


class MultipleDocumentsInput(BaseModel):
    """Multiple documents input for batch processing"""
    model_config = ConfigDict(extra='forbid')

    documents: List[DocumentInput] = Field(
        min_length=1,
        max_length=1000,  # Max pages limit
        description="List of documents to process together"
    )


# ============================================================================
# PROCESSING CONFIGURATION SCHEMAS
# ============================================================================

class ProcessingMethod(str, Enum):
    """Method for processing document"""
    AUTO = "auto"  # Automatically choose based on size
    INLINE = "inline"  # Inline processing (<20MB)
    FILE_API = "file_api"  # File API upload (>20MB, up to 50MB)


class OutputFormat(str, Enum):
    """Output format for processing results"""
    TEXT = "text"  # Plain text output
    STRUCTURED = "structured"  # Structured JSON output
    TRANSCRIPTION = "transcription"  # HTML transcription with layout preservation


class DocumentProcessingConfig(BaseModel):
    """Configuration for document processing"""
    model_config = ConfigDict(extra='forbid')

    method: ProcessingMethod = Field(
        default=ProcessingMethod.AUTO,
        description="Processing method (auto, inline, or file_api)"
    )
    output_format: OutputFormat = Field(
        default=OutputFormat.TEXT,
        description="Output format (text, structured, or transcription)"
    )
    model: Optional[str] = Field(
        default=None,
        description="Gemini model to use (defaults to config.DEFAULT_MODEL)"
    )
    prompt: Optional[str] = Field(
        default="Summarize this document",
        description="Prompt for document processing"
    )
    use_streaming: bool = Field(
        default=False,
        description="Whether to stream the response"
    )
    wait_for_processing: bool = Field(
        default=True,
        description="Wait for file processing completion (File API only)"
    )
    max_wait_time: int = Field(
        default=300,
        ge=0,
        description="Maximum wait time in seconds for file processing"
    )
    response_schema: Optional[type] = Field(
        default=None,
        description="Pydantic model for structured output (only used with STRUCTURED format)"
    )
    response_mime_type: Optional[Literal["application/json", "text/x.enum"]] = Field(
        default=None,
        description="MIME type for structured output"
    )


# ============================================================================
# OUTPUT SCHEMAS
# ============================================================================

class FileMetadata(BaseModel):
    """Metadata about uploaded/processed file"""
    model_config = ConfigDict(extra='forbid')

    name: str = Field(description="File name/identifier from Gemini API")
    uri: Optional[str] = Field(None, description="File URI for File API")
    state: str = Field(description="File processing state (PROCESSING, ACTIVE, FAILED)")
    size_bytes: Optional[int] = Field(None, description="File size in bytes")
    mime_type: str = Field(default="application/pdf", description="MIME type of the file")
    display_name: Optional[str] = Field(None, description="Display name for the file")


class DocumentProcessingResult(BaseModel):
    """Result from processing a single document"""
    model_config = ConfigDict(extra='forbid')

    success: bool = Field(description="Whether processing was successful")
    document_id: Optional[str] = Field(None, description="Identifier for the processed document")
    text: Optional[str] = Field(None, description="Text output (when output_format is TEXT)")
    structured_data: Optional[dict] = Field(None, description="Structured JSON output (when output_format is STRUCTURED)")
    transcription: Optional[str] = Field(None, description="HTML transcription (when output_format is TRANSCRIPTION)")
    metadata: Optional[FileMetadata] = Field(None, description="File metadata if using File API")
    error: Optional[str] = Field(None, description="Error message if processing failed")
    method_used: ProcessingMethod = Field(description="Processing method actually used")


class MultipleDocumentsResult(BaseModel):
    """Result from processing multiple documents"""
    model_config = ConfigDict(extra='forbid')

    results: List[DocumentProcessingResult] = Field(description="Results for each document")
    combined_text: Optional[str] = Field(None, description="Combined text output from all documents")
    combined_structured: Optional[dict] = Field(None, description="Combined structured output from all documents")
    success_count: int = Field(description="Number of successfully processed documents")
    failure_count: int = Field(description="Number of failed documents")


# ============================================================================
# ERROR SCHEMAS
# ============================================================================

class DocumentProcessingError(BaseModel):
    """Error information for document processing"""
    model_config = ConfigDict(extra='forbid')

    error_type: str = Field(description="Type of error (e.g., 'DownloadError', 'UploadError', 'ProcessingError')")
    message: str = Field(description="Error message")
    document_id: Optional[str] = Field(None, description="Document identifier if applicable")
    details: Optional[dict] = Field(None, description="Additional error details")


# ============================================================================
# DOCUMENT PROCESSOR CLASS
# ============================================================================

class DocumentProcessor:
    """
    Document processor using Gemini API.
    Supports multiple input sources, processing methods, and output formats.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        from google import genai
        from . import config

        self.api_key = api_key or config.GEMINI_API_KEY
        self.model = model or config.DEFAULT_MODEL
        self.client = genai.Client(api_key=self.api_key)

    def process(
        self,
        document: DocumentInput,
        config: Optional[DocumentProcessingConfig] = None
    ) -> DocumentProcessingResult:
        """
        Process a single document.

        Args:
            document: Document input with source information
            config: Processing configuration (optional)

        Returns:
            DocumentProcessingResult with text, structured data, or transcription
        """
        if config is None:
            config = DocumentProcessingConfig()

        try:
            # Determine processing method
            method = self._determine_method(document, config)

            # Process document based on method
            if method == ProcessingMethod.INLINE:
                result = self._process_inline(document, config)
            else:  # FILE_API
                result = self._process_file_api(document, config)

            result.method_used = method
            return result

        except Exception as e:
            return DocumentProcessingResult(
                success=False,
                error=str(e),
                method_used=config.method if config.method != ProcessingMethod.AUTO else ProcessingMethod.FILE_API
            )

    def process_multiple(
        self,
        documents: MultipleDocumentsInput,
        config: Optional[DocumentProcessingConfig] = None
    ) -> MultipleDocumentsResult:
        """
        Process multiple documents together.

        Args:
            documents: Multiple documents input
            config: Processing configuration (optional)

        Returns:
            MultipleDocumentsResult with combined results
        """
        if config is None:
            config = DocumentProcessingConfig()

        results = []
        for doc in documents.documents:
            result = self.process(doc, config)
            results.append(result)

        success_count = sum(1 for r in results if r.success)
        failure_count = len(results) - success_count

        # Combine successful results if needed
        combined_text = None
        combined_structured = None
        if config.output_format == OutputFormat.TEXT:
            texts = [r.text for r in results if r.success and r.text]
            if texts:
                combined_text = "\n\n---\n\n".join(texts)
        elif config.output_format == OutputFormat.STRUCTURED:
            structured_list = [r.structured_data for r in results if r.success and r.structured_data]
            if structured_list:
                combined_structured = {"documents": structured_list}

        return MultipleDocumentsResult(
            results=results,
            combined_text=combined_text,
            combined_structured=combined_structured,
            success_count=success_count,
            failure_count=failure_count
        )

    def _determine_method(
        self,
        document: DocumentInput,
        config: DocumentProcessingConfig
    ) -> ProcessingMethod:
        """Determine processing method based on config and document size"""
        if config.method != ProcessingMethod.AUTO:
            return config.method

        # Auto-determine based on document size
        source = document.source

        if source.source_type == "bytes":
            size = len(source.data)
        elif source.source_type == "base64":
            import base64
            size = len(base64.b64decode(source.data))
        elif source.source_type == "path":
            size = Path(source.file_path).stat().st_size
        else:  # url - default to FILE_API as we need to download first
            return ProcessingMethod.FILE_API

        # Use inline if <20MB, otherwise File API
        if size < 20 * 1024 * 1024:
            return ProcessingMethod.INLINE
        else:
            return ProcessingMethod.FILE_API

    def _process_inline(
        self,
        document: DocumentInput,
        config: DocumentProcessingConfig
    ) -> DocumentProcessingResult:
        """Process document inline (<20MB)"""
        from google.genai import types

        # Get document bytes
        pdf_bytes = self._get_document_bytes(document)

        # Build contents
        contents = [
            types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
            config.prompt or "Summarize this document"
        ]

        # Build config for generation
        gen_config = self._build_generation_config(config)

        # Generate content
        if config.use_streaming:
            # Streaming response
            response_text = ""
            for chunk in self.client.models.generate_content_stream(
                model=config.model or self.model,
                contents=contents,
                config=gen_config
            ):
                if hasattr(chunk, 'text') and chunk.text:
                    response_text += chunk.text
        else:
            # Non-streaming response
            response = self.client.models.generate_content(
                model=config.model or self.model,
                contents=contents,
                config=gen_config
            )
            response_text = response.text

        # Parse response based on output format
        return self._parse_response(response_text, config, response if not config.use_streaming else None)

    def _process_file_api(
        self,
        document: DocumentInput,
        config: DocumentProcessingConfig
    ) -> DocumentProcessingResult:
        """Process document using File API (>=20MB or large files)"""
        from google.genai import types

        # Upload file
        uploaded_file = self._upload_file(document)

        # Wait for processing if configured
        if config.wait_for_processing:
            self._wait_for_file_processing(uploaded_file, config.max_wait_time)

        # Build contents
        contents = [
            uploaded_file,
            config.prompt or "Summarize this document"
        ]

        # Build config for generation
        gen_config = self._build_generation_config(config)

        # Generate content
        if config.use_streaming:
            response_text = ""
            for chunk in self.client.models.generate_content_stream(
                model=config.model or self.model,
                contents=contents,
                config=gen_config
            ):
                if hasattr(chunk, 'text') and chunk.text:
                    response_text += chunk.text
            response = None
        else:
            response = self.client.models.generate_content(
                model=config.model or self.model,
                contents=contents,
                config=gen_config
            )
            response_text = response.text

        # Parse response
        result = self._parse_response(response_text, config, response if not config.use_streaming else None)

        # Add file metadata
        result.metadata = FileMetadata(
            name=uploaded_file.name,
            uri=getattr(uploaded_file, 'uri', None),
            state=getattr(uploaded_file, 'state', 'ACTIVE'),
            mime_type=getattr(uploaded_file, 'mime_type', 'application/pdf'),
            display_name=getattr(document.source, 'display_name', None)
        )

        return result

    def _get_document_bytes(self, document: DocumentInput) -> bytes:
        """Extract bytes from document source"""
        import httpx
        import base64
        from io import BytesIO

        source = document.source

        if source.source_type == "bytes":
            return source.data
        elif source.source_type == "base64":
            return base64.b64decode(source.data)
        elif source.source_type == "path":
            return Path(source.file_path).read_bytes()
        elif source.source_type == "url":
            response = httpx.get(source.url, timeout=60.0)
            response.raise_for_status()
            return response.content
        else:
            raise ValueError(f"Unknown source type: {source.source_type}")

    def _upload_file(self, document: DocumentInput):
        """Upload file to Gemini File API"""
        import httpx
        import io

        source = document.source

        # Get file bytes
        if source.source_type == "url":
            response = httpx.get(source.url, timeout=60.0)
            response.raise_for_status()
            pdf_bytes = response.content
        elif source.source_type == "path":
            pdf_bytes = Path(source.file_path).read_bytes()
        elif source.source_type == "bytes":
            pdf_bytes = source.data
        elif source.source_type == "base64":
            import base64
            pdf_bytes = base64.b64decode(source.data)
        else:
            raise ValueError(f"Unknown source type: {source.source_type}")

        # Check size limit (50MB for File API)
        max_size = 50 * 1024 * 1024
        if len(pdf_bytes) > max_size:
            raise ValueError(f"PDF too large ({len(pdf_bytes) / 1024 / 1024:.2f}MB). File API limit is 50MB.")

        # Upload to File API
        pdf_io = io.BytesIO(pdf_bytes)
        uploaded_file = self.client.files.upload(
            file=pdf_io,
            config=dict(
                mime_type="application/pdf",
                display_name=getattr(source, 'display_name', None)
            )
        )

        return uploaded_file

    def _wait_for_file_processing(self, uploaded_file, max_wait_time: int = 300):
        """Wait for file processing to complete"""
        import time

        start_time = time.time()
        while time.time() - start_time < max_wait_time:
            file_info = self.client.files.get(name=uploaded_file.name)
            state = getattr(file_info, 'state', None)

            if state == "ACTIVE":
                return
            elif state == "FAILED":
                raise Exception(f"File processing failed: {uploaded_file.name}")

            time.sleep(2)

        raise TimeoutError(f"File processing timeout after {max_wait_time} seconds")

    def _build_generation_config(self, config: DocumentProcessingConfig) -> dict:
        """Build generation config from DocumentProcessingConfig"""
        gen_config = {}

        # Set structured output if configured
        if config.output_format == OutputFormat.STRUCTURED and config.response_schema:
            if config.response_mime_type:
                gen_config["response_mime_type"] = config.response_mime_type
            else:
                gen_config["response_mime_type"] = "application/json"
            gen_config["response_schema"] = config.response_schema

        return gen_config

    def _parse_response(
        self,
        response_text: str,
        config: DocumentProcessingConfig,
        response=None
    ) -> DocumentProcessingResult:
        """Parse response based on output format"""
        result = DocumentProcessingResult(
            success=True,
            document_id=None,
            method_used=ProcessingMethod.INLINE
        )

        if config.output_format == OutputFormat.TEXT:
            result.text = response_text
        elif config.output_format == OutputFormat.STRUCTURED:
            import json
            try:
                if response and hasattr(response, 'parsed') and response.parsed is not None:
                    # Use parsed Pydantic model if available
                    if hasattr(response.parsed, 'model_dump'):
                        result.structured_data = response.parsed.model_dump()
                    else:
                        result.structured_data = response.parsed
                else:
                    # Parse JSON from text
                    result.structured_data = json.loads(response_text)
            except Exception as e:
                result.structured_data = {"raw_text": response_text, "parse_error": str(e)}
        elif config.output_format == OutputFormat.TRANSCRIPTION:
            result.transcription = response_text

        return result

