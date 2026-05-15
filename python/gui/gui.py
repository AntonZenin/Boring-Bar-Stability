# gui.py
# Графический интерфейс для исследования устойчивости состояния равновесия
# расточной борштанги при крутильных колебаниях методом D-разбиения.
#
# Архитектура:
#   - Tkinter форма с полями ввода всех физических параметров
#   - При нажатии "Построить" вызывается внешний бинарь dpartition (C++)
#   - Вывод C++ парсится, точки рисуются на canvas matplotlib
#
# Запуск: python3 gui.py
# Требуется: скомпилированный бинарь ./dpartition рядом со скриптом.

import os
import sys
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox

import numpy as np
import matplotlib

matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg,
    NavigationToolbar2Tk,
)


# Путь к C++ исполняемому файлу. Ищем рядом со скриптом.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DPARTITION_BIN = os.path.join(SCRIPT_DIR, "dpartition")
if os.name == "nt":
    DPARTITION_BIN += ".exe"


# Описание параметров: (внутренний ключ, подпись, единицы, значение по
# умолчанию). Значения по умолчанию взяты из отчёта — пользователь может
# править их в окне.
PARAM_SPECS = [
    ("rho",    "Плотность материала ρ",                   "кг/м³",     "7800"),
    ("G",      "Модуль сдвига G",                         "Па",        "8e10"),
    ("R_out",  "Внешний радиус борштанги R",              "м",         "0.04"),
    ("R_in",   "Внутренний радиус борштанги r",           "м",         "0.02"),
    ("r_out",  "Внешний радиус режущей головки R_h",      "м",         "0.05"),
    ("r_in",   "Внутренний радиус режущей головки r_h",   "м",         "0.025"),
    ("l_head", "Длина режущей головки l_h",               "м",         "0.1"),
    ("Jr",     "Момент инерции головки J_r (0 = авто)",   "кг·м²",     "2.5"),
    ("delta1", "Внутреннее трение δ₁ (sigma)",            "-",         "3.44e-6"),
    ("L",      "Длина борштанги L",                       "м",         "2.5"),
    ("w_min",  "ω минимальная",                           "рад/с",     "10"),
    ("w_max",  "ω максимальная",                          "рад/с",     "20000"),
    ("N",      "Число точек по ω",                        "-",         "20000"),
]


class DPartitionApp:
    def __init__(self, root):
        self.root = root
        self.root.title(
            "D-разбиение: устойчивость крутильных колебаний расточной борштанги"
        )
        self.root.geometry("1200x780")

        self.entries = {}
        self._build_ui()

    # ---------- построение интерфейса ----------

    def _build_ui(self):
        # Главный делитель: слева панель параметров, справа график.
        main = ttk.Frame(self.root, padding=8)
        main.pack(fill=tk.BOTH, expand=True)

        # === Левая колонка: ввод параметров ===
        left = ttk.LabelFrame(main, text="Параметры модели", padding=10)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))

        for i, (key, label, unit, default) in enumerate(PARAM_SPECS):
            ttk.Label(left, text=label).grid(
                row=i, column=0, sticky=tk.W, pady=2
            )
            entry = ttk.Entry(left, width=14)
            entry.insert(0, default)
            entry.grid(row=i, column=1, padx=(6, 4), pady=2)
            ttk.Label(left, text=unit, foreground="#555").grid(
                row=i, column=2, sticky=tk.W
            )
            self.entries[key] = entry

        # Кнопки
        btn_row = ttk.Frame(left)
        btn_row.grid(row=len(PARAM_SPECS), column=0, columnspan=3,
                     pady=(12, 0), sticky=tk.EW)

        ttk.Button(btn_row, text="Построить", command=self.on_plot).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Button(btn_row, text="Сбросить", command=self.on_reset).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Button(btn_row, text="Очистить график",
                   command=self.on_clear).pack(side=tk.LEFT, padx=2)

        # Чекбокс: сохранять предыдущие кривые на графике для сравнения.
        self.hold_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            left,
            text="Накладывать кривые (для сравнения)",
            variable=self.hold_var,
        ).grid(row=len(PARAM_SPECS) + 1, column=0, columnspan=3,
               sticky=tk.W, pady=(8, 0))
        self.ticks_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            left,
            text="Показывать штрихи D-разбиения",
            variable=self.ticks_var,
        ).grid(row=len(PARAM_SPECS) + 2, column=0, columnspan=3,
               sticky=tk.W, pady=(2, 0))

        # Поле статуса (выводим λ₁, λ₂ и т.п.)
        self.status_var = tk.StringVar(value="Готов к расчёту.")
        status = ttk.Label(left, textvariable=self.status_var,
                          foreground="#0066aa", wraplength=260,
                          justify=tk.LEFT)
        status.grid(row=len(PARAM_SPECS) + 3, column=0, columnspan=3,
                    sticky=tk.W, pady=(12, 0))

        # === Правая часть: график matplotlib ===
        right = ttk.Frame(main)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.fig = Figure(figsize=(7, 6), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self._reset_axes()

        self.canvas = FigureCanvasTkAgg(self.fig, master=right)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        toolbar = NavigationToolbar2Tk(self.canvas, right)
        toolbar.update()

        # Счётчик кривых — для разных цветов при "наложении".
        self._curve_count = 0

    def _reset_axes(self):
        """Настраивает оси: подписи как на рисунке из отчёта."""
        self.ax.clear()
        self.ax.set_title("Кривая D-разбиения")
        self.ax.set_xlabel(r"$\mathrm{Re}\,\hat{\delta}$")
        self.ax.set_ylabel(r"$\mathrm{Im}\,\hat{\delta}$")
        self.ax.grid(True, linestyle="--", alpha=0.5)
        self.ax.axhline(0, color="black", linewidth=0.5)
        self.ax.axvline(0, color="black", linewidth=0.5)

    # ---------- обработчики кнопок ----------

    def on_plot(self):
        try:
            params = self._read_params()
        except ValueError as e:
            messagebox.showerror("Ошибка ввода", str(e))
            return

        if not os.path.exists(DPARTITION_BIN):
            messagebox.showerror(
                "Бинарь не найден",
                f"Не найден исполняемый файл {DPARTITION_BIN}.\n"
                f"Скомпилируйте C++ модуль командой:\n"
                f"  g++ -O2 -std=c++17 -o dpartition dpartition.cpp"
            )
            return

        # Запускаем C++ программу с параметрами; читаем stdout/stderr.
        try:
            result = self._run_solver(params)
        except subprocess.CalledProcessError as e:
            messagebox.showerror(
                "Ошибка C++ модуля",
                f"dpartition завершился с кодом {e.returncode}.\n"
                f"stderr:\n{e.stderr}"
            )
            return
        except Exception as e:
            messagebox.showerror("Ошибка запуска", str(e))
            return

        omega, re, im = result["points"]
        if omega.size == 0:
            messagebox.showwarning(
                "Нет данных",
                "C++ модуль не вернул ни одной точки."
            )
            return

        # Вблизи резонансов δ̂ имеет полюсы — значения уходят в
        # бесконечность. Вместо того, чтобы удалять такие точки
        # (тогда matplotlib соединит соседей через весь экран
        # длинной прямой), вставляем туда NaN — это разрывает
        # линию, как и должно быть для кривой с разрывом.
        mag = np.hypot(re, im)
        if mag.size > 10:
            cap = 50.0 * np.median(mag)
            re = np.where(mag < cap, re, np.nan)
            im = np.where(mag < cap, im, np.nan)

        # Рисуем. Если не "наложение" — очищаем.
        if not self.hold_var.get():
            self._reset_axes()
            self._curve_count = 0

        # Чтобы кривая выглядела как на рисунке из отчёта (с короткими
        # "усиками" — штрихами от каждой точки наружу), нарисуем
        # сам контур и редкие тики. Тики ставим, чтобы пометить
        # направление обхода по omega (это важно для метода D-разбиения).
        label = (f"L={params['L']:g} м, δ₁={params['delta1']:g}, "
                 f"ω∈[{params['w_min']:g}, {params['w_max']:g}]")

        color = f"C{self._curve_count % 10}"
        self.ax.plot(re, im, "-", color=color, linewidth=1.2, label=label)

        # Точка с минимальным |Im| — там, где кривая пересекает Re-ось:
        # это та самая характеристическая точка из отчёта (-94.84; 2.04).
        i_cross = int(np.argmin(np.abs(im)))
        self.ax.plot(re[i_cross], im[i_cross], "s",
                     color=color, markersize=6)
        self.ax.annotate(
            f"  Re={re[i_cross]:.3g}\n  Im={im[i_cross]:.3g}",
            xy=(re[i_cross], im[i_cross]),
            xytext=(8, 8), textcoords="offset points",
            fontsize=8, color=color,
        )

        # Штрихи-усики, направленные перпендикулярно кривой — как на
        # рис. 4 из отчёта. Это визуализация D-разбиения: штрих указывает
        # в сторону "области с большим числом неустойчивых корней".
        if self.ticks_var.get():
            self._draw_hatch_ticks(re, im, color=color)

        self.ax.legend(loc="best", fontsize=8)
        self.ax.relim()
        self.ax.autoscale_view()
        self.canvas.draw_idle()

        self._curve_count += 1
        meta = result["meta"]
        self.status_var.set(
            f"Готово. Точек: {omega.size}.\n"
            f"{meta}\n"
            f"Re-пересечение: {re[i_cross]:.4g}, "
            f"Im там: {im[i_cross]:.4g}."
        )

    def on_reset(self):
        """Возвращает все поля к значениям по умолчанию."""
        for key, _, _, default in PARAM_SPECS:
            self.entries[key].delete(0, tk.END)
            self.entries[key].insert(0, default)
        self.status_var.set("Параметры сброшены.")

    def on_clear(self):
        """Очищает график."""
        self._reset_axes()
        self._curve_count = 0
        self.canvas.draw_idle()
        self.status_var.set("График очищен.")

    # ---------- внутренние ----------

    def _read_params(self):
        """Читает значения из полей ввода в dict с проверкой типов."""
        p = {}
        for key, label, _, _ in PARAM_SPECS:
            raw = self.entries[key].get().strip().replace(",", ".")
            if raw == "":
                raise ValueError(f"Поле '{label}' пустое.")
            try:
                if key == "N":
                    val = int(float(raw))
                else:
                    val = float(raw)
            except ValueError:
                raise ValueError(
                    f"Не удаётся разобрать значение '{raw}' "
                    f"в поле '{label}'."
                )
            p[key] = val

        # Базовая валидация.
        if p["R_out"] <= p["R_in"]:
            raise ValueError("R_out должен быть больше R_in (борштанга-труба).")
        if p["r_out"] <= p["r_in"]:
            raise ValueError("r_out должен быть больше r_in (головка-труба).")
        if p["L"] <= 0 or p["rho"] <= 0 or p["G"] <= 0:
            raise ValueError("ρ, G, L должны быть положительны.")
        if p["w_max"] <= p["w_min"]:
            raise ValueError("ω_max должен быть больше ω_min.")
        if p["N"] < 2:
            raise ValueError("Число точек N должно быть ≥ 2.")
        return p

    def _run_solver(self, p):
        """Вызывает C++ бинарь, парсит вывод."""
        args = [
            DPARTITION_BIN,
            f"{p['rho']:.12g}",
            f"{p['G']:.12g}",
            f"{p['R_out']:.12g}",
            f"{p['R_in']:.12g}",
            f"{p['r_out']:.12g}",
            f"{p['r_in']:.12g}",
            f"{p['l_head']:.12g}",
            f"{p['Jr']:.12g}",
            f"{p['delta1']:.12g}",
            f"{p['L']:.12g}",
            f"{p['w_min']:.12g}",
            f"{p['w_max']:.12g}",
            str(int(p["N"])),
        ]
        proc = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )

        omega_list, re_list, im_list = [], [], []
        for line in proc.stdout.splitlines():
            parts = line.split()
            if len(parts) != 3:
                continue
            try:
                w, r, im = (float(parts[0]), float(parts[1]),
                            float(parts[2]))
            except ValueError:
                continue
            # Отбрасываем переполнения / NaN.
            if (not np.isfinite(r)) or (not np.isfinite(im)):
                continue
            omega_list.append(w)
            re_list.append(r)
            im_list.append(im)

        return {
            "points": (
                np.array(omega_list),
                np.array(re_list),
                np.array(im_list),
            ),
            "meta": proc.stderr.strip(),
        }

    def _draw_hatch_ticks(self, re, im, color, n_ticks=30):
        """
        Рисует короткие штрихи перпендикулярно кривой — как на Рис.4
        из отчёта. Длина штриха адаптивна: пропорциональна локальному
        расстоянию между соседними точками, чтобы на петлях разного
        масштаба штрихи выглядели одинаково короткими.
        """
        if re.size < 3:
            return
        # Локальные касательные через конечные разности.
        dr = np.gradient(re)
        di = np.gradient(im)
        seg = np.hypot(dr, di)
        seg[seg == 0] = 1.0
        # Нормаль (повёрнутая на +90°).
        nx = -di / seg
        ny = dr / seg

        # Выбираем равномерно распределённые индексы.
        idxs = np.linspace(0, re.size - 1, n_ticks).astype(int)

        # Длина каждого штриха — небольшая доля локального шага кривой.
        # Так на больших и малых петлях штрихи будут визуально похожи
        # по длине относительно самой петли.
        for k in idxs:
            local_scale = seg[k] * 8.0  # 8 шагов — короткий, заметный штрих
            x0, y0 = re[k], im[k]
            x1 = x0 + nx[k] * local_scale
            y1 = y0 + ny[k] * local_scale
            self.ax.plot([x0, x1], [y0, y1], "-",
                         color=color, linewidth=0.8, alpha=0.7)


def main():
    root = tk.Tk()
    app = DPartitionApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
