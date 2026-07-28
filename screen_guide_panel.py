import tkinter as tk
from tkinter import ttk, colorchooser, messagebox, simpledialog
import json
import os
import math

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

class OverlayWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.attributes("-fullscreen", True)
        self.attributes("-topmost", True)
        self.attributes("-transparentcolor", "#000001")
        self.config(bg="#000001")
        self.overrideredirect(True)
        self.set_click_through()
        self.canvas = tk.Canvas(self, bg="#000001", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.visible = True

    def set_click_through(self):
        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            ex_style = ctypes.windll.user32.GetWindowLongPtrW(hwnd, -20)
            ex_style |= 0x00000020
            ctypes.windll.user32.SetWindowLongPtrW(hwnd, -20, ex_style)
        except Exception:
            pass

    def clear(self):
        self.canvas.delete("all")

    def draw_single_line(self, w, h, line_cfg):
        """绘制单条线条，中心坐标系: -100(左/上) 到 0(中心) 到 100(右/下)"""
        def to_pixel(val, total):
            try:
                return int(total / 2 + float(val) / 100 * total / 2)
            except (ValueError, TypeError):
                return total // 2

        cx = to_pixel(line_cfg["x"], w)
        cy = to_pixel(line_cfg["y"], h)
        angle = math.radians(line_cfg["angle"])
        dx = math.cos(angle) * line_cfg["length"] / 2
        dy = math.sin(angle) * line_cfg["length"] / 2
        self.canvas.create_line(cx - dx, cy - dy, cx + dx, cy + dy,
                                fill=line_cfg["color"], width=line_cfg["width"])

    def render_config(self, config_data):
        if not self.visible:
            self.clear()
            return
        self.clear()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        for line in config_data["lines"]:
            self.draw_single_line(sw, sh, line)

    def toggle_visibility(self):
        self.visible = not self.visible
        if self.visible:
            self.deiconify()
        else:
            self.withdraw()


class ControlPanel(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("多层屏幕辅助线｜增强版（实时调节）")
        self.geometry("620x720")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self.on_close_panel)

        self.overlay = OverlayWindow(self)
        self.config_list = []
        self.current_config_idx = -1
        self.selected_line_index = -1

        self.load_config()
        self.build_ui()
        self.refresh_preset_list()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    self.config_list = json.load(f).get("configs", [])
            except Exception as err:
                messagebox.showerror("配置读取失败", str(err))
        
        # 自动迁移旧版配置
        migrated = False
        for config in self.config_list:
            for line in config.get("lines", []):
                if "name" not in line:
                    line["name"] = "未命名"
                    migrated = True
                for key in ["x", "y"]:
                    val = line.get(key, 0)
                    if isinstance(val, str) and val.endswith("%"):
                        line[key] = round(float(val.strip("%")) - 50, 1)
                        migrated = True
        if migrated:
            self.save_config_file(show_message=False)

        if not self.config_list:
            self.config_list = [{
                "name": "默认十字准星",
                "lines": [
                    {"name": "横线", "x": 0, "y": 0, "length": 220, "angle": 0, "width": 2, "color": "#00ff00"},
                    {"name": "竖线", "x": 0, "y": 0, "length": 220, "angle": 90, "width": 2, "color": "#00ff00"}
                ]
            }]

    def save_config_file(self, show_message=True):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump({"configs": self.config_list}, f, ensure_ascii=False, indent=2)
            if show_message:
                messagebox.showinfo("保存成功", f"配置已保存到：\n{CONFIG_FILE}")
        except Exception as err:
            if show_message:
                messagebox.showerror("保存失败", f"无法写入配置文件：\n{CONFIG_FILE}\n\n错误信息：{err}")

    def reload_config(self):
        self.load_config()
        self.current_config_idx = 0 if self.config_list else -1
        self.selected_line_index = -1
        self.refresh_preset_list()

    def get_active_lines(self):
        if self.current_config_idx < 0:
            return []
        return self.config_list[self.current_config_idx]["lines"]

    def refresh_preset_list(self):
        self.preset_listbox.delete(0, tk.END)
        for cfg in self.config_list:
            self.preset_listbox.insert(tk.END, cfg["name"])
        if self.current_config_idx >= 0 and self.current_config_idx < len(self.config_list):
            self.preset_listbox.selection_set(self.current_config_idx)
        self.refresh_line_listbox(preserve_selection=False)
        self.render_current_preset()

    def render_current_preset(self):
        if 0 <= self.current_config_idx < len(self.config_list):
            self.overlay.render_config(self.config_list[self.current_config_idx])

    def on_select_preset(self, event):
        sel = self.preset_listbox.curselection()
        if not sel:
            return
        new_index = sel[0]
        if new_index == self.current_config_idx:
            return
        self.current_config_idx = new_index
        self.selected_line_index = -1
        self.refresh_line_listbox(preserve_selection=False)
        self.render_current_preset()

    def add_new_preset(self):
        name = simpledialog.askstring("新建预设", "输入预设名称：", initialvalue="新预设")
        if not name:
            return
        template = {
            "name": name,
            "lines": [
                {"name": "线条1", "x": 0, "y": 0, "length": 200, "angle": 0, "width": 2, "color": "#00ff00"}
            ]
        }
        self.config_list.append(template)
        self.save_config_file()
        self.current_config_idx = len(self.config_list) - 1
        self.selected_line_index = -1
        self.refresh_preset_list()
        self.preset_listbox.selection_set(self.current_config_idx)
        self.refresh_line_listbox(preserve_selection=False)
        self.render_current_preset()

    def delete_preset(self):
        sel = self.preset_listbox.curselection()
        if not sel:
            messagebox.showwarning("提示", "先选中一个预设！")
            return
        idx = sel[0]
        if len(self.config_list) <= 1:
            messagebox.showinfo("限制", "至少保留一个预设！")
            return
        del self.config_list[idx]
        self.current_config_idx = min(idx, len(self.config_list) - 1)
        self.selected_line_index = -1
        self.save_config_file()
        self.refresh_preset_list()

    def rename_preset(self):
        sel = self.preset_listbox.curselection()
        if not sel:
            messagebox.showwarning("提示", "先选中预设！")
            return
        idx = sel[0]
        old_name = self.config_list[idx]["name"]
        new_name = simpledialog.askstring("重命名预设", "设置名称：", initialvalue=old_name)
        if new_name:
            self.config_list[idx]["name"] = new_name
            self.save_config_file()
            self.current_config_idx = idx
            self.refresh_preset_list()
            self.preset_listbox.selection_set(idx)

    def refresh_line_listbox(self, preserve_selection=True):
        saved_selection = self.selected_line_index if preserve_selection else -1
        self.line_listbox.delete(0, tk.END)
        lines = self.get_active_lines()
        for line in lines:
            name = line.get("name", "未命名")
            self.line_listbox.insert(tk.END, f"{name} | {line['color']}")
        if preserve_selection and 0 <= saved_selection < len(lines):
            self.line_listbox.selection_clear(0, tk.END)
            self.line_listbox.selection_set(saved_selection)
            self.line_listbox.see(saved_selection)

    def on_select_line(self, event):
        sel = self.line_listbox.curselection()
        if not sel:
            return
        new_index = sel[0]
        if new_index == self.selected_line_index:
            return
        self.selected_line_index = new_index
        self.load_line_params_to_slider()

    def load_line_params_to_slider(self):
        if self.selected_line_index < 0:
            return
        line = self.get_active_lines()[self.selected_line_index]
        # 自动迁移旧版百分比格式
        def to_val(v):
            try:
                return float(v)
            except (ValueError, TypeError):
                return float(v.strip("%")) - 50 if isinstance(v, str) else 0

        self.var_x.set(to_val(line["x"]))
        self.var_y.set(to_val(line["y"]))
        self.var_len.set(line["length"])
        self.var_width.set(line["width"])
        self.var_angle.set(line["angle"])
        self.color_str.set(line["color"])
        self._sync_entries()
        self._apply_to_line()

    # 参数字段配置: (滑条变量, 输入框, 最小值, 最大值, 是否整数)
    PARAM_FIELDS = [
        ('var_x', 'entry_x', -100, 100, False),
        ('var_y', 'entry_y', -100, 100, False),
        ('var_len', 'entry_len', 2, 600, True),
        ('var_width', 'entry_width', 1, 10, True),
        ('var_angle', 'entry_angle', 0, 360, False),
    ]

    def on_slider_change(self, event=None):
        self._sync_entries()
        self._apply_to_line()

    def _sync_entries(self):
        """将滑条值同步到输入框"""
        for var_name, entry_name, _, _, is_int in self.PARAM_FIELDS:
            entry = getattr(self, entry_name)
            val = getattr(self, var_name).get()
            entry.delete(0, tk.END)
            entry.insert(0, str(int(val)) if is_int else f"{val:.1f}")

    def _on_entry_confirm(self, event=None):
        """从输入框读取值并应用约束"""
        try:
            for var_name, entry_name, min_val, max_val, _ in self.PARAM_FIELDS:
                entry = getattr(self, entry_name)
                val = float(entry.get())
                getattr(self, var_name).set(max(min_val, min(max_val, val)))
            self._sync_entries()
            self._apply_to_line()
        except ValueError:
            self._sync_entries()

    def _apply_to_line(self):
        if self.selected_line_index < 0:
            return
        line = self.get_active_lines()[self.selected_line_index]
        line["x"] = round(self.var_x.get(), 1)
        line["y"] = round(self.var_y.get(), 1)
        line["length"] = int(self.var_len.get())
        line["width"] = int(self.var_width.get())
        line["angle"] = round(self.var_angle.get(), 1)
        line["color"] = self.color_str.get()
        self.render_current_preset()
        self.refresh_line_listbox()

    def add_new_line(self):
        line_count = len(self.get_active_lines()) + 1
        template = {
            "name": f"线条{line_count}",
            "x": 0, "y": 0,
            "length": 150, "angle": 0,
            "width": 2, "color": "#00ff00"
        }
        self.get_active_lines().append(template)
        self.refresh_line_listbox(preserve_selection=False)
        self.render_current_preset()
        new_idx = len(self.get_active_lines()) - 1
        self.line_listbox.selection_set(new_idx)
        self.selected_line_index = new_idx
        self.load_line_params_to_slider()

    def rename_line(self):
        if self.selected_line_index < 0:
            messagebox.showwarning("提示", "先选中线条！")
            return
        lines = self.get_active_lines()
        line = lines[self.selected_line_index]
        old_name = line.get("name", "未命名")
        new_name = simpledialog.askstring("重命名线条", "设置线条名称：", initialvalue=old_name)
        if new_name:
            line["name"] = new_name
            self.refresh_line_listbox()
            self.save_config_file()

    def delete_selected_line(self):
        if self.selected_line_index < 0:
            messagebox.showwarning("提示", "选中线条后再删除！")
            return
        lines = self.get_active_lines()
        if len(lines) <= 1:
            messagebox.showinfo("限制", "至少保留一条线条！")
            return
        del lines[self.selected_line_index]
        self.selected_line_index = -1
        self.refresh_line_listbox(preserve_selection=False)
        self.render_current_preset()

    def pick_color(self):
        c = colorchooser.askcolor(self.color_str.get())
        if c[1]:
            self.color_str.set(c[1])
            self._apply_to_line()

    def build_ui(self):
        main = ttk.Frame(self, padding=10)
        main.pack(fill=tk.BOTH, expand=True)

        top_btn_frame = ttk.Frame(main)
        top_btn_frame.pack(fill=tk.X, pady=(0,6))
        ttk.Button(top_btn_frame, text="显示/隐藏辅助线", command=self.overlay.toggle_visibility).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        preset_frame = ttk.LabelFrame(main, text="预设列表（点击切换）", padding=6)
        preset_frame.pack(fill=tk.BOTH)
        self.preset_listbox = tk.Listbox(preset_frame, height=5, selectbackground="#0078d7", selectforeground="white", activestyle="dotbox", exportselection=False)
        self.preset_listbox.pack(fill=tk.BOTH, expand=True)
        self.preset_listbox.bind("<<ListboxSelect>>", self.on_select_preset)

        preset_btn_frame = ttk.Frame(preset_frame)
        preset_btn_frame.pack(fill=tk.X, pady=4)
        ttk.Button(preset_btn_frame, text="新建预设", command=self.add_new_preset).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)
        ttk.Button(preset_btn_frame, text="重命名", command=self.rename_preset).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)
        ttk.Button(preset_btn_frame, text="删除预设", command=self.delete_preset).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)

        ttk.Separator(main).pack(fill=tk.X, pady=8)

        line_frame = ttk.LabelFrame(main, text="线条列表（选中后编辑）", padding=6)
        line_frame.pack(fill=tk.BOTH)
        self.line_listbox = tk.Listbox(line_frame, height=4, selectbackground="#0078d7", selectforeground="white", activestyle="dotbox", exportselection=False)
        self.line_listbox.pack(fill=tk.BOTH, expand=True)
        self.line_listbox.bind("<<ListboxSelect>>", self.on_select_line)

        line_btn_frame = ttk.Frame(line_frame)
        line_btn_frame.pack(fill=tk.X, pady=4)
        ttk.Button(line_btn_frame, text="新增线条", command=self.add_new_line).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)
        ttk.Button(line_btn_frame, text="重命名", command=self.rename_line).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)
        ttk.Button(line_btn_frame, text="删除线条", command=self.delete_selected_line).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)

        ttk.Separator(main).pack(fill=tk.X, pady=8)

        param_frame = ttk.LabelFrame(main, text="线条参数调节【中心坐标系：X/Y范围 -100~100】", padding=6)
        param_frame.pack(fill=tk.X)

        self.var_x = tk.DoubleVar(value=0.0)
        self.var_y = tk.DoubleVar(value=0.0)
        self.var_len = tk.DoubleVar(value=200)
        self.var_width = tk.DoubleVar(value=2)
        self.var_angle = tk.DoubleVar(value=0)
        self.color_str = tk.StringVar(value="#00ff00")

        # 参数面板配置: (标签, 变量名, 滑条最小值, 滑条最大值)
        param_configs = [
            ("横向位置 X (-100~100)", 'var_x', -100, 100),
            ("纵向位置 Y (-100~100)", 'var_y', -100, 100),
            ("线段长度", 'var_len', 2, 600),
            ("线条宽度", 'var_width', 1, 10),
            ("旋转角度", 'var_angle', 0, 360),
        ]

        for row, (label, var_name, from_, to_) in enumerate(param_configs):
            ttk.Label(param_frame, text=label).grid(row=row, column=0, sticky="w")
            scale = ttk.Scale(param_frame, from_=from_, to=to_,
                             variable=getattr(self, var_name),
                             orient=tk.HORIZONTAL, command=self.on_slider_change)
            scale.grid(row=row, column=1, sticky="ew", padx=5)
            entry_name = 'entry_' + var_name[4:]  # var_x -> entry_x
            entry = ttk.Entry(param_frame, width=8)
            entry.grid(row=row, column=2, padx=2)
            entry.bind("<Return>", self._on_entry_confirm)
            entry.bind("<FocusOut>", self._on_entry_confirm)
            setattr(self, entry_name, entry)

        param_frame.columnconfigure(1, weight=1)
        ttk.Button(param_frame, text="选择颜色", command=self.pick_color).grid(row=row, column=0, columnspan=3, pady=4, sticky="ew")

        ttk.Button(main, text="强制刷新预览（备用）", command=self._apply_to_line).pack(pady=5, fill=tk.X)

        save_frame = ttk.Frame(main)
        save_frame.pack(fill=tk.X)
        ttk.Button(save_frame, text="保存配置文件", command=self.save_config_file).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        ttk.Button(save_frame, text="重载配置", command=self.reload_config).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        ttk.Separator(main).pack(fill=tk.X, pady=8)
        ttk.Button(main, text="完全退出程序", command=self.full_exit).pack(fill=tk.X)

    # 核心修改：点击窗口右上角X → 标准最小化，任务栏保留图标
    def on_close_panel(self):
        self.iconify()

    def full_exit(self):
        if messagebox.askokcancel("退出确认", "确定要完全退出程序吗？"):
            try:
                self.overlay.destroy()
            except Exception:
                pass
            self.quit()
            self.destroy()


if __name__ == "__main__":
    app = ControlPanel()
    app.mainloop()