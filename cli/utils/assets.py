"""
Asset generation utility for auto-deploy-stores.

Handles resizing and generating app icons, splash screens, and other assets.
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


def generate_app_icons(source_icon_path: Path, output_dir: Path) -> None:
    """Generate all required app icons from a source icon."""
    with Image.open(source_icon_path) as img:
        # Standard icon (1024x1024)
        icon = img.resize((1024, 1024), Image.Resampling.LANCZOS)
        icon.save(output_dir / "icon.png")
        
        # Adaptive icon (foreground)
        adaptive_foreground = img.resize((1024, 1024), Image.Resampling.LANCZOS)
        adaptive_foreground.save(output_dir / "adaptive-icon.png")
        
        # Favicon (48x48)
        favicon = img.resize((48, 48), Image.Resampling.LANCZOS)
        favicon.save(output_dir / "favicon.png")


def generate_splash_screens(source_icon_path: Path, output_dir: Path, app_name: str) -> None:
    """Generate splash screens from source icon."""
    # Create a white background splash screen (1242x2436)
    width, height = 1242, 2436
    splash = Image.new("RGB", (width, height), color="white")
    
    with Image.open(source_icon_path) as img:
        # Resize icon to fit in the middle
        icon_size = 400
        icon = img.resize((icon_size, icon_size), Image.Resampling.LANCZOS)
        
        # Paste icon in center
        x = (width - icon_size) // 2
        y = (height - icon_size) // 2 - 100 # Slightly above center
        
        # If icon has alpha, use it as mask
        if icon.mode == "RGBA":
            splash.paste(icon, (x, y), icon)
        else:
            splash.paste(icon, (x, y))
            
    splash.save(output_dir / "splash.png")
