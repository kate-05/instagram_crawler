# Instagram Crawler 구현 계획

## 프로젝트 개요
- **프로젝트명**: Instagram Crawler (인스타그램 크롤러)
- **위치**: `D:\PythonProject_Kate\Claude_InstaExtractor`
- **GUI 참조**: `D:\PythonProject_Kate\Claude_YTBExtractor` 와 동일한 스타일

## 수집 대상 데이터
1. **프로필** - 사용자명, 팔로워, 팔로잉, 게시물 수, 바이오
2. **게시물** - 이미지/동영상, 캡션, 좋아요 수, 댓글 수, 해시태그
3. **릴스** - 릴스 동영상, 조회수, 좋아요, 댓글
4. **스토리** - 스토리 이미지/동영상 (로그인 필요)
5. **하이라이트** - 하이라이트 컬렉션 및 내용 (로그인 필요)
6. **댓글** - 게시물별 댓글 및 답글
7. **좋아요** - 좋아요 수 (사용자 목록은 제한적)
8. **해시태그** - 게시물에서 추출한 해시태그

## 기술 스택
- **GUI**: CustomTkinter (YTBExtractor와 동일)
- **크롤링**: instaloader (가장 안정적인 인스타그램 라이브러리)
- **데이터베이스**: SQLite
- **언어**: Python 3.x

---

## 프로젝트 구조

```
D:\PythonProject_Kate\Claude_InstaExtractor\instagram_crawler/
├── main.py                      # GUI 애플리케이션 진입점
├── config.py                    # 설정 파일
├── requirements.txt             # 의존성
├── crawler/                     # 크롤러 모듈
│   ├── __init__.py
│   ├── profile.py              # 프로필 정보 수집
│   ├── posts.py                # 게시물 수집
│   ├── reels.py                # 릴스 수집
│   ├── stories.py              # 스토리 수집
│   ├── highlights.py           # 하이라이트 수집
│   ├── comments.py             # 댓글 수집
│   └── hashtags.py             # 해시태그 분석
├── database/                    # 데이터베이스 모듈
│   ├── __init__.py
│   ├── models.py               # SQLite 스키마
│   └── manager.py              # CRUD 작업
├── utils/                       # 유틸리티
│   ├── __init__.py
│   └── helpers.py              # 진행상태, 내보내기
├── exports/                     # 내보내기 폴더 (자동 생성)
├── sessions/                    # 로그인 세션 저장 폴더
├── crawl_progress.json         # 진행 상태 파일
└── instagram_crawler.db        # SQLite 데이터베이스
```

---

## 데이터베이스 스키마

### 1. profiles (프로필)
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | INTEGER PK | 고유 ID |
| username | TEXT UNIQUE | 인스타그램 사용자명 |
| full_name | TEXT | 표시 이름 |
| biography | TEXT | 바이오 |
| follower_count | INTEGER | 팔로워 수 |
| following_count | INTEGER | 팔로잉 수 |
| post_count | INTEGER | 게시물 수 |
| is_private | BOOLEAN | 비공개 계정 여부 |
| profile_pic_url | TEXT | 프로필 사진 URL |
| status | TEXT | 크롤링 상태 |
| created_at | TIMESTAMP | 생성 시간 |

### 2. posts (게시물)
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | INTEGER PK | 고유 ID |
| profile_id | INTEGER FK | 프로필 ID |
| shortcode | TEXT UNIQUE | 게시물 고유 코드 |
| post_type | TEXT | 타입 (image/video/carousel/reel) |
| caption | TEXT | 캡션 |
| like_count | INTEGER | 좋아요 수 |
| comment_count | INTEGER | 댓글 수 |
| view_count | INTEGER | 조회수 (동영상) |
| media_url | TEXT | 미디어 URL |
| posted_at | TIMESTAMP | 게시 시간 |
| created_at | TIMESTAMP | 수집 시간 |

### 3. stories (스토리)
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | INTEGER PK | 고유 ID |
| profile_id | INTEGER FK | 프로필 ID |
| media_type | TEXT | 타입 (image/video) |
| media_url | TEXT | 미디어 URL |
| posted_at | TIMESTAMP | 게시 시간 |
| expires_at | TIMESTAMP | 만료 시간 |
| created_at | TIMESTAMP | 수집 시간 |

### 4. highlights (하이라이트)
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | INTEGER PK | 고유 ID |
| profile_id | INTEGER FK | 프로필 ID |
| title | TEXT | 하이라이트 제목 |
| cover_url | TEXT | 커버 이미지 URL |
| item_count | INTEGER | 아이템 수 |
| created_at | TIMESTAMP | 수집 시간 |

### 5. highlight_items (하이라이트 아이템)
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | INTEGER PK | 고유 ID |
| highlight_id | INTEGER FK | 하이라이트 ID |
| media_type | TEXT | 타입 (image/video) |
| media_url | TEXT | 미디어 URL |
| posted_at | TIMESTAMP | 게시 시간 |

### 6. comments (댓글)
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | INTEGER PK | 고유 ID |
| post_id | INTEGER FK | 게시물 ID |
| parent_id | INTEGER FK | 부모 댓글 ID (답글용) |
| username | TEXT | 작성자 |
| text | TEXT | 댓글 내용 |
| like_count | INTEGER | 좋아요 수 |
| posted_at | TIMESTAMP | 작성 시간 |
| created_at | TIMESTAMP | 수집 시간 |

### 7. hashtags (해시태그)
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | INTEGER PK | 고유 ID |
| post_id | INTEGER FK | 게시물 ID |
| tag | TEXT | 해시태그 (# 제외) |

---

## GUI 구성 (YTBExtractor 스타일 통일)

### 메인 윈도우
- **제목**: "인스타그램 크롤러"
- **크기**: 900x700 (인스타 데이터가 더 많아 약간 확대)
- **테마**: 다크모드, 블루 컬러

### UI 섹션

1. **로그인 섹션** (상단)
   - 세션 쿠키 입력 또는 ID/PW 로그인
   - 로그인 상태 표시
   - "로그인" / "로그아웃" 버튼

2. **계정 입력 섹션**
   - 라벨: "계정 URL 또는 사용자명 입력:"
   - 입력 필드 + "추가" 버튼

3. **수집 옵션 체크박스**
   - [x] 프로필 정보
   - [x] 게시물
   - [x] 릴스
   - [ ] 스토리 (로그인 필요)
   - [ ] 하이라이트 (로그인 필요)
   - [x] 댓글
   - [x] 해시태그

4. **계정 목록 섹션**
   - 스크롤 가능한 리스트
   - 각 항목: 체크박스, 사용자명, 상태, 삭제 버튼

5. **진행 상태 섹션**
   - 전체 진행률 표시
   - 프로그레스 바
   - 현재 작업 표시

6. **로그 영역**
   - 타임스탬프 포함 로그 메시지

7. **컨트롤 버튼**
   - 시작 / 일시정지 / 중지 / 내보내기

---

## 크롤링 워크플로우

### 단계 (CrawlStep)
1. `PROFILE_INFO` - 프로필 기본 정보
2. `POST_LIST` - 게시물 목록 수집
3. `POST_DETAILS` - 게시물 상세 (좋아요, 미디어)
4. `REELS` - 릴스 수집
5. `STORIES` - 스토리 수집 (로그인 필요)
6. `HIGHLIGHTS` - 하이라이트 수집 (로그인 필요)
7. `COMMENTS` - 댓글 수집
8. `HASHTAGS` - 해시태그 추출/분석

### 진행 상태 추적
- `crawl_progress.json` 파일로 저장
- 중단 후 재개 가능
- 단계별 진행 상황 저장

---

## 구현 순서

### Phase 1: 기본 구조 (파일 생성)
1. `config.py` - 설정 파일
2. `requirements.txt` - 의존성
3. `database/models.py` - DB 스키마
4. `database/manager.py` - DB 매니저

### Phase 2: 크롤러 모듈
1. `crawler/profile.py` - 프로필 크롤러
2. `crawler/posts.py` - 게시물 크롤러
3. `crawler/reels.py` - 릴스 크롤러
4. `crawler/stories.py` - 스토리 크롤러
5. `crawler/highlights.py` - 하이라이트 크롤러
6. `crawler/comments.py` - 댓글 크롤러
7. `crawler/hashtags.py` - 해시태그 분석

### Phase 3: 유틸리티
1. `utils/helpers.py` - 진행상태, 내보내기

### Phase 4: GUI
1. `main.py` - 메인 애플리케이션

---

## 주요 고려사항

### 1. 레이트 리밋 대응
- 요청 간 딜레이 (2-5초)
- 429 에러 시 자동 대기
- 일일 요청 한도 관리

### 2. 로그인 세션 관리
- 세션 파일 저장/로드
- 세션 만료 감지 및 재로그인

### 3. 비공개 계정 처리
- 비공개 계정 감지
- 팔로우 상태 확인
- 접근 불가 시 스킵

### 4. 미디어 다운로드 (선택적)
- 이미지/동영상 URL 저장
- 실제 파일 다운로드 옵션

---

## 내보내기 형식

### JSON
```json
{
  "profile": {...},
  "posts": [...],
  "reels": [...],
  "stories": [...],
  "highlights": [...],
  "comments": [...],
  "hashtags": [...]
}
```

### CSV
- `{username}_profile.csv`
- `{username}_posts.csv`
- `{username}_comments.csv`
- `{username}_hashtags.csv`

---

## 검증 방법

1. **단위 테스트**
   - 각 크롤러 모듈 테스트
   - DB 작업 테스트

2. **통합 테스트**
   - 공개 계정으로 전체 워크플로우 테스트
   - 로그인 후 스토리/하이라이트 테스트

3. **GUI 테스트**
   - 모든 버튼 동작 확인
   - 진행 상태 표시 확인
   - 내보내기 기능 확인
