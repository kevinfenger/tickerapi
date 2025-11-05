#!/usr/bin/env python3

import os
from PIL import Image, ImageDraw, ImageFont

def create_duke_logo():
    """Create a simple, high-contrast DUKE logo that will work on LED screens"""
    
    # Create a 32x32 image with white background
    img = Image.new('RGB', (32, 32), 'white')
    draw = ImageDraw.Draw(img)
    
    # Duke's colors: Duke Blue (#012169) and white
    duke_blue = (1, 33, 105)  # Official Duke blue
    white = (255, 255, 255)
    
    # Method 1: Simple text-based logo
    try:
        # Try to use a built-in font
        font = ImageFont.load_default()
        
        # Draw "DUKE" text in Duke blue
        text = "DUKE"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Center the text
        x = (32 - text_width) // 2
        y = (32 - text_height) // 2
        
        draw.text((x, y), text, fill=duke_blue, font=font)
        
    except:
        # Fallback: Create a simple geometric logo
        # Draw a blue "D" shape
        draw.rectangle([4, 8, 12, 24], fill=duke_blue)  # Vertical bar
        draw.ellipse([12, 8, 28, 24], outline=duke_blue, width=2)  # Curved part
        
        # Add "UKE" below
        draw.rectangle([14, 26, 16, 28], fill=duke_blue)  # U left
        draw.rectangle([18, 26, 20, 28], fill=duke_blue)  # U right
        draw.rectangle([14, 28, 20, 30], fill=duke_blue)  # U bottom
        
        draw.rectangle([22, 26, 24, 30], fill=duke_blue)  # K vertical
        draw.rectangle([24, 27, 26, 28], fill=duke_blue)  # K middle
        draw.rectangle([25, 26, 27, 27], fill=duke_blue)  # K top
        draw.rectangle([25, 29, 27, 30], fill=duke_blue)  # K bottom
    
    return img

def create_alternative_duke_logos():
    """Create several alternative Duke logos with different approaches"""
    
    logos = []
    
    # Version 1: Blue background with white "D"
    img1 = Image.new('RGB', (32, 32), (1, 33, 105))  # Duke blue background
    draw1 = ImageDraw.Draw(img1)
    
    # Draw a large white "D"
    draw1.rectangle([8, 4, 12, 28], fill='white')  # Vertical bar
    draw1.ellipse([12, 4, 24, 16], outline='white', width=2)  # Top curve
    draw1.ellipse([12, 16, 24, 28], outline='white', width=2)  # Bottom curve
    
    logos.append(("duke_blue_bg", img1))
    
    # Version 2: High contrast black and white
    img2 = Image.new('RGB', (32, 32), 'white')
    draw2 = ImageDraw.Draw(img2)
    
    # Create a bold "D" in black
    draw2.rectangle([6, 2, 10, 30], fill='black')  # Vertical bar
    draw2.ellipse([10, 2, 26, 18], outline='black', width=3)  # Top curve
    draw2.ellipse([10, 14, 26, 30], outline='black', width=3)  # Bottom curve
    
    logos.append(("duke_bw", img2))
    
    # Version 3: Simple block letters
    img3 = Image.new('RGB', (32, 32), 'white')
    draw3 = ImageDraw.Draw(img3)
    
    # Draw "DUKE" in simple block letters
    # D
    draw3.rectangle([2, 8, 4, 24], fill='black')
    draw3.rectangle([4, 8, 8, 10], fill='black')
    draw3.rectangle([4, 22, 8, 24], fill='black')
    draw3.rectangle([8, 10, 10, 22], fill='black')
    
    # U
    draw3.rectangle([12, 8, 14, 22], fill='black')
    draw3.rectangle([18, 8, 20, 22], fill='black')
    draw3.rectangle([14, 22, 18, 24], fill='black')
    
    # K
    draw3.rectangle([22, 8, 24, 24], fill='black')
    draw3.rectangle([24, 14, 26, 16], fill='black')
    draw3.rectangle([26, 12, 28, 14], fill='black')
    draw3.rectangle([26, 18, 28, 20], fill='black')
    
    # E
    draw3.rectangle([2, 26, 4, 32], fill='black')
    draw3.rectangle([4, 26, 8, 28], fill='black')
    draw3.rectangle([4, 28, 6, 30], fill='black')
    draw3.rectangle([4, 30, 8, 32], fill='black')
    
    logos.append(("duke_block", img3))
    
    return logos

def main():
    # Path to the college logos directory
    college_dir = "/app/get_images/sport_logos/college"
    
    print("Creating improved DUKE logos...")
    
    # Create the main improved logo
    improved_logo = create_duke_logo()
    improved_logo.save(os.path.join(college_dir, "DUKE_improved.bmp"))
    print(f"✓ Created DUKE_improved.bmp")
    
    # Create alternative versions
    alternatives = create_alternative_duke_logos()
    
    for name, logo in alternatives:
        filename = f"DUKE_{name}.bmp"
        logo.save(os.path.join(college_dir, filename))
        print(f"✓ Created {filename}")
    
    print(f"\nCreated {len(alternatives) + 1} Duke logo variations!")
    print("Test these on your LED screen:")
    print("- DUKE_improved.bmp (text-based)")
    print("- DUKE_blue_bg.bmp (blue background)")
    print("- DUKE_bw.bmp (high contrast black/white)")
    print("- DUKE_block.bmp (block letters)")
    
    # Also create a simple white logo as backup
    simple_white = Image.new('RGB', (32, 32), 'white')
    draw = ImageDraw.Draw(simple_white)
    draw.rectangle([10, 10, 22, 22], fill='black')
    draw.text((14, 14), "D", fill='white')
    simple_white.save(os.path.join(college_dir, "DUKE_simple.bmp"))
    print("- DUKE_simple.bmp (minimal design)")

if __name__ == "__main__":
    main()