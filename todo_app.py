"""桌面 Todo 清单 —— NES 复古游戏机风格。
运行：python3 todo_app.py
数据：./todos.json
"""
import json
import tkinter as tk
from tkinter import ttk
from datetime import datetime
from pathlib import Path

DATA_FILE = Path(__file__).parent / "todos.json"

# — 一代宗师配色（民国旧宅 / 老木头褐 / 旗袍旧红 / 黄铜灯）—
BLACK      = "#0e0a06"   # 外壳（窗框阴影，深褐黑）
PANEL      = "#1a1208"   # 屏幕区（深褐，年代感）
LINE       = "#3a2e1c"   # 分隔线 / 行底（老木头褐）
RED        = "#a04832"   # 主色（旗袍旧红，褪色感）
RED_DK     = "#5a2818"   # 暗红（按下 / 阴影）
GOLD       = "#a08858"   # 黄铜金（描边 / 标题）
WHITE      = "#d8c098"   # 主文字（黄铜灯下奶白）
DIM        = "#8a7858"   # 次要文字（灰褐）
SEL        = "#3a2818"   # 选中行底色（旧木底）

FONT       = ("Menlo", 13)
FONT_BOLD  = ("Menlo", 13, "bold")
FONT_SM    = ("Menlo", 11)
FONT_TINY  = ("Menlo", 10)

PLACEHOLDER = "ENTER TASK_"

def _hide_python_dock_icon():
    """设置激活策略为 Accessory（无 Dock 图标）+ 应用图标换为 Todo.icns。

    launcher execv 了 python3.9 后，进程仍带 Python 火箭图标出现在 Dock。
    这里在 tk.Tk() 初始化 Cocoa 之后用 PyObjC 改激活策略并设置应用图标。
    所有调用都包在 try 里，失败不影响主程序。
    """
    try:
        import AppKit
        NSApp = AppKit.NSApplication.sharedApplication()
        # Accessory = 无 Dock 图标、无菜单栏、可显示窗口
        NSApp.setActivationPolicy_(
            AppKit.NSApplicationActivationPolicyAccessory
        )
        # 应用图标换成 Todo.icns
        icon_path = (
            Path(__file__).parent
            / "Todo.app" / "Contents" / "Resources" / "Todo.icns"
        )
        if icon_path.exists():
            icon = AppKit.NSImage.alloc().initWithContentsOfFile_(str(icon_path))
            if icon:
                NSApp.setApplicationIconImage_(icon)
    except Exception:
        # PyObjC 不可用 / 调用失败 → 静默忽略，不影响 app 启动
        pass
def load_todos():
    if not DATA_FILE.exists():
        return []
    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        # JSON 损坏：先备份原文件再返回空，避免下次 save 直接覆盖丢数据
        import time
        bak = DATA_FILE.with_name(f"todos.json.bak.{int(time.time())}")
        try:
            DATA_FILE.replace(bak)
        except OSError:
            pass
        return []
    except OSError:
        return []


def save_todos(todos):
    DATA_FILE.write_text(
        json.dumps(todos, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


class TodoApp:
    def __init__(self, root):
        self.root = root
        root.title("Todo")
        root.geometry("400x300")
        root.minsize(360, 260)
        root.configure(bg=BLACK)

        self.todos = load_todos()
        self.selected_ids = set()
        self.editing_id = None
        self.row_h = 30  # 默认值，_build() 中也会设置

        self.pet_window = None  # 由 launch_main 在外部注入

        # 数据迁移：老 todo 补默认字段（priority=1, due=None, tags=[]）
        for t in self.todos:
            t.setdefault("priority", 1)
            t.setdefault("due", None)
            t.setdefault("tags", [])

        self._build()
        self._set_placeholder()
        self._refresh()

    # ---------- UI ----------
    def _build(self):
        root = self.root
        root.configure(bg=BLACK)

        # — 工具栏：放 root 顶级（不随 panel expand 被挤）—
        bar = tk.Frame(root, bg=BLACK, height=32)
        bar.pack(side="bottom", fill="x", padx=10, pady=(6, 10))
        bar.pack_propagate(False)

        self.bar_canvas = tk.Canvas(
            bar, height=32, bg=BLACK, highlightthickness=0, bd=0,
        )
        self.bar_canvas.pack(fill="x", padx=4)
        self._bar_btns = []

        def make_btn(label, cmd):
            self._bar_btns.append((label, cmd))

        make_btn("✓", self.toggle_done)
        make_btn("✕", self.delete_selected)
        make_btn("C", self.clear_done)
        make_btn("↑", lambda: self.move(-1))
        make_btn("↓", lambda: self.move(1))

        self.bar_canvas.bind("<Configure>", lambda _e: self._redraw_bar())
        self.bar_canvas.bind("<Button-1>", self._bar_click)
        self.bar_canvas.bind("<Motion>",   self._bar_hover)

        # — ttk 样式：clam 主题 + NES 配色 —
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(
            "NES.TButton",
            font=FONT_SM, foreground=WHITE, background=BLACK,
            bordercolor=RED, borderwidth=1, focuscolor=RED,
            relief="raised", padding=(6, 2),
        )
        style.map(
            "NES.TButton",
            foreground=[("active", WHITE), ("disabled", DIM)],
            background=[("active", RED), ("pressed", RED_DK)],
        )
        style.configure(
            "NES.Flat.TButton",
            font=("Menlo", 12, "bold"),
            foreground=WHITE, background=RED,
            bordercolor=WHITE, borderwidth=1, focuscolor=WHITE,
            relief="ridge", padding=(4, 0),
        )
        style.map(
            "NES.Flat.TButton",
            foreground=[("active", WHITE)],
            background=[("active", RED_DK), ("pressed", RED_DK)],
        )

        # 外壳边框（细描边 + 圆角内框）
        outer = tk.Frame(root, bg=BLACK)
        outer.pack(fill="both", expand=True, padx=10, pady=10)

        # — 顶部红色横条 + 标题 —
        title_bar = tk.Frame(outer, bg=RED, height=32)
        title_bar.pack(fill="x")
        title_bar.pack_propagate(False)
        tk.Label(
            title_bar, text="★  TODO  LIST  ★",
            font=("Menlo", 14, "bold"),
            fg=WHITE, bg=RED,
        ).pack(side="left", padx=12)
        self.status = tk.Label(
            title_bar, text="0/0",
            font=("Menlo", 13, "bold"),
            fg=WHITE, bg=RED,
        )
        self.status.pack(side="right", padx=12)
        ttk.Button(
            title_bar, text="▽", command=self._collapse, style="NES.Flat.TButton",
        ).pack(side="right", padx=(0, 8))

        # — 屏幕面板（黑底）—
        panel = tk.Frame(outer, bg=PANEL)
        panel.pack(fill="both", expand=True, pady=(2, 0))

        # 输入区（屏幕内）
        inp = tk.Frame(panel, bg=PANEL)
        inp.pack(fill="x", padx=12, pady=(10, 6))

        tk.Label(
            inp, text="›", font=FONT_BOLD, fg=RED, bg=PANEL,
        ).pack(side="left", padx=(0, 4))

        self.entry_var = tk.StringVar()
        self.entry = tk.Entry(
            inp, textvariable=self.entry_var,
            font=FONT, bg=PANEL, fg=WHITE,
            insertbackground=WHITE, relief="flat",
            highlightthickness=0, borderwidth=0,
        )
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<Return>", lambda _e: self.add())
        self.entry.bind("<FocusIn>", self._clear_placeholder)
        self.entry.bind("<FocusOut>", self._set_placeholder)

        # 下划线
        self._inp_underline = tk.Frame(panel, bg=RED, height=2)
        self._inp_underline.pack(fill="x", padx=12, pady=(0, 8))

        # 列表（Canvas 自绘）
        wrap = tk.Frame(panel, bg=PANEL)
        wrap.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        wrap.grid_rowconfigure(0, weight=1)
        wrap.grid_columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(
            wrap, bg=PANEL, highlightthickness=0, bd=0,
        )
        self.canvas.grid(row=0, column=0, sticky="nsew")
        vsb = ttk.Scrollbar(wrap, orient="vertical", command=self.canvas.yview)
        vsb.grid(row=0, column=1, sticky="ns")
        self.canvas.configure(yscrollcommand=vsb.set)

        # 工具栏已移到 root 顶级（见 _build 顶部），这里不再创建

    def _redraw_bar(self):
        c = self.bar_canvas
        c.delete("all")
        self._bar_rects = []
        if not self._bar_btns:
            return
        w = c.winfo_width()
        n = len(self._bar_btns)
        bw, bh, gap = 56, 30, 6
        total = n * bw + (n - 1) * gap
        x = max(4, (w - total) / 2)
        y = (c.winfo_height() - bh) / 2
        for i, (label, _cmd) in enumerate(self._bar_btns):
            x1, y1 = x, y
            x2, y2 = x + bw, y + bh
            hover = (i == getattr(self, "_hover_idx", -1))
            c.create_rectangle(
                x1, y1, x2, y2,
                fill=RED if hover else BLACK,
                outline=RED, width=2,
            )
            c.create_text(
                (x1 + x2) / 2, (y1 + y2) / 2 + 1,
                text=label, fill=WHITE,
                font=("Menlo", 20, "bold"),
            )
            self._bar_rects.append((x1, y1, x2, y2, i))
            x = x2 + gap

    def _bar_click(self, e):
        for x1, y1, x2, y2, i in self._bar_rects:
            if x1 <= e.x <= x2 and y1 <= e.y <= y2:
                _, cmd = self._bar_btns[i]
                cmd()
                return

    def _bar_hover(self, e):
        new_idx = -1
        for x1, y1, x2, y2, i in self._bar_rects:
            if x1 <= e.x <= x2 and y1 <= e.y <= y2:
                new_idx = i
                break
        if new_idx != getattr(self, "_hover_idx", -1):
            self._hover_idx = new_idx
            self._redraw_bar()

        self.row_h = 30
        self._row_y = []
        self.canvas.bind("<Configure>", lambda _e: self._redraw())
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<Double-Button-1>", self._on_dblclick)
        self.root.bind("<Delete>", lambda _e: self.delete_selected())
        self.root.bind("<Control-Up>",  lambda _e: self.move(-1))
        self.root.bind("<Control-Down>",lambda _e: self.move(1))
        self.root.bind("<Command-Up>",  lambda _e: self.move(-1))
        self.root.bind("<Command-Down>",lambda _e: self.move(1))
        # 优先级 / 到期日快捷键
        # 用 bind_all('<KeyPress>') + 手动判 modifier，比 <Command-1> 在 macOS Tk 上稳
        # （<Command-数字> 写法在 Tk 上偶尔被 Entry 拦截或不触发）
        self.root.bind_all("<KeyPress>", self._on_key_press)

    # ---------- placeholder ----------
    def _set_placeholder(self, _e=None):
        if not self.entry_var.get():
            self.entry_var.set(PLACEHOLDER)
            self.entry.config(fg=DIM)

    def _clear_placeholder(self, _e=None):
        if self.entry_var.get() == PLACEHOLDER:
            self.entry_var.set("")
        self.entry.config(fg=WHITE)

    # ---------- 数据操作 ----------
    def add(self):
        raw = self.entry_var.get().strip()
        if not raw or raw == PLACEHOLDER:
            return

        # 解析 inline 元数据语法: p=N d=YYYY-MM-DD t=tag1,tag2
        # 例如: "九州通 p=0 d=2026-08-30 t=PR稿"
        import re
        priority = 1  # 默认 medium
        due = None
        tags = []

        p_match = re.search(r"\bp=([012])\b", raw)
        if p_match:
            priority = int(p_match.group(1))
            raw = re.sub(r"\bp=[012]\b", "", raw, count=1).strip()

        d_match = re.search(r"\bd=(\d{4}-\d{2}-\d{2})\b", raw)
        if d_match:
            due = d_match.group(1)
            raw = re.sub(r"\bd=\d{4}-\d{2}-\d{2}\b", "", raw, count=1).strip()

        t_match = re.search(r"\bt=([^\s]+(?:\s[^=][^\s]*)*)", raw)
        if t_match:
            tag_str = t_match.group(1)
            tags = [t.strip() for t in tag_str.split(",") if t.strip()]
            raw = raw.replace(t_match.group(0), "", 1).strip()

        title = raw.replace("  ", " ").strip()
        if not title:
            return

        self.todos.insert(0, {
            "id": int(datetime.now().timestamp() * 1000),
            "title": title,
            "done": False,
            "priority": priority,
            "due": due,
            "tags": tags,
            "created": datetime.now().strftime("%Y-%m-%d %H:%M"),
        })
        self.entry_var.set("")
        self._sort_todos()
        self._persist()
        self.entry.focus_set()

    def _sort_todos(self):
        """按 priority → due → created 排序。"""
        def key(t):
            pr = t.get("priority", 1)
            due = t.get("due") or "9999-99-99"  # 无 due 排最后
            created = t.get("created", "9999")
            return (pr, due, created)
        # 未完成在上、已完成移到尾部
        not_done = [t for t in self.todos if not t["done"]]
        done = [t for t in self.todos if t["done"]]
        not_done.sort(key=key)
        done.sort(key=key)
        self.todos = not_done + done

    def toggle_done(self):
        if not self.selected_ids:
            return
        moved = []
        for t in self.todos:
            if t["id"] in self.selected_ids:
                t["done"] = not t["done"]
                if t["done"]:
                    moved.append(t)
        # 勾选完的任务移到最底层
        if moved:
            self.todos = [t for t in self.todos if t not in moved] + moved
        self._persist()

    def delete_selected(self):
        if not self.selected_ids:
            return
        self.todos = [t for t in self.todos if t["id"] not in self.selected_ids]
        self.selected_ids.clear()
        self._persist()

    def clear_done(self):
        before = len(self.todos)
        self.todos = [t for t in self.todos if not t["done"]]
        if len(self.todos) != before:
            self._persist()
        else:
            self._flash("没有已完成项。")

    def move(self, delta):
        if not self.selected_ids:
            return
        for tid in list(self.selected_ids):
            ids = [t["id"] for t in self.todos]
            if tid not in ids:
                continue
            idx = ids.index(tid)
            new_idx = max(0, min(len(self.todos) - 1, idx + delta))
            if new_idx != idx:
                self.todos.insert(new_idx, self.todos.pop(idx))
        self._persist()

    def _flash(self, text, ms=1500):
        self._saved_status = self.status.cget("text")
        self.status.config(text=text)
        self.root.after(ms, lambda: self.status.config(text=self._saved_status))

    def _set_priority(self, p):
        """设置选中项的优先级 (0=高/1=中/2=低)。
        Toggle 行为：再按同一键（高/低）会回到中，方便清除红/灰条。"""
        names = ["高", "中", "低"]
        if not self.selected_ids:
            self._flash("先选中任务")
            return
        for tid in self.selected_ids:
            for t in self.todos:
                if t["id"] == tid:
                    current = t.get("priority", 1)
                    # Toggle: 当前已经是 p (且不是中) → 回到中 (1)
                    if current == p and p != 1:
                        new_p = 1
                    else:
                        new_p = p
                    t["priority"] = new_p
                    break
        self._sort_todos()
        self._persist()
        # 反馈当前选中项的最终优先级（多选可能混合）
        levels = set()
        for tid in self.selected_ids:
            for t in self.todos:
                if t["id"] == tid:
                    levels.add(t.get("priority", 1))
                    break
        if len(levels) == 1:
            self._flash(f"优先级 → {names[list(levels)[0]]}")
        else:
            self._flash(f"优先级已设 ({len(levels)} 种)")

    def _set_due(self):
        """弹窗让用户输入到期日 (YYYY-MM-DD)，留空清除。"""
        if not self.selected_ids:
            self._flash("先选中任务")
            return
        from tkinter import simpledialog
        current = ""
        for tid in self.selected_ids:
            for t in self.todos:
                if t["id"] == tid:
                    current = t.get("due") or ""
                    break
            if current: break
        s = simpledialog.askstring(
            "到期日", "YYYY-MM-DD (留空清除):",
            initialvalue=current, parent=self.root,
        )
        if s is None:
            return
        s = s.strip()
        import re as _re
        if s and not _re.match(r"^\d{4}-\d{2}-\d{2}$", s):
            self._flash("格式：YYYY-MM-DD")
            return
        for tid in self.selected_ids:
            for t in self.todos:
                if t["id"] == tid:
                    t["due"] = s if s else None
                    break
        self._sort_todos()
        self._persist()
        self._flash("已设到期" if s else "已清除到期")

    def _on_key_press(self, event):
        """App 级键盘事件：⌘1/⌘2/⌘3 = 优先级，⌘D = 到期日。
        用 bind_all + 手动判 modifier 比 <Command-N> 写法在 macOS Tk 上稳。
        返回 'break' 表示消费该事件，None 表示让默认行为继续。"""
        # Cmd modifier 在 macOS Tk 上 mask = 0x10（0x8 是 Alt/Option，不是 Cmd）
        if not (event.state & 0x10):
            return None
        key = event.keysym.lower()
        if key == "1":
            self._set_priority(0)
            return "break"
        if key == "2":
            self._set_priority(1)
            return "break"
        if key == "3":
            self._set_priority(2)
            return "break"
        if key == "d":
            self._set_due()
            return "break"
        return None

    def _collapse(self):
        # 同进程切换：隐藏主窗口，显示宠物窗口（Toplevel）
        save_todos(self.todos)
        self.root.withdraw()
        if self.pet_window is not None:
            self.pet_window.show()

    # ---------- 渲染 ----------
    def _persist(self):
        save_todos(self.todos)
        # 通知宠物窗口刷新计数（同进程直接回调，无文件 IO）
        if getattr(self, "pet_window", None) is not None:
            self.pet_window.refresh()
        self._refresh()

    def _refresh(self):
        done = sum(1 for t in self.todos if t["done"])
        self.status.config(text=f"{done:02d}/{len(self.todos):02d}")
        self._redraw()

    def _redraw(self, _e=None):
        c = self.canvas
        c.delete("all")
        self._row_y = []

        w = max(c.winfo_width(), 200)
        y = 0
        for idx, t in enumerate(self.todos):
            y0 = y
            y1 = y + self.row_h
            sel = t["id"] in self.selected_ids

            # 行底色
            if sel:
                c.create_rectangle(0, y0, w, y1, fill=SEL, outline="")
            elif idx % 2 == 1:
                c.create_rectangle(0, y0, w, y1, fill=LINE, outline="")

            # —— 优先级条（左侧 3px 宽竖条）——
            pr = t.get("priority", 1)
            if pr == 0:    # 红色 = 高优先级
                c.create_rectangle(0, y0, 3, y1, fill=RED, outline="")
            elif pr == 2:  # 灰 = 低优先级
                c.create_rectangle(0, y0, 3, y1, fill=DIM, outline="")

            # 复选框（像素方框）—— 右移 6px 给 priority 条留位
            bx = 18
            by = y0 + (self.row_h - 16) / 2
            if t["done"]:
                c.create_rectangle(bx, by, bx+16, by+16,
                                   fill=RED, outline=RED)
                # NES 风格打钩（粗像素 ✓）
                c.create_line(bx+4, by+9, bx+7, by+12, fill=WHITE, width=2)
                c.create_line(bx+7, by+12, bx+13, by+4, fill=WHITE, width=2)
            else:
                c.create_rectangle(bx, by, bx+16, by+16,
                                   fill=PANEL, outline=DIM)

            # 文字
            color = DIM if t["done"] else WHITE
            title = t["title"]

            # —— 右侧 due 日期 ——
            due = t.get("due")
            due_text = ""
            due_color = None
            if due and len(due) == 10:
                # YYYY-MM-DD → MM/DD 紧凑显示
                mm, dd = due[5:7], due[8:10]
                # 去掉前导 0
                mm_l = mm.lstrip("0") or "0"
                dd_l = dd.lstrip("0") or "0"
                due_text = f"· {mm_l}/{dd_l}"
                today = datetime.now().strftime("%Y-%m-%d")
                if due < today:
                    due_color = RED_DK  # 已过期
                elif due == today:
                    due_color = RED     # 今天到期
                else:
                    due_color = DIM     # 未来
                # 已完成项的 due 文字用 DIM
                if t["done"]:
                    due_color = DIM

            # 估算 title 截断长度（要给 due 留 ~48px 空间）
            due_w = 48 if due_text else 0
            max_chars = max(5, (w - bx - 26 - 12 - due_w) // 8)
            if len(title) > max_chars:
                title = title[:max_chars-1] + "…"
            tx = bx + 26
            c.create_text(tx, (y0+y1)//2, text=title,
                          anchor="w", fill=color, font=FONT)

            # due 日期文字（右对齐到行尾）
            if due_text:
                dx = w - 8
                c.create_text(dx, (y0+y1)//2, text=due_text,
                              anchor="e", fill=due_color, font=FONT_SM)

            # 行下划线
            c.create_line(0, y1, w, y1, fill=LINE)

            self._row_y.append((t["id"], y0, y1))
            y = y1

        c.configure(scrollregion=(0, 0, w, max(y, c.winfo_height())))

    # ---------- 事件 ----------
    def _hit(self, y):
        for tid, y0, y1 in self._row_y:
            if y0 <= y < y1:
                return tid
        return None

    def _on_click(self, e):
        tid = self._hit(e.y)
        if tid is None:
            self.selected_ids.clear()
            self._redraw()
            return
        # 点击复选框区域
        if 10 <= e.x <= 30:
            self.selected_ids = {tid}
            self.toggle_done()
            return
        # 普通点击：单选 / ⌘+点击 多选
        mods = e.state & 0x11  # Shift(0x1) + Cmd(0x10) 都进入多选（macOS Tk）
        if mods:
            if tid in self.selected_ids:
                self.selected_ids.discard(tid)
            else:
                self.selected_ids.add(tid)
        else:
            self.selected_ids = {tid}
        self._redraw()

    def _on_dblclick(self, e):
        tid = self._hit(e.y)
        if tid is None or 10 <= e.x <= 30:
            return
        self._start_edit(tid, e.y)

    def _start_edit(self, tid, y_click):
        for item_tid, y0, _y1 in self._row_y:
            if item_tid == tid:
                y_top = y0
                break
        todo = next((t for t in self.todos if t["id"] == tid), None)
        if todo is None:
            return
        if self.editing_id is not None:
            self._commit_edit()

        w = self.canvas.winfo_width()
        edit_x, edit_y = 38, y_top + 4
        edit_w = max(100, w - 38 - 110)
        edit_h = self.row_h - 8

        self.edit = tk.Entry(
            self.canvas, font=FONT, bg=PANEL, fg=WHITE,
            insertbackground=WHITE, relief="solid", borderwidth=1,
            highlightthickness=1, highlightcolor=RED,
        )
        self.edit.insert(0, todo["title"])
        self.edit.select_range(0, "end")
        self.edit.focus_set()
        self.edit.place(x=edit_x, y=edit_y, width=edit_w, height=edit_h)
        self.editing_id = tid
        self.edit.bind("<Return>",  lambda _e: self._commit_edit())
        self.edit.bind("<Escape>",  lambda _e: self._cancel_edit())
        self.edit.bind("<FocusOut>",lambda _e: self._commit_edit())

    def _commit_edit(self):
        if self.editing_id is None or not getattr(self, "edit", None):
            return
        new_title = self.edit.get().strip()
        tid = self.editing_id
        try:
            self.edit.destroy()
        except tk.TclError:
            pass
        self.edit = None
        self.editing_id = None
        if new_title:
            for t in self.todos:
                if t["id"] == tid:
                    t["title"] = new_title
                    break
        self._persist()

    def _cancel_edit(self):
        if self.editing_id is None:
            return
        try:
            self.edit.destroy()
        except tk.TclError:
            pass
        self.edit = None
        self.editing_id = None


def main():
    root = tk.Tk()
    _hide_python_dock_icon()
    try:
        root.tk.call("tk", "scaling", 1.2)
    except tk.TclError:
        pass
    TodoApp(root)
    root.mainloop()


# ============================================================
# 桌面宠物 —— NES 风格小卡片
# ============================================================

PET_W, PET_H = 240, 110


class PetWindow:
    """迷你卡片，悬浮屏幕右下角，无边框、置顶。
    Toplevel 而非独立 Tk：与主窗口共享同一 Python 进程，
    数据通过 self.app.todos 直接读取（无需重新 load_todos()）。
    双击切到完整 Todo 窗口。
    """

    def __init__(self, master, app):
        self.master = master   # 主窗口 Tk root
        self.app = app         # TodoApp 实例（用于读 todos）

        # 用 Toplevel 而非 Tk（关键：同一进程、同一事件循环）
        self.toplevel = tk.Toplevel(master)
        self.toplevel.overrideredirect(True)
        self.toplevel.attributes("-topmost", True)
        self.toplevel.configure(bg=BLACK)
        try:
            self.toplevel.tk.call("tk", "scaling", 1.2)
        except tk.TclError:
            pass

        # 初始隐藏（用户从 ▽ 切换时才显示）
        self.toplevel.withdraw()

        # 位置：屏幕右下角
        sw = self.toplevel.winfo_screenwidth()
        sh = self.toplevel.winfo_screenheight()
        x = sw - PET_W - 24
        y = sh - PET_H - 80
        self.toplevel.geometry(f"{PET_W}x{PET_H}+{x}+{y}")

        self.canvas = tk.Canvas(
            self.toplevel, width=PET_W, height=PET_H,
            bg=BLACK, highlightthickness=0, bd=0,
        )
        self.canvas.pack()

        self.canvas.bind("<Double-Button-1>", self._open_main)
        self.canvas.bind("<Button-1>", self._start_drag)
        self.canvas.bind("<B1-Motion>", self._drag)
        self.canvas.bind("<Enter>", lambda _e: self.canvas.config(cursor="hand2"))
        self.canvas.bind("<Leave>", lambda _e: self.canvas.config(cursor=""))

        # 让 TodoApp 知道宠物窗口存在（用于 _persist 后回调刷新）
        self.app.pet_window = self

    def show(self):
        """显示宠物窗口，并刷新数据。"""
        self._draw()
        self.toplevel.deiconify()
        self.toplevel.lift()

    def hide(self):
        """隐藏宠物窗口（不销毁）。"""
        self.toplevel.withdraw()

    def refresh(self):
        """TodoApp 数据变更后调用，重绘宠物窗口。"""
        if self.toplevel.winfo_viewable():
            self._draw()

    def _draw(self):
        c = self.canvas
        c.delete("all")

        # 外壳
        c.create_rectangle(0, 0, PET_W, PET_H, fill=BLACK, outline=RED, width=2)

        # 顶部红条
        c.create_rectangle(2, 2, PET_W-2, 26, fill=RED, outline="")
        c.create_text(
            10, 14, text="\u2605  TODO  \u2605", anchor="w",
            font=("Menlo", 12, "bold"), fill=WHITE,
        )
        # 数据来源：app.todos（同一进程，直接读内存，避免 load_todos() IO）
        todos = self.app.todos
        n_total = len(todos)
        n_done = sum(1 for t in todos if t["done"])
        remain = n_total - n_done
        c.create_text(
            PET_W - 10, 14, text=f"{remain:02d}/{n_total:02d}", anchor="e",
            font=("Menlo", 12, "bold"), fill=WHITE,
        )

        # 屏幕区
        sx1, sy1, sx2, sy2 = 10, 32, PET_W-10, PET_H-22
        c.create_rectangle(sx1, sy1, sx2, sy2, fill=PANEL, outline=LINE)

        # 大数字 + REMAIN
        big_x = sx1 + 50
        big_y = (sy1 + sy2) / 2 - 4
        c.create_text(
            big_x, big_y, text=f"{remain:02d}", anchor="center",
            font=("Menlo", 26, "bold"), fill=WHITE,
        )
        c.create_text(
            big_x, big_y + 20, text="REMAIN", anchor="center",
            font=("Menlo", 8, "bold"), fill=DIM,
        )

        # 进度条
        bar_y = sy2 - 8
        bar_x1 = big_x + 40
        bar_x2 = sx2 - 8
        bar_w = bar_x2 - bar_x1
        c.create_rectangle(bar_x1, bar_y, bar_x2, bar_y + 4, fill=LINE, outline="")
        if n_total > 0:
            fill_w = bar_w * n_done / n_total
            c.create_rectangle(bar_x1, bar_y, bar_x1 + fill_w, bar_y + 4,
                               fill=RED, outline="")

        # 小装饰：A/B 圆按钮
        for cx, cy in [(PET_W - 28, sy1 + 18), (PET_W - 28, sy1 + 36)]:
            c.create_oval(cx - 5, cy - 5, cx + 5, cy + 5,
                          fill=RED, outline=RED_DK)

        # 底部提示条
        c.create_rectangle(2, PET_H-20, PET_W-2, PET_H-2,
                           fill=BLACK, outline="")
        c.create_text(
            PET_W // 2, PET_H - 11,
            text="\u25c6 DOUBLE-CLICK TO OPEN \u25c6",
            font=("Menlo", 9, "bold"), fill=RED,
        )

    def _open_main(self, _e=None):
        """双击宠物：隐藏自己，显示主窗口。"""
        self.hide()
        self.master.deiconify()
        self.master.lift()
        self.master.focus_force()

    def _start_drag(self, e):
        self._ox, self._oy = e.x, e.y

    def _drag(self, e):
        x = self.toplevel.winfo_x() + e.x - self._ox
        y = self.toplevel.winfo_y() + e.y - self._oy
        self.toplevel.geometry(f"+{x}+{y}")


def launch_main():
    """启动 Todo App（含主窗口 + 宠物窗口 Toplevel，同进程）。"""
    root = tk.Tk()
    _hide_python_dock_icon()
    try:
        root.tk.call("tk", "scaling", 1.2)
    except tk.TclError:
        pass
    root.geometry("400x300")
    root.minsize(360, 260)

    app = TodoApp(root)
    # 宠物窗口作为 Toplevel，初始隐藏（用户点 ▽ 时才显示）
    pet = PetWindow(root, app)
    del pet  # 已被 app.pet_window 引用，此变量不需要

    root.mainloop()


if __name__ == "__main__":
    launch_main()