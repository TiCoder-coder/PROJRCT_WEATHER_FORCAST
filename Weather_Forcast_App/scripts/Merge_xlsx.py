import os
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


MERGE_DIR_NAME = "Merge_data"
OUTPUT_DIR_NAME = "output"
MERGE_VRAIN_FILENAME = "merged_vrain_comprehensive_data.xlsx"
MERGE_VIETNAM_FILENAME = "merged_vietnam_weather_data.xlsx"
MERGE_OTHER_FILENAME = "merged_other_data.xlsx"
LOG_VRAIN_FILENAME = "merged_vrain_files_log.txt"
LOG_VIETNAM_FILENAME = "merged_vietnam_files_log.txt"
LOG_OTHER_FILENAME = "merged_other_files_log.txt"


def load_processed_files(log_path: Path) -> set[str]:
    if not log_path.exists():
        return set()

    processed = set()
    try:
        with log_path.open("r", encoding="utf-8") as f:
            for line in f:
                name = line.strip()
                if name:
                    processed.add(name)
    except Exception as e:
        print(f"Loi khi doc log file {log_path.name}: {e}")
    return processed


def save_processed_files(log_path: Path, processed_files: set[str]) -> None:
    try:
        with log_path.open("w", encoding="utf-8") as f:
            for name in sorted(processed_files):
                f.write(name + "\n")
    except Exception as e:
        print(f"Loi khi ghi log file {log_path.name}: {e}")


def read_excel_file(file_path: Path) -> pd.DataFrame:
    """Đọc file Excel với exception handling"""
    try:
        return pd.read_excel(file_path)
    except Exception as e:
        print(f"Loi khi doc file {file_path.name}: {e}")
        return pd.DataFrame()


def get_new_excel_files(output_dir: Path, processed_files: set[str]) -> tuple[list[Path], list[Path], list[Path]]:
    """
    Lấy danh sách các file .xlsx MỚI trong thư mục output
    và phân loại thành 3 nhóm: vietnam_weather_, vrain_comprehensive_, và các file còn lại.
    """
    if not output_dir.exists():
        print(f"Thu muc nguon khong ton tai: {output_dir}")
        return [], [], []

    all_excel_files = sorted(output_dir.glob("*.xlsx"))
    if not all_excel_files:
        print(f"Khong tim thay file .xlsx nao trong thu muc: {output_dir}")
        return [], [], []

    vietnam_files = []
    vrain_files = []
    other_files = []
    
    for file_path in all_excel_files:
        if file_path.name not in processed_files:
            if file_path.name.startswith("vietnam_weather_"):
                vietnam_files.append(file_path)
            elif file_path.name.startswith("vrain_comprehensive_"):
                vrain_files.append(file_path)
            else:
                other_files.append(file_path)

    print(f"Tong so file .xlsx trong output: {len(all_excel_files)}")
    print(f"So file vietnam_weather_ moi: {len(vietnam_files)}")
    print(f"So file vrain_comprehensive_ moi: {len(vrain_files)}")
    print(f"So file khac moi: {len(other_files)}")

    return vietnam_files, vrain_files, other_files


def merge_files_concurrently(file_list: list[Path], max_workers: int = 4) -> pd.DataFrame:
    """Đọc nhiều file Excel song song để tăng tốc độ và loại bỏ cột trùng"""
    dfs = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_file = {
            executor.submit(read_excel_file, file_path): file_path 
            for file_path in file_list
        }
        
        for future in as_completed(future_to_file):
            file_path = future_to_file[future]
            try:
                df = future.result()
                if not df.empty:
                    # Loại bỏ cột trùng lặp nếu có
                    df = df.loc[:, ~df.columns.duplicated()]
                    dfs.append(df)
                    print(f"✓ Da doc xong: {file_path.name} ({len(df.columns)} cot)")
            except Exception as e:
                print(f"✗ Loi khi xu ly file {file_path.name}: {e}")
    
    if dfs:
        merged = pd.concat(dfs, ignore_index=True)
        # Loại bỏ cột trùng sau khi concat
        merged = merged.loc[:, ~merged.columns.duplicated()]
        return merged
    return pd.DataFrame()


def merge_single_category(file_list: list[Path], merge_path: Path, 
                         log_path: Path, processed_files: set[str],
                         category_name: str = "du lieu") -> None:
    """
    Merge một loại file cụ thể (vietnam_weather_, vrain_comprehensive_, hoặc các file khác)
    """
    if not file_list:
        print(f"Khong co file {category_name} moi de merge.")
        return
    
    print(f"\n=== MERGE FILE {category_name.upper()} ===")
    print(f"So luong file: {len(file_list)}")
    
    new_data = merge_files_concurrently(file_list)
    
    if new_data.empty:
        print(f"Khong doc duoc du lieu hop le tu cac file {category_name} moi.")
        return
    
    # Loại bỏ cột trùng lặp trong dữ liệu mới
    new_data = new_data.loc[:, ~new_data.columns.duplicated()]
    print(f"Tong so dong du lieu moi: {len(new_data)}, So cot: {len(new_data.columns)}")
    
    if merge_path.exists():
        try:
            print(f"Dang doc file merge cu: {merge_path.name}")
            old_data = pd.read_excel(merge_path)
            # Loại bỏ cột trùng trong dữ liệu cũ
            old_data = old_data.loc[:, ~old_data.columns.duplicated()]
            
            before_rows = len(old_data)
            
            # Đảm bảo cả hai dataframe có cùng cột
            all_columns = list(set(old_data.columns) | set(new_data.columns))
            
            # Thêm cột thiếu vào old_data
            for col in all_columns:
                if col not in old_data.columns:
                    old_data[col] = None
            
            # Thêm cột thiếu vào new_data
            for col in all_columns:
                if col not in new_data.columns:
                    new_data[col] = None
            
            # Sắp xếp cột theo thứ tự giống nhau
            old_data = old_data[sorted(all_columns)]
            new_data = new_data[sorted(all_columns)]
            
            merged_df = pd.concat([old_data, new_data], ignore_index=True)
            # Loại bỏ cột trùng sau khi concat
            merged_df = merged_df.loc[:, ~merged_df.columns.duplicated()]
            
            print(f"Da append {len(new_data)} dong vao {before_rows} dong cu.")
            print(f"Tong so dong sau khi merge: {len(merged_df)}, So cot: {len(merged_df.columns)}")
        except Exception as e:
            print(f"Loi khi doc file merge cu, chi dung du lieu moi. Chi tiet: {e}")
            merged_df = new_data
    else:
        print(f"Chua co file merge cu. Tao file merge moi tu du lieu {category_name}.")
        merged_df = new_data
        print(f"Tong so dong trong file merge moi: {len(merged_df)}, So cot: {len(merged_df.columns)}")
    
    try:
        merged_df.to_excel(merge_path, index=False)
        print(f"Da ghi file merge thanh cong tai: {merge_path}")
        print(f"Danh sach cot: {', '.join(merged_df.columns.tolist()[:10])}...")
    except Exception as e:
        print(f"Loi khi ghi file Excel merge: {e}")
        return
    
    for f in file_list:
        processed_files.add(f.name)
    save_processed_files(log_path, processed_files)
    print(f"Da cap nhat log voi {len(file_list)} file {category_name} moi.")


def merge_excel_files_once(base_dir: Path) -> None:
    """
    Hàm chính:
    - Đọc log các file đã merge
    - Tìm các file .xlsx mới trong thư mục output
    - Phân loại thành 3 nhóm: vietnam_weather_, vrain_comprehensive_, và file khác
    - Append dữ liệu mới vào file merge cũ (nếu có)
    - Cập nhật lại log
    """
    
    output_dir = base_dir / OUTPUT_DIR_NAME
    merge_dir = base_dir / MERGE_DIR_NAME
    merge_dir.mkdir(parents=True, exist_ok=True)
    
    merge_vietnam_path = merge_dir / MERGE_VIETNAM_FILENAME
    log_vietnam_path = merge_dir / LOG_VIETNAM_FILENAME
    
    merge_vrain_path = merge_dir / MERGE_VRAIN_FILENAME
    log_vrain_path = merge_dir / LOG_VRAIN_FILENAME
    
    merge_other_path = merge_dir / MERGE_OTHER_FILENAME
    log_other_path = merge_dir / LOG_OTHER_FILENAME
    
    print("======== BAT DAU MERGE =========")
    print(f"Thu muc nguon (output):    {output_dir}")
    print(f"Thu muc merge (Merge_data): {merge_dir}")
    print("================================")
    
    processed_vietnam = load_processed_files(log_vietnam_path)
    processed_vrain = load_processed_files(log_vrain_path)
    processed_other = load_processed_files(log_other_path)
    
    if processed_vietnam:
        print(f"Da tung merge {len(processed_vietnam)} file vietnam_weather_ truoc do.")
    if processed_vrain:
        print(f"Da tung merge {len(processed_vrain)} file vrain_comprehensive_ truoc do.")
    if processed_other:
        print(f"Da tung merge {len(processed_other)} file khac truoc do.")
    
    all_processed = processed_vietnam.union(processed_vrain).union(processed_other)
    vietnam_files, vrain_files, other_files = get_new_excel_files(output_dir, all_processed)
    
    merge_single_category(vietnam_files, merge_vietnam_path, 
                         log_vietnam_path, processed_vietnam,
                         "vietnam_weather_")
    
    merge_single_category(vrain_files, merge_vrain_path,
                         log_vrain_path, processed_vrain,
                         "vrain_comprehensive_")
    
    merge_single_category(other_files, merge_other_path,
                         log_other_path, processed_other,
                         "khac")
    
    print("======== KET THUC MERGE =========")


if __name__ == "__main__":
    SCRIPT_DIR = Path(__file__).parent
    BASE_DIR = SCRIPT_DIR.parent
    
    print(f"Script dir: {SCRIPT_DIR}")
    print(f"Base dir: {BASE_DIR}")
    
    output_dir = BASE_DIR / OUTPUT_DIR_NAME
    if not output_dir.exists():
        print(f"ERROR: Khong tim thay thu muc output tai: {output_dir}")
        print(f"Vui long tao thu muc: {output_dir}")
        sys.exit(1)
    
    merge_excel_files_once(BASE_DIR)