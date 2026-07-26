import flet as ft
import sqlite3
from datetime import datetime
import os

# استيراد مكتبة إنشاء الـ PDF
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False

# محاولة استيراد مكتبة الإشعارات والصوت
try:
    from plyer import notification
    HAS_NOTIFICATIONS = True
except ImportError:
    HAS_NOTIFICATIONS = False

def send_task_notification(title, message):
    if HAS_NOTIFICATIONS:
        try:
            notification.notify(
                title=title,
                message=message,
                app_name="منظّم يومك",
                timeout=10
            )
        except Exception:
            pass

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

    # شريط علوي مخصص ومُموّسَط
    page.appbar = ft.AppBar(
        title=ft.Text("منظّم يومك 🎯", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
        center_title=True,
        bgcolor=ft.Colors.BLUE_700,
    )

    pdf_status = ft.Text("", size=14, color=ft.Colors.BLUE_700)

    # دالة تصدير وإنشاء الـ PDF مباشرة (متوافقة مع الهواتف)
    def export_pdf_direct(e):
        try:
            if os.name == 'nt':
                filepath = "expenses_report.pdf"
            else:
                filepath = os.path.join(page.get_storage_dir() if hasattr(page, 'get_storage_dir') else ".", "expenses_report.pdf")
            
            if not filepath or filepath == "expenses_report.pdf":
                filepath = "expenses_report.pdf"

            doc = SimpleDocTemplate(filepath, pagesize=letter)
            elements = []
            styles = getSampleStyleSheet()

            title_style = ParagraphStyle(
                'TitleStyle',
                parent=styles['Heading1'],
                fontSize=18,
                alignment=1,
                spaceAfter=20
            )

            elements.append(Paragraph("<b>Monazzam Yawmak - Expenses Report</b>", title_style))
            elements.append(Spacer(1, 10))

            conn = sqlite3.connect("data.db")
            cursor = conn.cursor()
            cursor.execute("SELECT description, amount, created_at FROM expenses")
            expenses = cursor.fetchall()
            conn.close()

            data = [["Description", "Amount", "Date"]]
            total = 0.0
            for desc, amt, dt in expenses:
                total += amt
                data.append([str(desc), f"{amt:.2f}", str(dt)])

            data.append(["Total Expenses", f"{total:.2f}", ""])

            t = Table(data, colWidths=[200, 100, 150])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1A73E8")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#F1F3F4")),
                ('GRID', (0, 0), (-1, -1), 1, colors.white),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#E8F0FE")),
            ]))

            elements.append(t)
            doc.build(elements)
            pdf_status.value = f"✅ تم حفظ التقرير بنجاح!"
        except Exception as ex:
            pdf_status.value = f"❌ خطأ أثناء الحفظ: {str(ex)}"
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
                ft.Text(
                    "مرحباً بك 👋",
                    size=28,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.BLUE_900,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Text(
                    "تطبيق منظّم يومك",
                    size=20,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.GREY_800,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Container(
                    content=ft.Text(
                        "تصميم وتطوير: حكيم محفوظ",
                        size=14,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.BLUE_600,
                    ),
                    padding=8,
                    border_radius=10,
                    bgcolor=ft.Colors.BLUE_50,
                ),
                ft.Divider(height=15, color=ft.Colors.TRANSPARENT),
                ft.Text(
                    "« تنظيم يومك هو أول خطوات نجاحك »",
                    size=13,
                    italic=True,
                    color=ft.Colors.GREY_600,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Divider(height=25, color=ft.Colors.TRANSPARENT),
                ft.ElevatedButton(
                    "الدخول للتطبيق 🚀",
                    on_click=enter_app,
                    style=ft.ButtonStyle(
                        padding=20,
                        shape=ft.RoundedRectangleBorder(radius=12),
                    ),
                ),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        alignment=ft.Alignment(0, 0),
        expand=True,
    )

    # --- ب) واجهة المهام مع ميزة التعديل والحذف ---
    tasks_list = ft.Column()
    task_input = ft.TextField(hint_text="أدخل مهمة جديدة...", expand=True)
    
    selected_date_str = {"date": ""}
    selected_time_str = {"time": ""}

    date_button_text = ft.Text("اختر التاريخ", size=12)
    time_button_text = ft.Text("اختر الوقت", size=12)

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

    # نافذة منبثقة لتعديل المهمة
    edit_task_id = {"id": None}
    edit_task_input = ft.TextField(label="تعديل نص المهمة")

    def save_edited_task(e):
        if edit_task_id["id"] and edit_task_input.value.strip():
            conn = sqlite3.connect("data.db")
            cur = conn.cursor()
            cur.execute("UPDATE tasks SET title = ? WHERE id = ?", (edit_task_input.value.strip(), edit_task_id["id"]))
            conn.commit()
            conn.close()
            edit_task_dlg.open = False
            load_tasks()

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
                                    ft.Text(
                                        f"🕒 أُضيفت: {created_at}{due_info}", 
                                        style=ft.TextStyle(size=12, color=ft.Colors.GREY_700)
                                    ),
                                ],
                                alignment=ft.MainAxisAlignment.CENTER,
                                spacing=2,
                                expand=True,
                            ),
                            ft.IconButton(icon=ft.Icons.EDIT, icon_size=18, icon_color=ft.Colors.BLUE, on_click=open_edit_task),
                            ft.IconButton(icon=ft.Icons.DELETE, icon_size=18, icon_color=ft.Colors.RED, on_click=delete_task_item),
                        ],
                        alignment=ft.MainAxisAlignment.START,
                    ),
                    padding=10,
                )
            )
            tasks_list.controls.append(task_card)
        page.update()

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

            notification_msg = f"تم تسجيل المهمة: '{title}'"
            if due_date_str:
                notification_msg += f" (الموعد: {due_date_str})"

            send_task_notification(
                title="تذكير بمهمة جديدة 📌",
                message=notification_msg
            )

            task_input.value = ""
            selected_date_str["date"] = ""
            selected_time_str["time"] = ""
            date_button_text.value = "اختر التاريخ"
            time_button_text.value = "اختر الوقت"
            load_tasks()

    tasks_view = ft.Container(
        content=ft.Column([
            ft.Text("📋 قائمة المهام اليومية", size=18, weight=ft.FontWeight.BOLD),
            ft.Row([
                task_input,
                ft.FloatingActionButton(icon=ft.Icons.ADD, on_click=add_task)
            ]),
            ft.Row([
                ft.OutlinedButton(
                    content=ft.Row([ft.Icon(ft.Icons.CALENDAR_MONTH, size=16), date_button_text]),
                    on_click=open_date_picker
                ),
                ft.OutlinedButton(
                    content=ft.Row([ft.Icon(ft.Icons.ACCESS_TIME, size=16), time_button_text]),
                    on_click=open_time_picker
                ),
            ]),
            ft.Divider(),
            tasks_list
        ]),
        padding=10
    )

    # --- ج) واجهة المصروفات مع ميزة التعديل والحذف ---
    expenses_list = ft.Column()
    expense_desc = ft.TextField(hint_text="وصف المصروف", expand=True)
    expense_amount = ft.TextField(hint_text="المبلغ", width=100, keyboard_type=ft.KeyboardType.NUMBER)
    total_text = ft.Text("الإجمالي: 0 ريال", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_700)

    # نافذة منبثقة لتعديل المصروف
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

        total = 0.0
        for row in rows:
            exp_id, desc, amt, created_at = row
            total += amt

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
                                ft.IconButton(icon=ft.Icons.DELETE, icon_size=18, icon_color=ft.Colors.RED, on_click=delete_expense_item),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        padding=10,
                    )
                )
            )
        total_text.value = f"الإجمالي: {total:.2f} ريال"
        page.update()

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
            except ValueError:
                pass

    expenses_view = ft.Container(
        content=ft.Column([
            ft.Text("💰 المصروفات اليومية", size=18, weight=ft.FontWeight.BOLD),
            ft.Row([
                expense_desc,
                expense_amount,
            ]),
            ft.Row([
                ft.ElevatedButton("إضافة مصروف", icon=ft.Icons.ATTACH_MONEY, on_click=add_expense),
                ft.ElevatedButton("تصدير تقرير PDF", icon=ft.Icons.PICTURE_AS_PDF, on_click=export_pdf_direct),
            ]),
            pdf_status,
            ft.Divider(),
            total_text,
            expenses_list
        ]),
        padding=10
    )

    # --- د) التنقل بين الأقسام ---
    content_area = ft.Container(content=tasks_view, expand=True)

    def show_tasks(e):
        content_area.content = tasks_view
        page.update()

    def show_expenses(e):
        content_area.content = expenses_view
        page.update()

    nav_bar = ft.Row([
        ft.OutlinedButton("📋 المهام", on_click=show_tasks),
        ft.OutlinedButton("💰 المصروفات", on_click=show_expenses),
    ], alignment=ft.MainAxisAlignment.CENTER)

    main_layout = ft.Column(
        [
            nav_bar,
            content_area,
        ],
        expand=True,
        visible=False,
    )

    page.add(welcome_screen, main_layout)
    load_tasks()
    load_expenses()

ft.app(target=main)