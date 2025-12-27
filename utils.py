"""
Главные функции приложения
"""

import json
import subprocess
from pathlib import Path
from typing import Optional, Dict, Tuple
from urllib.parse import urlparse

import requests



def _run_bytes(cmd: list[str], cwd: Optional[Path] = None) -> bytes:
    proc = subprocess.run(cmd, cwd=str(cwd) if cwd else None,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    return proc.stdout


def _repo_parts(repo_url: str) -> Optional[Tuple[str, str]]:
    if not repo_url.startswith("https://github.com/"):
        return None
    parsed = urlparse(repo_url)
    parts = parsed.path.strip("/").replace(".git", "").split("/")
    if len(parts) < 2:
        return None
    return parts[0], parts[1]


def _get_remote_commit(repo_url: str) -> Optional[str]:
    parts = _repo_parts(repo_url)
    if parts is None:
        return None
    owner, name = parts
    resp = requests.get(
        f"https://api.github.com/repos/{owner}/{name}/commits",
        headers={"Accept": "application/vnd.github.v3+json"},
        params={"per_page": 1},
        timeout=10,
    )
    if resp.status_code != 200:
        return None
    data = resp.json()
    if not isinstance(data, list) or not data:
        return None
    return data[0].get("sha")


def _clone_or_fetch(repo_url: str, local_path: Path) -> None:
    if not local_path.exists():
        _run_bytes(["git", "clone", "--depth", "1", repo_url, str(local_path)])
    else:
        _run_bytes(["git", "fetch", "origin"], cwd=local_path)


def _local_commit(local_path: Path) -> str:
    return _run_bytes(["git", "rev-parse", "HEAD"], cwd=local_path).decode().strip()


def _repo_size_bytes(path: Path) -> int:
    total = 0
    for root, dirs, files in __import__("os").walk(path):
        if ".git" in dirs:
            dirs.remove(".git")
        for f in files:
            p = Path(root) / f
            if p.is_file():
                total += p.stat().st_size
    return total


def _file_counts(path: Path, code_exts: set[str]) -> Tuple[int, int]:
    total = 0
    code_files = 0
    for root, dirs, files in __import__("os").walk(path):
        if ".git" in dirs:
            dirs.remove(".git")
        for f in files:
            total += 1
            if Path(f).suffix.lower() in code_exts:
                code_files += 1
    return total, code_files


def _lines_of_code(path: Path, code_exts: set[str]) -> int:
    count = 0
    for root, dirs, files in __import__("os").walk(path):
        if ".git" in dirs:
            dirs.remove(".git")
        for f in files:
            if Path(f).suffix.lower() in code_exts:
                p = Path(root) / f
                with p.open("r", encoding="utf-8", errors="ignore") as fh:
                    for _ in fh:
                        count += 1
    return count

def _cache_path_for(repo_url: str, cache_dir: Path) -> Path:
    safe = repo_url.replace("/", "_").replace(":", "_")
    return cache_dir / f"{safe}.json"


def _load_cached_stats(repo_url: str, cache_dir: Path) -> Optional[dict]:
    p = _cache_path_for(repo_url, cache_dir)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def _save_cached_stats(repo_url: str, cache_dir: Path, stats: dict) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    p = _cache_path_for(repo_url, cache_dir)
    p.write_text(json.dumps(stats, ensure_ascii=False), encoding="utf-8")

DEFAULT_CODE_EXTS = {
    ".py", ".js", ".ts", ".go", ".rs", ".java", ".c", ".cpp", ".h", ".hpp", ".md", ".html", ".css", ".rb", ".php"
}


def get_stats(repo_url: str, config, code_exts: Optional[set[str]] = None) -> Optional[dict]:
    code_exts = code_exts or DEFAULT_CODE_EXTS
    parts = _repo_parts(repo_url)
    if parts is None:
        return None

    repo_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")
    local_path = Path(config.REPO_FOLDER) / repo_name

    remote_sha = _get_remote_commit(repo_url)
    if remote_sha is None:
        return None

    cached = _load_cached_stats(repo_url, Path(config.REPO_CACHES))
    if cached and cached.get("commit") == remote_sha:
        return cached

    # ensure repo present and up-to-date
    _clone_or_fetch(repo_url, local_path)
    local_sha = _local_commit(local_path)

    total_files, code_files = _file_counts(local_path, code_exts)
    total_lines = _lines_of_code(local_path, code_exts)
    size_bytes = _repo_size_bytes(local_path)

    stats = {
        "Коммит": remote_sha,
        "Репозиторий": repo_url,
        "Всего файлов": total_files,
        "Файлов с кодом": code_files,
        "Байт": size_bytes,
        "Строк кода": total_lines,
    }

    _save_cached_stats(repo_url, Path(config.REPO_CACHES), stats)
    return stats


def render_image(stats):
    from PIL import Image, ImageDraw, ImageFont
    import io
    
    try:
        font = ImageFont.truetype("assets/font.ttf", 20)
    except:
        font = ImageFont.load_default()

    draw_temp = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    line_height = 40

    height = 80

    for key, value in stats.items():
        text = f"{key}: {value}"
        text_width = draw_temp.textbbox((0, 0), text, font=font)[2]
        if text_width > 440:
            height += line_height * 2
        else:
            height += line_height
    
    width = 500
    img = Image.new('RGB', (width, height), color='black')
    draw = ImageDraw.Draw(img)
    draw.text((width // 2, 30), "СТАТИСТИКА", fill='red', font=font, anchor="mm")
    y_offset = 70
    for key, value in stats.items():
        text = f"{key}: {value}"
        text_width = draw.textbbox((0, 0), text, font=font)[2]
        
        if text_width > 440:
            key_text = f"{key}:"
            draw.text((30, y_offset), key_text, fill='yellow', font=font)
            draw.text((30, y_offset + 25), str(value), fill='white', font=font)
            
            y_offset += line_height * 2
        else:
            colon_pos = len(f"{key}:")
            full_text = f"{key}: {value}"
            draw.text((30, y_offset), full_text[:colon_pos], fill='yellow', font=font)
            key_bbox = draw.textbbox((30, y_offset), full_text[:colon_pos], font=font)
            key_width = key_bbox[2] - key_bbox[0]
            draw.text((30 + key_width, y_offset), full_text[colon_pos:], fill='white', font=font)
            
            y_offset += line_height

    img_buffer = io.BytesIO()
    img.save(img_buffer, format='PNG')
    img_buffer.seek(0)
    
    return img_buffer