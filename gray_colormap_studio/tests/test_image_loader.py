"""画像ローダーと画素値変換のテスト。"""

import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from astropy.io import fits

APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from src.package.image_loader import load_image
from src.utils import apply_colormap, load_grayscale


class ImageLoaderTests(unittest.TestCase):
    """FITS 読み込みと元画素値の保持を確認する。"""

    def test_loads_fits_image_and_preserves_uint16(self) -> None:
        expected = np.array([[0, 256], [4096, 65535]], dtype=np.uint16)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.fits"
            fits.PrimaryHDU(data=expected).writeto(path)

            actual = load_image(path)

        self.assertEqual(actual.dtype, np.uint16)
        np.testing.assert_array_equal(actual, expected)

    def test_loads_first_hdu_containing_image_data(self) -> None:
        expected = np.arange(12, dtype=np.float32).reshape(3, 4)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "extension.fits"
            fits.HDUList(
                [fits.PrimaryHDU(), fits.ImageHDU(data=expected)]
            ).writeto(path)

            actual = load_image(path)

        np.testing.assert_array_equal(actual, expected)

    def test_loads_singleton_frame_without_collapsing_2d_shapes(self) -> None:
        expected = np.array([[7, 11, 13, 17]], dtype=np.uint16)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "single-row.fits"
            fits.PrimaryHDU(data=expected).writeto(path)

            actual = load_image(path)

        self.assertEqual(actual.shape, (1, 4))
        np.testing.assert_array_equal(actual, expected)

    def test_grayscale_conversion_keeps_uint16_values(self) -> None:
        expected = np.array([[10, 1000], [30000, 60000]], dtype=np.uint16)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "gray.fit"
            fits.PrimaryHDU(data=expected).writeto(path)

            actual = load_grayscale(path)

        self.assertEqual(actual.dtype, np.uint16)
        np.testing.assert_array_equal(actual, expected)

    def test_colormap_normalizes_native_value_range(self) -> None:
        values = np.array([[0, 65535]], dtype=np.uint16)

        image = apply_colormap(values, "gray")

        self.assertEqual(image.mode, "RGB")
        self.assertEqual(image.size, (2, 1))
        self.assertNotEqual(image.getpixel((0, 0)), image.getpixel((1, 0)))


if __name__ == "__main__":
    unittest.main()
