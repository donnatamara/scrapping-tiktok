import sqlite3
import csv
import os
from pathlib import Path
from typing import List, Optional

from models import Account, Video


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        if db_path != ":memory:":
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn: Optional[sqlite3.Connection] = None

    def connect(self):
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._create_tables()
        self._migrate()

    def _create_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS accounts (
                username TEXT PRIMARY KEY,
                unique_id TEXT,
                nickname TEXT,
                bio TEXT,
                profile_url TEXT,
                avatar_url TEXT,
                followers INTEGER,
                following INTEGER,
                total_likes INTEGER,
                video_count INTEGER,
                verified INTEGER DEFAULT 0,
                private_account INTEGER DEFAULT 0,
                business_account INTEGER,
                email TEXT,
                website TEXT,
                instagram TEXT,
                youtube TEXT,
                linktree TEXT,
                whatsapp TEXT,
                facebook TEXT,
                profile_location TEXT,
                location_detected TEXT,
                location_source TEXT,
                creator_keywords TEXT,
                creator_keywords_found TEXT,
                business_indicators_found TEXT,
                live_detected INTEGER,
                has_tiktok_shop INTEGER,
                monetization INTEGER,
                average_views REAL,
                average_likes REAL,
                average_comments REAL,
                average_shares REAL,
                engagement_rate REAL,
                scraped_at TEXT
            );

            CREATE TABLE IF NOT EXISTS videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id TEXT,
                caption TEXT,
                upload_date TEXT,
                video_url TEXT,
                views INTEGER,
                likes INTEGER,
                comments INTEGER,
                shares INTEGER,
                duration INTEGER,
                hashtags TEXT,
                music TEXT,
                video_location TEXT,
                scraped_at TEXT,
                FOREIGN KEY (account_id) REFERENCES accounts(username)
            );

            CREATE INDEX IF NOT EXISTS idx_videos_account ON videos(account_id);
        """)
        self.conn.commit()

    def _migrate(self):
        migrations = [
            ("ALTER TABLE accounts ADD COLUMN profile_location TEXT",),
            ("ALTER TABLE accounts ADD COLUMN profile_location TEXT",),
            ("ALTER TABLE accounts ADD COLUMN monetization INTEGER",),
            ("ALTER TABLE videos ADD COLUMN video_location TEXT",),
        ]
        for sql in migrations:
            try:
                self.conn.execute(sql[0])
            except sqlite3.OperationalError:
                pass
        try:
            self.conn.execute("ALTER TABLE accounts RENAME COLUMN tiktok_shop TO has_tiktok_shop")
        except sqlite3.OperationalError:
            pass
        self.conn.commit()

    def account_exists(self, username: str) -> bool:
        cursor = self.conn.execute(
            "SELECT 1 FROM accounts WHERE username = ?", (username,)
        )
        return cursor.fetchone() is not None

    def save_account(self, account: Account):
        self.conn.execute("""
            INSERT OR REPLACE INTO accounts (
                username, unique_id, nickname, bio,
                profile_url, avatar_url, followers, following,
                total_likes, video_count, verified, private_account,
                business_account, email, website, instagram,
                youtube, linktree, whatsapp, facebook,
                profile_location, location_detected, location_source,
                creator_keywords, creator_keywords_found,
                business_indicators_found,
                live_detected, has_tiktok_shop, monetization,
                average_views, average_likes, average_comments,
                average_shares, engagement_rate, scraped_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            account.username, account.unique_id, account.nickname, account.bio,
            account.profile_url, account.avatar_url, account.followers, account.following,
            account.total_likes, account.video_count, int(account.verified), int(account.private_account),
            account.business_account, account.email, account.website, account.instagram,
            account.youtube, account.linktree, account.whatsapp, account.facebook,
            account.profile_location, account.location_detected, account.location_source,
            account.creator_keywords, account.creator_keywords_found,
            account.business_indicators_found,
            account.live_detected, account.has_tiktok_shop, account.monetization,
            account.average_views, account.average_likes, account.average_comments,
            account.average_shares, account.engagement_rate, account.scraped_at,
        ))
        self.conn.commit()

    def save_video(self, video: Video):
        self.conn.execute("""
            INSERT INTO videos (
                account_id, caption, upload_date, video_url,
                views, likes, comments, shares,
                duration, hashtags, music, video_location, scraped_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            video.account_id, video.caption, video.upload_date, video.video_url,
            video.views, video.likes, video.comments, video.shares,
            video.duration, video.hashtags, video.music, video.video_location,
            video.scraped_at,
        ))
        self.conn.commit()

    def get_all_accounts(self) -> List[dict]:
        cursor = self.conn.execute("SELECT * FROM accounts")
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def get_all_videos(self) -> List[dict]:
        cursor = self.conn.execute("SELECT * FROM videos")
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def export_csv(self, accounts_path: str, videos_path: str):
        accounts = self.get_all_accounts()
        videos = self.get_all_videos()

        os.makedirs(os.path.dirname(accounts_path), exist_ok=True)

        if accounts:
            with open(accounts_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=accounts[0].keys())
                writer.writeheader()
                writer.writerows(accounts)

        if videos:
            with open(videos_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=videos[0].keys())
                writer.writeheader()
                writer.writerows(videos)

    def get_account_count(self) -> int:
        cursor = self.conn.execute("SELECT COUNT(*) FROM accounts")
        return cursor.fetchone()[0]

    def get_video_count(self) -> int:
        cursor = self.conn.execute("SELECT COUNT(*) FROM videos")
        return cursor.fetchone()[0]

    def close(self):
        if self.conn:
            self.conn.close()
