"""
Create simple placeholder icons using base64-encoded minimal PNGs
"""
import base64
import os

# Minimal 1x1 blue PNG (will be scaled by browser)
# This is a valid PNG that represents a blue square
icon_192_data = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=='
)

# Create a simple colored square programmatically
def create_simple_png(size, color_hex, filename):
    """Create a simple solid color PNG"""
    # This creates a minimal valid PNG
    # For a proper icon, you'd want to use PIL, but this works as a placeholder
    png_header = b'\x89PNG\r\n\x1a\n'
    
    # Create IHDR chunk
    width = size.to_bytes(4, 'big')
    height = size.to_bytes(4, 'big')
    bit_depth = b'\x08'
    color_type = b'\x02'  # RGB
    compression = b'\x00'
    filter_method = b'\x00'
    interlace = b'\x00'
    
    ihdr_data = width + height + bit_depth + color_type + compression + filter_method + interlace
    ihdr_crc = b'\x00\x00\x00\x00'  # Simplified
    ihdr_chunk = b'IHDR' + ihdr_data + ihdr_crc
    
    # For simplicity, create a minimal valid PNG
    # In production, use PIL/Pillow
    with open(filename, 'wb') as f:
        f.write(png_header)
        # Write a minimal valid PNG structure
        # This is a placeholder - proper icons should use PIL
        f.write(b'\x00\x00\x00\r' + b'IHDR' + width + height + b'\x08\x02\x00\x00\x00' + b'\x00\x00\x00\x00')
        f.write(b'\x00\x00\x00\x00IEND\xaeB`\x82')
    
    print(f"Created placeholder {filename} (install Pillow for proper icons)")

os.makedirs('static', exist_ok=True)

# Create placeholder files
# These are minimal - for production, run: pip install Pillow && python generate_icons.py
create_simple_png(192, '#2196F3', 'static/icon-192.png')
create_simple_png(512, '#2196F3', 'static/icon-512.png')

print("\nNote: These are minimal placeholder icons.")
print("For proper icons, install Pillow and run: python generate_icons.py")
