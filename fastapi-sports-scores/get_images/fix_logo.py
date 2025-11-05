#!/usr/bin/env python3

import os
import sys
from PIL import Image, ImageEnhance, ImageOps

def analyze_logo(logo_path):
    """Analyze the logo and print statistics"""
    try:
        img = Image.open(logo_path)
        print(f"Analyzing {logo_path}:")
        print(f"  Size: {img.size}")
        print(f"  Mode: {img.mode}")
        
        if img.mode == 'P':
            # Get palette colors
            palette = img.getpalette()
            if palette:
                # Convert palette to RGB tuples
                rgb_palette = [(palette[i], palette[i+1], palette[i+2]) 
                             for i in range(0, len(palette), 3)]
                unique_colors = len(set(rgb_palette))
                print(f"  Palette colors: {unique_colors}")
        
        # Convert to RGB for analysis
        rgb_img = img.convert('RGB')
        pixels = list(rgb_img.getdata())
        unique_pixels = set(pixels)
        print(f"  Unique RGB colors: {len(unique_pixels)}")
        
        # Check for low contrast
        gray_img = rgb_img.convert('L')
        pixel_values = list(gray_img.getdata())
        brightness_range = max(pixel_values) - min(pixel_values)
        avg_brightness = sum(pixel_values) / len(pixel_values)
        print(f"  Brightness range: {brightness_range} (0-255)")
        print(f"  Average brightness: {avg_brightness:.1f}")
        
        if brightness_range < 100:
            print("  ⚠️  LOW CONTRAST detected!")
        
        return rgb_img
        
    except Exception as e:
        print(f"Error analyzing {logo_path}: {e}")
        return None

def enhance_logo(img, output_path, method="contrast"):
    """Enhance logo for better LED display"""
    try:
        if method == "contrast":
            # Increase contrast
            enhancer = ImageEnhance.Contrast(img)
            enhanced = enhancer.enhance(2.0)  # Double the contrast
            
        elif method == "brightness":
            # Adjust brightness
            enhancer = ImageEnhance.Brightness(img)
            enhanced = enhancer.enhance(1.2)  # 20% brighter
            
        elif method == "high_contrast":
            # Convert to high contrast B&W
            gray = img.convert('L')
            # Use adaptive threshold
            threshold = 128
            enhanced = gray.point(lambda x: 255 if x > threshold else 0, mode='1')
            enhanced = enhanced.convert('RGB')
            
        elif method == "blue_white":
            # Duke specific: enhance blue and white
            pixels = img.load()
            width, height = img.size
            
            for y in range(height):
                for x in range(width):
                    r, g, b = pixels[x, y]
                    
                    # If it's bluish, make it pure blue
                    if b > r and b > g and b > 100:
                        pixels[x, y] = (0, 0, 255)  # Pure blue
                    # If it's light, make it pure white
                    elif r + g + b > 400:
                        pixels[x, y] = (255, 255, 255)  # Pure white
                    # If it's dark, make it black
                    else:
                        pixels[x, y] = (0, 0, 0)  # Pure black
            
            enhanced = img
            
        elif method == "quantize":
            # Reduce to specific LED-friendly colors
            led_colors = [
                (0, 0, 0),        # Black
                (255, 255, 255),  # White
                (0, 0, 255),      # Blue
                (255, 0, 0),      # Red
                (0, 255, 0),      # Green
                (255, 255, 0),    # Yellow
            ]
            
            # Convert each pixel to nearest LED color
            pixels = img.load()
            width, height = img.size
            
            for y in range(height):
                for x in range(width):
                    r, g, b = pixels[x, y]
                    
                    # Find closest LED color
                    min_distance = float('inf')
                    closest_color = (0, 0, 0)
                    
                    for led_r, led_g, led_b in led_colors:
                        distance = ((r - led_r) ** 2 + (g - led_g) ** 2 + (b - led_b) ** 2) ** 0.5
                        if distance < min_distance:
                            min_distance = distance
                            closest_color = (led_r, led_g, led_b)
                    
                    pixels[x, y] = closest_color
            
            enhanced = img
        
        # Save enhanced version
        enhanced.save(output_path)
        print(f"Enhanced logo saved to: {output_path}")
        return enhanced
        
    except Exception as e:
        print(f"Error enhancing logo: {e}")
        return None

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 fix_logo.py <logo_name> [method]")
        print("Methods: contrast, brightness, high_contrast, blue_white, quantize")
        print("Example: python3 fix_logo.py DUKE contrast")
        return
    
    logo_name = sys.argv[1].upper()
    method = sys.argv[2] if len(sys.argv) > 2 else "blue_white"
    
    # Path to the logo
    logo_path = f"get_images/sport_logos/college/{logo_name}.bmp"
    
    if not os.path.exists(logo_path):
        print(f"Logo not found: {logo_path}")
        return
    
    # Analyze original
    print("=== ORIGINAL LOGO ===")
    original_img = analyze_logo(logo_path)
    
    if original_img:
        # Create enhanced versions
        print(f"\n=== ENHANCING WITH METHOD: {method} ===")
        output_path = f"get_images/sport_logos/college/{logo_name}_fixed_{method}.bmp"
        enhanced_img = enhance_logo(original_img, output_path, method)
        
        if enhanced_img:
            print("\n=== ENHANCED LOGO ===")
            analyze_logo(output_path)
            
            # Also create all methods for comparison
            methods = ["contrast", "brightness", "high_contrast", "blue_white", "quantize"]
            print(f"\nCreating all enhancement methods for comparison...")
            for m in methods:
                if m != method:  # Skip the one we already created
                    out_path = f"get_images/sport_logos/college/{logo_name}_fixed_{m}.bmp"
                    enhance_logo(original_img, out_path, m)
            
            print(f"\nAll enhanced versions created! Test them on your LED screen:")
            for m in methods:
                print(f"  - {logo_name}_fixed_{m}.bmp")

if __name__ == "__main__":
    main()