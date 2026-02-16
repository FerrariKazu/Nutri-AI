#!/usr/bin/env python3
import os
import time
import subprocess
import sys
import logging
from datetime import datetime

# Configuration
WATCH_DIR = "frontend"
MAX_FILE_SIZE_MB = 50
CHECK_INTERVAL_SECONDS = 30
GIT_REMOTE = "origin"
GIT_BRANCH = "main" # We will auto-detect

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [FRONTEND-SYNC] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("FrontendSync")

def get_file_size_mb(filepath):
    try:
        if os.path.isfile(filepath) and not os.path.islink(filepath):
            return os.path.getsize(filepath) / (1024 * 1024)
        return 0
    except OSError:
        return 0

def check_large_files(directory, max_size_mb):
    """Scan directory for files exceeding max_size_mb."""
    large_files = []
    for root, dirs, files in os.walk(directory):
        # Skip node_modules and .git explicitly as a failsafe
        if 'node_modules' in dirs:
            dirs.remove('node_modules')
        if '.git' in dirs:
            dirs.remove('.git')
        if 'dist' in dirs:
            dirs.remove('dist')
            
        for file in files:
            filepath = os.path.join(root, file)
            size = get_file_size_mb(filepath)
            if size > max_size_mb:
                large_files.append((filepath, size))
    return large_files

def run_git_command(command):
    """Run a git command and return output/success."""
    try:
        result = subprocess.run(
            command, 
            cwd=os.getcwd(), 
            check=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True
        )
        return True, result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return False, e.stderr.strip()

def get_current_branch():
    success, output = run_git_command(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    if success:
        return output
    return None

def has_frontend_changes():
    """Check if there are any changes in the frontend directory."""
    # Check for modified/deleted files
    success, output = run_git_command(["git", "status", "--porcelain", WATCH_DIR])
    if success and output:
        return True
    return False

def sync_frontend():
    # 1. Check for changes
    if not has_frontend_changes():
        return

    logger.info("Changes detected in frontend/...")

    # 2. Safety Scan for Large Files
    logger.info("Scanning for large files...")
    large_files = check_large_files(WATCH_DIR, MAX_FILE_SIZE_MB)
    if large_files:
        logger.warning(f"⚠️  BLOCKING SYNC: Found {len(large_files)} large files (> {MAX_FILE_SIZE_MB}MB):")
        for f, s in large_files:
            logger.warning(f"   - {f} ({s:.2f} MB)")
        logger.warning("Please remove these files or add them to .gitignore before syncing.")
        return

    # 3. Git Add
    logger.info("Staging changes...")
    success, _ = run_git_command(["git", "add", WATCH_DIR])
    if not success:
        logger.error("Failed to git add.")
        return

    # 4. Git Commit
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    commit_msg = f"chore(frontend): Auto-sync {timestamp}"
    logger.info(f"Committing: {commit_msg}")
    success, _ = run_git_command(["git", "commit", "-m", commit_msg])
    if not success:
        logger.error("Failed to commit (maybe nothing to commit?).")
        return

    # 5. Git Push
    current_branch = get_current_branch()
    if not current_branch:
        logger.error("Could not determine current branch.")
        return

    logger.info(f"Pushing to {GIT_REMOTE}/{current_branch}...")
    success, out = run_git_command(["git", "push", GIT_REMOTE, current_branch])
    if success:
        logger.info("✅ Push successful.")
    else:
        logger.error(f"❌ Push failed: {out}")

def main():
    logger.info(f"Starting Frontend Auto-Sync (Interval: {CHECK_INTERVAL_SECONDS}s, Max Size: {MAX_FILE_SIZE_MB}MB)")
    logger.info("Use Ctrl+C to stop.")

    try:
        while True:
            try:
                sync_frontend()
            except Exception as e:
                logger.error(f"Error during sync cycle: {e}")
            
            time.sleep(CHECK_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        logger.info("Stopping Auto-Sync.")

if __name__ == "__main__":
    main()
