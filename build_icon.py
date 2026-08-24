"""生成复古便携游戏机 APP 图标（黑红配色，无任何文字）。

使用 RGBA + 透明背景，macOS Launchpad/Dock 会自动套上圆角遮罩。
"""
from PIL import Image, ImageDraw
from pathlib import Path

# 一代宗师配色（与 todo_app.py 一致）
BLACK      = (14, 10, 6, 255)      # #0e0a06  深褐黑
SHELL_DK   = (58, 46, 28, 255)     # #3a2e1c  老木头褐
RED        = (160, 72, 50, 255)    # #a04832  旗袍旧红
RED_DK     = (90, 40, 24, 255)     # #5a2818  暗红
RED_HI     = (200, 100, 70, 255)   # 旧红高光（仍偏暖）
WHITE      = (216, 192, 152, 255)  # #d8c098  奶白（黄铜灯下）
DIM        = (138, 120, 88, 255)   # #8a7858  灰褐
BG_BLACK  = (0, 0, 0, 255)  # 整体底色：纯黑
SHELL     = (140, 110, 70, 255)  # 黄铜金（顶部高光）

SIZE = 1024
img = Image.new("RGBA", (SIZE, SIZE), BG_BLACK)
d = ImageDraw.Draw(img)

W, H = 780, 920
y0 = (SIZE - H) // 2
x0 = (SIZE - W) // 2

r = 50
def rr(x1, y1, x2, y2, r, fill, outline=None, width=1):
    d.rectangle([x1+r, y1, x2-r, y2], fill=fill)
    d.rectangle([x1, y1+r, x2, y2-r], fill=fill)
    d.ellipse([x1, y1, x1+2*r, y1+2*r], fill=fill)
    d.ellipse([x2-2*r, y1, x2, y1+2*r], fill=fill)
    d.ellipse([x1, y2-2*r, x1+2*r, y2], fill=fill)
    d.ellipse([x2-2*r, y2-2*r, x2, y2], fill=fill)
    if outline:
        d.arc([x1, y1, x1+2*r, y1+2*r], 180, 270, fill=outline, width=width)
        d.arc([x2-2*r, y1, x2, y1+2*r], 270, 360, fill=outline, width=width)
        d.arc([x1, y2-2*r, x1+2*r, y2], 90, 180, fill=outline, width=width)
        d.arc([x2-2*r, y2-2*r, x2, y2], 0, 90, fill=outline, width=width)
        d.line([x1+r, y1, x2-r, y1], fill=outline, width=width)
        d.line([x1+r, y2, x2-r, y2], fill=outline, width=width)
        d.line([x1, y1+r, x1, y2-r], fill=outline, width=width)
        d.line([x2, y1+r, x2, y2-r], fill=outline, width=width)

# 外壳（黑色塑料）
rr(x0, y0, x0+W, y0+H, r, SHELL_DK, outline=WHITE, width=12)  # 深灰外壳 + 更粗白色描边
# 顶部高光
d.rectangle([x0+30, y0+18, x0+W-30, y0+30], fill=SHELL)  # 顶部亮条：区分上下两区

# LCD 屏幕区
scr_x1 = x0 + 80
scr_x2 = x0 + W - 80
scr_y1 = y0 + 60
scr_y2 = y0 + 460

# 红色边框 + 黑色屏幕
rr(scr_x1-25, scr_y1-25, scr_x2+25, scr_y2+25, 18, RED)
rr(scr_x1, scr_y1, scr_x2, scr_y2, 8, BLACK)

# — 屏幕内容（无任何文字）—

# 左侧：大红色勾选框 + 黑对勾
box_size = 180
box_x = scr_x1 + 60
box_y = scr_y1 + 100
d.rectangle([box_x, box_y, box_box_size, box_y+box_size], fill=RED) if False else d.rectangle([box_x, box_y, box_x+box_size, box_y+box_size], fill=RED)
d.line([box_x+40, box_y+95, box_x+80, box_y+135], fill=BLACK, width=24)
d.line([box_x+80, box_y+135, box_x+145, box_y+45], fill=BLACK, width=24)

# 右侧：3 条任务横线（无文字，纯几何）
list_x1 = box_x + box_size + 80
list_x2 = scr_x2 - 60
line_y_start = box_y + 20
for i in range(3):
        ly = line_y_start + i * 70
        d.rectangle([list_x1, ly, list_x1+40, ly+40], outline=RED, width=5)
        d.line([list_x1+70, ly+20, list_x2, ly+20], fill=RED, width=12)

# D-Pad
pad_cx = x0 + 200
pad_cy = y0 + 620
arm, thick = 70, 60
d.rectangle([pad_cx-arm-thick//2, pad_cy-thick//2, pad_cx+arm+thick//2, pad_cy+thick//2], fill=SHELL_DK, outline=RED, width=3)
d.rectangle([pad_cx-thick//2, pad_cy-arm-thick//2, pad_cx+thick//2, pad_cy+arm+thick//2], fill=SHELL_DK, outline=RED, width=3)
d.rectangle([pad_cx-thick//2, pad_cy-thick//2, pad_cx+thick//2, pad_cy+thick//2], fill=RED)

# SELECT / START 椭圆
for cy in [y0 + 540, y0 + 600]:
    d.ellipse([x0+390, cy-15, x0+490, cy+15], fill=SHELL_DK, outline=RED, width=3)

# A / B 圆按钮
for (cx, cy) in [(x0+620, y0+540), (x0+560, y0+620)]:
    d.ellipse([cx-50, cy-50, cx+50, cy+50], fill=RED, outline=RED_DK, width=4)
    d.ellipse([cx-32, cy-32, cx+10, cy+10], fill=RED_HI)

# 底部装饰条
d.rectangle([x0+40, y0+H-60, x0+W-40, y0+H-30], fill=SHELL_DK, outline=RED, width=2)

out = Path(__file__).parent / "icon.png"
img.save(out, "PNG")
print(f"saved: {out}")
print(f"  mode={img.mode} size={img.size}")
