import flet as ft
import sqlite3
from datetime import datetime, timedelta

# --- 1. إعداد قاعدة البيانات وتحديث الجداول ---
def init_db():
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            done INTEGER,
            created_at TEXT,
            due_date TEXT,
            recurrence TEXT DEFAULT 'لا تتكرر',
            last_reset_date TEXT
        )
    """)
    # التحقق من وجود الأعمدة الجديدة في جدول المهام للتوافق مع التحديثات
    for col, col_type in [("due_date", "TEXT"), ("recurrence", "TEXT DEFAULT 'لا تتكرر'"), ("last_reset_date", "TEXT")]:
        try:
            cursor.execute(f"ALTER TABLE tasks ADD COLUMN {col} {col_type}")
        except sqlite3.OperationalError:
            pass

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT,
            amount REAL,
            category TEXT,
            created_at TEXT,
            date_only TEXT
        )
    """)
    try:
        cursor.execute("ALTER TABLE expenses ADD COLUMN date_only TEXT")
    except sqlite3.OperationalError:
        pass

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE
        )
    """)
    
    default_cats = ["طعام 🍔", "مواصلات 🚗", "فواتير 💡", "تسوق 🛍️", "مصروف كلية", "أخرى 📦"]
    for cat in default_cats:
        try:
            cursor.execute("INSERT INTO categories (name) VALUES (?)", (cat,))
        except sqlite3.IntegrityError:
            pass

    # جدول الإعدادات العامة (الميزانية، رمز القفل، إلخ)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    
    # القيم الافتراضية
    defaults = {"monthly_budget": "1500", "app_pin": "1234", "lock_enabled": "False"}
    for k, v in defaults.items():
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))

    conn.commit()
    conn.close()

init_db()

# --- 2. واجهة التطبيق الرئيسية ---
def main(page: ft.Page):
    page.title = "منظّم يومك الاحترافي 🎯"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 10
    page.rtl = True
    page.locale_configuration = ft.LocaleConfiguration(
        supported_locales=[ft.Locale("ar")],
        current_locale=ft.Locale("ar")
    )

    date_picker = ft.DatePicker(confirm_text="موافق", cancel_text="إلغاء")
    time_picker = ft.TimePicker(confirm_text="موافق", cancel_text="إلغاء")
    page.overlay.extend([date_picker, time_picker])

    def get_setting(key):
        conn = sqlite3.connect("data.db")
        cur = conn.cursor()
        cur.execute("SELECT value FROM settings WHERE key = ?", (key,))
        res = cur.fetchone()
        conn.close()
        return res[0] if res else ""

    def set_setting(key, value):
        conn = sqlite3.connect("data.db")
        cur = conn.cursor()
        cur.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
        conn.commit()
        conn.close()

    def show_snack(message, icon=ft.Icons.CHECK_CIRCLE, is_error=False):
        page.snack_bar = ft.SnackBar(
            content=ft.Row([
                ft.Icon(icon, color=ft.Colors.WHITE, size=20),
                ft.Text(message, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD)
            ], spacing=10),
            bgcolor=ft.Colors.RED_700 if is_error else ft.Colors.GREEN_700,
            behavior=ft.SnackBarBehavior.FLOATING,
            shape=ft.RoundedRectangleBorder(radius=10),
        )
        page.snack_bar.open = True
        page.update()

    def toggle_theme(e):
        if page.theme_mode == ft.ThemeMode.LIGHT:
            page.theme_mode = ft.ThemeMode.DARK
        else:
            page.theme_mode = ft.ThemeMode.LIGHT
        refresh_all_views()
        page.update()

    def clear_all_data(e):
        conn = sqlite3.connect("data.db")
        cur = conn.cursor()
        cur.execute("DELETE FROM tasks")
        cur.execute("DELETE FROM expenses")
        conn.commit()
        conn.close()
        load_tasks()
        load_expenses()
        load_analytics()
        show_snack("تم مسح كافة البيانات بنجاح", icon=ft.Icons.WARNING, is_error=True)

    # --- معالجة المهام المتكررة تلقائياً عند فتح التطبيق ---
    def check_recurring_tasks():
        today_str = datetime.now().strftime("%Y-%m-%d")
        conn = sqlite3.connect("data.db")
        cur = conn.cursor()
        cur.execute("SELECT id, recurrence, last_reset_date FROM tasks WHERE recurrence != 'لا تتكرر'")
        tasks = cur.fetchall()
        
        for tid, rec, last_reset in tasks:
            if last_reset != today_str:
                should_reset = False
                if rec == "يومية":
                    should_reset = True
                elif rec == "أسبوعية":
                    if not last_reset:
                        should_reset = True
                    else:
                        d_last = datetime.strptime(last_reset, "%Y-%m-%d")
                        if (datetime.now() - d_last).days >= 7:
                            should_reset = True
                elif rec == "شهرية":
                    if not last_reset:
                        should_reset = True
                    else:
                        d_last = datetime.strptime(last_reset, "%Y-%m-%d")
                        if (datetime.now() - d_last).days >= 30:
                            should_reset = True
                
                if should_reset:
                    cur.execute("UPDATE tasks SET done = 0, last_reset_date = ? WHERE id = ?", (today_str, tid))
        conn.commit()
        conn.close()

    check_recurring_tasks()

    # --- شاشة قفل التطبيق بـ PIN ---
    pin_input = ft.TextField(label="أدخل رمز المرور (افتراضي: 1234)", password=True, can_reveal_password=True, text_align=ft.TextAlign.CENTER, width=220, border_radius=10)
    
    def try_unlock_app(e):
        saved_pin = get_setting("app_pin")
        if pin_input.value == saved_pin:
            lock_screen.visible = False
            lock_screen.opacity = 0.0
            welcome_screen.visible = True
            welcome_screen.opacity = 1.0
            page.update()
        else:
            show_snack("رمز المرور غير صحيح!", icon=ft.Icons.ERROR, is_error=True)

    lock_screen = ft.Container(
        content=ft.Column([
            ft.Icon(ft.Icons.LOCK_OUTLINE, size=80, color=ft.Colors.BLUE_700),
            ft.Text("التطبيق مقفل لحماية خصوصيتك 🔒", size=20, weight=ft.FontWeight.BOLD),
            ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
            pin_input,
            ft.ElevatedButton(content=ft.Text("فتح التطبيق 🔓", color=ft.Colors.WHITE), on_click=try_unlock_app, bgcolor=ft.Colors.BLUE_600, style=ft.ButtonStyle(padding=15, shape=ft.RoundedRectangleBorder(radius=10)))
        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        alignment=ft.alignment.Alignment(0, 0),
        expand=True,
        visible=(get_setting("lock_enabled") == "True")
    )

    # حقول إعدادات الميزانية والقفل
    budget_input = ft.TextField(label="سقف المصروفات الشهري (ريال)", value=get_setting("monthly_budget"), width=220, border_radius=10, keyboard_type=ft.KeyboardType.NUMBER)
    new_pin_input = ft.TextField(label="رمز المرور الجديد", value=get_setting("app_pin"), width=220, border_radius=10, password=True)
    lock_switch = ft.Switch(value=(get_setting("lock_enabled") == "True"))

    def save_settings_changes(e):
        set_setting("monthly_budget", budget_input.value.strip() if budget_input.value else "1500")
        set_setting("app_pin", new_pin_input.value.strip() if new_pin_input.value else "1234")
        set_setting("lock_enabled", str(lock_switch.value))
        show_snack("تم حفظ الإعدادات بنجاح!")
        update_stats()
        load_analytics()

    settings_view_container = ft.Container(
        content=ft.Column([
            ft.Text("⚙️ إعدادات التطبيق المتقدمة", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700),
            ft.Divider(height=10),
            ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("💰 إدارة الميزانية", weight=ft.FontWeight.BOLD),
                        ft.Text("حدد سقف مصروفاتك الشهري لتلقي التنبيهات:", size=12, color=ft.Colors.GREY_600),
                        budget_input
                    ], spacing=8),
                    padding=15
                )
            ),
            ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("🔒 حماية التطبيق برمز سري (PIN)", weight=ft.FontWeight.BOLD),
                        ft.Row([
                            ft.Text("تفعيل قفل التطبيق عند البدء"),
                            lock_switch
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        new_pin_input
                    ], spacing=8),
                    padding=15
                )
            ),
            ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("المظهر والوضع", weight=ft.FontWeight.BOLD),
                        ft.Row([
                            ft.Text("الوضع الليلي / النهاري"),
                            ft.Switch(value=page.theme_mode == ft.ThemeMode.DARK, on_change=toggle_theme)
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                    ]),
                    padding=15
                )
            ),
            ft.ElevatedButton(content=ft.Text("حفظ التعديلات والإعدادات", color=ft.Colors.WHITE), on_click=save_settings_changes, bgcolor=ft.Colors.BLUE_600),
            ft.Divider(height=10),
            ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("إدارة البيانات", weight=ft.FontWeight.BOLD, color=ft.Colors.RED_600),
                        ft.Text("حذف جميع المهام والمصروفات المسجلة نهائياً.", size=12, color=ft.Colors.GREY_600),
                        ft.Divider(height=5),
                        ft.ElevatedButton(content=ft.Text("مسح كافة البيانات 🗑️", color=ft.Colors.WHITE), on_click=clear_all_data, bgcolor=ft.Colors.RED_600)
                    ], spacing=8),
                    padding=15
                )
            ),
            ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("حول التطبيق", weight=ft.FontWeight.BOLD),
                        ft.Text("منظّم يومك الاحترافي - الإصدار الشامل المطور."),
                        ft.Text("تم البرمجة والتطوير بواسطة: حكيم محفوظ 💻", size=12, color=ft.Colors.BLUE_600)
                    ], spacing=5),
                    padding=15
                )
            )
        ], spacing=15, scroll=ft.ScrollMode.AUTO),
        padding=5,
        expand=True
    )

    content_area = ft.Container(content=None, expand=True)

    # أزرار شريط التنقل السفلي (أصبحت 4 تبويبات شاملة)
    btn_tasks_tab = ft.ElevatedButton(
        content=ft.Text("📋 المهام", color=ft.Colors.WHITE),
        bgcolor=ft.Colors.BLUE_700,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=15), padding=8)
    )
    
    btn_expenses_tab = ft.ElevatedButton(
        content=ft.Text("💰 المصروفات", color=ft.Colors.WHITE if page.theme_mode == ft.ThemeMode.DARK else ft.Colors.BLACK87),
        bgcolor=ft.Colors.GREY_800 if page.theme_mode == ft.ThemeMode.DARK else ft.Colors.GREY_200,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=15), padding=8)
    )

    btn_calendar_tab = ft.ElevatedButton(
        content=ft.Text("📅 التقويم", color=ft.Colors.WHITE if page.theme_mode == ft.ThemeMode.DARK else ft.Colors.BLACK87),
        bgcolor=ft.Colors.GREY_800 if page.theme_mode == ft.ThemeMode.DARK else ft.Colors.GREY_200,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=15), padding=8)
    )

    btn_analytics_tab = ft.ElevatedButton(
        content=ft.Text("📊 التحليلات", color=ft.Colors.WHITE if page.theme_mode == ft.ThemeMode.DARK else ft.Colors.BLACK87),
        bgcolor=ft.Colors.GREY_800 if page.theme_mode == ft.ThemeMode.DARK else ft.Colors.GREY_200,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=15), padding=8)
    )

    def update_tab_buttons_colors(selected_btn):
        for b in [btn_tasks_tab, btn_expenses_tab, btn_calendar_tab, btn_analytics_tab]:
            if b == selected_btn:
                b.bgcolor = ft.Colors.BLUE_700
                b.content.color = ft.Colors.WHITE
            else:
                b.bgcolor = ft.Colors.GREY_800 if page.theme_mode == ft.ThemeMode.DARK else ft.Colors.GREY_200
                b.content.color = ft.Colors.WHITE if page.theme_mode == ft.ThemeMode.DARK else ft.Colors.BLACK87

    def show_tasks_tab(e):
        update_tab_buttons_colors(btn_tasks_tab)
        content_area.content = tasks_view_container
        page.update()

    def show_expenses_tab(e):
        update_tab_buttons_colors(btn_expenses_tab)
        content_area.content = expenses_view_container
        page.update()

    def show_calendar_tab(e):
        update_tab_buttons_colors(btn_calendar_tab)
        build_calendar_view()
        content_area.content = calendar_view_container
        page.update()

    def show_analytics_tab(e):
        update_tab_buttons_colors(btn_analytics_tab)
        load_analytics()
        content_area.content = analytics_content
        page.update()

    def show_settings_screen(e):
        for b in [btn_tasks_tab, btn_expenses_tab, btn_calendar_tab, btn_analytics_tab]:
            b.bgcolor = ft.Colors.GREY_800 if page.theme_mode == ft.ThemeMode.DARK else ft.Colors.GREY_200
            b.content.color = ft.Colors.WHITE if page.theme_mode == ft.ThemeMode.DARK else ft.Colors.BLACK87
        content_area.content = settings_view_container
        page.update()

    btn_tasks_tab.on_click = show_tasks_tab
    btn_expenses_tab.on_click = show_expenses_tab
    btn_calendar_tab.on_click = show_calendar_tab
    btn_analytics_tab.on_click = show_analytics_tab

    page.appbar = ft.AppBar(
        title=ft.Text("منظّم يومك الاحترافي 🎯", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
        center_title=True,
        bgcolor=ft.Colors.BLUE_700,
        actions=[
            ft.IconButton(
                icon=ft.Icons.SETTINGS,
                icon_color=ft.Colors.WHITE,
                tooltip="الإعدادات المتقدمة",
                on_click=show_settings_screen
            )
        ]
    )

    def enter_app(e):
        welcome_screen.opacity = 0.0
        welcome_screen.visible = False
        main_layout.visible = True
        main_layout.opacity = 1.0
        check_due_tasks_notifications()
        page.update()

    welcome_screen = ft.Container(
        content=ft.Column(
            [
                ft.Icon(ft.Icons.AUTO_AWESOME, size=80, color=ft.Colors.BLUE_700),
                ft.Text("مرحباً بك يا حكيم 👋", size=26, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_900, text_align=ft.TextAlign.CENTER),
                ft.Text("تطبيق منظّم يومك (النسخة الشاملة والمطورة)", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_800, text_align=ft.TextAlign.CENTER),
                ft.Container(
                    content=ft.Text("تصميم وتطوير: حكيم محفوظ", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_600),
                    padding=8, border_radius=10, bgcolor=ft.Colors.BLUE_50,
                ),
                ft.Divider(height=15, color=ft.Colors.TRANSPARENT),
                ft.Text("« نحو إنتاجية متكاملة وإدارة ذكية للمهام والميزانية »", size=13, italic=True, color=ft.Colors.GREY_600, text_align=ft.TextAlign.CENTER),
                ft.Divider(height=25, color=ft.Colors.TRANSPARENT),
                ft.ElevatedButton(
                    content=ft.Text("الدخول لوحة التحكم 🚀", color=ft.Colors.WHITE),
                    on_click=enter_app,
                    bgcolor=ft.Colors.BLUE_600,
                    style=ft.ButtonStyle(padding=20, shape=ft.RoundedRectangleBorder(radius=12)),
                ),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        alignment=ft.alignment.Alignment(0, 0),
        expand=True,
        animate_opacity=400,
        visible=(get_setting("lock_enabled") != "True")
    )

    total_expenses_card_text = ft.Text("0.00 ريال", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_600)
    remaining_tasks_card_text = ft.Text("0", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700)
    streak_card_text = ft.Text("🔥 0 أيام", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.AMBER_700)

    def update_stats():
        conn = sqlite3.connect("data.db")
        cur = conn.cursor()
        cur.execute("SELECT SUM(amount) FROM expenses")
        res_exp = cur.fetchone()[0]
        total_exp = res_exp if res_exp else 0.0

        cur.execute("SELECT COUNT(*) FROM tasks WHERE done = 0")
        res_tasks = cur.fetchone()[0]
        rem_tasks = res_tasks if res_tasks else 0

        # حساب الـ Streak (الأيام المتتالية المنجزة)
        cur.execute("SELECT COUNT(*), SUM(CASE WHEN done = 1 THEN 1 ELSE 0 END) FROM tasks")
        t_stat = cur.fetchone()
        conn.close()

        total_t = t_stat[0] if t_stat[0] else 0
        done_t = t_stat[1] if t_stat[1] else 0
        
        streak_val = done_t if total_t > 0 and done_t == total_t else (done_t // 2)

        total_expenses_card_text.value = f"{total_exp:.2f} ريال"
        remaining_tasks_card_text.value = str(rem_tasks)
        streak_card_text.value = f"🔥 {streak_val} إنجاز"
        page.update()

    def check_due_tasks_notifications():
        conn = sqlite3.connect("data.db")
        cur = conn.cursor()
        cur.execute("SELECT title, due_date FROM tasks WHERE done = 0 AND due_date != ''")
        tasks = cur.fetchall()
        conn.close()
        
        today_str = datetime.now().strftime("%Y-%m-%d")
        due_count = 0
        for title, due in tasks:
            if today_str in due:
                due_count += 1
        
        if due_count > 0:
            show_snack(f"تنبيه: لديك {due_count} مهام مستحقة اليوم!", icon=ft.Icons.NOTIFICATIONS_ACTIVE)

    # --- 3. التقويم التفاعلي (Interactive Calendar View) ---
    selected_calendar_date = {"date": datetime.now().strftime("%Y-%m-%d")}
    current_cal_year = {"y": datetime.now().year}
    current_cal_month = {"m": datetime.now().month}
    calendar_details_list = ft.Column(spacing=8)
    month_title_text = ft.Text("", size=16, weight=ft.FontWeight.BOLD)

    def build_calendar_view():
        calendar_details_list.controls.clear()
        y = current_cal_year["y"]
        m = current_cal_month["m"]
        
        month_names = ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو", "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"]
        month_title_text.value = f"📅 {month_names[m-1]} {y}"
        
        # جلب المهام والمصروفات الخاصة بالشهر المحدد
        conn = sqlite3.connect("data.db")
        cur = conn.cursor()
        cur.execute("SELECT title, due_date, done FROM tasks WHERE due_date LIKE ?", (f"{y}-{m:02d}%",))
        month_tasks = cur.fetchall()
        
        cur.execute("SELECT description, amount, category, date_only FROM expenses WHERE date_only LIKE ?", (f"{y}-{m:02d}%",))
        month_expenses = cur.fetchall()
        conn.close()

        # عرض تفاصيل اليوم المحدد
        calendar_details_list.controls.append(
            ft.Text(f"📌 المهام والمصروفات ليوم: {selected_calendar_date['date']}", weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700)
        )
        
        day_t_count = 0
        for t, d, dn in month_tasks:
            if selected_calendar_date["date"] in d:
                day_t_count += 1
                status_icon = "✅" if dn else "⏳"
                calendar_details_list.controls.append(
                    ft.Text(f"{status_icon} مهمة: {t}", size=13)
                )
        if day_t_count == 0:
            calendar_details_list.controls.append(ft.Text("لا توجد مهام مسجلة في هذا اليوم.", size=12, color=ft.Colors.GREY_500))

        calendar_details_list.controls.append(ft.Divider(height=5))
        
        day_e_count = 0
        for desc, amt, cat, dt in month_expenses:
            if dt == selected_calendar_date["date"]:
                day_e_count += 1
                calendar_details_list.controls.append(
                    ft.Text(f"💰 مصروف [{cat}]: {desc} ({amt:.2f} ريال)", size=13, color=ft.Colors.RED_500)
                )
        if day_e_count == 0:
            calendar_details_list.controls.append(ft.Text("لا توجد مصروفات مسجلة في هذا اليوم.", size=12, color=ft.Colors.GREY_500))

        page.update()

    def change_month(delta):
        m = current_cal_month["m"] + delta
        y = current_cal_year["y"]
        if m > 12:
            m = 1
            y += 1
        elif m < 1:
            m = 12
            y -= 1
        current_cal_month["m"] = m
        current_cal_year["y"] = y
        build_calendar_view()

    calendar_view_container = ft.Container(
        content=ft.Column([
            ft.Text("📅 التقويم الذكي والتنظيم الزمني", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700),
            ft.Row([
                ft.IconButton(icon=ft.Icons.ARROW_FORWARD, on_click=lambda e: change_month(1)),
                month_title_text,
                ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=lambda e: change_month(-1)),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(height=10),
            calendar_details_list
        ], scroll=ft.ScrollMode.AUTO),
        padding=5,
        expand=True
    )

    analytics_content = ft.Column(spacing=15, scroll=ft.ScrollMode.AUTO, expand=True)

    def load_analytics():
        analytics_content.controls.clear()
        conn = sqlite3.connect("data.db")
        cur = conn.cursor()
        
        cur.execute("SELECT category, SUM(amount), COUNT(*) FROM expenses GROUP BY category")
        data = cur.fetchall()

        cur.execute("SELECT COUNT(*), SUM(CASE WHEN done = 1 THEN 1 ELSE 0 END) FROM tasks")
        task_stats = cur.fetchone()
        conn.close()

        total_tasks_count = task_stats[0] if task_stats[0] else 0
        done_tasks_count = task_stats[1] if task_stats[1] else 0

        # فحص الميزانية وسقف الصرف
        budget_limit = float(get_setting("monthly_budget")) if get_setting("monthly_budget") else 1500.0
        total_spent = sum([item[1] for item in data]) if data else 0.0
        budget_pct = (total_spent / budget_limit) if budget_limit > 0 else 0

        analytics_content.controls.append(
            ft.Text("📊 لوحة التحليلات والميزانية الذكية", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700)
        )

        # كارد مؤشر الميزانية
        budget_color = ft.Colors.GREEN_400 if budget_pct < 0.8 else (ft.Colors.AMBER_400 if budget_pct <= 1.0 else ft.Colors.RED_600)
        analytics_content.controls.append(
            ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Text("مؤشر الميزانية الشهرية", weight=ft.FontWeight.BOLD),
                            ft.Text(f"{total_spent:.2f} / {budget_limit:.2f} ريال", weight=ft.FontWeight.BOLD, color=budget_color)
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.ProgressBar(value=min(budget_pct, 1.0), color=budget_color, bgcolor=ft.Colors.GREY_300, height=10),
                        ft.Text("⚠️ تنبيه: اقتربت من تجاوز الحد الأقصى للميزانية!" if budget_pct >= 0.8 and budget_pct <= 1.0 else ("🚨 تحذير: تجاوزت سقف الميزانية المحددة!" if budget_pct > 1.0 else "✅ وضعك المالي ممتاز وتحت السيطرة."), size=11, color=budget_color)
                    ], spacing=6),
                    padding=15
                )
            )
        )

        analytics_content.controls.append(
            ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("ملخص إنجاز المهام والإنتاجية", weight=ft.FontWeight.BOLD, size=14),
                        ft.Text(f"إجمالي المهام المسجلة: {total_tasks_count}"),
                        ft.Text(f"المهام المنجزة: {done_tasks_count}"),
                        ft.Text(f"المهام المتبقية: {total_tasks_count - done_tasks_count}"),
                    ], spacing=5),
                    padding=15
                )
            )
        )

        analytics_content.controls.append(
            ft.Text("📈 نسب ومؤشرات المصروفات حسب التصنيف:", weight=ft.FontWeight.BOLD, size=15)
        )

        if not data:
            analytics_content.controls.append(
                ft.Text("لا توجد مصروفات مسجلة حالياً لعرض التحليلات.", color=ft.Colors.GREY_500)
            )
        else:
            colors_list = [ft.Colors.BLUE_400, ft.Colors.RED_400, ft.Colors.GREEN_400, ft.Colors.AMBER_400, ft.Colors.PURPLE_400, ft.Colors.TEAL_400]
            total_sum = total_spent if total_spent > 0 else 1

            for idx, (cat, total, count) in enumerate(data):
                percentage = (total / total_sum) * 100
                c_color = colors_list[idx % len(colors_list)]
                
                analytics_content.controls.append(
                    ft.Card(
                        content=ft.Container(
                            content=ft.Column([
                                ft.Row([
                                    ft.Row([
                                        ft.Container(width=12, height=12, bgcolor=c_color, border_radius=3),
                                        ft.Text(f"{cat}", weight=ft.FontWeight.BOLD),
                                    ], spacing=8),
                                    ft.Text(f"{total:.2f} ريال ({percentage:.1f}%)", weight=ft.FontWeight.BOLD, color=ft.Colors.RED_500),
                                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                                ft.ProgressBar(value=percentage / 100.0, color=c_color, bgcolor=ft.Colors.GREY_300, height=8),
                                ft.Text(f"عدد المعاملات: {count}", size=11, color=ft.Colors.GREY_600)
                            ], spacing=6),
                            padding=12
                        )
                    )
                )
        page.update()

    tasks_list = ft.Column(spacing=8)
    task_filter_mode = {"mode": "all"}

    # خيارات التكرار للمهام الجديدة
    recurrence_dropdown = ft.Dropdown(
        label="التكرار",
        value="لا تتكرر",
        width=120,
        border_radius=10,
        options=[
            ft.dropdown.Option("لا تتكرر"),
            ft.dropdown.Option("يومية"),
            ft.dropdown.Option("أسبوعية"),
            ft.dropdown.Option("شهرية"),
        ]
    )

    def add_task(e):
        if task_input.value and task_input.value.strip():
            title = task_input.value.strip()
            now_str = datetime.now().strftime("%Y-%m-%d | %I:%M %p")
            
            due_date_str = ""
            if selected_date_str["date"] or selected_time_str["time"]:
                d = selected_date_str["date"] if selected_date_str["date"] else datetime.now().strftime("%Y-%m-%d")
                t = selected_time_str["time"] if selected_time_str["time"] else ""
                due_date_str = f"{d} {t}".strip()
            else:
                due_date_str = datetime.now().strftime("%Y-%m-%d")

            rec_mode = recurrence_dropdown.value

            conn = sqlite3.connect("data.db")
            cursor = conn.cursor()
            cursor.execute("INSERT INTO tasks (title, done, created_at, due_date, recurrence, last_reset_date) VALUES (?, 0, ?, ?, ?, ?)", (title, now_str, due_date_str, rec_mode, datetime.now().strftime("%Y-%m-%d")))
            conn.commit()
            conn.close()

            task_input.value = ""
            selected_date_str["date"] = ""
            selected_time_str["time"] = ""
            date_button_text.value = "التاريخ"
            time_button_text.value = "الوقت"
            load_tasks()
            load_analytics()
            show_snack("تمت إضافة المهمة بنجاح!", icon=ft.Icons.TASK_ALT)

    task_input = ft.TextField(
        hint_text="أدخل مهمة جديدة...", 
        expand=True, 
        border_radius=10, 
        border_color=ft.Colors.BLUE_400,
        on_submit=add_task
    )
    
    selected_date_str = {"date": ""}
    selected_time_str = {"time": ""}
    date_button_text = ft.Text("التاريخ", size=12)
    time_button_text = ft.Text("الوقت", size=12)

    def on_date_change(e):
        if date_picker.value:
            selected_date_str["date"] = date_picker.value.strftime("%Y-%m-%d")
            date_button_text.value = f"📅 {selected_date_str['date']}"
            page.update()

    def on_time_change(e):
        if time_picker.value:
            time_obj = time_picker.value
            hour, minute = time_obj.hour, time_obj.minute
            period = "م" if hour >= 12 else "ص"
            hour_12 = hour % 12 or 12
            formatted_time = f"{hour_12:02d}:{minute:02d} {period}"
            selected_time_str["time"] = formatted_time
            time_button_text.value = f"⏰ {selected_time_str['time']}"
            page.update()

    date_picker.on_change = on_date_change
    time_picker.on_change = on_time_change

    edit_task_id = {"id": None}
    edit_task_input = ft.TextField(label="تعديل نص المهمة", on_submit=lambda e: save_edited_task(e))

    def save_edited_task(e):
        if edit_task_id["id"] and edit_task_input.value.strip():
            conn = sqlite3.connect("data.db")
            cur = conn.cursor()
            cur.execute("UPDATE tasks SET title = ? WHERE id = ?", (edit_task_input.value.strip(), edit_task_id["id"]))
            conn.commit()
            conn.close()
            edit_task_dlg.open = False
            load_tasks()
            show_snack("تم تعديل المهمة بنجاح", icon=ft.Icons.EDIT_NOTE)

    edit_task_dlg = ft.AlertDialog(
        title=ft.Text("تعديل المهمة"),
        content=edit_task_input,
        actions=[
            ft.TextButton("حفظ", on_click=save_edited_task),
            ft.TextButton("إلغاء", on_click=lambda e: setattr(edit_task_dlg, 'open', False) or page.update())
        ]
    )
    page.overlay.append(edit_task_dlg)

    search_task_input = ft.TextField(
        hint_text="بحث سريع في المهام...", 
        prefix_icon=ft.Icons.SEARCH, 
        dense=True, 
        border_radius=10,
        on_change=lambda e: load_tasks()
    )

    def load_tasks():
        tasks_list.controls.clear()
        search_query = search_task_input.value.strip() if search_task_input.value else ""
        
        conn = sqlite3.connect("data.db")
        cursor = conn.cursor()
        
        query = "SELECT id, title, done, created_at, due_date, recurrence FROM tasks WHERE 1=1"
        params = []
        
        if task_filter_mode["mode"] == "active":
            query += " AND done = 0"
        elif task_filter_mode["mode"] == "completed":
            query += " AND done = 1"
            
        if search_query:
            query += " AND title LIKE ?"
            params.append(f"%{search_query}%")
            
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        for row in rows:
            task_id, title, done, created_at, due_date, recurrence = row
            
            def on_change(e, tid=task_id):
                is_done = e.control.value
                c = sqlite3.connect("data.db")
                cur = c.cursor()
                cur.execute("UPDATE tasks SET done = ? WHERE id = ?", (1 if is_done else 0, tid))
                c.commit()
                c.close()
                load_tasks()
                update_stats()

            def open_edit_task(e, tid=task_id, t_title=title):
                edit_task_id["id"] = tid
                edit_task_input.value = t_title
                edit_task_dlg.open = True
                page.update()

            def delete_task_item(e, tid=task_id):
                c = sqlite3.connect("data.db")
                cur = c.cursor()
                cur.execute("DELETE FROM tasks WHERE id = ?", (tid,))
                c.commit()
                c.close()
                load_tasks()
                load_analytics()
                show_snack("تم حذف المهمة", icon=ft.Icons.DELETE_OUTLINE, is_error=True)

            due_info = f" | 📅 {due_date}" if due_date else ""
            rec_info = f" | 🔄 {recurrence}" if recurrence and recurrence != "لا تتكرر" else ""
            text_color = ft.Colors.GREY_500 if done else (ft.Colors.WHITE70 if page.theme_mode == ft.ThemeMode.DARK else ft.Colors.BLACK87)
            
            task_content = ft.Container(
                content=ft.Row(
                    [
                        ft.Checkbox(value=bool(done), on_change=on_change),
                        ft.Column(
                            [
                                ft.Text(
                                    title, 
                                    style=ft.TextStyle(
                                        size=16, 
                                        weight=ft.FontWeight.BOLD,
                                        decoration=ft.TextDecoration.LINE_THROUGH if done else ft.TextDecoration.NONE,
                                        color=text_color
                                    )
                                ),
                                ft.Text(f"🕒 {created_at}{due_info}{rec_info}", style=ft.TextStyle(size=11, color=ft.Colors.GREY_400 if page.theme_mode == ft.ThemeMode.DARK else ft.Colors.GREY_700)),
                            ],
                            alignment=ft.MainAxisAlignment.CENTER,
                            spacing=2,
                            expand=True,
                        ),
                        ft.IconButton(icon=ft.Icons.EDIT, icon_size=18, icon_color=ft.Colors.BLUE_400, on_click=open_edit_task),
                        ft.IconButton(icon=ft.Icons.DELETE, icon_size=18, icon_color=ft.Colors.RED_400, on_click=delete_task_item),
                    ],
                    alignment=ft.MainAxisAlignment.START,
                ),
                padding=10,
            )

            dismissible_card = ft.Dismissible(
                content=ft.Card(content=task_content),
                background=ft.Container(bgcolor=ft.Colors.RED_400, alignment=ft.alignment.Alignment(1, 0), padding=20, content=ft.Icon(ft.Icons.DELETE, color=ft.Colors.WHITE)),
                secondary_background=ft.Container(bgcolor=ft.Colors.RED_400, alignment=ft.alignment.Alignment(-1, 0), padding=20, content=ft.Icon(ft.Icons.DELETE, color=ft.Colors.WHITE)),
                on_dismiss=lambda e, tid=task_id: delete_task_item(None, tid)
            )

            tasks_list.controls.append(dismissible_card)
        update_stats()
        page.update()

    btn_filter_all = ft.OutlinedButton("الكل", on_click=lambda e: set_task_filter("all"))
    btn_filter_active = ft.OutlinedButton("النشطة", on_click=lambda e: set_task_filter("active"))
    btn_filter_completed = ft.OutlinedButton("المكتملة", on_click=lambda e: set_task_filter("completed"))

    def set_task_filter(mode):
        task_filter_mode["mode"] = mode
        load_tasks()

    def clear_completed_tasks(e):
        conn = sqlite3.connect("data.db")
        cur = conn.cursor()
        cur.execute("DELETE FROM tasks WHERE done = 1")
        conn.commit()
        conn.close()
        load_tasks()
        load_analytics()
        show_snack("تم تفريغ المهام المكتملة بنجاح", icon=ft.Icons.CLEANING_SERVICES)

    tasks_view_container = ft.Container(
        content=ft.Column([
            ft.Row([
                task_input,
                recurrence_dropdown,
                ft.ElevatedButton(content=ft.Text("إضافة", color=ft.Colors.WHITE), on_click=add_task, bgcolor=ft.Colors.GREEN_600, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))
            ]),
            ft.Row([
                ft.OutlinedButton(content=ft.Row([ft.Icon(ft.Icons.CALENDAR_MONTH, size=16), date_button_text]), on_click=lambda e: setattr(date_picker, 'open', True) or page.update()),
                ft.OutlinedButton(content=ft.Row([ft.Icon(ft.Icons.ACCESS_TIME, size=16), time_button_text]), on_click=lambda e: setattr(time_picker, 'open', True) or page.update()),
            ]),
            search_task_input,
            ft.Row([
                ft.Row([btn_filter_all, btn_filter_active, btn_filter_completed], spacing=5),
                ft.TextButton("حذف المكتمل 🗑️", on_click=clear_completed_tasks, style=ft.ButtonStyle(color=ft.Colors.RED_400))
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(height=10),
            tasks_list
        ], scroll=ft.ScrollMode.AUTO),
        padding=5,
        expand=True
    )

    expenses_list = ft.Column(spacing=8)
    expense_desc = ft.TextField(hint_text="وصف المصروف...", expand=True, border_radius=10, border_color=ft.Colors.BLUE_400, on_submit=lambda e: add_expense(e))
    expense_amount = ft.TextField(hint_text="المبلغ", width=95, keyboard_type=ft.KeyboardType.NUMBER, border_radius=10, border_color=ft.Colors.BLUE_400, on_submit=lambda e: add_expense(e))
    
    category_dropdown = ft.Dropdown(
        label="التصنيف",
        width=125,
        border_radius=10,
        options=[]
    )

    def load_categories_dropdown():
        conn = sqlite3.connect("data.db")
        cur = conn.cursor()
        cur.execute("SELECT name FROM categories")
        rows = cur.fetchall()
        conn.close()
        
        category_dropdown.options = [ft.dropdown.Option(row[0]) for row in rows]
        if category_dropdown.options and not category_dropdown.value:
            category_dropdown.value = rows[0][0]
        page.update()

    new_cat_input = ft.TextField(label="اسم التصنيف الجديد", border_radius=10)

    def save_new_category(e):
        if new_cat_input.value and new_cat_input.value.strip():
            c_name = new_cat_input.value.strip()
            try:
                conn = sqlite3.connect("data.db")
                cur = conn.cursor()
                cur.execute("INSERT INTO categories (name) VALUES (?)", (c_name,))
                conn.commit()
                conn.close()
                new_cat_input.value = ""
                new_cat_dlg.open = False
                load_categories_dropdown()
                show_snack("تمت إضافة التصنيف بنجاح")
            except sqlite3.IntegrityError:
                show_snack("هذا التصنيف موجود مسبقاً!", icon=ft.Icons.ERROR, is_error=True)

    new_cat_dlg = ft.AlertDialog(
        title=ft.Text("إضافة تصنيف جديد للمصروفات"),
        content=new_cat_input,
        actions=[
            ft.TextButton("إضافة", on_click=save_new_category),
            ft.TextButton("إلغاء", on_click=lambda e: setattr(new_cat_dlg, 'open', False) or page.update())
        ]
    )
    page.overlay.append(new_cat_dlg)

    def add_expense(e):
        if expense_desc.value and expense_amount.value and expense_desc.value.strip() and expense_amount.value.strip():
            try:
                desc = expense_desc.value.strip()
                amt = float(expense_amount.value.strip())
                cat = category_dropdown.value if category_dropdown.value else "أخرى 📦"
                now_str = datetime.now().strftime("%Y-%m-%d | %I:%M %p")
                date_only_str = datetime.now().strftime("%Y-%m-%d")

                conn = sqlite3.connect("data.db")
                cursor = conn.cursor()
                cursor.execute("INSERT INTO expenses (description, amount, category, created_at, date_only) VALUES (?, ?, ?, ?, ?)", (desc, amt, cat, now_str, date_only_str))
                conn.commit()
                conn.close()

                expense_desc.value = ""
                expense_amount.value = ""
                load_expenses()
                load_analytics()
                show_snack("تمت إضافة المصروف بنجاح", icon=ft.Icons.ATTACH_MONEY)
            except ValueError:
                show_snack("يرجى إدخال مبلغ صحيح!", icon=ft.Icons.ERROR, is_error=True)

    def load_expenses():
        expenses_list.controls.clear()
        conn = sqlite3.connect("data.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, description, amount, category, created_at FROM expenses")
        rows = cursor.fetchall()
        conn.close()

        for row in rows:
            exp_id, desc, amt, cat, created_at = row
            cat_text = cat if cat else "أخرى 📦"

            def delete_expense_item(e, eid=exp_id):
                c = sqlite3.connect("data.db")
                cur = c.cursor()
                cur.execute("DELETE FROM expenses WHERE id = ?", (eid,))
                c.commit()
                c.close()
                load_expenses()
                load_analytics()
                show_snack("تم حذف المصروف", icon=ft.Icons.DELETE_OUTLINE, is_error=True)

            desc_color = ft.Colors.WHITE70 if page.theme_mode == ft.ThemeMode.DARK else ft.Colors.BLACK87

            expenses_list.controls.append(
                ft.Card(
                    content=ft.Container(
                        content=ft.Row(
                            [
                                ft.Icon(ft.Icons.MONEY_OFF, color=ft.Colors.RED_400),
                                ft.Column(
                                    [
                                        ft.Row([
                                            ft.Text(desc, size=15, weight=ft.FontWeight.BOLD, color=desc_color),
                                            ft.Container(content=ft.Text(cat_text, size=10, color=ft.Colors.BLUE_300 if page.theme_mode == ft.ThemeMode.DARK else ft.Colors.BLUE_800), bgcolor=ft.Colors.BLUE_900 if page.theme_mode == ft.ThemeMode.DARK else ft.Colors.BLUE_50, padding=4, border_radius=5)
                                        ], spacing=8),
                                        ft.Text(f"🕒 {created_at}", size=11, color=ft.Colors.GREY_400 if page.theme_mode == ft.ThemeMode.DARK else ft.Colors.GREY_700),
                                    ],
                                    expand=True,
                                    spacing=2,
                                ),
                                ft.Text(f"{amt:.2f} ريال", weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_400 if page.theme_mode == ft.ThemeMode.DARK else ft.Colors.GREEN_800),
                                ft.IconButton(icon=ft.Icons.DELETE, icon_size=18, icon_color=ft.Colors.RED_400, on_click=delete_expense_item),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        padding=10,
                    )
                )
            )
        update_stats()
        page.update()

    expenses_view_container = ft.Container(
        content=ft.Column([
            ft.Row([
                expense_desc,
                expense_amount,
                category_dropdown,
                ft.IconButton(icon=ft.Icons.ADD_CIRCLE, icon_color=ft.Colors.BLUE_600, tooltip="إضافة تصنيف جديد", on_click=lambda e: setattr(new_cat_dlg, 'open', True) or page.update()),
                ft.ElevatedButton(content=ft.Text("إضافة", color=ft.Colors.WHITE), on_click=add_expense, bgcolor=ft.Colors.GREEN_600, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))
            ]),
            ft.Divider(height=20),
            expenses_list
        ], scroll=ft.ScrollMode.AUTO),
        padding=5,
        expand=True
    )

    content_area.content = tasks_view_container

    def refresh_all_views():
        load_tasks()
        load_expenses()
        load_categories_dropdown()

    main_layout = ft.Column(
        [
            # الكروت العلوية للإحصائيات السريعة (المهام، المصاريف، والإنجازات 🔥)
            ft.Row([
                ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Text("المتبقي", size=11, color=ft.Colors.GREY_400 if page.theme_mode == ft.ThemeMode.DARK else ft.Colors.GREY_700),
                            remaining_tasks_card_text
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        padding=10, width=110
                    ),
                    elevation=2,
                ),
                ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Text("المصاريف", size=11, color=ft.Colors.GREY_400 if page.theme_mode == ft.ThemeMode.DARK else ft.Colors.GREY_700),
                            total_expenses_card_text
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        padding=10, width=110
                    ),
                    elevation=2,
                ),
                ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Text("الإنتاجية", size=11, color=ft.Colors.GREY_400 if page.theme_mode == ft.ThemeMode.DARK else ft.Colors.GREY_700),
                            streak_card_text
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        padding=10, width=110
                    ),
                    elevation=2,
                ),
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=8),

            ft.Divider(height=5, color=ft.Colors.TRANSPARENT),

            # أزرار التنقل بين الأقسام الأربعة
            ft.Row([
                btn_tasks_tab,
                btn_expenses_tab,
                btn_calendar_tab,
                btn_analytics_tab
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=5),

            ft.Divider(height=15),
            
            content_area
        ],
        visible=(get_setting("lock_enabled") != "True"),
        opacity=1.0 if (get_setting("lock_enabled") != "True") else 0.0,
        expand=True,
        animate_opacity=400
    )

    page.add(lock_screen, welcome_screen, main_layout)
    refresh_all_views()
    update_stats()

ft.app(target=main)