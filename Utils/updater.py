import time
from logging import getLogger
from locales.localizer import Localizer
import requests
import os
import zipfile
import shutil
import json
import re

logger = getLogger("FPS.update_checker")
localizer = Localizer()
_ = localizer.translate

REPOSITORY = "qorexdevs/FunPaySigma"
TAGS_URL = f"https://api.github.com/repos/{REPOSITORY}/tags"
RELEASES_URL = f"https://api.github.com/repos/{REPOSITORY}/releases"
LATEST_RELEASE_URL = f"{RELEASES_URL}/latest"

HEADERS = {
    "accept": "application/vnd.github+json",
    "User-Agent": "FunPaySigma-updater",
    "X-GitHub-Api-Version": "2022-11-28"
}

CACHE_FILE = "storage/cache/release_cache.json"
CACHE_TTL = 3600

class Release:

    def __init__(self, name: str, description: str, sources_link: str, tag_name: str | None = None):

        self.name = name
        self.description = description
        self.sources_link = sources_link
        self.tag_name = tag_name or name


def get_tags(current_tag: str) -> list[str] | None:
    """Cardinal-compatible tag lookup for the Sigma repository."""
    try:
        response = requests.get(TAGS_URL, headers=HEADERS, timeout=15)
        response.raise_for_status()
        tags = [item.get("name") for item in response.json() if item.get("name")]
        return tags or None
    except requests.RequestException:
        logger.debug("TRACEBACK", exc_info=True)
        return None


def get_next_tag(tags: list[str], current_tag: str):
    """Возвращает следующий тег по правилам обновлятора Cardinal."""
    try:
        current_index = tags.index(current_tag)
    except ValueError:
        return tags[-1] if tags else None
    return None if current_index == 0 else tags[current_index - 1]


def get_releases(from_tag: str) -> list[Release] | None:
    """Cardinal-compatible release lookup against qorexdevs/FunPaySigma."""
    try:
        response = requests.get(RELEASES_URL, headers=HEADERS, timeout=15)
        response.raise_for_status()
        releases = response.json()
        start = next((index for index, item in enumerate(releases)
                      if item.get("tag_name") == from_tag), None)
        if start is None:
            return None
        return [Release(item.get("tag_name", ""), item.get("body") or "",
                        item.get("zipball_url", ""), item.get("tag_name"))
                for item in reversed(releases[:start + 1])]
    except requests.RequestException:
        logger.debug("TRACEBACK", exc_info=True)
        return None

def parse_semver(version_str: str) -> tuple | None:
    version_str = version_str.lstrip('v')
    match = re.match(r'^(\d+)\.(\d+)\.(\d+)', version_str)
    if match:
        return (int(match.group(1)), int(match.group(2)), int(match.group(3)))
    return None

def is_semver(version_str: str) -> bool:
    return parse_semver(version_str) is not None

def compare_semver(version1: str, version2: str) -> int:
    v1 = parse_semver(version1)
    v2 = parse_semver(version2)

    if v1 is None or v2 is None:
        return 0

    if v1 > v2:
        return 1
    elif v1 < v2:
        return -1
    return 0

def _load_cache() -> dict | None:
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                cache = json.load(f)
                if (cache.get("repository") == REPOSITORY
                        and time.time() - cache.get("timestamp", 0) < CACHE_TTL):
                    return cache.get("release")
    except:
        pass
    return None

def _save_cache(release_data: dict):
    try:
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({"repository": REPOSITORY, "timestamp": time.time(), "release": release_data}, f)
    except:
        pass

def get_latest_release(max_retries: int = 3) -> Release | None:
    cached = _load_cache()
    if cached:
        logger.debug("Используем кэшированные данные о релизе")
        return Release(
            cached["tag_name"],
            cached["body"],
            cached["zipball_url"],
            cached["tag_name"]
        )

    for attempt in range(max_retries):
        try:
            response = requests.get(LATEST_RELEASE_URL, headers=HEADERS, timeout=15)

            if response.status_code == 403:
                remaining = response.headers.get("X-RateLimit-Remaining", "0")
                reset_time = response.headers.get("X-RateLimit-Reset")
                if remaining == "0" and reset_time:
                    wait_seconds = int(reset_time) - int(time.time()) + 5
                    if wait_seconds > 0 and wait_seconds < 300:
                        logger.warning(f"Rate limit. Ждём {wait_seconds} сек...")
                        time.sleep(wait_seconds)
                        continue
                    else:
                        logger.warning("Rate limit GitHub API. Попробуй позже.")
                        return None

            response.raise_for_status()
            release = response.json()

            _save_cache(release)

            return Release(
                release["tag_name"],
                release["body"],
                release["zipball_url"],
                release["tag_name"]
            )
        except requests.exceptions.RequestException as e:
            logger.warning(f"Попытка {attempt + 1} получить последний релиз не удалась: {e}")
            if attempt < max_retries - 1:
                time.sleep(5 * (attempt + 1))
            else:
                logger.error("Не удалось получить последний релиз с GitHub.")
                logger.debug("TRACEBACK", exc_info=True)
                return None
        except Exception:
            logger.debug("TRACEBACK", exc_info=True)
            return None

def get_new_releases(current_tag: str) -> int | list[Release]:
    latest = get_latest_release()
    if latest is None:
        return 3

    if not is_semver(latest.tag_name):
        return 2

    if not is_semver(current_tag):
        return [latest]

    if compare_semver(latest.tag_name, current_tag) > 0:
        return [latest]

    return 2

def get_skipped_count(releases: list[Release]) -> int:
    return 0

def format_version_info(current_version: str, releases: list[Release]) -> dict:
    return {
        "current": current_version,
        "latest": releases[0].tag_name if releases else current_version,
        "skipped": 0,
        "total_available": len(releases)
    }

def download_zip(url: str, max_retries: int = 3) -> int:

    for attempt in range(max_retries):
        try:
            with requests.get(url, stream=True, timeout=30) as r:
                r.raise_for_status()
                with open("storage/cache/update.zip", 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            return 0
        except Exception as e:
            logger.warning(f"Попытка {attempt + 1} скачать обновление не удалась: {e}")
            if attempt < max_retries - 1:
                time.sleep(5)
            else:
                logger.error("Не удалось скачать обновление с GitHub.")
                logger.debug("TRACEBACK", exc_info=True)
                return 1

def extract_update_archive() -> str | int:

    try:
        if os.path.exists("storage/cache/update/"):
            shutil.rmtree("storage/cache/update/", ignore_errors=True)
        os.makedirs("storage/cache/update")

        with zipfile.ZipFile("storage/cache/update.zip", "r") as zip:
            folder_name = zip.filelist[0].filename
            zip.extractall("storage/cache/update/")
        return folder_name
    except:
        logger.debug("TRACEBACK", exc_info=True)
        return 1

def zipdir(path, zip_obj, exclude_dirs=None, exclude_extensions=None):
    if exclude_dirs is None:
        exclude_dirs = set()
    if exclude_extensions is None:
        exclude_extensions = set()

    exclude_dirs = exclude_dirs | {"__pycache__", "cache", ".git", ".hypothesis", ".pytest_cache"}
    exclude_extensions = exclude_extensions | {".pyc", ".pyo", ".log", ".zip"}

    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]

        for file in files:
            if any(file.endswith(ext) for ext in exclude_extensions):
                continue
            zip_obj.write(os.path.join(root, file),
                          os.path.relpath(os.path.join(root, file),
                                          os.path.join(path, '..')))

def create_backup() -> int:
    try:
        cache_cleanup_dirs = ["storage/cache/backup", "storage/cache/update"]
        cache_cleanup_files = ["storage/cache/backup.zip", "storage/cache/update.zip"]

        for d in cache_cleanup_dirs:
            if os.path.exists(d):
                shutil.rmtree(d, ignore_errors=True)

        for f in cache_cleanup_files:
            if os.path.exists(f):
                os.remove(f)

        with zipfile.ZipFile("backup.zip", "w", zipfile.ZIP_DEFLATED) as zip:
            zipdir("storage", zip)
            zipdir("configs", zip)
            zipdir("plugins", zip)
        return 0
    except:
        logger.debug("TRACEBACK", exc_info=True)
        return 1

def extract_backup_archive() -> bool:

    try:
        if os.path.exists("storage/cache/backup/"):
            shutil.rmtree("storage/cache/backup/", ignore_errors=True)
        os.makedirs("storage/cache/backup")

        with zipfile.ZipFile("storage/cache/backup.zip", "r") as zip:
            zip.extractall("storage/cache/backup/")
        return True
    except:
        logger.debug("TRACEBACK", exc_info=True)
        return False

def install_release(folder_name: str) -> int:

    try:
        release_folder = os.path.join("storage/cache/update", folder_name)
        if not os.path.exists(release_folder):
            return 2

        if os.path.exists(os.path.join(release_folder, "delete.json")):
            with open(os.path.join(release_folder, "delete.json"), "r", encoding="utf-8") as f:
                data = json.loads(f.read())
                for i in data:
                    if not os.path.exists(i):
                        continue
                    if os.path.isfile(i):
                        os.remove(i)
                    else:
                        shutil.rmtree(i, ignore_errors=True)

        for i in os.listdir(release_folder):
            if i == "delete.json":
                continue

            source = os.path.join(release_folder, i)
            if source.endswith(".exe"):
                if not os.path.exists("update"):
                    os.mkdir("update")
                shutil.copy2(source, os.path.join("update", i))
                continue

            if os.path.isfile(source):
                shutil.copy2(source, i)
            else:
                shutil.copytree(source, os.path.join(".", i), dirs_exist_ok=True)
        return 0
    except:
        logger.debug("TRACEBACK", exc_info=True)
        return 1

def install_backup() -> bool:

    try:
        backup_folder = "storage/cache/backup"
        if not os.path.exists(backup_folder):
            return False

        for i in os.listdir(backup_folder):
            source = os.path.join(backup_folder, i)

            if os.path.isfile(source):
                shutil.copy2(source, i)
            else:
                shutil.copytree(source, os.path.join(".", i), dirs_exist_ok=True)
        return True
    except:
        logger.debug("TRACEBACK", exc_info=True)
        return False
