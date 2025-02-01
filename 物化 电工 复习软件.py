import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import sqlite3
import os
import matplotlib
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import appdirs
from datetime import datetime
from io import BytesIO
import random

# 字体配置增强
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False

# 数据存储路径优化
DATA_DIR = appdirs.user_data_dir("StudyMasterPro", "StudyMaster")
DB_PATH = os.path.join(DATA_DIR, "study_data_v5.db")
os.makedirs(DATA_DIR, exist_ok=True)

class StudyMasterPro:
    def __init__(self):
        self.setup_database()
        self.root = tk.Tk()
        self.root.title("智能学习管理系统 v9.0")
        self.root.geometry("1200x800")
        self.current_image = None
        self.build_interface()
        self.load_initial_data()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.mainloop()

    def setup_database(self):
        """完整的数据库初始化"""
        self.conn = sqlite3.connect(DB_PATH)
        self.cursor = self.conn.cursor()
        
        # 课程表
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY,
            course_type TEXT,
            chapter TEXT,
            resource_type TEXT,
            completed INTEGER DEFAULT 0,
            last_updated TEXT,
            sort_order INTEGER
        )''')
        
        # 错题表
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS mistakes (
            id INTEGER PRIMARY KEY,
            course_type TEXT,
            chapter TEXT,
            question TEXT,
            image BLOB,
            error_type TEXT,
            tags TEXT,
            mastery_level INTEGER DEFAULT 0,
            probability REAL DEFAULT 1.0,
            created_at TEXT,
            last_reviewed TEXT
        )''')
        self.conn.commit()

    def build_interface(self):
        """完整的界面构建"""
        self.notebook = ttk.Notebook(self.root)
        
        # 课程管理页
        self.course_frame = self.create_course_tab()
        # 错题管理页
        self.mistake_frame = self.create_mistake_tab()
        # 学习分析页
        self.analytics_frame = self.create_analytics_tab()
        
        self.notebook.add(self.course_frame, text="课程进度")
        self.notebook.add(self.mistake_frame, text="错题管理")
        self.notebook.add(self.analytics_frame, text="学习分析")
        self.notebook.pack(expand=True, fill='both')

    def create_course_tab(self):
        """课程管理页完整实现"""
        frame = ttk.Frame(self.notebook)
        
        # 课程树形结构
        self.course_tree = ttk.Treeview(frame, columns=('status', 'date'), show='tree headings')
        self.course_tree.heading('#0', text='课程结构', anchor='w')
        self.course_tree.heading('status', text='完成状态')
        self.course_tree.heading('date', text='最后更新')
        self.course_tree.column('#0', width=250)
        self.course_tree.column('status', width=100)
        self.course_tree.column('date', width=150)
        self.course_tree.pack(fill='both', expand=True)
        
        # 右键菜单
        self.tree_menu = tk.Menu(self.root, tearoff=0)
        self.tree_menu.add_command(label="切换状态", command=self.toggle_status)
        self.course_tree.bind("<Button-3>", self.show_context_menu)
        
        return frame

    def show_context_menu(self, event):
        """显示课程树右键菜单"""
        item = self.course_tree.identify_row(event.y)
        if item:
            self.course_tree.selection_set(item)
            self.tree_menu.post(event.x_root, event.y_root)

    def create_mistake_tab(self):
        """错题管理页完整实现"""
        frame = ttk.Frame(self.notebook)
        
        # 错题列表
        columns = ("id", "课程", "章节", "错误类型", "掌握程度", "添加时间")
        self.mistake_tree = ttk.Treeview(
            frame, 
            columns=columns, 
            show='headings',
            selectmode='browse'
        )
        for col in columns:
            self.mistake_tree.heading(col, text=col)
            self.mistake_tree.column(col, width=120, anchor='center')
        self.mistake_tree.pack(side='left', fill='both', expand=True)
        self.mistake_tree.bind("<<TreeviewSelect>>", self.show_mistake_detail)
        
        # 右键菜单
        self.mistake_menu = tk.Menu(self.root, tearoff=0)
        self.mistake_menu.add_command(label="删除记录", command=self.delete_mistake)
        self.mistake_tree.bind("<Button-3>", self.show_mistake_menu)
        
        # 详情面板
        detail_frame = ttk.Frame(frame)
        self.detail_text = tk.Text(detail_frame, wrap=tk.WORD, height=15)
        self.detail_text.pack(fill='both', expand=True)
        
        # 图片预览
        self.image_label = ttk.Label(detail_frame)
        self.image_label.pack(pady=5)
        
        # 控制按钮
        ctrl_frame = ttk.Frame(detail_frame)
        ttk.Button(ctrl_frame, text="随机复习", command=self.random_review).pack(side='left', padx=5)
        ttk.Button(ctrl_frame, text="标记掌握", command=lambda: self.update_mastery(2)).pack(side='left', padx=5)
        ttk.Button(ctrl_frame, text="仍需复习", command=lambda: self.update_mastery(1)).pack(side='left', padx=5)
        ctrl_frame.pack(pady=5)
        
        # 录入表单
        form_frame = ttk.LabelFrame(frame, text="新增错题")
        self.create_mistake_form(form_frame)
        form_frame.pack(fill='x', pady=5)
        
        detail_frame.pack(side='right', fill='both', expand=True, padx=10)
        return frame

    def show_mistake_menu(self, event):
        """显示错题右键菜单"""
        item = self.mistake_tree.identify_row(event.y)
        if item:
            self.mistake_tree.selection_set(item)
            self.mistake_menu.post(event.x_root, event.y_root)

    def delete_mistake(self):
        """删除错题记录"""
        selected = self.mistake_tree.selection()
        if selected:
            item_id = self.mistake_tree.item(selected[0], "values")[0]
            self.cursor.execute("DELETE FROM mistakes WHERE id=?", (item_id,))
            self.conn.commit()
            self.mistake_tree.delete(selected[0])
            messagebox.showinfo("提示", "记录删除成功")

    def create_mistake_form(self, parent):
        """完整的错题录入表单"""
        form = ttk.Frame(parent)
        
        # 第一行
        row0 = ttk.Frame(form)
        ttk.Label(row0, text="课程类型:").pack(side='left')
        self.course_var = tk.StringVar()
        course_combo = ttk.Combobox(
            row0, 
            textvariable=self.course_var,
            values=["物化", "电工"],
            state="readonly",
            width=15
        )
        course_combo.pack(side='left', padx=5)
        course_combo.bind("<<ComboboxSelected>>", self.update_chapters)
        row0.pack(fill='x', pady=5)

        # 第二行
        row1 = ttk.Frame(form)
        ttk.Label(row1, text="章节选择:").pack(side='left')
        self.chapter_var = tk.StringVar()
        self.chapter_combo = ttk.Combobox(
            row1,
            textvariable=self.chapter_var,
            width=25
        )
        self.chapter_combo.pack(side='left', padx=5)
        row1.pack(fill='x', pady=5)

        # 第三行
        row2 = ttk.Frame(form)
        ttk.Label(row2, text="错误类型:").pack(side='left')
        self.error_var = tk.StringVar()
        error_combo = ttk.Combobox(
            row2,
            textvariable=self.error_var,
            values=["概念错误", "计算错误", "审题错误", "方法错误"],
            width=15
        )
        error_combo.pack(side='left', padx=5)
        
        ttk.Label(row2, text="自定义标签:").pack(side='left')
        self.tag_entry = ttk.Entry(row2, width=20)
        self.tag_entry.pack(side='left', padx=5)
        row2.pack(fill='x', pady=5)

        # 第四行
        row3 = ttk.Frame(form)
        ttk.Button(row3, text="上传题目图片", command=self.upload_image).pack(side='left', padx=5)
        self.image_path = ttk.Label(row3, text="未选择图片")
        self.image_path.pack(side='left', padx=5)
        row3.pack(fill='x', pady=5)

        # 第五行
        row4 = ttk.Frame(form)
        ttk.Button(row4, text="提交记录", command=self.submit_mistake).pack(side='right', padx=5)
        row4.pack(fill='x', pady=5)

        form.pack(fill='x', padx=10, pady=5)

    def create_analytics_tab(self):
        """学习分析页完整实现"""
        frame = ttk.Frame(self.notebook)
        
        # 推荐系统面板
        rec_frame = ttk.LabelFrame(frame, text="学习推荐")
        self.recommendation_list = ttk.Treeview(
            rec_frame, 
            columns=("类型", "推荐内容"), 
            show='headings',
            height=8
        )
        self.recommendation_list.heading("类型", text="类型")
        self.recommendation_list.heading("推荐内容", text="推荐内容")
        self.recommendation_list.column("类型", width=100)
        self.recommendation_list.column("推荐内容", width=300)
        self.recommendation_list.pack(fill='both', expand=True)
        rec_frame.pack(side='left', fill='both', expand=True, padx=5, pady=5)
        
        # 可视化面板
        fig_frame = ttk.LabelFrame(frame, text="学习分析")
        self.figure = Figure(figsize=(8, 6), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.figure, fig_frame)
        self.canvas.get_tk_widget().pack(fill='both', expand=True)
        
        # 控制面板
        ctrl_frame = ttk.Frame(fig_frame)
        ttk.Button(ctrl_frame, text="刷新图表", command=self.update_analytics).pack(side='left', padx=5)
        self.period_var = ttk.Combobox(
            ctrl_frame, 
            values=["最近一周", "最近一月", "全部数据"],
            state="readonly",
            width=10
        )
        self.period_var.current(0)
        self.period_var.pack(side='left', padx=5)
        ctrl_frame.pack(fill='x', pady=5)
        fig_frame.pack(side='right', fill='both', expand=True, padx=5, pady=5)
        
        return frame

    def load_initial_data(self):
        """完整的初始化流程"""
        try:
            # 物理化学课程结构
            pc_courses = [
                ("热力学第一定律", 1),
                ("热力学第二定律", 2),
                ("多组分系统热力学", 3),
                ("化学平衡", 4),
                ("相平衡", 5),
                ("化学动力学", 6),
                ("电化学", 7),
                ("界面现象", 8),
                ("胶体化学", 9)
            ]
            
            # 电工课程结构
            ee_courses = [
                ("电路的基本概念与基本定律", 1),
                ("电路的基本定律和分析方法", 2),
                ("正弦交流电路", 3),
                ("三相交流电路", 4),
                ("电路的暂态分析", 5),
                ("磁路与铁心线圈电路", 6),
                ("异步电动机", 7),
                ("继电接触控制系统", 8),
                ("半导体器件", 9),
                ("三极管和基本放大电路", 10),
                ("集成运放电路", 11),
                ("电子电路中的反馈", 12),
                ("直流稳压电源", 13)
            ]
            
            # 初始化物理化学课程
            parent = self.course_tree.insert("", "end", text="物化")
            for chapter, order in pc_courses:
                node = self.course_tree.insert(parent, "end", text=chapter)
                for res in ["ppt", "作业"]:
                    self.course_tree.insert(node, "end", text=res, values=("未开始", datetime.now().strftime("%Y-%m-%d")))
                    self.cursor.execute('''
                        INSERT OR IGNORE INTO courses 
                        (course_type, chapter, resource_type, sort_order)
                        VALUES (?, ?, ?, ?)
                    ''', ("物化", chapter, res, order))
            
            # 初始化电工课程
            parent = self.course_tree.insert("", "end", text="电工")
            for chapter, order in ee_courses:
                node = self.course_tree.insert(parent, "end", text=chapter)
                for res in ["ppt", "作业"]:
                    self.course_tree.insert(node, "end", text=res, values=("未开始", datetime.now().strftime("%Y-%m-%d")))
                    self.cursor.execute('''
                        INSERT OR IGNORE INTO courses 
                        (course_type, chapter, resource_type, sort_order)
                        VALUES (?, ?, ?, ?)
                    ''', ("电工", chapter, res, order))
            
            self.conn.commit()
            self.load_mistakes()
            self.update_analytics()
        except Exception as e:
            messagebox.showerror("初始化错误", f"数据加载失败: {str(e)}")

    def toggle_status(self):
        """可靠的课程状态切换"""
        selected = self.course_tree.selection()
        if selected:
            item = self.course_tree.item(selected[0])
            current_status = item['values'][0] if item['values'] else "未开始"
            new_status = "已完成" if current_status == "未开始" else "未开始"
            
            # 获取课程路径
            path = []
            current_item = selected[0]
            while current_item:
                path.insert(0, self.course_tree.item(current_item, "text"))
                current_item = self.course_tree.parent(current_item)
            
            if len(path) == 3:
                course_type, chapter, resource = path
                self.cursor.execute('''
                    UPDATE courses 
                    SET completed=?, last_updated=?
                    WHERE course_type=? AND chapter=? AND resource_type=?
                ''', (1 if new_status == "已完成" else 0, 
                     datetime.now().isoformat(),
                     course_type, chapter, resource))
                self.conn.commit()
                self.course_tree.item(selected[0], values=(new_status, datetime.now().strftime("%Y-%m-%d")))
            else:
                messagebox.showwarning("操作错误", "请选择具体的资源节点")

    def update_chapters(self, event=None):
        """动态更新章节选项"""
        course = self.course_var.get()
        self.chapter_combo['values'] = self.get_chapters(course)

    def get_chapters(self, course):
        """从数据库获取章节数据"""
        self.cursor.execute('''
            SELECT DISTINCT chapter 
            FROM courses 
            WHERE course_type=? 
            ORDER BY sort_order
        ''', (course,))
        return [row[0] for row in self.cursor.fetchall()]

    def upload_image(self):
        """图片上传功能"""
        path = filedialog.askopenfilename(
            title="选择题目图片",
            filetypes=[("图片文件", "*.png *.jpg *.jpeg")]
        )
        if path:
            try:
                with open(path, "rb") as f:
                    self.current_image = f.read()
                img = Image.open(BytesIO(self.current_image))
                img.thumbnail((300, 300))
                photo = ImageTk.PhotoImage(img)
                self.image_label.config(image=photo)
                self.image_label.image = photo
                self.image_path.config(text=os.path.basename(path))
            except Exception as e:
                messagebox.showerror("图片错误", f"图片加载失败: {str(e)}")

    def submit_mistake(self):
        """提交错题完整流程"""
        if not all([self.course_var.get(), self.chapter_var.get(), self.error_var.get()]):
            messagebox.showwarning("输入不完整", "请填写必填字段（课程、章节、错误类型）")
            return
        
        try:
            self.cursor.execute('''
                INSERT INTO mistakes (
                    course_type, 
                    chapter, 
                    question, 
                    image, 
                    error_type, 
                    tags, 
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                self.course_var.get(),
                self.chapter_var.get(),
                self.detail_text.get("1.0", "end-1c"),
                self.current_image,
                self.error_var.get(),
                self.tag_entry.get(),
                datetime.now().isoformat()
            ))
            self.conn.commit()
            self.load_mistakes()
            self.clear_form()
            messagebox.showinfo("成功", "错题记录已保存")
        except sqlite3.Error as e:
            messagebox.showerror("数据库错误", f"提交失败: {str(e)}")

    def clear_form(self):
        """清空输入表单"""
        self.course_var.set('')
        self.chapter_var.set('')
        self.error_var.set('')
        self.tag_entry.delete(0, tk.END)
        self.detail_text.delete(1.0, tk.END)
        self.current_image = None
        self.image_label.config(image=None)
        self.image_path.config(text="未选择图片")

    def load_mistakes(self):
        """加载错题数据到列表"""
        self.mistake_tree.delete(*self.mistake_tree.get_children())
        self.cursor.execute('''
            SELECT 
                id,
                course_type,
                chapter,
                error_type,
                CASE mastery_level
                    WHEN 2 THEN '已掌握'
                    WHEN 1 THEN '需复习'
                    ELSE '未学习' END,
                strftime('%Y-%m-%d %H:%M', created_at)
            FROM mistakes
            ORDER BY last_reviewed DESC
        ''')
        for row in self.cursor.fetchall():
            self.mistake_tree.insert("", "end", values=row)

    def show_mistake_detail(self, event):
        """显示错题详细信息"""
        selected = self.mistake_tree.selection()
        if selected:
            item_id = self.mistake_tree.item(selected[0], "values")[0]
            self.cursor.execute("SELECT * FROM mistakes WHERE id=?", (item_id,))
            mistake = self.cursor.fetchone()
            
            # 更新文本详情
            self.detail_text.delete(1.0, tk.END)
            self.detail_text.insert(tk.END, mistake[3])
            
            # 更新图片预览
            if mistake[4]:
                try:
                    img = Image.open(BytesIO(mistake[4]))
                    img.thumbnail((400, 400))
                    photo = ImageTk.PhotoImage(img)
                    self.image_label.config(image=photo)
                    self.image_label.image = photo
                except Exception as e:
                    messagebox.showerror("图片错误", f"无法加载图片: {str(e)}")
            else:
                self.image_label.config(image=None)

    def random_review(self):
        """智能随机复习功能"""
        self.cursor.execute('''
            SELECT * FROM mistakes 
            WHERE probability > 0 
            ORDER BY RANDOM() * probability DESC 
            LIMIT 1
        ''')
        mistake = self.cursor.fetchone()
        if mistake:
            self.show_review_window(mistake)
        else:
            messagebox.showinfo("提示", "当前没有需要复习的错题")

    def show_review_window(self, mistake):
        """显示复习窗口"""
        review_win = tk.Toplevel(self.root)
        review_win.title("错题复习")
        review_win.geometry("600x700")
        
        # 题目文本
        text_frame = ttk.Frame(review_win)
        text_scroll = ttk.Scrollbar(text_frame)
        text = tk.Text(
            text_frame, 
            wrap=tk.WORD, 
            yscrollcommand=text_scroll.set,
            height=10
        )
        text.insert(tk.END, mistake[3])
        text.config(state=tk.DISABLED)
        text.pack(side='left', fill='both', expand=True)
        text_scroll.config(command=text.yview)
        text_scroll.pack(side='right', fill='y')
        text_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # 题目图片
        if mistake[4]:
            img = Image.open(BytesIO(mistake[4]))
            img.thumbnail((500, 500))
            photo = ImageTk.PhotoImage(img)
            img_label = ttk.Label(review_win, image=photo)
            img_label.image = photo
            img_label.pack(pady=5)
        
        # 控制按钮
        btn_frame = ttk.Frame(review_win)
        ttk.Button(btn_frame, text="完全掌握", 
                 command=lambda: self.handle_review_result(mistake[0], 2, review_win)
                 ).pack(side='left', padx=10)
        ttk.Button(btn_frame, text="仍需复习", 
                 command=lambda: self.handle_review_result(mistake[0], 1, review_win)
                 ).pack(side='left', padx=10)
        btn_frame.pack(pady=10)

    def handle_review_result(self, mistake_id, mastery_level, window):
        """处理复习结果"""
        new_prob = max(0.1, 1.0 - (mastery_level-1)*0.4)
        self.cursor.execute('''
            UPDATE mistakes 
            SET mastery_level=?, probability=?, last_reviewed=?
            WHERE id=?
        ''', (mastery_level, new_prob, datetime.now().isoformat(), mistake_id))
        self.conn.commit()
        window.destroy()
        self.load_mistakes()

    def update_analytics(self):
        """更新学习分析数据"""
        self.figure.clear()
        
        # 获取分析周期
        period = self.period_var.get()
        if period == "最近一周":
            time_condition = "AND date(created_at) > date('now', '-7 days')"
        elif period == "最近一月":
            time_condition = "AND date(created_at) > date('now', '-1 month')"
        else:
            time_condition = ""
        
        # 错题类型分布
        ax1 = self.figure.add_subplot(221)
        self.cursor.execute(f'''
            SELECT error_type, COUNT(*) 
            FROM mistakes 
            WHERE 1=1 {time_condition}
            GROUP BY error_type
        ''')
        data = self.cursor.fetchall()
        if data:
            labels, sizes = zip(*data)
            ax1.pie(sizes, labels=labels, autopct='%1.1f%%')
            ax1.set_title('错题类型分布')
        else:
            ax1.text(0.5, 0.5, '暂无数据', ha='center', va='center')
        
        # 学习进度分析
        ax2 = self.figure.add_subplot(222)
        self.cursor.execute(f'''
            SELECT course_type, 
                   ROUND(100.0 * SUM(completed)/COUNT(*), 1) 
            FROM courses 
            GROUP BY course_type
        ''')
        data = self.cursor.fetchall()
        if data:
            courses, percents = zip(*data)
            ax2.bar(courses, percents)
            ax2.set_ylim(0, 100)
            ax2.set_title('课程完成进度')
            ax2.set_ylabel('完成百分比 (%)')
        
        # 生成学习推荐
        self.generate_recommendations(time_condition)
        
        self.figure.tight_layout()
        self.canvas.draw()

    def generate_recommendations(self, time_condition):
        """生成学习推荐"""
        self.recommendation_list.delete(*self.recommendation_list.get_children())
        
        # 推荐未完成课程
        self.cursor.execute('''
            SELECT course_type || ' - ' || chapter, resource_type
            FROM courses 
            WHERE completed=0
            ORDER BY sort_order
            LIMIT 3
        ''')
        for name, res_type in self.cursor.fetchall():
            self.recommendation_list.insert("", "end", values=(
                "未完成课程", 
                f"{name} ({res_type})"
            ))
        
        # 推荐高频错题章节
        self.cursor.execute(f'''
            SELECT course_type || ' - ' || chapter, COUNT(*) 
            FROM mistakes 
            WHERE 1=1 {time_condition}
            GROUP BY course_type, chapter 
            ORDER BY COUNT(*) DESC 
            LIMIT 2
        ''')
        for chapter, count in self.cursor.fetchall():
            self.recommendation_list.insert("", "end", values=(
                "高频错题", 
                f"{chapter} (错题数: {count})"
            ))

    def on_close(self):
        """关闭程序时的处理"""
        if messagebox.askokcancel("退出", "确定要退出程序吗？"):
            self.conn.close()
            self.root.destroy()

if __name__ == "__main__":
    StudyMasterPro()