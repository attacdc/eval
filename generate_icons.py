"""
Generate PWA icons for HumanEval
"""
try:
    from PIL import Image, ImageDraw, ImageFont
    import os
    
    def create_icon(size, filename):
        """Create a simple icon with HE text"""
        img = Image.new('RGB', (size, size), color='#2196F3')
        draw = ImageDraw.Draw(img)
        
        # Draw a white circle
        margin = size // 10
        draw.ellipse([margin, margin, size - margin, size - margin], fill='white')
        
        # Draw text
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size // 3)
        except:
            try:
                font = ImageFont.load_default()
            except:
                font = None
        
        text = "HE"
        if font:
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        else:
            text_width, text_height = size // 3, size // 3
        
        position = ((size - text_width) // 2, (size - text_height) // 2 - size // 20)
        draw.text(position, text, fill='#2196F3', font=font)
        
        img.save(filename)
        print(f"Created {filename}")
    
    # Create icons directory if it doesn't exist
    os.makedirs('static', exist_ok=True)
    
    # Generate icons
    create_icon(192, 'static/icon-192.png')
    create_icon(512, 'static/icon-512.png')
    
    print("Icons generated successfully!")
    
except ImportError:
    print("PIL (Pillow) not available. Install it with: pip install Pillow")
    print("Or manually add icon-192.png and icon-512.png to the static/ directory")
