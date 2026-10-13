"""Экран «Отчёты»: формирование за период и экспорт."""

from datetime import date, datetime, timedelta

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from services.payment_service import PaymentService
from services.report_service import ReportService
from services.attendance_service import AttendanceService
from ui.theme import make_header


class ReportsView:
    """Отчёты за период с экспортом в Excel и PDF."""

    KINDS = ("Посещаемость за период", "Оплаты за период")

    def __init__(self, parent: tk.Widget, session) -> None:
        """Инициализирует экран.

        Args:
            parent: родительский виджет.
            session: сессия SQLAlchemy.
        """
        self.session = session
        self.service = ReportService(session)
        self.current_headers: tuple = ()
        self.current_rows: list = []

        self.frame = tk.Frame(parent, bg="#f5f6fa")
        self.frame.pack(fill=tk.BOTH, expand=True)

        make_header(self.frame, "Отчёты")

        controls = tk.Frame(self.frame, bg="white", padx=20, pady=14)
        controls.pack(fill=tk.X, pady=(14, 0))

        self.kind_combo = ttk.Combobox(
            controls, state="readonly", values=list(self.KINDS), width=24
        )
        self.kind_combo.current(0)
        self.kind_combo.pack(side=tk.LEFT)

        today = date.today()
        month_start = today.replace(day=1)
        self.start_entry = self._date_field(controls, month_start)
        self.end_entry = self._date_field(controls, today)

        ttk.Button(
            controls,
            text="Сформировать",
            style="Primary.TButton",
            command=self._on_build,
        ).pack(side=tk.LEFT, padx=(14, 6))
        ttk.Button(
            controls,
            text="Экспорт PDF",
            style="Secondary.TButton",
            command=self._export_pdf,
        ).pack(side=tk.LEFT, padx=6)
        ttk.Button(
            controls,
            text="Экспорт Excel",
            style="Secondary.TButton",
            command=self._export_excel,
        ).pack(side=tk.LEFT)

        card = tk.Frame(self.frame, bg="white", padx=20, pady=16)
        card.pack(fill=tk.BOTH, expand=True, pady=(14, 0))
        self.summary_label = tk.Label(card, text="", bg="white", fg="#6b7590")
        self.summary_label.pack(anchor="w", pady=(0, 8))

        wrapper = tk.Frame(card, bg="white")
        wrapper.pack(fill=tk.BOTH, expand=True)
        self.table = ttk.Treeview(
            wrapper, columns=(), show="headings", selectmode="browse"
        )
        scrollbar = ttk.Scrollbar(wrapper, orient=tk.VERTICAL, command=self.table.yview)
        self.table.configure(yscrollcommand=scrollbar.set)
        self.table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self._on_build()

    def _date_field(self, parent: tk.Widget, value: date) -> ttk.Entry:
        """Создаёт поле даты с предзаполнением.

        Args:
            parent: родительский контейнер.
            value: начальное значение.

        Returns:
            Поле ввода даты.
        """
        entry = ttk.Entry(parent, width=12)
        entry.insert(0, value.strftime("%d.%m.%Y"))
        entry.pack(side=tk.LEFT, padx=6)
        return entry

    @staticmethod
    def _parse_date(text: str) -> date | None:
        """Разбирает дату дд.мм.гггг или возвращает None."""
        try:
            return datetime.strptime(text.strip(), "%d.%m.%Y").date()
        except ValueError:
            return None

    def _on_build(self) -> None:
        """Формирует отчёт по выбранным параметрам."""
        start = self._parse_date(self.start_entry.get())
        end = self._parse_date(self.end_entry.get())
        if start is None or end is None or start > end:
            messagebox.showerror(
                "Отчёты",
                "Даты должны быть в формате дд.мм.гггг, " "начало — не позже конца",
                parent=self.frame,
            )
            return

        headers, rows = self.service.build_report(self.kind_combo.get(), start, end)
        self.current_headers, self.current_rows = headers, rows

        columns = tuple(f"col{i}" for i in range(len(headers)))
        self.table["columns"] = columns
        for column, header_text in zip(columns, headers):
            self.table.heading(column, text=header_text)
            self.table.column(column, width=130, anchor=tk.W)
        self.table.delete(*self.table.get_children())
        for index, row in enumerate(rows, start=1):
            self.table.insert("", tk.END, values=(index,) + row)

        self.summary_label.config(
            text=f"Всего записей: {len(rows)}    Период: {start:%d.%m.%Y} — {end:%d.%m.%Y}"
        )

    def _export_excel(self) -> None:
        """Экспортирует текущий отчёт в Excel (или CSV при отсутствии openpyxl)."""
        if not self.current_rows:
            messagebox.showinfo(
                "Отчёты", "Сначала сформируйте отчёт", parent=self.frame
            )
            return
        try:
            from openpyxl import Workbook
        except ImportError:
            path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV", "*.csv")],
                parent=self.frame,
            )
            if not path:
                return
            import csv

            with open(path, "w", newline="", encoding="utf-8-sig") as file:
                csv.writer(file).writerows([self.current_headers, *self.current_rows])
            messagebox.showinfo(
                "Отчёты",
                "Библиотека openpyxl не установлена (pip install openpyxl), "
                "отчёт сохранён в CSV",
                parent=self.frame,
            )
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            parent=self.frame,
        )
        if not path:
            return
        workbook = Workbook()
        sheet = workbook.active
        sheet.append(list(self.current_headers))
        for row in self.current_rows:
            sheet.append([str(value) for value in row])
        workbook.save(path)
        messagebox.showinfo("Отчёты", f"Сохранено: {path}", parent=self.frame)

    def _export_pdf(self) -> None:
        """Экспортирует отчёт в PDF (или TXT при отсутствии reportlab)."""
        if not self.current_rows:
            messagebox.showinfo(
                "Отчёты", "Сначала сформируйте отчёт", parent=self.frame
            )
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf"), ("Текст", "*.txt")],
            parent=self.frame,
        )
        if not path:
            return
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle

            pdfmetrics.registerFont(TTFont("DejaVu", "C:/Windows/Fonts/DejaVuSans.ttf"))
            document = SimpleDocTemplate(path, pagesize=A4)
            data = [list(self.current_headers)] + [
                [str(value) for value in row] for row in self.current_rows
            ]
            table = Table(data)
            table.setStyle(
                TableStyle(
                    [
                        ("FONTNAME", (0, 0), (-1, -1), "DejaVu"),
                        ("FONTSIZE", (0, 0), (-1, -1), 9),
                        ("BACKGROUND", (0, 0), (-1, 0), "#eceef2"),
                        ("GRID", (0, 0), (-1, -1), 0.4, "#c9ced8"),
                    ]
                )
            )
            document.build([table])
            messagebox.showinfo("Отчёты", f"Сохранено: {path}", parent=self.frame)
        except Exception:
            with open(path.rsplit(".", 1)[0] + ".txt", "w", encoding="utf-8") as file:
                file.write("\t".join(self.current_headers) + "\n")
                for row in self.current_rows:
                    file.write("\t".join(str(value) for value in row) + "\n")
            messagebox.showinfo(
                "Отчёты",
                "PDF-библиотека недоступна, отчёт сохранён как TXT",
                parent=self.frame,
            )
