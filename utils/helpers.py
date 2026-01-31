"""Utility functions for Instagram Crawler."""

import json
import os
import re
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

from config import PROGRESS_PATH, CrawlStep


def extract_username(url: str) -> Optional[str]:
    """Extract username from Instagram URL.

    Args:
        url: Instagram URL or username

    Returns:
        Username or None if not found
    """
    url = url.strip().rstrip('/')

    # Check if it's a URL
    patterns = [
        r'instagram\.com/([^/\?]+)',
        r'instagr\.am/([^/\?]+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            username = match.group(1)
            # Skip non-username paths
            if username in ['p', 'reel', 'reels', 'stories', 'explore', 'accounts', 'tv']:
                return None
            return username

    # If not a URL, assume it's a username
    if url.startswith('@'):
        url = url[1:]

    # Basic validation
    if re.match(r'^[a-zA-Z0-9._]+$', url) and len(url) <= 30:
        return url

    return None


def sanitize_filename(name: str) -> str:
    """Sanitize a string to be safe for use as a filename.

    Args:
        name: Original filename

    Returns:
        Sanitized filename
    """
    # Remove invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        name = name.replace(char, '_')

    # Remove leading/trailing spaces and dots
    name = name.strip('. ')

    # Limit length
    if len(name) > 200:
        name = name[:200]

    return name or 'unnamed'


def format_number(num: int) -> str:
    """Format large numbers with K/M/B suffixes.

    Args:
        num: Number to format

    Returns:
        Formatted number string
    """
    if num is None:
        return "N/A"

    if num >= 1_000_000_000:
        return f"{num / 1_000_000_000:.1f}B"
    elif num >= 1_000_000:
        return f"{num / 1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num / 1_000:.1f}K"
    return str(num)


def parse_datetime(date_str: str) -> Optional[datetime]:
    """Parse datetime string in various formats.

    Args:
        date_str: Date string

    Returns:
        datetime object or None
    """
    if not date_str:
        return None

    formats = [
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%dT%H:%M:%S.%f',
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d',
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str.split('+')[0], fmt)
        except ValueError:
            continue

    return None


# ==================== Progress File Management ====================

def load_progress(progress_path: Path = PROGRESS_PATH) -> Dict[str, Any]:
    """Load progress data from JSON file.

    Args:
        progress_path: Path to progress file

    Returns:
        Progress data dictionary or empty structure
    """
    if not os.path.exists(progress_path):
        return {'last_updated': None, 'profiles': []}

    try:
        with open(progress_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {'last_updated': None, 'profiles': []}


def save_progress(progress_data: Dict[str, Any],
                  progress_path: Path = PROGRESS_PATH) -> bool:
    """Save progress data to JSON file.

    Args:
        progress_data: Progress data to save
        progress_path: Path to progress file

    Returns:
        True if saved successfully
    """
    try:
        progress_data['last_updated'] = datetime.now().isoformat()
        with open(progress_path, 'w', encoding='utf-8') as f:
            json.dump(progress_data, f, ensure_ascii=False, indent=2)
        return True
    except IOError:
        return False


def has_incomplete_work(progress_data: Dict[str, Any]) -> bool:
    """Check if there's any incomplete work in progress data.

    Args:
        progress_data: Progress data dictionary

    Returns:
        True if there's incomplete work
    """
    profiles = progress_data.get('profiles', [])
    for profile in profiles:
        if profile.get('status') == 'in_progress':
            return True

        steps = profile.get('steps_completed', {})
        for step in CrawlStep.all_steps():
            if steps.get(step) in ['pending', 'in_progress']:
                return True

    return False


def get_profile_progress(progress_data: Dict[str, Any],
                         profile_id: int) -> Optional[Dict[str, Any]]:
    """Get progress data for a specific profile.

    Args:
        progress_data: Full progress data
        profile_id: Profile database ID

    Returns:
        Profile progress data or None
    """
    for profile in progress_data.get('profiles', []):
        if profile.get('profile_id') == profile_id:
            return profile
    return None


def update_profile_progress(progress_data: Dict[str, Any],
                            profile_id: int,
                            username: str = None,
                            status: str = None,
                            total_posts: int = None,
                            current_post_index: int = None,
                            step: str = None,
                            step_status: str = None) -> Dict[str, Any]:
    """Update or create profile progress data.

    Args:
        progress_data: Full progress data
        profile_id: Profile database ID
        username: Instagram username
        status: Profile crawling status
        total_posts: Total posts count
        current_post_index: Current post index
        step: Step to update
        step_status: New status for the step

    Returns:
        Updated progress data
    """
    profile_progress = get_profile_progress(progress_data, profile_id)

    if not profile_progress:
        # Create new entry
        profile_progress = {
            'profile_id': profile_id,
            'username': username,
            'status': status or 'pending',
            'total_posts': total_posts or 0,
            'current_post_index': current_post_index or 0,
            'steps_completed': {step: 'pending' for step in CrawlStep.all_steps()}
        }
        if 'profiles' not in progress_data:
            progress_data['profiles'] = []
        progress_data['profiles'].append(profile_progress)
    else:
        # Update existing entry
        if username:
            profile_progress['username'] = username
        if status:
            profile_progress['status'] = status
        if total_posts is not None:
            profile_progress['total_posts'] = total_posts
        if current_post_index is not None:
            profile_progress['current_post_index'] = current_post_index
        if step and step_status:
            if 'steps_completed' not in profile_progress:
                profile_progress['steps_completed'] = {}
            profile_progress['steps_completed'][step] = step_status

    return progress_data


def remove_profile_from_progress(progress_data: Dict[str, Any],
                                 profile_id: int) -> Dict[str, Any]:
    """Remove a profile from progress data.

    Args:
        progress_data: Full progress data
        profile_id: Profile database ID to remove

    Returns:
        Updated progress data
    """
    profiles = progress_data.get('profiles', [])
    progress_data['profiles'] = [p for p in profiles if p.get('profile_id') != profile_id]
    return progress_data


def get_next_incomplete_step(profile_progress: Dict[str, Any]) -> Optional[str]:
    """Get the next incomplete step for a profile.

    Priority: in_progress steps first (resume), then first pending step.

    Args:
        profile_progress: Profile progress data

    Returns:
        Next incomplete step name or None
    """
    steps = profile_progress.get('steps_completed', {})

    # First, check for any in_progress step (resume from where we stopped)
    for step in CrawlStep.all_steps():
        if steps.get(step) == 'in_progress':
            return step

    # Then, find the first pending step
    for step in CrawlStep.all_steps():
        status = steps.get(step, 'pending')
        if status == 'pending':
            return step

    return None


# ==================== Export Functions ====================

def export_to_json(data: Dict[str, Any], filepath: str) -> bool:
    """Export data to JSON file.

    Args:
        data: Data to export
        filepath: Output file path

    Returns:
        True if successful
    """
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except IOError:
        return False


def export_to_csv(data: List[Dict[str, Any]], filepath: str,
                  fieldnames: List[str] = None) -> bool:
    """Export data to CSV file.

    Args:
        data: List of dictionaries to export
        filepath: Output file path
        fieldnames: Column names (auto-detected if not provided)

    Returns:
        True if successful
    """
    import csv

    if not data:
        return False

    if not fieldnames:
        fieldnames = list(data[0].keys())

    try:
        with open(filepath, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(data)
        return True
    except IOError:
        return False


def export_profile_data(db_manager, profile_id: int, export_dir: Path,
                        export_format: str = 'json') -> List[str]:
    """Export all data for a profile.

    Args:
        db_manager: DatabaseManager instance
        profile_id: Profile ID to export
        export_dir: Export directory path
        export_format: 'json' or 'csv'

    Returns:
        List of exported file paths
    """
    from datetime import datetime

    exported_files = []
    profile = db_manager.get_profile(profile_id=profile_id)

    if not profile:
        return exported_files

    username = sanitize_filename(profile['username'])
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Ensure export directory exists
    export_dir.mkdir(parents=True, exist_ok=True)

    if export_format == 'json':
        # Export everything to single JSON
        data = {
            'profile': profile,
            'posts': db_manager.get_profile_posts(profile_id),
            'stories': db_manager.get_profile_stories(profile_id),
            'highlights': [],
            'hashtag_stats': db_manager.get_profile_hashtags(profile_id),
            'stats': db_manager.get_profile_stats(profile_id),
        }

        # Add highlights with items
        highlights = db_manager.get_profile_highlights(profile_id)
        for h in highlights:
            h_data = dict(h)
            h_data['items'] = db_manager.get_highlight_items(h['id'])
            data['highlights'].append(h_data)

        # Add comments to posts
        for post in data['posts']:
            post['comments'] = db_manager.get_post_comments(post['id'])
            post['hashtags'] = db_manager.get_post_hashtags(post['id'])

        filepath = export_dir / f"{username}_{timestamp}.json"
        if export_to_json(data, str(filepath)):
            exported_files.append(str(filepath))

    else:  # CSV format
        # Export profile
        filepath = export_dir / f"{username}_profile_{timestamp}.csv"
        if export_to_csv([profile], str(filepath)):
            exported_files.append(str(filepath))

        # Export posts
        posts = db_manager.get_profile_posts(profile_id)
        if posts:
            filepath = export_dir / f"{username}_posts_{timestamp}.csv"
            if export_to_csv(posts, str(filepath)):
                exported_files.append(str(filepath))

        # Export comments
        all_comments = []
        for post in posts:
            comments = db_manager.get_post_comments(post['id'])
            all_comments.extend(comments)

        if all_comments:
            filepath = export_dir / f"{username}_comments_{timestamp}.csv"
            if export_to_csv(all_comments, str(filepath)):
                exported_files.append(str(filepath))

        # Export hashtags
        hashtag_stats = db_manager.get_profile_hashtags(profile_id)
        if hashtag_stats:
            filepath = export_dir / f"{username}_hashtags_{timestamp}.csv"
            if export_to_csv(hashtag_stats, str(filepath)):
                exported_files.append(str(filepath))

    return exported_files
