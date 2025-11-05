#!/usr/bin/env python3

import requests
import os
import sys
import argparse
from PIL import Image
import math

# LED display optimization settings from get_images.py
GAMMA = 2.4
PASSTHROUGH = [(0, 0, 0)]  # Don't dither black

def process(filename, output_8_bit=True, passthrough=PASSTHROUGH):
    """Given a color image filename, load image and apply gamma correction
       and error-diffusion dithering while quantizing to 565 color
       resolution. If output_8_bit is True, image is reduced to 8-bit
       paletted mode after quantization/dithering. If passthrough (a list
       of 3-tuple RGB values) is provided, dithering won't be applied to
       colors in the provided list, they'll be quantized only (allows areas
       of the image to remain clean and dither-free).
    """
    img = Image.open(filename).convert('RGB')
    err_next_pixel = (0, 0, 0)
    err_next_row = [(0, 0, 0) for _ in range(img.size[0])]
    for row in range(img.size[1]):
        for column in range(img.size[0]):
            pixel = img.getpixel((column, row))
            want = (math.pow(pixel[0] / 255.0, GAMMA) * 31.0,
                    math.pow(pixel[1] / 255.0, GAMMA) * 63.0,
                    math.pow(pixel[2] / 255.0, GAMMA) * 31.0)
            if pixel in passthrough:
                got = (pixel[0] >> 3,
                       pixel[1] >> 2,
                       pixel[2] >> 3)
            else:
                got = (min(max(int(err_next_pixel[0] * 0.5 +
                                   err_next_row[column][0] * 0.25 +
                                   want[0] + 0.5), 0), 31),
                       min(max(int(err_next_pixel[1] * 0.5 +
                                   err_next_row[column][1] * 0.25 +
                                   want[1] + 0.5), 0), 63),
                       min(max(int(err_next_pixel[2] * 0.5 +
                                   err_next_row[column][2] * 0.25 +
                                   want[2] + 0.5), 0), 31))
            err_next_pixel = (want[0] - got[0],
                              want[1] - got[1],
                              want[2] - got[2])
            err_next_row[column] = err_next_pixel
            rgb565 = ((got[0] << 3) | (got[0] >> 2),
                      (got[1] << 2) | (got[1] >> 4),
                      (got[2] << 3) | (got[2] >> 2))
            img.putpixel((column, row), rgb565)

    if output_8_bit:
        img = img.convert('P', palette=Image.ADAPTIVE)

    img.save(filename.split('.')[0] + '.bmp')

def analyze_brightness(image_path):
    """Analyze the brightness of an image"""
    try:
        with Image.open(image_path) as img:
            # Convert to grayscale and get average brightness
            grayscale = img.convert('L')
            pixels = list(grayscale.getdata())
            avg_brightness = sum(pixels) / len(pixels)
            return avg_brightness
    except Exception as e:
        print(f"Error analyzing brightness: {e}")
        return None

def process_image_for_led(input_path, resize_to_32=True, backup_original=True):
    """Process any image file for LED display optimization"""
    
    if not os.path.exists(input_path):
        print(f"❌ Error: File not found: {input_path}")
        return False
    
    print(f"Processing {input_path} for LED display...")
    
    try:
        # Get file info
        file_dir = os.path.dirname(input_path)
        file_name = os.path.basename(input_path)
        name_without_ext = os.path.splitext(file_name)[0]
        
        # Analyze original brightness
        original_brightness = analyze_brightness(input_path)
        if original_brightness:
            print(f"Original brightness: {original_brightness:.1f}/255")
        
        # Create backup if requested
        if backup_original:
            backup_path = os.path.join(file_dir, f"{name_without_ext}_original.bmp")
            if not os.path.exists(backup_path):
                with Image.open(input_path) as img:
                    img.save(backup_path)
                print(f"✓ Backup saved as {backup_path}")
        
        # Convert to PNG for processing (if not already)
        temp_png = os.path.join(file_dir, f"{name_without_ext}_temp.png")
        
        with Image.open(input_path) as img:
            # Resize if requested
            if resize_to_32 and img.size != (32, 32):
                print(f"Resizing from {img.size} to (32, 32)...")
                img = img.resize((32, 32), Image.Resampling.LANCZOS)
            
            # Convert to RGB if needed
            if img.mode != 'RGB':
                if img.mode in ('RGBA', 'LA'):
                    # Create white background for transparency
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'RGBA':
                        background.paste(img, mask=img.split()[-1])
                    else:
                        background.paste(img)
                    img = background
                else:
                    img = img.convert('RGB')
            
            # Save as temporary PNG
            img.save(temp_png)
        
        print("Applying gamma correction and error-diffusion dithering...")
        
        # Apply the LED optimization process
        process(temp_png)
        
        # Remove temporary PNG
        os.remove(temp_png)
        
        # Check final result
        final_bmp = os.path.join(file_dir, f"{name_without_ext}.bmp")
        final_brightness = analyze_brightness(final_bmp)
        
        if final_brightness:
            print(f"Final brightness: {final_brightness:.1f}/255")
            if original_brightness and final_brightness:
                brightness_change = final_brightness - original_brightness
                if brightness_change > 5:
                    print(f"✓ Brightness increased by {brightness_change:.1f}")
                elif brightness_change < -5:
                    print(f"⚠️  Brightness decreased by {abs(brightness_change):.1f}")
                else:
                    print(f"→ Brightness change: {brightness_change:+.1f}")
        
        print(f"✓ Successfully processed {final_bmp} for LED display")
        return True
        
    except Exception as e:
        print(f"❌ Error processing image: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Process images for LED display optimization')
    parser.add_argument('input_path', help='Path to input image file')
    parser.add_argument('--no-resize', action='store_true', help='Skip resizing to 32x32')
    parser.add_argument('--no-backup', action='store_true', help='Skip creating backup of original')
    
    args = parser.parse_args()
    
    success = process_image_for_led(
        args.input_path, 
        resize_to_32=not args.no_resize,
        backup_original=not args.no_backup
    )
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()