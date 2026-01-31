"""Instagram Crawler Test Runner"""

import sys
import os
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

# Test results
results = {
    'passed': 0,
    'failed': 0,
    'errors': []
}


def test(name):
    """Decorator for test functions."""
    def decorator(func):
        def wrapper():
            try:
                func()
                results['passed'] += 1
                print(f"  [PASS] {name}")
                return True
            except AssertionError as e:
                results['failed'] += 1
                results['errors'].append(f"{name}: {str(e)}")
                print(f"  [FAIL] {name}: {e}")
                return False
            except Exception as e:
                results['failed'] += 1
                results['errors'].append(f"{name}: {str(e)}")
                print(f"  [ERROR] {name}: {e}")
                return False
        return wrapper
    return decorator


# ==================== Database Tests ====================
print("\n" + "="*60)
print("1. DATABASE TESTS")
print("="*60)


@test("DB-001: init_database creates tables")
def test_db_init():
    from database.models import init_database
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        conn = init_database(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        assert 'profiles' in tables
        assert 'posts' in tables
        assert 'stories' in tables
        assert 'highlights' in tables
        assert 'comments' in tables
        assert 'hashtags' in tables

test_db_init()


@test("DB-P01: add_profile returns ID")
def test_add_profile():
    from database.manager import DatabaseManager
    with tempfile.TemporaryDirectory() as tmpdir:
        db = DatabaseManager(Path(tmpdir) / "test.db")
        result = db.add_profile(
            username="testuser",
            full_name="Test User",
            follower_count=100
        )
        db.close()
        assert result is not None
        assert isinstance(result, int)

test_add_profile()


@test("DB-P02: add_profile duplicate returns None")
def test_add_profile_duplicate():
    from database.manager import DatabaseManager
    with tempfile.TemporaryDirectory() as tmpdir:
        db = DatabaseManager(Path(tmpdir) / "test.db")
        db.add_profile(username="testuser")
        result = db.add_profile(username="testuser")
        db.close()
        assert result is None

test_add_profile_duplicate()


@test("DB-P03: get_profile by ID")
def test_get_profile_by_id():
    from database.manager import DatabaseManager
    with tempfile.TemporaryDirectory() as tmpdir:
        db = DatabaseManager(Path(tmpdir) / "test.db")
        pid = db.add_profile(username="testuser", full_name="Test")
        profile = db.get_profile(profile_id=pid)
        db.close()
        assert profile is not None
        assert profile['username'] == "testuser"
        assert profile['full_name'] == "Test"

test_get_profile_by_id()


@test("DB-P04: get_profile by username")
def test_get_profile_by_username():
    from database.manager import DatabaseManager
    with tempfile.TemporaryDirectory() as tmpdir:
        db = DatabaseManager(Path(tmpdir) / "test.db")
        db.add_profile(username="findme", full_name="Find Me")
        profile = db.get_profile(username="findme")
        db.close()
        assert profile is not None
        assert profile['full_name'] == "Find Me"

test_get_profile_by_username()


@test("DB-P05: get_profile not found returns None")
def test_get_profile_not_found():
    from database.manager import DatabaseManager
    with tempfile.TemporaryDirectory() as tmpdir:
        db = DatabaseManager(Path(tmpdir) / "test.db")
        profile = db.get_profile(username="notexist")
        db.close()
        assert profile is None

test_get_profile_not_found()


@test("DB-P06: get_all_profiles")
def test_get_all_profiles():
    from database.manager import DatabaseManager
    with tempfile.TemporaryDirectory() as tmpdir:
        db = DatabaseManager(Path(tmpdir) / "test.db")
        db.add_profile(username="user1")
        db.add_profile(username="user2")
        db.add_profile(username="user3")
        profiles = db.get_all_profiles()
        db.close()
        assert len(profiles) == 3

test_get_all_profiles()


@test("DB-P07: update_profile_status")
def test_update_profile_status():
    from database.manager import DatabaseManager
    from config import Status
    with tempfile.TemporaryDirectory() as tmpdir:
        db = DatabaseManager(Path(tmpdir) / "test.db")
        pid = db.add_profile(username="testuser")
        result = db.update_profile_status(pid, Status.COMPLETED)
        profile = db.get_profile(profile_id=pid)
        db.close()
        assert result == True
        assert profile['status'] == Status.COMPLETED

test_update_profile_status()


@test("DB-P08: delete_profile cascades")
def test_delete_profile():
    from database.manager import DatabaseManager
    with tempfile.TemporaryDirectory() as tmpdir:
        db = DatabaseManager(Path(tmpdir) / "test.db")
        pid = db.add_profile(username="testuser")
        db.add_post(pid, "ABC123", caption="Test post")
        result = db.delete_profile(pid)
        profile = db.get_profile(profile_id=pid)
        posts = db.get_profile_posts(pid)
        db.close()
        assert result == True
        assert profile is None
        assert len(posts) == 0

test_delete_profile()


@test("DB-T01: add_post returns ID")
def test_add_post():
    from database.manager import DatabaseManager
    with tempfile.TemporaryDirectory() as tmpdir:
        db = DatabaseManager(Path(tmpdir) / "test.db")
        pid = db.add_profile(username="testuser")
        post_id = db.add_post(pid, "ABC123", caption="Test caption")
        db.close()
        assert post_id is not None

test_add_post()


@test("DB-T02: add_post duplicate returns None")
def test_add_post_duplicate():
    from database.manager import DatabaseManager
    with tempfile.TemporaryDirectory() as tmpdir:
        db = DatabaseManager(Path(tmpdir) / "test.db")
        pid = db.add_profile(username="testuser")
        db.add_post(pid, "ABC123")
        result = db.add_post(pid, "ABC123")
        db.close()
        assert result is None

test_add_post_duplicate()


@test("DB-T03: add_posts_batch")
def test_add_posts_batch():
    from database.manager import DatabaseManager
    with tempfile.TemporaryDirectory() as tmpdir:
        db = DatabaseManager(Path(tmpdir) / "test.db")
        pid = db.add_profile(username="testuser")
        posts = [
            {'profile_id': pid, 'shortcode': 'A1'},
            {'profile_id': pid, 'shortcode': 'A2'},
            {'profile_id': pid, 'shortcode': 'A3'},
        ]
        added = db.add_posts_batch(posts)
        db.close()
        assert added == 3

test_add_posts_batch()


@test("DB-T04: get_profile_posts")
def test_get_profile_posts():
    from database.manager import DatabaseManager
    with tempfile.TemporaryDirectory() as tmpdir:
        db = DatabaseManager(Path(tmpdir) / "test.db")
        pid = db.add_profile(username="testuser")
        db.add_post(pid, "A1", post_type="image")
        db.add_post(pid, "A2", post_type="video")
        posts = db.get_profile_posts(pid)
        db.close()
        assert len(posts) == 2

test_get_profile_posts()


@test("DB-T05: get_profile_posts with filter")
def test_get_profile_posts_filter():
    from database.manager import DatabaseManager
    with tempfile.TemporaryDirectory() as tmpdir:
        db = DatabaseManager(Path(tmpdir) / "test.db")
        pid = db.add_profile(username="testuser")
        db.add_post(pid, "A1", post_type="image")
        db.add_post(pid, "A2", post_type="video")
        db.add_post(pid, "A3", post_type="image")
        posts = db.get_profile_posts(pid, post_type="image")
        db.close()
        assert len(posts) == 2

test_get_profile_posts_filter()


@test("DB-C01: add_comment")
def test_add_comment():
    from database.manager import DatabaseManager
    with tempfile.TemporaryDirectory() as tmpdir:
        db = DatabaseManager(Path(tmpdir) / "test.db")
        pid = db.add_profile(username="testuser")
        post_id = db.add_post(pid, "ABC123")
        cid = db.add_comment(post_id, "c1", "commenter", "Nice!")
        db.close()
        assert cid is not None

test_add_comment()


@test("DB-C02: add_comments_batch")
def test_add_comments_batch():
    from database.manager import DatabaseManager
    with tempfile.TemporaryDirectory() as tmpdir:
        db = DatabaseManager(Path(tmpdir) / "test.db")
        pid = db.add_profile(username="testuser")
        post_id = db.add_post(pid, "ABC123")
        comments = [
            {'post_id': post_id, 'comment_id': 'c1', 'username': 'u1', 'text': 'Hi'},
            {'post_id': post_id, 'comment_id': 'c2', 'username': 'u2', 'text': 'Hello'},
        ]
        added = db.add_comments_batch(comments)
        db.close()
        assert added == 2

test_add_comments_batch()


@test("DB-H01: add_hashtag")
def test_add_hashtag():
    from database.manager import DatabaseManager
    with tempfile.TemporaryDirectory() as tmpdir:
        db = DatabaseManager(Path(tmpdir) / "test.db")
        pid = db.add_profile(username="testuser")
        post_id = db.add_post(pid, "ABC123")
        hid = db.add_hashtag(post_id, "test")
        db.close()
        assert hid is not None

test_add_hashtag()


@test("DB-H02: add_hashtags_batch")
def test_add_hashtags_batch():
    from database.manager import DatabaseManager
    with tempfile.TemporaryDirectory() as tmpdir:
        db = DatabaseManager(Path(tmpdir) / "test.db")
        pid = db.add_profile(username="testuser")
        post_id = db.add_post(pid, "ABC123")
        added = db.add_hashtags_batch(post_id, ['tag1', 'tag2', 'tag3'])
        db.close()
        assert added == 3

test_add_hashtags_batch()


@test("DB-H03: get_post_hashtags")
def test_get_post_hashtags():
    from database.manager import DatabaseManager
    with tempfile.TemporaryDirectory() as tmpdir:
        db = DatabaseManager(Path(tmpdir) / "test.db")
        pid = db.add_profile(username="testuser")
        post_id = db.add_post(pid, "ABC123")
        db.add_hashtags_batch(post_id, ['instagram', 'photo'])
        tags = db.get_post_hashtags(post_id)
        db.close()
        assert 'instagram' in tags
        assert 'photo' in tags

test_get_post_hashtags()


# ==================== Utils Tests ====================
print("\n" + "="*60)
print("2. UTILS TESTS")
print("="*60)


@test("UT-001: extract_username from URL")
def test_extract_username_url():
    from utils.helpers import extract_username
    assert extract_username("https://instagram.com/testuser") == "testuser"
    assert extract_username("https://www.instagram.com/testuser/") == "testuser"
    assert extract_username("instagram.com/myprofile") == "myprofile"

test_extract_username_url()


@test("UT-002: extract_username from @username")
def test_extract_username_at():
    from utils.helpers import extract_username
    assert extract_username("@testuser") == "testuser"
    assert extract_username("testuser") == "testuser"

test_extract_username_at()


@test("UT-003: extract_username invalid")
def test_extract_username_invalid():
    from utils.helpers import extract_username
    assert extract_username("instagram.com/p/ABC123") is None
    assert extract_username("not a valid input!!!") is None

test_extract_username_invalid()


@test("UT-004: sanitize_filename")
def test_sanitize_filename():
    from utils.helpers import sanitize_filename
    assert sanitize_filename("test<>file") == "test__file"
    assert sanitize_filename("normal_file") == "normal_file"
    assert sanitize_filename("file:with:colons") == "file_with_colons"

test_sanitize_filename()


@test("UT-005: format_number")
def test_format_number():
    from utils.helpers import format_number
    assert format_number(500) == "500"
    assert format_number(1500) == "1.5K"
    assert format_number(1500000) == "1.5M"
    assert format_number(1500000000) == "1.5B"

test_format_number()


@test("UT-006: load_progress no file")
def test_load_progress_no_file():
    from utils.helpers import load_progress
    result = load_progress(Path("/nonexistent/path/file.json"))
    assert 'profiles' in result
    assert result['profiles'] == []

test_load_progress_no_file()


@test("UT-007: save_progress and load_progress")
def test_save_load_progress():
    from utils.helpers import save_progress, load_progress
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "progress.json"
        data = {'profiles': [{'profile_id': 1, 'status': 'completed'}]}
        save_progress(data, path)
        loaded = load_progress(path)
        assert loaded['profiles'][0]['profile_id'] == 1

test_save_load_progress()


@test("UT-008: has_incomplete_work")
def test_has_incomplete_work():
    from utils.helpers import has_incomplete_work
    data_complete = {'profiles': [{'status': 'completed', 'steps_completed': {}}]}
    data_incomplete = {'profiles': [{'status': 'in_progress', 'steps_completed': {}}]}
    assert has_incomplete_work(data_complete) == False
    assert has_incomplete_work(data_incomplete) == True

test_has_incomplete_work()


@test("UT-009: export_to_json")
def test_export_json():
    from utils.helpers import export_to_json
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "export.json"
        data = {'test': 'data', 'number': 123}
        result = export_to_json(data, str(path))
        assert result == True
        assert path.exists()

test_export_json()


@test("UT-010: export_to_csv")
def test_export_csv():
    from utils.helpers import export_to_csv
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "export.csv"
        data = [{'name': 'test', 'value': 1}, {'name': 'test2', 'value': 2}]
        result = export_to_csv(data, str(path))
        assert result == True
        assert path.exists()

test_export_csv()


# ==================== Hashtag Extractor Tests ====================
print("\n" + "="*60)
print("3. HASHTAG EXTRACTOR TESTS")
print("="*60)

# Import hashtags module directly to avoid instaloader dependency
import importlib.util
spec = importlib.util.spec_from_file_location("hashtags", Path(__file__).parent / "crawler" / "hashtags.py")
hashtags_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hashtags_module)
HashtagExtractor = hashtags_module.HashtagExtractor


@test("CR-HT01: extract single hashtag")
def test_extract_single_hashtag():
    extractor = HashtagExtractor()
    result = extractor.extract_hashtags("Hello #world")
    assert result == ['world']

test_extract_single_hashtag()


@test("CR-HT02: extract multiple hashtags")
def test_extract_multiple_hashtags():
    extractor = HashtagExtractor()
    result = extractor.extract_hashtags("#hello #world #test")
    assert len(result) == 3
    assert 'hello' in result
    assert 'world' in result

test_extract_multiple_hashtags()


@test("CR-HT03: extract removes duplicates")
def test_extract_duplicates():
    extractor = HashtagExtractor()
    result = extractor.extract_hashtags("#test #Test #TEST")
    assert len(result) == 1

test_extract_duplicates()


@test("CR-HT04: extract no hashtags")
def test_extract_no_hashtags():
    extractor = HashtagExtractor()
    result = extractor.extract_hashtags("No hashtags here")
    assert result == []

test_extract_no_hashtags()


@test("CR-HT05: extract Korean hashtags")
def test_extract_korean():
    extractor = HashtagExtractor()
    result = extractor.extract_hashtags("#한글태그 #테스트")
    assert '한글태그' in result
    assert '테스트' in result

test_extract_korean()


@test("CR-HT06: analyze_hashtags")
def test_analyze_hashtags():
    extractor = HashtagExtractor()
    hashtags = ['test', 'test', 'hello', 'test', 'world']
    result = extractor.analyze_hashtags(hashtags)
    assert result['total_count'] == 5
    assert result['unique_count'] == 3
    assert result['top_hashtags'][0] == ('test', 3)

test_analyze_hashtags()


# ==================== Config Tests ====================
print("\n" + "="*60)
print("4. CONFIG TESTS")
print("="*60)


@test("CFG-001: CrawlStep.all_steps()")
def test_crawl_steps():
    from config import CrawlStep
    steps = CrawlStep.all_steps()
    assert len(steps) == 8
    assert CrawlStep.PROFILE_INFO in steps
    assert CrawlStep.HASHTAGS in steps

test_crawl_steps()


@test("CFG-002: CrawlStep.login_required_steps()")
def test_login_required_steps():
    from config import CrawlStep
    steps = CrawlStep.login_required_steps()
    assert CrawlStep.STORIES in steps
    assert CrawlStep.HIGHLIGHTS in steps
    assert CrawlStep.POST_LIST not in steps

test_login_required_steps()


@test("CFG-003: Status constants")
def test_status_constants():
    from config import Status
    assert Status.PENDING == "pending"
    assert Status.COMPLETED == "completed"
    assert Status.IN_PROGRESS == "in_progress"

test_status_constants()


# ==================== Profile Crawler Tests ====================
print("\n" + "="*60)
print("5. PROFILE CRAWLER TESTS (requires instaloader)")
print("="*60)

try:
    import instaloader
    INSTALOADER_AVAILABLE = True
except ImportError:
    INSTALOADER_AVAILABLE = False
    print("  [SKIP] instaloader not available - skipping crawler tests")


if INSTALOADER_AVAILABLE:
    @test("CR-P01: extract_username URL formats")
    def test_profile_extract_username():
        from crawler.profile import ProfileCrawler
        crawler = ProfileCrawler()
        assert crawler.extract_username("https://instagram.com/testuser") == "testuser"
        assert crawler.extract_username("@myuser") == "myuser"
        assert crawler.extract_username("plainuser") == "plainuser"

    test_profile_extract_username()


    @test("CR-P02: extract_username invalid paths")
    def test_profile_extract_invalid():
        from crawler.profile import ProfileCrawler
        crawler = ProfileCrawler()
        assert crawler.extract_username("https://instagram.com/p/ABC123") is None
        assert crawler.extract_username("https://instagram.com/reel/XYZ") is None

    test_profile_extract_invalid()


# ==================== Summary ====================
print("\n" + "="*60)
print("TEST SUMMARY")
print("="*60)
print(f"  Passed: {results['passed']}")
print(f"  Failed: {results['failed']}")
print(f"  Total:  {results['passed'] + results['failed']}")
print("="*60)

if results['errors']:
    print("\nFailed Tests:")
    for error in results['errors']:
        print(f"  - {error}")

# Exit code
sys.exit(0 if results['failed'] == 0 else 1)
