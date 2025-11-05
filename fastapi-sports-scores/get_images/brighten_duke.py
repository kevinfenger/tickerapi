#!/usr/bin/env python3

import os
from PIL import Image

def brighten_duke_logo():
    """Brighten the dark blue portions of the DUKE logo while preserving the design"""
    
    college_dir = "/app/get_images/sport_logos/college"
    original_path = os.path.join(college_dir, "DUKE.bmp")
    
    if not os.path.exists(original_path):
        print(f"Error: {original_path} not found!")
        return
    
    # Load the original image
    img = Image.open(original_path)
    img = img.convert('RGB')
    
    print("Analyzing original DUKE logo...")
    
    # Analyze the image to find the dark blue areas
    pixels = img.load()
    width, height = img.size
    
    # Collect all unique colors
    colors = set()
    for y in range(height):
        for x in range(width):
            colors.add(pixels[x, y])
    
    print(f"Found {len(colors)} unique colors in the logo:")
    for color in sorted(colors):
        print(f"  RGB{color} - Brightness: {sum(color)/3:.1f}")
    
    # Create brightened versions
    versions = []
    
    # Version 1: Convert very dark colors to bright blue
    img1 = img.copy()
    pixels1 = img1.load()
    
    for y in range(height):
        for x in range(width):
            r, g, b = pixels1[x, y]
            brightness = (r + g + b) / 3
            
            # If it's very dark (likely the logo), make it bright blue
            if brightness < 50:  # Very dark pixels
                pixels1[x, y] = (0, 100, 255)  # Bright blue
            elif brightness < 100:  # Medium dark pixels
                pixels1[x, y] = (0, 150, 255)  # Even brighter blue
    
    versions.append(("bright_blue", img1))
    
    # Version 2: More conservative brightening
    img2 = img.copy()
    pixels2 = img2.load()
    
    for y in range(height):
        for x in range(width):
            r, g, b = pixels2[x, y]
            brightness = (r + g + b) / 3
            
            # If it's dark, brighten it significantly
            if brightness < 80:
                # Multiply each channel by a factor to brighten
                factor = 150 / max(brightness, 1)  # Avoid division by zero
                new_r = min(255, int(r * factor))
                new_g = min(255, int(g * factor))
                new_b = min(255, int(b * factor))
                pixels2[x, y] = (new_r, new_g, new_b)
    
    versions.append(("brightened", img2))
    
    # Version 3: Make it Duke blue specifically
    img3 = img.copy()
    pixels3 = img3.load()
    
    duke_blue = (0, 83, 155)  # Official Duke blue (brighter version)
    light_duke_blue = (64, 127, 191)  # Even lighter Duke blue
    
    for y in range(height):
        for x in range(width):
            r, g, b = pixels3[x, y]
            brightness = (r + g + b) / 3
            
            if brightness < 30:  # Very dark - main logo
                pixels3[x, y] = duke_blue
            elif brightness < 80:  # Medium dark - secondary elements
                pixels3[x, y] = light_duke_blue
    
    versions.append(("duke_blue", img3))
    
    # Version 4: High contrast approach
    img4 = img.copy()
    pixels4 = img4.load()
    
    for y in range(height):
        for x in range(width):
            r, g, b = pixels4[x, y]
            brightness = (r + g + b) / 3
            
            if brightness < 60:  # Dark areas become bright blue
                pixels4[x, y] = (0, 150, 255)
            else:  # Light areas stay white
                pixels4[x, y] = (255, 255, 255)
    
    versions.append(("high_contrast", img4))
    
    # Save all versions
    for name, version in versions:
        output_path = os.path.join(college_dir, f"DUKE_{name}.bmp")
        version.save(output_path)
        print(f"✓ Created DUKE_{name}.bmp")
    
    print(f"\nCreated {len(versions)} brightened Duke logo versions!")
    print("Try these on your LED screen:")
    print("- DUKE_bright_blue.bmp (dark areas → bright blue)")
    print("- DUKE_brightened.bmp (proportional brightening)")
    print("- DUKE_duke_blue.bmp (official Duke blue colors)")
    print("- DUKE_high_contrast.bmp (blue/white only)")

if __name__ == "__main__":
    brighten_duke_logo()