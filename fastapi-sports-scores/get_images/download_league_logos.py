#!/usr/bin/env python3

import requests
import os
from PIL import Image
import math

# LED display optimization settings from get_images.py
GAMMA = 2.4
PASSTHROUGH = [(0, 0, 0)]  # Don't dither black

def process(filename, output_8_bit=True, passthrough=PASSTHROUGH):
    """Apply LED optimization process"""
    try:
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
            try:
                img = img.convert('P', palette=Image.ADAPTIVE)
            except Exception as e:
                print(f"Warning: Could not convert to 8-bit palette: {e}")
                # Continue with RGB version

        img.save(filename.split('.')[0] + '.bmp')
        
    except Exception as e:
        print(f"Error processing image {filename}: {e}")
        # Fallback: simple resize and save
        try:
            simple_img = Image.open(filename).convert('RGB')
            simple_img.save(filename.split('.')[0] + '.bmp')
            print(f"Saved simple version of {filename}")
        except Exception as fallback_error:
            print(f"Fallback also failed: {fallback_error}")
            raise

def download_league_logo(name, url, directory):
    """Download and process a league logo"""
    
    print(f"Downloading {name} logo...")
    
    try:
        # Create directory if it doesn't exist
        os.makedirs(directory, exist_ok=True)
        
        # Download the logo
        img_path_png = os.path.join(directory, f"{name}.png")
        response = requests.get(url, stream=True)
        if response.status_code != 200:
            print(f"Failed to download {name} logo: HTTP {response.status_code}")
            return False
            
        with open(img_path_png, 'wb') as file:
            for chunk in response.iter_content(chunk_size=1024):
                file.write(chunk)

        print(f"Downloaded {name}, resizing to 32x32...")
        
        # Resize and process
        with Image.open(img_path_png) as the_img:
            img_resized = the_img.resize((32, 32), Image.Resampling.LANCZOS)
            img_resized.save(img_path_png)
            
            print(f"Processing {name} with LED optimization...")
            process(img_path_png)

        # Delete the temporary PNG
        os.remove(img_path_png)
        
        print(f"✓ Successfully processed {name}.bmp")
        return True
        
    except Exception as e:
        print(f"Error processing {name} logo: {e}")
        return False

def main():
    base_dir = "/app/get_images/sport_logos"
    
    # League logos with high-quality sources
    league_logos = [
        {
            "name": "NBA",
            "url": "https://logoeps.com/wp-content/uploads/2013/03/nba-vector-logo.png",
            "directory": os.path.join(base_dir, "leagues")
        },
        {
            "name": "NFL", 
            "url": "https://logos-world.net/wp-content/uploads/2020/06/NFL-Logo.png",
            "directory": os.path.join(base_dir, "leagues")
        },
        {
            "name": "NHL",
            "url": "https://logos-world.net/wp-content/uploads/2020/06/NHL-Logo.png", 
            "directory": os.path.join(base_dir, "leagues")
        },
        {
            "name": "NCAA",
            "url": "https://logos-world.net/wp-content/uploads/2020/06/NCAA-Logo.png",
            "directory": os.path.join(base_dir, "leagues")
        },
        {
            "name": "MLB",
            "url": "https://logos-world.net/wp-content/uploads/2020/04/MLB-Logo.png",
            "directory": os.path.join(base_dir, "leagues")
        },
        {
            "name": "MLS",
            "url": "https://logos-world.net/wp-content/uploads/2020/06/MLS-Logo.png",
            "directory": os.path.join(base_dir, "leagues")
        }
    ]
    
    print("Downloading and processing league logos for LED display...")
    
    successful = 0
    for league in league_logos:
        if download_league_logo(league["name"], league["url"], league["directory"]):
            successful += 1
        print()  # Empty line for readability
    
    print(f"✓ Successfully processed {successful}/{len(league_logos)} league logos!")
    print(f"League logos saved to: {os.path.join(base_dir, 'leagues')}")

if __name__ == "__main__":
    main()