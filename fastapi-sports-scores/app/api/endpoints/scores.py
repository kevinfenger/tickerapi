from fastapi import APIRouter, HTTPException, Query, Request
from typing import List, Dict, Any
from datetime import datetime, timezone, timedelta
from app.services.espn_service import ESPNService
from app.core.cache import Cache

router = APIRouter()
espn_service = ESPNService()
cache = Cache()

def get_sport_priority(sport: str) -> int:
    """Define sport priority for grouping (lower number = higher priority)"""
    sport_priorities = {
        'basketball/mens-college-basketball': 1,  # CBB first
        'basketball/nba': 2,                      # NBA second
        'football/college-football': 3,           # College Football
        'football/nfl': 4,                        # NFL
        'hockey/nhl': 5,                          # NHL
        'baseball/mlb': 6,                        # MLB
        'soccer/eng.1': 7,                        # Soccer leagues
        'soccer/usa.1': 8,
    }
    return sport_priorities.get(sport, 999)  # Default high number for unknown sports

def is_game_in_live_window(game_date: datetime, status: str, current_time: datetime) -> bool:
    """
    Check if a game should be included in the live endpoint.
    
    Args:
        game_date: The game's start time (UTC)
        status: The game's status (e.g., 'final', 'scheduled', 'in progress')
        current_time: Current UTC time
    
    Returns:
        True if the game should be included in live results
    """
    # Use 12 hours for final games since we only have start time, not end time
    twelve_hours_ago = current_time - timedelta(hours=12)
    
    # For scheduled games, include games within the next 18 hours (to account for US timezones)
    # This ensures we capture games that are "today" in US timezones even if they're tomorrow in UTC
    eighteen_hours_from_now = current_time + timedelta(hours=18)
    
    status_lower = status.lower()
    
    # Include if game is live
    if status_lower in ['in progress', 'halftime', '1st quarter', '2nd quarter', '3rd quarter', '4th quarter', 
                       '1st half', '2nd half', 'overtime', 'live', 'active']:
        return True
    
    # Include if game finished recently (started within last 12 hours)
    if status_lower == 'final' and game_date >= twelve_hours_ago:
        return True
    
    # Include if game is scheduled within the next 18 hours (covers US timezones)
    if status_lower == 'scheduled' and current_time <= game_date < eighteen_hours_from_now:
        return True
    
    return False

def convert_sport_format(sport: str) -> str:
    """Convert user-friendly sport format (with underscores) to ESPN API format (with slashes)"""
    # Handle special cases where we simplified the user format but ESPN still expects the full path
    sport_mappings = {
        "basketball_mens-college": "basketball/mens-college-basketball",
        "football_college": "football/college-football"
    }
    
    if sport in sport_mappings:
        return sport_mappings[sport]
    
    # Default conversion: replace underscores with slashes
    return sport.replace('_', '/')

def get_conference_groups() -> Dict[str, Dict[str, List[int]]]:
    """Get the conference to ESPN group mapping"""
    return {
        "big sky": {
            "basketball_mens-college": [5],  # Group 5 is Big Sky for basketball
            "football_college": [20]  # Group 20 is Big Sky for football
        },
        "big_sky": {  # Allow underscore version
            "basketball_mens-college": [5],
            "football_college": [20]
        },
        "big 12": {
            "basketball_mens-college": [21],  # Group 21 is Big 12 for basketball
        },
        "big_12": {  # Allow underscore version
            "basketball_mens-college": [21],
        },
        "mvfc": {
            "football_college": [21]  # Group 21 is MVFC for football
        },
        "missouri valley football": {  # Allow full name version
            "football_college": [21]
        },
        "fcs": {
            "football_college": [81]  # Group 81 is FCS football
        },
        "fcs football": {  # Allow full name version
            "football_college": [81]
        },
        "all": {
            "football_college": [90]  # Group 90 is all NCAA football (FBS + FCS)
        }
    }

def get_sport_examples() -> Dict[str, Any]:
    """Get available sports with user-friendly format"""
    return {
        "basketball": {
            "nba": "basketball_nba",
            "college": "basketball_mens-college", 
            "wnba": "basketball_wnba"
        },
        "football": {
            "nfl": "football_nfl",
            "college": "football_college"
        },
        "baseball": {
            "mlb": "baseball_mlb",
            "college": "baseball_college-baseball"
        },
        "hockey": {
            "nhl": "hockey_nhl"
        },
        "soccer": {
            "premier_league": "soccer_eng.1",
            "champions_league": "soccer_uefa.champions",
            "mls": "soccer_usa.1",
            "la_liga": "soccer_esp.1",
            "bundesliga": "soccer_ger.1",
            "serie_a": "soccer_ita.1",
            "ligue_1": "soccer_fra.1"
        },
        "tennis": {
            "atp": "tennis_atp",
            "wta": "tennis_wta"
        },
        "golf": {
            "pga": "golf_pga"
        }
    }

@router.get("/scores")
async def get_scores(
    request: Request,
    sport: str = Query("basketball_nba", description="Sport to get scores for (e.g., basketball_nba, football_nfl, baseball_mlb, hockey_nhl, soccer_eng.1)"),
    page: int = Query(1, ge=1, description="Page number (starts from 1)"),
    page_size: int = Query(5, ge=1, le=500, description="Number of scores per page"),
    force_refresh: bool = Query(False, description="Force refresh from ESPN API")
) -> Dict[str, Any]:
    # Convert user-friendly format to ESPN API format
    espn_sport = convert_sport_format(sport)
    
    # Calculate offset based on page and page_size
    offset = (page - 1) * page_size
    
    # Create sport-specific cache key
    cache_key = f"sports_scores_{sport.replace('.', '_')}"
    
    # Check cache unless force refresh is requested
    cached_scores = None if force_refresh else cache.get(cache_key)
    
    scores_data = None
    total_scores = 0
    
    if cached_scores:
        scores_data = cached_scores
        total_scores = len(cached_scores)
    else:
        try:
            # Fetch fresh scores from ESPN using converted format
            scores = await espn_service.fetch_scores(sport=espn_sport)
            
            cache.set(cache_key, scores)
            scores_data = scores
            total_scores = len(scores)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    # Calculate pagination
    offset = (page - 1) * page_size
    end_index = offset + page_size
    paginated_scores = scores_data[offset:end_index]
    
    if not paginated_scores and page > 1:
        raise HTTPException(status_code=404, detail="Page not found")
    
    # Calculate total pages
    total_pages = (total_scores + page_size - 1) // page_size
    
    # Build next page URL if there's a next page
    next_page_url = None
    if page < total_pages:
        # Properly construct base URL with port
        base_url = f"{request.url.scheme}://{request.url.netloc}{request.url.path}"
        next_page_url = f"{base_url}?sport={sport}&page={page + 1}&page_size={page_size}"
        if force_refresh:
            next_page_url += "&force_refresh=true"
    
    # Build previous page URL if there's a previous page
    prev_page_url = None
    if page > 1:
        # Properly construct base URL with port
        base_url = f"{request.url.scheme}://{request.url.netloc}{request.url.path}"
        prev_page_url = f"{base_url}?sport={sport}&page={page - 1}&page_size={page_size}"
        if force_refresh:
            prev_page_url += "&force_refresh=true"
    
    return {
        "data": paginated_scores,
        "pagination": {
            "current_page": page,
            "page_size": page_size,
            "total_scores": total_scores,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_previous": page > 1,
            "next_page_url": next_page_url,
            "previous_page_url": prev_page_url
        }
    }

@router.get("/sports")
async def get_available_sports() -> Dict[str, Any]:
    """Get list of available sports"""
    sports = get_sport_examples()
    
    return {
        "sports": sports,
        "examples": [
            "/api/scores?sport=football_nfl",
            "/api/scores?sport=soccer_eng.1", 
            "/api/scores?sport=baseball_mlb",
            "/api/scores?sport=hockey_nhl"
        ],
        "note": "Use underscores instead of slashes for better URL compatibility"
    }

@router.get("/conferences")
async def get_conferences(
    sport: str = Query("basketball_mens-college", description="Sport to get conferences for"),
    force_refresh: bool = Query(False, description="Force refresh from ESPN API")
) -> Dict[str, Any]:
    """Get list of conferences for a specific sport"""
    
    # Convert user-friendly format to ESPN API format
    espn_sport = convert_sport_format(sport)
    
    try:
        # Fetch scores to extract conference information
        scores = await espn_service.fetch_scores(sport=espn_sport, limit=100)
        
        # Extract unique conferences
        conferences = set()
        for score in scores:
            home_conf = score.get('home_team', {}).get('conference', '')
            away_conf = score.get('away_team', {}).get('conference', '')
            
            if home_conf and home_conf != 'Unknown':
                conferences.add(home_conf)
            if away_conf and away_conf != 'Unknown':
                conferences.add(away_conf)
        
        # Sort conferences alphabetically
        sorted_conferences = sorted(list(conferences))
        
        return {
            "sport": sport,
            "conferences": sorted_conferences,
            "total_conferences": len(sorted_conferences),
            "examples": [
                f"/api/scores?sport={sport}&conference=SEC",
                f"/api/live?sport={sport}&conference=Big Ten",
                f"/api/scores?sport={sport}&conference=ACC&page_size=5"
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conference/{conference_name}")
async def get_conference_games(
    request: Request,
    conference_name: str,
    sport: str = Query("basketball_mens-college", description="Sport type (basketball_mens-college, football_college)"),
    page: int = Query(1, description="Page number", ge=1),
    page_size: int = Query(10, description="Number of scores per page", ge=1, le=500),
    force_refresh: bool = Query(False, description="Force refresh cache")
):
    """Get games for a specific conference using ESPN groups parameter"""
    
    # Get conference groups mapping
    conference_groups = get_conference_groups()
    
    conference_key = conference_name.lower().replace("-", " ").replace("_", " ")
    
    if conference_key not in conference_groups:
        raise HTTPException(
            status_code=404, 
            detail=f"Conference '{conference_name}' not supported. Available: {list(conference_groups.keys())}"
        )
    
    if sport not in conference_groups[conference_key]:
        raise HTTPException(
            status_code=404,
            detail=f"Sport '{sport}' not available for conference '{conference_name}'"
        )
    
    # Get the group IDs for this conference/sport combination
    group_ids = conference_groups[conference_key][sport]
    
    cache_key = f"conference:{conference_key}:{sport}"
    
    if not force_refresh:
        cached_result = cache.get(cache_key)
        if cached_result:
            # Apply pagination to cached results
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            
            paginated_data = cached_result[start_idx:end_idx]
            
            total_scores = len(cached_result)
            total_pages = (total_scores + page_size - 1) // page_size
            
            return {
                "data": paginated_data,
                "pagination": {
                    "current_page": page,
                    "page_size": page_size,
                    "total_scores": total_scores,
                    "total_pages": total_pages,
                    "has_next": page < total_pages,
                    "has_previous": page > 1,
                    "next_page_url": f"{request.url.scheme}://{request.url.netloc}/api/conference/{conference_name}?sport={sport}&page={page + 1}&page_size={page_size}" if page < total_pages else None,
                    "previous_page_url": f"{request.url.scheme}://{request.url.netloc}/api/conference/{conference_name}?sport={sport}&page={page - 1}&page_size={page_size}" if page > 1 else None
                },
                "info": {
                    "conference": conference_name.title(),
                    "sport": sport,
                    "group_ids_used": group_ids,
                    "cache_duration": "5 minutes"
                }
            }
    
    # Fetch games from all group IDs for this conference
    all_conference_games = []
    
    # Convert sport format for ESPN API using the same conversion function
    espn_sport_format = convert_sport_format(sport)
    
    for group_id in group_ids:
        try:
            group_games = await espn_service.fetch_conference_games(espn_sport_format, group_id)
            all_conference_games.extend(group_games)
        except Exception as e:
            print(f"Error fetching group {group_id}: {e}")
            continue
    
    # Remove duplicates based on game ID
    seen_ids = set()
    unique_games = []
    for game in all_conference_games:
        if game['id'] not in seen_ids:
            seen_ids.add(game['id'])
            unique_games.append(game)
    
    # Cache the results
    cache.set(cache_key, unique_games, expiration_minutes=5)  # 5 minutes
    
    # Apply pagination
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_data = unique_games[start_idx:end_idx]
    
    total_scores = len(unique_games)
    total_pages = (total_scores + page_size - 1) // page_size
    
    return {
        "data": paginated_data,
        "pagination": {
            "current_page": page,
            "page_size": page_size,
            "total_scores": total_scores,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_previous": page > 1,
            "next_page_url": f"{request.url.scheme}://{request.url.netloc}/api/conference/{conference_name}?sport={sport}&page={page + 1}&page_size={page_size}" if page < total_pages else None,
            "previous_page_url": f"{request.url.scheme}://{request.url.netloc}/api/conference/{conference_name}?sport={sport}&page={page - 1}&page_size={page_size}" if page > 1 else None
        },
        "info": {
            "conference": conference_name.title(),
            "sport": sport,
            "group_ids_used": group_ids,
            "total_games_found": total_scores,
            "cache_duration": "5 minutes"
        }
    }

@router.get("/live")
async def get_live_scores(
    request: Request,
    sport: str = Query(None, description="Specific sport to get live scores for (e.g., basketball_nba, football_nfl). If not specified, gets all sports."),
    page: int = Query(1, ge=1, description="Page number (starts from 1)"),
    page_size: int = Query(10, ge=1, le=500, description="Number of scores per page"),
    force_refresh: bool = Query(False, description="Force refresh from ESPN API"),
    detailed_conferences: str = Query(None, description="Comma-separated list of conference names to include detailed games from (e.g., 'Big 12,SEC,Big Ten')")
) -> Dict[str, Any]:
    """Get live games, recently finished games (final games that started within the last 12 hours), and upcoming games within the next 18 hours (timezone-aware for US) from specified sport or all sports. Optionally include detailed conference games."""
    
    # Define the sports we want to check
    if sport:
        # Convert user-friendly format to ESPN API format
        espn_sport = convert_sport_format(sport)
        sports_to_check = [espn_sport]
        cache_key = f"live_scores_{sport.replace('.', '_')}"
    else:
        # If no sport specified, check all sports (using ESPN format)
        sports_to_check = [
            "basketball/nba",
            "football/nfl", 
            "baseball/mlb",
            "hockey/nhl",
            "soccer/eng.1",  # Premier League
            "soccer/usa.1",  # MLS
            "basketball/mens-college-basketball",
            "football/college-football"
        ]
        cache_key = "live_scores_all_sports"
    
    # Add detailed_conferences to cache key if specified
    if detailed_conferences:
        cache_key += f"_conf_{detailed_conferences.replace(',', '_').replace(' ', '')}"
    
    # Check cache unless force refresh is requested
    cached_scores = None if force_refresh else cache.get(cache_key)
    
    all_live_scores = []
    
    if cached_scores:
        all_live_scores = cached_scores
    else:
        # Fetch scores from all sports
        current_time = datetime.now(timezone.utc)
        
        for espn_sport_format in sports_to_check:
            try:
                scores = await espn_service.fetch_scores(sport=espn_sport_format, limit=50)
                
                # Filter for live games, recently finished games, or upcoming games within 18 hours
                for score in scores:
                    game_date = datetime.fromisoformat(score['date'].replace('Z', '+00:00'))
                    status = score['status']
                    
                    # Use helper function to check if game should be included
                    if is_game_in_live_window(game_date, status, current_time):
                        
                        # Add sport info to the score data
                        score['sport'] = espn_sport_format
                        score['sport_display'] = espn_sport_format.replace('/', ' ').title().replace('Nba', 'NBA').replace('Nfl', 'NFL').replace('Mlb', 'MLB').replace('Nhl', 'NHL')
                        all_live_scores.append(score)
                        
            except Exception as e:
                # Continue with other sports if one fails
                print(f"Error fetching {espn_sport_format}: {e}")
                continue
        
        # Fetch detailed conference games if requested
        if detailed_conferences:
            conference_scores = []
            conference_list = [conf.strip() for conf in detailed_conferences.split(',')]
            
            # Get the conference groups mapping
            conference_groups = get_conference_groups()
            
            # Fetch games for each specified conference
            for conference_name in conference_list:
                # Normalize conference name to match our mapping
                conference_key = conference_name.lower().replace(' ', '').replace('-', '_')
                
                if conference_key in conference_groups:
                    # Get groups for both basketball and football
                    for sport_key in ["basketball_mens-college", "football_college"]:
                        if sport_key in conference_groups[conference_key]:
                            groups = conference_groups[conference_key][sport_key]
                            
                            # Convert sport key to ESPN API format
                            espn_sport = convert_sport_format(sport_key)
                            
                            for group_id in groups:
                                try:
                                    games = await espn_service.fetch_conference_games(espn_sport, group_id)
                                    
                                    for game in games:
                                        # Add sport info to the game data
                                        game['sport'] = espn_sport
                                        game['sport_display'] = espn_sport.replace('/', ' ').title().replace('Nba', 'NBA').replace('Nfl', 'NFL').replace('Mlb', 'MLB').replace('Nhl', 'NHL')
                                        conference_scores.append(game)
                                        
                                except Exception as e:
                                    print(f"Error fetching conference group {group_id} for {sport_key}: {e}")
                                    continue
            
            # Combine and deduplicate (live scores take precedence)
            seen_ids = set()
            combined_scores = []
            
            # Add live scores first (these take priority)
            for score in all_live_scores:
                if score['id'] not in seen_ids:
                    seen_ids.add(score['id'])
                    combined_scores.append(score)
            
            # Add conference scores that aren't already included
            for score in conference_scores:
                if score['id'] not in seen_ids:
                    seen_ids.add(score['id'])
                    combined_scores.append(score)
            
            all_live_scores = combined_scores
        
        # Sort by game date (most recent first)
        all_live_scores.sort(key=lambda x: x['date'], reverse=True)
        
        # Group by league and then sort by time within each league
        # Sort by sport priority first, then by date within each sport
        all_live_scores.sort(key=lambda x: (get_sport_priority(x['sport']), x['date']))
        
        # Cache the results for 2 minutes (shorter cache for live data)
        cache.set(cache_key, all_live_scores, expiration_minutes=2)
    
    # Apply pagination
    total_scores = len(all_live_scores)
    offset = (page - 1) * page_size
    end_index = offset + page_size
    paginated_scores = all_live_scores[offset:end_index]
    
    if not paginated_scores and page > 1:
        raise HTTPException(status_code=404, detail="Page not found")
    
    # Calculate total pages
    total_pages = (total_scores + page_size - 1) // page_size
    
    # Build next page URL if there's a next page
    next_page_url = None
    if page < total_pages:
        # Properly construct base URL with port
        base_url = f"{request.url.scheme}://{request.url.netloc}{request.url.path}"
        params = [f"page={page + 1}", f"page_size={page_size}"]
        if sport:
            params.append(f"sport={sport}")
        if detailed_conferences:
            params.append(f"detailed_conferences={detailed_conferences}")
        if force_refresh:
            params.append("force_refresh=true")
        next_page_url = f"{base_url}?{'&'.join(params)}"
    
    # Build previous page URL if there's a previous page
    prev_page_url = None
    if page > 1:
        # Properly construct base URL with port
        base_url = f"{request.url.scheme}://{request.url.netloc}{request.url.path}"
        params = [f"page={page - 1}", f"page_size={page_size}"]
        if sport:
            params.append(f"sport={sport}")
        if detailed_conferences:
            params.append(f"detailed_conferences={detailed_conferences}")
        if force_refresh:
            params.append("force_refresh=true")
        prev_page_url = f"{base_url}?{'&'.join(params)}"
    
    return {
        "data": paginated_scores,
        "pagination": {
            "current_page": page,
            "page_size": page_size,
            "total_scores": total_scores,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_previous": page > 1,
            "next_page_url": next_page_url,
            "previous_page_url": prev_page_url
        },
        "info": {
            "description": "Live games or recently finished games (final games that started within the last 4 hours)",
            "sports_checked": sports_to_check,
            "cache_duration": "2 minutes",
            "filter": f"Specific sport: {sport}" if sport else "All sports"
        }
    }

@router.get("/top_performers")
async def get_top_performers(
    request: Request,
    sport: str = Query(None, description="Specific sport to get top performers for (e.g., basketball_nba, football_nfl). If not specified, gets all sports."),
    stat_category: str = Query(None, description="Filter by specific stat category (e.g., 'Pts', 'Reb', 'Ast', 'passing_td', 'rushing_td')"),
    top_n: int = Query(5, ge=1, le=20, description="Number of top performers to return per category"),
    force_refresh: bool = Query(False, description="Force refresh from ESPN API")
) -> Dict[str, Any]:
    """Get top performers across all sports from games in the past 24 hours"""
    
    # Define the sports we want to check
    if sport:
        espn_sport = convert_sport_format(sport)
        sports_to_check = [espn_sport]
        cache_key = f"top_performers_{sport.replace('.', '_')}"
    else:
        sports_to_check = [
            "basketball/nba",
            "football/nfl", 
            "baseball/mlb",
            "hockey/nhl",
            "basketball/mens-college-basketball",
            "football/college-football"
        ]
        cache_key = "top_performers_all_sports"
    
    # Add stat category and top_n to cache key
    if stat_category:
        cache_key += f"_stat_{stat_category.lower()}"
    cache_key += f"_top{top_n}"
    
    # Check cache unless force refresh is requested
    cached_performers = None if force_refresh else cache.get(cache_key)
    
    if cached_performers:
        return cached_performers
    
    # Collect all performers from games in the past 24 hours
    current_time = datetime.now(timezone.utc)
    twenty_four_hours_ago = current_time - timedelta(hours=24)
    
    all_performers = []
    
    for sport_name in sports_to_check:
        try:
            scores = await espn_service.fetch_scores(sport=sport_name, limit=50)
            
            for score in scores:
                game_date = datetime.fromisoformat(score['date'].replace('Z', '+00:00'))
                
                # Only include games from the past 24 hours
                if game_date >= twenty_four_hours_ago:
                    # Extract top performers from this game
                    for performer in score.get('top_performers', []):
                        performer_data = {
                            'player_name': performer['player_name'],
                            'team': performer['team'],
                            'team_abbr': performer['team_abbr'],
                            'stat_category': performer['stat_category'],
                            'value': performer['value'],
                            'description': performer['description'],
                            'sport': sport_name,
                            'sport_display': sport_name.replace('/', ' ').title().replace('Nba', 'NBA').replace('Nfl', 'NFL').replace('Mlb', 'MLB').replace('Nhl', 'NHL'),
                            'game_name': score['name'],
                            'game_date': score['date'],
                            'game_status': score['status']
                        }
                        all_performers.append(performer_data)
                        
        except Exception as e:
            print(f"Error fetching {sport_name} for top performers: {e}")
            continue
    
    # Organize performers by stat category
    performers_by_category = {}
    
    for performer in all_performers:
        category = performer['stat_category']
        
        # Filter by stat category if specified
        if stat_category and category.lower() != stat_category.lower():
            continue
            
        if category not in performers_by_category:
            performers_by_category[category] = []
        
        performers_by_category[category].append(performer)
    
    # Sort each category by value (descending) and take top N
    top_performers_result = {}
    
    for category, performers in performers_by_category.items():
        # Sort by value (highest first)
        sorted_performers = sorted(performers, key=lambda x: x['value'], reverse=True)
        top_performers_result[category] = sorted_performers[:top_n]
    
    # Calculate some summary stats
    total_games_analyzed = len(set(f"{p['sport']}_{p['game_name']}" for p in all_performers))
    total_performers = len(all_performers)
    unique_players = len(set(p['player_name'] for p in all_performers))
    
    result = {
        "top_performers": top_performers_result,
        "summary": {
            "total_games_analyzed": total_games_analyzed,
            "total_performer_records": total_performers,
            "unique_players": unique_players,
            "stat_categories_found": list(top_performers_result.keys()),
            "time_period": "Past 24 hours",
            "top_n_per_category": top_n
        },
        "filters": {
            "sport_filter": sport if sport else "All sports",
            "stat_category_filter": stat_category if stat_category else "All categories",
            "sports_checked": sports_to_check
        }
    }
    
    # Cache the results for 10 minutes
    cache.set(cache_key, result, expiration_minutes=10)
    
    return result


