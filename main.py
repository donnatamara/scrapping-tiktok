import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Settings
from logger import setup_logger
from database import Database
from scraper import TikTokScraper


def parse_args():
    parser = argparse.ArgumentParser(description="TikTok Banyumas Scraper")
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Jalankan browser tanpa UI",
    )
    parser.add_argument(
        "--visible",
        action="store_true",
        help="Tampilkan browser",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Mode debug (log lebih detail)",
    )
    parser.add_argument(
        "--connect",
        type=str,
        default="",
        help="Connect ke remote Chrome via CDP (contoh: http://localhost:9222)",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    settings = Settings()

    if args.headless:
        settings.HEADLESS = True
    elif args.visible:
        settings.HEADLESS = False

    if args.connect:
        settings.REMOTE_CDP = args.connect

    log_level = "DEBUG" if args.debug else "INFO"

    logger = setup_logger(settings.LOG_FILE, log_level)
    logger.info("=" * 60)
    logger.info("TIKTOK BANYUMAS SCRAPER v2.0")
    logger.info("=" * 60)
    mode = f"REMOTE CDP: {settings.REMOTE_CDP}" if settings.REMOTE_CDP else ("HEADLESS" if settings.HEADLESS else "VISIBLE")
    logger.info(f"Mode: {mode}")

    db = Database(settings.DATABASE_PATH)
    db.connect()
    logger.info(f"Database: {settings.DATABASE_PATH}")

    scraper = TikTokScraper(settings, db, logger)

    try:
        scraper.run()
    except KeyboardInterrupt:
        logger.warning("Scraping dihentikan oleh user")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        raise
    finally:
        logger.info("Mengekspor ke CSV...")
        db.export_csv(settings.ACCOUNTS_CSV, settings.VIDEOS_CSV)

        account_count = db.get_account_count()
        video_count = db.get_video_count()

        print()
        print("=" * 60)
        print("  SCRAPING SELESAI")
        print("=" * 60)
        print(f"  Database : {settings.DATABASE_PATH}")
        print(f"  Accounts : {settings.ACCOUNTS_CSV} ({account_count} akun)")
        print(f"  Videos   : {settings.VIDEOS_CSV} ({video_count} video)")
        print("=" * 60)
        print()

        db.close()


if __name__ == "__main__":
    main()
