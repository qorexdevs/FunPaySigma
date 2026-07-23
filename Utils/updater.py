import time
from logging import getLogger
from locales.localizer import Localizer
import requests
import os
import zipfile
import shutil
import json
import re
import html as html_lib
from urllib.parse import unquote
from xml.etree import ElementTree

logger = getLogger("FPS.update_checker")
localizer = Localizer()
_ = localizer.translate

REPOSITORY = "qorexdevs/FunPaySigma"
TAGS_URL = f"https://api.github.com/repos/{REPOSITORY}/tags"
RELEASES_URL = f"https://api.github.com/repos/{REPOSITORY}/releases"
LATEST_RELEASE_URL = f"{RELEASES_URL}/latest"
LATEST_RELEASE_PAGE_URL = f"https://github.com/{REPOSITORY}/releases/latest"
RELEASES_ATOM_URL = f"https://github.com/{REPOSITORY}/releases.atom"

HEADERS = {
    "accept": "application/vnd.github+json",
    "User-Agent": "FunPaySigma-updater",
    "X-GitHub-Api-Version": "2022-11-28"
}

CACHE_FILE = "storage/cache/release_cache.json"
CACHE_TTL = 300

class Release:

    def __init__(self, name: str, description: str, sources_link: str, tag_name: str | None = None):

        self.name = name
        self.description = description or ""
        self.sources_link = sources_link
        self.tag_name = tag_name or name


def _archive_url(tag_name: str) -> str:
    return f"https://github.com/{REPOSITORY}/archive/refs/tags/{tag_name}.zip"


def _release_from_data(data: dict | None) -> Release | None:
    if not isinstance(data, dict):
        return None
    tag_name = data.get("tag_name") or data.get("name")
    if not isinstance(tag_name, str) or not tag_name.strip():
        return None
    tag_name = tag_name.strip()
    return Release(tag_name, data.get("body") or "", _archive_url(tag_name), tag_name)


def _strip_atom_html(value: str | None) -> str:
    if not value:
        return ""
    value = re.sub(r"<br\s*/?>", "\n", value, flags=re.IGNORECASE)
    value = re.sub(r"<li[^>]*>", "- ", value, flags=re.IGNORECASE)
    value = re.sub(r"</(?:p|li|h[1-6])>", "\n", value, flags=re.IGNORECASE)
    value = re.sub(r"<[^>]+>", "", value)
    value = html_lib.unescape(value).replace("\r", "")
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def _get_atom_releases() -> list[Release]:
    try:
        response = requests.get(RELEASES_ATOM_URL, headers=HEADERS, timeout=12)
        response.raise_for_status()
        root = ElementTree.fromstring(response.content)
        namespace = {"atom": "http://www.w3.org/2005/Atom"}
        releases = []
        for entry in root.findall("atom:entry", namespace):
            link = entry.find("atom:link[@rel='alternate']", namespace)
            href = link.get("href", "") if link is not None else ""
            match = re.search(r"/releases/tag/([^/?#]+)", href)
            if not match:
                continue
            tag_name = unquote(match.group(1))
            content = entry.find("atom:content", namespace)
            description = _strip_atom_html(content.text if content is not None else "")
            releases.append(Release(tag_name, description, _archive_url(tag_name), tag_name))
        return releases
    except Exception as error:
        logger.warning(f"Не удалось прочитать GitHub Atom feed: {error}")
        logger.debug("TRACEBACK", exc_info=True)
        return []


def _get_latest_from_release_page() -> Release | None:
    try:
        response = requests.get(LATEST_RELEASE_PAGE_URL, headers=HEADERS, timeout=12,
                                allow_redirects=False)
        locations = [response.headers.get("Location", ""), response.url, response.text[:10000]]
        for value in locations:
            match = re.search(r"/releases/tag/([^/?#\"']+)", value or "")
            if match:
                tag_name = unquote(match.group(1))
                return Release(tag_name, "", _archive_url(tag_name), tag_name)
        response.raise_for_status()
    except Exception as error:
        logger.warning(f"Не удалось определить latest release по GitHub redirect: {error}")
        logger.debug("TRACEBACK", exc_info=True)
    return None


def get_tags(current_tag: str) -> list[str] | None:
    """Cardinal-compatible tag lookup for the Sigma repository."""
    try:
        response = requests.get(TAGS_URL, headers=HEADERS, timeout=15)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            raise ValueError("GitHub tags API вернул неожиданный формат")
        tags = [item.get("name") for item in payload if isinstance(item, dict) and item.get("name")]
        return tags or None
    except (requests.RequestException, ValueError, TypeError):
        logger.debug("TRACEBACK", exc_info=True)
        tags = [release.tag_name for release in _get_atom_releases()]
        return tags or None


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
        if not isinstance(releases, list):
            raise ValueError("GitHub releases API вернул неожиданный формат")
        start = next((index for index, item in enumerate(releases)
                      if isinstance(item, dict) and item.get("tag_name") == from_tag), None)
        if start is None:
            return None
        return [release for item in reversed(releases[:start + 1])
                if (release := _release_from_data(item)) is not None]
    except (requests.RequestException, ValueError, TypeError):
        logger.debug("TRACEBACK", exc_info=True)
        releases = _get_atom_releases()
        start = next((index for index, release in enumerate(releases)
                      if release.tag_name == from_tag), None)
        if start is None:
            return None
        return list(reversed(releases[:start + 1]))

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

def _load_cache(allow_stale: bool = False) -> dict | None:
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                cache = json.load(f)
                if cache.get("repository") != REPOSITORY:
                    return None
                release = cache.get("release")
                if _release_from_data(release) is None:
                    return None
                is_fresh = time.time() - cache.get("timestamp", 0) < CACHE_TTL
                return release if allow_stale or is_fresh else None
    except Exception:
        logger.debug("Не удалось прочитать кэш обновлений", exc_info=True)
    return None

def _save_cache(release_data: dict | Release):
    try:
        if isinstance(release_data, Release):
            release_data = {
                "tag_name": release_data.tag_name,
                "body": release_data.description,
                "zipball_url": release_data.sources_link,
            }
        release = _release_from_data(release_data)
        if release is None:
            return
        normalized = {
            "tag_name": release.tag_name,
            "body": release.description,
            "zipball_url": release.sources_link,
        }
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({"repository": REPOSITORY, "timestamp": time.time(), "release": normalized},
                      f, ensure_ascii=False)
    except Exception:
        logger.debug("Не удалось сохранить кэш обновлений", exc_info=True)

def get_latest_release(max_retries: int = 3, force_refresh: bool = False) -> Release | None:
    cached = None if force_refresh else _load_cache()
    if cached:
        logger.debug("Используем кэшированные данные о релизе")
        return _release_from_data(cached)

    for attempt in range(max_retries):
        try:
            response = requests.get(LATEST_RELEASE_URL, headers=HEADERS, timeout=12)

            if response.status_code == 403:
                remaining = response.headers.get("X-RateLimit-Remaining", "0")
                if remaining == "0":
                    logger.warning("GitHub API rate limit исчерпан, переключаюсь на fallback.")
                    break

            response.raise_for_status()
            release = _release_from_data(response.json())
            if release is None:
                raise ValueError("GitHub API вернул релиз без tag_name")
            _save_cache(release)
            return release
        except (requests.exceptions.RequestException, ValueError, TypeError) as e:
            logger.warning(f"Попытка {attempt + 1} получить последний релиз не удалась: {e}")
            if attempt < max_retries - 1:
                time.sleep(min(2 * (attempt + 1), 5))
        except Exception:
            logger.debug("TRACEBACK", exc_info=True)
            break

    atom_releases = _get_atom_releases()
    if atom_releases:
        release = atom_releases[0]
        _save_cache(release)
        logger.info("Последний релиз получен через GitHub Atom fallback.")
        return release

    release = _get_latest_from_release_page()
    if release is not None:
        _save_cache(release)
        logger.info("Последний релиз получен через GitHub redirect fallback.")
        return release

    stale_cache = _load_cache(allow_stale=True)
    if stale_cache:
        logger.warning("GitHub недоступен, использую последний сохранённый release-кэш.")
        return _release_from_data(stale_cache)

    logger.error("Не удалось получить последний релиз ни одним способом.")
    return None

def get_new_releases(current_tag: str) -> int | list[Release]:
    latest = get_latest_release()
    if latest is None:
        return 3

    if not is_semver(latest.tag_name):
        return 2

    if not is_semver(current_tag):
        return [latest]

    comparison = compare_semver(latest.tag_name, current_tag)
    if comparison < 0:
        refreshed = get_latest_release(force_refresh=True)
        if refreshed is not None:
            latest = refreshed
            comparison = compare_semver(latest.tag_name, current_tag)

    if comparison > 0:
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

def _archive_download_urls(url: str) -> list[str]:
    urls = [url]
    patterns = (
        r"/zipball/([^/?#]+)",
        r"/archive/refs/tags/([^/?#]+)\.zip",
        r"/zip/refs/tags/([^/?#]+)",
    )
    tag_name = None
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            tag_name = unquote(match.group(1))
            break
    if tag_name:
        urls.extend([
            _archive_url(tag_name),
            f"https://codeload.github.com/{REPOSITORY}/zip/refs/tags/{tag_name}",
        ])
    return list(dict.fromkeys(urls))


def download_zip(url: str, max_retries: int = 3) -> int:

    os.makedirs("storage/cache", exist_ok=True)
    target_path = "storage/cache/update.zip"
    temp_path = "storage/cache/update.tmp.zip"
    for download_url in _archive_download_urls(url):
        for attempt in range(max_retries):
            try:
                with requests.get(download_url, headers=HEADERS, stream=True, timeout=30) as response:
                    response.raise_for_status()
                    with open(temp_path, "wb") as file:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                file.write(chunk)
                with zipfile.ZipFile(temp_path, "r") as archive:
                    if not archive.namelist():
                        raise zipfile.BadZipFile("Архив обновления пуст")
                os.replace(temp_path, target_path)
                return 0
            except Exception as error:
                try:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                except OSError:
                    logger.debug("Не удалось удалить временный архив обновления", exc_info=True)
                logger.warning(
                    f"Попытка {attempt + 1} скачать обновление с {download_url} не удалась: {error}"
                )
                if attempt < max_retries - 1:
                    time.sleep(min(2 * (attempt + 1), 5))
                else:
                    logger.debug("TRACEBACK", exc_info=True)
    logger.error("Не удалось скачать обновление ни с одного GitHub endpoint.")
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
