from tkinter.filedialog import askopenfilename

import cv2
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

sun_image = askopenfilename()
smoothing = False

# 画像の読み込み（グレースケール）
img = cv2.imread(sun_image, cv2.IMREAD_GRAYSCALE)
if smoothing:
    blurred = cv2.GaussianBlur(img, (5, 5), 0)
else:
    blurred = img


# グリッドの作成
X, Y = np.meshgrid(np.arange(img.shape[1]), np.arange(img.shape[0]))

# ★ 色を付けたい明るさ（輝度値）
target_level = 800  # ← 好きな値に変更
target_color = "red"  # ← 好きな色に変更

step= 20
level = list(range(0,255,step))


# 等高線の描画（通常）
plt.figure(figsize=(8, 8))
plt.imshow(img, cmap="gray", origin="upper")
contour = plt.contour(X, Y, blurred, levels=level, colors="skyblue", linewidths=0.5)
plt.clabel(contour, inline=True, fontsize=8, fmt="%1.0f")

""""""  # ★ 特定の明るさの等高線を色付きで追加描画
plt.contour(X, Y, blurred, levels=[target_level], colors=target_color, linewidths=2)
""""""

plt.contour(X, Y, blurred, levels=[3816], colors="magenta", linewidths=2)

plt.contour(X, Y, blurred, levels=[1136], colors="green", linewidths=2)

plt.title(f"sun isophoto step={step}")
plt.axis("off")
plt.show()
