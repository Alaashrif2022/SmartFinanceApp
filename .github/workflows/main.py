import calendar
import datetime
import json
import os
import sqlite3
import tkinter as tk
from tkinter import messagebox, ttk
import requests

# رابط قاعدة البيانات السحابية الخاص بك
FIREBASE_URL = "https://alaa-shrif-833ea-default-rtdb.firebaseio.com/"

DAYS_AR = {
    "Saturday": "السبت",
    "Sunday": "الأحد",
    "Monday": "الإثنين",
    "Tuesday": "الثلاثاء",
    "Wednesday": "الأربعاء",
    "Thursday": "الخميس",
    "Friday": "الجمعة",
}

def get_db_path():
    user_home = os.path.expanduser("~")
    selected_dir = os.path.join(user_home, "SmartFinanceData_Cloud")
    if not os.path.exists(selected_dir):
        try:
            os.makedirs(selected_dir, exist_ok=True)
        except Exception:
            selected_dir = os.getcwd()
    return os.path.join(selected_dir, "smart_finance_v2.db")

DB_PATH = get_db_path()

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS page_names (
            page_key TEXT PRIMARY KEY,
            custom_name TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            content TEXT,
            target_date TEXT,
            created_at TEXT,
            status TEXT DEFAULT 'قيد الانتظار'
        )
    """)
    try:
        cursor.execute("ALTER TABLE notes ADD COLUMN status TEXT DEFAULT 'قيد الانتظار'")
    except sqlite3.OperationalError:
        pass

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_memos (
            date TEXT PRIMARY KEY,
            content TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_schedule (
            date TEXT,
            row_index INTEGER,
            time_slot TEXT,
            name_val TEXT,
            amount_val REAL,
            PRIMARY KEY (date, row_index)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT,
            category TEXT,
            amount REAL,
            date TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS work_hours (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            check_in TEXT,
            check_out TEXT,
            total_hours REAL,
            attendees INTEGER,
            users INTEGER
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS accountant_entries (
            date TEXT PRIMARY KEY,
            amount REAL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fixed_expense_status (
            date TEXT,
            item_name TEXT,
            status TEXT,
            amount REAL,
            PRIMARY KEY (date, item_name)
        )
    """)
    
    cursor.execute("INSERT OR IGNORE INTO app_settings (key, value) VALUES ('app_name', 'برنامج الدخل - الإدارة المالية اليومية')")
    conn.commit()
    conn.close()

init_db()

class SmartFinanceApp:
    def __init__(self, root):
        self.root = root
        
        self.app_title = self.get_setting("app_name", "برنامج الدخل - الإدارة المالية اليومية")
        self.root.title(self.app_title)
        self.root.geometry("1200x780")
        
        self.root.resizable(True, True)
        self.root.state('zoomed')

        now = datetime.date.today()
        self.selected_year = tk.IntVar(value=now.year)
        self.selected_month = tk.IntVar(value=now.month)
        self.selected_day = tk.IntVar(value=now.day)
        
        self.inc_categories = ["العمل", "إبراهيم", "محمد", "مبيعات", "متفرقات"]
        self.exp_categories = ["البيت", "الصالون", "السيارة", "متفرقات"]
        self.fixed_categories = ["الكهرباء", "الماء", "الإيجار", "الإنترنت", "متفرقات"]

        self.setup_styles()
        self.create_top_bar()
        self.create_alert_banner()
        self.create_main_layout()
        self.show_page("work_hours")

    def sync_to_firebase(self, path, data):
        try:
            requests.put(f"{FIREBASE_URL}/{path}.json", json=data)
        except Exception:
            pass

    def get_setting(self, key, default_val):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM app_settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else default_val

    def set_setting(self, key, value):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO app_settings (key, value) VALUES (?, ?)", (key, value))
        conn.commit()
        conn.close()
        self.sync_to_firebase(f"settings/{key}", value)

    def get_page_name(self, page_key, default_name):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT custom_name FROM page_names WHERE page_key = ?", (page_key,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else default_name

    def set_page_name(self, page_key, name):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO page_names (page_key, custom_name) VALUES (?, ?)", (page_key, name))
        conn.commit()
        conn.close()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview.Heading", font=("Arial", 10, "bold"), background="#e2e8f0", relief="solid")
        style.configure("Treeview", font=("Arial", 10, "bold"), rowheight=28)

    def create_top_bar(self):
        self.top_bar = tk.Frame(self.root, bg="#0f172a", height=70)
        self.top_bar.pack(side="top", fill="x")

        title_frame = tk.Frame(self.top_bar, bg="#0f172a")
        title_frame.pack(side="right", padx=15, pady=5)

        self.lbl_title = tk.Label(title_frame, text=f"💎 {self.app_title}", font=("Arial", 13, "bold"), bg="#0f172a", fg="white")
        self.lbl_title.pack(side="top", anchor="e")

        change_title_f = tk.Frame(title_frame, bg="#0f172a")
        change_title_f.pack(side="bottom", anchor="e", pady=2)

        self.e_app_name = tk.Entry(change_title_f, font=("Arial", 9), width=22)
        self.e_app_name.insert(0, self.app_title)
        self.e_app_name.pack(side="right", padx=2)

        def update_app_name():
            new_title = self.e_app_name.get().strip()
            if not new_title:
                messagebox.showerror("خطأ", "أدخل اسماً للبرنامج أولاً")
                return
            self.app_title = new_title
            self.set_setting("app_name", new_title)
            self.root.title(new_title)
            self.lbl_title.config(text=f"💎 {new_title}")
            messagebox.showinfo("تم التحديث", "تم تغيير اسم البرنامج بنجاح!")

        tk.Button(change_title_f, text="تغيير اسم البرنامج", command=update_app_name, bg="#0284c7", fg="white", font=("Arial", 8, "bold")).pack(side="right", padx=2)

        control_frame = tk.Frame(self.top_bar, bg="#0f172a")
        control_frame.pack(side="left", padx=15)

        tk.Label(control_frame, text="السنة:", fg="white", bg="#0f172a", font=("Arial", 10, "bold")).pack(side="left", padx=2)
        self.year_combo = ttk.Combobox(control_frame, values=[str(y) for y in range(2024, 2031)], width=6, font=("Arial", 10))
        self.year_combo.set(str(self.selected_year.get()))
        self.year_combo.pack(side="left", padx=5)
        self.year_combo.bind("<<ComboboxSelected>>", lambda e: self.on_date_changed())

        tk.Label(control_frame, text="الشهر:", fg="white", bg="#0f172a", font=("Arial", 10, "bold")).pack(side="left", padx=2)
        self.month_combo = ttk.Combobox(control_frame, values=[str(m) for m in range(1, 13)], width=4, font=("Arial", 10))
        self.month_combo.set(str(self.selected_month.get()))
        self.month_combo.pack(side="left", padx=5)
        self.month_combo.bind("<<ComboboxSelected>>", lambda e: self.on_date_changed())

        self.days_container_frame = tk.Frame(self.root, bg="#1e293b", height=50)
        self.days_container_frame.pack(side="top", fill="x")
        self.update_days_bar()

    def create_alert_banner(self):
        self.alert_frame = tk.Frame(self.root, bg="#dc2626", height=32)
        self.lbl_alert = tk.Label(self.alert_frame, text="", font=("Arial", 10, "bold"), bg="#dc2626", fg="white")
        self.lbl_alert.pack(side="top", fill="x", pady=3)
        self.update_alert_banner()

    def update_alert_banner(self):
        today = datetime.date.today()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT title, target_date FROM notes WHERE status != 'مكتملة'")
        uncompleted = cursor.fetchall()
        conn.close()

        urgent_tasks = []
        warning_tasks = []

        for title, t_date_str in uncompleted:
            try:
                t_date = datetime.datetime.strptime(t_date_str, "%Y-%m-%d").date()
                diff_days = (t_date - today).days

                if diff_days <= 1:
                    urgent_tasks.append(f"🚨 {title} ({t_date_str})")
                elif diff_days <= 5:
                    warning_tasks.append(f"⚠️ {title} ({t_date_str})")
            except:
                pass

        total_alerts = urgent_tasks + warning_tasks

        if total_alerts:
            self.alert_frame.pack(side="top", fill="x", before=self.days_container_frame)
            if urgent_tasks:
                self.alert_frame.config(bg="#b91c1c")
                self.lbl_alert.config(bg="#b91c1c", text=f"🔔 تنبيه مهام عاجلة/غير منجزة ({len(total_alerts)}): " + "  |  ".join(urgent_tasks))
            else:
                self.alert_frame.config(bg="#ca8a04")
                self.lbl_alert.config(bg="#ca8a04", text=f"🔔 تنبيه مهام قريبة ({len(total_alerts)}): " + "  |  ".join(warning_tasks))
        else:
            self.alert_frame.pack_forget()

    def on_date_changed(self):
        self.update_days_bar()
        self.refresh_current_page()

    def update_days_bar(self):
        try:
            self.selected_year.set(int(self.year_combo.get()))
            self.selected_month.set(int(self.month_combo.get()))
        except:
            pass

        for widget in self.days_container_frame.winfo_children():
            widget.destroy()

        year = self.selected_year.get()
        month = self.selected_month.get()
        if month == 12:
            next_month_first = datetime.date(year + 1, 1, 1)
        else:
            next_month_first = datetime.date(year, month + 1, 1)
        days_in_month = (next_month_first - datetime.date(year, month, 1)).days

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        month_prefix = f"{year:04d}-{month:02d}"
        cursor.execute("SELECT date FROM daily_memos WHERE date LIKE ? AND content != ''", (f"{month_prefix}%",))
        memo_dates = {r[0] for r in cursor.fetchall()}
        conn.close()

        tk.Label(self.days_container_frame, text="أيام الشهر:", bg="#1e293b", fg="#38bdf8", font=("Arial", 10, "bold")).pack(side="left", padx=10)

        today_date = datetime.date.today()
        for d in range(1, days_in_month + 1):
            d_date = datetime.date(year, month, d)
            d_str = d_date.strftime("%Y-%m-%d")
            
            is_today = (d_date == today_date)
            is_selected = (d == self.selected_day.get())
            has_memo = (d_str in memo_dates)

            if is_selected:
                bg_color = "#2563eb"
                btn_text = f"✓ {d}" if has_memo else str(d)
            elif has_memo:
                bg_color = "#9333ea"
                btn_text = f"📝 {d}"
            elif is_today:
                bg_color = "#16a34a"
                btn_text = str(d)
            else:
                bg_color = "#334155"
                btn_text = str(d)
            
            btn_day = tk.Button(
                self.days_container_frame,
                text=btn_text,
                bg=bg_color,
                fg="white",
                font=("Arial", 9, "bold"),
                width=5,
                bd=1,
                command=lambda day=d: self.select_day(day)
            )
            btn_day.pack(side="left", padx=1, pady=8)

    def select_day(self, day):
        self.selected_day.set(day)
        self.update_days_bar()
        self.refresh_current_page()

    def get_current_date_str(self):
        return f"{self.selected_year.get():04d}-{self.selected_month.get():02d}-{self.selected_day.get():02d}"

    def get_active_categories(self, trans_type, base_list):
        month_str = f"{self.selected_year.get():04d}-{self.selected_month.get():02d}"
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        if trans_type == "مصروف ثابت":
            cursor.execute("SELECT DISTINCT item_name FROM fixed_expense_status WHERE date LIKE ? AND amount > 0", (f"{month_str}%",))
        else:
            cursor.execute("SELECT DISTINCT category FROM transactions WHERE type = ? AND date LIKE ? AND amount > 0", (trans_type, f"{month_str}%"))
        recorded_cats = [r[0] for r in cursor.fetchall()]
        conn.close()
        return list(dict.fromkeys(base_list + recorded_cats))

    def create_main_layout(self):
        main_container = tk.Frame(self.root)
        main_container.pack(fill="both", expand=True)

        self.sidebar = tk.Frame(main_container, bg="#0f172a", width=250)
        self.sidebar.pack(side="right", fill="y")

        self.content_container = tk.Frame(main_container, bg="#f8fafc")
        self.content_container.pack(side="left", fill="both", expand=True)

        self.canvas = tk.Canvas(self.content_container, bg="#f8fafc", highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.content_container, orient="vertical", command=self.canvas.yview)
        
        self.content_area = tk.Frame(self.canvas, bg="#f8fafc")

        self.content_area.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas_window = self.canvas.create_window((0, 0), window=self.content_area, anchor="nw")

        def on_canvas_configure(event):
            self.canvas.itemconfig(self.canvas_window, width=event.width)

        self.canvas.bind("<Configure>", on_canvas_configure)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.bind_mouse_scroll(self.root)
        self.refresh_sidebar_buttons()

    def refresh_sidebar_buttons(self):
        for widget in self.sidebar.winfo_children():
            widget.destroy()

        tk.Label(self.sidebar, text="📌 قائمة الأقسام والصفحات", bg="#0f172a", fg="#38bdf8", font=("Arial", 11, "bold")).pack(pady=10)

        default_names = {
            "work_hours": "⏱️ ساعات العمل والحضور",
            "income": "💵 الدخل اليومي",
            "expense": "🛍️ المصاريف اليومية",
            "fixed": "📌 المصاريف الثابتة والتذكير",
            "accountant": "💰 المحاسب والادخار المستقل",
            "schedule": "📅 جدول المتابعة اليومي",
            "notes": "📝 مذكرات والمهام",
            "ledger": "📖 السجل المالي والتقارير الشاملة"
        }

        for pk in default_names.keys():
            current_name = self.get_page_name(pk, default_names[pk])
            
            btn_frame = tk.Frame(self.sidebar, bg="#0f172a")
            btn_frame.pack(fill="x", pady=2, padx=5)

            btn = tk.Button(
                btn_frame,
                text=current_name,
                command=lambda p=pk: self.show_page(p),
                bg="#0f172a",
                fg="white",
                activebackground="#1e293b",
                activeforeground="white",
                font=("Arial", 10, "bold"),
                bd=0,
                anchor="e",
                padx=10,
                pady=10,
                cursor="hand2"
            )
            btn.pack(side="right", fill="x", expand=True)

            def rename_popup(key=pk, d_name=default_names[pk]):
                win = tk.Toplevel(self.root)
                win.title("تعديل اسم الصفحة")
                win.geometry("350x150")
                win.grab_set()

                tk.Label(win, text="أدخل الاسم الجديد للصفحة:", font=("Arial", 10, "bold")).pack(pady=10)
                e_name = tk.Entry(win, width=25, font=("Arial", 11))
                e_name.insert(0, self.get_page_name(key, d_name))
                e_name.pack(pady=5)

                def save_new_name():
                    new_n = e_name.get().strip()
                    if new_n:
                        self.set_page_name(key, new_n)
                        win.destroy()
                        self.refresh_sidebar_buttons()
                        self.refresh_current_page()

                tk.Button(win, text="حفظ التعديل", command=save_new_name, bg="#16a34a", fg="white", font=("Arial", 10, "bold")).pack(pady=10)

            tk.Button(
                btn_frame,
                text="✏️",
                command=rename_popup,
                bg="#1e293b",
                fg="#facc15",
                font=("Arial", 8),
                bd=0,
                cursor="hand2"
            ).pack(side="left", padx=2)

    def bind_mouse_scroll(self, widget):
        widget.bind("<MouseWheel>", self.on_mouse_wheel)
        widget.bind("<Button-4>", self.on_mouse_wheel)
        widget.bind("<Button-5>", self.on_mouse_wheel)
        for child in widget.winfo_children():
            self.bind_mouse_scroll(child)

    def on_mouse_wheel(self, event):
        if event.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(1, "units")
        else:
            move = -1 if event.delta > 0 else 1
            self.canvas.yview_scroll(move, "units")

    def show_page(self, page_key):
        self.current_page_key = page_key
        for widget in self.content_area.winfo_children():
            widget.destroy()

        self.update_alert_banner()

        if page_key == "work_hours":
            self.build_work_hours_page()
        elif page_key == "income":
            self.build_income_page()
        elif page_key == "expense":
            self.build_expense_page()
        elif page_key == "fixed":
            self.build_fixed_page()
        elif page_key == "accountant":
            self.build_accountant_page()
        elif page_key == "schedule":
            self.build_daily_schedule_page()
        elif page_key == "notes":
            self.build_notes_page()
        elif page_key == "ledger":
            self.build_ledger_page()

        self.root.after(100, lambda: self.bind_mouse_scroll(self.content_area))

    def refresh_current_page(self):
        if hasattr(self, "current_page_key"):
            self.show_page(self.current_page_key)

    # ==========================================
    # 1. ساعات العمل والحضور
    # ==========================================
    def build_work_hours_page(self):
        page_title = self.get_page_name("work_hours", "ساعات العمل والحضور")
        tk.Label(self.content_area, text=f"⏱️ {page_title} - تاريخ اليوم: {self.get_current_date_str()}", font=("Arial", 14, "bold"), fg="#1e293b", bg="#f8fafc").pack(anchor="w", padx=20, pady=15)

        form_f = tk.LabelFrame(self.content_area, text=" إدخال البيانات اليومية (حفظ تلقائي سحابي) ", font=("Arial", 11, "bold"), bg="#f8fafc")
        form_f.pack(fill="x", padx=20, pady=10)

        times_list = [f"{h:02d}:{m:02d}" for h in range(24) for m in (0, 30)]

        tk.Label(form_f, text="وقت الدخول:", bg="#f8fafc", font=("Arial", 11)).grid(row=0, column=0, padx=10, pady=10)
        self.e_in = ttk.Combobox(form_f, values=times_list, width=10, font=("Arial", 11))
        self.e_in.grid(row=0, column=1, padx=10, pady=10)

        tk.Label(form_f, text="وقت الخروج:", bg="#f8fafc", font=("Arial", 11)).grid(row=0, column=2, padx=10, pady=10)
        self.e_out = ttk.Combobox(form_f, values=times_list, width=10, font=("Arial", 11))
        self.e_out.grid(row=0, column=3, padx=10, pady=10)

        tk.Label(form_f, text="عدد الحضور:", bg="#f8fafc", font=("Arial", 11)).grid(row=1, column=0, padx=10, pady=10)
        self.e_attendees = tk.Entry(form_f, width=12, font=("Arial", 11))
        self.e_attendees.grid(row=1, column=1, padx=10, pady=10)

        tk.Label(form_f, text="عدد المستخدمين:", bg="#f8fafc", font=("Arial", 11)).grid(row=1, column=2, padx=10, pady=10)
        self.e_users = tk.Entry(form_f, width=12, font=("Arial", 11))
        self.e_users.grid(row=1, column=3, padx=10, pady=10)

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT check_in, check_out, attendees, users FROM work_hours WHERE date = ?", (self.get_current_date_str(),))
        row = cursor.fetchone()
        conn.close()

        if row:
            self.e_in.set(row[0] if row[0] is not None else "")
            self.e_out.set(row[1] if row[1] is not None else "")
            self.e_attendees.insert(0, str(row[2]) if row[2] is not None else "0")
            self.e_users.insert(0, str(row[3]) if row[3] is not None else "0")

        for widget in [self.e_in, self.e_out, self.e_attendees, self.e_users]:
            widget.bind("<FocusOut>", lambda e: self.save_work_data_auto())
            if isinstance(widget, ttk.Combobox):
                widget.bind("<<ComboboxSelected>>", lambda e: self.save_work_data_auto())

        btn_box = tk.Frame(self.content_area, bg="#f8fafc")
        btn_box.pack(pady=10)
        tk.Button(btn_box, text="🗑️ حذف / تفريغ بيانات اليوم", command=self.delete_work_data, bg="#dc2626", fg="white", font=("Arial", 11, "bold"), padx=15, pady=6).pack(side="left", padx=5)

        self.build_work_summary_section()

    def save_work_data_auto(self):
        try:
            cin = self.e_in.get().strip()
            cout = self.e_out.get().strip()
            
            hours = 0.0
            if cin and cout:
                t1 = datetime.datetime.strptime(cin, "%H:%M")
                t2 = datetime.datetime.strptime(cout, "%H:%M")
                hours = (t2 - t1).total_seconds() / 3600

            att = int(self.e_attendees.get() or 0)
            usr = int(self.e_users.get() or 0)
            d_str = self.get_current_date_str()

            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM work_hours WHERE date = ?", (d_str,))
            cursor.execute("INSERT INTO work_hours (date, check_in, check_out, total_hours, attendees, users) VALUES (?, ?, ?, ?, ?, ?)",
                           (d_str, cin, cout, hours, att, usr))
            conn.commit()
            conn.close()

            self.sync_to_firebase(f"work_hours/{d_str.replace('-', '_')}", {
                "check_in": cin, "check_out": cout, "total_hours": hours, "attendees": att, "users": usr
            })
        except Exception:
            pass

    def delete_work_data(self):
        if messagebox.askyesno("تأكيد الحذف", f"هل أنت متأكد من حذف تفاصيل ساعات العمل والحضور لليوم ({self.get_current_date_str()})؟"):
            d_str = self.get_current_date_str()
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM work_hours WHERE date = ?", (d_str,))
            conn.commit()
            conn.close()
            self.sync_to_firebase(f"work_hours/{d_str.replace('-', '_')}", None)
            self.refresh_current_page()

    def build_work_summary_section(self):
        summary_f = tk.LabelFrame(self.content_area, text=" الملخص والإحصائيات الشاملة ", font=("Arial", 11, "bold"), bg="#f8fafc")
        summary_f.pack(fill="x", padx=20, pady=15)

        d_str = self.get_current_date_str()
        year_month = d_str[:7]

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT total_hours, attendees, users FROM work_hours WHERE date = ?", (d_str,))
        day_row = cursor.fetchone()
        
        cursor.execute("SELECT SUM(total_hours), SUM(attendees), SUM(users) FROM work_hours WHERE date >= ? AND date <= ?", (f"{year_month}-01", d_str))
        cum_row = cursor.fetchone()
        conn.close()

        day_hrs = day_row[0] if day_row and day_row[0] is not None else 0.0
        day_att = day_row[1] if day_row and day_row[1] is not None else 0
        day_usr = day_row[2] if day_row and day_row[2] is not None else 0
        day_ratio = (day_usr / day_att * 100) if day_att > 0 else 0.0

        cum_hrs = cum_row[0] if cum_row and cum_row[0] is not None else 0.0
        cum_att = cum_row[1] if cum_row and cum_row[1] is not None else 0
        cum_usr = cum_row[2] if cum_row and cum_row[2] is not None else 0
        cum_ratio = (cum_usr / cum_att * 100) if cum_att > 0 else 0.0

        passed_days = self.selected_day.get()
        avg_hrs = cum_hrs / passed_days if passed_days > 0 else 0.0

        grid_f = tk.Frame(summary_f, bg="#f8fafc")
        grid_f.pack(fill="x", padx=10, pady=5)

        boxes_data = [
            ("ساعات العمل اليوم", f"{day_hrs:.2f} ساعة", "#e2e8f0", "#0f172a"),
            ("إجمالي ساعات الشهر", f"{cum_hrs:.2f} ساعة", "#dbeafe", "#1e40af"),
            ("متوسط الساعات اليومي", f"{avg_hrs:.2f} ساعة", "#ccfbf1", "#115e59"),
            ("حضور ومستخدمو اليوم", f"الحضور: {day_att}\nالمستخدمين: {day_usr} ({day_ratio:.1f}%)", "#fef08a", "#713f12"),
            ("إجمالي الشهر (حضور/مستخدمين)", f"الحضور: {cum_att}\nالمستخدمين: {cum_usr} ({cum_ratio:.1f}%)", "#fed7aa", "#9a3412")
        ]

        for idx, (title, val, bg_c, fg_c) in enumerate(boxes_data):
            box = tk.LabelFrame(grid_f, text=f" {title} ", font=("Arial", 10, "bold"), labelanchor="n", bg=bg_c, fg=fg_c, width=220, height=75)
            box.grid(row=idx//3, column=idx%3, padx=6, pady=6, sticky="nsew")
            box.pack_propagate(False)
            tk.Label(box, text=val, font=("Arial", 10, "bold"), bg=bg_c, fg=fg_c, justify="center").pack(expand=True)

    # ==========================================
    # 2. الدخل اليومي
    # ==========================================
    def build_income_page(self):
        page_title = self.get_page_name("income", "الدخل اليومي")
        tk.Label(self.content_area, text=f"💵 {page_title} - تاريخ اليوم: {self.get_current_date_str()}", font=("Arial", 14, "bold"), fg="#1e293b", bg="#f8fafc").pack(anchor="w", padx=20, pady=10)

        display_categories = self.get_active_categories("دخل", self.inc_categories)

        mgmt_f = tk.LabelFrame(self.content_area, text=" إدارة بنود الدخل ", font=("Arial", 10, "bold"), bg="#f8fafc")
        mgmt_f.pack(fill="x", padx=20, pady=5)

        tk.Label(mgmt_f, text="اختر البند:", bg="#f8fafc", font=("Arial", 10)).pack(side="left", padx=5)
        self.selected_inc_var = tk.StringVar(value=display_categories[0] if display_categories else "")
        self.inc_select_combo = ttk.Combobox(mgmt_f, textvariable=self.selected_inc_var, values=display_categories, width=15, state="readonly", font=("Arial", 10))
        self.inc_select_combo.pack(side="left", padx=5)

        tk.Label(mgmt_f, text="الاسم الجديد:", bg="#f8fafc", font=("Arial", 10)).pack(side="left", padx=5)
        self.e_rename_inc = tk.Entry(mgmt_f, width=12, font=("Arial", 10))
        self.e_rename_inc.pack(side="left", padx=5)

        def rename_item():
            old_name = self.selected_inc_var.get()
            new_name = self.e_rename_inc.get().strip()
            if not new_name: return
            if old_name in self.inc_categories:
                self.inc_categories[self.inc_categories.index(old_name)] = new_name
            
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("UPDATE transactions SET category = ? WHERE category = ? AND type = 'دخل'", (new_name, old_name))
            conn.commit()
            conn.close()
            self.refresh_current_page()

        tk.Button(mgmt_f, text="تعديل الاسم", command=rename_item, bg="#ca8a04", fg="white", font=("Arial", 9, "bold")).pack(side="left", padx=5)

        def delete_item():
            item = self.selected_inc_var.get()
            if messagebox.askyesno("تأكيد الحذف", f"هل أنت متأكد من حذف البند ({item})؟"):
                if item in self.inc_categories: self.inc_categories.remove(item)
                self.refresh_current_page()

        tk.Button(mgmt_f, text="حذف البند", command=delete_item, bg="#dc2626", fg="white", font=("Arial", 9, "bold")).pack(side="left", padx=5)

        form_f = tk.LabelFrame(self.content_area, text=" إدخال مبالغ الدخل لليوم (حفظ سحابي فوري) ", font=("Arial", 11, "bold"), bg="#f8fafc")
        form_f.pack(fill="x", padx=20, pady=5)

        d_str = self.get_current_date_str()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT category, amount FROM transactions WHERE type='دخل' AND date=?", (d_str,))
        saved_inc = {row[0]: row[1] for row in cursor.fetchall()}
        conn.close()

        self.inc_entries = []
        for i, cat in enumerate(display_categories):
            tk.Label(form_f, text=cat, font=("Arial", 11, "bold"), bg="#f8fafc").grid(row=i//3, column=(i%3)*2, sticky="w", padx=10, pady=4)
            ent = tk.Entry(form_f, width=12, font=("Arial", 11))
            if cat in saved_inc:
                ent.insert(0, str(saved_inc[cat]))
            ent.grid(row=i//3, column=(i%3)*2+1, padx=10, pady=4)
            ent.bind("<FocusOut>", lambda e: self.save_income_data_auto())
            self.inc_entries.append((cat, ent))

        btn_box = tk.Frame(self.content_area, bg="#f8fafc")
        btn_box.pack(pady=5)
        tk.Button(btn_box, text="🗑️ حذف دخل اليوم بالكامل", command=self.delete_income_data, bg="#dc2626", fg="white", font=("Arial", 11, "bold"), padx=15, pady=5).pack(side="left", padx=5)

        self.build_income_summary_section(display_categories)

    def save_income_data_auto(self):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        d_str = self.get_current_date_str()
        cursor.execute("DELETE FROM transactions WHERE date = ? AND type = 'دخل'", (d_str,))
        
        firebase_payload = {}
        for cat, ent in self.inc_entries:
            val_str = ent.get().strip()
            if val_str == "": continue
            try:
                val = float(val_str)
                cursor.execute("INSERT INTO transactions (type, category, amount, date) VALUES (?, ?, ?, ?)", ("دخل", cat, val, d_str))
                firebase_payload[cat] = val
            except: pass
        conn.commit()
        conn.close()
        self.sync_to_firebase(f"income/{d_str.replace('-', '_')}", firebase_payload)

    def delete_income_data(self):
        if messagebox.askyesno("تأكيد الحذف", f"هل أنت متأكد من حذف دخل اليوم ({self.get_current_date_str()})؟"):
            d_str = self.get_current_date_str()
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM transactions WHERE date = ? AND type = 'دخل'", (d_str,))
            conn.commit()
            conn.close()
            self.sync_to_firebase(f"income/{d_str.replace('-', '_')}", None)
            self.refresh_current_page()

    def build_income_summary_section(self, display_categories):
        summary_f = tk.LabelFrame(self.content_area, text=" تفصيل الدخل ", font=("Arial", 11, "bold"), bg="#f8fafc")
        summary_f.pack(fill="x", padx=20, pady=5)
        d_str = self.get_current_date_str()
        year_month = d_str[:7]
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        total_day_inc = 0.0
        total_cum_inc = 0.0
        item_results = []
        for cat in display_categories:
            cursor.execute("SELECT SUM(amount) FROM transactions WHERE type='دخل' AND category=? AND date=?", (cat, d_str))
            day_amt = cursor.fetchone()[0] or 0.0
            cursor.execute("SELECT SUM(amount) FROM transactions WHERE type='دخل' AND category=? AND date >= ? AND date <= ?", (cat, f"{year_month}-01", d_str))
            cum_amt = cursor.fetchone()[0] or 0.0
            total_day_inc += day_amt
            total_cum_inc += cum_amt
            item_results.append((cat, day_amt, cum_amt))
        conn.close()

        p10 = total_day_inc * 0.10
        p90 = total_day_inc * 0.90
        grid_f = tk.Frame(summary_f, bg="#f8fafc")
        grid_f.pack(fill="x", padx=10, pady=5)
        idx = 0
        for cat, day_amt, cum_amt in item_results:
            box = tk.LabelFrame(grid_f, text=f" {cat} ", font=("Arial", 11, "bold"), labelanchor="n", bg="#e2e8f0", fg="#0f172a", width=180, height=75)
            box.grid(row=idx//4, column=idx%4, padx=6, pady=6, sticky="nsew")
            box.pack_propagate(False)
            tk.Label(box, text=f"اليوم: {day_amt:.2f}\nالتراكمي: {cum_amt:.2f}", font=("Arial", 10, "bold"), bg="#e2e8f0", fg="#1e293b", justify="center").pack(expand=True)
            idx += 1

        res_f = tk.Frame(summary_f, bg="#f8fafc")
        res_f.pack(fill="x", padx=10, pady=5)
        b1 = tk.LabelFrame(res_f, text="إجمالي الدخل", font=("Arial", 11, "bold"), labelanchor="n", bg="#dbeafe", fg="#1e40af")
        b1.pack(side="left", fill="both", expand=True, padx=4)
        tk.Label(b1, text=f"اليوم: {total_day_inc:.2f}\nالتراكمي: {total_cum_inc:.2f}", font=("Arial", 10, "bold"), bg="#dbeafe", fg="#1e3a8a", justify="center").pack(pady=6)

        b2 = tk.LabelFrame(res_f, text="خصم 10% من الدخل", font=("Arial", 11, "bold"), labelanchor="n", bg="#fee2e2", fg="#991b1b")
        b2.pack(side="left", fill="both", expand=True, padx=4)
        tk.Label(b2, text=f"القيمة: {p10:.2f}", font=("Arial", 11, "bold"), bg="#fee2e2", fg="#7f1d1d", justify="center").pack(pady=12)

        b3 = tk.LabelFrame(res_f, text="الباقي (90% من الدخل)", font=("Arial", 11, "bold"), labelanchor="n", bg="#dcfce7", fg="#166534")
        b3.pack(side="left", fill="both", expand=True, padx=4)
        tk.Label(b3, text=f"القيمة: {p90:.2f}", font=("Arial", 11, "bold"), bg="#dcfce7", fg="#14532d", justify="center").pack(pady=12)

    # ==========================================
    # 3. المصاريف اليومية
    # ==========================================
    def build_expense_page(self):
        page_title = self.get_page_name("expense", "المصاريف اليومية")
        tk.Label(self.content_area, text=f"🛍️ {page_title} - تاريخ اليوم: {self.get_current_date_str()}", font=("Arial", 14, "bold"), fg="#1e293b", bg="#f8fafc").pack(anchor="w", padx=20, pady=10)

        display_categories = self.get_active_categories("مصروف", self.exp_categories)
        mgmt_f = tk.LabelFrame(self.content_area, text=" إدارة بنود المصاريف ", font=("Arial", 10, "bold"), bg="#f8fafc")
        mgmt_f.pack(fill="x", padx=20, pady=5)

        tk.Label(mgmt_f, text="اختر البند:", bg="#f8fafc", font=("Arial", 10)).pack(side="left", padx=5)
        self.selected_exp_var = tk.StringVar(value=display_categories[0] if display_categories else "")
        self.exp_select_combo = ttk.Combobox(mgmt_f, textvariable=self.selected_exp_var, values=display_categories, width=15, state="readonly", font=("Arial", 10))
        self.exp_select_combo.pack(side="left", padx=5)

        tk.Label(mgmt_f, text="الاسم الجديد:", bg="#f8fafc", font=("Arial", 10)).pack(side="left", padx=5)
        self.e_rename_exp = tk.Entry(mgmt_f, width=12, font=("Arial", 10))
        self.e_rename_exp.pack(side="left", padx=5)

        def rename_exp_item():
            old_name = self.selected_exp_var.get()
            new_name = self.e_rename_exp.get().strip()
            if not new_name: return
            if old_name in self.exp_categories: self.exp_categories[self.exp_categories.index(old_name)] = new_name
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("UPDATE transactions SET category = ? WHERE category = ? AND type = 'مصروف'", (new_name, old_name))
            conn.commit()
            conn.close()
            self.refresh_current_page()

        tk.Button(mgmt_f, text="تعديل الاسم", command=rename_exp_item, bg="#ca8a04", fg="white", font=("Arial", 9, "bold")).pack(side="left", padx=5)

        def delete_exp_item():
            item = self.selected_exp_var.get()
            if messagebox.askyesno("تأكيد الحذف", f"هل أنت متأكد من حذف البند ({item})؟"):
                if item in self.exp_categories: self.exp_categories.remove(item)
                self.refresh_current_page()

        tk.Button(mgmt_f, text="حذف البند", command=delete_exp_item, bg="#dc2626", fg="white", font=("Arial", 9, "bold")).pack(side="left", padx=5)

        form_f = tk.LabelFrame(self.content_area, text=" إدخال المصاريف اليومية (حفظ سحابي فوري) ", font=("Arial", 11, "bold"), bg="#f8fafc")
        form_f.pack(fill="x", padx=20, pady=5)

        d_str = self.get_current_date_str()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT category, amount FROM transactions WHERE type='مصروف' AND date=?", (d_str,))
        saved_exp = {row[0]: row[1] for row in cursor.fetchall()}
        conn.close()

        self.exp_entries = []
        for i, cat in enumerate(display_categories):
            tk.Label(form_f, text=cat, font=("Arial", 11, "bold"), bg="#f8fafc").grid(row=i//3, column=(i%3)*2, sticky="w", padx=10, pady=4)
            ent = tk.Entry(form_f, width=12, font=("Arial", 11))
            if cat in saved_exp:
                ent.insert(0, str(saved_exp[cat]))
            ent.grid(row=i//3, column=(i%3)*2+1, padx=10, pady=4)
            ent.bind("<FocusOut>", lambda e: self.save_expense_data_auto())
            self.exp_entries.append((cat, ent))

        btn_box = tk.Frame(self.content_area, bg="#f8fafc")
        btn_box.pack(pady=5)
        tk.Button(btn_box, text="🗑️ حذف مصاريف اليوم بالكامل", command=self.delete_expense_data, bg="#b91c1c", fg="white", font=("Arial", 11, "bold"), padx=15, pady=5).pack(side="left", padx=5)

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT SUM(amount) FROM transactions WHERE type='دخل' AND date=?", (d_str,))
        total_inc = cursor.fetchone()[0] or 0.0
        cursor.execute("SELECT SUM(amount) FROM transactions WHERE type='مصروف' AND date=?", (d_str,))
        total_exp = cursor.fetchone()[0] or 0.0
        conn.close()

        net_90 = total_inc * 0.90
        net_remaining = net_90 - total_exp

        status_box = tk.Frame(self.content_area, bg="#e0f2fe", bd=1, relief="solid")
        status_box.pack(fill="x", padx=20, pady=5)
        tk.Label(status_box, text=f"💰 صافي المتبقي النهائي بعد المصاريف: {net_remaining:.2f} (90% من الدخل: {net_90:.2f})", font=("Arial", 11, "bold"), fg="#0369a1", bg="#e0f2fe").pack(pady=6)

        self.build_expense_summary_section(display_categories)

    def save_expense_data_auto(self):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        d_str = self.get_current_date_str()
        cursor.execute("DELETE FROM transactions WHERE date = ? AND type = 'مصروف'", (d_str,))
        
        firebase_payload = {}
        for cat, ent in self.exp_entries:
            val_str = ent.get().strip()
            if val_str == "": continue
            try:
                val = float(val_str)
                cursor.execute("INSERT INTO transactions (type, category, amount, date) VALUES (?, ?, ?, ?)", ("مصروف", cat, val, d_str))
                firebase_payload[cat] = val
            except: pass
        conn.commit()
        conn.close()
        self.sync_to_firebase(f"expense/{d_str.replace('-', '_')}", firebase_payload)

    def delete_expense_data(self):
        if messagebox.askyesno("تأكيد الحذف", f"هل أنت متأكد من حذف مصاريف اليوم ({self.get_current_date_str()})؟"):
            d_str = self.get_current_date_str()
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM transactions WHERE date = ? AND type = 'مصروف'", (d_str,))
            conn.commit()
            conn.close()
            self.sync_to_firebase(f"expense/{d_str.replace('-', '_')}", None)
            self.refresh_current_page()

    def build_expense_summary_section(self, display_categories):
        summary_f = tk.LabelFrame(self.content_area, text=" تفصيل المصاريف ", font=("Arial", 11, "bold"), bg="#f8fafc")
        summary_f.pack(fill="x", padx=20, pady=5)
        d_str = self.get_current_date_str()
        year_month = d_str[:7]
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        total_day_exp = 0.0
        total_cum_exp = 0.0
        item_results = []
        for cat in display_categories:
            cursor.execute("SELECT SUM(amount) FROM transactions WHERE type='مصروف' AND category=? AND date=?", (cat, d_str))
            day_amt = cursor.fetchone()[0] or 0.0
            cursor.execute("SELECT SUM(amount) FROM transactions WHERE type='مصروف' AND category=? AND date >= ? AND date <= ?", (cat, f"{year_month}-01", d_str))
            cum_amt = cursor.fetchone()[0] or 0.0
            total_day_exp += day_amt
            total_cum_exp += cum_amt
            item_results.append((cat, day_amt, cum_amt))
        conn.close()

        grid_f = tk.Frame(summary_f, bg="#f8fafc")
        grid_f.pack(fill="x", padx=10, pady=5)
        idx = 0
        for cat, day_amt, cum_amt in item_results:
            box = tk.LabelFrame(grid_f, text=f" {cat} ", font=("Arial", 11, "bold"), labelanchor="n", bg="#fee2e2", fg="#7f1d1d", width=200, height=75)
            box.grid(row=idx//4, column=idx%4, padx=6, pady=6, sticky="nsew")
            box.pack_propagate(False)
            tk.Label(box, text=f"اليوم: {day_amt:.2f}\nالتراكمي: {cum_amt:.2f}", font=("Arial", 10, "bold"), bg="#fee2e2", fg="#991b1b", justify="center").pack(expand=True)
            idx += 1

        res_f = tk.Frame(summary_f, bg="#f8fafc")
        res_f.pack(fill="x", padx=10, pady=5)
        b1 = tk.LabelFrame(res_f, text="إجمالي المصاريف", font=("Arial", 11, "bold"), labelanchor="n", bg="#fef08a", fg="#713f12")
        b1.pack(side="left", fill="both", expand=True, padx=4)
        tk.Label(b1, text=f"اليوم: {total_day_exp:.2f}\nالتراكمي: {total_cum_exp:.2f}", font=("Arial", 10, "bold"), bg="#fef08a", fg="#854d0e", justify="center").pack(pady=10)

    # ==========================================
    # 4. المصاريف الثابتة والتذكير
    # ==========================================
    def build_fixed_page(self):
        page_title = self.get_page_name("fixed", "المصاريف الثابتة والتذكير")
        tk.Label(self.content_area, text=f"📌 {page_title} - تاريخ اليوم: {self.get_current_date_str()}", font=("Arial", 14, "bold"), fg="#1e293b", bg="#f8fafc").pack(anchor="w", padx=20, pady=10)

        display_categories = self.get_active_categories("مصروف ثابت", self.fixed_categories)
        mgmt_f = tk.LabelFrame(self.content_area, text=" إدارة بنود المصاريف الثابتة ", font=("Arial", 10, "bold"), bg="#f8fafc")
        mgmt_f.pack(fill="x", padx=20, pady=5)

        tk.Label(mgmt_f, text="اختر البند:", bg="#f8fafc", font=("Arial", 10)).pack(side="left", padx=5)
        self.selected_fixed_var = tk.StringVar(value=display_categories[0] if display_categories else "")
        self.fixed_select_combo = ttk.Combobox(mgmt_f, textvariable=self.selected_fixed_var, values=display_categories, width=15, state="readonly", font=("Arial", 10))
        self.fixed_select_combo.pack(side="left", padx=5)

        tk.Label(mgmt_f, text="الاسم الجديد:", bg="#f8fafc", font=("Arial", 10)).pack(side="left", padx=5)
        self.e_rename_fixed = tk.Entry(mgmt_f, width=12, font=("Arial", 10))
        self.e_rename_fixed.pack(side="left", padx=5)

        def rename_fixed_item():
            old_name = self.selected_fixed_var.get()
            new_name = self.e_rename_fixed.get().strip()
            if not new_name: return
            if old_name in self.fixed_categories: self.fixed_categories[self.fixed_categories.index(old_name)] = new_name
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("UPDATE fixed_expense_status SET item_name = ? WHERE item_name = ?", (new_name, old_name))
            cursor.execute("UPDATE transactions SET category = ? WHERE category = ? AND type = 'مصروف ثابت'", (new_name, old_name))
            conn.commit()
            conn.close()
            self.refresh_current_page()

        tk.Button(mgmt_f, text="تعديل الاسم", command=rename_fixed_item, bg="#ca8a04", fg="white", font=("Arial", 9, "bold")).pack(side="left", padx=5)

        def delete_fixed_item():
            item = self.selected_fixed_var.get()
            if messagebox.askyesno("تأكيد الحذف", f"هل أنت متأكد من حذف البند ({item})؟"):
                if item in self.fixed_categories: self.fixed_categories.remove(item)
                self.refresh_current_page()

        tk.Button(mgmt_f, text="حذف البند", command=delete_fixed_item, bg="#dc2626", fg="white", font=("Arial", 9, "bold")).pack(side="left", padx=5)

        f = tk.LabelFrame(self.content_area, text=" تفاصيل وحالات المصاريف الثابتة (حفظ سحابي فوري) ", font=("Arial", 11, "bold"), bg="#f8fafc")
        f.pack(fill="x", padx=20, pady=5)

        self.fixed_widgets = []
        d_str = self.get_current_date_str()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        for i, cat in enumerate(display_categories):
            cursor.execute("SELECT status, amount FROM fixed_expense_status WHERE date = ? AND item_name = ?", (d_str, cat))
            row = cursor.fetchone()
            st_val = row[0] if row else "لم يتم السداد"
            amt_val = str(row[1]) if row and row[1] is not None else "0"

            row_f = tk.Frame(f, bg="#f8fafc", pady=4)
            row_f.pack(fill="x")
            tk.Label(row_f, text=cat, width=15, anchor="w", font=("Arial", 11, "bold"), bg="#f8fafc").pack(side="left", padx=5)
            
            ent = tk.Entry(row_f, width=10, font=("Arial", 11))
            ent.insert(0, amt_val)
            ent.pack(side="left", padx=5)

            status_var = tk.StringVar(value=st_val)
            cb = ttk.Combobox(row_f, textvariable=status_var, values=["لم يتم السداد", "تم السداد"], width=15, state="readonly", font=("Arial", 10))
            cb.pack(side="left", padx=5)

            ent.bind("<FocusOut>", lambda e: self.save_fixed_data_auto())
            cb.bind("<<ComboboxSelected>>", lambda e: self.save_fixed_data_auto())

            self.fixed_widgets.append((cat, ent, status_var))
        conn.close()

        btn_box = tk.Frame(self.content_area, bg="#f8fafc")
        btn_box.pack(pady=10)
        tk.Button(btn_box, text="🗑️ تفريغ / حذف حالة اليوم", command=self.delete_fixed_data, bg="#dc2626", fg="white", font=("Arial", 11, "bold"), padx=15, pady=6).pack(side="left", padx=5)

    def save_fixed_data_auto(self):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        d_str = self.get_current_date_str()
        cursor.execute("DELETE FROM transactions WHERE date = ? AND type = 'مصروف ثابت'", (d_str,))
        
        firebase_payload = {}
        for cat, ent, var in self.fixed_widgets:
            val_str = ent.get().strip()
            if val_str == "": continue
            try:
                val = float(val_str)
                cursor.execute("INSERT OR REPLACE INTO fixed_expense_status (date, item_name, status, amount) VALUES (?, ?, ?, ?)", (d_str, cat, var.get(), val))
                if var.get() == "تم السداد" and val > 0:
                    cursor.execute("INSERT INTO transactions (type, category, amount, date) VALUES (?, ?, ?, ?)", ("مصروف ثابت", cat, val, d_str))
                firebase_payload[cat] = {"amount": val, "status": var.get()}
            except: pass

        conn.commit()
        conn.close()
        self.sync_to_firebase(f"fixed_expenses/{d_str.replace('-', '_')}", firebase_payload)

    def delete_fixed_data(self):
        if messagebox.askyesno("تأكيد الحذف", f"هل أنت متأكد من تفريغ حالات المصاريف الثابتة لليوم ({self.get_current_date_str()})؟"):
            d_str = self.get_current_date_str()
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM fixed_expense_status WHERE date = ?", (d_str,))
            cursor.execute("DELETE FROM transactions WHERE date = ? AND type = 'مصروف ثابت'", (d_str,))
            conn.commit()
            conn.close()
            self.sync_to_firebase(f"fixed_expenses/{d_str.replace('-', '_')}", None)
            self.refresh_current_page()

    # ==========================================
    # 5. المحاسب والادخار المستقل
    # ==========================================
    def build_accountant_page(self):
        page_title = self.get_page_name("accountant", "المحاسب والادخار المستقل")
        tk.Label(self.content_area, text=f"💰 {page_title} - تاريخ اليوم: {self.get_current_date_str()}", font=("Arial", 14, "bold"), fg="#1e293b", bg="#f8fafc").pack(anchor="w", padx=20, pady=10)

        input_f = tk.Frame(self.content_area, bg="#f8fafc")
        input_f.pack(fill="x", padx=20, pady=5)

        acc_f = tk.LabelFrame(input_f, text=" إدخال قيمة المحاسب (حفظ سحابي) ", font=("Arial", 11, "bold"), bg="#f8fafc")
        acc_f.pack(side="left", fill="both", expand=True, padx=5)

        tk.Label(acc_f, text="القيمة:", bg="#f8fafc", font=("Arial", 10, "bold")).pack(side="left", padx=5, pady=8)
        self.e_acc = tk.Entry(acc_f, width=10, font=("Arial", 10))
        self.e_acc.pack(side="left", padx=5)

        d_str = self.get_current_date_str()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT amount FROM accountant_entries WHERE date=?", (d_str,))
        row_acc = cursor.fetchone()
        if row_acc and row_acc[0] is not None:
            self.e_acc.insert(0, str(row_acc[0]))

        def save_accountant_auto(event=None):
            val_str = self.e_acc.get().strip()
            if val_str == "": return
            try:
                val = float(val_str)
                conn_db = sqlite3.connect(DB_PATH)
                cur = conn_db.cursor()
                cur.execute("INSERT OR REPLACE INTO accountant_entries (date, amount) VALUES (?, ?)", (d_str, val))
                conn_db.commit()
                conn_db.close()
                self.sync_to_firebase(f"accountant/{d_str.replace('-', '_')}", val)
            except: pass

        self.e_acc.bind("<FocusOut>", save_accountant_auto)

        sav_f = tk.LabelFrame(input_f, text=" 🏦 الادخار اليومي (مستقل) ", font=("Arial", 11, "bold"), bg="#f8fafc")
        sav_f.pack(side="left", fill="both", expand=True, padx=5)

        tk.Label(sav_f, text="المبلغ:", bg="#f8fafc", font=("Arial", 10, "bold")).pack(side="left", padx=5, pady=8)
        self.e_sav = tk.Entry(sav_f, width=10, font=("Arial", 10))
        
        cursor.execute("SELECT category, amount FROM transactions WHERE type='ادخار' AND date=?", (d_str,))
        saved_sav = {row[0]: row[1] for row in cursor.fetchall()}
        if "إيداع بالادخار" in saved_sav:
            self.e_sav.insert(0, str(saved_sav["إيداع بالادخار"]))
        elif "سحب من الادخار" in saved_sav:
            self.e_sav.insert(0, str(saved_sav["سحب من الادخار"]))

        self.e_sav.pack(side="left", padx=5)

        def do_saving(action):
            val_str = self.e_sav.get().strip()
            if val_str == "": return
            try:
                amt = float(val_str)
                conn_db = sqlite3.connect(DB_PATH)
                cur = conn_db.cursor()
                cur.execute("DELETE FROM transactions WHERE type='ادخار' AND date=?", (d_str,))
                cur.execute("INSERT INTO transactions (type, category, amount, date) VALUES (?, ?, ?, ?)", ("ادخار", action, amt, d_str))
                conn_db.commit()
                conn_db.close()
                self.sync_to_firebase(f"savings/{d_str.replace('-', '_')}", {"action": action, "amount": amt})
                self.refresh_current_page()
            except: messagebox.showerror("خطأ", "أدخل مبلغاً صحيحاً")

        tk.Button(sav_f, text="+ إيداع", command=lambda: do_saving("إيداع بالادخار"), bg="green", fg="white", font=("Arial", 9, "bold")).pack(side="left", padx=3)
        tk.Button(sav_f, text="- سحب", command=lambda: do_saving("سحب من الادخار"), bg="orange", fg="white", font=("Arial", 9, "bold")).pack(side="left", padx=3)
        conn.close()

        selected_month_year_str = f"{self.selected_year.get():04d}-{self.selected_month.get():02d}"
        table_f = tk.LabelFrame(self.content_area, text=f" 📋 سجل المحاسب والادخار للشهر: ({selected_month_year_str}) ", font=("Arial", 11, "bold"), bg="#f8fafc")
        table_f.pack(fill="x", padx=20, pady=10)

        columns = ("date", "accountant", "sav_deposit", "sav_withdraw", "sav_net")
        self.acc_tree = ttk.Treeview(table_f, columns=columns, show="headings", height=10)
        for col, txt, w in zip(columns, ["التاريخ", "قيمة المحاسب", "إيداع ادخار (+)", "سحب ادخار (-)", "صافي الادخار"], [130, 130, 130, 130, 150]):
            self.acc_tree.heading(col, text=txt)
            self.acc_tree.column(col, width=w, anchor="center")
        self.acc_tree.pack(side="left", fill="both", expand=True, padx=10, pady=5)

        scroll_acc = ttk.Scrollbar(table_f, orient="vertical", command=self.acc_tree.yview)
        scroll_acc.pack(side="right", fill="y", pady=5)
        self.acc_tree.configure(yscrollcommand=scroll_acc.set)
        self.load_accountant_and_savings_table(selected_month_year_str)

        btn_acc_del = tk.Frame(self.content_area, bg="#f8fafc")
        btn_acc_del.pack(fill="x", padx=20, pady=2)

        def delete_selected_acc_row():
            selected = self.acc_tree.selection()
            if not selected:
                messagebox.showwarning("تنبيه", "حدد يوماً من الجدول أولاً.")
                return
            row_date = self.acc_tree.item(selected[0], "values")[0]
            if messagebox.askyesno("تأكيد الحذف", f"هل أنت متأكد من حذف السجل لليوم ({row_date})؟"):
                conn_db = sqlite3.connect(DB_PATH)
                cur = conn_db.cursor()
                cur.execute("DELETE FROM accountant_entries WHERE date=?", (row_date,))
                cur.execute("DELETE FROM transactions WHERE type='ادخار' AND date=?", (row_date,))
                conn_db.commit()
                conn_db.close()
                self.sync_to_firebase(f"accountant/{row_date.replace('-', '_')}", None)
                self.sync_to_firebase(f"savings/{row_date.replace('-', '_')}", None)
                self.refresh_current_page()

        tk.Button(btn_acc_del, text="🗑️ حذف السجل اليومي المحدد", command=delete_selected_acc_row, bg="#dc2626", fg="white", font=("Arial", 10, "bold")).pack(side="right", padx=5)
        self.build_accountant_summary_box(selected_month_year_str)

    def load_accountant_and_savings_table(self, month_str):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT date FROM accountant_entries WHERE date LIKE ?", (f"{month_str}%",))
        dates_acc = [r[0] for r in cursor.fetchall()]
        cursor.execute("SELECT date FROM transactions WHERE type='ادخار' AND date LIKE ?", (f"{month_str}%",))
        dates_sav = [r[0] for r in cursor.fetchall()]
        all_dates = sorted(list(set(dates_acc + dates_sav)), reverse=True)

        for d in all_dates:
            cursor.execute("SELECT amount FROM accountant_entries WHERE date=?", (d,))
            r_acc = cursor.fetchone()
            acc_val = r_acc[0] if r_acc and r_acc[0] is not None else 0.0
            cursor.execute("SELECT SUM(amount) FROM transactions WHERE type='ادخار' AND category='إيداع بالادخار' AND date=?", (d,))
            dep_val = cursor.fetchone()[0] or 0.0
            cursor.execute("SELECT SUM(amount) FROM transactions WHERE type='ادخار' AND category='سحب من الادخار' AND date=?", (d,))
            wit_val = cursor.fetchone()[0] or 0.0
            net_sav = dep_val - wit_val
            self.acc_tree.insert("", "end", values=(d, f"{acc_val:.2f}", f"{dep_val:.2f}", f"{wit_val:.2f}", f"{net_sav:.2f}"))
        conn.close()

    def build_accountant_summary_box(self, year_month):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        d_str = self.get_current_date_str()
        year_str = str(self.selected_year.get())

        cursor.execute("SELECT amount FROM accountant_entries WHERE date=?", (d_str,))
        acc_day = (cursor.fetchone() or [0.0])[0] or 0.0
        cursor.execute("SELECT SUM(amount) FROM accountant_entries WHERE date LIKE ?", (f"{year_month}%",))
        acc_month = (cursor.fetchone() or [0.0])[0] or 0.0
        cursor.execute("SELECT SUM(amount) FROM accountant_entries WHERE date LIKE ?", (f"{year_str}%",))
        acc_year = (cursor.fetchone() or [0.0])[0] or 0.0

        cursor.execute("SELECT SUM(amount) FROM transactions WHERE type='ادخار' AND category='إيداع بالادخار' AND date=?", (d_str,))
        s_dep_day = cursor.fetchone()[0] or 0.0
        cursor.execute("SELECT SUM(amount) FROM transactions WHERE type='ادخار' AND category='سحب من الادخار' AND date=?", (d_str,))
        s_wit_day = cursor.fetchone()[0] or 0.0
        sav_day_net = s_dep_day - s_wit_day

        cursor.execute("SELECT SUM(amount) FROM transactions WHERE type='ادخار' AND category='إيداع بالادخار' AND date LIKE ?", (f"{year_month}%",))
        s_dep_m = cursor.fetchone()[0] or 0.0
        cursor.execute("SELECT SUM(amount) FROM transactions WHERE type='ادخار' AND category='سحب من الادخار' AND date LIKE ?", (f"{year_month}%",))
        s_wit_m = cursor.fetchone()[0] or 0.0
        sav_month_net = s_dep_m - s_wit_m

        cursor.execute("SELECT SUM(amount) FROM transactions WHERE type='ادخار' AND category='إيداع بالادخار' AND date LIKE ?", (f"{year_str}%",))
        s_dep_y = cursor.fetchone()[0] or 0.0
        cursor.execute("SELECT SUM(amount) FROM transactions WHERE type='ادخار' AND category='سحب من الادخار' AND date LIKE ?", (f"{year_str}%",))
        s_wit_y = cursor.fetchone()[0] or 0.0
        sav_year_net = s_dep_y - s_wit_y
        conn.close()

        summary_bottom_f = tk.LabelFrame(self.content_area, text=" الإجماليات المستقلة ", font=("Arial", 11, "bold"), bg="#f8fafc")
        summary_bottom_f.pack(fill="x", padx=20, pady=10)
        res_grid = tk.Frame(summary_bottom_f, bg="#f8fafc")
        res_grid.pack(fill="x", padx=10, pady=5)

        box_acc = tk.LabelFrame(res_grid, text=" إجماليات المحاسب ", font=("Arial", 11, "bold"), labelanchor="n", bg="#ccfbf1", fg="#115e59", width=450, height=85)
        box_acc.pack(side="left", fill="both", expand=True, padx=5)
        box_acc.pack_propagate(False)
        tk.Label(box_acc, text=f"اليوم: {acc_day:.2f} | الشهر: {acc_month:.2f}\nالسنة: {acc_year:.2f}", font=("Arial", 10, "bold"), bg="#ccfbf1", fg="#134e4a", justify="center").pack(expand=True)

        box_sav_sum = tk.LabelFrame(res_grid, text=" إجماليات الادخار ", font=("Arial", 11, "bold"), labelanchor="n", bg="#fef08a", fg="#854d0e", width=450, height=85)
        box_sav_sum.pack(side="left", fill="both", expand=True, padx=5)
        box_sav_sum.pack_propagate(False)
        tk.Label(box_sav_sum, text=f"اليوم: {sav_day_net:.2f} | الشهر: {sav_month_net:.2f}\nالسنة: {sav_year_net:.2f}", font=("Arial", 10, "bold"), bg="#fef08a", fg="#713f12", justify="center").pack(expand=True)

    # ==========================================
    # 6. جدول المتابعة اليومي
    # ==========================================
    def build_daily_schedule_page(self):
        page_title = self.get_page_name("schedule", "جدول المتابعة اليومي")
        current_d_str = self.get_current_date_str()

        sticky_top_container = tk.Frame(self.content_area, bg="#f8fafc")
        sticky_top_container.pack(fill="x", padx=20, pady=(10, 0), side="top")

        tk.Label(sticky_top_container, text=f"📅 {page_title} - تاريخ اليوم: {current_d_str}", font=("Arial", 14, "bold"), fg="#1e293b", bg="#f8fafc").pack(anchor="w", pady=(0, 5))

        buttons_bar = tk.Frame(sticky_top_container, bg="#e2e8f0", bd=1, relief="solid")
        buttons_bar.pack(fill="x", pady=2)
        btn_inner = tk.Frame(buttons_bar, bg="#e2e8f0")
        btn_inner.pack(fill="x", padx=10, pady=6)
        tk.Button(btn_inner, text="🗑️ تفريغ الجدول اليومي", command=self.clear_daily_schedule, bg="#dc2626", fg="white", font=("Arial", 11, "bold"), padx=15, pady=4).pack(side="left", padx=5)

        header_frame = tk.Frame(sticky_top_container, bg="#0f172a", height=40)
        header_frame.pack(fill="x", pady=(5, 0))
        header_frame.pack_propagate(False)

        tk.Label(header_frame, text="الساعة (24h)", width=22, bg="#0f172a", fg="white", font=("Arial", 11, "bold"), anchor="center").pack(side="left", padx=5)
        self.lbl_names_count = tk.Label(header_frame, text="الاسم (المسجلون: 0)", width=35, bg="#0f172a", fg="white", font=("Arial", 11, "bold"), anchor="center")
        self.lbl_names_count.pack(side="left", padx=5)
        self.lbl_amount_sum = tk.Label(header_frame, text="المجموع: 0.00", width=25, bg="#0f172a", fg="#facc15", font=("Arial", 11, "bold"), anchor="center")
        self.lbl_amount_sum.pack(side="left", padx=5)

        time_slots = []
        h, m = 7, 0
        while not (h == 0 and m == 0):
            time_slots.append(f"{h:02d}:{m:02d}")
            m += 30
            if m == 60:
                h += 1; m = 0
                if h == 24: h = 0
        h, m = 0, 0
        while not (h == 4 and m == 30):
            time_slots.append(f"{h:02d}:{m:02d}")
            m += 30
            if m == 60:
                h += 1; m = 0

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT row_index, name_val, amount_val FROM daily_schedule WHERE date = ?", (current_d_str,))
        saved_data = {row[0]: (row[1], row[2]) for row in cursor.fetchall()}
        conn.close()

        scroll_container = tk.Frame(self.content_area, bg="#f8fafc")
        scroll_container.pack(fill="both", expand=True, padx=20, pady=(0, 10), side="top")

        sched_canvas = tk.Canvas(scroll_container, bg="#ffffff", highlightthickness=1, highlightbackground="#cbd5e1", height=500)
        sched_scrollbar = ttk.Scrollbar(scroll_container, orient="vertical", command=sched_canvas.yview)
        rows_frame = tk.Frame(sched_canvas, bg="#ffffff")
        rows_frame.bind("<Configure>", lambda e: sched_canvas.configure(scrollregion=sched_canvas.bbox("all")))
        sched_window = sched_canvas.create_window((0, 0), window=rows_frame, anchor="nw")
        sched_canvas.bind("<Configure>", lambda event: sched_canvas.itemconfig(sched_window, width=event.width))
        sched_canvas.configure(yscrollcommand=sched_scrollbar.set)
        sched_canvas.pack(side="left", fill="both", expand=True)
        sched_scrollbar.pack(side="right", fill="y")

        self.schedule_entries = []
        for idx, t_slot in enumerate(time_slots):
            r_bg = "#f1f5f9" if idx % 2 == 0 else "#ffffff"
            row_f = tk.Frame(rows_frame, bg=r_bg, height=35)
            row_f.pack(fill="x", pady=1)
            row_f.pack_propagate(False)

            tk.Label(row_f, text=t_slot, width=22, bg=r_bg, fg="#0f172a", font=("Arial", 10, "bold"), anchor="center").pack(side="left", padx=5)
            e_name = tk.Entry(row_f, width=32, font=("Arial", 10))
            e_name.pack(side="left", padx=10, pady=5)
            e_amount = tk.Entry(row_f, width=20, font=("Arial", 10))
            e_amount.pack(side="left", padx=10, pady=5)

            if idx in saved_data:
                n_val, a_val = saved_data[idx]
                if n_val: e_name.insert(0, n_val)
                if a_val: e_amount.insert(0, str(a_val))

            e_name.bind("<KeyRelease>", lambda e: self.update_schedule_totals(time_slots))
            e_amount.bind("<KeyRelease>", lambda e: self.update_schedule_totals(time_slots))
            e_name.bind("<FocusOut>", lambda e: self.save_daily_schedule_auto())
            e_amount.bind("<FocusOut>", lambda e: self.save_daily_schedule_auto())

            self.schedule_entries.append((t_slot, e_name, e_amount))

        self.update_schedule_totals(time_slots)

    def update_schedule_totals(self, time_slots):
        total_sum = 0.0
        names_count = 0
        for _, e_name, e_amount in self.schedule_entries:
            if e_name.get().strip(): names_count += 1
            a_txt = e_amount.get().strip()
            if a_txt:
                try: total_sum += float(a_txt)
                except: pass
        self.lbl_names_count.config(text=f"الاسم (المسجلون: {names_count})")
        self.lbl_amount_sum.config(text=f"المجموع: {total_sum:.2f}")

    def save_daily_schedule_auto(self):
        current_d_str = self.get_current_date_str()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM daily_schedule WHERE date = ?", (current_d_str,))
        
        firebase_payload = {}
        for idx, (t_slot, e_name, e_amount) in enumerate(self.schedule_entries):
            n_val = e_name.get().strip()
            a_str = e_amount.get().strip()
            a_val = 0.0
            if a_str:
                try: a_val = float(a_str)
                except: pass

            if n_val or a_val > 0:
                cursor.execute("INSERT INTO daily_schedule (date, row_index, time_slot, name_val, amount_val) VALUES (?, ?, ?, ?, ?)",
                               (current_d_str, idx, t_slot, n_val, a_val))
                firebase_payload[str(idx)] = {"time": t_slot, "name": n_val, "amount": a_val}

        conn.commit()
        conn.close()
        self.sync_to_firebase(f"daily_schedule/{current_d_str.replace('-', '_')}", firebase_payload)

    def clear_daily_schedule(self):
        current_d_str = self.get_current_date_str()
        if messagebox.askyesno("تأكيد التفريغ", f"هل أنت متأكد من تفريغ جدول يوم ({current_d_str})؟"):
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM daily_schedule WHERE date = ?", (current_d_str,))
            conn.commit()
            conn.close()
            self.sync_to_firebase(f"daily_schedule/{current_d_str.replace('-', '_')}", None)
            self.refresh_current_page()

    # ==========================================
    # 7. قسم المذكرات والمهام
    # ==========================================
    def build_notes_page(self):
        page_title = self.get_page_name("notes", "مذكرات والمهام")
        tk.Label(self.content_area, text=f"📝 {page_title} والمذكرات", font=("Arial", 14, "bold"), fg="#1e293b", bg="#f8fafc").pack(anchor="w", padx=20, pady=10)

        section_tasks = tk.LabelFrame(self.content_area, text=" المهام اليومية ", font=("Arial", 12, "bold"), fg="#0369a1", bg="#f8fafc")
        section_tasks.pack(fill="x", padx=20, pady=10)

        input_f = tk.Frame(section_tasks, bg="#f8fafc")
        input_f.pack(fill="x", padx=10, pady=5)

        tk.Label(input_f, text="العنوان:", bg="#f8fafc", font=("Arial", 10, "bold")).grid(row=0, column=0, padx=5, pady=5, sticky="w")
        e_title = tk.Entry(input_f, width=25, font=("Arial", 10))
        e_title.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        tk.Label(input_f, text="التاريخ (YYYY-MM-DD):", bg="#f8fafc", font=("Arial", 10, "bold")).grid(row=0, column=2, padx=5, pady=5, sticky="w")
        e_target_date = tk.Entry(input_f, width=15, font=("Arial", 10))
        e_target_date.insert(0, self.get_current_date_str())
        e_target_date.grid(row=0, column=3, padx=5, pady=5, sticky="w")

        tk.Label(input_f, text="التفاصيل:", bg="#f8fafc", font=("Arial", 10, "bold")).grid(row=1, column=0, padx=5, pady=5, sticky="nw")
        txt_content = tk.Text(input_f, width=55, height=3, font=("Arial", 10))
        txt_content.grid(row=1, column=1, columnspan=3, padx=5, pady=5, sticky="w")

        def save_note():
            title = e_title.get().strip()
            content = txt_content.get("1.0", tk.END).strip()
            t_date = e_target_date.get().strip()
            created_at = datetime.date.today().strftime("%Y-%m-%d")
            if not title: return

            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO notes (title, content, target_date, created_at, status) VALUES (?, ?, ?, ?, 'قيد الانتظار')",
                           (title, content, t_date, created_at))
            note_id = cursor.lastrowid
            conn.commit()
            conn.close()

            self.sync_to_firebase(f"notes/{note_id}", {"title": title, "content": content, "target_date": t_date, "status": "قيد الانتظار"})
            e_title.delete(0, tk.END)
            txt_content.delete("1.0", tk.END)
            self.refresh_notes_table()
            self.update_alert_banner()

        tk.Button(input_f, text="💾 حفظ المهمة", command=save_note, bg="#16a34a", fg="white", font=("Arial", 10, "bold"), padx=15, pady=4).grid(row=2, column=1, padx=5, pady=5, sticky="w")

        filter_bar = tk.Frame(section_tasks, bg="#f8fafc")
        filter_bar.pack(fill="x", padx=10, pady=5)
        tk.Label(filter_bar, text="عرض حسب:", bg="#f8fafc", font=("Arial", 10, "bold")).pack(side="left", padx=5)
        self.note_filter_var = tk.StringVar(value="الكل")
        combo_note_filter = ttk.Combobox(filter_bar, textvariable=self.note_filter_var, values=["الكل", "مهام اليوم المحدد", "المهام المستقبلية"], state="readonly", width=18)
        combo_note_filter.pack(side="left", padx=5)
        combo_note_filter.bind("<<ComboboxSelected>>", lambda e: self.refresh_notes_table())

        columns = ("id", "chk", "status", "title", "content", "target_date", "created_at", "del")
        self.notes_tree = ttk.Treeview(section_tasks, columns=columns, show="headings", height=8)
        for col, txt, w in zip(columns, ["ID", "☑️", "الحالة", "العنوان", "التفاصيل", "التاريخ", "الإنشاء", "🗑️"], [35, 40, 85, 170, 280, 105, 105, 75]):
            self.notes_tree.heading(col, text=txt)
            self.notes_tree.column(col, width=w, anchor="center")
        self.notes_tree.pack(side="left", fill="both", expand=True, padx=10, pady=5)

        def on_tree_click(event):
            region = self.notes_tree.identify("region", event.x, event.y)
            if region == "cell":
                col = self.notes_tree.identify_column(event.x)
                selected = self.notes_tree.selection()
                if not selected: return
                note_id = self.notes_tree.item(selected[0], "values")[0]
                if col == "#2": toggle_note_status_by_id(note_id)
                elif col == "#8": delete_note_by_id(note_id)

        self.notes_tree.bind("<Button-1>", on_tree_click)
        scroll_notes = ttk.Scrollbar(section_tasks, orient="vertical", command=self.notes_tree.yview)
        scroll_notes.pack(side="right", fill="y", pady=5)
        self.notes_tree.configure(yscrollcommand=scroll_notes.set)

        def toggle_note_status_by_id(note_id):
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT status FROM notes WHERE id = ?", (note_id,))
            row = cursor.fetchone()
            if row:
                new_st = "مكتملة" if row[0] != "مكتملة" else "قيد الانتظار"
                cursor.execute("UPDATE notes SET status = ? WHERE id = ?", (new_st, note_id))
                conn.commit()
            conn.close()
            self.sync_to_firebase(f"notes/{note_id}/status", new_st)
            self.refresh_notes_table()
            self.update_alert_banner()

        def delete_note_by_id(note_id):
            if messagebox.askyesno("تأكيد الحذف", "هل أنت متأكد من حذف هذه المهمة؟"):
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("DELETE FROM notes WHERE id = ?", (note_id,))
                conn.commit()
                conn.close()
                self.sync_to_firebase(f"notes/{note_id}", None)
                self.refresh_notes_table()
                self.update_alert_banner()

        self.refresh_notes_table()

        current_d_str = self.get_current_date_str()
        section_memo = tk.LabelFrame(self.content_area, text=f" المذكرة اليومية لتاريخ ({current_d_str}) (حفظ سحابي) ", font=("Arial", 12, "bold"), fg="#854d0e", bg="#f8fafc")
        section_memo.pack(fill="x", padx=20, pady=10)

        self.memo_text = tk.Text(section_memo, width=80, height=8, font=("Arial", 11), bg="#ffffff", fg="#0f172a", relief="solid", bd=1)
        self.memo_text.pack(fill="x", padx=10, pady=5)

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT content FROM daily_memos WHERE date = ?", (current_d_str,))
        memo_row = cursor.fetchone()
        conn.close()
        if memo_row and memo_row[0]: self.memo_text.insert("1.0", memo_row[0])

        def save_daily_memo_auto(event=None):
            memo_content = self.memo_text.get("1.0", tk.END).strip()
            conn_db = sqlite3.connect(DB_PATH)
            cur = conn_db.cursor()
            cur.execute("INSERT OR REPLACE INTO daily_memos (date, content) VALUES (?, ?)", (current_d_str, memo_content))
            conn_db.commit()
            conn_db.close()
            self.sync_to_firebase(f"daily_memos/{current_d_str.replace('-', '_')}", memo_content)
            self.update_days_bar()

        self.memo_text.bind("<FocusOut>", save_daily_memo_auto)

    def refresh_notes_table(self):
        if not hasattr(self, "notes_tree"): return
        for r in self.notes_tree.get_children(): self.notes_tree.delete(r)

        filter_val = self.note_filter_var.get()
        curr_d = self.get_current_date_str()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        if filter_val == "مهام اليوم المحدد":
            cursor.execute("SELECT id, status, title, content, target_date, created_at FROM notes WHERE target_date = ? ORDER BY id DESC", (curr_d,))
        elif filter_val == "المهام المستقبلية":
            cursor.execute("SELECT id, status, title, content, target_date, created_at FROM notes WHERE target_date > ? ORDER BY target_date ASC", (curr_d,))
        else:
            cursor.execute("SELECT id, status, title, content, target_date, created_at FROM notes ORDER BY target_date ASC, id DESC")

        for r in cursor.fetchall():
            n_id, status, title, content, t_date_str, created_at = r
            chk_symbol = "☑" if status == "مكتملة" else "☐"
            self.notes_tree.insert("", "end", values=(n_id, chk_symbol, status, title, content, t_date_str, created_at, "🗑️"))
        conn.close()

    # ==========================================
    # 8. السجل المالي والتقارير الشاملة
    # ==========================================
    def build_ledger_page(self):
        page_title = self.get_page_name("ledger", "السجل المالي والتقارير الشاملة")
        selected_month_year_str = f"{self.selected_year.get()}-{self.selected_month.get():02d}"
        tk.Label(self.content_area, text=f"📖 {page_title} - شهر: ({selected_month_year_str})", font=("Arial", 14, "bold"), fg="#1e293b", bg="#f8fafc").pack(anchor="w", padx=20, pady=10)

        filter_f = tk.LabelFrame(self.content_area, text=" التصفية والبحث ", font=("Arial", 10, "bold"), bg="#f8fafc")
        filter_f.pack(fill="x", padx=20, pady=5)

        tk.Label(filter_f, text="البند:", bg="#f8fafc", font=("Arial", 10, "bold")).grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.filter_var = tk.StringVar(value="الكل")
        cats = ["الكل", "دخل", "مصروف", "مصروف ثابت", "ادخار"] + self.inc_categories + self.exp_categories + self.fixed_categories
        self.combo_filter = ttk.Combobox(filter_f, textvariable=self.filter_var, values=cats, font=("Arial", 10), width=18)
        self.combo_filter.grid(row=0, column=1, padx=5, pady=5)

        tk.Label(filter_f, text="المدى:", bg="#f8fafc", font=("Arial", 10, "bold")).grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.time_range_var = tk.StringVar(value="شهري")
        self.combo_range = ttk.Combobox(filter_f, textvariable=self.time_range_var, values=["شهري", "يومي", "أسبوعي", "سنوي", "نطاق مخصص", "الكل"], width=12, font=("Arial", 10), state="readonly")
        self.combo_range.grid(row=0, column=3, padx=5, pady=5)
        self.combo_range.bind("<<ComboboxSelected>>", self.toggle_custom_date_inputs)

        self.custom_date_frame = tk.Frame(filter_f, bg="#f8fafc")
        d_str = self.get_current_date_str()
        tk.Label(self.custom_date_frame, text="من:", bg="#f8fafc", font=("Arial", 9, "bold")).pack(side="left", padx=2)
        self.e_date_from = tk.Entry(self.custom_date_frame, width=11, font=("Arial", 10))
        self.e_date_from.insert(0, d_str)
        self.e_date_from.pack(side="left", padx=2)
        tk.Label(self.custom_date_frame, text="إلى:", bg="#f8fafc", font=("Arial", 9, "bold")).pack(side="left", padx=2)
        self.e_date_to = tk.Entry(self.custom_date_frame, width=11, font=("Arial", 10))
        self.e_date_to.insert(0, d_str)
        self.e_date_to.pack(side="left", padx=2)

        btn_box_ledger = tk.Frame(filter_f, bg="#f8fafc")
        btn_box_ledger.grid(row=0, column=5, padx=10, pady=5)
        tk.Button(btn_box_ledger, text="تطبيق", command=self.refresh_ledger_table, bg="#2563eb", fg="white", font=("Arial", 10, "bold")).pack(side="left", padx=4)
        tk.Button(btn_box_ledger, text="🗑️ حذف", command=self.delete_selected_transaction, bg="#dc2626", fg="white", font=("Arial", 10, "bold")).pack(side="left", padx=4)

        columns = ("id", "date", "type", "category", "amount")
        self.tree = ttk.Treeview(self.content_area, columns=columns, show="headings", height=16)
        for col, txt in zip(columns, ["ID", "التاريخ", "النوع", "البند", "المبلغ"]):
            self.tree.heading(col, text=txt)
            self.tree.column(col, width=120, anchor="center")
        self.tree.pack(side="left", fill="both", expand=True, padx=20, pady=5)

        scroll = ttk.Scrollbar(self.content_area, orient="vertical", command=self.tree.yview)
        scroll.pack(side="right", fill="y", pady=5)
        self.tree.configure(yscrollcommand=scroll.set)

        self.lbl_ledger_sum = tk.Label(self.content_area, text="الإجمالي: 0.00", font=("Arial", 11, "bold"), fg="#1e3a8a", bg="#f8fafc")
        self.lbl_ledger_sum.pack(pady=5)
        self.refresh_ledger_table()

    def toggle_custom_date_inputs(self, event=None):
        if self.time_range_var.get() == "نطاق مخصص":
            self.custom_date_frame.grid(row=0, column=4, padx=5, pady=5)
        else:
            self.custom_date_frame.grid_forget()

    def refresh_ledger_table(self):
        for r in self.tree.get_children(): self.tree.delete(r)
        f_val = self.filter_var.get().strip()
        r_val = self.time_range_var.get()
        curr_date = datetime.date(self.selected_year.get(), self.selected_month.get(), self.selected_day.get())

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        query = "SELECT id, date, type, category, amount FROM transactions WHERE 1=1"
        params = []

        if f_val and f_val != "الكل":
            if f_val in ["دخل", "مصروف", "مصروف ثابت", "ادخار"]:
                query += " AND type = ?"; params.append(f_val)
            else:
                query += " AND category LIKE ?"; params.append(f"%{f_val}%")

        if r_val == "شهري":
            ym = f"{self.selected_year.get():04d}-{self.selected_month.get():02d}"
            query += " AND date LIKE ?"; params.append(f"{ym}%")
            label_text = f"إجمالي شهر ({ym}): "
        elif r_val == "يومي":
            d_str = curr_date.strftime("%Y-%m-%d")
            query += " AND date = ?"; params.append(d_str)
            label_text = f"إجمالي يوم ({d_str}): "
        elif r_val == "أسبوعي":
            sw = curr_date - datetime.timedelta(days=curr_date.weekday())
            ew = sw + datetime.timedelta(days=6)
            query += " AND date >= ? AND date <= ?"; params.extend([sw.strftime("%Y-%m-%d"), ew.strftime("%Y-%m-%d")])
            label_text = f"إجمالي الأسبوع: "
        elif r_val == "سنوي":
            ys = str(self.selected_year.get())
            query += " AND date LIKE ?"; params.append(f"{ys}%")
            label_text = f"إجمالي سنة ({ys}): "
        elif r_val == "نطاق مخصص":
            df = self.e_date_from.get().strip()
            dt = self.e_date_to.get().strip()
            query += " AND date >= ? AND date <= ?"; params.extend([df, dt])
            label_text = f"إجمالي الفترة: "
        else:
            label_text = "الإجمالي الشامل: "

        query += " ORDER BY date DESC, id DESC"
        cursor.execute(query, params)
        total = 0.0
        for row in cursor.fetchall():
            self.tree.insert("", "end", values=row)
            total += row[4]
        conn.close()
        self.lbl_ledger_sum.config(text=f"{label_text} {total:.2f}")

    def delete_selected_transaction(self):
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("تنبيه", "حدد حركة من الجدول أولاً.")
            return

        if messagebox.askyesno("تأكيد الحذف", "هل أنت متأكد من حذف هذه الحركة؟"):
            t_id = self.tree.item(selected_items[0], "values")[0]
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM transactions WHERE id = ?", (t_id,))
            conn.commit()
            conn.close()
            self.sync_to_firebase(f"transactions/{t_id}", None)
            self.refresh_ledger_table()

if __name__ == "__main__":
    root = tk.Tk()
    app = SmartFinanceApp(root)
    root.mainloop()
