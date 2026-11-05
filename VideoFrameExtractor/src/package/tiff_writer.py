"""Atomic TIFF writing with sample-preservation validation."""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import tifffile


def write_tiff_atomic(image: np.ndarray, destination: Path, temp_dir: Path) -> None:
    """Write an image without reducing its integer sample depth or values."""
    image = np.asarray(image)
    if image.dtype not in (np.dtype("uint8"), np.dtype("uint16")):
        raise TypeError(f"未対応の画像データ型です: {image.dtype}")
    if image.ndim not in (2, 3) or (image.ndim == 3 and image.shape[-1] not in (3, 4)):
        raise ValueError(f"未対応の画像形状です: {image.shape}")

    temp_dir.mkdir(parents=True, exist_ok=True)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = temp_dir / f"{destination.stem}.{os.getpid()}.partial.tif"
    try:
        tifffile.imwrite(
            temporary,
            image,
            photometric="rgb" if image.ndim == 3 else "minisblack",
            metadata=None,
            compression=None,
        )
        with tifffile.TiffFile(temporary) as tif:
            if not tif.pages or tif.pages[0].shape != image.shape:
                raise IOError("TIFF検証に失敗しました（画像形状不一致）。")
            if tif.pages[0].dtype != image.dtype:
                raise IOError("TIFF検証に失敗しました（データ型不一致）。")
            saved = tif.pages[0].asarray()
            if not np.array_equal(saved, image):
                raise IOError("TIFF検証に失敗しました（画素値が一致しません）。")
        os.replace(temporary, destination)
    finally:
        if temporary.exists():
            temporary.unlink()
