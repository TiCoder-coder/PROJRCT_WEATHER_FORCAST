import mimetypes
from pathlib import Path
from datetime import datetime
import pandas as pd
import json
from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import render
from django.utils.html import escape


def _base_dir() -> Path:
    """
    Trả về thư mục Weather_Forcast_App
    """
    base = Path(settings.BASE_DIR)
    
    if base.name == "Weather_Forcast_App":
        return base
    
    weather_app_dir = base / "Weather_Forcast_App"
    if weather_app_dir.exists():
        return weather_app_dir
    
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
    
    if base not in p.parents and p != base:
        raise Http404("Invalid path")
    
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
    base = _base_dir()
    print(f"DEBUG: BASE_DIR from settings: {settings.BASE_DIR}")
    print(f"DEBUG: Calculated base_dir: {base}")
    
    output_dir = _output_dir()
    merge_dir = _merge_dir()
    
    print(f"DEBUG: Output dir: {output_dir}")
    print(f"DEBUG: Merge dir: {merge_dir}")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    merge_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n=== Scanning OUTPUT directory ===")
    output_items = _get_files_info(output_dir)
    latest_output = output_items[0] if output_items else None

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


def _get_file_type(filename: str) -> str:
    """Xác định loại file từ extension"""
    ext = Path(filename).suffix.lower()
    if ext in ['.csv']:
        return 'csv'
    elif ext in ['.xlsx', '.xls']:
        return 'excel'
    elif ext == '.json':
        return 'json'
    else:  # .txt và các loại khác
        return 'txt'


def dataset_view_view(request, folder: str, filename: str):
    """
    View xem trước file từ thư mục output hoặc Merge_data
    Sử dụng template duy nhất: dataset_preview.html
    """
    if folder == "output":
        base_dir = _output_dir()
    elif folder == "merged":
        base_dir = _merge_dir()
    else:
        raise Http404("Invalid folder")
    
    p = _safe_join(base_dir, filename)
    
    # Xác định loại file
    file_type = _get_file_type(filename)
    
    # Kiểm tra nếu là request AJAX để lấy thêm dữ liệu (chỉ cho CSV/Excel)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    # Xử lý CSV/Excel files
    if file_type in ['csv', 'excel']:
        try:
            page = int(request.GET.get('page', 1))
            rows_per_page = 100
            start_row = (page - 1) * rows_per_page
            end_row = start_row + rows_per_page
            
            # Đọc file với chunk để tối ưu
            if file_type == 'csv':
                if is_ajax:
                    # Đọc phần cần thiết cho AJAX request
                    df = pd.read_csv(p, encoding='utf-8', skiprows=range(1, start_row), nrows=rows_per_page)
                    total_rows = 0
                    with open(p, 'r', encoding='utf-8') as f:
                        total_rows = sum(1 for line in f) - 1  # Trừ header
                else:
                    # Đọc 100 dòng đầu cho trang đầu
                    df = pd.read_csv(p, encoding='utf-8', nrows=rows_per_page)
                    total_rows = 0
                    with open(p, 'r', encoding='utf-8') as f:
                        total_rows = sum(1 for line in f) - 1
            else:  # Excel
                if is_ajax:
                    # Đọc toàn bộ để lấy tổng số dòng, nhưng chỉ lấy phần cần thiết
                    df_full = pd.read_excel(p, engine='openpyxl')
                    total_rows = len(df_full)
                    df = df_full.iloc[start_row:end_row]
                else:
                    # Chỉ đọc 100 dòng đầu
                    df = pd.read_excel(p, engine='openpyxl', nrows=rows_per_page)
                    df_full = pd.read_excel(p, engine='openpyxl')
                    total_rows = len(df_full)
            
            # Nếu là AJAX request, trả về JSON
            if is_ajax:
                data = {
                    'data': df.fillna('').to_dict('records'),
                    'page': page,
                    'total_rows': total_rows,
                    'has_more': end_row < total_rows
                }
                return HttpResponse(json.dumps(data, default=str), content_type='application/json')
            
            # Chuyển DataFrame thành HTML table
            html_table = df.fillna('').to_html(
                classes='table table-striped table-bordered',
                index=False,
                float_format=lambda x: '{:.2f}'.format(x) if isinstance(x, float) else str(x)
            )
            
            # Chuẩn bị context cho template
            context = {
                'filename': filename,
                'folder': folder,
                'file_type': file_type,
                'file_size_kb': p.stat().st_size / 1024,
                'total_rows': total_rows,
                'rows_per_page': rows_per_page,
                'showing_rows': min(rows_per_page, total_rows),
                'html_table': html_table,
                'referer_url': request.META.get('HTTP_REFERER', '/'),
                'download_url': request.path.replace('/view/', '/download/'),
                'is_table': True,
            }
            
            return render(request, 'weather/dataset_preview.html', context)
            
        except Exception as e:
            # Render template lỗi
            error_context = {
                'error_title': 'Lỗi khi đọc file',
                'error_message': f'Không thể đọc file {escape(filename)}',
                'error_detail': str(e),
                'back_url': request.META.get('HTTP_REFERER', '/'),
            }
            return render(request, 'weather/error.html', error_context, status=500)
    
    # Xử lý TXT/JSON files
    else:
        try:
            # Đọc nội dung file
            with open(p, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Chuẩn bị context cho template
            context = {
                'filename': filename,
                'folder': folder,
                'file_type': file_type,
                'file_size_kb': p.stat().st_size / 1024,
                'content': content,
                'referer_url': request.META.get('HTTP_REFERER', '/'),
                'download_url': request.path.replace('/view/', '/download/'),
                'is_table': False,
            }
            
            return render(request, 'weather/dataset_preview.html', context)
            
        except UnicodeDecodeError:
            # Nếu không đọc được dưới dạng UTF-8 text, thử đọc binary
            try:
                with open(p, 'rb') as f:
                    content = f.read().decode('utf-8', errors='ignore')
                
                context = {
                    'filename': filename,
                    'folder': folder,
                    'file_type': file_type,
                    'file_size_kb': p.stat().st_size / 1024,
                    'content': content,
                    'referer_url': request.META.get('HTTP_REFERER', '/'),
                    'download_url': request.path.replace('/view/', '/download/'),
                    'is_table': False,
                }
                
                return render(request, 'weather/dataset_preview.html', context)
                
            except Exception as e:
                # Nếu không đọc được dưới dạng text, trả về file để download
                content_type, _ = mimetypes.guess_type(str(p))
                resp = FileResponse(open(p, "rb"), content_type=content_type or "application/octet-stream")
                resp["Content-Disposition"] = f'inline; filename="{p.name}"'
                return resp
                
        except Exception as e:
            # Render template lỗi
            error_context = {
                'error_title': 'Lỗi khi đọc file',
                'error_message': f'Không thể đọc file {escape(filename)}',
                'error_detail': str(e),
                'back_url': request.META.get('HTTP_REFERER', '/'),
            }
            return render(request, 'weather/error.html', error_context, status=500)