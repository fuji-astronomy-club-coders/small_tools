"""Regression tests for byte-order-safe 16-bit frame extraction."""
from __future__ import annotations

import importlib
import struct
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import tifffile

from src.package.ser_reader import SerReader
from src.package.tiff_writer import write_tiff_atomic


def make_ser(
    path: Path,
    pixels: np.ndarray,
    *,
    color_id: int = 0,
    pixel_depth: int = 16,
    file_byte_order: str = "little",
    flag: int = 0,
) -> None:
    """Write one SER frame with independently selectable flag and byte order."""
    height, width = pixels.shape[:2]
    header = bytearray(178)
    header[:14] = b"LUCAM-RECORDER"
    struct.pack_into(
        "<7I", header, 14,
        0, color_id, flag, width, height, pixel_depth, 1,
    )
    dtype = np.dtype("<u2" if file_byte_order == "little" else ">u2")
    path.write_bytes(bytes(header) + pixels.astype(dtype, copy=False).tobytes())


class TestSer16Bit(unittest.TestCase):
    def test_default_de_facto_flag_zero_means_little_endian(self):
        expected = np.array([[0, 1, 255, 256, 0x1234, 32768, 65535]], dtype=np.uint16)
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "legacy_little.ser"
            make_ser(source, expected, file_byte_order="little", flag=0)
            with SerReader(source) as reader:
                actual = reader.read_frame(0)
                self.assertEqual(reader.byte_order, "little")
            self.assertEqual(actual.dtype, np.uint16)
            np.testing.assert_array_equal(actual, expected)

    def test_default_de_facto_flag_one_means_big_endian(self):
        expected = np.array([[0, 1, 255, 256, 0x1234, 32768, 65535]], dtype=np.uint16)
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "legacy_big.ser"
            make_ser(source, expected, file_byte_order="big", flag=1)
            with SerReader(source) as reader:
                actual = reader.read_frame(0)
                self.assertEqual(reader.byte_order, "big")
            self.assertEqual(actual.dtype, np.uint16)
            np.testing.assert_array_equal(actual, expected)

    def test_spec_mode_is_available_for_spec_conforming_files(self):
        expected = np.array([[0x0102, 0x0FFF, 0x8001, 0xFFFF]], dtype=np.uint16)
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "spec_little.ser"
            make_ser(source, expected, file_byte_order="little", flag=1)
            with SerReader(source, endian_mode="spec") as reader:
                actual = reader.read_frame(0)
            np.testing.assert_array_equal(actual, expected)

    def test_12bit_samples_in_16bit_words_are_preserved(self):
        expected = np.array([[0, 1, 255, 256, 2048, 4095]], dtype=np.uint16)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, output = root / "12bit.ser", root / "frame.tiff"
            make_ser(source, expected, pixel_depth=12, file_byte_order="little", flag=0)
            with SerReader(source) as reader:
                actual = reader.read_frame(0)
                self.assertEqual(reader.bytes_per_sample, 2)
            write_tiff_atomic(actual, output, root / "temp")
            saved = tifffile.imread(output)
            self.assertEqual(saved.dtype, np.uint16)
            np.testing.assert_array_equal(saved, expected)

    def test_rgb_16bit_is_preserved(self):
        expected = np.array(
            [[[0, 32768, 65535], [1024, 2048, 4096]]], dtype=np.uint16
        )
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "rgb.ser"
            make_ser(source, expected, color_id=100, file_byte_order="little", flag=0)
            with SerReader(source) as reader:
                actual = reader.read_frame(0)
            self.assertEqual(actual.dtype, np.uint16)
            np.testing.assert_array_equal(actual, expected)

    def test_endian_override_can_be_forced(self):
        expected = np.array([[0x0102, 0x1234, 0xFFFF]], dtype=np.uint16)
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "forced.ser"
            make_ser(source, expected, file_byte_order="big", flag=0)
            with SerReader(source, endian_mode="big") as reader:
                actual = reader.read_frame(0)
            np.testing.assert_array_equal(actual, expected)


class TestAviHighBitDepth(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fake_av = types.ModuleType("av")
        cls.fake_av.open = lambda _path: None
        cls.patch = patch.dict(sys.modules, {"av": cls.fake_av})
        cls.patch.start()
        cls.module = importlib.import_module("src.package.avi_reader")
        importlib.reload(cls.module)

    @classmethod
    def tearDownClass(cls):
        cls.patch.stop()

    def test_gray16le_keeps_uint16_samples(self):
        expected = np.array([[0, 257, 32768, 65535]], dtype=np.uint16)

        class Format:
            name = "gray16le"
            bits_per_pixel = 16
            components = []

        class Frame:
            format = Format()
            def to_ndarray(self, format=None):
                self.requested_format = format
                return expected.copy()

        frame = Frame()
        actual = self.module.AviReader._frame_to_array(frame)
        self.assertEqual(frame.requested_format, "gray16le")
        self.assertEqual(actual.dtype, np.uint16)
        np.testing.assert_array_equal(actual, expected)

    def test_yuv420p10le_converts_to_rgb48_not_rgb24(self):
        expected = np.array([[[0, 1024, 65535]]], dtype=np.uint16)

        class Format:
            name = "yuv420p10le"
            bits_per_pixel = 15  # subsampling makes this less than 24
            components = []

        class Frame:
            format = Format()
            def to_ndarray(self, format=None):
                self.requested_format = format
                return expected.copy()

        frame = Frame()
        actual = self.module.AviReader._frame_to_array(frame)
        self.assertEqual(frame.requested_format, "rgb48le")
        self.assertEqual(actual.dtype, np.uint16)
        np.testing.assert_array_equal(actual, expected)


if __name__ == "__main__":
    unittest.main()
