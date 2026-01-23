import json
import threading
import uuid
from pathlib import Path
from datetime import datetime

import pandas as pd
import numpy as np

from django.http import JsonResponse, HttpResponseNotAllowed, Http404
from django.views.decorators.http import require_http_methods


APP_ROOT = Path(__file__).resolve().parents[1]
MERGE_DIR = APP_ROOT / "Merge_data"
OUTPUT_DIR = APP_ROOT / "output"

CLEANED_ROOT = APP_ROOT / "cleaned_data"
CLEANED_MERGE_DIR = CLEANED_ROOT / "Clean_Data_For_File_Merge"
CLEANED_RAW_DIR = CLEANED_ROOT / "Clean_Data_For_File_Not_Merge"

ALLOWED_EXTS = {".csv", ".xlsx", ".xls"}
LOG_LIMIT = 4000


_JOBS = {}
_JOBS_LOCK = threading.Lock()


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _push(job_id: str, line: str):
    line = (line or "").rstrip("\n")
    if not line:
        return
    with _JOBS_LOCK:
        job = _JOBS.get(job_id)
        if not job:
            return
        job["logs"].append(line)
        if len(job["logs"]) > LOG_LIMIT:
            job["logs"] = job["logs"][-LOG_LIMIT:]


def _set_progress(job_id: str, pct: int, step: str):
    pct = max(0, min(100, int(pct)))
    with _JOBS_LOCK:
        job = _JOBS.get(job_id)
        if not job:
            return
        job["progress"] = {"pct": pct, "step": step}


def _safe_pick_file(base_dir: Path, filename: str) -> Path:
    base_dir = base_dir.resolve()
    p = (base_dir / filename).resolve()

    if base_dir not in p.parents:
        raise Http404("Invalid path")

    if not p.exists() or not p.is_file():
        raise Http404("File not found")

    if p.suffix.lower() not in ALLOWED_EXTS:
        raise Http404("Unsupported file type")

    return p


def _scan_files(directory: Path):
    directory.mkdir(parents=True, exist_ok=True)
    patterns = ["*.xlsx", "*.xls", "*.csv"]
    files = []
    for pat in patterns:
        files.extend(list(directory.glob(pat)))
    files = sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)

    items = []
    for p in files:
        st = p.stat()
        items.append({
            "name": p.name,
            "size_mb": round(st.st_size / (1024 * 1024), 2),
            "mtime": datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            "ext": p.suffix.lower(),
        })
    return items


def _load_df(file_path: Path, job_id: str) -> pd.DataFrame:
    _push(job_id, f"[INFO] Đang đọc file: {file_path.name}")
    if file_path.suffix.lower() in [".xlsx", ".xls"]:
        return pd.read_excel(file_path)
    # csv
    return pd.read_csv(file_path, encoding="utf-8-sig", low_memory=False)


def _clean_dataframe(df: pd.DataFrame, job_id: str):
    """
    Clean “an toàn” cho nhiều nguồn:
    - trim string
    - convert numeric nếu có thể
    - parse datetime nếu tên cột gợi ý
    - fill missing: numeric->median, text->mode/"unknown"
    - drop duplicates
    """
    report = {}

    _push(job_id, f"[INFO] Shape ban đầu: rows={len(df)} cols={df.shape[1]}")
    report["rows_before"] = int(len(df))
    report["cols"] = int(df.shape[1])

    _set_progress(job_id, 15, "Profiling missing/duplicates")
    missing_before = int(df.isna().sum().sum())
    dup_before = int(df.duplicated().sum())
    report["missing_before"] = missing_before
    report["duplicates_before"] = dup_before
    _push(job_id, f"[INFO] Missing trước: {missing_before}")
    _push(job_id, f"[INFO] Duplicate trước: {dup_before}")

    _set_progress(job_id, 30, "Chuẩn hoá string & numeric")
    obj_cols = df.select_dtypes(include=["object"]).columns
    for c in obj_cols:
        df[c] = df[c].astype(str).str.strip().replace({"nan": np.nan, "None": np.nan, "": np.nan})

    for c in obj_cols:
        s = pd.to_numeric(df[c].str.replace(",", ".", regex=False), errors="coerce")
        if s.notna().sum() >= max(5, int(0.6 * len(df[c].dropna()))):
            df[c] = s

    _set_progress(job_id, 45, "Parse datetime (nếu có)")
    candidates = []
    for c in df.columns:
        name = str(c).lower()
        if any(k in name for k in ["time", "date", "timestamp", "ngày", "giờ", "cap nhat", "cập nhật"]):
            candidates.append(c)

    for c in candidates:
        try:
            parsed = pd.to_datetime(df[c], errors="coerce", dayfirst=True, utc=False)
            if parsed.notna().sum() >= max(5, int(0.3 * len(df))):
                df[c] = parsed
                _push(job_id, f"[INFO] Parsed datetime column: {c}")
        except Exception:
            pass

    _set_progress(job_id, 60, "Impute missing")
    num_cols = df.select_dtypes(include=[np.number]).columns
    obj_cols = df.select_dtypes(include=["object"]).columns

    for c in num_cols:
        med = df[c].median(skipna=True)
        if pd.isna(med):
            med = 0
        df[c] = df[c].fillna(med)

    for c in obj_cols:
        mode = None
        try:
            mode = df[c].mode(dropna=True)
            mode = mode.iloc[0] if not mode.empty else None
        except Exception:
            mode = None
        df[c] = df[c].fillna(mode if mode is not None else "unknown")

    _set_progress(job_id, 75, "Drop duplicates")
    before = len(df)
    df = df.drop_duplicates()
    removed = before - len(df)
    report["duplicates_removed"] = int(removed)
    _push(job_id, f"[INFO] Removed duplicates: {removed}")

    _set_progress(job_id, 90, "Final check")
    missing_after = int(df.isna().sum().sum())
    report["missing_after"] = missing_after
    report["rows_after"] = int(len(df))
    _push(job_id, f"[INFO] Missing sau: {missing_after}")
    _push(job_id, f"[INFO] Shape sau: rows={len(df)} cols={df.shape[1]}")

    _set_progress(job_id, 95, "Done cleaning")
    return df, report


def _worker(job_id: str, source: str, filename: str | None):
    try:
        _push(job_id, "========== START CLEAN ==========")
        _push(job_id, f"[INFO] source={source}")
        _set_progress(job_id, 5, "Chuẩn bị thư mục")

        MERGE_DIR.mkdir(parents=True, exist_ok=True)
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        CLEANED_MERGE_DIR.mkdir(parents=True, exist_ok=True)
        CLEANED_RAW_DIR.mkdir(parents=True, exist_ok=True)

        if source == "merge":
            in_dir = MERGE_DIR
            out_dir = CLEANED_MERGE_DIR
            out_folder_key = "cleaned_merge"
        elif source == "output":
            in_dir = OUTPUT_DIR
            out_dir = CLEANED_RAW_DIR
            out_folder_key = "cleaned_raw"
        else:
            raise ValueError("Invalid source")

        if not filename:
            items = _scan_files(in_dir)
            if not items:
                raise FileNotFoundError("Không có file nào trong thư mục nguồn.")
            filename = items[0]["name"]

        file_path = _safe_pick_file(in_dir, filename)

        _set_progress(job_id, 10, "Đọc dữ liệu")
        df = _load_df(file_path, job_id)

        _set_progress(job_id, 20, "Clean dữ liệu")
        df2, report = _clean_dataframe(df, job_id)

        _set_progress(job_id, 96, "Ghi file output")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        stem = file_path.stem
        out_name = f"cleaned_{source}_{stem}_{ts}.csv"
        out_path = out_dir / out_name
        df2.to_csv(out_path, index=False, encoding="utf-8-sig")

        size_mb = round(out_path.stat().st_size / (1024 * 1024), 2)
        _push(job_id, f"[INFO] Saved: {out_name} ({size_mb} MB)")
        _push(job_id, "========== DONE ==========")

        with _JOBS_LOCK:
            job = _JOBS.get(job_id)
            if job:
                job["done"] = True
                job["error"] = None
                job["finished_at"] = _now()
                job["result"] = {
                    "source": source,
                    "input_file": file_path.name,
                    "output_file": out_name,
                    "output_folder_key": out_folder_key,
                    "size_mb": size_mb,
                    "report": report,
                    "view_url": f"/datasets/view/{out_folder_key}/{out_name}/",
                    "download_url": f"/datasets/download/{out_folder_key}/{out_name}/",
                }
                job["progress"] = {"pct": 100, "step": "Hoàn thành"}

    except Exception as e:
        _push(job_id, f"[ERROR] {type(e).__name__}: {e}")
        with _JOBS_LOCK:
            job = _JOBS.get(job_id)
            if job:
                job["done"] = True
                job["error"] = f"{type(e).__name__}: {e}"
                job["finished_at"] = _now()
                job["progress"] = {"pct": 100, "step": "Lỗi"}


@require_http_methods(["GET"])
def clean_files_list_view(request):
    source = (request.GET.get("source") or "").strip().lower()
    if source == "merge":
        items = _scan_files(MERGE_DIR)
    elif source == "output":
        items = _scan_files(OUTPUT_DIR)
    else:
        return JsonResponse({"ok": False, "message": "source phải là merge/output"}, status=400)

    return JsonResponse({"ok": True, "source": source, "files": items})


@require_http_methods(["POST"])
def clean_data_start_view(request):
    source = None
    filename = None

    ct = (request.headers.get("content-type") or "").lower()
    if "application/json" in ct:
        try:
            payload = json.loads(request.body.decode("utf-8"))
        except Exception:
            payload = {}
        source = (payload.get("source") or "").strip().lower()
        filename = (payload.get("filename") or "").strip() or None
    else:
        source = (request.POST.get("source") or "").strip().lower()
        filename = (request.POST.get("filename") or "").strip() or None

    if source not in ("merge", "output"):
        return JsonResponse({"ok": False, "message": "source phải là merge hoặc output"}, status=400)

    job_id = uuid.uuid4().hex
    with _JOBS_LOCK:
        _JOBS[job_id] = {
            "job_id": job_id,
            "started_at": _now(),
            "finished_at": None,
            "done": False,
            "error": None,
            "logs": [],
            "progress": {"pct": 0, "step": "Khởi tạo"},
            "result": None,
        }

    t = threading.Thread(target=_worker, args=(job_id, source, filename), daemon=True)
    t.start()
    return JsonResponse({"ok": True, "job_id": job_id})


@require_http_methods(["GET"])
def clean_data_tail_view(request):
    job_id = (request.GET.get("job_id") or "").strip()
    since = request.GET.get("since", "0")
    try:
        since_i = max(0, int(since))
    except Exception:
        since_i = 0

    with _JOBS_LOCK:
        job = _JOBS.get(job_id)

    if not job:
        return JsonResponse({"ok": False, "message": "job_id không tồn tại"}, status=404)

    logs = job["logs"]
    new_lines = logs[since_i:]
    next_since = since_i + len(new_lines)

    return JsonResponse({
        "ok": True,
        "job_id": job_id,
        "done": job["done"],
        "error": job["error"],
        "progress": job["progress"],
        "started_at": job["started_at"],
        "finished_at": job["finished_at"],
        "lines": new_lines,
        "next_since": next_since,
        "result": job["result"],
    })


clean_data_view = clean_data_start_view
