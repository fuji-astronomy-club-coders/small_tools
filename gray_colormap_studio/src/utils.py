"""画像の読み込みとカラーマップ変換に関する共通処理。"""

from pathlib import Path

import numpy as np
from matplotlib import colormaps
from PIL import Image

from src.package.image_loader import FITS_SUFFIXES, TIFF_SUFFIXES, load_image


def load_grayscale(path: str | Path) -> np.ndarray:
    """画像をグレースケール配列として読み込む。

    画素値のビット深度と数値範囲を保持する。カラー画像は輝度へ変換する。

    Args:
        path: 読み込む画像ファイルのパス。

    Returns:
        2D グレースケール配列。
    """
    image = load_image(path)
    if image.ndim == 2:
        return image
    if image.shape[-1] == 1:
        return image[..., 0]

    suffix = Path(path).suffix.lower()
    # tifffile と FITS は RGB 配列として扱い、OpenCV のラスター画像は BGR として扱う。
    is_rgb = suffix in TIFF_SUFFIXES or suffix in FITS_SUFFIXES
    weights = (
        np.array([0.299, 0.587, 0.114], dtype=np.float64)
        if is_rgb
        else np.array([0.114, 0.587, 0.299], dtype=np.float64)
    )
    gray = np.sum(image[..., :3].astype(np.float64) * weights, axis=-1)
    if np.issubdtype(image.dtype, np.integer):
        return np.rint(gray).astype(image.dtype)
    return gray.astype(image.dtype, copy=False)


def apply_colormap(gray: np.ndarray, cmap_name: str) -> Image.Image:
    """元の画素値を線形正規化してカラーマップを適用する。

    FITS などの 16-bit 整数・浮動小数点画像にも対応する。入力配列は変更しない。

    Args:
        gray: 2D グレースケール配列。
        cmap_name: Matplotlib のカラーマップ名。

    Returns:
        表示・保存用の RGB 画像。
    """
    values = np.asarray(gray, dtype=np.float64)
    finite = np.isfinite(values)
    normalized = np.zeros(values.shape, dtype=np.float32)
    if finite.any():
        minimum = float(np.min(values[finite]))
        maximum = float(np.max(values[finite]))
        if maximum > minimum:
            normalized[finite] = (
                (values[finite] - minimum) / (maximum - minimum)
            ).astype(np.float32)

    rgb = np.rint(colormaps[cmap_name](normalized)[..., :3] * 255.0)
    return Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8))


def available_colormaps() -> list[str]:
    """Matplotlib で利用可能なカラーマップ名を返す。"""
    return sorted(colormaps)
