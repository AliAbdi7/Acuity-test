import ctypes
import json
import math
import platform
import random
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import stat_algorithm as stat

if platform.system() == "Windows":
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

CARD_WIDTH_MM = stat.CARD_WIDTH_MM
CARD_HEIGHT_MM = stat.CARD_HEIGHT_MM


class StATDesktopApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Stanford Acuity Test (StAT) - myeyes.ai/measure Rebuild (v8)")
        self.root.geometry("1240x860")
        self.root.minsize(1060, 760)
        self.root.configure(bg="#FFFFFF")

        sw = self.root.winfo_screenwidth() or 1920
        sh = self.root.winfo_screenheight() or 1080
        self.diagonal_inches = 15.6
        self.pixels_per_mm, self.card_width_px = stat.calculate_screen_pixels_per_mm(
            sw, sh, diagonal_inches=self.diagonal_inches
        )

        self.user_name = ""
        self.test_date = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.distance_cm = 100.0
        self.selected_eye = "Left Eye"
        self.exam_mode = "standard_20"
        self.max_questions = 20

        self.belief = []
        self.question_index = 0
        self.current_size_arcmins = 2.2
        self.current_direction = "RIGHT"
        self.history = []
        self.exam_active = False

        # Store results for both Left Eye and Right Eye
        self.eye_results = {
            "Left Eye": None,
            "Right Eye": None
        }
        self.display_unit = "Score (0-100 / 100+)"

        self.root.bind("<Up>", lambda e: self.submit_answer("UP"))
        self.root.bind("<Down>", lambda e: self.submit_answer("DOWN"))
        self.root.bind("<Left>", lambda e: self.submit_answer("LEFT"))
        self.root.bind("<Right>", lambda e: self.submit_answer("RIGHT"))

        self.container = tk.Frame(self.root, bg="#FFFFFF")
        self.container.pack(fill="both", expand=True)

        self.show_calibration_screen()

    # =========================================================================
    # STEP 1: FULL-WIDTH CREDIT CARD CALIBRATION + USER NAME & DATE
    # =========================================================================

    def show_calibration_screen(self):
        self.exam_active = False
        for widget in self.container.winfo_children():
            widget.destroy()

        header = tk.Label(
            self.container,
            text="Step 1: Screen Calibration, Patient Info & Viewing Distance",
            font=("Helvetica", 19, "bold"),
            bg="#FFFFFF",
            fg="#0F172A"
        )
        header.pack(pady=(14, 4))

        sub = tk.Label(
            self.container,
            text="Automatically sized for a 15.6-inch screen. Place a real bank/ID card (85.60 mm × 53.98 mm) "
                 "on the blue card below to verify or fine-tune.",
            font=("Helvetica", 10),
            bg="#FFFFFF",
            fg="#475569"
        )
        sub.pack(pady=(0, 8))

        card_box = tk.LabelFrame(
            self.container,
            text=" 1. Exact Credit / Bank Card Calibration (85.60 mm × 53.98 mm) ",
            font=("Helvetica", 11, "bold"),
            bg="#FFFFFF",
            fg="#0F172A",
            padx=18,
            pady=8
        )
        card_box.pack(fill="x", padx=36, pady=(0, 10))

        preset_frame = tk.Frame(card_box, bg="#FFFFFF")
        preset_frame.pack(fill="x", pady=(0, 6))
        tk.Label(
            preset_frame,
            text="Auto-Set by Screen Size:",
            font=("Helvetica", 10, "bold"),
            bg="#FFFFFF",
            fg="#334155"
        ).pack(side="left", padx=(0, 8))

        for diag, label in [
            (13.3, '13.3"'),
            (14.0, '14.0"'),
            (15.6, '15.6" (Standard Laptop)'),
            (16.0, '16.0"'),
            (17.3, '17.3"'),
            (24.0, '24.0" Monitor'),
            (27.0, '27.0" Monitor')
        ]:
            tk.Button(
                preset_frame,
                text=label,
                font=("Helvetica", 9, "bold" if diag == 15.6 else "normal"),
                bg="#2563EB" if abs(self.diagonal_inches - diag) < 0.05 else "#F1F5F9",
                fg="#FFFFFF" if abs(self.diagonal_inches - diag) < 0.05 else "#1E293B",
                relief="flat",
                padx=10,
                pady=3,
                command=lambda d=diag: self.apply_diagonal_preset(d)
            ).pack(side="left", padx=3)

        self.card_canvas = tk.Canvas(
            card_box, width=900, height=310, bg="#F8FAFC", highlightthickness=1, highlightbackground="#CBD5E1"
        )
        self.card_canvas.pack(pady=4)

        slider_row = tk.Frame(card_box, bg="#FFFFFF")
        slider_row.pack(fill="x", pady=(4, 2))

        tk.Button(
            slider_row, text="− Smaller", font=("Helvetica", 9, "bold"), bg="#F1F5F9",
            command=lambda: self.nudge_card(-2.0)
        ).pack(side="left", padx=(0, 8))

        self.slider_var = tk.DoubleVar(value=self.card_width_px)
        slider = ttk.Scale(
            slider_row,
            from_=160,
            to=760,
            orient="horizontal",
            variable=self.slider_var,
            command=self.on_card_slider_change
        )
        slider.pack(side="left", fill="x", expand=True)

        tk.Button(
            slider_row, text="+ Larger", font=("Helvetica", 9, "bold"), bg="#F1F5F9",
            command=lambda: self.nudge_card(2.0)
        ).pack(side="left", padx=(8, 0))

        self.ppi_label = tk.Label(
            card_box, text="", font=("Helvetica", 10, "bold"), bg="#FFFFFF", fg="#2563EB"
        )
        self.ppi_label.pack(pady=2)
        self.draw_calibration_card()

        bottom_box = tk.LabelFrame(
            self.container,
            text=" 2. Patient / User Info, Date of Test & Viewing Distance ",
            font=("Helvetica", 11, "bold"),
            bg="#FFFFFF",
            fg="#0F172A",
            padx=18,
            pady=10
        )
        bottom_box.pack(fill="x", padx=36, pady=(0, 10))

        row_opts = tk.Frame(bottom_box, bg="#FFFFFF")
        row_opts.pack(fill="x")

        # User Name (Optional)
        col_user = tk.Frame(row_opts, bg="#FFFFFF")
        col_user.pack(side="left", expand=True, fill="x", padx=6)
        tk.Label(col_user, text="User Name (Optional):", font=("Helvetica", 10, "bold"), bg="#FFFFFF").pack(anchor="w")
        self.user_var = tk.StringVar(value=self.user_name)
        ttk.Entry(col_user, textvariable=self.user_var, width=18, font=("Helvetica", 11)).pack(anchor="w", pady=4, fill="x")

        # Date of Test
        col_date = tk.Frame(row_opts, bg="#FFFFFF")
        col_date.pack(side="left", expand=True, fill="x", padx=6)
        tk.Label(col_date, text="Date of Test:", font=("Helvetica", 10, "bold"), bg="#FFFFFF").pack(anchor="w")
        if not self.test_date:
            self.test_date = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.date_var = tk.StringVar(value=self.test_date)
        ttk.Entry(col_date, textvariable=self.date_var, width=18, font=("Helvetica", 11)).pack(anchor="w", pady=4, fill="x")

        # Distance
        col1 = tk.Frame(row_opts, bg="#FFFFFF")
        col1.pack(side="left", expand=True, fill="x", padx=6)
        tk.Label(col1, text="Distance to Laptop (cm):", font=("Helvetica", 10, "bold"), bg="#FFFFFF").pack(anchor="w")
        self.dist_var = tk.DoubleVar(value=self.distance_cm)
        ttk.Spinbox(col1, from_=40, to=400, increment=5, textvariable=self.dist_var, width=10, font=("Helvetica", 11)).pack(anchor="w", pady=4)

        # Eye selection
        col2 = tk.Frame(row_opts, bg="#FFFFFF")
        col2.pack(side="left", expand=True, fill="x", padx=6)
        tk.Label(col2, text="Eye to Test First:", font=("Helvetica", 10, "bold"), bg="#FFFFFF").pack(anchor="w")
        self.eye_var = tk.StringVar(value=self.selected_eye)
        eye_f = tk.Frame(col2, bg="#FFFFFF")
        eye_f.pack(anchor="w", pady=4)
        for eye_opt in ["Left Eye", "Right Eye"]:
            ttk.Radiobutton(eye_f, text=eye_opt, value=eye_opt, variable=self.eye_var).pack(side="left", padx=(0, 8))

        # Stopping rule
        col3 = tk.Frame(row_opts, bg="#FFFFFF")
        col3.pack(side="left", expand=True, fill="x", padx=6)
        tk.Label(col3, text="Stopping Rule:", font=("Helvetica", 10, "bold"), bg="#FFFFFF").pack(anchor="w")
        self.mode_var = tk.StringVar(value=self.exam_mode)
        mode_f = tk.Frame(col3, bg="#FFFFFF")
        mode_f.pack(anchor="w", pady=4)
        ttk.Radiobutton(mode_f, text="20 Qs", value="standard_20", variable=self.mode_var).pack(side="left", padx=(0, 8))
        ttk.Radiobutton(mode_f, text="StAT-star", value="stat_star", variable=self.mode_var).pack(side="left")

        btn_bar = tk.Frame(self.container, bg="#FFFFFF")
        btn_bar.pack(pady=6)

        tk.Button(
            btn_bar,
            text="Start Stanford Acuity Test (StAT)  →",
            font=("Helvetica", 13, "bold"),
            bg="#2563EB",
            fg="#FFFFFF",
            activebackground="#1D4ED8",
            activeforeground="#FFFFFF",
            padx=26,
            pady=9,
            relief="flat",
            cursor="hand2",
            command=self.start_exam
        ).pack(side="left", padx=8)

        tk.Button(
            btn_bar,
            text="📈 View Vision History Over Time",
            font=("Helvetica", 11, "bold"),
            bg="#F1F5F9",
            fg="#1E293B",
            padx=16,
            pady=9,
            relief="groove",
            cursor="hand2",
            command=self.open_history_window
        ).pack(side="left", padx=8)

    def apply_diagonal_preset(self, diag_inches):
        self.diagonal_inches = diag_inches
        sw = self.root.winfo_screenwidth() or 1920
        sh = self.root.winfo_screenheight() or 1080
        self.pixels_per_mm, self.card_width_px = stat.calculate_screen_pixels_per_mm(
            sw, sh, diagonal_inches=diag_inches
        )
        self.slider_var.set(self.card_width_px)
        self.show_calibration_screen()

    def nudge_card(self, delta_px):
        self.card_width_px = max(160.0, min(760.0, self.card_width_px + delta_px))
        self.pixels_per_mm = self.card_width_px / CARD_WIDTH_MM
        self.slider_var.set(self.card_width_px)
        self.draw_calibration_card()

    def on_card_slider_change(self, _=None):
        self.card_width_px = float(self.slider_var.get())
        self.pixels_per_mm = self.card_width_px / CARD_WIDTH_MM
        self.draw_calibration_card()

    def draw_calibration_card(self):
        self.card_canvas.delete("all")
        cw, ch = 900, 310
        w = self.card_width_px
        h = w * (CARD_HEIGHT_MM / CARD_WIDTH_MM)
        x0 = (cw - w) / 2.0
        y0 = (ch - h) / 2.0
        x1, y1 = x0 + w, y0 + h

        self.card_canvas.create_rectangle(x0, y0, x1, y1, fill="#1E40AF", outline="#1E3A8A", width=2)
        self.card_canvas.create_rectangle(x0, y0, x1, y0 + 20, fill="#1D4ED8", outline="")
        for mm_tick in [0, 20, 40, 60, 85.6]:
            tx = x0 + (mm_tick / CARD_WIDTH_MM) * w
            self.card_canvas.create_line(tx, y0, tx, y0 + 8, fill="#FFFFFF", width=1.5)
            anchor = "w" if mm_tick == 0 else ("e" if mm_tick > 80 else "center")
            self.card_canvas.create_text(
                tx, y0 + 13, text=f"{mm_tick:g}mm", fill="#FFFFFF", font=("Courier", 8, "bold"), anchor=anchor
            )

        self.card_canvas.create_rectangle(
            x0 + w * 0.08, y0 + h * 0.36, x0 + w * 0.21, y0 + h * 0.58, fill="#FBBF24", outline="#D97706"
        )
        self.card_canvas.create_text(
            (x0 + x1) / 2,
            y0 + h * 0.72,
            text="5412   7534   8901   2345",
            fill="#FFFFFF",
            font=("Courier", 12, "bold")
        )
        self.card_canvas.create_text(
            (x0 + x1) / 2,
            y0 + h * 0.88,
            text=f"ISO/IEC 7810 Standard Bank Card: {CARD_WIDTH_MM} mm × {CARD_HEIGHT_MM} mm",
            fill="#E2E8F0",
            font=("Helvetica", 9, "bold")
        )

        ppi = self.pixels_per_mm * 25.4
        self.ppi_label.config(
            text=f"Card Size: {w:.0f} px × {h:.0f} px  |  Scale: {self.pixels_per_mm:.2f} px/mm ({ppi:.0f} PPI)"
        )

    # =========================================================================
    # STEP 2: SPLIT-SCREEN EXAM WITH TWO STACKED CHARTS + ENGLISH PROMPT
    # =========================================================================

    def start_exam(self, override_eye=None):
        if hasattr(self, "user_var"):
            self.user_name = self.user_var.get().strip()
        if hasattr(self, "date_var"):
            self.test_date = self.date_var.get().strip() or datetime.now().strftime("%Y-%m-%d %H:%M")
        if hasattr(self, "dist_var"):
            try:
                self.distance_cm = max(30.0, float(self.dist_var.get()))
            except Exception:
                pass
        if override_eye:
            self.selected_eye = override_eye
        elif hasattr(self, "eye_var"):
            self.selected_eye = self.eye_var.get()

        if hasattr(self, "mode_var"):
            self.exam_mode = self.mode_var.get()

        self.max_questions = 20 if self.exam_mode == "standard_20" else 60

        self.belief = stat.get_prior_belief()
        self.question_index = 0
        self.history = []
        self.exam_active = True

        self.build_exam_screen()
        self.next_question()

    def build_exam_screen(self):
        for widget in self.container.winfo_children():
            widget.destroy()

        main_split = tk.Frame(self.container, bg="#FFFFFF")
        main_split.pack(fill="both", expand=True)

        left_panel = tk.Frame(main_split, bg="#FFFFFF")
        left_panel.pack(side="left", fill="both", expand=True)

        top_bar_left = tk.Frame(left_panel, bg="#FFFFFF")
        top_bar_left.pack(fill="x", padx=20, pady=(14, 0))

        tk.Button(
            top_bar_left,
            text="✖",
            font=("Helvetica", 16, "bold"),
            bg="#FFFFFF",
            fg="#9CA3AF",
            relief="flat",
            bd=0,
            cursor="hand2",
            command=self.show_calibration_screen
        ).pack(side="right")

        self.eye_title_lbl = tk.Label(
            left_panel,
            text=self.selected_eye,
            font=("Helvetica", 26),
            bg="#FFFFFF",
            fg="#333333"
        )
        self.eye_title_lbl.pack(pady=(0, 10))

        self.optotype_canvas = tk.Canvas(
            left_panel, width=380, height=340, bg="#FFFFFF", highlightthickness=0
        )
        self.optotype_canvas.pack(pady=8, expand=True)

        controls_frame = tk.Frame(left_panel, bg="#FFFFFF")
        controls_frame.pack(pady=6)
        btn_style = {"font": ("Helvetica", 10, "bold"), "width": 7, "pady": 3, "bg": "#F8FAFC", "relief": "groove"}
        tk.Button(controls_frame, text="↑ Up", command=lambda: self.submit_answer("UP"), **btn_style).grid(row=0, column=1, pady=2)
        tk.Button(controls_frame, text="← Left", command=lambda: self.submit_answer("LEFT"), **btn_style).grid(row=1, column=0, padx=4)
        tk.Button(controls_frame, text="↓ Down", command=lambda: self.submit_answer("DOWN"), **btn_style).grid(row=1, column=1, pady=2)
        tk.Button(controls_frame, text="Right →", command=lambda: self.submit_answer("RIGHT"), **btn_style).grid(row=1, column=2, padx=4)

        self.progress_lbl = tk.Label(
            left_panel,
            text="Progress: 0%",
            font=("Helvetica", 14),
            bg="#FFFFFF",
            fg="#333333"
        )
        self.progress_lbl.pack(pady=(8, 18))

        divider = tk.Frame(main_split, bg="#E5E7EB", width=1)
        divider.pack(side="left", fill="y")

        right_panel = tk.Frame(main_split, bg="#FFFFFF", width=440)
        right_panel.pack(side="right", fill="y", padx=16)
        right_panel.pack_propagate(False)

        tk.Label(
            right_panel,
            text="StAT Algorithm",
            font=("Helvetica", 24),
            bg="#FFFFFF",
            fg="#333333"
        ).pack(pady=(16, 6))

        self.stats_text_lbl = tk.Label(
            right_panel,
            text="",
            font=("Helvetica", 11),
            bg="#FFFFFF",
            fg="#777777",
            justify="center"
        )
        self.stats_text_lbl.pack(pady=(0, 8))

        tk.Label(
            right_panel,
            text="Likelihood of Acuity Scores (arcmins):",
            font=("Helvetica", 11),
            bg="#FFFFFF",
            fg="#777777"
        ).pack(pady=(2, 1))

        self.curve_canvas_arcmin = tk.Canvas(
            right_panel, width=400, height=190, bg="#FFFFFF", highlightthickness=0
        )
        self.curve_canvas_arcmin.pack(pady=(0, 6))

        tk.Label(
            right_panel,
            text="Likelihood of Acuity Scores (logMAR):",
            font=("Helvetica", 11),
            bg="#FFFFFF",
            fg="#777777"
        ).pack(pady=(2, 1))

        self.curve_canvas_logmar = tk.Canvas(
            right_panel, width=400, height=190, bg="#FFFFFF", highlightthickness=0
        )
        self.curve_canvas_logmar.pack(pady=(0, 6))

    def next_question(self):
        conf = stat.get_confidence_within_10_percent(self.belief)
        reached_limit = (self.question_index >= self.max_questions)
        stat_star_done = (self.exam_mode == "stat_star" and self.question_index >= 5 and conf >= 0.95)

        if reached_limit or stat_star_done:
            self.update_stat_panel()
            map_k1, map_logmar = stat.get_map_acuity_logmar(self.belief)
            ci_low, ci_high = stat.get_credible_interval(self.belief, 0.95)
            metrics = stat.arcmins_to_clinical_metrics(map_k1)

            want_continue = messagebox.askyesno(
                f"{self.question_index} Questions Completed ({self.selected_eye})",
                f"{self.question_index} Questions Completed!\n\n"
                f"Vision Score (0–100): {metrics['score_0_100']}\n"
                f"Current MAP Acuity: {map_k1:.2f} arcmin ({map_logmar:.2f} logMAR | {metrics['snellen_feet']})\n"
                f"95% Confidence Interval: [{ci_low:.1f}, {ci_high:.1f}] arcmins\n"
                f"Calibrated Confidence: {conf*100:.1f}%\n\n"
                f"Would you like to continue with 10 additional questions to further refine accuracy?\n"
                f"(Yes = Continue +10 Questions  |  No = Finish & View Results)"
            )
            if want_continue:
                self.max_questions += 10
            else:
                self.save_current_eye_and_show_results()
                return

        self.current_size_arcmins = stat.choose_next_letter_size(self.belief)
        self.current_direction = random.choice(["UP", "DOWN", "LEFT", "RIGHT"])

        self.draw_crisp_tumbling_e(self.current_size_arcmins, self.current_direction)
        self.update_stat_panel()

    def submit_answer(self, chosen_direction):
        if not self.exam_active:
            return

        is_correct = (chosen_direction == self.current_direction)
        observation = {
            'size': self.current_size_arcmins,
            'correct': is_correct
        }

        self.belief = stat.update_belief(self.belief, observation)
        self.question_index += 1

        map_k1, map_logmar = stat.get_map_acuity_logmar(self.belief)
        ci_low, ci_high = stat.get_credible_interval(self.belief, 0.95)
        conf = stat.get_confidence_within_10_percent(self.belief)

        self.history.append({
            'q': self.question_index,
            'size_arcmins': self.current_size_arcmins,
            'size_logmar': math.log10(self.current_size_arcmins),
            'direction': self.current_direction,
            'answer': chosen_direction,
            'correct': is_correct,
            'map_k1': map_k1,
            'map_logmar': map_logmar,
            'ci_low': ci_low,
            'ci_high': ci_high,
            'confidence': conf
        })

        self.next_question()

    def draw_crisp_tumbling_e(self, arcmins, direction):
        self.optotype_canvas.delete("all")
        cw = int(self.optotype_canvas["width"])
        ch = int(self.optotype_canvas["height"])
        cx, cy = cw // 2, ch // 2

        total_px = stat.arcmins_to_pixels(arcmins, self.distance_cm, self.pixels_per_mm)
        total_px = max(5.0, min(float(min(cw, ch) - 24), total_px))

        stroke = max(1.0, round(total_px / 5.0)) if total_px >= 10.0 else (total_px / 5.0)

        e_pts_grid = [
            (0, 0), (5, 0), (5, 1), (1, 1),
            (1, 2), (5, 2), (5, 3), (1, 3),
            (1, 4), (5, 4), (5, 5), (0, 5)
        ]

        poly_coords = []
        for gx, gy in e_pts_grid:
            dx = gx - 2.5
            dy = gy - 2.5
            if direction == "RIGHT":
                rx, ry = dx, dy
            elif direction == "LEFT":
                rx, ry = -dx, -dy
            elif direction == "DOWN":
                rx, ry = -dy, dx
            elif direction == "UP":
                rx, ry = dy, -dx
            else:
                rx, ry = dx, dy

            px = round(cx + rx * stroke)
            py = round(cy + ry * stroke)
            poly_coords.extend([px, py])

        self.optotype_canvas.create_polygon(poly_coords, fill="#000000", outline="")

    def update_stat_panel(self):
        map_k1, map_logmar = stat.get_map_acuity_logmar(self.belief)
        ci_low, ci_high = stat.get_credible_interval(self.belief, 0.95)
        curr_logmar = math.log10(self.current_size_arcmins)
        score_str, _ = stat.arcmins_to_score_0_100(map_k1)

        progress_pct = min(100, int(round((self.question_index / float(max(1, self.max_questions))) * 100)))
        self.progress_lbl.config(text=f"Progress: {progress_pct}%")

        self.stats_text_lbl.config(
            text=(
                f"N done: {self.question_index}\n"
                f"Curr size: {self.current_size_arcmins:.1f} arcmin\n"
                f"Curr size: {curr_logmar:.1f} logMAR\n\n"
                f"MAP acuity: {map_k1:.1f} arcmin\n"
                f"MAP acuity: {map_logmar:.1f} logMAR\n"
                f"Vision Score (0–100): {score_str}\n\n"
                f"Interval: [{ci_low:.1f}, {ci_high:.1f}] arcmins"
            )
        )

        arc_xs, arc_ys = stat.get_smooth_posterior_curve_arcmins(self.belief, max_x=12.0, num_points=120)
        self.draw_chart_on_canvas(
            canvas=self.curve_canvas_arcmin,
            xs=arc_xs,
            ys=arc_ys,
            min_x=0.0,
            max_x=12.0,
            x_ticks=[0, 2, 4, 6, 8, 10, 12],
            x_label="Acuity (arcmins)",
            line_color="#E15759",
            is_logmar=False
        )

        log_xs, log_ys = stat.get_smooth_posterior_curve_logmar(self.belief, min_logmar=-0.8, max_logmar=1.25, num_points=100)
        self.draw_chart_on_canvas(
            canvas=self.curve_canvas_logmar,
            xs=log_xs,
            ys=log_ys,
            min_x=-0.8,
            max_x=1.25,
            x_ticks=[-0.8, -0.4, 0, 0.4, 0.8, 1.2],
            x_label="Acuity (logMAR)",
            line_color="#7970C6",
            is_logmar=True
        )

    def draw_chart_on_canvas(self, canvas, xs, ys, min_x, max_x, x_ticks, x_label, line_color, is_logmar, cw=400, ch=190):
        canvas.delete("all")
        pad_l, pad_r, pad_t, pad_b = 44, 12, 14, 34
        plot_w = cw - pad_l - pad_r
        plot_h = ch - pad_t - pad_b
        range_x = max_x - min_x
        axis_ceiling, y_ticks = stat.get_nice_y_axis_ticks(max(ys) if ys else 0.08)

        x0 = pad_l
        y0 = pad_t + plot_h

        for xt in x_ticks:
            px = x0 + ((xt - min_x) / range_x) * plot_w
            canvas.create_line(px, pad_t, px, y0, fill="#E5E7EB", dash=(3, 3))
        for i, (tv, _) in enumerate(y_ticks):
            if i == 0:
                continue
            py = y0 - (tv / axis_ceiling) * plot_h
            canvas.create_line(x0, py, x0 + plot_w, py, fill="#E5E7EB", dash=(3, 3))

        canvas.create_line(x0, pad_t, x0, y0, fill="#6B7280", width=1)
        canvas.create_line(x0, y0, x0 + plot_w, y0, fill="#6B7280", width=1)

        for xt in x_ticks:
            px = x0 + ((xt - min_x) / range_x) * plot_w
            canvas.create_line(px, y0, px, y0 + 4, fill="#6B7280")
            lbl = "0" if abs(xt) < 1e-9 else (f"{xt:.1f}" if is_logmar else f"{int(xt)}")
            canvas.create_text(px, y0 + 13, text=lbl, font=("Helvetica", 8), fill="#4B5563")

        canvas.create_text(
            x0 + plot_w / 2, y0 + 26, text=x_label, font=("Helvetica", 9, "bold"), fill="#111827"
        )

        for tv, lbl in y_ticks:
            py = y0 - (tv / axis_ceiling) * plot_h
            canvas.create_line(x0 - 4, py, x0, py, fill="#6B7280")
            canvas.create_text(x0 - 6, py, text=lbl, anchor="e", font=("Helvetica", 8), fill="#4B5563")

        pts = []
        for xv, yv in zip(xs, ys):
            px = x0 + ((xv - min_x) / range_x) * plot_w
            py = y0 - (yv / axis_ceiling) * plot_h
            pts.extend([px, py])

        if len(pts) >= 4:
            canvas.create_line(pts, fill=line_color, width=1.6, smooth=True)

        leg_x = x0 + plot_w * 0.25
        leg_y = pad_t + 8
        canvas.create_line(leg_x - 16, leg_y, leg_x - 2, leg_y, fill=line_color, width=1.5)
        canvas.create_oval(leg_x - 11.5, leg_y - 2.5, leg_x - 6.5, leg_y + 2.5, outline=line_color, fill="#FFFFFF")
        canvas.create_text(leg_x + 2, leg_y, text="likelihood", anchor="w", font=("Helvetica", 8), fill="#555555")

    # =========================================================================
    # STEP 3: FINAL RESULTS SCREEN + 0-100 SCORE + VISION HISTORY TRACKING
    # =========================================================================

    def save_current_eye_and_show_results(self):
        self.exam_active = False
        pred_k1 = stat.get_predicted_acuity(self.belief)
        map_k1, map_logmar = stat.get_map_acuity_logmar(self.belief)
        conf = stat.get_confidence_within_10_percent(self.belief)
        low_ci, high_ci = stat.get_credible_interval(self.belief, 0.95)
        metrics = stat.arcmins_to_clinical_metrics(map_k1)
        arc_xs, arc_ys = stat.get_smooth_posterior_curve_arcmins(self.belief, max_x=12.0, num_points=120)
        log_xs, log_ys = stat.get_smooth_posterior_curve_logmar(self.belief, min_logmar=-0.8, max_logmar=1.25, num_points=100)

        eye_key = self.selected_eye if self.selected_eye in ("Left Eye", "Right Eye") else "Left Eye"
        snap = {
            "user_name": self.user_name or "Guest",
            "test_date": self.test_date or datetime.now().strftime("%Y-%m-%d %H:%M"),
            "eye": eye_key,
            "question_index": self.question_index,
            "predicted_k1": pred_k1,
            "map_k1": map_k1,
            "map_logmar": map_logmar,
            "score_0_100": metrics["score_0_100"],
            "score_0_100_num": metrics["score_0_100_num"],
            "snellen_feet": metrics["snellen_feet"],
            "snellen_meters": metrics["snellen_meters"],
            "confidence": conf,
            "ci_low": low_ci,
            "ci_high": high_ci,
            "curve_arc_xs": arc_xs,
            "curve_arc_ys": arc_ys,
            "curve_log_xs": log_xs,
            "curve_log_ys": log_ys,
            "history": list(self.history)
        }
        self.eye_results[eye_key] = snap

        # Save to persistent vision_history.json for tracking over time
        stat.append_vision_history_record({
            "user_name": snap["user_name"],
            "test_date": snap["test_date"],
            "eye": snap["eye"],
            "score_0_100": snap["score_0_100"],
            "score_0_100_num": snap["score_0_100_num"],
            "map_k1": round(snap["map_k1"], 3),
            "map_logmar": round(snap["map_logmar"], 3),
            "snellen_feet": snap["snellen_feet"],
            "ci_low": round(snap["ci_low"], 2),
            "ci_high": round(snap["ci_high"], 2),
            "question_index": snap["question_index"]
        })

        self.show_results_screen()

    def format_acuity_unit(self, arcmin_val, unit_name):
        v = max(0.05, arcmin_val)
        if "0-100" in unit_name or "100+" in unit_name:
            sc_str, _ = stat.arcmins_to_score_0_100(v)
            return f"{sc_str} (0–100 scale)"
        if "LogMAR" in unit_name:
            return f"{math.log10(v):.2f} logMAR"
        if "20/" in unit_name:
            return f"20/{round(20 * v)}"
        if "6/" in unit_name:
            return f"6/{6 * v:.1f}"
        if "Decimal" in unit_name:
            return f"{1.0 / v:.2f}"
        return f"{v:.1f} arcmin"

    def format_interval_unit(self, lo_val, hi_val, unit_name):
        lo = max(0.05, lo_val)
        hi = max(0.05, hi_val)
        if "0-100" in unit_name or "100+" in unit_name:
            return stat.arcmins_interval_to_score_0_100(lo, hi)
        if "LogMAR" in unit_name:
            return f"{math.log10(lo):.2f}  to  {math.log10(hi):.2f} logMAR"
        if "20/" in unit_name:
            return f"20/{round(20 * lo)}  to  20/{round(20 * hi)}"
        if "6/" in unit_name:
            return f"6/{6 * lo:.1f}  to  6/{6 * hi:.1f}"
        if "Decimal" in unit_name:
            return f"{1.0 / hi:.2f}  to  {1.0 / lo:.2f}"
        return f"{lo:.1f}  to  {hi:.1f} arcmin"

    def show_results_screen(self):
        self.exam_active = False
        for widget in self.container.winfo_children():
            widget.destroy()

        # User & Date Info Banner
        banner = tk.Frame(self.container, bg="#F8FAFC", bd=1, relief="solid", padx=16, pady=6)
        banner.pack(pady=(14, 10))
        u_txt = self.user_name if self.user_name else "Guest"
        tk.Label(
            banner,
            text=f"Patient / User: {u_txt}     |     Date of Test: {self.test_date}",
            font=("Helvetica", 11, "bold"),
            bg="#F8FAFC",
            fg="#1E293B"
        ).pack(side="left", padx=8)
        tk.Button(
            banner,
            text="✎ Edit Name / Setup",
            font=("Helvetica", 9),
            bg="#E2E8F0",
            relief="flat",
            command=self.show_calibration_screen
        ).pack(side="left", padx=8)

        # Top Eye Action Buttons (✔ Left Eye Done | + Test Right Eye)
        btn_row_top = tk.Frame(self.container, bg="#FFFFFF")
        btn_row_top.pack(pady=(4, 12))

        left_done = self.eye_results["Left Eye"] is not None
        right_done = self.eye_results["Right Eye"] is not None

        tk.Button(
            btn_row_top,
            text="✔ Left Eye Done" if left_done else "+ Test Left Eye",
            font=("Helvetica", 12, "bold"),
            bg="#2E77B5",
            fg="#FFFFFF",
            padx=22,
            pady=7,
            relief="flat",
            cursor="hand2",
            command=lambda: self.start_exam(override_eye="Left Eye")
        ).pack(side="left", padx=95)

        tk.Button(
            btn_row_top,
            text="✔ Right Eye Done" if right_done else "+ Test Right Eye",
            font=("Helvetica", 12, "bold"),
            bg="#2E77B5",
            fg="#FFFFFF",
            padx=22,
            pady=7,
            relief="flat",
            cursor="hand2",
            command=lambda: self.start_exam(override_eye="Right Eye")
        ).pack(side="left", padx=95)

        cards_row = tk.Frame(self.container, bg="#FFFFFF")
        cards_row.pack(padx=50, pady=4)

        for eye_name in ["Left Eye", "Right Eye"]:
            res = self.eye_results[eye_name]
            card = tk.Frame(cards_row, bg="#F5F5F5", bd=1, relief="solid", width=440, height=515, padx=16, pady=12)
            card.pack(side="left", padx=16)
            card.pack_propagate(False)

            tk.Label(
                card, text=f"{eye_name} Results", font=("Helvetica", 13, "bold"), bg="#F5F5F5", fg="#333333"
            ).pack(pady=(0, 6))

            if not res:
                tk.Label(
                    card, text="No results yet", font=("Helvetica", 12, "italic"), bg="#F5F5F5", fg="#555555"
                ).pack(pady=40)
            else:
                score_str = self.format_acuity_unit(res["map_k1"], self.display_unit)
                interval_str = self.format_interval_unit(res["ci_low"], res["ci_high"], self.display_unit)
                sc_100_str = res["score_0_100"]
                sc_100_int = stat.arcmins_interval_to_score_0_100(res["ci_low"], res["ci_high"])

                tk.Label(
                    card,
                    text=f"Vision Score (0–100): {sc_100_str}   (Interval: {sc_100_int})",
                    font=("Helvetica", 10, "bold"),
                    bg="#EFF6FF",
                    fg="#1D4ED8",
                    padx=10,
                    pady=3
                ).pack(pady=(0, 6))

                tk.Label(
                    card,
                    text=f"Measured acuity score ¹ :\n{score_str}",
                    font=("Helvetica", 11, "bold"),
                    bg="#F5F5F5",
                    fg="#333333",
                    justify="center"
                ).pack(pady=(0, 4))

                tk.Label(
                    card,
                    text=f"With confidence interval ² :\n{interval_str}",
                    font=("Helvetica", 11),
                    bg="#F5F5F5",
                    fg="#333333",
                    justify="center"
                ).pack(pady=(0, 6))

                plots_box = tk.Frame(card, bg="#FFFFFF", bd=1, relief="solid", padx=4, pady=4)
                plots_box.pack(fill="both", expand=True)

                c_arc = tk.Canvas(plots_box, width=380, height=145, bg="#FFFFFF", highlightthickness=0)
                c_arc.pack(pady=2)
                self.draw_chart_on_canvas(
                    c_arc, res["curve_arc_xs"], res["curve_arc_ys"],
                    0.0, 12.0, [0, 2, 4, 6, 8, 10, 12], "Acuity (arcmins)", "#E15759", False, cw=380, ch=145
                )

                c_log = tk.Canvas(plots_box, width=380, height=145, bg="#FFFFFF", highlightthickness=0)
                c_log.pack(pady=2)
                self.draw_chart_on_canvas(
                    c_log, res["curve_log_xs"], res["curve_log_ys"],
                    -0.8, 1.25, [-0.8, -0.4, 0, 0.4, 0.8, 1.2], "Acuity (logMAR)", "#7970C6", True, cw=380, ch=145
                )

        bottom_stack = tk.Frame(self.container, bg="#FFFFFF")
        bottom_stack.pack(pady=(12, 8))

        self.unit_combo = ttk.Combobox(
            bottom_stack,
            values=[
                "Score (0-100 / 100+)",
                "ArcMin Units",
                "LogMAR Units",
                "Snellen (20/X)",
                "Snellen (6/X)",
                "Decimal Units"
            ],
            state="readonly",
            font=("Helvetica", 11),
            width=22,
            justify="center"
        )
        self.unit_combo.set(self.display_unit)
        self.unit_combo.bind("<<ComboboxSelected>>", self.on_unit_change)
        self.unit_combo.pack(pady=(0, 8))

        action_btns = tk.Frame(bottom_stack, bg="#FFFFFF")
        action_btns.pack()

        tk.Button(
            action_btns,
            text="⬇ Save Results",
            font=("Helvetica", 11, "bold"),
            bg="#FFFFFF",
            fg="#333333",
            bd=1,
            relief="solid",
            padx=20,
            pady=6,
            cursor="hand2",
            command=self.export_results_report
        ).pack(side="left", padx=6)

        tk.Button(
            action_btns,
            text="📈 View Vision History Over Time",
            font=("Helvetica", 11, "bold"),
            bg="#EFF6FF",
            fg="#1D4ED8",
            bd=1,
            relief="solid",
            padx=16,
            pady=6,
            cursor="hand2",
            command=self.open_history_window
        ).pack(side="left", padx=6)

    def on_unit_change(self, _=None):
        self.display_unit = self.unit_combo.get()
        self.show_results_screen()

    def open_history_window(self):
        win = tk.Toplevel(self.root)
        win.title("Vision History Over Time (vision_history.json)")
        win.geometry("860x480")
        win.configure(bg="#FFFFFF")

        tk.Label(
            win,
            text="Vision History Over Time — Tracked Tests",
            font=("Helvetica", 15, "bold"),
            bg="#FFFFFF",
            fg="#0F172A"
        ).pack(pady=(14, 8))

        cols = ("Date of Test", "User Name", "Eye", "Score (0–100)", "Acuity (arcmin)", "LogMAR", "Snellen", "95% Interval")
        tree = ttk.Treeview(win, columns=cols, show="headings", height=14)
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, anchor="center", width=102)

        records = stat.load_vision_history()
        for r in reversed(records):
            tree.insert(
                "",
                "end",
                values=(
                    r.get("test_date", ""),
                    r.get("user_name", "Guest"),
                    r.get("eye", ""),
                    r.get("score_0_100", ""),
                    f"{float(r.get('map_k1', 0)):.2f}",
                    f"{float(r.get('map_logmar', 0)):.2f}",
                    r.get("snellen_feet", ""),
                    f"[{float(r.get('ci_low', 0)):.1f}, {float(r.get('ci_high', 0)):.1f}]"
                )
            )
        tree.pack(fill="both", expand=True, padx=20, pady=8)

        def clear_hist():
            if messagebox.askyesno("Clear History", "Are you sure you want to clear all saved vision history?"):
                stat.clear_vision_history()
                win.destroy()

        tk.Button(
            win, text="🗑 Clear Saved History", font=("Helvetica", 10), bg="#FEE2E2", fg="#DC2626",
            relief="flat", padx=14, pady=5, command=clear_hist
        ).pack(pady=8)

    def export_results_report(self):
        filepath = filedialog.asksaveasfilename(
            title="Save StAT Vision Results Report",
            defaultextension=".html",
            initialfile="StAT_Vision_Results_Report.html",
            filetypes=[("HTML Visual Report (with Distributions)", "*.html"), ("JSON Data", "*.json")]
        )
        if not filepath:
            return

        if filepath.endswith(".json"):
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump({
                    "user_name": self.user_name or "Guest",
                    "test_date": self.test_date,
                    "eye_results": self.eye_results,
                    "vision_history": stat.load_vision_history()
                }, f, indent=2)
            messagebox.showinfo("Saved", f"Results saved to:\n{filepath}")
            return

        def make_svg_curve(xs, ys, min_x, max_x, x_label, color):
            w, h = 380, 160
            pad_l, pad_r, pad_t, pad_b = 40, 12, 14, 30
            pw, ph = w - pad_l - pad_r, h - pad_t - pad_b
            max_y = max(max(ys), 0.1) * 1.05
            pts = []
            for xv, yv in zip(xs, ys):
                px = pad_l + ((xv - min_x) / (max_x - min_x)) * pw
                py = pad_t + ph - (yv / max_y) * ph
                pts.append(f"{px:.1f},{py:.1f}")
            poly = " ".join(pts)
            return (
                f'<svg width="{w}" height="{h}" style="background:#fff; border:1px solid #eee; margin:4px 0;">'
                f'<line x1="{pad_l}" y1="{pad_t}" x2="{pad_l}" y2="{pad_t+ph}" stroke="#666"/>'
                f'<line x1="{pad_l}" y1="{pad_t+ph}" x2="{pad_l+pw}" y2="{pad_t+ph}" stroke="#666"/>'
                f'<polyline fill="none" stroke="{color}" stroke-width="2" points="{poly}"/>'
                f'<text x="{pad_l+pw/2}" y="{h-6}" text-anchor="middle" font-size="12" font-family="sans-serif">{x_label}</text>'
                f'</svg>'
            )

        cards_html = ""
        for eye_name in ["Left Eye", "Right Eye"]:
            r = self.eye_results[eye_name]
            if not r:
                cards_html += f'<div class="card"><h3>{eye_name} Results</h3><p><i>No results yet</i></p></div>'
            else:
                svg_arc = make_svg_curve(r["curve_arc_xs"], r["curve_arc_ys"], 0.0, 12.0, "Acuity (arcmins)", "#E15759")
                svg_log = make_svg_curve(r["curve_log_xs"], r["curve_log_ys"], -0.8, 1.25, "Acuity (logMAR)", "#7970C6")
                sc_int = stat.arcmins_interval_to_score_0_100(r["ci_low"], r["ci_high"])
                cards_html += (
                    f'<div class="card">'
                    f'<h3>{eye_name} Results</h3>'
                    f'<p style="color:#1d4ed8;font-weight:bold;">Vision Score (0–100): {r["score_0_100"]} (Interval: {sc_int})</p>'
                    f'<p>Measured acuity score ¹ :<br><b>{r["map_k1"]:.1f} arcmin</b> ({r["snellen_feet"]} | {r["map_logmar"]:.2f} logMAR)</p>'
                    f'<p>With confidence interval ² :<br>{r["ci_low"]:.1f} to {r["ci_high"]:.1f} arcmin</p>'
                    f'{svg_arc}{svg_log}'
                    f'</div>'
                )

        u_txt = self.user_name if self.user_name else "Guest"
        html_doc = (
            "<!DOCTYPE html><html><head><meta charset='utf-8'><title>StAT Vision Report</title>"
            "<style>body{font-family:sans-serif;text-align:center;padding:30px;}"
            ".grid{display:flex;justify-content:center;gap:24px;}"
            ".card{background:#f5f5f5;border:1px solid #ddd;padding:20px;width:420px;border-radius:6px;}</style>"
            f"</head><body><h2>Stanford Acuity Test (StAT) — Results</h2>"
            f"<p style='color:#475569;margin-bottom:20px;'><b>Patient / User:</b> {u_txt} &nbsp;|&nbsp; <b>Date of Test:</b> {self.test_date}</p>"
            f"<div class='grid'>{cards_html}</div></body></html>"
        )

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html_doc)
        messagebox.showinfo("Saved", f"Visual Report with Distributions saved to:\n{filepath}")


if __name__ == "__main__":
    root = tk.Tk()
    app = StATDesktopApp(root)
    root.mainloop()
