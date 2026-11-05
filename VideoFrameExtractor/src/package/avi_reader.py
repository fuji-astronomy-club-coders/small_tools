"""AVI frame reader using PyAV without silently reducing high bit depth."""
from __future__ import annotations

import logging
import re
from pathlib import Path

import av
import numpy as np

logger = logging.getLogger(__name__)


class AviReader:
    """Decode AVI frames and keep high-bit-depth formats at 16 bits."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.container = av.open(str(self.path))
        streams = [s for s in self.container.streams if s.type == "video"]
        if not streams:
            self.container.close()
            raise ValueError("AVI内に動画ストリームがありません。")
        self.stream = streams[0]
        logger.info("AVI: %s, codec=%s", self.path, self.stream.codec_context.name)

    @staticmethod
    def _is_high_bit_depth(frame) -> bool:
        """Detect >8-bit component formats, including subsampled YUV formats."""
        fmt = frame.format
        name = (getattr(fmt, "name", "") or "").lower()

        # bits_per_pixel is not enough: yuv420p10le reports 15 bits/pixel,
        # despite each component being 10-bit. Check the pixel-format name.
        if re.search(r"(?:p|gray|gbr|rgb|bgr|ya|yuv|yuva)(?:0?10|0?12|0?14|16)(?:le|be|$)", name):
            return True
        if any(token in name for token in ("gray16", "rgb48", "bgr48", "gbrp10", "gbrp12", "gbrp16")):
            return True

        # PyAV versions expose component bit depths on the format object.
        for component in getattr(fmt, "components", ()) or ():
            bits = getattr(component, "bits", None)
            if isinstance(bits, int) and bits > 8:
                return True
        return False

    @classmethod
    def _frame_to_array(cls, frame) -> np.ndarray:
        """Convert a decoded frame to uint8 or uint16 without 8-bit truncation."""
        fmt = (frame.format.name or "").lower()

        if fmt in ("gray", "gray8"):
            arr = frame.to_ndarray(format="gray")
            return np.asarray(arr, dtype=np.uint8)

        if fmt in ("gray16le", "gray16be"):
            arr = frame.to_ndarray(format="gray16le")
            return np.asarray(arr).astype(np.uint16, copy=False)

        if cls._is_high_bit_depth(frame):
            # Convert high-depth RGB/YUV/Bayer-decoded frames to 16-bit RGB.
            # For high-depth grayscale sources keep a single channel.
            if fmt.startswith("gray"):
                arr = frame.to_ndarray(format="gray16le")
                return np.asarray(arr).astype(np.uint16, copy=False)
            arr = frame.to_ndarray(format="rgb48le")
            arr = np.asarray(arr)
            if arr.dtype.itemsize != 2:
                raise ValueError(
                    f"高ビット深度AVIの16bit変換に失敗しました: format={fmt}, dtype={arr.dtype}"
                )
            return arr.astype(np.uint16, copy=False)

        if fmt in ("rgb24", "bgr24"):
            return frame.to_ndarray(format="rgb24").astype(np.uint8, copy=False)

        # 8-bit YUV / other common formats are converted to ordinary RGB8.
        arr = frame.to_ndarray(format="rgb24")
        return np.asarray(arr, dtype=np.uint8)

    def read_frame(self, index: int) -> np.ndarray:
        if index < 0:
            raise IndexError("フレーム番号は0以上にしてください。")
        self.container.seek(0, stream=self.stream, backward=True, any_frame=False)
        for current, frame in enumerate(self.container.decode(self.stream)):
            if current == index:
                array = self._frame_to_array(frame)
                logger.debug(
                    "AVI frame=%d pixel_format=%s output_dtype=%s shape=%s",
                    index,
                    frame.format.name,
                    array.dtype,
                    array.shape,
                )
                return array
        raise IndexError(f"AVIフレーム範囲外: {index}")

    def close(self) -> None:
        self.container.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
