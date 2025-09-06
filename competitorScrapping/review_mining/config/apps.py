"""
Target apps configuration for review mining.
Defines the apps to scrape reviews for and their metadata.
"""

from typing import Dict, List, Any

TARGET_APPS = {
    'mobile_apps': {
        'spotify': {
            'name': 'Spotify',
            'package_id': 'com.spotify.music',
            'category': 'music_streaming',
            'platforms': ['android', 'ios'],
            'keywords': ['spotify', 'music streaming', 'playlist'],
            'competitors': ['apple_music', 'youtube_music', 'amazon_music']
        },
        'netflix': {
            'name': 'Netflix',
            'package_id': 'com.netflix.mediaclient',
            'category': 'video_streaming',
            'platforms': ['android', 'ios'],
            'keywords': ['netflix', 'streaming', 'movies', 'tv shows'],
            'competitors': ['disney_plus', 'hulu', 'amazon_prime']
        },
        'uber': {
            'name': 'Uber',
            'package_id': 'com.ubercab',
            'category': 'transportation',
            'platforms': ['android', 'ios'],
            'keywords': ['uber', 'rideshare', 'taxi'],
            'competitors': ['lyft', 'taxi', 'public_transport']
        },
        'airbnb': {
            'name': 'Airbnb',
            'package_id': 'com.airbnb.android',
            'category': 'travel',
            'platforms': ['android', 'ios'],
            'keywords': ['airbnb', 'accommodation', 'vacation rental'],
            'competitors': ['booking', 'hotels', 'vrbo']
        },
        'day_one': {
            'name': 'Day One',
            'category': 'journaling',
            'platforms': ['reddit'],
            'keywords': ['day one', 'journal', 'diary', 'daily journal', 'journaling app'],
            'competitors': ['journey', 'daily', 'grid_diary', 'momento']
        },
        'journey': {
            'name': 'Journey',
            'category': 'journaling',
            'platforms': ['reddit'],
            'keywords': ['journey', 'journal', 'diary', 'journaling', 'memories'],
            'competitors': ['day_one', 'daily', 'grid_diary', 'momento']
        },
        'daily': {
            'name': 'Daily - Journal & Diary',
            'category': 'journaling',
            'platforms': ['reddit'],
            'keywords': ['daily', 'journal', 'diary', 'mood tracker', 'daily journal', 'daily notes', 'habit tracker'],
            'competitors': ['day_one', 'journey', 'grid_diary', 'momento']
        }
    },
    'web_apps': {
        'slack': {
            'name': 'Slack',
            'url': 'https://slack.com',
            'category': 'communication',
            'keywords': ['slack', 'team communication', 'workplace chat'],
            'competitors': ['microsoft_teams', 'discord', 'zoom']
        },
        'zoom': {
            'name': 'Zoom',
            'url': 'https://zoom.us',
            'category': 'video_conferencing',
            'keywords': ['zoom', 'video calls', 'meetings'],
            'competitors': ['microsoft_teams', 'google_meet', 'skype']
        }
    }
}

# Reddit subreddits to monitor for each app category
SUBREDDIT_MAPPING = {
    'music_streaming': ['spotify', 'music', 'streaming', 'playlists'],
    'video_streaming': ['netflix', 'streaming', 'movies', 'television'],
    'transportation': ['uber', 'rideshare', 'transportation'],
    'travel': ['airbnb', 'travel', 'vacation'],
    'communication': ['slack', 'workplace', 'productivity'],
    'video_conferencing': ['zoom', 'videoconferencing', 'remotework'],
    'journaling': ['journaling', 'diary', 'productivity', 'selfimprovement', 'mentalhealth', 'writing']
}

# Review categories for classification
REVIEW_CATEGORIES = {
    'ux_ui': {
        'name': 'User Experience & Interface',
        'keywords': ['interface', 'design', 'usability', 'navigation', 'ui', 'ux', 'user-friendly']
    },
    'pricing': {
        'name': 'Pricing & Billing',
        'keywords': ['price', 'cost', 'expensive', 'cheap', 'billing', 'subscription', 'payment']
    },
    'performance': {
        'name': 'Performance & Reliability',
        'keywords': ['slow', 'fast', 'lag', 'crash', 'bug', 'stable', 'performance', 'loading']
    },
    'features': {
        'name': 'Features & Functionality',
        'keywords': ['feature', 'function', 'capability', 'tool', 'option', 'missing', 'need']
    },
    'customer_service': {
        'name': 'Customer Service',
        'keywords': ['support', 'help', 'service', 'response', 'staff', 'customer care']
    },
    'content_quality': {
        'name': 'Content Quality',
        'keywords': ['content', 'quality', 'selection', 'variety', 'catalog', 'library']
    }
}

def get_app_config(app_name: str) -> Dict[str, Any]:
    """Get configuration for a specific app."""
    for category in TARGET_APPS.values():
        if app_name in category:
            return category[app_name]
    return {}

def get_apps_by_category(category: str) -> Dict[str, Any]:
    """Get all apps in a specific category."""
    return TARGET_APPS.get(category, {})

def get_subreddits_for_category(category: str) -> List[str]:
    """Get relevant subreddits for a category."""
    return SUBREDDIT_MAPPING.get(category, [])
