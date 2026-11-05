"""画像一覧・プレビュー・一括保存を備えたメインウィンドウ。"""
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QListWidget, QLabel, QPushButton, QComboBox,
    QFileDialog, QMessageBox, QHBoxLayout, QVBoxLayout, QSplitter,
    QGroupBox, QFormLayout, QProgressDialog, QCheckBox
)
import numpy as np
from PIL import Image

from src.utils import load_grayscale, apply_colormap, available_colormaps


IMAGE_FILTER = (
    "画像ファイル (*.png *.jpg *.jpeg *.tif *.tiff *.bmp *.webp *.gif);;"
    "すべてのファイル (*)"
)


class MainWindow(QMainWindow):
    """Gray Colormap Studio のメイン画面。"""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Gray Colormap Studio")
        self.resize(1120, 720)
        self.paths: list[Path] = []
        self.gray_cache: dict[Path, np.ndarray] = {}
        self.output_dir: Path | None = None
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
        self.preview.setMinimumSize(400, 300)
        self.preview.setStyleSheet("QLabel { background: #20242b; color: #d8dce2; border: 1px solid #505761; }")
        self.preview.setScaledContents(False)
        right_layout.addWidget(self.preview_title)
        right_layout.addWidget(self.preview, 1)
        self.status_label = QLabel("画像を追加してください。")
        root.addWidget(self.status_label)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)

        self.add_button.clicked.connect(self.add_images)
        self.remove_button.clicked.connect(self.remove_selected)
        self.reload_button.clicked.connect(self.reload_selected)
        self.file_list.currentItemChanged.connect(self.update_preview)
        self.cmap_combo.currentTextChanged.connect(self._colormap_changed)
        self.output_button.clicked.connect(self.choose_output_dir)
        self.save_selected_button.clicked.connect(lambda: self.save_images(selected_only=True))
        self.save_all_button.clicked.connect(lambda: self.save_images(selected_only=False))

    def add_images(self) -> None:
        names, _ = QFileDialog.getOpenFileNames(self, "グレースケール画像を選択", "", IMAGE_FILTER)
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
        self.status_label.setText(f"{added} 件の画像を追加しました。合計 {len(self.paths)} 件。")
        if self.file_list.count() and self.file_list.currentRow() < 0:
            self.file_list.setCurrentRow(0)
        if failures:
            QMessageBox.warning(self, "読み込みエラー", "\n".join(failures[:15]))

    def remove_selected(self) -> None:
        rows = sorted({self.file_list.row(item) for item in self.file_list.selectedItems()}, reverse=True)
        for row in rows:
            path = self.paths.pop(row)
            self.gray_cache.pop(path, None)
            self.file_list.takeItem(row)
        if not self.paths:
            self.preview.clear()
            self.preview.setText("プレビュー")
            self.preview_title.setText("画像を選択してください")
        self.status_label.setText(f"一覧内の画像数: {len(self.paths)}")

    def reload_selected(self) -> None:
        item = self.file_list.currentItem()
        if item is None:
            QMessageBox.information(self, "再読み込み", "再読み込みする画像を選択してください。")
            return
        path = Path(item.text())
        try:
            self.gray_cache[path] = load_grayscale(path)
            self.update_preview()
            self.status_label.setText(f"再読み込みしました: {path.name}")
        except Exception as exc:
            QMessageBox.critical(self, "再読み込みエラー", f"{path}\n{exc}")

    def choose_output_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "保存先フォルダーを選択")
        if directory:
            self.output_dir = Path(directory)
            self.output_label.setText(str(self.output_dir))

    def _colormap_changed(self, _name: str) -> None:
        if self.auto_preview.isChecked():
            self.update_preview()

    def update_preview(self, *_args) -> None:
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
                f"{path.name}  |  {gray.shape[1]} × {gray.shape[0]} px  |  {self.cmap_combo.currentText()}"
            )
            self.status_label.setText(f"プレビュー中: {path.name}")
        except Exception as exc:
            QMessageBox.critical(self, "プレビューエラー", str(exc))

    def _show_image(self, image: Image.Image) -> None:
        rgb = np.asarray(image.convert("RGB"))
        height, width, _ = rgb.shape
        qimage = QImage(rgb.data, width, height, 3 * width, QImage.Format.Format_RGB888).copy()
        pixmap = QPixmap.fromImage(qimage)
        self.preview.setPixmap(pixmap.scaled(
            self.preview.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        ))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.update_preview()

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
        progress = QProgressDialog("画像を変換して保存しています…", "キャンセル", 0, len(targets), self)
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
        QMessageBox.warning(self, "保存結果", message) if failures else QMessageBox.information(self, "保存結果", message)
