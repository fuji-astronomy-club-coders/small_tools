"""画像一覧・プレビュー・ヒストグラム・一括保存を備えたメインウィンドウ."""

from pathlib import Path

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PIL import Image
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from src.utils import apply_colormap, available_colormaps, load_grayscale


IMAGE_FILTER = (
    "画像ファイル (*.png *.jpg *.jpeg *.tif *.tiff *.bmp *.webp *.gif *.fits *.fit *.fts);;"
    "FITS ファイル (*.fits *.fit *.fts);;"
    "すべてのファイル (*)"
)


class MainWindow(QMainWindow):
    """Gray Colormap Studio のメイン画面。"""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Gray Colormap Studio")
        self.resize(1180, 820)
        self.paths: list[Path] = []
        self.gray_cache: dict[Path, np.ndarray] = {}
        self.output_dir: Path | None = None
        self.histogram_edges: np.ndarray | None = None
        self.histogram_counts: np.ndarray | None = None
        self.histogram_cursor_line = None
        self._build_ui()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        toolbar = QHBoxLayout()
        self.add_button = QPushButton("画像を追加")
        self.remove_button = QPushButton("選択画像を一覧から削除")
        self.reload_button = QPushButton("選択画像を再読み込み")
        toolbar.addWidget(self.add_button)
        toolbar.addWidget(self.remove_button)
        toolbar.addWidget(self.reload_button)
        toolbar.addStretch(1)
        root.addLayout(toolbar)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(splitter, 1)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel("読み込み画像"))
        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        left_layout.addWidget(self.file_list, 1)
        splitter.addWidget(left)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        controls = QGroupBox("変換設定")
        form = QFormLayout(controls)
        self.cmap_combo = QComboBox()
        self.cmap_combo.addItems(available_colormaps())
        self.cmap_combo.setCurrentText("viridis")
        self.output_label = QLabel("未選択（元画像の隣に保存）")
        self.output_label.setWordWrap(True)
        self.output_button = QPushButton("保存先フォルダーを選択")
        self.save_selected_button = QPushButton("選択画像を保存")
        self.save_all_button = QPushButton("すべて保存")
        self.auto_preview = QCheckBox("カラーマップ変更時にプレビューを更新")
        self.auto_preview.setChecked(True)
        form.addRow("カラーマップ", self.cmap_combo)
        form.addRow("出力先", self.output_label)
        form.addRow(self.output_button)
        form.addRow(self.auto_preview)
        form.addRow(self.save_selected_button, self.save_all_button)
        right_layout.addWidget(controls)

        self.preview_title = QLabel("画像を選択してください")
        self.preview_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview = QLabel("プレビュー")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumSize(400, 260)
        self.preview.setStyleSheet(
            "QLabel { background: #20242b; color: #d8dce2; "
            "border: 1px solid #505761; }"
        )
        self.preview.setScaledContents(False)
        right_layout.addWidget(self.preview_title)
        right_layout.addWidget(self.preview, 3)

        self.histogram_title = QLabel("画素値ヒストグラム（縦軸：対数）")
        self.histogram_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(self.histogram_title)
        self.histogram_figure = Figure(figsize=(7, 2.2), tight_layout=True)
        self.histogram_axes = self.histogram_figure.add_subplot(111)
        self.histogram_canvas = FigureCanvasQTAgg(self.histogram_figure)
        self.histogram_canvas.setMinimumHeight(190)
        self.histogram_canvas.mpl_connect(
            "motion_notify_event", self._on_histogram_motion
        )
        right_layout.addWidget(self.histogram_canvas, 2)
        self.histogram_value_label = QLabel(
            "ヒストグラム上にカーソルを移動すると、画素値と画素数を表示します。"
        )
        self.histogram_value_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        right_layout.addWidget(self.histogram_value_label)

        self.status_label = QLabel("画像を追加してください。")
        root.addWidget(self.status_label)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 4)

        self.add_button.clicked.connect(self.add_images)
        self.remove_button.clicked.connect(self.remove_selected)
        self.reload_button.clicked.connect(self.reload_selected)
        self.file_list.currentItemChanged.connect(self.update_preview)
        self.cmap_combo.currentTextChanged.connect(self._colormap_changed)
        self.output_button.clicked.connect(self.choose_output_dir)
        self.save_selected_button.clicked.connect(
            lambda: self.save_images(selected_only=True)
        )
        self.save_all_button.clicked.connect(
            lambda: self.save_images(selected_only=False)
        )
        self._clear_histogram()

    def add_images(self) -> None:
        names, _ = QFileDialog.getOpenFileNames(
            self, "画像ファイルを選択", "", IMAGE_FILTER
        )
        if not names:
            return

        added = 0
        failures: list[str] = []
        for name in names:
            path = Path(name)
            if path in self.paths:
                continue
            try:
                self.gray_cache[path] = load_grayscale(path)
                self.paths.append(path)
                self.file_list.addItem(str(path))
                added += 1
            except Exception as exc:
                failures.append(f"{path.name}: {exc}")

        self.status_label.setText(
            f"{added} 件の画像を追加しました。合計 {len(self.paths)} 件。"
        )
        if self.file_list.count() and self.file_list.currentRow() < 0:
            self.file_list.setCurrentRow(0)
        elif self.file_list.currentItem() is not None:
            self.update_preview()
        if failures:
            QMessageBox.warning(self, "読み込みエラー", "\n".join(failures[:15]))

    def remove_selected(self) -> None:
        rows = sorted(
            {self.file_list.row(item) for item in self.file_list.selectedItems()},
            reverse=True,
        )
        for row in rows:
            path = self.paths.pop(row)
            self.gray_cache.pop(path, None)
            self.file_list.takeItem(row)

        if not self.paths:
            self.preview.clear()
            self.preview.setText("プレビュー")
            self.preview_title.setText("画像を選択してください")
            self._clear_histogram()
        elif self.file_list.currentItem() is not None:
            self.update_preview()
        self.status_label.setText(f"一覧内の画像数: {len(self.paths)}")

    def reload_selected(self) -> None:
        item = self.file_list.currentItem()
        if item is None:
            QMessageBox.information(
                self, "再読み込み", "再読み込みする画像を選択してください。"
            )
            return
        path = Path(item.text())
        try:
            self.gray_cache[path] = load_grayscale(path)
            self.update_preview()
            self.status_label.setText(f"再読み込みしました: {path.name}")
        except Exception as exc:
            QMessageBox.critical(self, "再読み込みエラー", f"{path}\n{exc}")

    def choose_output_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self, "保存先フォルダーを選択"
        )
        if directory:
            self.output_dir = Path(directory)
            self.output_label.setText(str(self.output_dir))

    def _colormap_changed(self, _name: str) -> None:
        if self.auto_preview.isChecked():
            self._render_selected_image(update_histogram=False)

    def update_preview(self, *_args) -> None:
        self._render_selected_image(update_histogram=True)

    def _render_selected_image(self, update_histogram: bool) -> None:
        item = self.file_list.currentItem()
        if item is None:
            return
        path = Path(item.text())
        try:
            gray = self.gray_cache.get(path)
            if gray is None:
                gray = load_grayscale(path)
                self.gray_cache[path] = gray
            result = apply_colormap(gray, self.cmap_combo.currentText())
            self._show_image(result)
            self.preview_title.setText(
                f"{path.name}  |  {gray.shape[1]} × {gray.shape[0]} px  |  "
                f"{self.cmap_combo.currentText()}  |  "
                f"範囲: {np.min(gray):.6g} ～ {np.max(gray):.6g}"
            )
            self.status_label.setText(f"プレビュー中: {path.name}")
            if update_histogram:
                self._update_histogram(gray)
        except Exception as exc:
            QMessageBox.critical(self, "プレビューエラー", str(exc))

    def _show_image(self, image: Image.Image) -> None:
        rgb = np.asarray(image.convert("RGB"))
        height, width, _ = rgb.shape
        qimage = QImage(
            rgb.data, width, height, 3 * width, QImage.Format.Format_RGB888
        ).copy()
        pixmap = QPixmap.fromImage(qimage)
        self.preview.setPixmap(
            pixmap.scaled(
                self.preview.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def _update_histogram(self, gray: np.ndarray) -> None:
        values = np.asarray(gray).reshape(-1)
        values = values[np.isfinite(values)]
        self.histogram_axes.clear()
        self.histogram_edges = None
        self.histogram_counts = None
        self.histogram_cursor_line = None

        if values.size == 0:
            self.histogram_axes.set_title("No finite pixel values")
            self.histogram_canvas.draw_idle()
            self.histogram_value_label.setText("表示できる画素値がありません。")
            return

        minimum = float(np.min(values))
        maximum = float(np.max(values))
        if maximum == minimum:
            padding = max(abs(minimum) * 1e-6, 0.5)
            histogram_range = (minimum - padding, maximum + padding)
        else:
            histogram_range = (minimum, maximum)

        counts, edges = np.histogram(values, bins=256, range=histogram_range)
        centers = (edges[:-1] + edges[1:]) / 2
        widths = np.diff(edges)
        nonzero = counts > 0
        self.histogram_axes.bar(
            centers[nonzero],
            counts[nonzero],
            width=widths[nonzero],
            align="center",
            linewidth=0,
        )
        self.histogram_axes.set_yscale("log")
        self.histogram_axes.set_xlabel("Pixel value")
        self.histogram_axes.set_ylabel("Pixel count (log)")
        self.histogram_axes.grid(True, axis="y", alpha=0.25)
        self.histogram_axes.set_xlim(edges[0], edges[-1])
        self.histogram_edges = edges
        self.histogram_counts = counts
        self.histogram_cursor_line = self.histogram_axes.axvline(
            centers[0], visible=False, linewidth=1
        )
        self.histogram_canvas.draw_idle()
        self.histogram_value_label.setText(
            f"値の範囲: {minimum:.6g} ～ {maximum:.6g}　"
            f"|　画素数: {values.size:,}"
        )

    def _on_histogram_motion(self, event) -> None:
        if (
            event.inaxes is not self.histogram_axes
            or event.xdata is None
            or self.histogram_edges is None
            or self.histogram_counts is None
            or self.histogram_cursor_line is None
        ):
            return

        index = int(
            np.searchsorted(self.histogram_edges, event.xdata, side="right") - 1
        )
        index = min(max(index, 0), len(self.histogram_counts) - 1)
        lower = self.histogram_edges[index]
        upper = self.histogram_edges[index + 1]
        count = int(self.histogram_counts[index])
        self.histogram_cursor_line.set_xdata([event.xdata, event.xdata])
        self.histogram_cursor_line.set_visible(True)
        self.histogram_value_label.setText(
            f"カーソル値: {event.xdata:.6g}　|　"
            f"階級: [{lower:.6g}, {upper:.6g})　|　"
            f"画素数: {count:,}"
        )
        self.histogram_canvas.draw_idle()

    def _clear_histogram(self) -> None:
        self.histogram_axes.clear()
        self.histogram_axes.set_title("Pixel histogram")
        self.histogram_edges = None
        self.histogram_counts = None
        self.histogram_cursor_line = None
        self.histogram_canvas.draw_idle()
        self.histogram_value_label.setText(
            "ヒストグラム上にカーソルを移動すると、画素値と画素数を表示します。"
        )

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._render_selected_image(update_histogram=False)

    def save_images(self, selected_only: bool) -> None:
        if selected_only:
            items = self.file_list.selectedItems()
            if not items and self.file_list.currentItem() is not None:
                items = [self.file_list.currentItem()]
            targets = [Path(item.text()) for item in items]
        else:
            targets = list(self.paths)
        if not targets:
            QMessageBox.information(self, "保存", "保存する画像がありません。")
            return

        cmap_name = self.cmap_combo.currentText()
        failures: list[str] = []
        saved = 0
        progress = QProgressDialog(
            "画像を変換して保存しています…", "キャンセル", 0, len(targets), self
        )
        progress.setWindowTitle("一括保存")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.show()

        for index, path in enumerate(targets, start=1):
            if progress.wasCanceled():
                break
            try:
                gray = self.gray_cache.get(path)
                if gray is None:
                    gray = load_grayscale(path)
                output_dir = self.output_dir or path.parent
                output_dir.mkdir(parents=True, exist_ok=True)
                destination = output_dir / f"{path.stem}_{cmap_name}.png"
                apply_colormap(gray, cmap_name).save(destination, format="PNG")
                saved += 1
            except Exception as exc:
                failures.append(f"{path.name}: {exc}")
            progress.setValue(index)

        progress.close()
        self.status_label.setText(f"保存完了: {saved}/{len(targets)} 件")
        message = f"{saved} 件の画像を保存しました。"
        if failures:
            message += "\n\n失敗:\n" + "\n".join(failures[:15])
            QMessageBox.warning(self, "保存結果", message)
        else:
            QMessageBox.information(self, "保存結果", message)
