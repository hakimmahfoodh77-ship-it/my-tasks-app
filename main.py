import flet as ft
import sqlite3
from datetime import datetime

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
            due_date TEXT
        )
    """)
    try:
        cursor.execute("ALTER TABLE tasks ADD COLUMN due_date TEXT")
    except sqlite3.OperationalError:
        pass

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT,
            amount REAL,
            category TEXT,
            created_at TEXT
        )
    """)
    try:
        cursor.execute("ALTER TABLE expenses ADD COLUMN category TEXT")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()

init_db()

# --- 2. واجهة التطبيق الرئيسية ---
def main(page: ft.Page):
    page.title = "منظّم يومك 🎯"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 10
    page.rtl = True
    page.locale_configuration = ft.LocaleConfiguration(
        supported_locales=[ft.Locale("ar")],
        current_locale=ft.Locale("ar")
    )

    # نظام التنبيهات المخصص بالأيقونات
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

    # --- تغيير الوضع (ليلي / نهاري) ---
    def toggle_theme(e):
        if page.theme_mode == ft.ThemeMode.LIGHT:
            page.theme_mode = ft.ThemeMode.DARK
            theme_btn.icon = ft.Icons.LIGHT_MODE
            theme_btn.icon_color = ft.Colors.AMBER_400
        else:
            page.theme_mode = ft.ThemeMode.LIGHT
            theme_btn.icon = ft.Icons.DARK_MODE
            theme_btn.icon_color = ft.Colors.WHITE
        load_tasks()
        load_expenses()
        page.update()

    theme_btn = ft.IconButton(
        icon=ft.Icons.DARK_MODE,
        icon_color=ft.Colors.WHITE,
        tooltip="تبديل الوضع الليلي/النهاري",
        on_click=toggle_theme
    )

    page.appbar = ft.AppBar(
        title=ft.Text("منظّم يومك 🎯", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
        center_title=True,
        bgcolor=ft.Colors.BLUE_700,
        actions=[theme_btn]
    )

    # --- أ) الشاشة الترحيبية مع حركة انتقال ناعمة ---
    def enter_app(e):
        welcome_screen.opacity = 0.0
        welcome_screen.visible = False
        main_layout.visible = True
        main_layout.opacity = 1.0
        page.update()

    welcome_screen = ft.Container(
        content=ft.Column(
            [
                ft.Icon(ft.Icons.AUTO_AWESOME, size=80, color=ft.Colors.BLUE_700),
                ft.Text("مرحباً بك يا حكيم 👋", size=26, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_900, text_align=ft.TextAlign.CENTER),
                ft.Text("تطبيق منظّم يومك (النسخة المذهلة)", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_800, text_align=ft.TextAlign.CENTER),
                ft.Container(
                    content=ft.Text("تصميم وتطوير: حكيم محفوظ", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_600),
                    padding=8, border_radius=10, bgcolor=ft.Colors.BLUE_50,
                ),
                ft.Divider(height=15, color=ft.Colors.TRANSPARENT),
                ft.Text("« ابتكار الواجهات يبدأ هنا .. نحو إنتاجية بلا حدود »", size=13, italic=True, color=ft.Colors.GREY_600, text_align=ft.TextAlign.CENTER),
                ft.Divider(height=25, color=ft.Colors.TRANSPARENT),
                ft.ElevatedButton(
                    "الدخول لوحة التحكم 🚀",
                    on_click=enter_app,
                    style=ft.ButtonStyle(padding=20, shape=ft.RoundedRectangleBorder(radius=12)),
                ),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        alignment=ft.Alignment(0, 0),
        expand=True,
        animate_opacity=400,
    )

    # عناصر الإحصائيات وشريط التقدم التفاعلي
    total_expenses_card_text = ft.Text("0.00 ريال", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_600)
    remaining_tasks_card_text = ft.Text("0", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700)
    
    progress_bar = ft.ProgressBar(value=0.0, width=320, height=8, border_radius=5, color=ft.Colors.GREEN_500, bgcolor=ft.Colors.GREY_300)
    progress_text = ft.Text("نسبة إنجاز المهام: 0%", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_600)

    def update_stats():
        conn = sqlite3.connect("data.db")
        cur = conn.cursor()
        cur.execute("SELECT SUM(amount) FROM expenses")
        res_exp = cur.fetchone()[0]
        total_exp = res_exp if res_exp else 0.0

        cur.execute("SELECT COUNT(*) FROM tasks")
        total_t = cur.fetchone()[0] or 0
        
        cur.execute("SELECT COUNT(*) FROM tasks WHERE done = 0")
        res_tasks = cur.fetchone()[0]
        rem_tasks = res_tasks if res_tasks else 0
        conn.close()

        total_expenses_card_text.value = f"{total_exp:.2f} ريال"
        remaining_tasks_card_text.value = str(rem_tasks)

        if total_t > 0:
            done_count = total_t - rem_tasks
            ratio = done_count / total_t
            progress_bar.value = ratio
            progress_text.value = f"نسبة إنجاز المهام: {int(ratio * 100)}% ({done_count}/{total_t})"
        else:
            progress_bar.value = 0.0
            progress_text.value = "نسبة إنجاز المهام: 0%"

        page.update()

    # --- ب) واجهة المهام ---
    tasks_list = ft.Column(spacing=8)
    task_filter_mode = {"mode": "all"}

    def add_task(e):
        if task_input.value and task_input.value.strip():
            title = task_input.value.strip()
            now_str = datetime.now().strftime("%Y-%m-%d | %I:%M %p")
            
            due_date_str = ""
            if selected_date_str["date"] or selected_time_str["time"]:
                d = selected_date_str["date"] if selected_date_str["date"] else "اليوم"
                t = selected_time_str["time"] if selected_time_str["time"] else ""
                due_date_str = f"{d} {t}".strip()

            conn = sqlite3.connect("data.db")
            cursor = conn.cursor()
            cursor.execute("INSERT INTO tasks (title, done, created_at, due_date) VALUES (?, 0, ?, ?)", (title, now_str, due_date_str))
            conn.commit()
            conn.close()

            task_input.value = ""
            selected_date_str["date"] = ""
            selected_time_str["time"] = ""
            date_button_text.value = "التاريخ"
            time_button_text.value = "الوقت"
            load_tasks()
            show_snack("تمت إضافة المهمة بنجاح!", icon=ft.Icons.TASK_ALT)

    task_input = ft.TextField(
        hint_text="أدخل مهمة جديدة (واضغط Enter)...", 
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

    date_picker = ft.DatePicker(on_change=on_date_change, confirm_text="موافق", cancel_text="إلغاء")
    time_picker = ft.TimePicker(on_change=on_time_change, confirm_text="موافق", cancel_text="إلغاء")
    page.overlay.extend([date_picker, time_picker])

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
        
        query = "SELECT id, title, done, created_at, due_date FROM tasks WHERE 1=1"
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
            task_id, title, done, created_at, due_date = row
            
            def on_change(e, tid=task_id):
                is_done = e.control.value
                c = sqlite3.connect("data.db")
                cur = c.cursor()
                cur.execute("UPDATE tasks SET done = ? WHERE id = ?", (1 if is_done else 0, tid))
                c.commit()
                c.close()
                load_tasks()

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
                show_snack("تم حذف المهمة", icon=ft.Icons.DELETE_OUTLINE, is_error=True)

            due_info = f" | 📅 الموعد: {due_date}" if due_date else ""
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
                                ft.Text(f"🕒 {created_at}{due_info}", style=ft.TextStyle(size=12, color=ft.Colors.GREY_400 if page.theme_mode == ft.ThemeMode.DARK else ft.Colors.GREY_700)),
                            ],
                            alignment=ft.MainAxisAlignment.CENTER,
                            spacing=2,
                            expand=True,
                        ),
                        ft.IconButton(icon=ft.Icons.EDIT, icon_size=18, icon_color=ft.Colors.BLUE_400, on_click=open_edit_task),
                        ft.IconButton(icon=ft.Icons.DELETE, icon_size=18, icon_color=ft.Colors.RED_400, on_click=delete_task_item, tooltip="اسحب أو اضغط للحذف"),
                    ],
                    alignment=ft.MainAxisAlignment.START,
                ),
                padding=10,
            )

            dismissible_card = ft.Dismissible(
                content=ft.Card(content=task_content),
                background=ft.Container(bgcolor=ft.Colors.RED_400, alignment=ft.Alignment(0.8, 0), padding=ft.padding.symmetric(horizontal=20), content=ft.Icon(ft.Icons.DELETE, color=ft.Colors.WHITE)),
                secondary_background=ft.Container(bgcolor=ft.Colors.RED_400, alignment=ft.Alignment(-0.8, 0), padding=ft.padding.symmetric(horizontal=20), content=ft.Icon(ft.Icons.DELETE, color=ft.Colors.WHITE)),
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
        show_snack("تم تفريغ المهام المكتملة بنجاح", icon=ft.Icons.CLEANING_SERVICES)

    tasks_view_container = ft.Container(
        content=ft.Column([
            ft.Row([
                task_input,
                ft.ElevatedButton("إضافة", on_click=add_task, bgcolor=ft.Colors.GREEN_600, color=ft.Colors.WHITE, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))
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
        ]),
        padding=5
    )

    # --- ج) واجهة المصروفات ---
    expenses_list = ft.Column(spacing=8)
    expense_desc = ft.TextField(hint_text="وصف المصروف...", expand=True, border_radius=10, border_color=ft.Colors.BLUE_400, on_submit=lambda e: add_expense(e))
    expense_amount = ft.TextField(hint_text="المبلغ", width=95, keyboard_type=ft.KeyboardType.NUMBER, border_radius=10, border_color=ft.Colors.BLUE_400, on_submit=lambda e: add_expense(e))
    
    category_dropdown = ft.Dropdown(
        label="التصنيف",
        value="طعام 🍔",
        width=125,
        border_radius=10,
        options=[
            ft.dropdown.Option("طعام 🍔"),
            ft.dropdown.Option("مواصلات 🚗"),
            ft.dropdown.Option("فواتير 💡"),
            ft.dropdown.Option("تسوق 🛍️"),
            ft.dropdown.Option("أخرى 📦"),
        ]
    )

    def add_expense(e):
        if expense_desc.value and expense_amount.value and expense_desc.value.strip() and expense_amount.value.strip():
            try:
                desc = expense_desc.value.strip()
                amt = float(expense_amount.value.strip())
                cat = category_dropdown.value
                now_str = datetime.now().strftime("%Y-%m-%d | %I:%M %p")

                conn = sqlite3.connect("data.db")
                cursor = conn.cursor()
                cursor.execute("INSERT INTO expenses (description, amount, category, created_at) VALUES (?, ?, ?, ?)", (desc, amt, cat, now_str))
                conn.commit()
                conn.close()

                expense_desc.value = ""
                expense_amount.value = ""
                load_expenses()
                show_snack("تمت إضافة المصروف بنجاح", icon=ft.Icons.ATTACH_MONEY)
            except ValueError:
                show_snack("يرجى إدخال مبلغ صحيح!", icon=ft.Icons.ERROR, is_error=True)

    edit_expense_id = {"id": None}
    edit_exp_desc = ft.TextField(label="تعديل الوصف")
    edit_exp_amt = ft.TextField(label="تعديل المبلغ", keyboard_type=ft.KeyboardType.NUMBER)

    def save_edited_expense(e):
        if edit_expense_id["id"] and edit_exp_desc.value.strip() and edit_exp_amt.value.strip():
            try:
                amt = float(edit_exp_amt.value.strip())
                conn = sqlite3.connect("data.db")
                cur = conn.cursor()
                cur.execute("UPDATE expenses SET description = ?, amount = ? WHERE id = ?", (edit_exp_desc.value.strip(), amt, edit_expense_id["id"]))
                conn.commit()
                conn.close()
                edit_expense_dlg.open = False
                load_expenses()
                show_snack("تم تعديل المصروف بنجاح", icon=ft.Icons.CHECK)
            except ValueError:
                pass

    edit_expense_dlg = ft.AlertDialog(
        title=ft.Text("تعديل المصروف"),
        content=ft.Column([edit_exp_desc, edit_exp_amt], tight=True),
        actions=[
            ft.TextButton("حفظ", on_click=save_edited_expense),
            ft.TextButton("إلغاء", on_click=lambda e: setattr(edit_expense_dlg, 'open', False) or page.update())
        ]
    )
    page.overlay.append(edit_expense_dlg)

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

            def open_edit_exp(e, eid=exp_id, d=desc, a=amt):
                edit_expense_id["id"] = eid
                edit_exp_desc.value = d
                edit_exp_amt.value = str(a)
                edit_expense_dlg.open = True
                page.update()

            def delete_expense_item(e, eid=exp_id):
                c = sqlite3.connect("data.db")
                cur = c.cursor()
                cur.execute("DELETE FROM expenses WHERE id = ?", (eid,))
                c.commit()
                c.close()
                load_expenses()
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
                                ft.IconButton(icon=ft.Icons.EDIT, icon_size=18, icon_color=ft.Colors.BLUE_400, on_click=open_edit_exp),
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
                ft.ElevatedButton("إضافة", on_click=add_expense, bgcolor=ft.Colors.GREEN_600, color=ft.Colors.WHITE, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))
            ]),
            ft.Divider(height=20),
            expenses_list
        ]),
        padding=5
    )

    # --- د) أزرار التبديل والأدوات العليا ---
    content_area = ft.Container(content=tasks_view_container, expand=True)

    btn_tasks_tab = ft.ElevatedButton(
        "📋 المهام اليومية",
        bgcolor=ft.Colors.BLUE_700,
        color=ft.Colors.WHITE,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=20), padding=15)
    )
    
    btn_expenses_tab = ft.ElevatedButton(
        "💰 المصروفات",
        bgcolor=ft.Colors.GREY_800 if page.theme_mode == ft.ThemeMode.DARK else ft.Colors.GREY_200,
        color=ft.Colors.WHITE if page.theme_mode == ft.ThemeMode.DARK else ft.Colors.BLACK87,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=20), padding=15)
    )

    def show_tasks_tab(e):
        btn_tasks_tab.bgcolor = ft.Colors.BLUE_700
        btn_tasks_tab.color = ft.Colors.WHITE
        btn_expenses_tab.bgcolor = ft.Colors.GREY_800 if page.theme_mode == ft.ThemeMode.DARK else ft.Colors.GREY_200
        btn_expenses_tab.color = ft.Colors.WHITE if page.theme_mode == ft.ThemeMode.DARK else ft.Colors.BLACK87
        content_area.content = tasks_view_container
        page.update()

    def show_expenses_tab(e):
        btn_expenses_tab.bgcolor = ft.Colors.BLUE_700
        btn_expenses_tab.color = ft.Colors.WHITE
        btn_tasks_tab.bgcolor = ft.Colors.GREY_800 if page.theme_mode == ft.ThemeMode.DARK else ft.Colors.GREY_200
        btn_tasks_tab.color = ft.Colors.WHITE if page.theme_mode == ft.ThemeMode.DARK else ft.Colors.BLACK87
        content_area.content = expenses_view_container
        page.update()

    btn_tasks_tab.on_click = show_tasks_tab
    btn_expenses_tab.on_click = show_expenses_tab

    main_layout = ft.Column(
        [
            ft.Row([
                ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Text("المهام المتبقية", size=12, color=ft.Colors.GREY_400 if page.theme_mode == ft.ThemeMode.DARK else ft.Colors.GREY_700),
                            remaining_tasks_card_text
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        padding=12, width=165
                    ),
                    elevation=2,
                ),
                ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Text("إجمالي المصاريف", size=12, color=ft.Colors.GREY_400 if page.theme_mode == ft.ThemeMode.DARK else ft.Colors.GREY_700),
                            total_expenses_card_text
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        padding=12, width=165
                    ),
                    elevation=2,
                ),
            ], alignment=ft.MainAxisAlignment.CENTER),

            ft.Container(
                content=ft.Column([
                    progress_text,
                    progress_bar
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
                padding=ft.padding.symmetric(vertical=5),
                alignment=ft.Alignment(0, 0)
            ),

            ft.Divider(height=5, color=ft.Colors.TRANSPARENT),

            ft.Row([
                btn_tasks_tab,
                btn_expenses_tab,
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=15),

            ft.Divider(height=15),
            
            content_area
        ],
        scroll=ft.ScrollMode.AUTO,
        expand=True,
        visible=False,
        opacity=0.0,
        animate_opacity=400,
    )

    page.add(welcome_screen, main_layout)
    load_tasks()
    load_expenses()

ft.app(target=main)