#お試しなのでChatGPTが100%書いたコードです
import drms
import requests
from astropy.io import fits
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import os
import numpy as np


# 設定

# 取得したい日時（TAI 国際原子時） 日本時間（JST）は、TAIよりも現在 9時間遅れている
date = "2025.08.30_21:30:00_TAI"

# 保存先
# 実際のフォルダパスに変更してください
save_dir = r"C:\Users\sakil\OneDrive\デスクトップ\SDO_HMI"
os.makedirs(save_dir, exist_ok=True)

# 指定時刻の前後何分まで検索するか
search_minutes = 5

# 指定時刻を日時に変換

target_time = datetime.strptime(
    date, "%Y.%m.%d_%H:%M:%S_TAI"
)

start_time = target_time - timedelta(minutes=search_minutes)
end_time = target_time + timedelta(minutes=search_minutes)

start_str = start_time.strftime("%Y.%m.%d_%H:%M:%S_TAI")
end_str = end_time.strftime("%Y.%m.%d_%H:%M:%S_TAI")

print("指定時刻:", date)
print("検索開始:", start_str)
print("検索終了:", end_str)

# JSOCから観測データを検索

client = drms.Client()

series = f"hmi.Ic_45s[{start_str}-{end_str}]"

result = client.query(
    series,
    key="T_REC",
    seg="continuum"
)

# query() の結果は2つのDataFrameからなるタプル
records, segments = result

# 時刻とFITSファイルのパスを結合する
result = records.join(segments)

print("\n検索結果:")
print(result)

if result.empty:
    raise ValueError(
        "前後5分以内に該当する観測データがありません。"
    )

# 指定時刻に最も近いデータを選択

# T_RECはJSOCの検索結果に記録された時刻
result = result.copy()

result["観測日時"] = result["T_REC"].apply(
    lambda t: datetime.strptime(
        str(t), "%Y.%m.%d_%H:%M:%S_TAI"
    )
)

result["時間差秒"] = result["観測日時"].apply(
    lambda t: abs((t - target_time).total_seconds())
)

# 時間差が最も小さいレコードを選ぶ
best = result.loc[result["時間差秒"].idxmin()]

observed_time = best["観測日時"]
file_path = best["continuum"]
time_difference = (
    observed_time - target_time
).total_seconds()

print("\n選択したデータ")
print("実際の観測記録時刻:", best["T_REC"])
print("指定時刻との差:", time_difference, "秒")
print("JSOC上のファイル:", file_path)

if not isinstance(file_path, str) or not file_path.startswith("/"):
    raise ValueError("FITS画像の保存先を取得できませんでした。")

# FITS画像をダウンロード

url = "http://jsoc.stanford.edu" + file_path

# 観測時刻をファイル名に含める
time_label = observed_time.strftime("%Y%m%d_%H%M%S")

filename = f"sunspot_{time_label}_TAI.fits"
save_path = os.path.join(save_dir, filename)

response = requests.get(url, timeout=120)
response.raise_for_status()

# FITSファイルとして保存
with open(save_path, "wb") as f:
    f.write(response.content)

print("\nFITS保存完了")
print("保存先:", os.path.abspath(save_path))
print("ファイルサイズ:", os.path.getsize(save_path), "bytes")

# FITS画像を読み込む

with fits.open(save_path) as hdul:
    hdul.verify("exception")
    hdul.info()

    # データが格納されているHDUを探す
    image_hdu = next(
        (hdu for hdu in hdul if hdu.data is not None),
        None
    )

    if image_hdu is None:
        raise ValueError("FITS内に画像データがありません。")

    image = np.array(image_hdu.data, copy=True)

print("\nFITS形式: 読み込み成功")
print("画像サイズ:", image.shape)
print("データ型:", image.dtype)

# オレンジ色で表示

plt.figure(figsize=(8, 8))

plt.imshow(
    image,
    cmap="Oranges",
    origin="lower"
)

plt.colorbar(label="Intensity")
plt.title(
    f"SDO HMI Continuum Intensity\n"
    f"{best['T_REC']} (TAI)"
)
plt.axis("off")
plt.tight_layout()
plt.show()

# 保存したFITSファイルを再確認

with fits.open(save_path) as hdul:
    hdul.verify("exception")

    check_hdu = next(
        (hdu for hdu in hdul if hdu.data is not None),
        None
    )

    if check_hdu is None:
        raise ValueError("保存したFITSに画像データがありません。")

    print("\n===== 最終確認 =====")
    print("FITS形式: 正常")
    print("ファイル名:", filename)
    print("画像サイズ:", check_hdu.data.shape)
    print("画像データ型:", check_hdu.data.dtype)
    print("実際の観測記録時刻:", best["T_REC"])
    print("指定時刻との差:", time_difference, "秒")
    print("保存先:", os.path.abspath(save_path))