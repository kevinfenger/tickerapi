#!/usr/bin/env python3
"""
Script to search for Montana State in ESPN college football groups
"""
import asyncio
import aiohttp
import json
import sys

async def search_group(session, group_id):
    """Search a specific ESPN group for Montana State"""
    url = f"https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard"
    params = {"groups": group_id}
    
    try:
        async with session.get(url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                
                # Check if there are any games
                events = data.get('events', [])
                montana_state_games = []
                
                for event in events:
                    competitors = event.get('competitions', [{}])[0].get('competitors', [])
                    
                    for competitor in competitors:
                        team = competitor.get('team', {})
                        name = team.get('name', '').lower()
                        display_name = team.get('displayName', '').lower()
                        
                        if 'montana state' in name or 'montana state' in display_name:
                            montana_state_games.append({
                                'group_id': group_id,
                                'game_id': event.get('id'),
                                'game_name': event.get('name'),
                                'date': event.get('date'),
                                'status': event.get('status', {}).get('type', {}).get('description'),
                                'teams': [comp.get('team', {}).get('displayName') for comp in competitors]
                            })
                            break
                
                if montana_state_games:
                    print(f"✅ Group {group_id}: Found {len(montana_state_games)} Montana State game(s)")
                    for game in montana_state_games:
                        print(f"   - {game['game_name']} ({game['status']}) - {game['date']}")
                    return montana_state_games
                else:
                    print(f"❌ Group {group_id}: No Montana State games found ({len(events)} total games)")
                    return []
                    
            else:
                print(f"⚠️  Group {group_id}: HTTP {response.status}")
                return []
                
    except Exception as e:
        print(f"🔥 Group {group_id}: Error - {e}")
        return []

async def main():
    """Search through multiple ESPN groups for Montana State football"""
    print("🔍 Searching ESPN groups for Montana State college football...")
    print("=" * 60)
    
    # Search groups 1-50 (common range for college conferences)
    groups_to_search = range(1, 51)
    
    all_montana_state_games = []
    
    async with aiohttp.ClientSession() as session:
        # Search groups sequentially to avoid overwhelming ESPN's API
        for group_id in groups_to_search:
            games = await search_group(session, group_id)
            all_montana_state_games.extend(games)
            
            # Small delay to be respectful to ESPN's API
            await asyncio.sleep(0.1)
    
    print("\n" + "=" * 60)
    print(f"🏈 SUMMARY: Found Montana State in {len(set(game['group_id'] for game in all_montana_state_games))} groups")
    
    # Group by group_id for summary
    groups_with_montana_state = {}
    for game in all_montana_state_games:
        group_id = game['group_id']
        if group_id not in groups_with_montana_state:
            groups_with_montana_state[group_id] = []
        groups_with_montana_state[group_id].append(game)
    
    for group_id, games in groups_with_montana_state.items():
        print(f"\n📍 Group {group_id}:")
        for game in games:
            print(f"   • {game['game_name']}")
            print(f"     Status: {game['status']}")
            print(f"     Date: {game['date']}")
            print(f"     Teams: {' vs '.join(game['teams'])}")

if __name__ == "__main__":
    asyncio.run(main())