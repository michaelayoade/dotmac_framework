"""
Image processing and chart generation utilities.

This module provides comprehensive image processing capabilities including
chart generation, QR codes, thumbnails, watermarking, and image optimization.
"""

import io
import logging
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Optional, Tuple, Union

# Chart generation
import matplotlib

# QR code generation
import qrcode

# PIL/Pillow for image processing
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from PIL.ExifTags import TAGS
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import CircleModuleDrawer, RoundedModuleDrawer

matplotlib.use("Agg")  # Use non-interactive backend
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

logger = logging.getLogger(__name__)


@dataclass
class ImageMetadata:
    """Metadata for processed images."""

    file_id: str
    original_filename: str
    format: str
    width: int
    height: int
    size_bytes: int
    processing_type: str
    created_at: datetime
    quality: Optional[int] = None
    has_transparency: bool = False
    color_mode: str = "RGB"
    dpi: Optional[Tuple[int, int]] = None
    custom_metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.custom_metadata is None:
            self.custom_metadata = {}


class ImageProcessor:
    """Comprehensive image processing with chart generation and optimization."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize image processor with configuration."""
        self.config = config or {}
        self.max_dimensions = self.config.get("max_dimensions", (2048, 2048))
        self.compression_quality = self.config.get("compression_quality", 85)
        self.thumbnail_size = self.config.get("thumbnail_size", (150, 150))
        self.watermark_opacity = self.config.get("watermark_opacity", 128)

        # Chart configuration
        self.chart_config = self.config.get(
            "chart",
            {
                "figsize": (10, 6),
                "dpi": 100,
                "style": "seaborn-v0_8",
                "colors": [
                    "#1f77b4",
                    "#ff7f0e",
                    "#2ca02c",
                    "#d62728",
                    "#9467bd",
                    "#8c564b",
                ],
            },
        )

        # Setup matplotlib style
        if self.chart_config.get("style"):
            try:
                plt.style.use(self.chart_config["style"])
            except Exception:
                logger.warning(
                    f"Could not set matplotlib style: {self.chart_config['style']}"
                )

    def generate_chart(
        self,
        chart_type: str,
        data: Dict[str, Any],
        output_path: Optional[str] = None,
        style_config: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, ImageMetadata]:
        """
        Generate charts (bar, line, pie, etc.) as images.

        Args:
            chart_type: Type of chart ('bar', 'line', 'pie', 'scatter', 'histogram')
            data: Chart data dictionary
            output_path: Output file path (optional)
            style_config: Chart styling configuration

        Returns:
            Tuple of (file_path, metadata)
        """
        if not output_path:
            file_id = str(uuid.uuid4())
            output_path = f"/tmp/chart_{file_id}.png"
        else:
            file_id = str(uuid.uuid4())

        style_config = style_config or {}

        try:
            # Create figure
            figsize = style_config.get("figsize", self.chart_config["figsize"])
            dpi = style_config.get("dpi", self.chart_config["dpi"])

            fig, ax = plt.subplots(figsize=figsize, dpi=dpi)

            # Generate chart based on type
            if chart_type == "bar":
                self._create_bar_chart(ax, data, style_config)
            elif chart_type == "line":
                self._create_line_chart(ax, data, style_config)
            elif chart_type == "pie":
                self._create_pie_chart(ax, data, style_config)
            elif chart_type == "scatter":
                self._create_scatter_chart(ax, data, style_config)
            elif chart_type == "histogram":
                self._create_histogram_chart(ax, data, style_config)
            else:
                raise ValueError(f"Unsupported chart type: {chart_type}")

            # Apply common styling
            self._apply_chart_styling(fig, ax, data, style_config)

            # Save chart
            plt.tight_layout()
            plt.savefig(
                output_path,
                format="png",
                dpi=dpi,
                bbox_inches="tight",
                facecolor="white",
                edgecolor="none",
            )
            plt.close(fig)

            # Get image info
            with Image.open(output_path) as img:
                width, height = img.size
                file_size = Path(output_path).stat().st_size

            # Create metadata
            metadata = ImageMetadata(
                file_id=file_id,
                original_filename=f"{chart_type}_chart.png",
                format="PNG",
                width=width,
                height=height,
                size_bytes=file_size,
                processing_type="chart_generation",
                created_at=datetime.now(timezone.utc),
                custom_metadata={
                    "chart_type": chart_type,
                    "data_points": len(data.get("values", [])),
                    "style": style_config.get("style", "default"),
                },
            )

            logger.info(
                f"Generated {chart_type} chart: {output_path} ({width}x{height})"
            )
            return output_path, metadata

        except Exception as e:
            logger.error(f"Error generating {chart_type} chart: {e}")
            raise

    def generate_qr_code(
        self,
        data: str,
        output_path: Optional[str] = None,
        size: Tuple[int, int] = (200, 200),
        style_config: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, ImageMetadata]:
        """
        Generate QR code image.

        Args:
            data: Data to encode in QR code
            output_path: Output file path (optional)
            size: QR code size (width, height)
            style_config: QR code styling configuration

        Returns:
            Tuple of (file_path, metadata)
        """
        if not output_path:
            file_id = str(uuid.uuid4())
            output_path = f"/tmp/qr_code_{file_id}.png"
        else:
            file_id = str(uuid.uuid4())

        style_config = style_config or {}

        try:
            # Create QR code
            qr = qrcode.QRCode(
                version=style_config.get("version", 1),
                error_correction=getattr(
                    qrcode.constants,
                    f"ERROR_CORRECT_{style_config.get('error_correction', 'M')}",
                ),
                box_size=style_config.get("box_size", 10),
                border=style_config.get("border", 4),
            )

            qr.add_data(data)
            qr.make(fit=True)

            # Create image with styling
            fill_color = style_config.get("fill_color", "black")
            back_color = style_config.get("back_color", "white")

            # Check if we should use styled image
            module_drawer = style_config.get("module_drawer")
            if module_drawer == "rounded":
                image_factory = StyledPilImage
                module_drawer = RoundedModuleDrawer()
            elif module_drawer == "circle":
                image_factory = StyledPilImage
                module_drawer = CircleModuleDrawer()
            else:
                image_factory = None
                module_drawer = None

            if image_factory and module_drawer:
                img = qr.make_image(
                    image_factory=image_factory,
                    module_drawer=module_drawer,
                    fill_color=fill_color,
                    back_color=back_color,
                )
            else:
                img = qr.make_image(fill_color=fill_color, back_color=back_color)

            # Resize if needed
            if size != img.size:
                img = img.resize(size, Image.Resampling.LANCZOS)

            # Save image
            img.save(output_path, format="PNG")

            # Get file size
            file_size = Path(output_path).stat().st_size

            # Create metadata
            metadata = ImageMetadata(
                file_id=file_id,
                original_filename="qr_code.png",
                format="PNG",
                width=size[0],
                height=size[1],
                size_bytes=file_size,
                processing_type="qr_generation",
                created_at=datetime.now(timezone.utc),
                custom_metadata={
                    "data_length": len(data),
                    "error_correction": style_config.get("error_correction", "M"),
                    "version": qr.version,
                },
            )

            logger.info(f"Generated QR code: {output_path} ({size[0]}x{size[1]})")
            return output_path, metadata

        except Exception as e:
            logger.error(f"Error generating QR code: {e}")
            raise

    def create_thumbnail(
        self,
        image_input: Union[str, BinaryIO, Image.Image],
        output_path: Optional[str] = None,
        size: Tuple[int, int] = None,
        maintain_aspect: bool = True,
    ) -> Tuple[str, ImageMetadata]:
        """
        Create image thumbnail.

        Args:
            image_input: Source image (path, file object, or PIL Image)
            output_path: Output file path (optional)
            size: Thumbnail size (optional, uses config default)
            maintain_aspect: Whether to maintain aspect ratio

        Returns:
            Tuple of (file_path, metadata)
        """
        if not output_path:
            file_id = str(uuid.uuid4())
            output_path = f"/tmp/thumbnail_{file_id}.png"
        else:
            file_id = str(uuid.uuid4())

        size = size or self.thumbnail_size

        try:
            # Load image
            if isinstance(image_input, str):
                img = Image.open(image_input)
                original_filename = Path(image_input).name
            elif isinstance(image_input, Image.Image):
                img = image_input.copy()
                original_filename = "image"
            else:
                img = Image.open(image_input)
                original_filename = "image"

            # Convert to RGB if necessary
            if img.mode in ("RGBA", "LA", "P"):
                # Create white background
                background = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "P":
                    img = img.convert("RGBA")
                background.paste(
                    img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None
                )
                img = background
            elif img.mode != "RGB":
                img = img.convert("RGB")

            # Create thumbnail
            if maintain_aspect:
                img.thumbnail(size, Image.Resampling.LANCZOS)
                # Create new image with exact size and center the thumbnail
                thumb = Image.new("RGB", size, (255, 255, 255))
                thumb_pos = ((size[0] - img.size[0]) // 2, (size[1] - img.size[1]) // 2)
                thumb.paste(img, thumb_pos)
                img = thumb
            else:
                img = img.resize(size, Image.Resampling.LANCZOS)

            # Apply sharpening
            img = img.filter(
                ImageFilter.UnsharpMask(radius=1, percent=150, threshold=3)
            )

            # Save thumbnail
            img.save(output_path, format="PNG", optimize=True)

            # Get file size
            file_size = Path(output_path).stat().st_size

            # Create metadata
            metadata = ImageMetadata(
                file_id=file_id,
                original_filename=f"thumb_{original_filename}",
                format="PNG",
                width=img.size[0],
                height=img.size[1],
                size_bytes=file_size,
                processing_type="thumbnail_generation",
                created_at=datetime.now(timezone.utc),
                custom_metadata={
                    "thumbnail_size": size,
                    "maintain_aspect": maintain_aspect,
                },
            )

            logger.info(
                f"Created thumbnail: {output_path} ({img.size[0]}x{img.size[1]})"
            )
            return output_path, metadata

        except Exception as e:
            logger.error(f"Error creating thumbnail: {e}")
            raise

    def add_watermark(
        self,
        image_input: Union[str, BinaryIO, Image.Image],
        watermark_text: str,
        output_path: Optional[str] = None,
        position: str = "bottom-right",
        style_config: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, ImageMetadata]:
        """
        Add text watermark to image.

        Args:
            image_input: Source image
            watermark_text: Text to use as watermark
            output_path: Output file path (optional)
            position: Watermark position (corner names or center)
            style_config: Watermark styling configuration

        Returns:
            Tuple of (file_path, metadata)
        """
        if not output_path:
            file_id = str(uuid.uuid4())
            output_path = f"/tmp/watermarked_{file_id}.png"
        else:
            file_id = str(uuid.uuid4())

        style_config = style_config or {}

        try:
            # Load image
            if isinstance(image_input, str):
                img = Image.open(image_input)
                original_filename = Path(image_input).name
            elif isinstance(image_input, Image.Image):
                img = image_input.copy()
                original_filename = "image"
            else:
                img = Image.open(image_input)
                original_filename = "image"

            # Create watermark
            watermark_img = self._create_text_watermark(
                img.size, watermark_text, position, style_config
            )

            # Apply watermark
            img = Image.alpha_composite(img.convert("RGBA"), watermark_img).convert(
                "RGB"
            )

            # Save image
            img.save(
                output_path,
                format="PNG",
                optimize=True,
                quality=self.compression_quality,
            )

            # Get file size
            file_size = Path(output_path).stat().st_size

            # Create metadata
            metadata = ImageMetadata(
                file_id=file_id,
                original_filename=f"watermarked_{original_filename}",
                format="PNG",
                width=img.size[0],
                height=img.size[1],
                size_bytes=file_size,
                processing_type="watermark_addition",
                created_at=datetime.now(timezone.utc),
                quality=self.compression_quality,
                custom_metadata={
                    "watermark_text": watermark_text,
                    "watermark_position": position,
                },
            )

            logger.info(f"Added watermark to image: {output_path}")
            return output_path, metadata

        except Exception as e:
            logger.error(f"Error adding watermark: {e}")
            raise

    def optimize_image(
        self,
        image_input: Union[str, BinaryIO, Image.Image],
        output_path: Optional[str] = None,
        max_dimensions: Optional[Tuple[int, int]] = None,
        quality: Optional[int] = None,
        format: str = "JPEG",
    ) -> Tuple[str, ImageMetadata]:
        """
        Optimize image for web/storage.

        Args:
            image_input: Source image
            output_path: Output file path (optional)
            max_dimensions: Maximum dimensions (optional)
            quality: Compression quality (optional)
            format: Output format

        Returns:
            Tuple of (file_path, metadata)
        """
        if not output_path:
            file_id = str(uuid.uuid4())
            ext = "jpg" if format.upper() == "JPEG" else format.lower()
            output_path = f"/tmp/optimized_{file_id}.{ext}"
        else:
            file_id = str(uuid.uuid4())

        max_dimensions = max_dimensions or self.max_dimensions
        quality = quality or self.compression_quality

        try:
            # Load image
            if isinstance(image_input, str):
                img = Image.open(image_input)
                original_filename = Path(image_input).name
            elif isinstance(image_input, Image.Image):
                img = image_input.copy()
                original_filename = "image"
            else:
                img = Image.open(image_input)
                original_filename = "image"

            original_size = img.size

            # Resize if needed
            if img.size[0] > max_dimensions[0] or img.size[1] > max_dimensions[1]:
                img.thumbnail(max_dimensions, Image.Resampling.LANCZOS)

            # Convert format if needed
            if format.upper() == "JPEG" and img.mode in ("RGBA", "LA", "P"):
                # Create white background for JPEG
                background = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "P":
                    img = img.convert("RGBA")
                background.paste(
                    img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None
                )
                img = background
            elif format.upper() != "JPEG" and img.mode != "RGBA":
                img = img.convert("RGBA")

            # Apply enhancement
            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(1.1)

            # Save optimized image
            save_kwargs = {"format": format, "optimize": True}
            if format.upper() == "JPEG":
                save_kwargs["quality"] = quality

            img.save(output_path, **save_kwargs)

            # Get file size
            file_size = Path(output_path).stat().st_size

            # Create metadata
            metadata = ImageMetadata(
                file_id=file_id,
                original_filename=f"optimized_{original_filename}",
                format=format.upper(),
                width=img.size[0],
                height=img.size[1],
                size_bytes=file_size,
                processing_type="optimization",
                created_at=datetime.now(timezone.utc),
                quality=quality if format.upper() == "JPEG" else None,
                custom_metadata={
                    "original_size": original_size,
                    "compression_ratio": round(
                        file_size / (original_size[0] * original_size[1] * 3), 4
                    ),
                },
            )

            logger.info(
                f"Optimized image: {output_path} (size reduction: {original_size} -> {img.size})"
            )
            return output_path, metadata

        except Exception as e:
            logger.error(f"Error optimizing image: {e}")
            raise

    def _create_bar_chart(self, ax, data: Dict[str, Any], style_config: Dict[str, Any]):
        """Create bar chart."""
        labels = data.get("labels", [])
        values = data.get("values", [])

        if not labels or not values:
            raise ValueError("Bar chart requires 'labels' and 'values'")

        colors = style_config.get("colors", self.chart_config["colors"])

        bars = ax.bar(labels, values, color=colors[: len(values)])

        # Add value labels on bars
        if style_config.get("show_values", True):
            for bar in bars:
                height = bar.get_height()
                ax.text(
                    bar.get_x() + bar.get_width() / 2.0,
                    height,
                    f"{height:.1f}" if isinstance(height, float) else str(height),
                    ha="center",
                    va="bottom",
                )

    def _create_line_chart(
        self, ax, data: Dict[str, Any], style_config: Dict[str, Any]
    ):
        """Create line chart."""
        if "series" in data:
            # Multiple series
            for i, series in enumerate(data["series"]):
                x_data = series.get("x", range(len(series.get("y", []))))
                y_data = series.get("y", [])
                label = series.get("label", f"Series {i+1}")

                ax.plot(x_data, y_data, label=label, marker="o")

            ax.legend()
        else:
            # Single series
            x_data = data.get("x", range(len(data.get("y", []))))
            y_data = data.get("y", [])

            ax.plot(
                x_data, y_data, marker="o", color=style_config.get("color", "#1f77b4")
            )

    def _create_pie_chart(self, ax, data: Dict[str, Any], style_config: Dict[str, Any]):
        """Create pie chart."""
        labels = data.get("labels", [])
        sizes = data.get("values", [])

        if not labels or not sizes:
            raise ValueError("Pie chart requires 'labels' and 'values'")

        colors = style_config.get("colors", self.chart_config["colors"])
        explode = style_config.get("explode", [0.1] + [0] * (len(sizes) - 1))

        wedges, texts, autotexts = ax.pie(
            sizes,
            labels=labels,
            colors=colors[: len(sizes)],
            explode=explode[: len(sizes)] if explode else None,
            autopct="%1.1f%%",
            shadow=style_config.get("shadow", True),
        )

        ax.axis("equal")

    def _create_scatter_chart(
        self, ax, data: Dict[str, Any], style_config: Dict[str, Any]
    ):
        """Create scatter chart."""
        x_data = data.get("x", [])
        y_data = data.get("y", [])

        if not x_data or not y_data:
            raise ValueError("Scatter chart requires 'x' and 'y' data")

        size = style_config.get("size", 50)
        color = style_config.get("color", "#1f77b4")
        alpha = style_config.get("alpha", 0.7)

        ax.scatter(x_data, y_data, s=size, c=color, alpha=alpha)

    def _create_histogram_chart(
        self, ax, data: Dict[str, Any], style_config: Dict[str, Any]
    ):
        """Create histogram chart."""
        values = data.get("values", [])

        if not values:
            raise ValueError("Histogram requires 'values' data")

        bins = style_config.get("bins", 30)
        color = style_config.get("color", "#1f77b4")
        alpha = style_config.get("alpha", 0.7)

        ax.hist(values, bins=bins, color=color, alpha=alpha, edgecolor="black")

    def _apply_chart_styling(
        self, fig: Figure, ax, data: Dict[str, Any], style_config: Dict[str, Any]
    ):
        """Apply common styling to chart."""
        # Set title
        title = data.get("title") or style_config.get("title", "")
        if title:
            ax.set_title(title, fontsize=style_config.get("title_size", 16), pad=20)

        # Set axis labels
        xlabel = data.get("xlabel") or style_config.get("xlabel", "")
        ylabel = data.get("ylabel") or style_config.get("ylabel", "")

        if xlabel:
            ax.set_xlabel(xlabel, fontsize=style_config.get("label_size", 12))
        if ylabel:
            ax.set_ylabel(ylabel, fontsize=style_config.get("label_size", 12))

        if style_config.get("grid", True):
            ax.grid(True, alpha=0.3)

        # Background color
        bg_color = style_config.get("background_color", "white")
        fig.patch.set_facecolor(bg_color)
        ax.set_facecolor(bg_color)

        # Rotate x-axis labels if needed
        if style_config.get("rotate_labels"):
            plt.xticks(rotation=style_config["rotate_labels"])

    def _create_text_watermark(
        self,
        image_size: Tuple[int, int],
        text: str,
        position: str,
        style_config: Dict[str, Any],
    ) -> Image.Image:
        """Create text watermark overlay."""
        # Create transparent image for watermark
        watermark = Image.new("RGBA", image_size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(watermark)

        # Font configuration
        font_size = style_config.get("font_size", max(image_size) // 40)
        try:
            # Try to load a font
            font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", font_size)
        except Exception:
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except Exception:
                font = ImageFont.load_default()

        # Get text dimensions
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # Calculate position
        margin = style_config.get("margin", 20)

        if position == "top-left":
            x, y = margin, margin
        elif position == "top-right":
            x, y = image_size[0] - text_width - margin, margin
        elif position == "bottom-left":
            x, y = margin, image_size[1] - text_height - margin
        elif position == "bottom-right":
            x, y = (
                image_size[0] - text_width - margin,
                image_size[1] - text_height - margin,
            )
        elif position == "center":
            x, y = (image_size[0] - text_width) // 2, (image_size[1] - text_height) // 2
        else:
            # Default to bottom-right
            x, y = (
                image_size[0] - text_width - margin,
                image_size[1] - text_height - margin,
            )

        # Text color with opacity
        color = style_config.get("color", (255, 255, 255))
        opacity = style_config.get("opacity", self.watermark_opacity)
        text_color = (*color, opacity)

        # Draw text
        draw.text((x, y), text, font=font, fill=text_color)

        return watermark
