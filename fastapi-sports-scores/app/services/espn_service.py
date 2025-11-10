import aiohttp
import asyncio
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class ESPNService:
    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self.base_url = "https://site.api.espn.com/apis/site/v2/sports"

    def _convert_venue_name(self, venue_name: str) -> str:
        """Convert specific venue names to custom names"""
        venue_conversions = {
            "Washington-Grizzly Stadium": "Eastern Idaho Shithole"
        }
        return venue_conversions.get(venue_name, venue_name)

    async def fetch_game_details(self, sport: str, event_id: str) -> Dict[str, Any]:
        """Fetch detailed game information for in-progress games"""
        url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/summary?event={event_id}"
        
        headers = {
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (compatible; Sports-API/1.0)"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Extract detailed status information
                        competitions = data.get('header', {}).get('competitions', [])
                        if competitions:
                            competition = competitions[0]
                            status = competition.get('status', {})
                            
                            return {
                                'period': status.get('displayPeriod'),
                                'clock': status.get('displayClock'),
                                'period_number': status.get('period'),
                                'type_detail': status.get('type', {}).get('detail')
                            }
                        
                        return {}
                    else:
                        print(f"Failed to fetch game details for {event_id}: HTTP {response.status}")
                        return {}
                        
        except Exception as e:
            print(f"Error processing event: {e}")
            return None

    async def _get_performers_from_summary(self, event_id: str, sport: str) -> List[Dict[str, Any]]:
        """Fetch live game performers from ESPN game summary endpoint"""
        url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/summary?event={event_id}"
        
        headers = {
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (compatible; Sports-API/1.0)"
        }
        
        performers = []
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # For football (NFL and college), get stats from boxscore.players
                        boxscore = data.get('boxscore', {})
                        players_data = boxscore.get('players', [])
                        
                        for team_players in players_data:
                            team_info = team_players.get('team', {})
                            team_name = team_info.get('displayName', 'Unknown')
                            original_team_abbr = team_info.get('abbreviation', 'UNK')
                            team_abbr = self._convert_team_abbreviation(original_team_abbr)
                            
                            statistics = team_players.get('statistics', [])
                            
                            # Focus on key offensive categories for top performers
                            key_categories = ['passing', 'rushing', 'receiving']
                            
                            for stat_category in statistics:
                                category_name = stat_category.get('name', '')
                                
                                if category_name in key_categories:
                                    athletes = stat_category.get('athletes', [])
                                    keys = stat_category.get('keys', [])
                                    
                                    # Get top performers in this category
                                    for athlete in athletes[:2]:  # Top 2 per category per team
                                        athlete_info = athlete.get('athlete', {})
                                        player_name = athlete_info.get('displayName', 'Unknown')
                                        stats = athlete.get('stats', [])
                                        
                                        if stats and len(stats) > 1:
                                            # Get the main stat (usually yards - index 1)
                                            main_stat_value = stats[1] if len(stats) > 1 else stats[0]
                                            
                                            # Skip if no meaningful stats
                                            if not main_stat_value or main_stat_value == '0' or main_stat_value == 0:
                                                continue
                                            
                                            # Convert to number if it's a string
                                            try:
                                                if isinstance(main_stat_value, str):
                                                    main_stat_value = float(main_stat_value)
                                            except (ValueError, TypeError):
                                                continue
                                            
                                            # Format stat description based on category
                                            if category_name == 'passing':
                                                stat_description = f"{main_stat_value} passing yards"
                                                stat_category_display = "Pass Yds"
                                            elif category_name == 'rushing':
                                                stat_description = f"{main_stat_value} rushing yards"
                                                stat_category_display = "Rush Yds"
                                            elif category_name == 'receiving':
                                                stat_description = f"{main_stat_value} receiving yards"
                                                stat_category_display = "Rec Yds"
                                            else:
                                                stat_description = f"{main_stat_value} {category_name}"
                                                stat_category_display = category_name.title()
                                            
                                            performer = {
                                                'player_name': player_name,
                                                'team': team_name,
                                                'team_abbr': team_abbr,
                                                'stat_category': stat_category_display,
                                                'value': main_stat_value,
                                                'description': stat_description
                                            }
                                            performers.append(performer)
                        
                        return performers[:8]  # Limit to top 8 performers
                    else:
                        print(f"Failed to fetch summary for {event_id}: HTTP {response.status}")
                        return []
                        
        except Exception as e:
            print(f"Error fetching summary performers for {event_id}: {e}")
            return []

    async def _enrich_with_detailed_status(self, scores, sport: str = "basketball/mens-college-basketball"):
        """Enrich in-progress games with detailed status information."""
        try:
            # Identify in-progress games
            in_progress_ids = [
                score['id'] for score in scores 
                if score['status'] in ['In Progress', 'Halftime', '2nd Half']  # Common in-progress statuses
            ]
            
            # Fetch detailed status for all in-progress games concurrently
            if in_progress_ids:
                detailed_statuses = await asyncio.gather(
                    *[self.fetch_game_details(sport, game_id) for game_id in in_progress_ids],
                    return_exceptions=True
                )
                
                # Create mapping of game_id to detailed status
                status_map = {}
                for i, status in enumerate(detailed_statuses):
                    if not isinstance(status, Exception) and status:
                        status_map[in_progress_ids[i]] = status
                
                # Update scores with detailed status
                for score in scores:
                    if score['id'] in status_map:
                        score['game_details'] = status_map[score['id']]
            
            return scores
        except Exception as e:
            print(f"Error enriching with detailed status: {e}")
            return scores

    def _build_team_data(self, competitor: dict) -> dict:
        """Build team data from ESPN competitor data"""
        # Get rank and convert 99 to None (99 means unranked)
        rank = competitor.get('curatedRank', {}).get('current') if competitor.get('curatedRank') else None
        if rank == 99:
            rank = None
        
        team_info = competitor.get('team', {})
        
        # Get original abbreviation and apply custom replacements
        original_abbreviation = team_info.get('abbreviation', 'UNK')
        abbreviation = self._convert_team_abbreviation(original_abbreviation)
        
        return {
            'name': team_info.get('displayName', 'Unknown'),  # Full team name (e.g., "Montana State Bobcats")
            'nickname': team_info.get('name', team_info.get('displayName', 'Unknown')),  # Team nickname (e.g., "Bobcats")
            'abbreviation': abbreviation,  # Team abbreviation with custom conversions
            'score': competitor.get('score', '0'),
            'conference': 'Unknown',  # Simplified - no longer trying to detect conference
            'rank': rank
        }
    
    def _convert_team_abbreviation(self, abbreviation: str) -> str:
        """Convert specific team abbreviations to custom versions"""
        abbreviation_conversions = {
            "MONT": "dUMb"
        }
        return abbreviation_conversions.get(abbreviation, abbreviation)

    async def fetch_scores(self, sport: str, limit: int = 10) -> List[Dict]:
        """Fetch scores from ESPN API"""
        url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/scoreboard"
        
        all_scores = []
        
        try:
            await self._fetch_from_endpoint(url, all_scores, limit)
        except Exception as e:
            print(f"Error fetching from {url}: {e}")
        
        # Remove duplicates based on game ID
        seen_ids = set()
        unique_scores = []
        for score in all_scores:
            if score['id'] not in seen_ids:
                seen_ids.add(score['id'])
                unique_scores.append(score)
        
        limited_scores = unique_scores[:limit]
        
        # Enrich in-progress games with detailed status
        enriched_scores = await self._enrich_with_detailed_status(limited_scores, sport)
        
        return enriched_scores
    
    async def fetch_conference_games(self, sport: str, group_id: int) -> List[Dict]:
        """Fetch games for a specific conference group from ESPN API"""
        url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/scoreboard?groups={group_id}"
        
        headers = {
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (compatible; Sports-API/1.0)"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    events = data.get('events', [])
                    
                    games = []
                    for event in events:
                        transformed_game = self._transform_event(event)
                        if transformed_game:
                            # Populate top_performers for the transformed game
                            transformed_game['top_performers'] = await self._get_top_performers(event, sport)
                            games.append(transformed_game)
                    
                    # Enrich in-progress games with detailed status
                    enriched_games = await self._enrich_with_detailed_status(games, sport)
                    
                    return enriched_games
                else:
                    print(f"ESPN API error for group {group_id}: {response.status}")
                    return []
    
    async def fetch_top25_games(self, sport: str, division: str = None) -> List[Dict]:
        """Fetch games involving top 25 teams using individual game summaries"""
        logger.info(f"Fetching top 25 games for {sport}")
        
        # First get all games from scoreboard
        scoreboard_url = f"http://site.api.espn.com/apis/site/v2/sports/{sport}/scoreboard"
        if division:
            scoreboard_url += f"?groups={division}"
            
        async with aiohttp.ClientSession() as session:
            async with session.get(scoreboard_url) as response:
                if response.status != 200:
                    logger.error(f"Failed to fetch scoreboard: {response.status}")
                    return []
                
                data = await response.json()
                games = data.get('events', [])
                
                # Check games directly from scoreboard for ranking info
                top25_games = []
                for game in games:
                    has_ranked_team = False
                    
                    # Check if any competitor is ranked in top 25
                    # Look in the scoreboard data for curatedRank.current
                    competitions = game.get('competitions', [])
                    for competition in competitions:
                        competitors = competition.get('competitors', [])
                        for competitor in competitors:
                            # Check for ranking in curatedRank.current (scoreboard API structure)
                            curated_rank = competitor.get('curatedRank', {})
                            rank = curated_rank.get('current') if curated_rank else None
                            
                            if rank is not None and isinstance(rank, int) and 1 <= rank <= 25 and rank != 99:
                                has_ranked_team = True
                                break
                        
                        if has_ranked_team:
                            break
                    
                    if has_ranked_team:
                        # Transform the game data
                        transformed_game = self._transform_event(game)
                        if transformed_game:
                            # Populate top_performers for the transformed game
                            transformed_game['top_performers'] = await self._get_top_performers(game, sport)
                            top25_games.append(transformed_game)
                
                logger.info(f"Found {len(top25_games)} top 25 games")
                return top25_games
    

    def _transform_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Transform ESPN event data to our standard format"""
        competitions = event.get('competitions', [])
        if not competitions:
            return None
            
        competition = competitions[0]
        competitors = competition.get('competitors', [])
        
        home_team = None
        away_team = None
        
        for competitor in competitors:
            team_data = self._build_team_data(competitor)
            
            if competitor.get('homeAway') == 'home':
                home_team = team_data
            elif competitor.get('homeAway') == 'away':
                away_team = team_data
        
        if not home_team or not away_team:
            return None
            
        return {
            'id': event.get('id'),
            'name': event.get('name', 'Unknown vs Unknown'),
            'date': event.get('date'),
            'status': competition.get('status', {}).get('type', {}).get('description', 'Unknown'),
            'home_team': home_team,
            'away_team': away_team,
            'venue': self._convert_venue_name(competition.get('venue', {}).get('fullName', 'Unknown Venue')),
            'top_performers': [],  # Will be populated separately for performance
            'game_details': None  # Will be populated for in-progress games
        }
    
    async def _fetch_from_endpoint(self, url: str, scores_list: List[Dict[str, Any]], limit: int):
        """Fetch scores from a specific endpoint and add to scores list"""
        headers = {
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (compatible; Sports-API/1.0)"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    events = data.get('events', [])
                    
                    # Transform the ESPN data to a simpler format
                    for event in events:
                        # Don't apply early limits in comprehensive mode - collect all games first
                        competitions = event.get('competitions', [])
                        if competitions:
                            competition = competitions[0]
                            competitors = competition.get('competitors', [])
                            
                            home_team = None
                            away_team = None
                            
                            for competitor in competitors:
                                if competitor.get('homeAway') == 'home':
                                    home_team = self._build_team_data(competitor)
                                elif competitor.get('homeAway') == 'away':
                                    away_team = self._build_team_data(competitor)
                            
                            score_data = {
                                'id': event.get('id'),
                                'name': event.get('name', 'Unknown vs Unknown'),
                                'date': event.get('date'),
                                'status': competition.get('status', {}).get('type', {}).get('description', 'Unknown'),
                                'home_team': home_team,
                                'away_team': away_team,
                                'venue': self._convert_venue_name(competition.get('venue', {}).get('fullName', 'Unknown Venue')),
                                'top_performers': await self._get_top_performers(event, url.split('/')[-2] + '/' + url.split('/')[-1].split('?')[0])
                            }
                            scores_list.append(score_data)
                else:
                    response.raise_for_status()

    async def _get_top_performers(self, event: Dict[str, Any], sport: str) -> List[Dict[str, Any]]:
        """Get top performers for a specific game"""
        performers = []
        
        try:
            # Check if the event has competitions and competitors with statistics
            competitions = event.get('competitions', [])
            if not competitions:
                return performers
                
            competition = competitions[0]
            competitors = competition.get('competitors', [])
            
            # For football games (NFL and college), always try to fetch detailed stats
            # from the game summary endpoint since football scoreboard often lacks comprehensive leaders data
            if 'football' in sport:
                status = competition.get('status', {}).get('type', {}).get('description', '')
                # Fetch detailed stats for in-progress games and recently finished games
                if status in ['In Progress', 'Halftime', '1st Quarter', '2nd Quarter', '3rd Quarter', '4th Quarter', 'Final']:
                    event_id = event.get('id')
                    if event_id:
                        # Use correct ESPN API sport format for summary endpoint
                        summary_sport = sport  # Keep the original sport format (football/nfl or football/college-football)
                        summary_performers = await self._get_performers_from_summary(event_id, summary_sport)
                        if summary_performers:
                            return summary_performers
            
            # Check if we have leaders data in the main response for other sports
            has_leaders = any(competitor.get('leaders', []) for competitor in competitors)
            
            # Process standard leaders data (works for most sports)
            for competitor in competitors:
                team_name = competitor.get('team', {}).get('displayName', 'Unknown')
                original_team_abbr = competitor.get('team', {}).get('abbreviation', 'UNK')
                team_abbr = self._convert_team_abbreviation(original_team_abbr)
                
                # Get leaders from competitor statistics
                leaders = competitor.get('leaders', [])
                
                for leader_category in leaders:
                    category_name = leader_category.get('name', 'Unknown')
                    display_name = leader_category.get('displayName', category_name)
                    short_display_name = leader_category.get('shortDisplayName', display_name)
                    
                    # Get the leaders in this category
                    category_leaders = leader_category.get('leaders', [])
                    
                    for leader in category_leaders[:1]:  # Take top performer in each category
                        athlete = leader.get('athlete', {})
                        player_name = athlete.get('displayName', 'Unknown Player')
                        value = leader.get('value', 0)
                        
                        # Skip internal rating stats and other non-user-friendly stats
                        if category_name.upper() in ['RAT', 'RATING', 'EFF', 'PER']:
                            continue
                        
                        # Format the stat based on sport and category
                        stat_description = self._format_stat_description(
                            sport, category_name, short_display_name, value
                        )
                        
                        performer = {
                            'player_name': player_name,
                            'team': team_name,
                            'team_abbr': team_abbr,
                            'stat_category': short_display_name,
                            'value': value,
                            'description': stat_description
                        }
                        performers.append(performer)
            
        except Exception as e:
            # If we can't get performer data, just return empty list
            print(f"Error getting performers for event {event.get('id', 'unknown')}: {e}")
        
        return performers
    
    def _format_stat_description(self, sport: str, category: str, display_name: str, value: float) -> str:
        """Format stat description based on sport and category"""
        try:
            # Convert value to appropriate format
            if isinstance(value, float) and value.is_integer():
                value = int(value)
            
            # Basketball stats
            if 'basketball' in sport.lower():
                if 'point' in category.lower() or 'scoring' in category.lower():
                    return f"{value} points"
                elif 'rebound' in category.lower():
                    return f"{value} rebounds"
                elif 'assist' in category.lower():
                    return f"{value} assists"
                elif 'steal' in category.lower():
                    return f"{value} steals"
                elif 'block' in category.lower():
                    return f"{value} blocks"
            
            # Football stats  
            elif 'football' in sport.lower():
                if 'passing' in category.lower() and 'yard' in category.lower():
                    return f"{value} passing yards"
                elif 'rushing' in category.lower() and 'yard' in category.lower():
                    return f"{value} rushing yards"
                elif 'receiving' in category.lower() and 'yard' in category.lower():
                    return f"{value} receiving yards"
                elif 'touchdown' in category.lower() or 'td' in category.lower():
                    return f"{value} touchdowns"
                elif 'sack' in category.lower():
                    return f"{value} sacks"
                elif 'interception' in category.lower():
                    return f"{value} interceptions"
            
            # Baseball stats
            elif 'baseball' in sport.lower():
                if 'hit' in category.lower():
                    return f"{value} hits"
                elif 'rbi' in category.lower():
                    return f"{value} RBIs"
                elif 'run' in category.lower():
                    return f"{value} runs"
                elif 'home run' in category.lower() or 'hr' in category.lower():
                    return f"{value} home runs"
                elif 'strikeout' in category.lower():
                    return f"{value} strikeouts"
            
            # Hockey stats
            elif 'hockey' in sport.lower():
                if 'goal' in category.lower():
                    return f"{value} goals"
                elif 'assist' in category.lower():
                    return f"{value} assists"
                elif 'save' in category.lower():
                    return f"{value} saves"
                elif 'shot' in category.lower():
                    return f"{value} shots"
            
            # Soccer stats
            elif 'soccer' in sport.lower():
                if 'goal' in category.lower():
                    return f"{value} goals"
                elif 'assist' in category.lower():
                    return f"{value} assists"
                elif 'save' in category.lower():
                    return f"{value} saves"
                elif 'shot' in category.lower():
                    return f"{value} shots"
            
            # Default formatting
            return f"{value} {display_name.lower()}"
            
        except Exception:
            return f"{value} {display_name.lower()}"