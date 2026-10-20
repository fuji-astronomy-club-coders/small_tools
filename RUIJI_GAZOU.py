import os
import hashlib
from typing import List
from tkinter.filedialog import askopenfilename, askdirectory

from PIL import Image
import imagehash


def get_file_hash(filepath: str) -> str:
    """
    ファイルのSHA-256ハッシュを取得する。

    Args:
        filepath (str): ハッシュを計算するファイルのパス。

    Returns:
        str: 計算されたSHA-256ハッシュの16進数文字列。
    """
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        # メモリ節約のため少しずつ読み込む[cite: 1]
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def find_exact_duplicate(target_filepath: str, search_dir: str) -> List[str]:
    """
    指定したファイルと完全に一致する（バイナリデータが等しい）ファイルをディレクトリから探す。

    Args:
        target_filepath (str): 検索の基準となるターゲットファイルの絶対/相対パス。
        search_dir (str): 検索対象となるディレクトリのパス。

    Returns:
        List[str]: 完全一致したファイルのパスを格納したリスト。
    """
    target_hash = get_file_hash(target_filepath)
    matched_files: List[str] = []

    for root, _, files in os.walk(search_dir):
        for file in files:
            file_path = os.path.join(root, file)
            # ターゲットファイル自身は除外したい場合は以下の判定を追加[cite: 1]
            if os.path.abspath(file_path) == os.path.abspath(target_filepath):
                continue

            try:
                if get_file_hash(file_path) == target_hash:
                    print(f"[完全一致] {file_path}")  # [cite: 1]
                    matched_files.append(file_path)
            except Exception:
                pass

    return matched_files


def find_similar_images(
    target_img_path: str, search_dir: str, cutoff: int = 5
) -> List[str]:
    """
    指定画像と見た目が似ている画像をディレクトリから探す。

    Args:
        target_img_path (str): 検索の基準となるターゲット画像のパス。
        search_dir (str): 検索対象となるディレクトリのパス。
        cutoff (int, optional): 類似度の閾値。値が小さいほど厳密に判定（0でほぼ完全一致、5〜10で類似画像）[cite: 2]。デフォルトは5。

    Returns:
        List[str]: 類似していると判定された画像のパスを格納したリスト。
    """
    # 探したい元画像のハッシュを計算[cite: 2]
    try:
        target_hash = imagehash.phash(Image.open(target_img_path))
    except Exception as e:
        print(f"元画像の読み込みに失敗しました: {e}")  # [cite: 2]
        return []

    matched_files: List[str] = []

    # ディレクトリ内を探索[cite: 2]
    for root, _, files in os.walk(search_dir):
        for file in files:
            if file.lower().endswith(
                (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp")
            ):  # [cite: 2]
                file_path = os.path.join(root, file)

                try:
                    # 比較先画像のハッシュを計算[cite: 2]
                    test_hash = imagehash.phash(Image.open(file_path))

                    # ハッシュの差分を計算[cite: 2]
                    distance = target_hash - test_hash

                    if distance <= cutoff:
                        print(f"[一致] 距離:{distance} - {file_path}")  # [cite: 2]
                        matched_files.append(file_path)
                except Exception:
                    # 画像として読み込めないファイルはスキップ[cite: 2]
                    pass

    return matched_files


if __name__ == "__main__":
    print("=== 画像検索モジュール テスト実行 ===")

    # 探したい指定画像[cite: 1, 2]
    target = askopenfilename(title="ターゲット画像を選択してください")

    if target:
        # 探す対象のディレクトリ[cite: 1, 2]
        directory = askdirectory(title="検索対象のディレクトリを選択してください")

        if directory:
            print(f"Target image: {target}")  # [cite: 1, 2]
            print(f"Directory   : {directory}\n")  # [cite: 1, 2]

            # --- 完全一致検索 ---
            print("【完全一致ファイルの検索を開始します...】")  # [cite: 1]
            exact_results = find_exact_duplicate(target, directory)
            print(
                f"-> 合計 {len(exact_results)} 件の完全一致ファイルが見つかりました。\n"
            )  # [cite: 1]

            # --- 類似画像検索 ---
            print("【類似画像の検索を開始します... (cutoff=3)】")  # [cite: 2]
            similar_results = find_similar_images(target, directory, cutoff=3)
            print(
                f"-> 合計 {len(similar_results)} 件の類似画像が見つかりました。\n"
            )  # [cite: 2]

        else:
            print("ディレクトリが選択されなかったため、処理を中断します。")
    else:
        print("ターゲット画像が選択されなかったため、処理を中断します。")
