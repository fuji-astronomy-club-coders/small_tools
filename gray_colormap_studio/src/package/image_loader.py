"""TIFF/FITS と一般的な画像ファイルを NumPy 配列として読み込む。"""

from pathlib import Path

import cv2
import numpy as np
import tifffile
from astropy.io import fits


FITS_SUFFIXES = {".fits", ".fit", ".fts"}
TIFF_SUFFIXES = {".tif", ".tiff"}


def load_image(image_path: str | Path) -> np.ndarray:
    """画像ファイルを元の画素データ型を維持して読み込む。

    TIFF は tifffile、FITS は Astropy、その他のラスター画像は
    OpenCV で読み込む。FITS は最初に画像データを持つ HDU を使用する。

    Args:
        image_path: 読み込む画像ファイルのパス。

    Returns:
        画素値を保持した NumPy 配列。カラー画像はチャンネル軸を持つ。

    Raises:
        ValueError: ファイルが存在しない、読み込めない、または対応外の配列形状の場合。
    """
    path = Path(image_path)
    if not path.is_file():
        raise ValueError(f"存在しない画像ファイルです: {path}")

    suffix = path.suffix.lower()
    if suffix in TIFF_SUFFIXES:
        image = tifffile.imread(path)
    elif suffix in FITS_SUFFIXES:
        with fits.open(path, memmap=False) as hdus:
            image_hdu = next((hdu for hdu in hdus if hdu.data is not None), None)
            if image_hdu is None:
                raise ValueError(f"FITS 内に画像データがありません: {path}")
            image = np.array(image_hdu.data, copy=True)
    else:
        image = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)

    if image is None:
        raise ValueError(f"画像の読み込みに失敗しました: {path}")

    array = np.asarray(image)
    # FITS の (1, 高さ, 幅) 形式は単一フレームとして扱う。
    # 2D の (1, 幅) のような細長い画像は squeeze せず、その形を保持する。
    if (
        array.ndim == 3
        and array.shape[0] == 1
        and array.shape[-1] not in (1, 3, 4)
    ):
        array = array[0]

    if array.size == 0:
        raise ValueError(f"画像データが空です: {path}")
    if array.ndim not in (2, 3):
        raise ValueError(
            f"対応していない画像配列の次元です: {array.shape} "
            "(2D グレースケールまたはチャンネル付き 2D 画像が必要です)"
        )
    if array.ndim == 3 and array.shape[-1] not in (1, 3, 4):
        raise ValueError(f"対応していないチャンネル数です: {array.shape}")

    if not (
        np.issubdtype(array.dtype, np.number)
        or np.issubdtype(array.dtype, np.bool_)
    ):
        raise ValueError(f"数値画像ではありません: {path}")

    if np.issubdtype(array.dtype, np.floating):
        array = np.nan_to_num(
            array, copy=True, nan=0.0, posinf=0.0, neginf=0.0
        )

    return array
