"""
File processors for various operations (image processing, document conversion)
Handles file processing with optional dependencies for graceful degradation
"""

import mimetypes
import warnings
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import IO, Optional, Union

try:
    from PIL import Image, ImageFilter

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    warnings.warn(
        "Pillow (PIL) not available - image processing will be limited", stacklevel=2
    )

OPENCV_AVAILABLE = False  # Not currently used

try:
    import magic

    MAGIC_AVAILABLE = True
except ImportError:
    try:
        import python_magic as magic

        MAGIC_AVAILABLE = True
    except ImportError:
        MAGIC_AVAILABLE = False
        # python-magic is optional for MIME type detection


@dataclass
class ProcessingOptions:
    """Options for file processing operations."""

    quality: int = 85  # JPEG quality (1-100)
    format: str = "JPEG"  # Output format
    optimize: bool = True
    progressive: bool = True
    preserve_metadata: bool = False


@dataclass
class ImageMetadata:
    """Image metadata information."""

    width: int
    height: int
    format: str
    mode: str
    size_bytes: int
    has_transparency: bool = False
    color_profile: Optional[str] = None


class BaseProcessor:
    """Base class for all file processors."""

    def __init__(self):
        self.supported_formats = set()
        self._check_dependencies()

    def _check_dependencies(self):
        """Check if required dependencies are available."""
        pass

    def _ensure_path(self, output_path: Optional[Union[str, Path]]) -> Optional[Path]:
        """Ensure output path exists if provided."""
        if output_path:
            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            return path
        return None

    def detect_mime_type(self, file_path: Union[str, Path, bytes]) -> str:
        """Detect MIME type of file."""
        if isinstance(file_path, bytes):
            # For byte content
            if MAGIC_AVAILABLE:
                return magic.from_buffer(file_path, mime=True)
            else:
                # Fallback - try to guess from content
                if file_path.startswith(b"\xff\xd8\xff"):
                    return "image/jpeg"
                elif file_path.startswith(b"\x89PNG"):
                    return "image/png"
                elif file_path.startswith(b"GIF8"):
                    return "image/gif"
                elif file_path.startswith(b"\x42\x4d"):
                    return "image/bmp"
                elif file_path.startswith(b"RIFF") and b"WEBP" in file_path[:20]:
                    return "image/webp"
                else:
                    return "application/octet-stream"
        else:
            # For file paths
            path = Path(file_path)

            if MAGIC_AVAILABLE and path.exists():
                return magic.from_file(str(path), mime=True)
            else:
                # Fallback to mimetypes
                mime_type, _ = mimetypes.guess_type(str(path))
                return mime_type or "application/octet-stream"


class ImageProcessor(BaseProcessor):
    """Image processing with graceful degradation."""

    def __init__(self):
        super().__init__()
        self.supported_formats = {"JPEG", "PNG", "GIF", "BMP", "WEBP", "TIFF"}
        if PIL_AVAILABLE:
            # Add formats supported by PIL
            self.supported_formats.update(Image.registered_extensions().keys())

    def _check_dependencies(self):
        """Check if required dependencies are available."""
        if not PIL_AVAILABLE:
            warnings.warn(
                "Pillow not available - image processing will be very limited",
                stacklevel=2,
            )

    def get_image_info(
        self, image_path: Union[str, Path, bytes, IO]
    ) -> Optional[ImageMetadata]:
        """Get image metadata information."""
        if not PIL_AVAILABLE:
            warnings.warn("Cannot get image info - Pillow not available", stacklevel=2)
            return None

        try:
            if isinstance(image_path, (str, Path)):
                with Image.open(image_path) as img:
                    return self._extract_metadata(img)
            elif isinstance(image_path, bytes):
                with Image.open(BytesIO(image_path)) as img:
                    return self._extract_metadata(img)
            else:  # IO object
                with Image.open(image_path) as img:
                    return self._extract_metadata(img)
        except Exception as e:
            warnings.warn(f"Failed to get image info: {e}", stacklevel=2)
            return None

    def _extract_metadata(self, img: "Image.Image") -> ImageMetadata:
        """Extract metadata from PIL Image object."""
        return ImageMetadata(
            width=img.width,
            height=img.height,
            format=img.format or "Unknown",
            mode=img.mode,
            size_bytes=len(img.tobytes()),
            has_transparency="transparency" in img.info or img.mode in ("RGBA", "LA"),
            color_profile=img.info.get("icc_profile"),
        )

    def resize_image(
        self,
        image_path: Union[str, Path, bytes, IO],
        width: Optional[int] = None,
        height: Optional[int] = None,
        output_path: Optional[Union[str, Path]] = None,
        options: Optional[ProcessingOptions] = None,
    ) -> bytes:
        """Resize image with optional output to file."""
        if not PIL_AVAILABLE:
            return self._fallback_resize(image_path, width, height, output_path)

        options = options or ProcessingOptions()

        try:
            # Open image
            if isinstance(image_path, (str, Path)):
                img = Image.open(image_path)
            elif isinstance(image_path, bytes):
                img = Image.open(BytesIO(image_path))
            else:  # IO object
                img = Image.open(image_path)

            # Calculate new dimensions
            original_width, original_height = img.size

            if width and height:
                new_size = (width, height)
            elif width:
                # Maintain aspect ratio based on width
                ratio = width / original_width
                new_size = (width, int(original_height * ratio))
            elif height:
                # Maintain aspect ratio based on height
                ratio = height / original_height
                new_size = (int(original_width * ratio), height)
            else:
                # No resize needed
                new_size = (original_width, original_height)

            # Resize image
            resized_img = img.resize(new_size, Image.Resampling.LANCZOS)

            # Save or return
            return self._save_image(resized_img, output_path, options)

        except Exception as e:
            warnings.warn(f"Image resize failed: {e}", stacklevel=2)
            return self._fallback_resize(image_path, width, height, output_path)

    def crop_image(
        self,
        image_path: Union[str, Path, bytes, IO],
        x: int,
        y: int,
        width: int,
        height: int,
        output_path: Optional[Union[str, Path]] = None,
        options: Optional[ProcessingOptions] = None,
    ) -> bytes:
        """Crop image to specified dimensions."""
        if not PIL_AVAILABLE:
            return self._fallback_operation(image_path, output_path, "crop")

        options = options or ProcessingOptions()

        try:
            # Open image
            if isinstance(image_path, (str, Path)):
                img = Image.open(image_path)
            elif isinstance(image_path, bytes):
                img = Image.open(BytesIO(image_path))
            else:
                img = Image.open(image_path)

            # Crop image
            cropped_img = img.crop((x, y, x + width, y + height))

            return self._save_image(cropped_img, output_path, options)

        except Exception as e:
            warnings.warn(f"Image crop failed: {e}", stacklevel=2)
            return self._fallback_operation(image_path, output_path, "crop")

    def rotate_image(
        self,
        image_path: Union[str, Path, bytes, IO],
        angle: float,
        expand: bool = True,
        output_path: Optional[Union[str, Path]] = None,
        options: Optional[ProcessingOptions] = None,
    ) -> bytes:
        """Rotate image by specified angle."""
        if not PIL_AVAILABLE:
            return self._fallback_operation(image_path, output_path, "rotate")

        options = options or ProcessingOptions()

        try:
            # Open image
            if isinstance(image_path, (str, Path)):
                img = Image.open(image_path)
            elif isinstance(image_path, bytes):
                img = Image.open(BytesIO(image_path))
            else:
                img = Image.open(image_path)

            # Rotate image
            rotated_img = img.rotate(angle, expand=expand, fillcolor="white")

            return self._save_image(rotated_img, output_path, options)

        except Exception as e:
            warnings.warn(f"Image rotation failed: {e}", stacklevel=2)
            return self._fallback_operation(image_path, output_path, "rotate")

    def apply_filter(
        self,
        image_path: Union[str, Path, bytes, IO],
        filter_type: str = "SHARPEN",
        output_path: Optional[Union[str, Path]] = None,
        options: Optional[ProcessingOptions] = None,
    ) -> bytes:
        """Apply filter to image."""
        if not PIL_AVAILABLE:
            return self._fallback_operation(
                image_path, output_path, f"filter_{filter_type}"
            )

        options = options or ProcessingOptions()

        try:
            # Open image
            if isinstance(image_path, (str, Path)):
                img = Image.open(image_path)
            elif isinstance(image_path, bytes):
                img = Image.open(BytesIO(image_path))
            else:
                img = Image.open(image_path)

            # Apply filter
            filter_map = {
                "BLUR": ImageFilter.BLUR,
                "CONTOUR": ImageFilter.CONTOUR,
                "DETAIL": ImageFilter.DETAIL,
                "EDGE_ENHANCE": ImageFilter.EDGE_ENHANCE,
                "EMBOSS": ImageFilter.EMBOSS,
                "FIND_EDGES": ImageFilter.FIND_EDGES,
                "SHARPEN": ImageFilter.SHARPEN,
                "SMOOTH": ImageFilter.SMOOTH,
            }

            if filter_type in filter_map:
                filtered_img = img.filter(filter_map[filter_type])
            else:
                warnings.warn(f"Unknown filter type: {filter_type}", stacklevel=2)
                filtered_img = img

            return self._save_image(filtered_img, output_path, options)

        except Exception as e:
            warnings.warn(f"Filter application failed: {e}", stacklevel=2)
            return self._fallback_operation(
                image_path, output_path, f"filter_{filter_type}"
            )

    def convert_format(
        self,
        image_path: Union[str, Path, bytes, IO],
        output_format: str = "JPEG",
        output_path: Optional[Union[str, Path]] = None,
        options: Optional[ProcessingOptions] = None,
    ) -> bytes:
        """Convert image to different format."""
        if not PIL_AVAILABLE:
            return self._fallback_operation(
                image_path, output_path, f"convert_to_{output_format}"
            )

        options = options or ProcessingOptions()
        options.format = output_format.upper()

        try:
            # Open image
            if isinstance(image_path, (str, Path)):
                img = Image.open(image_path)
            elif isinstance(image_path, bytes):
                img = Image.open(BytesIO(image_path))
            else:
                img = Image.open(image_path)

            # Convert mode if needed for JPEG
            if options.format == "JPEG" and img.mode in ("RGBA", "LA"):
                # Convert RGBA to RGB for JPEG
                background = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "RGBA":
                    background.paste(
                        img, mask=img.split()[-1]
                    )  # Use alpha channel as mask
                else:
                    background.paste(img)
                img = background

            return self._save_image(img, output_path, options)

        except Exception as e:
            warnings.warn(f"Format conversion failed: {e}", stacklevel=2)
            return self._fallback_operation(
                image_path, output_path, f"convert_to_{output_format}"
            )

    def _save_image(
        self,
        img: "Image.Image",
        output_path: Optional[Union[str, Path]],
        options: ProcessingOptions,
    ) -> bytes:
        """Save PIL image to file or return bytes."""
        save_kwargs = {
            "format": options.format,
            "quality": options.quality,
            "optimize": options.optimize,
        }

        if options.format == "JPEG":
            save_kwargs["progressive"] = options.progressive

        if output_path:
            path = self._ensure_path(output_path)
            img.save(path, **save_kwargs)
            with open(path, "rb") as f:
                return f.read()
        else:
            buffer = BytesIO()
            img.save(buffer, **save_kwargs)
            return buffer.getvalue()

    def _fallback_resize(
        self,
        image_path: Union[str, Path, bytes, IO],
        width: Optional[int],
        height: Optional[int],
        output_path: Optional[Union[str, Path]],
    ) -> bytes:
        """Fallback for image resize when PIL unavailable."""
        warnings.warn(
            "Image resize not available - returning original image", stacklevel=2
        )
        return self._get_original_bytes(image_path, output_path)

    def _fallback_operation(
        self,
        image_path: Union[str, Path, bytes, IO],
        output_path: Optional[Union[str, Path]],
        operation: str,
    ) -> bytes:
        """Fallback for image operations when PIL unavailable."""
        warnings.warn(
            f"Image {operation} not available - returning original image", stacklevel=2
        )
        return self._get_original_bytes(image_path, output_path)

    def _get_original_bytes(
        self,
        image_path: Union[str, Path, bytes, IO],
        output_path: Optional[Union[str, Path]],
    ) -> bytes:
        """Get original image bytes."""
        if isinstance(image_path, bytes):
            data = image_path
        elif isinstance(image_path, (str, Path)):
            with open(image_path, "rb") as f:
                data = f.read()
        else:  # IO object
            data = image_path.read()
            if hasattr(image_path, "seek"):
                image_path.seek(0)  # Reset position

        if output_path:
            path = self._ensure_path(output_path)
            with open(path, "wb") as f:
                f.write(data)

        return data


class DocumentProcessor(BaseProcessor):
    """Document processing operations."""

    def __init__(self):
        super().__init__()
        self.supported_formats = {"PDF", "DOC", "DOCX", "TXT", "RTF"}

    def extract_text(self, document_path: Union[str, Path, bytes, IO]) -> str:
        """Extract text from document (placeholder implementation)."""
        warnings.warn(
            "Document text extraction not implemented - use specialized libraries",
            stacklevel=2,
        )

        if isinstance(document_path, (str, Path)):
            try:
                with open(document_path, encoding="utf-8", errors="ignore") as f:
                    return f.read()
            except Exception:
                return "Text extraction failed"

        return "Text extraction not available for this input type"

    def convert_to_pdf(
        self,
        document_path: Union[str, Path, bytes, IO],
        output_path: Optional[Union[str, Path]] = None,
    ) -> bytes:
        """Convert document to PDF (placeholder implementation)."""
        warnings.warn(
            "Document to PDF conversion not implemented - use specialized libraries",
            stacklevel=2,
        )

        # Return placeholder PDF content
        placeholder_content = b"PDF conversion not available"

        if output_path:
            path = self._ensure_path(output_path)
            with open(path, "wb") as f:
                f.write(placeholder_content)

        return placeholder_content


# Convenience functions for backward compatibility
def resize_image(
    image_path: Union[str, Path, bytes, IO],
    width: int,
    height: int,
    output_path: Optional[Union[str, Path]] = None,
) -> bytes:
    """Resize image to specified dimensions."""
    processor = ImageProcessor()
    return processor.resize_image(image_path, width, height, output_path)


def convert_image_format(
    image_path: Union[str, Path, bytes, IO],
    output_format: str,
    output_path: Optional[Union[str, Path]] = None,
) -> bytes:
    """Convert image to specified format."""
    processor = ImageProcessor()
    return processor.convert_format(image_path, output_format, output_path)


def get_image_info(image_path: Union[str, Path, bytes, IO]) -> Optional[ImageMetadata]:
    """Get image metadata."""
    processor = ImageProcessor()
    return processor.get_image_info(image_path)


# Export main classes and functions
__all__ = [
    "ProcessingOptions",
    "ImageMetadata",
    "BaseProcessor",
    "ImageProcessor",
    "DocumentProcessor",
    "resize_image",
    "convert_image_format",
    "get_image_info",
]
