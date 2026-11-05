"""画像一覧・Matplotlib プレビュー・ヒストグラム操作を備えたメインウィンドウ."""

from pathlib import Path

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib.widgets import SpanSelector
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
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
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from src.utils import available_colormaps, load_grayscale


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
        self.resize(1280, 920)
        self.paths: list[Path] = []
        self.gray_cache: dict[Path, np.ndarray] = {}
        self.output_dir: Path | None = None
        self.histogram_edges: np.ndarray | None = None
        self.histogram_counts: np.ndarray | None = None
        self.histogram_cursor_line = None
        self.histogram_span: SpanSelector | None = None
        self._histogram_press_x: float | None = None
        self.display_min: float | None = None
        self.display_max: float | None = None
        self.contour_level: float | None = None
        self.histogram_contour_line = None
        self.zoom_factor = 1.0
        self.zoom_center: tuple[float, float] | None = None
        self._preview_full_xlim: tuple[float, float] | None = None
        self._preview_full_ylim: tuple[float, float] | None = None
        self._building_controls = False
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

        self.operation_header = QToolButton()
        self.operation_header.setText("Matplotlib 表示・画像オペレーション")
        self.operation_header.setCheckable(True)
        self.operation_header.setChecked(True)
        self.operation_header.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextBesideIcon
        )
        self.operation_header.setArrowType(Qt.ArrowType.DownArrow)
        right_layout.addWidget(self.operation_header)

        controls = QGroupBox()
        self.operations_panel = controls
        form = QFormLayout(controls)
        self.cmap_combo = QComboBox()
        self.cmap_combo.addItems(available_colormaps())
        self.cmap_combo.setCurrentText("gray")
        self.interpolation_combo = QComboBox()
        self.interpolation_combo.addItems(
            ["nearest", "bilinear", "bicubic", "spline16", "lanczos", "none"]
        )
        self.origin_combo = QComboBox()
        self.origin_combo.addItems(["upper", "lower"])
        self.aspect_combo = QComboBox()
        self.aspect_combo.addItems(["equal", "auto"])
        self.colorbar_check = QCheckBox("カラーバーを表示")
        self.colorbar_check.setChecked(True)
        self.contour_check = QCheckBox("等輝度線を表示")
        self.contour_check.setChecked(True)
        self.vmin_spin = QDoubleSpinBox()
        self.vmax_spin = QDoubleSpinBox()
        for spin in (self.vmin_spin, self.vmax_spin):
            spin.setRange(-1e300, 1e300)
            spin.setDecimals(8)
            spin.setKeyboardTracking(False)
        self.reset_range_button = QPushButton("輝度範囲を全体に戻す")
        self.zoom_in_button = QPushButton("＋ 拡大")
        self.zoom_out_button = QPushButton("－ 縮小")
        self.zoom_reset_button = QPushButton("全体表示")
        self.zoom_value_label = QLabel("100%")
        zoom_row = QWidget()
        zoom_layout = QHBoxLayout(zoom_row)
        zoom_layout.setContentsMargins(0, 0, 0, 0)
        zoom_layout.addWidget(self.zoom_in_button)
        zoom_layout.addWidget(self.zoom_out_button)
        zoom_layout.addWidget(self.zoom_reset_button)
        zoom_layout.addWidget(self.zoom_value_label)
        self.clear_contour_button = QPushButton("等輝度線を解除")
        self.output_label = QLabel("未選択（元画像の隣に保存）")
        self.output_label.setWordWrap(True)
        self.output_button = QPushButton("保存先フォルダーを選択")
        self.save_selected_button = QPushButton("選択画像を保存")
        self.save_all_button = QPushButton("すべて保存")

        form.addRow("カラーマップ", self.cmap_combo)
        form.addRow("補間 (interpolation)", self.interpolation_combo)
        form.addRow("原点 (origin)", self.origin_combo)
        form.addRow("縦横比 (aspect)", self.aspect_combo)
        form.addRow(self.colorbar_check)
        form.addRow("表示下限 (vmin)", self.vmin_spin)
        form.addRow("表示上限 (vmax)", self.vmax_spin)
        form.addRow(self.reset_range_button)
        form.addRow("画像ズーム", zoom_row)
        form.addRow(self.contour_check)
        form.addRow(self.clear_contour_button)
        form.addRow("出力先", self.output_label)
        form.addRow(self.output_button)
        form.addRow(self.save_selected_button, self.save_all_button)
        right_layout.addWidget(controls)
        self.operation_header.toggled.connect(self._toggle_operations)

        self.preview_title = QLabel("画像を選択してください")
        self.preview_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(self.preview_title)
        self.preview_figure = Figure(figsize=(8, 5), tight_layout=True)
        self.preview_axes = self.preview_figure.add_subplot(111)
        self.preview_canvas = FigureCanvasQTAgg(self.preview_figure)
        self.preview_canvas.setMinimumHeight(320)
        self.preview_canvas.mpl_connect("scroll_event", self._on_preview_scroll)
        right_layout.addWidget(self.preview_canvas, 4)

        self.histogram_title = QLabel(
            "画素値ヒストグラム（対数軸） — ドラッグ：表示範囲 / クリック：等輝度線"
        )
        self.histogram_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(self.histogram_title)
        self.histogram_figure = Figure(figsize=(8, 2.5), tight_layout=True)
        self.histogram_axes = self.histogram_figure.add_subplot(111)
        self.histogram_canvas = FigureCanvasQTAgg(self.histogram_figure)
        self.histogram_canvas.setMinimumHeight(210)
        self.histogram_canvas.mpl_connect(
            "motion_notify_event", self._on_histogram_motion
        )
        self.histogram_canvas.mpl_connect(
            "button_press_event", self._on_histogram_press
        )
        self.histogram_canvas.mpl_connect(
            "button_release_event", self._on_histogram_release
        )
        self.histogram_span = SpanSelector(
            self.histogram_axes,
            self._on_histogram_range_selected,
            "horizontal",
            useblit=True,
            props={"alpha": 0.22, "facecolor": "tab:orange"},
            interactive=True,
            drag_from_anywhere=True,
        )
        right_layout.addWidget(self.histogram_canvas, 2)
        self.histogram_value_label = QLabel(
            "ヒストグラム上をドラッグして表示輝度範囲を選択、クリックして等輝度線を指定します。"
        )
        self.histogram_value_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        right_layout.addWidget(self.histogram_value_label)

        self.status_label = QLabel("画像を追加してください。")
        root.addWidget(self.status_label)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 5)

        self.add_button.clicked.connect(self.add_images)
        self.remove_button.clicked.connect(self.remove_selected)
        self.reload_button.clicked.connect(self.reload_selected)
        self.file_list.currentItemChanged.connect(self.update_preview)
        self.cmap_combo.currentTextChanged.connect(self._render_selected_image)
        self.interpolation_combo.currentTextChanged.connect(self._render_selected_image)
        self.origin_combo.currentTextChanged.connect(self._render_selected_image)
        self.aspect_combo.currentTextChanged.connect(self._render_selected_image)
        self.colorbar_check.toggled.connect(self._render_selected_image)
        self.contour_check.toggled.connect(self._render_selected_image)
        self.vmin_spin.valueChanged.connect(self._range_spin_changed)
        self.vmax_spin.valueChanged.connect(self._range_spin_changed)
        self.reset_range_button.clicked.connect(self._reset_display_range)
        self.zoom_in_button.clicked.connect(self._zoom_in)
        self.zoom_out_button.clicked.connect(self._zoom_out)
        self.zoom_reset_button.clicked.connect(self._reset_zoom)
        self.clear_contour_button.clicked.connect(self._clear_contour)
        self.output_button.clicked.connect(self.choose_output_dir)
        self.save_selected_button.clicked.connect(
            lambda: self.save_images(selected_only=True)
        )
        self.save_all_button.clicked.connect(
            lambda: self.save_images(selected_only=False)
        )
        self._clear_histogram()

    def _toggle_operations(self, expanded: bool) -> None:
        """画像オペレーション欄の表示・非表示を切り替える。"""
        self.operations_panel.setVisible(expanded)
        self.operation_header.setArrowType(
            Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow
        )

    def _current_gray(self) -> np.ndarray | None:
        item = self.file_list.currentItem()
        if item is None:
            return None
        path = Path(item.text())
        gray = self.gray_cache.get(path)
        if gray is None:
            gray = load_grayscale(path)
            self.gray_cache[path] = gray
        return gray

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
            self._preview_full_xlim = None
            self._preview_full_ylim = None
            self.zoom_factor = 1.0
            self.zoom_center = None
            self.zoom_value_label.setText("100%")
            self.preview_axes.clear()
            self.preview_canvas.draw_idle()
            self.preview_title.setText("画像を選択してください")
            self._clear_histogram()
        elif self.file_list.currentItem() is not None:
            self.update_preview()
        self.status_label.setText(f"一覧内の画像数: {len(self.paths)}")

    def reload_selected(self) -> None:
        item = self.file_list.currentItem()
        if item is None:
            QMessageBox.information(self, "再読み込み", "画像を選択してください。")
            return
        path = Path(item.text())
        try:
            self.gray_cache[path] = load_grayscale(path)
            self.display_min = self.display_max = None
            self.contour_level = None
            self.zoom_factor = 1.0
            self.zoom_center = None
            self.update_preview()
        except Exception as exc:
            QMessageBox.critical(self, "再読み込みエラー", f"{path}\n{exc}")

    def choose_output_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "保存先フォルダーを選択")
        if directory:
            self.output_dir = Path(directory)
            self.output_label.setText(str(self.output_dir))

    def update_preview(self, *_args) -> None:
        self.display_min = self.display_max = None
        self.contour_level = None
        self.zoom_factor = 1.0
        self.zoom_center = None
        gray = self._current_gray()
        if gray is None:
            return
        finite = gray[np.isfinite(gray)]
        if finite.size:
            self._set_range_controls(float(finite.min()), float(finite.max()))
        self._update_histogram(gray)
        self._render_selected_image()

    def _set_range_controls(self, lower: float, upper: float) -> None:
        if upper <= lower:
            upper = lower + max(abs(lower) * 1e-9, 1e-9)
        self._building_controls = True
        try:
            self.vmin_spin.setValue(lower)
            self.vmax_spin.setValue(upper)
        finally:
            self._building_controls = False

    def _range_spin_changed(self, *_args) -> None:
        if self._building_controls:
            return
        lower, upper = self.vmin_spin.value(), self.vmax_spin.value()
        if upper <= lower:
            return
        self.display_min, self.display_max = lower, upper
        self._render_selected_image()

    def _reset_display_range(self) -> None:
        gray = self._current_gray()
        if gray is None:
            return
        finite = gray[np.isfinite(gray)]
        if finite.size == 0:
            return
        self.display_min = self.display_max = None
        self._set_range_controls(float(finite.min()), float(finite.max()))
        self._render_selected_image()

    def _render_selected_image(self, *_args) -> None:
        gray = self._current_gray()
        item = self.file_list.currentItem()
        if gray is None or item is None:
            return
        finite = gray[np.isfinite(gray)]
        if finite.size == 0:
            return
        vmin = self.display_min
        vmax = self.display_max
        if vmin is None or vmax is None:
            vmin, vmax = float(finite.min()), float(finite.max())
        if vmax <= vmin:
            return

        self.preview_figure.clear()
        self.preview_axes = self.preview_figure.add_subplot(111)
        image = self.preview_axes.imshow(
            gray,
            cmap=self.cmap_combo.currentText(),
            vmin=vmin,
            vmax=vmax,
            interpolation=self.interpolation_combo.currentText(),
            origin=self.origin_combo.currentText(),
            aspect=self.aspect_combo.currentText(),
        )
        image_xlim = self.preview_axes.get_xlim()
        image_ylim = self.preview_axes.get_ylim()
        self._preview_full_xlim = (float(image_xlim[0]), float(image_xlim[1]))
        self._preview_full_ylim = (float(image_ylim[0]), float(image_ylim[1]))
        if self.contour_check.isChecked() and self.contour_level is not None:
            if float(finite.min()) < self.contour_level < float(finite.max()):
                self.preview_axes.contour(
                    gray,
                    levels=[self.contour_level],
                    colors=["red"],
                    linewidths=0.8,
                    origin=self.origin_combo.currentText(),
                )
        self.preview_axes.set_title(item.text())
        self.preview_axes.set_xlabel("X (pixel)")
        self.preview_axes.set_ylabel("Y (pixel)")
        if self.colorbar_check.isChecked():
            self.preview_figure.colorbar(image, ax=self.preview_axes, label="Intensity")
        self._apply_preview_zoom()
        self.preview_canvas.draw_idle()
        self.preview_title.setText(
            f"{Path(item.text()).name} | {gray.shape[1]} × {gray.shape[0]} px | "
            f"vmin={vmin:.6g} / vmax={vmax:.6g}"
            + (
                f" | 等輝度線={self.contour_level:.6g}"
                if self.contour_level is not None
                else ""
            )
        )
        self.status_label.setText(f"プレビュー中: {Path(item.text()).name}")

    def _zoom_in(self) -> None:
        """表示倍率を上げる。"""
        self.zoom_factor = min(self.zoom_factor * 1.25, 32.0)
        self._apply_preview_zoom()

    def _zoom_out(self) -> None:
        """表示倍率を下げる。"""
        self.zoom_factor = max(self.zoom_factor / 1.25, 1.0)
        if self.zoom_factor == 1.0:
            self.zoom_center = None
        self._apply_preview_zoom()

    def _reset_zoom(self) -> None:
        """画像全体が収まる表示倍率に戻す。"""
        self.zoom_factor = 1.0
        self.zoom_center = None
        self._apply_preview_zoom()

    def _on_preview_scroll(self, event) -> None:
        """マウスホイールでカーソル位置を中心に拡大・縮小する。"""
        if (
            event.inaxes is not self.preview_axes
            or event.xdata is None
            or event.ydata is None
        ):
            return
        if event.button == "up":
            self.zoom_factor = min(self.zoom_factor * 1.2, 32.0)
        elif event.button == "down":
            self.zoom_factor = max(self.zoom_factor / 1.2, 1.0)
        else:
            return
        self.zoom_center = (float(event.xdata), float(event.ydata))
        if self.zoom_factor == 1.0:
            self.zoom_center = None
        self._apply_preview_zoom()

    def _apply_preview_zoom(self) -> None:
        """画像の全体範囲と倍率から表示領域を設定する。"""
        if self._preview_full_xlim is None or self._preview_full_ylim is None:
            return

        x_start, x_end = self._preview_full_xlim
        y_start, y_end = self._preview_full_ylim
        x_lower, x_upper = min(x_start, x_end), max(x_start, x_end)
        y_lower, y_upper = min(y_start, y_end), max(y_start, y_end)
        if self.zoom_center is None:
            center_x = (x_lower + x_upper) / 2
            center_y = (y_lower + y_upper) / 2
        else:
            center_x, center_y = self.zoom_center

        half_width = (x_upper - x_lower) / (2 * self.zoom_factor)
        half_height = (y_upper - y_lower) / (2 * self.zoom_factor)
        center_x = min(max(center_x, x_lower + half_width), x_upper - half_width)
        center_y = min(max(center_y, y_lower + half_height), y_upper - half_height)

        if x_start <= x_end:
            self.preview_axes.set_xlim(
                center_x - half_width, center_x + half_width
            )
        else:
            self.preview_axes.set_xlim(
                center_x + half_width, center_x - half_width
            )
        if y_start <= y_end:
            self.preview_axes.set_ylim(
                center_y - half_height, center_y + half_height
            )
        else:
            self.preview_axes.set_ylim(
                center_y + half_height, center_y - half_height
            )

        self.zoom_value_label.setText(f"{self.zoom_factor * 100:.0f}%")
        self.preview_canvas.draw_idle()

    def _update_histogram(self, gray: np.ndarray) -> None:
        values = np.asarray(gray).reshape(-1)
        values = values[np.isfinite(values)]
        if self.histogram_span is not None:
            self.histogram_span.disconnect_events()
        self.histogram_axes.clear()
        self.histogram_contour_line = None
        self.histogram_cursor_line = None
        self.histogram_span = SpanSelector(
            self.histogram_axes,
            self._on_histogram_range_selected,
            "horizontal",
            useblit=True,
            props={"alpha": 0.22, "facecolor": "tab:orange"},
            interactive=True,
            drag_from_anywhere=True,
        )
        self.histogram_edges = None
        self.histogram_counts = None
        if values.size == 0:
            self.histogram_axes.set_title("No finite pixel values")
            self.histogram_canvas.draw_idle()
            return
        minimum, maximum = float(values.min()), float(values.max())
        if maximum == minimum:
            padding = max(abs(minimum) * 1e-6, 0.5)
            histogram_range = (minimum - padding, maximum + padding)
        else:
            histogram_range = (minimum, maximum)
        counts, edges = np.histogram(values, bins=256, range=histogram_range)
        centers = (edges[:-1] + edges[1:]) / 2
        nonzero = counts > 0
        self.histogram_axes.bar(
            centers[nonzero],
            counts[nonzero],
            width=np.diff(edges)[nonzero],
            align="center",
            linewidth=0,
        )
        self.histogram_axes.set_yscale("log")
        self.histogram_axes.set_xlabel("Pixel value")
        self.histogram_axes.set_ylabel("Pixel count (log)")
        self.histogram_axes.grid(True, axis="y", alpha=0.25)
        self.histogram_axes.set_xlim(edges[0], edges[-1])
        self.histogram_edges, self.histogram_counts = edges, counts
        self.histogram_cursor_line = self.histogram_axes.axvline(
            centers[0], visible=False, linewidth=1, color="tab:orange"
        )
        self._draw_histogram_contour_level()
        self.histogram_canvas.draw_idle()
        self.histogram_value_label.setText(
            f"値の範囲: {minimum:.6g} ～ {maximum:.6g} | 画素数: {values.size:,}"
        )

    def _draw_histogram_contour_level(self) -> None:
        """選択中の等輝度線レベルをヒストグラム上に表示する。"""
        legend = self.histogram_axes.get_legend()
        if legend is not None:
            legend.remove()
        if self.histogram_contour_line is not None:
            try:
                self.histogram_contour_line.remove()
            except ValueError:
                pass
            self.histogram_contour_line = None

        if self.contour_level is None or self.histogram_edges is None:
            return
        lower, upper = float(self.histogram_edges[0]), float(self.histogram_edges[-1])
        if not lower <= self.contour_level <= upper:
            return
        self.histogram_contour_line = self.histogram_axes.axvline(
            self.contour_level,
            color="tab:red",
            linestyle="--",
            linewidth=1.6,
            label=f"等輝度線: {self.contour_level:.6g}",
            zorder=5,
        )
        self.histogram_axes.legend(loc="upper right", fontsize="small")

    def _on_histogram_motion(self, event) -> None:
        if (
            event.inaxes is not self.histogram_axes
            or event.xdata is None
            or self.histogram_edges is None
            or self.histogram_counts is None
        ):
            return
        index = int(np.searchsorted(self.histogram_edges, event.xdata, side="right") - 1)
        index = min(max(index, 0), len(self.histogram_counts) - 1)
        lower, upper = self.histogram_edges[index : index + 2]
        count = int(self.histogram_counts[index])
        if self.histogram_cursor_line is not None:
            self.histogram_cursor_line.set_xdata([event.xdata, event.xdata])
            self.histogram_cursor_line.set_visible(True)
        self.histogram_value_label.setText(
            f"カーソル値: {event.xdata:.8g} | 階級: [{lower:.8g}, {upper:.8g}) "
            f"| 画素数: {count:,}"
        )
        self.histogram_canvas.draw_idle()

    def _on_histogram_range_selected(self, xmin: float, xmax: float) -> None:
        if xmax <= xmin:
            return
        self.display_min, self.display_max = float(xmin), float(xmax)
        self._set_range_controls(self.display_min, self.display_max)
        self._render_selected_image()
        self.histogram_value_label.setText(
            f"表示輝度範囲を設定: {self.display_min:.8g} ～ {self.display_max:.8g}"
        )

    def _on_histogram_press(self, event) -> None:
        if (
            event.inaxes is self.histogram_axes
            and event.x is not None
            and event.button == 1
        ):
            self._histogram_press_x = float(event.x)

    def _on_histogram_release(self, event) -> None:
        if (
            self._histogram_press_x is None
            or event.inaxes is not self.histogram_axes
            or event.x is None
            or event.xdata is None
            or event.button != 1
            or self.histogram_edges is None
        ):
            self._histogram_press_x = None
            return
        pixel_distance = abs(float(event.x) - self._histogram_press_x)
        self._histogram_press_x = None
        # ドラッグ操作は SpanSelector が処理するため、短いクリックのみ等輝度線にする。
        if pixel_distance > 4:
            return
        self.contour_level = float(event.xdata)
        self._draw_histogram_contour_level()
        self.histogram_canvas.draw_idle()
        self._render_selected_image()
        self.histogram_value_label.setText(
            f"等輝度線を設定: {self.contour_level:.8g}"
        )

    def _clear_contour(self) -> None:
        self.contour_level = None
        self._draw_histogram_contour_level()
        self.histogram_canvas.draw_idle()
        self._render_selected_image()

    def _clear_histogram(self) -> None:
        if self.histogram_span is not None:
            self.histogram_span.disconnect_events()
            self.histogram_span = None
        self.histogram_axes.clear()
        self.histogram_contour_line = None
        self.histogram_cursor_line = None
        self.histogram_axes.set_title("Pixel histogram")
        self.histogram_edges = None
        self.histogram_counts = None
        self.histogram_cursor_line = None
        self.histogram_canvas.draw_idle()
        self.histogram_value_label.setText(
            "ヒストグラムをドラッグして輝度範囲を選択、クリックして等輝度線を指定します。"
        )

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if hasattr(self, "preview_canvas"):
            self.preview_canvas.draw_idle()

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
                lower = self.display_min
                upper = self.display_max
                current_item = self.file_list.currentItem()
                if current_item is None or path != Path(current_item.text()):
                    lower = upper = None
                finite = gray[np.isfinite(gray)]
                vmin = lower if lower is not None else float(finite.min())
                vmax = upper if upper is not None else float(finite.max())
                normalized = np.clip((gray.astype(float) - vmin) / (vmax - vmin), 0, 1)
                from matplotlib import colormaps
                rgb = np.rint(colormaps[cmap_name](normalized)[..., :3] * 255).astype(np.uint8)
                from PIL import Image
                output_dir = self.output_dir or path.parent
                output_dir.mkdir(parents=True, exist_ok=True)
                destination = output_dir / f"{path.stem}_{cmap_name}.png"
                Image.fromarray(rgb, mode="RGB").save(destination, format="PNG")
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
