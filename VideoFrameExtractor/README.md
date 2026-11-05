# VideoFrameExtractor

SER / AVI 動画から指定したフレームを TIFF として一括抽出する Python ツールです。

## 特徴

- JSON 1ファイルに複数の抽出タスクを定義
- SER の 8bit / 9〜16bit（16bitワード格納）、Mono / Bayer / RGB / BGR を読み込み
- AVI は PyAV でデコード（8bitに加え、10/12/14/16bit系の高ビット深度をRGB48またはGray16で保持）
- TIFF は非圧縮で保存（画素データを再圧縮しない）
- 保存前に一時ファイルへ書き込み、形状・データ型を検証してから移動
- タスク単位でエラーを記録し、後続タスクを継続
- `logs/` に実行ログ、`temp/` に一時ファイルを配置

## セットアップ

Python 3.10 以上を推奨します。

```bash
python -m venv .venv
# Windows
.venv\\Scripts\\activate
# macOS / Linux
source .venv/bin/activate

python -m pip install -r requirements.txt
```

## 実行

```bash
python run.py
```

引数なしで起動するとJSONファイル選択ダイアログが表示されます。JSONを選択すると抽出を開始し、キャンセルすると何も抽出せず終了します。

指示ファイルを指定する場合：

```bash
python run.py --input instructions/example.json
```

## JSON形式

`tasks` 配列の各要素が1枚の抽出指示です。

```json
{
  "tasks": [
    {
      "source": "videos/sample.ser",
      "format": "ser",
      "frame": 120,
      "output_dir": "output/ser",
      "filename": "sample_00120.tiff"
    },
    {
      "source": "videos/sample.avi",
      "format": "avi",
      "frame": 250,
      "output_dir": "output/avi",
      "filename": "sample_00250.tif"
    }
  ]
}
```

| 項目 | 説明 |
|---|---|
| `source` | 入力動画のパス。絶対パスを推奨。相対パスはプロジェクトルート基準 |
| `format` | `ser` または `avi`。省略時は拡張子から判定 |
| `frame` | 抽出するフレーム番号（0始まり） |
| `output_dir` | 保存先ディレクトリ。相対パスはプロジェクトルート基準 |
| `filename` | 出力ファイル名（`.tif` / `.tiff`） |
| `ser_endian_mode` | SERのバイト順。省略時は`config.json`の値を使用（`legacy` / `spec` / `little` / `big`） |

## 品質・データ保持について

- SERは格納されたサンプル値を配列化し、TIFFへ保存します。16bitワードの値を8bitに縮小したり、0〜255へクリップしたりしません。PixelDepthPerPlaneが9〜16の場合も、2バイト/サンプルとして読み込みます。
- SERの`LittleEndian`ヘッダーフラグには、仕様書どおりの解釈と、天文ソフトで広く使われる逆の解釈が存在します。本ツールの既定値`legacy`は、Siril / SER Player等で使われる方式（フラグ0=Little Endian、1=Big Endian）です。これは前回版が採用していた解釈と逆です。
- AVIは復号後の16bitグレースケールを`uint16`、高ビット深度のYUV/RGBをRGB48（`uint16`の3チャンネル）として保存します。8bit形式は8bitのまま保存します。
- AVI はコーデックで復号されたフレームを保存します。AVI自体が非可逆圧縮の場合、元の撮像データを復元することはできませんが、このツールでは復号後に追加のJPEG等の非可逆圧縮を行いません。
- AVIは動画コーデックやピクセル形式によって、PyAV/FFmpegによる色形式変換が必要になる場合があります。元AVIの圧縮パケットをTIFFに変換することはできません。
- Bayerデータはデモザイクせず、元の1チャンネル画素配列として保存します。TIFFだけではBayer配列の色配列情報を完全に表現できないため、元のColorIDはログに記録します。
- TIFFは既定で非圧縮です。

### SERバイト順の設定

`config.json`の`ser_endian_mode`で既定値を変更できます。

- `legacy`（既定）: 天文ソフトで一般的な解釈。フラグ0=Little Endian、1=Big Endian。
- `spec`: SER仕様書のフィールド名どおりの解釈。フラグ1=Little Endian、0=Big Endian。
- `little` / `big`: ヘッダー値を無視してバイト順を固定。

特定タスクだけ変更する場合は、そのタスクに`"ser_endian_mode": "spec"`のように指定できます。読み込み時のバイト順とフレームごとの`min` / `max`はログに出力されます。

既定では既存ファイルを上書きしません。許可する場合は`config.json`の`overwrite`を`true`にします。

## ログ・一時ファイル

- `logs/extractor.log`: 実行履歴、成功・失敗、例外情報
- `temp/`: TIFFの一時書き出し先。正常処理後は一時ファイルを削除します。

## テスト

```bash
python -m unittest discover -s tests -v
```

SERのデファクト/仕様準拠バイト順、16bit Mono / RGB、12bitサンプル、強制バイト順、TIFF保存後の全画素値、およびAVIのGray16 / YUV10bit→RGB48変換を回帰テストします。

## 制限事項

SERの仕様外ヘッダー、未対応ColorID、AVIの未対応コーデックなどはエラーとしてログに記録します。処理失敗時は該当タスクをスキップし、次のタスクを続行します。
