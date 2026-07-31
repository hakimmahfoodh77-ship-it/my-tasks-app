import flet as ft
import sqlite3
from datetime import datetime

# --- 1. إعداد قاعدة البيانات ---
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
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# --- 2. واجهة التطبيق الرئيسية ---
def main(page: ft.Page):
    page.title = "منظّم يومك"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 10
    page.rtl = True
    page.locale_configuration = ft.LocaleConfiguration(
        supported_locales=[ft.Locale("ar")],
        current_locale=ft.Locale("ar")
    )

    page.appbar = ft.AppBar(
        title=ft.Text("منظّم يومك 🎯", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
        center_title=True,
        bgcolor=ft.Colors.BLUE_700,
    )

    def show_snack(message, is_error=False):
        page.snack_bar = ft.SnackBar(
            content=ft.Text(message, color=ft.Colors.WHITE),
            bgcolor=ft.Colors.RED_700 if is_error else ft.Colors.GREEN_700
        )
        page.snack_bar.open = True
        page.update()

    # --- أ) الشاشة الترحيبية ---
    def enter_app(e):
        welcome_screen.visible = False
        main_layout.visible = True
        page.update()

    welcome_screen = ft.Container(
        content=ft.Column(
            [
                ft.Icon(ft.Icons.DASHBOARD_CUSTOMIZE_ROUNDED, size=80, color=ft.Colors.BLUE_700),
                ft.Text("مرحباً بك 👋", size=28, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_900, text_align=ft.TextAlign.CENTER),
                ft.Text("تطبيق منظّم يومك", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_800, text_align=ft.TextAlign.CENTER),
                ft.Container(
                    content=ft.Text("تصميم وتطوير: حكيم محفوظ", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_600),
                    padding=8, border_radius=10, bgcolor=ft.Colors.BLUE_50,
                ),
                ft.Divider(height=15, color=ft.Colors.TRANSPARENT),
                ft.Text("« تنظيم يومك هو أول خطوات نجاحك »", size=13, italic=True, color=ft.Colors.GREY_600, text_align=ft.TextAlign.CENTER),
                ft.Divider(height=25, color=ft.Colors.TRANSPARENT),
                ft.ElevatedButton(
                    "الدخول للتطبيق 🚀",
                    on_click=enter_app,
                    style=ft.ButtonStyle(padding=20, shape=ft.RoundedRectangleBorder(radius=12)),
                ),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        alignment=ft.Alignment(0, 0),
        expand=True,
    )

    # إحصائيات علوية
    total_expenses_card_text = ft.Text("0.00 ريال", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_600)
    remaining_tasks_card_text = ft.Text("0", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700)

    def update_stats():
        conn = sqlite3.connect("data.db")
        cur = conn.cursor()
        cur.execute("SELECT SUM(amount) FROM expenses")
        res_exp = cur.fetchone()[0]
        total_exp = res_exp if res_exp else 0.0

        cur.execute("SELECT COUNT(*) FROM tasks WHERE done = 0")
        res_tasks = cur.fetchone()[0]
        rem_tasks = res_tasks if res_tasks else 0
        conn.close()

        total_expenses_card_text.value = f"{total_exp:.2f} ريال"
        remaining_tasks_card_text.value = str(rem_tasks)
        page.update()

    # --- ب) واجهة المهام ---
    tasks_list = ft.Column(spacing=8)

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
            show_snack(f"📌 تمت إضافة المهمة بنجاح!")

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
            hour = time_obj.hour
            minute = time_obj.minute
            period = "م" if hour >= 12 else "ص"
            hour_12 = hour % 12
            if hour_12 == 0:
                hour_12 = 12
            formatted_time = f"{hour_12:02d}:{minute:02d} {period}"
            
            selected_time_str["time"] = formatted_time
            time_button_text.value = f"⏰ {selected_time_str['time']}"
            page.update()

    date_picker = ft.DatePicker(on_change=on_date_change, confirm_text="موافق", cancel_text="إلغاء")
    time_picker = ft.TimePicker(on_change=on_time_change, confirm_text="موافق", cancel_text="إلغاء")
    page.overlay.extend([date_picker, time_picker])

    def open_date_picker(e):
        date_picker.open = True
        page.update()

    def open_time_picker(e):
        time_picker.open = True
        page.update()

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
            show_snack("تم تعديل المهمة بنجاح ✅")

    edit_task_dlg = ft.AlertDialog(
        title=ft.Text("تعديل المهمة"),
        content=edit_task_input,
        actions=[
            ft.TextButton("حفظ", on_click=save_edited_task),
            ft.TextButton("إلغاء", on_click=lambda e: setattr(edit_task_dlg, 'open', False) or page.update())
        ]
    )
    page.overlay.append(edit_task_dlg)

    def load_tasks():
        tasks_list.controls.clear()
        conn = sqlite3.connect("data.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, done, created_at, due_date FROM tasks")
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
                show_snack("تم حذف المهمة بنجاح")

            due_info = f" | 📅 الموعد: {due_date}" if due_date else ""
            
            task_card = ft.Card(
                content=ft.Container(
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
                                            color=ft.Colors.GREY_500 if done else ft.Colors.BLACK87
                                        )
                                    ),
                                    ft.Text(f"🕒 {created_at}{due_info}", style=ft.TextStyle(size=12, color=ft.Colors.GREY_700)),
                                ],
                                alignment=ft.MainAxisAlignment.CENTER,
                                spacing=2,
                                expand=True,
                            ),
                            ft.IconButton(icon=ft.Icons.EDIT, icon_size=18, icon_color=ft.Colors.BLUE, on_click=open_edit_task),
                            ft.TextButton("حذف", on_click=delete_task_item, style=ft.ButtonStyle(color=ft.Colors.RED_500)),
                        ],
                        alignment=ft.MainAxisAlignment.START,
                    ),
                    padding=10,
                )
            )
            tasks_list.controls.append(task_card)
        update_stats()
        page.update()

    tasks_view_container = ft.Container(
        content=ft.Column([
            ft.Row([
                task_input,
                ft.ElevatedButton("إضافة", on_click=add_task, bgcolor=ft.Colors.GREEN_600, color=ft.Colors.WHITE, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))
            ]),
            ft.Row([
                ft.OutlinedButton(content=ft.Row([ft.Icon(ft.Icons.CALENDAR_MONTH, size=16), date_button_text]), on_click=open_date_picker),
                ft.OutlinedButton(content=ft.Row([ft.Icon(ft.Icons.ACCESS_TIME, size=16), time_button_text]), on_click=open_time_picker),
            ]),
            ft.Divider(height=20),
            tasks_list
        ]),
        padding=5
    )

    # --- ج) واجهة المصروفات ---
    expenses_list = ft.Column(spacing=8)

    def add_expense(e):
        if expense_desc.value and expense_amount.value and expense_desc.value.strip() and expense_amount.value.strip():
            try:
                desc = expense_desc.value.strip()
                amt = float(expense_amount.value.strip())
                now_str = datetime.now().strftime("%Y-%m-%d | %I:%M %p")

                conn = sqlite3.connect("data.db")
                cursor = conn.cursor()
                cursor.execute("INSERT INTO expenses (description, amount, created_at) VALUES (?, ?, ?)", (desc, amt, now_str))
                conn.commit()
                conn.close()

                expense_desc.value = ""
                expense_amount.value = ""
                load_expenses()
                show_snack(" تمت إضافة المصروف بنجاح")
            except ValueError:
                pass

    expense_desc = ft.TextField(
        hint_text="وصف المصروف...", 
        expand=True, 
        border_radius=10, 
        border_color=ft.Colors.BLUE_400,
        on_submit=add_expense
    )
    expense_amount = ft.TextField(
        hint_text="المبلغ", 
        width=110, 
        keyboard_type=ft.KeyboardType.NUMBER, 
        border_radius=10, 
        border_color=ft.Colors.BLUE_400,
        on_submit=add_expense
    )

    edit_expense_id = {"id": None}
    edit_exp_desc = ft.TextField(label="تعديل الوصف")
    edit_exp_amt = ft.TextField(label="تعديل المبلغ", keyboard_type=ft.KeyboardType.NUMBER, on_submit=lambda e: save_edited_expense(e))

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
                show_snack("تم تعديل المصروف بنجاح ✅")
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
        cursor.execute("SELECT id, description, amount, created_at FROM expenses")
        rows = cursor.fetchall()
        conn.close()

        for row in rows:
            exp_id, desc, amt, created_at = row

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
                show_snack("تم حذف المصروف")

            expenses_list.controls.append(
                ft.Card(
                    content=ft.Container(
                        content=ft.Row(
                            [
                                ft.Icon(ft.Icons.MONEY_OFF, color=ft.Colors.RED_400),
                                ft.Column(
                                    [
                                        ft.Text(desc, size=15, weight=ft.FontWeight.BOLD),
                                        ft.Text(f"🕒 {created_at}", size=11, color=ft.Colors.GREY_700),
                                    ],
                                    expand=True,
                                    spacing=2,
                                ),
                                ft.Text(f"{amt:.2f} ريال", weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_800),
                                ft.IconButton(icon=ft.Icons.EDIT, icon_size=18, icon_color=ft.Colors.BLUE, on_click=open_edit_exp),
                                ft.TextButton("حذف", on_click=delete_expense_item, style=ft.ButtonStyle(color=ft.Colors.RED_500)),
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
                ft.ElevatedButton("إضافة", on_click=add_expense, bgcolor=ft.Colors.GREEN_600, color=ft.Colors.WHITE, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))
            ]),
            ft.Divider(height=20),
            expenses_list
        ]),
        padding=5
    )

    # --- د) أزرار التبديل ---
    content_area = ft.Container(content=tasks_view_container, expand=True)

    btn_tasks_tab = ft.ElevatedButton(
        "المهام اليومية",
        bgcolor=ft.Colors.BLUE_700,
        color=ft.Colors.WHITE,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=20), padding=15)
    )
    
    btn_expenses_tab = ft.ElevatedButton(
        "المصروفات",
        bgcolor=ft.Colors.GREY_200,
        color=ft.Colors.BLACK87,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=20), padding=15)
    )

    def show_tasks_tab(e):
        btn_tasks_tab.bgcolor = ft.Colors.BLUE_700
        btn_tasks_tab.color = ft.Colors.WHITE
        btn_expenses_tab.bgcolor = ft.Colors.GREY_200
        btn_expenses_tab.color = ft.Colors.BLACK87
        content_area.content = tasks_view_container
        page.update()

    def show_expenses_tab(e):
        btn_expenses_tab.bgcolor = ft.Colors.BLUE_700
        btn_expenses_tab.color = ft.Colors.WHITE
        btn_tasks_tab.bgcolor = ft.Colors.GREY_200
        btn_tasks_tab.color = ft.Colors.BLACK87
        content_area.content = expenses_view_container
        page.update()

    btn_tasks_tab.on_click = show_tasks_tab
    btn_expenses_tab.on_click = show_expenses_tab

    main_layout = ft.Column(
        [
            # بطاقات الإحصائيات العلوية (تم عكس مكانها: المهام في اليمين، المصاريف في اليسار)
            ft.Row([
                ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Text("المهام المتبقية", size=12, color=ft.Colors.GREY_700),
                            remaining_tasks_card_text
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        padding=12, width=165
                    ),
                    elevation=2,
                ),
                ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Text("إجمالي المصاريف", size=12, color=ft.Colors.GREY_700),
                            total_expenses_card_text
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        padding=12, width=165
                    ),
                    elevation=2,
                ),
            ], alignment=ft.MainAxisAlignment.CENTER),

            ft.Divider(height=10, color=ft.Colors.TRANSPARENT),

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
    )

    page.add(welcome_screen, main_layout)
    load_tasks()
    load_expenses()

ft.app(target=main)