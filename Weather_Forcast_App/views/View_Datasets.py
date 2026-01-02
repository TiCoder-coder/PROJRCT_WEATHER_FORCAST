import mimetypes
from pathlib import Path
from datetime import datetime

from django.conf import settings
from django.http import FileResponse, Http404
from django.shortcuts import render


def _base_dir() -> Path:
    """
    Trả về thư mục Weather_Forcast_App
    Nếu BASE_DIR là D:\PROJRCT_WEATHER_FORCAST thì trả về D:\PROJRCT_WEATHER_FORCAST\Weather_Forcast_App
    Nếu BASE_DIR đã là Weather_Forcast_App thì trả về chính nó
    """
    base = Path(settings.BASE_DIR)
    
    # Kiểm tra xem BASE_DIR đã là Weather_Forcast_App chưa
    if base.name == "Weather_Forcast_App":
        return base
    
    # Nếu chưa, thêm Weather_Forcast_App vào đường dẫn
    weather_app_dir = base / "Weather_Forcast_App"
    if weather_app_dir.exists():
        return weather_app_dir
    
    # Fallback: trả về BASE_DIR
    print(f"WARNING: Could not find Weather_Forcast_App directory. Using BASE_DIR: {base}")
    return base


def _output_dir() -> Path:
    """Trả về thư mục output"""
    return _base_dir() / "output"


def _merge_dir() -> Path:
    """Trả về thư mục Merge_data"""
    return _base_dir() / "Merge_data"


def _safe_join(base_dir: Path, filename: str) -> Path:
    """
    Kiểm tra và trả về đường dẫn file an toàn
    """
    base = base_dir.resolve()
    p = (base / filename).resolve()
    
    # Kiểm tra file có nằm trong thư mục base không
    if base not in p.parents and p != base:
        raise Http404("Invalid path")
    
    # Kiểm tra file có tồn tại không
    if not p.exists() or not p.is_file():
        raise Http404("File not found")
    
    return p


def _get_files_info(directory: Path) -> list:
    """
    Lấy thông tin các file trong thư mục
    """
    print(f"DEBUG: Checking directory: {directory}")
    print(f"DEBUG: Directory exists: {directory.exists()}")
    
    if not directory.exists():
        print(f"DEBUG: Directory does not exist, creating: {directory}")
        try:
            directory.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"ERROR: Could not create directory: {e}")
        return []
    
    patterns = ["*.xlsx", "*.csv", "*.json", "*.txt"]
    files = []
    for pat in patterns:
        found = list(directory.glob(pat))
        print(f"DEBUG: Pattern '{pat}' found {len(found)} files")
        files.extend(found)

    files = sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)
    print(f"DEBUG: Total files found: {len(files)}")

    items = []
    for p in files:
        st = p.stat()
        items.append({
            "name": p.name,
            "size_mb": round(st.st_size / (1024 * 1024), 2),
            "mtime": datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
        })

    return items


def datasets_view(request):
    """
    View hiển thị danh sách file từ cả thư mục output và Merge_data
    """
    # Debug info
    base = _base_dir()
    print(f"DEBUG: BASE_DIR from settings: {settings.BASE_DIR}")
    print(f"DEBUG: Calculated base_dir: {base}")
    
    # Tạo thư mục nếu chưa tồn tại
    output_dir = _output_dir()
    merge_dir = _merge_dir()
    
    print(f"DEBUG: Output dir: {output_dir}")
    print(f"DEBUG: Merge dir: {merge_dir}")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    merge_dir.mkdir(parents=True, exist_ok=True)

    # Lấy danh sách file từ output
    print(f"\n=== Scanning OUTPUT directory ===")
    output_items = _get_files_info(output_dir)
    latest_output = output_items[0] if output_items else None

    # Lấy danh sách file từ Merge_data
    print(f"\n=== Scanning MERGE_DATA directory ===")
    merged_items = _get_files_info(merge_dir)
    latest_merged = merged_items[0] if merged_items else None

    print(f"\nDEBUG: Returning {len(output_items)} output files and {len(merged_items)} merged files")

    return render(request, "weather/Datasets.html", {
        "output_items": output_items,
        "latest_output": latest_output,
        "merged_items": merged_items,
        "latest_merged": latest_merged,
    })


def dataset_download_view(request, folder: str, filename: str):
    """
    View tải xuống file từ thư mục output hoặc Merge_data
    folder: 'output' hoặc 'merged'
    """
    if folder == "output":
        base_dir = _output_dir()
    elif folder == "merged":
        base_dir = _merge_dir()
    else:
        raise Http404("Invalid folder")
    
    p = _safe_join(base_dir, filename)
    content_type, _ = mimetypes.guess_type(str(p))
    resp = FileResponse(open(p, "rb"), content_type=content_type or "application/octet-stream")
    resp["Content-Disposition"] = f'attachment; filename="{p.name}"'
    return resp


def dataset_view_view(request, folder: str, filename: str):
    """
    View xem trước file từ thư mục output hoặc Merge_data
    folder: 'output' hoặc 'merged'
    """
    if folder == "output":
        base_dir = _output_dir()
    elif folder == "merged":
        base_dir = _merge_dir()
    else:
        raise Http404("Invalid folder")
    
    p = _safe_join(base_dir, filename)
    content_type, _ = mimetypes.guess_type(str(p))
    resp = FileResponse(open(p, "rb"), content_type=content_type or "application/octet-stream")
    resp["Content-Disposition"] = f'inline; filename="{p.name}"'
    return resp
