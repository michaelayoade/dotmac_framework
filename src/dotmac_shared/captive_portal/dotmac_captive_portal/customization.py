"""
Portal customization and theming system for captive portals.

Provides comprehensive customization capabilities including themes, branding,
custom HTML/CSS, multi-language support, and dynamic content management.
"""

import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from io import BytesIO
from pathlib import Path
from typing import Any

import structlog
from jinja2 import Environment, FileSystemLoader
from PIL import Image

logger = structlog.get_logger(__name__)


class ThemeType(Enum):
    """Portal theme types."""

    DEFAULT = "default"
    CORPORATE = "corporate"
    HOSPITALITY = "hospitality"
    RETAIL = "retail"
    EDUCATION = "education"
    HEALTHCARE = "healthcare"
    CUSTOM = "custom"


class ContentType(Enum):
    """Content types for portal pages."""

    WELCOME = "welcome"
    TERMS = "terms"
    PRIVACY = "privacy"
    SUCCESS = "success"
    ERROR = "error"
    MAINTENANCE = "maintenance"


@dataclass
class ColorScheme:
    """Color scheme configuration."""

    primary: str = "#007bff"
    secondary: str = "#6c757d"
    success: str = "#28a745"
    warning: str = "#ffc107"
    danger: str = "#dc3545"
    info: str = "#17a2b8"
    light: str = "#f8f9fa"
    dark: str = "#343a40"
    background: str = "#ffffff"
    text: str = "#333333"

    def to_dict(self) -> dict[str, str]:
        """Convert to dictionary for CSS generation."""
        return {
            "primary": self.primary,
            "secondary": self.secondary,
            "success": self.success,
            "warning": self.warning,
            "danger": self.danger,
            "info": self.info,
            "light": self.light,
            "dark": self.dark,
            "background": self.background,
            "text": self.text,
        }


@dataclass
class Typography:
    """Typography configuration."""

    font_family: str = "Arial, sans-serif"
    font_size_base: str = "16px"
    font_size_h1: str = "2.5rem"
    font_size_h2: str = "2rem"
    font_size_h3: str = "1.75rem"
    font_size_h4: str = "1.5rem"
    font_size_small: str = "0.875rem"
    font_weight_normal: str = "400"
    font_weight_bold: str = "700"
    line_height: str = "1.5"

    def to_dict(self) -> dict[str, str]:
        """Convert to dictionary for CSS generation."""
        return {
            "font_family": self.font_family,
            "font_size_base": self.font_size_base,
            "font_size_h1": self.font_size_h1,
            "font_size_h2": self.font_size_h2,
            "font_size_h3": self.font_size_h3,
            "font_size_h4": self.font_size_h4,
            "font_size_small": self.font_size_small,
            "font_weight_normal": self.font_weight_normal,
            "font_weight_bold": self.font_weight_bold,
            "line_height": self.line_height,
        }


@dataclass
class BrandingConfig:
    """Branding configuration for portals."""

    company_name: str = "Guest Network"
    logo_url: str | None = None
    favicon_url: str | None = None
    website_url: str | None = None
    support_email: str | None = None
    support_phone: str | None = None

    # Social media links
    facebook_url: str | None = None
    twitter_url: str | None = None
    instagram_url: str | None = None
    linkedin_url: str | None = None

    # Legal information
    terms_url: str | None = None
    privacy_url: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "company_name": self.company_name,
            "logo_url": self.logo_url,
            "favicon_url": self.favicon_url,
            "website_url": self.website_url,
            "support_email": self.support_email,
            "support_phone": self.support_phone,
            "social_media": {
                "facebook": self.facebook_url,
                "twitter": self.twitter_url,
                "instagram": self.instagram_url,
                "linkedin": self.linkedin_url,
            },
            "legal": {
                "terms_url": self.terms_url,
                "privacy_url": self.privacy_url,
            },
        }


@dataclass
class LayoutConfig:
    """Layout configuration for portal pages."""

    layout_type: str = "centered"  # centered, full_width, sidebar
    container_max_width: str = "600px"
    background_image: str | None = None
    background_video: str | None = None
    background_overlay: bool = True
    background_overlay_opacity: float = 0.7

    # Component visibility
    show_logo: bool = True
    show_progress_bar: bool = True
    show_language_selector: bool = False
    show_social_login: bool = True
    show_footer: bool = True

    # Form styling
    form_style: str = "card"  # card, inline, minimal
    button_style: str = "rounded"  # rounded, square, pill
    input_style: str = "outline"  # outline, filled, underline

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "layout_type": self.layout_type,
            "container_max_width": self.container_max_width,
            "background": {
                "image": self.background_image,
                "video": self.background_video,
                "overlay": self.background_overlay,
                "overlay_opacity": self.background_overlay_opacity,
            },
            "components": {
                "logo": self.show_logo,
                "progress_bar": self.show_progress_bar,
                "language_selector": self.show_language_selector,
                "social_login": self.show_social_login,
                "footer": self.show_footer,
            },
            "styles": {
                "form": self.form_style,
                "button": self.button_style,
                "input": self.input_style,
            },
        }


class Theme:
    """Portal theme configuration."""

    def __init__(
        self,
        theme_id: str,
        name: str,
        theme_type: ThemeType = ThemeType.DEFAULT,
        colors: ColorScheme | None = None,
        typography: Typography | None = None,
        layout: LayoutConfig | None = None,
        custom_css: str | None = None,
        custom_js: str | None = None,
        **kwargs,
    ):
        self.theme_id = theme_id
        self.name = name
        self.theme_type = theme_type
        self.colors = colors or ColorScheme()
        self.typography = typography or Typography()
        self.layout = layout or LayoutConfig()
        self.custom_css = custom_css
        self.custom_js = custom_js

        # Additional properties
        self.description = kwargs.get("description", "")
        self.preview_image = kwargs.get("preview_image")
        self.responsive = kwargs.get("responsive", True)
        self.dark_mode_support = kwargs.get("dark_mode_support", False)

        self.created_at = datetime.now(UTC)
        self.updated_at = datetime.now(UTC)

    def generate_css(self) -> str:
        """Generate CSS for the theme."""
        css_template = """
        /* Theme: {theme_name} */
        :root {{
            /* Colors */
            --color-primary: {colors[primary]};
            --color-secondary: {colors[secondary]};
            --color-success: {colors[success]};
            --color-warning: {colors[warning]};
            --color-danger: {colors[danger]};
            --color-info: {colors[info]};
            --color-light: {colors[light]};
            --color-dark: {colors[dark]};
            --color-background: {colors[background]};
            --color-text: {colors[text]};

            /* Typography */
            --font-family: {typography[font_family]};
            --font-size-base: {typography[font_size_base]};
            --font-size-h1: {typography[font_size_h1]};
            --font-size-h2: {typography[font_size_h2]};
            --font-size-h3: {typography[font_size_h3]};
            --font-size-h4: {typography[font_size_h4]};
            --font-size-small: {typography[font_size_small]};
            --font-weight-normal: {typography[font_weight_normal]};
            --font-weight-bold: {typography[font_weight_bold]};
            --line-height: {typography[line_height]};

            /* Layout */
            --container-max-width: {layout[container_max_width]};
        }}

        body {{
            font-family: var(--font-family);
            font-size: var(--font-size-base);
            line-height: var(--line-height);
            color: var(--color-text);
            background-color: var(--color-background);
        }}

        .portal-container {{
            max-width: var(--container-max-width);
            margin: 0 auto;
            padding: 2rem;
        }}

        .btn-primary {{
            background-color: var(--color-primary);
            border-color: var(--color-primary);
            color: white;
        }}

        .btn-primary:hover {{
            background-color: var(--color-primary);
            filter: brightness(0.9);
        }}

        h1 {{ font-size: var(--font-size-h1); }}
        h2 {{ font-size: var(--font-size-h2); }}
        h3 {{ font-size: var(--font-size-h3); }}
        h4 {{ font-size: var(--font-size-h4); }}

        {custom_css}
        """

        return css_template.format(
            theme_name=self.name,
            colors=self.colors.to_dict(),
            typography=self.typography.to_dict(),
            layout=self.layout.to_dict(),
            custom_css=self.custom_css or "",
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert theme to dictionary."""
        return {
            "theme_id": self.theme_id,
            "name": self.name,
            "theme_type": self.theme_type.value,
            "description": self.description,
            "colors": self.colors.to_dict(),
            "typography": self.typography.to_dict(),
            "layout": self.layout.to_dict(),
            "custom_css": self.custom_css,
            "custom_js": self.custom_js,
            "responsive": self.responsive,
            "dark_mode_support": self.dark_mode_support,
            "preview_image": self.preview_image,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class ContentManager:
    """Manages portal content and templates."""

    def __init__(self, template_dir: str = "templates"):
        self.template_dir = Path(template_dir)
        self.template_dir.mkdir(exist_ok=True)
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=True,
        )
        self._content_cache: dict[str, str] = {}
        self._translations: dict[str, dict[str, str]] = {}

    def set_content(
        self,
        content_type: ContentType | str,
        content: str,
        language: str = "en",
        portal_id: str | None = None,
    ):
        """Set content for a specific type and language."""
        if isinstance(content_type, ContentType):
            content_type = content_type.value

        cache_key = f"{portal_id or 'default'}:{content_type}:{language}"
        self._content_cache[cache_key] = content

        logger.info(
            "Content updated",
            content_type=content_type,
            language=language,
            portal_id=portal_id,
        )

    def get_content(
        self,
        content_type: ContentType | str,
        language: str = "en",
        portal_id: str | None = None,
        fallback_language: str = "en",
    ) -> str | None:
        """Get content for a specific type and language."""
        if isinstance(content_type, ContentType):
            content_type = content_type.value

        # Try specific portal + language
        cache_key = f"{portal_id or 'default'}:{content_type}:{language}"
        if cache_key in self._content_cache:
            return self._content_cache[cache_key]

        # Try fallback language
        if language != fallback_language:
            fallback_key = (
                f"{portal_id or 'default'}:{content_type}:{fallback_language}"
            )
            if fallback_key in self._content_cache:
                return self._content_cache[fallback_key]

        # Try default portal
        if portal_id:
            default_key = f"default:{content_type}:{language}"
            if default_key in self._content_cache:
                return self._content_cache[default_key]

        return None

    def render_template(
        self,
        template_name: str,
        context: dict[str, Any],
        language: str = "en",
    ) -> str:
        """Render a Jinja2 template with context."""
        try:
            template = self.jinja_env.get_template(f"{language}/{template_name}")
        except (FileNotFoundError, OSError):
            # Fallback to English template
            template = self.jinja_env.get_template(f"en/{template_name}")

        # Add translation helper to context
        context["_"] = lambda key: self.get_translation(key, language)
        context["lang"] = language

        return template.render(**context)

    def set_translation(self, key: str, value: str, language: str = "en"):
        """Set translation for a key."""
        if language not in self._translations:
            self._translations[language] = {}

        self._translations[language][key] = value

    def get_translation(self, key: str, language: str = "en") -> str:
        """Get translation for a key."""
        if language in self._translations and key in self._translations[language]:
            return self._translations[language][key]

        # Fallback to English
        if (
            language != "en"
            and "en" in self._translations
            and key in self._translations["en"]
        ):
            return self._translations["en"][key]

        # Return key if no translation found
        return key

    def load_translations_from_file(self, file_path: str, language: str):
        """Load translations from JSON file."""
        try:
            with open(file_path, encoding="utf-8") as f:
                translations = json.load(f)
                for key, value in translations.items():
                    self.set_translation(key, value, language)

            logger.info(
                "Translations loaded",
                file_path=file_path,
                language=language,
                count=len(translations),
            )
        except Exception as e:
            logger.exception(
                "Failed to load translations", file_path=file_path, error=str(e)
            )


class AssetManager:
    """Manages portal assets like images, videos, and files."""

    def __init__(self, asset_dir: str = "assets"):
        self.asset_dir = Path(asset_dir)
        self.asset_dir.mkdir(exist_ok=True)

        # Create subdirectories
        self.images_dir = self.asset_dir / "images"
        self.videos_dir = self.asset_dir / "videos"
        self.documents_dir = self.asset_dir / "documents"

        for directory in [self.images_dir, self.videos_dir, self.documents_dir]:
            directory.mkdir(exist_ok=True)

        # Supported formats
        self.supported_image_formats = {
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".webp",
            ".svg",
        }
        self.supported_video_formats = {".mp4", ".webm", ".ogg", ".mov"}
        self.supported_document_formats = {".pdf", ".txt", ".html", ".css", ".js"}

    async def upload_image(
        self,
        image_data: bytes,
        filename: str,
        portal_id: str | None = None,
        optimize: bool = True,
        max_size: tuple = (1920, 1080),
    ) -> dict[str, Any]:
        """Upload and process image asset."""
        file_path = self._get_asset_path("images", filename, portal_id)

        # Validate file format
        file_ext = Path(filename).suffix.lower()
        if file_ext not in self.supported_image_formats:
            msg = f"Unsupported image format: {file_ext}"
            raise ValueError(msg)

        # Process image if optimization is enabled
        if optimize and file_ext in {".jpg", ".jpeg", ".png"}:
            image_data = self._optimize_image(image_data, max_size)

        # Save image
        with open(file_path, "wb") as f:
            f.write(image_data)

        # Generate metadata
        metadata = {
            "filename": filename,
            "file_path": str(file_path),
            "file_size": len(image_data),
            "format": file_ext,
            "portal_id": portal_id,
            "uploaded_at": datetime.now(UTC).isoformat(),
            "asset_url": self._generate_asset_url("images", filename, portal_id),
        }

        # Get image dimensions
        if file_ext in {".jpg", ".jpeg", ".png"}:
            try:
                with Image.open(file_path) as img:
                    metadata["width"] = img.width
                    metadata["height"] = img.height
            except (OSError, ValueError, AttributeError):
                pass

        logger.info(
            "Image uploaded",
            filename=filename,
            file_size=len(image_data),
            portal_id=portal_id,
        )

        return metadata

    async def upload_document(
        self,
        document_data: bytes,
        filename: str,
        portal_id: str | None = None,
    ) -> dict[str, Any]:
        """Upload document asset."""
        file_path = self._get_asset_path("documents", filename, portal_id)

        # Validate file format
        file_ext = Path(filename).suffix.lower()
        if file_ext not in self.supported_document_formats:
            msg = f"Unsupported document format: {file_ext}"
            raise ValueError(msg)

        # Save document
        with open(file_path, "wb") as f:
            f.write(document_data)

        metadata = {
            "filename": filename,
            "file_path": str(file_path),
            "file_size": len(document_data),
            "format": file_ext,
            "portal_id": portal_id,
            "uploaded_at": datetime.now(UTC).isoformat(),
            "asset_url": self._generate_asset_url("documents", filename, portal_id),
        }

        logger.info(
            "Document uploaded",
            filename=filename,
            file_size=len(document_data),
            portal_id=portal_id,
        )

        return metadata

    def get_asset_url(
        self,
        asset_type: str,
        filename: str,
        portal_id: str | None = None,
    ) -> str:
        """Get URL for an asset."""
        return self._generate_asset_url(asset_type, filename, portal_id)

    def delete_asset(
        self,
        asset_type: str,
        filename: str,
        portal_id: str | None = None,
    ) -> bool:
        """Delete an asset."""
        file_path = self._get_asset_path(asset_type, filename, portal_id)

        try:
            file_path.unlink()
            logger.info(
                "Asset deleted",
                asset_type=asset_type,
                filename=filename,
                portal_id=portal_id,
            )
            return True
        except FileNotFoundError:
            return False
        except (OSError, PermissionError) as e:
            logger.exception(
                "Failed to delete asset",
                error=str(e),
                asset_type=asset_type,
                filename=filename,
            )
            return False

    def _get_asset_path(
        self,
        asset_type: str,
        filename: str,
        portal_id: str | None = None,
    ) -> Path:
        """Get file path for an asset."""
        base_dir = self.asset_dir / asset_type

        if portal_id:
            base_dir = base_dir / portal_id
            base_dir.mkdir(exist_ok=True)

        return base_dir / filename

    def _generate_asset_url(
        self,
        asset_type: str,
        filename: str,
        portal_id: str | None = None,
    ) -> str:
        """Generate URL for an asset."""
        if portal_id:
            return f"/assets/{asset_type}/{portal_id}/{filename}"
        return f"/assets/{asset_type}/{filename}"

    def _optimize_image(self, image_data: bytes, max_size: tuple) -> bytes:
        """Optimize image size and quality."""
        try:
            with Image.open(BytesIO(image_data)) as img:
                # Convert to RGB if necessary
                if img.mode in ("RGBA", "LA", "P"):
                    img = img.convert("RGB")

                # Resize if larger than max_size
                img.thumbnail(max_size, Image.Resampling.LANCZOS)

                # Save optimized image
                output = BytesIO()
                img.save(output, format="JPEG", quality=85, optimize=True)
                return output.getvalue()
        except (OSError, ValueError, AttributeError) as e:
            logger.warning("Failed to optimize image", error=str(e))
            return image_data


class PortalCustomizer:
    """Main portal customization manager."""

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.themes: dict[str, Theme] = {}
        self.content_manager = ContentManager(config.get("template_dir", "templates"))
        self.asset_manager = AssetManager(config.get("asset_dir", "assets"))

        # Load default themes
        self._load_default_themes()

        # Default branding
        self.default_branding = BrandingConfig()

    def create_theme(
        self,
        name: str,
        theme_type: ThemeType = ThemeType.CUSTOM,
        **theme_config,
    ) -> Theme:
        """Create a new custom theme."""
        theme_id = str(uuid.uuid4())

        theme = Theme(
            theme_id=theme_id,
            name=name,
            theme_type=theme_type,
            **theme_config,
        )

        self.themes[theme_id] = theme

        logger.info(
            "Custom theme created",
            theme_id=theme_id,
            name=name,
            theme_type=theme_type.value,
        )

        return theme

    def get_theme(self, theme_id: str) -> Theme | None:
        """Get theme by ID."""
        return self.themes.get(theme_id)

    def list_themes(self) -> list[dict[str, Any]]:
        """List all available themes."""
        return [theme.to_dict() for theme in self.themes.values()]

    def generate_portal_html(
        self,
        template_name: str,
        theme_id: str,
        branding: BrandingConfig,
        context: dict[str, Any],
        language: str = "en",
    ) -> str:
        """Generate complete portal HTML."""
        theme = self.get_theme(theme_id)
        if not theme:
            theme = next(iter(self.themes.values()))  # Use first available theme

        # Prepare template context
        template_context = {
            "theme": theme.to_dict(),
            "branding": branding.to_dict(),
            "css": theme.generate_css(),
            "custom_js": theme.custom_js or "",
            **context,
        }

        # Render template
        try:
            return self.content_manager.render_template(
                template_name,
                template_context,
                language,
            )
        except Exception as e:
            logger.exception(
                "Failed to render portal template",
                template_name=template_name,
                theme_id=theme_id,
                error=str(e),
            )
            return self._generate_fallback_html(context)

    def update_portal_branding(
        self,
        portal_id: str,
        branding_updates: dict[str, Any],
    ) -> BrandingConfig:
        """Update portal branding configuration."""
        # In a real implementation, this would update the database
        updated_branding = BrandingConfig(**branding_updates)

        logger.info(
            "Portal branding updated",
            portal_id=portal_id,
            updates=list(branding_updates.keys()),
        )

        return updated_branding

    def _load_default_themes(self):
        """Load default themes."""
        # Default theme
        default_theme = Theme(
            theme_id="default",
            name="Default",
            theme_type=ThemeType.DEFAULT,
            description="Clean and simple default theme",
        )
        self.themes["default"] = default_theme

        # Corporate theme
        corporate_colors = ColorScheme(
            primary="#2c3e50",
            secondary="#34495e",
            background="#ecf0f1",
            text="#2c3e50",
        )
        corporate_typography = Typography(
            font_family="'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
            font_size_base="14px",
        )

        corporate_theme = Theme(
            theme_id="corporate",
            name="Corporate",
            theme_type=ThemeType.CORPORATE,
            colors=corporate_colors,
            typography=corporate_typography,
            description="Professional corporate theme",
        )
        self.themes["corporate"] = corporate_theme

        # Hospitality theme
        hospitality_colors = ColorScheme(
            primary="#d4a574",
            secondary="#8b6914",
            background="#f8f5f0",
            text="#5d4e37",
        )
        hospitality_layout = LayoutConfig(
            background_image="/assets/images/hospitality-bg.jpg",
            background_overlay=True,
            background_overlay_opacity=0.3,
        )

        hospitality_theme = Theme(
            theme_id="hospitality",
            name="Hospitality",
            theme_type=ThemeType.HOSPITALITY,
            colors=hospitality_colors,
            layout=hospitality_layout,
            description="Warm and welcoming hospitality theme",
        )
        self.themes["hospitality"] = hospitality_theme

        logger.info("Default themes loaded", count=len(self.themes))

    def _generate_fallback_html(self, context: dict[str, Any]) -> str:
        """Generate basic fallback HTML when template rendering fails."""
        return f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Guest Network Access</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 2rem; background: #f5f5f5; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; padding: 2rem; border-radius: 8px; }}
                .btn {{ background: #007bff; color: white; padding: 12px 24px; border: none; border-radius: 4px; cursor: pointer; }}
                .btn:hover {{ background: #0056b3; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Welcome to Guest Network</h1>
                <p>Please authenticate to access the internet.</p>
                {context.get('content', '')}
            </div>
        </body>
        </html>
        """
