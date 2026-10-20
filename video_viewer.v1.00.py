import cv2
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button
from matplotlib.animation import FuncAnimation
import tkinter as tk
from tkinter import filedialog
import os
import sys

version=1.00

def main():
    # 1. GUIによる動画選択 (tkinterを使用)
    root = tk.Tk()
    root.withdraw() # メインウィンドウを隠す
    # 最前面に表示してフォーカスを当てる
    root.attributes('-topmost', True) 
    
    file_path = filedialog.askopenfilename(
        title="再生する動画ファイルを選択してください",
        filetypes=[("Video files", "*.mp4 *.avi *.mov *.mkv"), ("All files", "*.*")]
    )
    root.destroy()

    if not file_path:
        print("動画が選択されませんでした。終了します。")
        sys.exit()

    # 動画の読み込み設定
    cap = cv2.VideoCapture(file_path)
    if not cap.isOpened():
        print("動画の読み込みに失敗しました。")
        sys.exit()

    # 動画情報の取得
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps == 0 or fps != fps: # fpsが取得できない場合のフェールセーフ
        fps = 30.0 

    # 5. currentの動画名, pathの取得
    file_name = os.path.basename(file_path)

    # MatplotlibのFigureとAxesの初期化
    fig, ax = plt.subplots(figsize=(10, 8))
    # ウィジェットとテキストを表示するための余白を確保
    plt.subplots_adjust(bottom=0.35, top=0.85) 

    # 動画名とパスの表示
    fig.text(0.5, 0.94, f"Name: {file_name}", ha='center', va='center', fontsize=14, fontweight='bold')
    # パスが長すぎる場合ははみ出さないようにフォントサイズを小さくする
    fig.text(0.5, 0.89, f"Path: {file_path}", ha='center', va='center', fontsize=9, color='gray')

    # 初期フレーム（0フレーム目）の取得と表示
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    ret, frame = cap.read()
    if ret:
        # OpenCVのBGRをMatplotlib用のRGBに変換
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img_display = ax.imshow(frame)
    ax.axis('off')

    # 再生状態を管理する辞書
    state = {
        'playing': True,
        'frame_idx': 0.0 # 0.25刻みなどの速度に対応するためfloat型で管理
    }

    # ================= ウィジェットの配置 =================
    
    # 4. 再生位置調整スライダー
    ax_pos = plt.axes([0.15, 0.2, 0.7, 0.03])
    pos_slider = Slider(ax_pos, 'Position', 0, total_frames - 1, valinit=0, valstep=1)

    # 3. 再生速度制御スライダー (-8.0 ~ 8.0, 0.25刻み)
    ax_speed = plt.axes([0.15, 0.12, 0.7, 0.03])
    speed_slider = Slider(ax_speed, 'Speed', -8.0, 8.0, valinit=1.0, valstep=0.25)

    # 2. 再生、停止機能ボタン
    ax_play = plt.axes([0.45, 0.02, 0.1, 0.06])
    btn_play = Button(ax_play, 'Pause')

    # ================= イベントハンドラ =================

    def toggle_play(event):
        """再生/停止ボタンが押された時の処理"""
        state['playing'] = not state['playing']
        btn_play.label.set_text('Pause' if state['playing'] else 'Play')
        fig.canvas.draw_idle()

    btn_play.on_clicked(toggle_play)

    def on_pos_changed(val):
        """再生位置スライダーがユーザーによって動かされた時の処理"""
        if not pos_slider.eventson: 
            return # アニメーションループからの自動更新時は無視する
        
        state['frame_idx'] = val
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(val))
        ret, fr = cap.read()
        if ret:
            img_display.set_data(cv2.cvtColor(fr, cv2.COLOR_BGR2RGB))
            fig.canvas.draw_idle()

    pos_slider.on_changed(on_pos_changed)

    def update(frame_count):
        """アニメーションの毎フレーム更新処理"""
        if state['playing']:
            speed = speed_slider.val
            state['frame_idx'] += speed
            
            # 動画の最初・最後に来た時の範囲外処理（停止させる）
            if state['frame_idx'] <= 0:
                state['frame_idx'] = 0
                state['playing'] = False
                btn_play.label.set_text('Play')
            elif state['frame_idx'] >= total_frames - 1:
                state['frame_idx'] = total_frames - 1
                state['playing'] = False
                btn_play.label.set_text('Play')
                
            # スライダーの見た目だけを更新 (無限ループを防ぐためeventsonを一時的にFalseにする)
            pos_slider.eventson = False
            pos_slider.set_val(state['frame_idx'])
            pos_slider.eventson = True
            
            # OpenCVで指定フレームにシークして読み込む
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(state['frame_idx']))
            ret, fr = cap.read()
            if ret:
                img_display.set_data(cv2.cvtColor(fr, cv2.COLOR_BGR2RGB))
                
        return [img_display]

    # ウィンドウが閉じられた時のメモリ解放処理
    def on_close(event):
        cap.release()

    fig.canvas.mpl_connect('close_event', on_close)

    # アニメーションの実行 (実際の動画のFPSに合わせてインターバルを設定)
    interval_ms = 1000 / fps
    ani = FuncAnimation(fig, update, interval=interval_ms, blit=False, cache_frame_data=False)

    # プレイヤーの表示
    plt.show()

if __name__ == "__main__":
    main()