#!/usr/bin/env python3

import requests
import os
from PIL import Image

def download_purdue_logo():
    """Download the Purdue logo from the provided URL"""
    
    logo_url = "https://a.espncdn.com/i/teamlogos/ncaa/500/2509.png"
    college_dir = "/app/get_images/sport_logos/college"
    
    print(f"Downloading Purdue logo from {logo_url}")
    
    try:
        # Download the logo
        response = requests.get(logo_url, stream=True)
        if response.status_code != 200:
            print(f"Failed to download logo: HTTP {response.status_code}")
            return False
        
        # Save temporarily as PNG
        temp_png = os.path.join(college_dir, "PUR_temp.png")
        with open(temp_png, 'wb') as file:
            for chunk in response.iter_content(chunk_size=1024):
                file.write(chunk)
        
        print("Downloaded PNG, converting to BMP...")
        
        # Resize and convert to BMP
        with Image.open(temp_png) as img:
            # Resize to 32x32 for LED display
            img_resized = img.resize((32, 32), Image.Resampling.LANCZOS)
            
            # Convert to RGB if needed (remove alpha channel)
            if img_resized.mode in ('RGBA', 'LA'):
                # Create white background
                background = Image.new('RGB', img_resized.size, (255, 255, 255))
                if img_resized.mode == 'RGBA':
                    background.paste(img_resized, mask=img_resized.split()[-1])  # Use alpha as mask
                else:
                    background.paste(img_resized)
                img_resized = background
            elif img_resized.mode != 'RGB':
                img_resized = img_resized.convert('RGB')
            
            # Save as BMP
            bmp_path = os.path.join(college_dir, "PUR.bmp")
            img_resized.save(bmp_path)
        
        # Remove temp PNG
        os.remove(temp_png)
        
        print(f"✓ Successfully saved PUR.bmp")
        
        # Check brightness (like we did for Duke)
        with Image.open(bmp_path) as img:
            # Convert to grayscale and get average brightness
            grayscale = img.convert('L')
            pixels = list(grayscale.getdata())
            avg_brightness = sum(pixels) / len(pixels)
            print(f"Average brightness: {avg_brightness:.1f}/255")
            
            if avg_brightness < 100:
                print("⚠️  Logo appears dark, might need brightening for LED display")
            else:
                print("✓ Logo brightness looks good for LED display")
        
        return True
        
    except Exception as e:
        print(f"Error downloading logo: {e}")
        return False

def main():
    print("Downloading Purdue logo (team ID 2509)...")
    success = download_purdue_logo()
    
    if success:
        print("✓ Purdue logo downloaded successfully!")
    else:
        print("❌ Failed to download Purdue logo")

if __name__ == "__main__":
    main()