"""
Enhance LOGO.png to higher quality and clarity
"""
import os
from PIL import Image, ImageEnhance

# Source and destination paths
assets_dir = "assets"
logo_jpg = os.path.join(assets_dir, "LOGO.jpg")
logo_png = os.path.join(assets_dir, "LOGO.png")

def enhance_logo():
    """
    Load LOGO.jpg, upscale, enhance clarity, and save as high-quality PNG
    """
    if not os.path.exists(logo_jpg):
        print(f"❌ {logo_jpg} not found!")
        return
    
    print(f"📦 Loading {logo_jpg}...")
    img = Image.open(logo_jpg)
    original_size = img.size
    print(f"   Original size: {original_size}")
    
    # Convert to RGBA for transparency support
    img = img.convert('RGBA')
    
    # Upscale image using high-quality resampling (2x size)
    new_width = original_size[0] * 2
    new_height = original_size[1] * 2
    print(f"🔧 Upscaling to: {new_width}x{new_height}...")
    img_upscaled = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    # Enhance sharpness for clarity
    print(f"✨ Enhancing clarity...")
    enhancer = ImageEnhance.Sharpness(img_upscaled)
    img_enhanced = enhancer.enhance(1.5)  # 50% more sharp
    
    # Enhance color vibrancy
    print(f"🎨 Enhancing colors...")
    enhancer = ImageEnhance.Color(img_enhanced)
    img_enhanced = enhancer.enhance(1.2)  # 20% more vibrant
    
    # Enhance contrast for better definition
    print(f"🌟 Enhancing contrast...")
    enhancer = ImageEnhance.Contrast(img_enhanced)
    img_enhanced = enhancer.enhance(1.1)  # 10% more contrast
    
    # Save with highest quality
    print(f"💾 Saving high-quality PNG...")
    # PNG doesn't have quality parameter, but we save with full optimization
    img_enhanced.save(logo_png, 'PNG', optimize=False)
    
    new_size = os.path.getsize(logo_png) / 1024
    print(f"✅ Success! {logo_png} ({new_size:.2f} KB)")
    print(f"   Size increased: {original_size} → {new_width}x{new_height}")
    print(f"   Quality: Enhanced (sharper, vibrant, better contrast)")

if __name__ == "__main__":
    enhance_logo()
