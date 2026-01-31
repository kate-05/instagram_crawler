"""Database module for Instagram Crawler."""

from database.models import init_database
from database.manager import DatabaseManager

__all__ = ['init_database', 'DatabaseManager']
