import glob
import os
import shutil
import sys
from tkinter import filedialog as fd

import ffmpeg
import tqdm

"""
a1=sys.argv[1]
a2=int(sys.argv[2])
"""
a1=fd.askdirectory(title="動画が入っているフォルダを選択してください")
a2=-1
dir = a1
a=False
#↑動画がはいってぅふぉるだ
save_dir = a1
#↑画像を保存するフォルダ


in_files = []
for pattern in ("*.ser", "*.avi", "*.mp4"):
    in_files.extend(glob.glob(os.path.join(dir, pattern)))

if not in_files:
    if a:
        in_files=[dir]
        save_dir= save_dir+ "\\"+dir.split("\\")[a2]+ "\\"
        
    else:
        print("SERファイルが見つかりませんでした。")
save_dir= save_dir+ "\\"+dir.split("/")[a2]+ "\\"
for file_path in tqdm.tqdm(in_files):
    file_name = os.path.splitext(os.path.basename(file_path))[0]
    out_dir = os.path.join(save_dir , file_name)
    print(f"処理中: {file_name}")
    if os.path.abspath(out_dir) == os.path.abspath(dir):
        print("⚠️ testフォルダを削除しようとしています！中止します。")
        continue  # または raise Exception
    if os.path.isdir(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(out_dir)
    (
        ffmpeg
            .input(file_path)
            .output(os.path.join(out_dir, "img%08d.tiff"))
            .run()
    )
    
print(save_dir)
print(in_files)