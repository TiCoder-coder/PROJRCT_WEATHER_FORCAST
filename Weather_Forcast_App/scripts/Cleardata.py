import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
import base64
import io 
import os
import json

from django.http import JsonResponse
from django.conf import settings
from datetime import datetime
from sklearn.impute import SimpleImputer


def clean_data_view(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body)
        filename = data.get('filename')
        file_type = (data.get("file_type") or "merged").lower()
        action = data.get('action', 'analyze')        # analyze | clean

        if file_type == 'merged':
            file_path = os.path.join(
                settings.BASE_DIR,
                'Weather_Forcast_App', 'Merge_data', filename
            )
        else:
            file_path = os.path.join(
                settings.BASE_DIR,
                'Weather_Forcast_App', 'output', filename
            )

        if not os.path.exists(file_path):
            return JsonResponse({'success': False, 'message': 'File không tồn tại'})

        ext = os.path.splitext(file_path)[1].lower()
        if ext in [".xlsx", ".xls"]:
            data_df = pd.read_excel(file_path, engine="openpyxl")
        elif ext == ".csv":
            try:
                data_df = pd.read_csv(file_path, encoding="utf-8")
            except UnicodeDecodeError:
                data_df = pd.read_csv(file_path, encoding="utf-8-sig")
        else:
            return JsonResponse({'success': False, 'message': 'Chỉ hỗ trợ CSV/XLSX'}, status=400)


        if action == 'analyze':
            return JsonResponse({
                'success': True,
                'analysis': analyze_missing_data(data_df, filename)
            })

        if action == 'clean':
            return JsonResponse({
                'success': True,
                **perform_cleaning(data_df, filename, file_type)
            })

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})
def analyze_missing_data(data_df, filename):
    total_rows = len(data_df)
    total_columns = len(data_df.columns)

    data_df.replace(["N/A", "NA", "null", ""], np.nan, inplace=True)

    missing_report = []
    for col in data_df.columns:
        missing = data_df[col].isna().sum()
        missing_report.append({
            "column": col,
            "missing_count": int(missing),
            "percent": round(missing / total_rows * 100, 2),
            "dtype": str(data_df[col].dtype)
        })

    plt.figure(figsize=(12, 8))
    sns.heatmap(data_df.isna(), cmap="Blues", yticklabels=False)
    plt.title(f"Missing Data Heatmap - {filename}")
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    plt.close()
    heatmap = base64.b64encode(buf.getvalue()).decode()

    return {
        "filename": filename,
        "total_rows": total_rows,
        "total_columns": total_columns,
        "missing_report": missing_report,
        "heatmap_image": heatmap
    }
def perform_cleaning(data_df, filename, file_type="merged"):
    original_df = data_df.copy()
    cleaning_log = {}
    file_type = (file_type or "merged").lower()

    if file_type not in ("merged", "output"):
        file_type = "merged"


    # =========================
    # Chuẩn hóa missing
    # =========================
    data_df.columns = [str(c).strip() for c in data_df.columns]
    data_df.replace(["N/A", "NA", "null", "NULL", ""], np.nan, inplace=True)

    # =========================
    # Loại dòng rác / header lặp (cực quan trọng)
    # =========================
    first_col = data_df.columns[0]
    data_df = data_df[~data_df[first_col].astype(str).str.contains("DANH SÁCH", case=False, na=False)]

    if "Tên Trạm" in data_df.columns:
        data_df = data_df[data_df["Tên Trạm"].astype(str).str.strip().ne("Tên Trạm")]
    if "Tỉnh/Thành phố" in data_df.columns:
        data_df = data_df[~data_df["Tỉnh/Thành phố"].astype(str).str.contains("Tỉnh/TP", na=False)]
    if "STT" in data_df.columns:
        data_df = data_df[data_df["STT"].astype(str).str.strip().ne("STT")]

    if "Unnamed: 2" in data_df.columns:
        data_df = data_df[data_df["Unnamed: 2"].astype(str).str.strip().ne("Tên Trạm")]

    data_df = data_df.reset_index(drop=True)

    # =========================
    # Xử lý dữ liệu âm
    # =========================
    negative_fixed = {}
    for col in data_df.select_dtypes(include=[np.number]).columns:
        count = (data_df[col] < 0).sum()
        if count > 0:
            data_df.loc[data_df[col] < 0, col] = 0
            negative_fixed[col] = int(count)
    cleaning_log["negative_fixed"] = negative_fixed

    # =========================
    # Chuẩn hóa kiểu dữ liệu
    # =========================
    dtype_log = {}
    for col in data_df.columns:
        if data_df[col].dtype == object:
            converted = pd.to_numeric(data_df[col], errors="coerce")
            ratio = converted.notna().mean()
            if ratio >= 0.85:
                data_df[col] = converted
                dtype_log[col] = f"string → numeric (parsed {ratio:.0%})"


        col_l = col.lower()
        if ("date" in col_l) or ("time" in col_l) or ("thời gian" in col_l) or ("ngày" in col_l):
            data_df[col] = pd.to_datetime(data_df[col], errors="coerce")
            dtype_log[col] = "→ datetime"

    cleaning_log["datatype_standardized"] = dtype_log


    key_cols = [c for c in ["station_id", "data_time"] if c in data_df.columns]
    if key_cols:
        before = len(data_df)
        data_df = data_df.dropna(subset=key_cols)   # drop dòng thiếu key
        cleaning_log["dropna_key_rows"] = before - len(data_df)

    if set(["station_id", "data_time"]).issubset(data_df.columns):
        if "timestamp" in data_df.columns:
            data_df["timestamp"] = pd.to_datetime(data_df["timestamp"], errors="coerce")
            data_df = data_df.sort_values(["station_id", "data_time", "timestamp"])
        before = len(data_df)
        data_df = data_df.drop_duplicates(subset=["station_id", "data_time"], keep="last")
        cleaning_log["dedup_station_time_removed"] = before - len(data_df)


    # =========================
    # Imputation
    # =========================
    num_cols = data_df.select_dtypes(include=[np.number]).columns.tolist()
    dt_cols = data_df.select_dtypes(include=["datetime64[ns]"]).columns.tolist()
    cat_cols = [c for c in data_df.columns if c not in num_cols and c not in dt_cols]

    for c in num_cols:
        m = data_df[c].mean()
        data_df[c] = data_df[c].fillna(m if pd.notna(m) else 0)

    for c in dt_cols:
        mode = data_df[c].mode()
        data_df[c] = data_df[c].fillna(mode.iloc[0] if not mode.empty else pd.NaT)

    for c in cat_cols:
        mode = data_df[c].mode()
        data_df[c] = data_df[c].fillna(mode.iloc[0] if not mode.empty else "")

    # =========================
    # Kiểm tra toàn vẹn dữ liệu
    # =========================
    integrity_report = []
    if "category_id" in data_df.columns:
        valid_ids = {1, 2, 3, 4}
        invalid = ~data_df["category_id"].isin(valid_ids)
        if invalid.sum() > 0:
            integrity_report.append({
                "column": "category_id",
                "invalid_count": int(invalid.sum())
            })

    # =========================
    # So sánh trước – sau
    # =========================
    original_missing_like = original_df.replace(["N/A","NA","null","NULL",""], np.nan)
    comparison = {
        "rows_before": len(original_df),
        "rows_after": len(data_df),
        "columns_before": original_df.shape[1],
        "columns_after": data_df.shape[1],
        "missing_before": int(original_missing_like.isna().sum().sum()),
        "missing_after": int(data_df.isna().sum().sum()),
    }


    # =========================
    # Xuất file CSV
    # =========================
    today = datetime.now().strftime("%Y%m%d_%H%M%S")
    clean_filename = f"{os.path.splitext(filename)[0]}_cleaned_{today}.csv"

    base = os.path.join(settings.BASE_DIR, "Weather_Forcast_App", "cleaned_data")
    if file_type == "merged":
        output_dir = os.path.join(base, "Clean_Data_For_File_Merge")
    else:
        output_dir = os.path.join(base, "Clean_Data_For_File_Not_Merge")
    os.makedirs(output_dir, exist_ok=True)


    output_path = os.path.join(output_dir, clean_filename)
    data_df.to_csv(output_path, index=False, encoding="utf-8-sig")

    # =========================
    # Xuất báo cáo JSON
    # =========================
    report_path = output_path.replace(".csv", "_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({
            "comparison": comparison,
            "cleaning_log": cleaning_log,
            "integrity_report": integrity_report
        }, f, ensure_ascii=False, indent=4)

    return {
        "message": "Làm sạch dữ liệu hoàn tất",
        "output_file": clean_filename,
        "report_file": os.path.basename(report_path)
    }