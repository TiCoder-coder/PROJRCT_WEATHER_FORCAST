import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.impute import SimpleImputer

# =========================
# 1. LOAD DATA
# =========================
input_path = r"/media/voanhnhat/SDD_OUTSIDE5/PROJECT_WEATHER_FORECAST/Weather_Forcast_App/Merge_data/merged_vietnam_weather_data.xlsx"

data_df = pd.read_excel(input_path)

print("===== PREVIEW DATA =====")
print(data_df.head())
print("\n===== INFO =====")
print(data_df.info())

# =========================
# 2. PHÂN TÍCH THIẾU DỮ LIỆU
# =========================
print("\n===== MISSING DATA REPORT =====")
for col in data_df.columns:
    missing_data = data_df[col].isna().sum()
    missing_percent = missing_data / len(data_df) * 100
    print(f"Column: {col} -> {missing_percent:.2f}% missing")

# =========================
# 3. VISUALIZE MISSING DATA
# =========================
plt.figure(figsize=(10, 8))
sns.heatmap(
    data_df.isna(),
    cmap="Blues",
    cbar=False,
    yticklabels=False
)
plt.title("Missing Data Heatmap")
plt.show()

# =========================
# 4. CHUẨN HOÁ GIÁ TRỊ THIẾU
# =========================
data_df.replace(["N/A", "NA", "null", ""], np.nan, inplace=True)

# =========================
# 5. TÁCH CỘT SỐ & CHỮ
# =========================
num_cols = data_df.select_dtypes(include=[np.number]).columns
cat_cols = data_df.select_dtypes(exclude=[np.number]).columns

print("\nNumeric columns:", list(num_cols))
print("Categorical columns:", list(cat_cols))

# =========================
# 6. IMPUTATION
# =========================
num_imputer = SimpleImputer(strategy="mean")
data_df[num_cols] = num_imputer.fit_transform(data_df[num_cols])

cat_imputer = SimpleImputer(strategy="most_frequent")
data_df[cat_cols] = cat_imputer.fit_transform(data_df[cat_cols])

# =========================
# 7. KIỂM TRA SAU XỬ LÝ
# =========================
print("\n===== MISSING AFTER IMPUTATION =====")
print(data_df.isna().sum())

print("\n===== DATA AFTER CLEANING =====")
print(data_df.head())

# =========================
# 8. XUẤT RA CSV
# =========================
output_path = r"/media/voanhnhat/SDD_OUTSIDE5/PROJECT_WEATHER_FORECAST/Weather_Forcast_App/Merge_data/merged_weather_data_cleaned.csv"

data_df.to_csv(output_path, index=False, encoding="utf-8-sig")

print(f"\n✔ Dữ liệu đã được xuất ra CSV tại:\n{output_path}")