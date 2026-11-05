"""SER reader with explicit support for real-world 16-bit byte-order variants."""
from __future__ import annotations

import logging
import struct
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

HEADER_SIZE = 178
COLOR_NAMES = {
    0: "MONO",
    8: "BAYER_RGGB",
    9: "BAYER_GRBG",
    10: "BAYER_GBRG",
    11: "BAYER_BGGR",
    100: "RGB",
    101: "BGR",
}


class SerReader:
    """Read SER frames while preserving their original integer samples.

    ``endian_mode`` controls the interpretation of the SER header's
    ``LittleEndian`` field:

    - ``legacy``: de-facto convention used by Siril / SER Player / GoQat;
      flag 0 means little-endian and flag 1 means big-endian.
    - ``spec``: literal interpretation of the field name/specification;
      flag 1 means little-endian and flag 0 means big-endian.
    - ``little`` / ``big``: force the byte order regardless of the flag.

    The default is ``legacy`` because this is the convention used by many
    astronomical SER producers and readers.
    """

    VALID_ENDIAN_MODES = {"legacy", "spec", "little", "big"}

    def __init__(self, path: Path, endian_mode: str = "legacy"):
        self.path = Path(path)
        self._file = self.path.open("rb")
        try:
            raw = self._file.read(HEADER_SIZE)
            if len(raw) != HEADER_SIZE:
                raise ValueError("SERヘッダーが不足しています。")

            file_id = raw[:14].split(b"\0", 1)[0]
            if file_id != b"LUCAM-RECORDER":
                raise ValueError("SERファイル識別子が不正です。")

            values = struct.unpack("<7I", raw[14:42])
            (
                self.luid,
                self.color_id,
                self.little_endian_flag,
                self.width,
                self.height,
                self.pixel_depth,
                self.frame_count,
            ) = values

            if self.width <= 0 or self.height <= 0 or self.frame_count <= 0:
                raise ValueError("SERヘッダーの寸法またはフレーム数が不正です。")
            if self.little_endian_flag not in (0, 1):
                raise ValueError(
                    f"SER LittleEndianフラグが不正です: {self.little_endian_flag}"
                )
            if self.color_id not in COLOR_NAMES:
                raise ValueError(f"未対応のSER ColorID: {self.color_id}")
            # PixelDepthPerPlane may be 10/12/14 for cameras that store those
            # samples in 16-bit words. The container width is still 2 bytes.
            if self.pixel_depth < 1 or self.pixel_depth > 16:
                raise ValueError(f"未対応のSERビット深度: {self.pixel_depth}")
            if not isinstance(endian_mode, str):
                raise ValueError("ser_endian_modeは文字列で指定してください。")
            endian_mode = endian_mode.strip().lower()
            if endian_mode not in self.VALID_ENDIAN_MODES:
                raise ValueError(
                    "ser_endian_modeは legacy / spec / little / big のいずれかです。"
                )
            self.endian_mode = endian_mode

            self.channels = 3 if self.color_id in (100, 101) else 1
            self.bytes_per_sample = 1 if self.pixel_depth <= 8 else 2
            self.frame_bytes = (
                self.width * self.height * self.channels * self.bytes_per_sample
            )
            self.data_offset = HEADER_SIZE
            expected = self.data_offset + self.frame_bytes * self.frame_count
            actual = self.path.stat().st_size
            if actual < expected:
                raise ValueError(
                    f"SERデータが途中で切れています。必要={expected} bytes, 実際={actual} bytes"
                )

            self.byte_order = self._resolve_byte_order()
            self.dtype = np.dtype("u1") if self.bytes_per_sample == 1 else np.dtype(
                "<u2" if self.byte_order == "little" else ">u2"
            )
            logger.info(
                "SER: %s, %dx%d, PixelDepthPerPlane=%dbit, ColorID=%s, "
                "LittleEndian flag=%d, data byte order=%s (%s), frames=%d",
                self.path,
                self.width,
                self.height,
                self.pixel_depth,
                COLOR_NAMES[self.color_id],
                self.little_endian_flag,
                self.byte_order,
                self.endian_mode,
                self.frame_count,
            )
        except Exception:
            self._file.close()
            raise

    def _resolve_byte_order(self) -> str:
        if self.bytes_per_sample == 1:
            return "not-applicable"
        if self.endian_mode == "little":
            return "little"
        if self.endian_mode == "big":
            return "big"
        if self.endian_mode == "legacy":
            # De-facto convention adopted by Siril, SER Player and others.
            return "little" if self.little_endian_flag == 0 else "big"
        # Literal specification interpretation.
        return "little" if self.little_endian_flag == 1 else "big"

    def read_frame(self, index: int) -> np.ndarray:
        """Read one zero-based frame into native uint8/uint16 memory."""
        if index < 0 or index >= self.frame_count:
            raise IndexError(f"SERフレーム範囲外: {index} (総数={self.frame_count})")
        self._file.seek(self.data_offset + index * self.frame_bytes)
        raw = self._file.read(self.frame_bytes)
        if len(raw) != self.frame_bytes:
            raise IOError(f"フレーム{index}の読み込みが途中で終了しました。")

        arr = np.frombuffer(raw, dtype=self.dtype)
        if self.channels == 3:
            arr = arr.reshape(self.height, self.width, 3)
            if self.color_id == 101:
                arr = arr[:, :, ::-1]
        else:
            arr = arr.reshape(self.height, self.width)

        # Normalize only the NumPy byte-order metadata, never the pixel range.
        # This performs a byte swap when needed but does not scale/clip values.
        target_dtype = np.uint8 if self.bytes_per_sample == 1 else np.uint16
        return arr.astype(target_dtype, copy=True)

    def close(self) -> None:
        if not self._file.closed:
            self._file.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
