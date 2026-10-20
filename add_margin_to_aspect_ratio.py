import os
from PIL import Image
from tkinter.filedialog import askopenfile, asksaveasfile


import os
from PIL import Image

def add_margin_to_aspect_ratio(input_path, output_path, target_w=1, target_h=1, bg_color=(0, 0, 0, 0)):
    """
    日本語パスに対応し、指定の縦横比に余白（透過対応）を追加する関数
    
    :param input_path: 入力ファイルパス
    :param output_path: 出力ファイルパス
    :param target_w: 比率の幅（例: 1）
    :param target_h: 比率の高さ（例: 1）
    :param bg_color: 余白の色 (R, G, B, A) デフォルトは完全透明
    """
    try:
        # 日本語パスでの文字化けエラーを避けるためバイナリモードで読み込み
        with open(input_path, 'rb') as f:
            img = Image.open(f)
            img.load()  # 画像データをメモリに展開

        # 透過情報を保持するため RGBA モードに統一
        if img.mode != 'RGBA':
            img = img.convert('RGBA')

        w, h = img.size

        # アスペクト比を元に新しいキャンバスサイズを計算
        if w * target_h > h * target_w:
            new_w = w
            new_h = int(w * target_h / target_w)
        else:
            new_h = h
            new_w = int(h * target_w / target_h)

        # 透過（RGBA）対応の新しいキャンバスを作成
        new_img = Image.new('RGBA', (new_w, new_h), bg_color)

        # 画像を中央に配置（第3引数にimgを渡すことで透過マスクを維持）
        offset_x = (new_w - w) // 2
        offset_y = (new_h - h) // 2
        new_img.paste(img, (offset_x, offset_y), img)

        # PNGとして保存
        new_img.save(output_path, format='PNG')
        print(f"成功: [{output_path}] を作成しました ({new_w}x{new_h}px)")

    except FileNotFoundError:
        print(f"エラー: 指定されたファイルが見つかりません: {input_path}")
    except Exception as e:
        print(f"エラーが発生しました: {e}")

# ==========================================
# 実行処理
# ==========================================

if __name__ == "__main__":
    # 例: "input.jpg" を 16:9 の比率にし、余白を黒(0,0,0)にして "output.jpg" として保存
    input_file = r"C:\Users\fujit\Downloads\天文ロゴ 黒.png"  # 変換したい画像の名前
    output_file = r"C:\Users\fujit\Downloads\天文ロゴ 黒_マージン.png"  # 保存する画像の名前

    add_margin_to_aspect_ratio(
        input_file,
        output_file,
        target_w=1,
        target_h=1,
        bg_color=(0, 0, 0, 0),  # 黒の余白
    )
