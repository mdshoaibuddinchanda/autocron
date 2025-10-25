"""
Real-World Use Cases.

Practical examples for common automation scenarios.
"""

from autocron import AutoCron
import requests
from datetime import datetime


# Data Pipeline Automation
def data_pipeline():
    """ETL job - Extract, Transform, Load."""
    print(f"[{datetime.now()}] Running data pipeline...")
    # Extract data from source
    # Transform data
    # Load to destination
    print("Data pipeline completed!")


# Web Scraping
def scrape_website():
    """Scrape data from a website."""
    print(f"[{datetime.now()}] Scraping website...")
    try:
        # Example: Fetch data from API
        # response = requests.get('https://api.example.com/data')
        # data = response.json()
        print("Scraping completed!")
    except Exception as e:
        print(f"Scraping failed: {e}")


# System Maintenance
def system_cleanup():
    """Clean up temporary files and logs."""
    print(f"[{datetime.now()}] Running system cleanup...")
    # Clean temp files
    # Rotate logs
    # Clear cache
    print("System cleanup completed!")


# Report Generation
def generate_weekly_report():
    """Generate weekly business report."""
    print(f"[{datetime.now()}] Generating weekly report...")
    # Collect data
    # Generate report
    # Send to stakeholders
    print("Report generated and sent!")


# API Monitoring
def health_check():
    """Monitor API health."""
    print(f"[{datetime.now()}] Running health check...")
    try:
        # response = requests.get('https://api.example.com/health')
        # if response.status_code == 200:
        print("✓ API is healthy")
    except Exception as e:
        print(f"✗ API health check failed: {e}")


# Database Backup
def backup_database():
    """Backup database."""
    print(f"[{datetime.now()}] Starting database backup...")
    # Execute backup command
    # Verify backup
    # Upload to cloud storage
    print("Database backup completed!")


if __name__ == "__main__":
    scheduler = AutoCron(log_path="./logs/use_cases.log", log_level="INFO")

    # Data Pipeline - Every 4 hours
    scheduler.add_task(
        name="data_pipeline", func=data_pipeline, every="4h", retries=3, notify="desktop"
    )

    # Web Scraping - Every 30 minutes
    scheduler.add_task(name="web_scraper", func=scrape_website, every="30m", retries=5, timeout=120)

    # System Maintenance - Daily at 3 AM
    scheduler.add_task(name="system_cleanup", func=system_cleanup, cron="0 3 * * *", retries=2)

    # Weekly Report - Every Monday at 9 AM
    scheduler.add_task(
        name="weekly_report",
        func=generate_weekly_report,
        cron="0 9 * * 1",
        notify="email",
        email_config={
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "from_email": "reports@company.com",
            "to_email": "team@company.com",
            "password": "your_password",
        },
    )

    # API Health Check - Every 5 minutes
    scheduler.add_task(name="health_check", func=health_check, every="5m", timeout=30)

    # Database Backup - Daily at 2 AM
    scheduler.add_task(
        name="db_backup", func=backup_database, cron="0 2 * * *", retries=3, notify="email"
    )

    print("=" * 70)
    print("AutoCron - Real-World Use Cases")
    print("=" * 70)
    print("\nScheduled tasks:")
    print("  1. Data Pipeline    - Every 4 hours")
    print("  2. Web Scraper      - Every 30 minutes")
    print("  3. System Cleanup   - Daily at 3:00 AM")
    print("  4. Weekly Report    - Mondays at 9:00 AM")
    print("  5. Health Check     - Every 5 minutes")
    print("  6. Database Backup  - Daily at 2:00 AM")
    print("\nPress Ctrl+C to stop")
    print("=" * 70)
    print()

    # Start the scheduler
    scheduler.start(blocking=True)
