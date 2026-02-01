"""Instagram Crawler - GUI Application using CustomTkinter."""

import customtkinter as ctk
from tkinter import messagebox
import threading
import queue
import os
from datetime import datetime
from typing import Optional, List, Dict, Any

import instaloader

# Try to import instagrapi for stories/highlights
try:
    from instagrapi import Client as InstagrapiClient
    INSTAGRAPI_AVAILABLE = True
except ImportError:
    INSTAGRAPI_AVAILABLE = False

from config import (
    WINDOW_WIDTH, WINDOW_HEIGHT, APPEARANCE_MODE, COLOR_THEME,
    DATABASE_PATH, EXPORT_DIR, SESSION_DIR, Status, CrawlStep, ACCESS_CODES
)
from database import DatabaseManager
from crawler import (
    ProfileCrawler, PostsCrawler, ReelsCrawler,
    StoriesCrawler, HighlightsCrawler, CommentsCrawler, HashtagExtractor
)
from crawler.highlights_v2 import HighlightsCrawlerV2, StoriesCrawlerV2
from utils.helpers import (
    load_progress, save_progress, has_incomplete_work,
    update_profile_progress, get_profile_progress, get_next_incomplete_step,
    remove_profile_from_progress, export_profile_data, extract_username
)


# Configure appearance
ctk.set_appearance_mode(APPEARANCE_MODE)
ctk.set_default_color_theme(COLOR_THEME)


class ProfileListItem(ctk.CTkFrame):
    """Individual profile item in the list."""

    def __init__(self, parent, profile_data: Dict[str, Any],
                 on_select: callable = None, on_delete: callable = None):
        super().__init__(parent)

        self.profile_data = profile_data
        self.on_select = on_select
        self.on_delete = on_delete
        self.selected = False

        self.configure(fg_color="transparent")

        # Checkbox
        self.checkbox_var = ctk.BooleanVar(value=False)
        self.checkbox = ctk.CTkCheckBox(
            self, text="", variable=self.checkbox_var,
            width=20, command=self._on_checkbox_change
        )
        self.checkbox.pack(side="left", padx=(5, 10))

        # Username
        username = profile_data.get('username', 'Unknown')
        self.name_label = ctk.CTkLabel(self, text=f"@{username}", anchor="w")
        self.name_label.pack(side="left", fill="x", expand=True)

        # Private indicator
        if profile_data.get('is_private'):
            private_label = ctk.CTkLabel(self, text="[비공개]", text_color="gray")
            private_label.pack(side="left", padx=5)

        # Status
        status = profile_data.get('status', Status.PENDING)
        post_count = profile_data.get('post_count', 0)
        status_text = self._format_status(status, post_count)
        self.status_label = ctk.CTkLabel(self, text=status_text, width=150)
        self.status_label.pack(side="right", padx=5)

        # Delete button
        self.delete_btn = ctk.CTkButton(
            self, text="X", width=30, height=25,
            fg_color="transparent", hover_color="#AA3333",
            command=self._on_delete
        )
        self.delete_btn.pack(side="right", padx=5)

    def _format_status(self, status: str, post_count: int) -> str:
        """Format status text for display."""
        if status == Status.PENDING:
            return f"대기중 ({post_count}개)"
        elif status == Status.IN_PROGRESS:
            return "진행중"
        elif status == Status.COMPLETED:
            return f"완료 ({post_count}개)"
        elif status == Status.PRIVATE:
            return "비공개"
        return status

    def _on_checkbox_change(self):
        """Handle checkbox state change."""
        self.selected = self.checkbox_var.get()
        if self.on_select:
            self.on_select(self.profile_data['id'], self.selected)

    def _on_delete(self):
        """Handle delete button click."""
        if self.on_delete:
            self.on_delete(self.profile_data['id'])

    def update_status(self, status: str, progress_text: str = None):
        """Update the displayed status."""
        if progress_text:
            self.status_label.configure(text=progress_text)
        else:
            post_count = self.profile_data.get('post_count', 0)
            self.status_label.configure(text=self._format_status(status, post_count))


class InstagramCrawlerApp(ctk.CTk):
    """Main application window."""

    def __init__(self):
        super().__init__()

        self.title("인스타그램 크롤러")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.minsize(700, 500)

        # Initialize components
        self.db = DatabaseManager(DATABASE_PATH)
        self.progress_data = load_progress()

        # Create shared instaloader instance
        self.loader = instaloader.Instaloader(
            download_pictures=False,
            download_videos=False,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
            compress_json=False,
            quiet=True
        )

        # Crawlers
        self.profile_crawler = ProfileCrawler(self.loader, progress_callback=self._log_message)
        self.posts_crawler = PostsCrawler(self.loader, progress_callback=self._log_message)
        self.reels_crawler = ReelsCrawler(self.loader, progress_callback=self._log_message)
        self.stories_crawler = StoriesCrawler(self.loader, progress_callback=self._log_message)
        self.highlights_crawler = HighlightsCrawler(self.loader, progress_callback=self._log_message)
        self.comments_crawler = CommentsCrawler(self.loader, progress_callback=self._log_message)
        self.hashtag_extractor = HashtagExtractor(progress_callback=self._log_message)

        # Instagrapi client for stories/highlights (alternative API)
        self.instagrapi_client = None
        self.stories_crawler_v2 = StoriesCrawlerV2(progress_callback=self._log_message)
        self.highlights_crawler_v2 = HighlightsCrawlerV2(progress_callback=self._log_message)

        # State
        self.is_crawling = False
        self.should_stop = False
        self.selected_profiles = set()
        self.profile_widgets = {}
        self.logged_in_user = None

        # Crawl options
        self.crawl_options = {
            'profile': True,
            'posts': True,
            'reels': True,
            'stories': False,
            'highlights': False,
            'comments': True,
            'hashtags': True,
        }

        # Message queue for thread-safe UI updates
        self.message_queue = queue.Queue()

        # Build UI
        self._create_widgets()

        # Load existing profiles
        self._load_profiles()

        # Check for incomplete work
        self.after(500, self._check_incomplete_work)

        # Process message queue
        self._process_message_queue()

    def _create_widgets(self):
        """Create all UI widgets."""
        # Main container
        self.main_container = ctk.CTkFrame(self)
        self.main_container.pack(fill="both", expand=True, padx=10, pady=10)

        # Title
        title_label = ctk.CTkLabel(
            self.main_container,
            text="인스타그램 크롤러",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.pack(pady=(0, 10))

        # Login section
        self._create_login_section()

        # Account input section
        self._create_input_section()

        # Crawl options section
        self._create_options_section()

        # Profile list section
        self._create_profile_list_section()

        # Progress section
        self._create_progress_section()

        # Log area
        self._create_log_section()

        # Button section
        self._create_button_section()

    def _create_login_section(self):
        """Create login section."""
        login_frame = ctk.CTkFrame(self.main_container)
        login_frame.pack(fill="x", pady=(0, 10))

        login_label = ctk.CTkLabel(login_frame, text="로그인 (선택):", anchor="w")
        login_label.pack(side="left", padx=5)

        self.login_status_label = ctk.CTkLabel(
            login_frame, text="로그인되지 않음",
            text_color="gray"
        )
        self.login_status_label.pack(side="left", padx=10)

        self.login_btn = ctk.CTkButton(
            login_frame, text="로그인", width=80,
            command=self._show_login_dialog
        )
        self.login_btn.pack(side="right", padx=5)

        self.logout_btn = ctk.CTkButton(
            login_frame, text="로그아웃", width=80,
            state="disabled", command=self._logout
        )
        self.logout_btn.pack(side="right", padx=5)

    def _create_input_section(self):
        """Create account input section."""
        input_frame = ctk.CTkFrame(self.main_container)
        input_frame.pack(fill="x", pady=(0, 10))

        input_label = ctk.CTkLabel(input_frame, text="계정 URL 또는 사용자명:")
        input_label.pack(side="left", padx=5)

        self.url_entry = ctk.CTkEntry(
            input_frame,
            placeholder_text="https://instagram.com/username 또는 @username"
        )
        self.url_entry.pack(side="left", fill="x", expand=True, padx=5)
        self.url_entry.bind("<Return>", lambda e: self._add_profile())

        self.add_btn = ctk.CTkButton(
            input_frame, text="추가", width=80,
            command=self._add_profile
        )
        self.add_btn.pack(side="right", padx=5)

    def _create_options_section(self):
        """Create crawl options section."""
        options_frame = ctk.CTkFrame(self.main_container)
        options_frame.pack(fill="x", pady=(0, 10))

        options_label = ctk.CTkLabel(options_frame, text="수집 옵션:", anchor="w")
        options_label.pack(side="left", padx=5)

        # Checkboxes for options
        self.option_vars = {}

        options = [
            ('profile', '프로필 정보', True),
            ('posts', '게시물', True),
            ('reels', '릴스', True),
            ('stories', '스토리 (로그인 필요)', False),
            ('highlights', '하이라이트 (로그인 필요)', False),
            ('comments', '댓글', True),
            ('hashtags', '해시태그', True),
        ]

        for key, label, default in options:
            var = ctk.BooleanVar(value=default)
            self.option_vars[key] = var
            cb = ctk.CTkCheckBox(
                options_frame, text=label, variable=var,
                command=lambda k=key: self._on_option_change(k)
            )
            cb.pack(side="left", padx=5)

    def _create_profile_list_section(self):
        """Create profile list section."""
        list_label = ctk.CTkLabel(self.main_container, text="계정 목록:", anchor="w")
        list_label.pack(fill="x", pady=(5, 2))

        # Scrollable profile list
        self.profile_list_frame = ctk.CTkScrollableFrame(self.main_container, height=180)
        self.profile_list_frame.pack(fill="both", expand=True, pady=(0, 10))

    def _create_progress_section(self):
        """Create progress section."""
        progress_frame = ctk.CTkFrame(self.main_container)
        progress_frame.pack(fill="x", pady=(0, 10))

        self.progress_label = ctk.CTkLabel(progress_frame, text="전체 진행률: 0%")
        self.progress_label.pack(side="left", padx=10)

        self.progress_bar = ctk.CTkProgressBar(progress_frame)
        self.progress_bar.pack(side="left", fill="x", expand=True, padx=10)
        self.progress_bar.set(0)

        # Current task label
        self.task_label = ctk.CTkLabel(
            self.main_container,
            text="현재 작업: 대기 중",
            anchor="w"
        )
        self.task_label.pack(fill="x", pady=(0, 5))

    def _create_log_section(self):
        """Create log section."""
        log_label = ctk.CTkLabel(self.main_container, text="로그:", anchor="w")
        log_label.pack(fill="x")

        self.log_text = ctk.CTkTextbox(self.main_container, height=100)
        self.log_text.pack(fill="x", pady=(0, 10))

    def _create_button_section(self):
        """Create button section."""
        button_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        button_frame.pack(fill="x")

        self.start_btn = ctk.CTkButton(
            button_frame, text="시작", width=100,
            command=self._start_crawling
        )
        self.start_btn.pack(side="left", padx=5)

        self.pause_btn = ctk.CTkButton(
            button_frame, text="일시정지", width=100,
            state="disabled", command=self._pause_crawling
        )
        self.pause_btn.pack(side="left", padx=5)

        self.stop_btn = ctk.CTkButton(
            button_frame, text="중단", width=100,
            state="disabled", command=self._stop_crawling
        )
        self.stop_btn.pack(side="left", padx=5)

        self.export_btn = ctk.CTkButton(
            button_frame, text="내보내기", width=100,
            command=self._export_data
        )
        self.export_btn.pack(side="right", padx=5)

    def _on_option_change(self, key: str):
        """Handle option checkbox change."""
        self.crawl_options[key] = self.option_vars[key].get()

        # Warn about login requirement for stories/highlights
        if key in ['stories', 'highlights'] and self.crawl_options[key]:
            if not self.instagrapi_client:
                names = {'stories': '스토리', 'highlights': '하이라이트'}
                messagebox.showwarning(
                    "로그인 필요",
                    f"{names.get(key, key)} 수집을 위해 먼저 로그인해주세요."
                )

    def _show_login_dialog(self):
        """Show login dialog."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("인스타그램 로그인")
        dialog.geometry("400x200")
        dialog.transient(self)
        dialog.grab_set()

        # Center the dialog
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 400) // 2
        y = self.winfo_y() + (self.winfo_height() - 200) // 2
        dialog.geometry(f"400x200+{x}+{y}")

        # Username
        username_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        username_frame.pack(fill="x", padx=20, pady=(20, 5))
        ctk.CTkLabel(username_frame, text="사용자명:", width=80).pack(side="left")
        username_entry = ctk.CTkEntry(username_frame, width=250)
        username_entry.pack(side="left", fill="x", expand=True)

        # Password
        password_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        password_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(password_frame, text="비밀번호:", width=80).pack(side="left")
        password_entry = ctk.CTkEntry(password_frame, width=250, show="*")
        password_entry.pack(side="left", fill="x", expand=True)

        # Status label
        status_label = ctk.CTkLabel(dialog, text="", text_color="red")
        status_label.pack(pady=5)

        def do_login():
            username = username_entry.get().strip()
            password = password_entry.get()

            if not username or not password:
                status_label.configure(text="사용자명과 비밀번호를 입력하세요")
                return

            status_label.configure(text="로그인 중...", text_color="gray")
            dialog.update()

            # Try to login with instaloader
            if self.profile_crawler.login(username, password):
                self.logged_in_user = username
                self.login_status_label.configure(
                    text=f"로그인됨: @{username}",
                    text_color="green"
                )
                self.login_btn.configure(state="disabled")
                self.logout_btn.configure(state="normal")

                # Save session
                self.profile_crawler.save_session(username)

                # Also login with instagrapi for stories/highlights
                if INSTAGRAPI_AVAILABLE:
                    try:
                        self.instagrapi_client = InstagrapiClient()
                        self.instagrapi_client.login(username, password)
                        self.stories_crawler_v2.set_client(self.instagrapi_client)
                        self.highlights_crawler_v2.set_client(self.instagrapi_client)
                        self._log_message("스토리/하이라이트 API 연결됨")
                    except Exception as e:
                        self._log_message(f"스토리/하이라이트 API 연결 실패: {str(e)}")
                        self.instagrapi_client = None

                dialog.destroy()
            else:
                status_label.configure(text="로그인 실패", text_color="red")

        # Login button
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=10)
        ctk.CTkButton(btn_frame, text="로그인", command=do_login).pack(side="right", padx=5)
        ctk.CTkButton(btn_frame, text="취소", command=dialog.destroy).pack(side="right", padx=5)

        # Bind Enter key
        password_entry.bind("<Return>", lambda e: do_login())

    def _logout(self):
        """Logout from Instagram."""
        self.profile_crawler.logout()
        self.logged_in_user = None
        self.instagrapi_client = None
        self.stories_crawler_v2.set_client(None)
        self.highlights_crawler_v2.set_client(None)
        self.login_status_label.configure(text="로그인되지 않음", text_color="gray")
        self.login_btn.configure(state="normal")
        self.logout_btn.configure(state="disabled")
        self._log_message("로그아웃됨")

    def _load_profiles(self):
        """Load profiles from database and display them."""
        profiles = self.db.get_all_profiles()

        for profile in profiles:
            self._add_profile_to_list(profile)

    def _add_profile_to_list(self, profile_data: Dict[str, Any]):
        """Add a profile widget to the list."""
        profile_id = profile_data['id']

        # Remove existing if present
        if profile_id in self.profile_widgets:
            self.profile_widgets[profile_id].destroy()

        # Create new widget
        widget = ProfileListItem(
            self.profile_list_frame,
            profile_data,
            on_select=self._on_profile_select,
            on_delete=self._on_profile_delete
        )
        widget.pack(fill="x", pady=2)

        self.profile_widgets[profile_id] = widget

    def _add_profile(self):
        """Add a new profile from URL input."""
        url_or_username = self.url_entry.get().strip()
        if not url_or_username:
            return

        # Extract username
        username = extract_username(url_or_username)
        if not username:
            messagebox.showerror("오류", "유효하지 않은 URL 또는 사용자명입니다.")
            return

        # Check if already exists
        existing = self.db.get_profile(username=username)
        if existing:
            messagebox.showinfo("알림", f"@{username}은(는) 이미 목록에 있습니다.")
            return

        # Clear input
        self.url_entry.delete(0, "end")

        # Disable add button during fetch
        self.add_btn.configure(state="disabled")
        self._log_message(f"프로필 정보 가져오는 중: @{username}")

        # Fetch profile info in background
        def fetch_profile():
            profile_info = self.profile_crawler.get_profile_info(username)

            if profile_info:
                # Add to database
                profile_id = self.db.add_profile(
                    username=profile_info['username'],
                    full_name=profile_info.get('full_name'),
                    biography=profile_info.get('biography'),
                    follower_count=profile_info.get('follower_count', 0),
                    following_count=profile_info.get('following_count', 0),
                    post_count=profile_info.get('post_count', 0),
                    is_private=profile_info.get('is_private', False),
                    profile_pic_url=profile_info.get('profile_pic_url'),
                    external_url=profile_info.get('external_url'),
                    is_verified=profile_info.get('is_verified', False)
                )

                if profile_id:
                    profile_data = self.db.get_profile(profile_id=profile_id)
                    self.message_queue.put(('add_profile', profile_data))
                    self.message_queue.put(('log', f"프로필 추가됨: @{username}"))
                else:
                    self.message_queue.put(('log', "프로필이 이미 존재합니다."))
            else:
                self.message_queue.put(('log', f"프로필 정보를 가져올 수 없습니다: @{username}"))

            self.message_queue.put(('enable_add', None))

        thread = threading.Thread(target=fetch_profile, daemon=True)
        thread.start()

    def _on_profile_select(self, profile_id: int, selected: bool):
        """Handle profile selection."""
        if selected:
            self.selected_profiles.add(profile_id)
        else:
            self.selected_profiles.discard(profile_id)

    def _on_profile_delete(self, profile_id: int):
        """Handle profile deletion."""
        if self.is_crawling:
            messagebox.showwarning("경고", "크롤링 중에는 프로필을 삭제할 수 없습니다.")
            return

        if messagebox.askyesno("확인", "이 프로필과 모든 관련 데이터를 삭제하시겠습니까?"):
            # Remove from database
            self.db.delete_profile(profile_id)

            # Remove from progress
            self.progress_data = remove_profile_from_progress(self.progress_data, profile_id)
            save_progress(self.progress_data)

            # Remove widget
            if profile_id in self.profile_widgets:
                self.profile_widgets[profile_id].destroy()
                del self.profile_widgets[profile_id]

            self.selected_profiles.discard(profile_id)
            self._log_message("프로필이 삭제되었습니다.")

    def _check_incomplete_work(self):
        """Check for incomplete work and offer to resume."""
        if has_incomplete_work(self.progress_data):
            result = messagebox.askyesno(
                "이어서 진행",
                "이전에 중단된 작업이 있습니다. 이어서 진행하시겠습니까?"
            )
            if result:
                self._start_crawling(resume=True)

    def _start_crawling(self, resume: bool = False):
        """Start the crawling process."""
        if self.is_crawling:
            return

        # Check login for stories/highlights
        if (self.crawl_options['stories'] or self.crawl_options['highlights']):
            if not self.profile_crawler.is_logged_in:
                messagebox.showwarning(
                    "로그인 필요",
                    "스토리/하이라이트를 수집하려면 로그인이 필요합니다."
                )
                return

        # Get profiles to crawl
        if resume:
            # Get in-progress profiles from progress data
            profiles_to_crawl = []
            for p_progress in self.progress_data.get('profiles', []):
                if p_progress.get('status') == 'in_progress':
                    profile = self.db.get_profile(profile_id=p_progress['profile_id'])
                    if profile:
                        profiles_to_crawl.append(profile)
        else:
            # Get selected profiles or all pending
            if self.selected_profiles:
                profiles_to_crawl = [
                    self.db.get_profile(profile_id=pid) for pid in self.selected_profiles
                    if self.db.get_profile(profile_id=pid)
                ]
            else:
                profiles_to_crawl = [
                    p for p in self.db.get_all_profiles()
                    if p['status'] in [Status.PENDING, Status.IN_PROGRESS]
                ]

        if not profiles_to_crawl:
            messagebox.showinfo("알림", "크롤링할 프로필이 없습니다.")
            return

        # Update UI state
        self.is_crawling = True
        self.should_stop = False
        self.start_btn.configure(state="disabled")
        self.pause_btn.configure(state="normal")
        self.stop_btn.configure(state="normal")
        self.add_btn.configure(state="disabled")

        # Start crawling in background
        thread = threading.Thread(
            target=self._crawl_profiles,
            args=(profiles_to_crawl, resume),
            daemon=True
        )
        thread.start()

    def _pause_crawling(self):
        """Pause the crawling process."""
        self.should_stop = True
        self._log_message("일시정지 요청됨. 현재 작업 완료 후 중단됩니다...")
        self.pause_btn.configure(state="disabled")

    def _stop_crawling(self):
        """Stop the crawling process."""
        self.should_stop = True
        self._log_message("중단 요청됨. 현재 작업 완료 후 중단됩니다...")
        self.stop_btn.configure(state="disabled")
        self.pause_btn.configure(state="disabled")

    def _crawl_profiles(self, profiles: List[Dict[str, Any]], resume: bool = False):
        """Crawl multiple profiles (runs in background thread)."""
        total_profiles = len(profiles)

        for p_idx, profile in enumerate(profiles):
            if self.should_stop:
                break

            profile_id = profile['id']
            username = profile['username']

            self.message_queue.put(('log', f"프로필 크롤링 시작: @{username}"))
            self.message_queue.put(('update_profile_status', (profile_id, Status.IN_PROGRESS, "진행중")))

            # Update profile status in DB
            self.db.update_profile_status(profile_id, Status.IN_PROGRESS)

            # Get or create progress
            p_progress = get_profile_progress(self.progress_data, profile_id)
            if not p_progress:
                self.progress_data = update_profile_progress(
                    self.progress_data, profile_id,
                    username=username,
                    status='in_progress',
                    total_posts=profile['post_count']
                )
                p_progress = get_profile_progress(self.progress_data, profile_id)

            # Get starting step
            if resume:
                next_step = get_next_incomplete_step(p_progress)
            else:
                next_step = CrawlStep.PROFILE_INFO

            # Get instaloader Profile object
            insta_profile = self.profile_crawler.get_profile(username)
            if not insta_profile and not profile.get('is_private'):
                self.message_queue.put(('log', f"프로필을 찾을 수 없습니다: @{username}"))
                continue

            # Process each step based on options
            success = True
            for step in CrawlStep.all_steps():
                if self.should_stop:
                    break

                # Skip if option not selected
                if not self._should_run_step(step):
                    continue

                # Skip completed steps when resuming
                if resume and p_progress['steps_completed'].get(step) == 'completed':
                    continue

                # Skip login-required steps if not logged in
                if step in CrawlStep.login_required_steps() and not self.profile_crawler.is_logged_in:
                    continue

                self.message_queue.put(('task', f"현재 작업: {self._get_step_name(step)}"))

                # Mark step as in progress
                self.progress_data = update_profile_progress(
                    self.progress_data, profile_id,
                    step=step, step_status='in_progress'
                )
                save_progress(self.progress_data)

                # Execute step
                try:
                    if step == CrawlStep.PROFILE_INFO:
                        success = self._process_profile_info(profile)
                    elif step == CrawlStep.POST_LIST:
                        success = self._process_posts(profile, insta_profile)
                    elif step == CrawlStep.POST_DETAILS:
                        success = True  # Details collected with posts
                    elif step == CrawlStep.REELS:
                        success = self._process_reels(profile, insta_profile)
                    elif step == CrawlStep.STORIES:
                        success = self._process_stories(profile, insta_profile)
                    elif step == CrawlStep.HIGHLIGHTS:
                        success = self._process_highlights(profile, insta_profile)
                    elif step == CrawlStep.COMMENTS:
                        success = self._process_comments(profile)
                    elif step == CrawlStep.HASHTAGS:
                        success = self._process_hashtags(profile)

                    if success and not self.should_stop:
                        # Mark step as completed
                        self.progress_data = update_profile_progress(
                            self.progress_data, profile_id,
                            step=step, step_status='completed'
                        )
                        save_progress(self.progress_data)

                except Exception as e:
                    self.message_queue.put(('log', f"오류 발생: {str(e)}"))
                    success = False
                    break

            # Update profile status
            if success and not self.should_stop:
                self.db.update_profile_status(profile_id, Status.COMPLETED)
                self.progress_data = update_profile_progress(
                    self.progress_data, profile_id,
                    status='completed'
                )
                self.message_queue.put(('update_profile_status', (profile_id, Status.COMPLETED, None)))
                self.message_queue.put(('log', f"프로필 크롤링 완료: @{username}"))
            else:
                self.message_queue.put(('log', f"프로필 크롤링 중단됨: @{username}"))

            save_progress(self.progress_data)

            # Update overall progress
            progress = (p_idx + 1) / total_profiles
            self.message_queue.put(('progress', progress))

        # Crawling finished
        self.message_queue.put(('crawl_finished', None))

    def _should_run_step(self, step: str) -> bool:
        """Check if a step should be run based on options."""
        step_to_option = {
            CrawlStep.PROFILE_INFO: 'profile',
            CrawlStep.POST_LIST: 'posts',
            CrawlStep.POST_DETAILS: 'posts',
            CrawlStep.REELS: 'reels',
            CrawlStep.STORIES: 'stories',
            CrawlStep.HIGHLIGHTS: 'highlights',
            CrawlStep.COMMENTS: 'comments',
            CrawlStep.HASHTAGS: 'hashtags',
        }
        option_key = step_to_option.get(step, 'profile')
        return self.crawl_options.get(option_key, True)

    def _process_profile_info(self, profile: Dict[str, Any]) -> bool:
        """Process profile info step."""
        # Profile info already fetched during add
        return True

    def _process_posts(self, profile: Dict[str, Any],
                       insta_profile: instaloader.Profile) -> bool:
        """Process posts step."""
        if not insta_profile:
            return False

        profile_id = profile['id']
        self.message_queue.put(('log', "게시물 수집 중..."))

        posts = self.posts_crawler.get_posts(
            insta_profile,
            stop_flag=lambda: self.should_stop
        )

        if posts:
            # Add posts to database
            for post_data in posts:
                post_data['profile_id'] = profile_id

            added = self.db.add_posts_batch(posts)
            self.message_queue.put(('log', f"게시물 {added}개 추가됨"))
            return True

        return not self.should_stop

    def _process_reels(self, profile: Dict[str, Any],
                       insta_profile: instaloader.Profile) -> bool:
        """Process reels step.

        Note: Reels are already collected by posts crawler with post_type='reel'.
        This step just reports the count - no separate API call needed.
        """
        profile_id = profile['id']
        self.message_queue.put(('log', "릴스 확인 중..."))

        # Reels are already captured by posts crawler with post_type='reel'
        existing_reels = self.db.get_profile_posts(profile_id, post_type='reel')
        reel_count = len(existing_reels) if existing_reels else 0

        if reel_count > 0:
            self.message_queue.put(('log', f"릴스 {reel_count}개 (게시물에서 수집됨)"))
        else:
            # Check if there are any posts at all
            all_posts = self.db.get_profile_posts(profile_id)
            if all_posts:
                self.message_queue.put(('log', "릴스 없음 (이 계정에 릴스가 없습니다)"))
            else:
                self.message_queue.put(('log', "릴스 확인 불가 (게시물 먼저 수집 필요)"))

        return True

    def _process_stories(self, profile: Dict[str, Any],
                         insta_profile: instaloader.Profile) -> bool:
        """Process stories step using instagrapi."""
        profile_id = profile['id']
        self.message_queue.put(('log', "스토리 수집 중..."))

        # Use instagrapi if available
        if self.instagrapi_client:
            try:
                # Get user_id from instagrapi
                user_id = self.instagrapi_client.user_id_from_username(profile['username'])
                stories = self.stories_crawler_v2.get_stories(
                    user_id,
                    stop_flag=lambda: self.should_stop
                )

                if stories:
                    for story_data in stories:
                        self.db.add_story(
                            profile_id=profile_id,
                            media_id=story_data['media_id'],
                            media_type=story_data['media_type'],
                            media_url=story_data.get('media_url'),
                            thumbnail_url=story_data.get('thumbnail_url'),
                            posted_at=story_data.get('posted_at'),
                            expires_at=story_data.get('expires_at')
                        )
                    self.message_queue.put(('log', f"스토리 {len(stories)}개 추가됨"))
                    return True
            except Exception as e:
                self.message_queue.put(('log', f"스토리 수집 오류: {str(e)}"))
                return False
        else:
            self.message_queue.put(('log', "스토리 수집에 로그인이 필요합니다"))
            return False

        return not self.should_stop

    def _process_highlights(self, profile: Dict[str, Any],
                            insta_profile: instaloader.Profile) -> bool:
        """Process highlights step using instagrapi."""
        profile_id = profile['id']
        self.message_queue.put(('log', "하이라이트 수집 중..."))

        # Use instagrapi if available
        if self.instagrapi_client:
            try:
                # Get user_id from instagrapi
                user_id = self.instagrapi_client.user_id_from_username(profile['username'])
                highlights_data = self.highlights_crawler_v2.get_highlights(
                    user_id,
                    stop_flag=lambda: self.should_stop
                )

                if highlights_data:
                    for highlight_info, items in highlights_data:
                        highlight_db_id = self.db.add_highlight(
                            profile_id=profile_id,
                            highlight_id=highlight_info['highlight_id'],
                            title=highlight_info['title'],
                            cover_url=highlight_info.get('cover_url'),
                            item_count=highlight_info['item_count']
                        )

                        if highlight_db_id:
                            for item in items:
                                self.db.add_highlight_item(
                                    highlight_id=highlight_db_id,
                                    media_id=item['media_id'],
                                    media_type=item['media_type'],
                                    media_url=item.get('media_url'),
                                    thumbnail_url=item.get('thumbnail_url'),
                                    posted_at=item.get('posted_at')
                                )

                    self.message_queue.put(('log', f"하이라이트 {len(highlights_data)}개 추가됨"))
                    return True
            except Exception as e:
                self.message_queue.put(('log', f"하이라이트 수집 오류: {str(e)}"))
                return False
        else:
            self.message_queue.put(('log', "하이라이트 수집에 로그인이 필요합니다"))
            return False

        return not self.should_stop

    def _process_comments(self, profile: Dict[str, Any]) -> bool:
        """Process comments step."""
        profile_id = profile['id']
        posts = self.db.get_profile_posts(profile_id)

        if not posts:
            self.message_queue.put(('log', "댓글 수집: 게시물이 없습니다"))
            return True

        total = len(posts)
        self.message_queue.put(('log', f"댓글 수집 시작... ({total}개 게시물)"))

        total_comments = 0
        for i, post in enumerate(posts):
            if self.should_stop:
                break

            # Skip if already has comments in DB
            existing_count = self.db.get_comment_count(post['id'])
            if existing_count > 0:
                self.message_queue.put(('log', f"[{i+1}/{total}] {post['shortcode']}: 이미 {existing_count}개 댓글 있음, 스킵"))
                continue

            # Skip posts with 0 comments
            if post.get('comment_count', 0) == 0:
                self.message_queue.put(('log', f"[{i+1}/{total}] {post['shortcode']}: 댓글 없음, 스킵"))
                continue

            self.message_queue.put(('log', f"[{i+1}/{total}] {post['shortcode']} 댓글 수집 중..."))

            comments = self.comments_crawler.get_comments(
                post['shortcode'], post['id'],
                stop_flag=lambda: self.should_stop
            )

            if comments:
                added = self.db.add_comments_batch(comments)
                total_comments += added
                self.message_queue.put(('log', f"[{i+1}/{total}] {post['shortcode']}: {added}개 댓글 저장됨"))

            # Update progress
            progress_text = f"댓글 ({i + 1}/{total})"
            self.message_queue.put(('update_profile_status', (profile_id, Status.IN_PROGRESS, progress_text)))

        self.message_queue.put(('log', f"댓글 수집 완료: 총 {total_comments}개 저장됨"))
        return not self.should_stop

    def _process_hashtags(self, profile: Dict[str, Any]) -> bool:
        """Process hashtags step."""
        profile_id = profile['id']
        posts = self.db.get_profile_posts(profile_id)

        if not posts:
            return True

        self.message_queue.put(('log', "해시태그 추출 중..."))

        for post in posts:
            # Extract hashtags from caption
            hashtags = self.hashtag_extractor.extract_hashtags(post.get('caption', ''))
            if hashtags:
                self.db.add_hashtags_batch(post['id'], hashtags)

        # Get stats
        hashtag_stats = self.db.get_profile_hashtags(profile_id)
        total_hashtags = sum(h['count'] for h in hashtag_stats)
        unique_hashtags = len(hashtag_stats)

        self.message_queue.put(('log', f"해시태그 추출 완료: {unique_hashtags}개 고유 태그, 총 {total_hashtags}회 사용"))

        return True

    def _get_step_name(self, step: str) -> str:
        """Get Korean name for step."""
        names = {
            CrawlStep.PROFILE_INFO: "프로필 정보 수집",
            CrawlStep.POST_LIST: "게시물 목록 수집",
            CrawlStep.POST_DETAILS: "게시물 상세정보 수집",
            CrawlStep.REELS: "릴스 수집",
            CrawlStep.STORIES: "스토리 수집",
            CrawlStep.HIGHLIGHTS: "하이라이트 수집",
            CrawlStep.COMMENTS: "댓글 수집",
            CrawlStep.HASHTAGS: "해시태그 추출",
        }
        return names.get(step, step)

    def _export_data(self):
        """Export crawled data."""
        profiles = self.db.get_all_profiles()
        completed = [p for p in profiles if p['status'] == Status.COMPLETED]

        if not completed:
            messagebox.showinfo("알림", "내보낼 수 있는 완료된 프로필이 없습니다.")
            return

        # Create export directory
        EXPORT_DIR.mkdir(parents=True, exist_ok=True)

        # Ask for export format
        export_format = messagebox.askquestion(
            "내보내기 형식",
            "JSON 형식으로 내보내시겠습니까? (아니오를 선택하면 CSV)"
        )

        format_type = 'json' if export_format == 'yes' else 'csv'

        for profile in completed:
            exported = export_profile_data(
                self.db, profile['id'], EXPORT_DIR, format_type
            )
            if exported:
                self._log_message(f"@{profile['username']} 내보내기 완료: {len(exported)}개 파일")

        messagebox.showinfo("완료", f"데이터가 {EXPORT_DIR}에 저장되었습니다.")

    def _log_message(self, message: str):
        """Log a message (thread-safe)."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.message_queue.put(('log', f"[{timestamp}] {message}"))

    def _process_message_queue(self):
        """Process messages from background threads."""
        try:
            while True:
                msg_type, data = self.message_queue.get_nowait()

                if msg_type == 'log':
                    self.log_text.insert("end", f"{data}\n")
                    self.log_text.see("end")

                elif msg_type == 'progress':
                    self.progress_bar.set(data)
                    self.progress_label.configure(text=f"전체 진행률: {int(data * 100)}%")

                elif msg_type == 'task':
                    self.task_label.configure(text=data)

                elif msg_type == 'add_profile':
                    profile_data = data
                    self._add_profile_to_list(profile_data)

                elif msg_type == 'enable_add':
                    self.add_btn.configure(state="normal")

                elif msg_type == 'update_profile_status':
                    profile_id, status, progress_text = data
                    if profile_id in self.profile_widgets:
                        self.profile_widgets[profile_id].update_status(status, progress_text)

                elif msg_type == 'crawl_finished':
                    self.is_crawling = False
                    self.should_stop = False
                    self.start_btn.configure(state="normal")
                    self.pause_btn.configure(state="disabled")
                    self.stop_btn.configure(state="disabled")
                    self.add_btn.configure(state="normal")
                    self.task_label.configure(text="현재 작업: 대기 중")

        except queue.Empty:
            pass

        # Schedule next check
        self.after(100, self._process_message_queue)

    def on_closing(self):
        """Handle window close event."""
        if self.is_crawling:
            if messagebox.askyesno("확인", "크롤링이 진행 중입니다. 종료하시겠습니까?"):
                self.should_stop = True
                save_progress(self.progress_data)
                self.db.close()
                self.destroy()
        else:
            self.db.close()
            self.destroy()


def verify_access() -> bool:
    """Verify access code before starting the application.

    Returns:
        True if access is granted, False otherwise
    """
    # Create a simple dialog for access code input
    dialog = ctk.CTk()
    dialog.title("인증")
    dialog.geometry("350x180")
    dialog.resizable(False, False)

    # Center the dialog
    dialog.update_idletasks()
    x = (dialog.winfo_screenwidth() - 350) // 2
    y = (dialog.winfo_screenheight() - 180) // 2
    dialog.geometry(f"350x180+{x}+{y}")

    result = {"verified": False}

    # Label
    label = ctk.CTkLabel(dialog, text="액세스 코드를 입력하세요", font=("", 14))
    label.pack(pady=(20, 10))

    # Entry
    code_entry = ctk.CTkEntry(dialog, width=250, placeholder_text="예: KATE2026Q1")
    code_entry.pack(pady=10)
    code_entry.focus()

    # Status label
    status_label = ctk.CTkLabel(dialog, text="", text_color="red")
    status_label.pack(pady=5)

    def check_code(event=None):
        code = code_entry.get().strip().upper()

        if not code:
            status_label.configure(text="코드를 입력해주세요")
            return

        expiry = ACCESS_CODES.get(code)

        if not expiry:
            status_label.configure(text="유효하지 않은 코드입니다")
            return

        expiry_date = datetime.strptime(expiry, "%Y-%m-%d")
        if datetime.now() > expiry_date:
            status_label.configure(text=f"만료된 코드입니다 (만료일: {expiry})")
            return

        result["verified"] = True
        dialog.destroy()

    # Bind Enter key
    code_entry.bind("<Return>", check_code)

    # Button
    btn = ctk.CTkButton(dialog, text="확인", command=check_code, width=100)
    btn.pack(pady=10)

    # Handle window close
    dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)

    dialog.mainloop()

    return result["verified"]


def main():
    """Main entry point."""
    # Verify access code first
    if not verify_access():
        return

    app = InstagramCrawlerApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()


if __name__ == "__main__":
    main()
