#!/usr/bin/env python3

import requests
import os
from PIL import Image

def search_for_purdue():
    """Search for Purdue in the ESPN API by team ID and name"""
    
    print("Searching for Purdue in ESPN API...")
    
    # First, let's try some common team IDs for Purdue
    purdue_possible_ids = [96, 2509, 509, 196, 296]  # Common patterns for major universities
    
    found_teams = []
    
    # Search basketball first
    for team_id in range(1, 1000):  # Extended search
        try:
            url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/teams/{team_id}"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                team_data = data.get('team', {})
                
                if team_data:
                    name = team_data.get('displayName', '')
                    abbreviation = team_data.get('abbreviation', '')
                    
                    # Check if this is Purdue
                    if 'purdue' in name.lower() or 'pur' == abbreviation.upper():
                        found_teams.append({
                            'id': team_id,
                            'name': name,
                            'abbreviation': abbreviation,
                            'sport': 'basketball',
                            'logos': team_data.get('logos', [])
                        })
                        print(f"Found Purdue Basketball: ID {team_id}, Name: {name}, Abbr: {abbreviation}")
                        
        except Exception as e:
            continue
            
        # Print progress every 100 teams
        if team_id % 100 == 0:
            print(f"Searched {team_id}/1000 basketball teams...")
    
    # Search football too
    for team_id in range(1, 1000):
        try:
            url = f"https://site.api.espn.com/apis/site/v2/sports/football/college-football/teams/{team_id}"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                team_data = data.get('team', {})
                
                if team_data:
                    name = team_data.get('displayName', '')
                    abbreviation = team_data.get('abbreviation', '')
                    
                    # Check if this is Purdue
                    if 'purdue' in name.lower() or 'pur' == abbreviation.upper():
                        found_teams.append({
                            'id': team_id,
                            'name': name,
                            'abbreviation': abbreviation,
                            'sport': 'football',
                            'logos': team_data.get('logos', [])
                        })
                        print(f"Found Purdue Football: ID {team_id}, Name: {name}, Abbr: {abbreviation}")
                        
        except Exception as e:
            continue
            
        # Print progress every 100 teams
        if team_id % 100 == 0:
            print(f"Searched {team_id}/1000 football teams...")
    
    return found_teams

def download_purdue_logo(team_info):
    """Download and process the Purdue logo"""
    
    college_dir = "/app/get_images/sport_logos/college"
    
    if not team_info['logos']:
        print(f"No logos found for {team_info['name']}")
        return False
    
    logo_url = team_info['logos'][0]['href']
    abbreviation = team_info['abbreviation']
    
    print(f"Downloading {abbreviation} logo from {logo_url}")
    
    try:
        # Download the logo
        response = requests.get(logo_url, stream=True)
        if response.status_code != 200:
            print(f"Failed to download logo: HTTP {response.status_code}")
            return False
        
        # Save temporarily as PNG
        temp_png = os.path.join(college_dir, f"{abbreviation}_temp.png")
        with open(temp_png, 'wb') as file:
            for chunk in response.iter_content(chunk_size=1024):
                file.write(chunk)
        
        # Resize and convert to BMP
        with Image.open(temp_png) as img:
            img_resized = img.resize((32, 32))
            img_resized.save(temp_png)
            
            # Convert to BMP
            bmp_path = os.path.join(college_dir, f"{abbreviation}.bmp")
            img_resized = img_resized.convert('RGB')
            img_resized.save(bmp_path)
        
        # Remove temp PNG
        os.remove(temp_png)
        
        print(f"✓ Successfully saved {abbreviation}.bmp")
        return True
        
    except Exception as e:
        print(f"Error downloading logo: {e}")
        return False

def quick_purdue_search():
    """Quick search for common Purdue variations"""
    
    # Try direct API calls for known Purdue patterns
    possible_abbreviations = ['PUR', 'PURDUE', 'PURD']
    
    for abbr in possible_abbreviations:
        print(f"Trying direct search for {abbr}...")
        
        # Try basketball first
        for sport, league in [('basketball', 'mens-college-basketball'), ('football', 'college-football')]:
            try:
                # Try the teams endpoint to see if we can find it by name
                url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/teams"
                response = requests.get(url)
                
                if response.status_code == 200:
                    data = response.json()
                    teams = data.get('sports', [{}])[0].get('leagues', [{}])[0].get('teams', [])
                    
                    for team in teams:
                        team_data = team['team']
                        if 'purdue' in team_data.get('displayName', '').lower():
                            print(f"Found Purdue in {sport}: {team_data['displayName']} ({team_data['abbreviation']})")
                            return {
                                'name': team_data['displayName'],
                                'abbreviation': team_data['abbreviation'],
                                'sport': sport,
                                'logos': team_data.get('logos', [])
                            }
            except:
                continue
    
    return None

def main():
    print("Looking for Purdue logos...")
    
    # First try a quick search
    purdue = quick_purdue_search()
    
    if purdue:
        print(f"Found Purdue quickly: {purdue['name']}")
        success = download_purdue_logo(purdue)
        if success:
            print("✓ Purdue logo downloaded successfully!")
            return
    
    # If quick search fails, do comprehensive search
    print("Quick search failed, doing comprehensive search...")
    found_teams = search_for_purdue()
    
    if found_teams:
        print(f"\nFound {len(found_teams)} Purdue teams:")
        for team in found_teams:
            print(f"  - {team['name']} ({team['abbreviation']}) - {team['sport']}")
        
        # Download the first one found
        success = download_purdue_logo(found_teams[0])
        if success:
            print("✓ Purdue logo downloaded successfully!")
    else:
        print("❌ Could not find Purdue in ESPN API")

if __name__ == "__main__":
    main()