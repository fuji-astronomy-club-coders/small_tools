"""画像の読み込みとカラーマップ変換に関する共通処理。"""
from pathlib import Path
import numpy as np
from PIL import Image
import matplotlib
from matplotlib import colormaps


def load_grayscale(path: str | Path) -> np.ndarray:
    """画像を8-bitグレースケール配列として読み込む。"""
    with Image.open(path) as image:
        return np.asarray(image.convert("L"), dtype=np.uint8).copy()


def apply_colormap(gray: np.ndarray, cmap_name: str) -> Image.Image:
    """グレースケール配列へ指定カラーマップを適用し、RGB画像を返す。"""
    cmap = colormaps[cmap_name]
    rgb = (cmap(gray.astype(np.float32) / 255.0)[..., :3] * 255.0).round().astype(np.uint8)
    return Image.fromarray(rgb, mode="RGB")


def available_colormaps() -> list[str]:
    """Matplotlibで利用可能なカラーマップ名を返す。"""
    return sorted(colormaps)
