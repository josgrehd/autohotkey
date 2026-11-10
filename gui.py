"""
Interfaz gráfica de usuario (GUI) completa con todas las opciones:
- Programador de Teclas, Combos (ctrl+up, shift+f1) y Secuencias (f1, 1, f2).
- Selector dinámico de Ventanas abiertas (Chrome, Edge, Firefox, Tibia, etc.) con auto-foco.
- Auto-Healer por detección de píxel/color (Captura con F8).
- Módulo Anti-AFK (Auto-Dancer para no ser desconectado).
- Guardado y carga de perfiles JSON.
"""

import os
import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import List

from engine import (
    AutoKeyEngine,
    KeyActionRule,
    PixelTriggerRule,
    VK_MAP,
    send_action,
    send_combo,
    get_open_window_titles,
    focus_window_by_title,
    get_mouse_position,
    get_pixel_color,
    is_key_pressed_globally
)

CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "hotkey": "f12",
    "countdown": 0,
    "window_filter": "",
    "auto_focus": False,
    "always_on_top": False,
    "anti_afk_enabled": False,
    "anti_afk_minutes": 5,
    "rules": [
        {"key": "f1", "interval": 1.5, "jitter": 0.1, "enabled": True},
        {"key": "1", "interval": 2.0, "jitter": 0.15, "enabled": True},
        {"key": "f2", "interval": 10.0, "jitter": 0.5, "enabled": True},
        {"key": "ctrl+up, ctrl+right, ctrl+down, ctrl+left", "interval": 60.0, "jitter": 2.0, "enabled": False},
    ],
    "pixel_triggers": [
        {
            "name": "Auto-Heal (Vida)",
            "x": 0,
            "y": 0,
            "expected_color": [0, 200, 0],
            "trigger_action": "f1",
            "cooldown": 1.0,
            "enabled": False
        },
        {
            "name": "Auto-Mana (Poción)",
            "x": 0,
            "y": 0,
            "expected_color": [0, 100, 255],
            "trigger_action": "f2",
            "cooldown": 1.5,
            "enabled": False
        }
    ]
}

AVAILABLE_KEYS = [
    "f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9", "f10", "f11", "f12",
    "1", "2", "3", "4", "5", "6", "7", "8", "9", "0",
    "space", "enter", "tab", "escape",
    "ctrl+up", "ctrl+down", "ctrl+left", "ctrl+right",
    "shift+f1", "shift+f2", "ctrl+f1", "ctrl+1",
    "f1, 1", "f1, 1, f2",
    "a", "b", "c", "d", "e", "f", "q", "w", "r", "s", "x"
]

HOTKEY_CHOICES = ["f12", "f11", "f10", "f9", "f8", "f7", "f6"]


class RuleRow:
    """Fila visual en la lista de teclas programadas."""
    def __init__(self, parent, rule: KeyActionRule, on_delete_callback, on_change_callback):
        self.parent = parent
        self.on_delete_callback = on_delete_callback
        self.on_change_callback = on_change_callback

        self.enabled_var = tk.BooleanVar(value=rule.enabled)
        self.key_var = tk.StringVar(value=rule.key)
        self.interval_var = tk.StringVar(value=str(rule.interval))
        self.jitter_var = tk.StringVar(value=str(rule.jitter))

        self.frame = ttk.Frame(parent, padding=(4, 3))
        self._build_widgets()

    def _build_widgets(self):
        self.chk = ttk.Checkbutton(self.frame, variable=self.enabled_var, command=self.on_change_callback)
        self.chk.grid(row=0, column=0, padx=(5, 10))

        self.key_cb = ttk.Combobox(self.frame, textvariable=self.key_var, values=AVAILABLE_KEYS, width=16)
        self.key_cb.grid(row=0, column=1, padx=5)
        self.key_cb.bind("<<ComboboxSelected>>", lambda e: self.on_change_callback())
        self.key_cb.bind("<KeyRelease>", lambda e: self.on_change_callback())

        self.int_entry = ttk.Entry(self.frame, textvariable=self.interval_var, width=8, justify="center")
        self.int_entry.grid(row=0, column=2, padx=5)
        self.int_entry.bind("<KeyRelease>", lambda e: self.on_change_callback())

        self.jit_entry = ttk.Entry(self.frame, textvariable=self.jitter_var, width=8, justify="center")
        self.jit_entry.grid(row=0, column=3, padx=5)
        self.jit_entry.bind("<KeyRelease>", lambda e: self.on_change_callback())

        self.btn_test = ttk.Button(self.frame, text="Probar", width=7, command=self._test_key)
        self.btn_test.grid(row=0, column=4, padx=5)

        self.btn_del = ttk.Button(self.frame, text="❌", width=3, command=lambda: self.on_delete_callback(self))
        self.btn_del.grid(row=0, column=5, padx=(5, 5))

    def _test_key(self):
        action = self.key_var.get().strip()
        if not action:
            messagebox.showwarning("Atención", "Debes especificar una tecla para probar.")
            return
        success = send_action(action)
        if not success:
            messagebox.showerror("Error", f"No se pudo ejecutar '{action}'. Revisa el nombre.")

    def get_rule(self) -> KeyActionRule:
        try:
            interval = float(self.interval_var.get())
        except ValueError:
            interval = 1.0

        try:
            jitter = float(self.jitter_var.get())
        except ValueError:
            jitter = 0.0

        return KeyActionRule(
            key=self.key_var.get().strip().lower(),
            interval=interval,
            jitter=jitter,
            enabled=self.enabled_var.get()
        )

    def destroy(self):
        self.frame.destroy()


class PixelTriggerWidget:
    """Widget de configuración para una regla de Auto-Heal por detección de color de píxel."""
    def __init__(self, parent, rule: PixelTriggerRule, on_change_callback, root_ref):
        self.parent = parent
        self.on_change_callback = on_change_callback
        self.root_ref = root_ref

        self.enabled_var = tk.BooleanVar(value=rule.enabled)
        self.name_var = tk.StringVar(value=rule.name)
        self.coords_var = tk.StringVar(value=f"X: {rule.x}, Y: {rule.y}")
        self.x = rule.x
        self.y = rule.y
        self.color = rule.expected_color
        self.action_var = tk.StringVar(value=rule.trigger_action)
        self.cooldown_var = tk.StringVar(value=str(rule.cooldown))

        self.card = ttk.LabelFrame(parent, text=f" {rule.name} ", padding=8)
        self._build()

    def _build(self):
        row1 = ttk.Frame(self.card)
        row1.pack(fill="x", pady=2)

        ttk.Checkbutton(row1, text="Habilitar regla", variable=self.enabled_var, command=self.on_change_callback).pack(side="left")

        ttk.Label(row1, text="  |  Tecla a pulsar:").pack(side="left")
        ttk.Entry(row1, textvariable=self.action_var, width=8, justify="center").pack(side="left", padx=5)

        ttk.Label(row1, text="Cooldown:").pack(side="left", padx=(10, 2))
        ttk.Entry(row1, textvariable=self.cooldown_var, width=5, justify="center").pack(side="left")
        ttk.Label(row1, text="s").pack(side="left")

        row2 = ttk.Frame(self.card)
        row2.pack(fill="x", pady=4)

        ttk.Label(row2, text="Posición detectada:").pack(side="left")
        ttk.Label(row2, textvariable=self.coords_var, font=("Segoe UI", 9, "bold")).pack(side="left", padx=5)

        # Muestra visual del color
        self.color_preview = tk.Canvas(row2, width=22, height=16, relief="ridge", bd=1)
        self.color_preview.pack(side="left", padx=5)
        self._update_color_preview()

        # Botón para capturar con F8
        self.btn_capture = ttk.Button(row2, text="📍 Capturar con F8", command=self._start_capture_mode)
        self.btn_capture.pack(side="left", padx=(10, 5))

        # Botón para probar disparo
        ttk.Button(row2, text="Probar Tecla", command=lambda: send_action(self.action_var.get())).pack(side="left", padx=5)

    def _update_color_preview(self):
        hex_color = f"#{self.color[0]:02x}{self.color[1]:02x}{self.color[2]:02x}"
        self.color_preview.configure(bg=hex_color)

    def _start_capture_mode(self):
        messagebox.showinfo(
            "Modo Captura de Píxel",
            "1. Coloca el puntero del ratón sobre la barra de Vida o Maná.\n"
            "2. Presiona la tecla F8 en tu teclado.\n\n"
            "La posición exacta y el color actual se capturarán automáticamente."
        )

        def _check_f8():
            # VK_F8 = 0x77
            if is_key_pressed_globally(0x77):
                mx, my = get_mouse_position()
                rgb = get_pixel_color(mx, my)
                self.x = mx
                self.y = my
                self.color = rgb
                self.coords_var.set(f"X: {mx}, Y: {my}")
                self._update_color_preview()
                self.on_change_callback()
                messagebox.showinfo("¡Capturado!", f"Posición guardada: X={mx}, Y={my}\nColor RGB: {rgb}")
            else:
                self.root_ref.after(100, _check_f8)

        self.root_ref.after(100, _check_f8)

    def get_rule(self) -> PixelTriggerRule:
        try:
            cd = float(self.cooldown_var.get())
        except ValueError:
            cd = 1.0

        return PixelTriggerRule(
            name=self.name_var.get(),
            x=self.x,
            y=self.y,
            expected_color=self.color,
            trigger_action=self.action_var.get(),
            cooldown=cd,
            enabled=self.enabled_var.get()
        )


class AutoKeyApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Auto Key Presser - Suite Completa (Gaming & Navegadores)")
        self.root.geometry("740x780")
        self.root.minsize(700, 680)

        self.style = ttk.Style()
        self._setup_styles()

        self.engine = AutoKeyEngine(
            on_log=self._threadsafe_log,
            on_state_change=self._threadsafe_state_change
        )

        self.rows: List[RuleRow] = []
        self.pixel_widgets: List[PixelTriggerWidget] = []

        # Variables reactivas
        self.hotkey_var = tk.StringVar(value="f12")
        self.countdown_var = tk.IntVar(value=0)
        self.window_filter_var = tk.StringVar(value="")
        self.auto_focus_var = tk.BooleanVar(value=False)
        self.always_on_top_var = tk.BooleanVar(value=False)

        # Anti-AFK
        self.anti_afk_enabled_var = tk.BooleanVar(value=False)
        self.anti_afk_mins_var = tk.IntVar(value=5)

        self._build_ui()
        self.load_config(CONFIG_FILE)

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _setup_styles(self):
        available_themes = self.style.theme_names()
        if "vista" in available_themes:
            self.style.theme_use("vista")
        elif "clam" in available_themes:
            self.style.theme_use("clam")

        self.style.configure("BigStart.TButton", font=("Segoe UI", 11, "bold"), foreground="#006600")
        self.style.configure("BigStop.TButton", font=("Segoe UI", 11, "bold"), foreground="#cc0000")
        self.style.configure("Header.TLabel", font=("Segoe UI", 9, "bold"))

    def _build_ui(self):
        # 1. Cabecera Principal de Control
        header_card = ttk.LabelFrame(self.root, text=" Panel de Control Principal ", padding=10)
        header_card.pack(fill="x", padx=12, pady=(8, 4))

        self.status_lbl = tk.Label(
            header_card,
            text="ESTADO: DETENIDO",
            bg="#333333",
            fg="#ff5555",
            font=("Segoe UI", 13, "bold"),
            padx=12,
            pady=4,
            relief="groove"
        )
        self.status_lbl.pack(fill="x", pady=(0, 6))

        self.btn_toggle = ttk.Button(
            header_card,
            text="▶ INICIAR AUTOMATIZACIÓN (o presiona F12)",
            style="BigStart.TButton",
            command=self.toggle_engine
        )
        self.btn_toggle.pack(fill="x", ipady=5, pady=(0, 8))

        # Fila rápida de Ventana Objetivo
        win_row = ttk.Frame(header_card)
        win_row.pack(fill="x", pady=(2, 2))

        ttk.Label(win_row, text="Ventana / Navegador:", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 5))
        self.win_cb = ttk.Combobox(win_row, textvariable=self.window_filter_var, width=28)
        self.win_cb.pack(side="left", padx=(0, 6))
        self.win_cb.bind("<<ComboboxSelected>>", lambda e: self._sync_engine_rules())
        self.win_cb.bind("<KeyRelease>", lambda e: self._sync_engine_rules())

        ttk.Button(win_row, text="🔄 Detectar Ventanas", command=self.refresh_open_windows).pack(side="left", padx=2)
        ttk.Button(win_row, text="🎯 Probar Foco", command=self.test_focus_window).pack(side="left", padx=2)

        chk_focus = ttk.Checkbutton(
            header_card,
            text="Traer la ventana al frente automáticamente al Iniciar",
            variable=self.auto_focus_var,
            command=self._sync_engine_rules
        )
        chk_focus.pack(anchor="w", pady=(4, 0))

        # 2. Pestañas (Notebook)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=12, pady=6)

        # Pestaña 1: Teclas y Rotaciones
        self.tab_keys = ttk.Frame(self.notebook, padding=6)
        self.notebook.add(self.tab_keys, text=" ⌨️ Teclas y Rotaciones ")
        self._build_tab_keys()

        # Pestaña 2: Auto-Healer por Píxel
        self.tab_healer = ttk.Frame(self.notebook, padding=8)
        self.notebook.add(self.tab_healer, text=" 🩸 Auto-Healer (Color Píxel) ")
        self._build_tab_healer()

        # Pestaña 3: Anti-AFK (Auto-Dancer)
        self.tab_afk = ttk.Frame(self.notebook, padding=8)
        self.notebook.add(self.tab_afk, text=" 🛡️ Anti-AFK (Auto-Dancer) ")
        self._build_tab_afk()

        # Pestaña 4: Ajustes y Atajos
        self.tab_settings = ttk.Frame(self.notebook, padding=8)
        self.notebook.add(self.tab_settings, text=" ⚙️ Ajustes ")
        self._build_tab_settings()

        # 3. Consola de Registro Inferior
        log_card = ttk.LabelFrame(self.root, text=" Registro de Actividad en Tiempo Real ", padding=6)
        log_card.pack(fill="x", padx=12, pady=(4, 8))

        log_inner = ttk.Frame(log_card)
        log_inner.pack(fill="both", expand=True)

        self.log_text = tk.Text(log_inner, height=5, wrap="word", font=("Consolas", 9), bg="#1e1e1e", fg="#d4d4d4")
        log_scroll = ttk.Scrollbar(log_inner, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scroll.set)

        self.log_text.pack(side="left", fill="both", expand=True)
        log_scroll.pack(side="right", fill="y")

        log_actions = ttk.Frame(log_card)
        log_actions.pack(fill="x", pady=(3, 0))
        ttk.Button(log_actions, text="Limpiar registro", command=self.clear_log).pack(side="right")

    def _build_tab_keys(self):
        cols_frame = ttk.Frame(self.tab_keys)
        cols_frame.pack(fill="x", padx=5, pady=(0, 4))
        ttk.Label(cols_frame, text="Activo", style="Header.TLabel", width=6).grid(row=0, column=0, padx=(5, 10))
        ttk.Label(cols_frame, text="Tecla / Combo / Secuencia", style="Header.TLabel", width=22).grid(row=0, column=1, padx=5)
        ttk.Label(cols_frame, text="Intervalo (s)", style="Header.TLabel", width=12).grid(row=0, column=2, padx=5)
        ttk.Label(cols_frame, text="Variación ±(s)", style="Header.TLabel", width=13).grid(row=0, column=3, padx=5)
        ttk.Label(cols_frame, text="Probar", style="Header.TLabel", width=8).grid(row=0, column=4, padx=5)
        ttk.Label(cols_frame, text="Borrar", style="Header.TLabel", width=6).grid(row=0, column=5, padx=5)

        self.canvas = tk.Canvas(self.tab_keys, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.tab_keys, orient="vertical", command=self.canvas.yview)
        self.scroll_frame = ttk.Frame(self.canvas)

        self.scroll_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width))

        self.canvas.pack(side="top", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y", before=self.canvas)

        btn_bar = ttk.Frame(self.tab_keys, padding=(0, 6, 0, 0))
        btn_bar.pack(fill="x")

        ttk.Button(btn_bar, text="➕ Agregar Tecla / Combo", command=self.add_empty_row).pack(side="left", padx=4)
        ttk.Button(btn_bar, text="🔄 Cargar Ejemplo Tibia", command=self.load_preset_tibia).pack(side="left", padx=4)
        ttk.Button(btn_bar, text="💾 Guardar Perfil", command=self.save_config_dialog).pack(side="right", padx=4)
        ttk.Button(btn_bar, text="📂 Cargar Perfil", command=self.load_config_dialog).pack(side="right", padx=4)

    def _build_tab_healer(self):
        info = (
            "El Auto-Healer lee directamente el color del píxel de tu barra de Vida o Maná.\n"
            "Cuando la vida baja, el color original desaparece y el bot pulsa tu hechizo de curación o poción."
        )
        ttk.Label(self.tab_healer, text=info, foreground="#444444", wraplength=680).pack(fill="x", pady=(0, 8))

        self.healer_container = ttk.Frame(self.tab_healer)
        self.healer_container.pack(fill="both", expand=True)

    def _build_tab_afk(self):
        info_afk = (
            "El Anti-AFK (Auto-Dancer) gira periódicamente a tu personaje en su misma casilla\n"
            "usando 'Ctrl + Flechas'. Evita la desconexión automática por inactividad tras 15 minutos."
        )
        ttk.Label(self.tab_afk, text=info_afk, foreground="#444444", wraplength=680).pack(fill="x", pady=(0, 10))

        afk_card = ttk.LabelFrame(self.tab_afk, text=" Configuración Anti-AFK ", padding=10)
        afk_card.pack(fill="x", pady=4)

        ttk.Checkbutton(
            afk_card,
            text="Activar Anti-AFK (Auto-Dancer periódico)",
            variable=self.anti_afk_enabled_var,
            command=self._sync_engine_rules
        ).pack(anchor="w", pady=(0, 10))

        row = ttk.Frame(afk_card)
        row.pack(fill="x", pady=4)

        ttk.Label(row, text="Ejecutar rotación cada:").pack(side="left")
        ttk.Spinbox(
            row,
            from_=1,
            to=14,
            textvariable=self.anti_afk_mins_var,
            width=5,
            justify="center",
            command=self._sync_engine_rules
        ).pack(side="left", padx=6)
        ttk.Label(row, text="minutos (Recomendado: 5 a 10 min)").pack(side="left")

        ttk.Button(
            afk_card,
            text="🔄 Probar Rotación de Giro Ahora",
            command=lambda: send_action("ctrl+up, ctrl+right, ctrl+down, ctrl+left", inter_key_delay=0.1)
        ).pack(anchor="w", pady=(12, 0))

    def _build_tab_settings(self):
        card = ttk.LabelFrame(self.tab_settings, text=" Opciones Generales ", padding=10)
        card.pack(fill="x", pady=4)

        # Atajo global
        row1 = ttk.Frame(card)
        row1.pack(fill="x", pady=4)
        ttk.Label(row1, text="Atajo rápido global para Iniciar/Pausar:").pack(side="left")
        self.hotkey_cb = ttk.Combobox(row1, textvariable=self.hotkey_var, values=HOTKEY_CHOICES, width=6, state="readonly")
        self.hotkey_cb.pack(side="left", padx=8)
        self.hotkey_cb.bind("<<ComboboxSelected>>", self._on_hotkey_changed)

        # Cuenta regresiva
        row2 = ttk.Frame(card)
        row2.pack(fill="x", pady=4)
        ttk.Label(row2, text="Cuenta regresiva al hacer clic en Iniciar:").pack(side="left")
        ttk.Spinbox(row2, from_=0, to=10, textvariable=self.countdown_var, width=5, justify="center").pack(side="left", padx=8)
        ttk.Label(row2, text="segundos").pack(side="left")

        # Siempre encima
        row3 = ttk.Frame(card)
        row3.pack(fill="x", pady=4)
        ttk.Checkbutton(
            row3,
            text="Mantener ventana de la aplicación siempre encima (Always on Top)",
            variable=self.always_on_top_var,
            command=self._update_always_on_top
        ).pack(side="left")

    def _update_always_on_top(self):
        self.root.attributes("-topmost", self.always_on_top_var.get())

    def refresh_open_windows(self):
        titles = get_open_window_titles()
        self.win_cb["values"] = titles
        self._threadsafe_log(f"Detectadas {len(titles)} ventanas abiertas en tu PC.")

    def test_focus_window(self):
        target = self.window_filter_var.get().strip()
        if not target:
            messagebox.showwarning("Atención", "Selecciona o escribe el nombre de una ventana primero.")
            return
        ok = focus_window_by_title(target)
        if ok:
            self._threadsafe_log(f"Ventana traída al frente: '{target}'")
        else:
            messagebox.showerror("No encontrada", f"No se encontró ninguna ventana abierta que contenga '{target}'.")

    def _sync_engine_rules(self):
        rules = [row.get_rule() for row in self.rows]
        self.engine.set_rules(rules)

        triggers = [w.get_rule() for w in self.pixel_widgets]
        self.engine.set_pixel_triggers(triggers)

        self.engine.target_window_filter = self.window_filter_var.get().strip()
        self.engine.auto_focus_window = self.auto_focus_var.get()
        self.engine.anti_afk_enabled = self.anti_afk_enabled_var.get()
        self.engine.anti_afk_interval_sec = max(30.0, float(self.anti_afk_mins_var.get()) * 60.0)

    def _on_hotkey_changed(self, event=None):
        hotkey = self.hotkey_var.get().strip().lower()
        self.engine.set_hotkey(hotkey)
        self.btn_toggle.configure(text=f"{'⏹ DETENER' if self.engine.is_running() else '▶ INICIAR'} AUTOMATIZACIÓN (o presiona {hotkey.upper()})")
        self._threadsafe_log(f"Atajo rápido cambiado a: {hotkey.upper()}")

    def add_row(self, rule: KeyActionRule):
        row = RuleRow(
            parent=self.scroll_frame,
            rule=rule,
            on_delete_callback=self.remove_row,
            on_change_callback=self._sync_engine_rules
        )
        row.frame.pack(fill="x", pady=2)
        self.rows.append(row)
        self._sync_engine_rules()

    def add_empty_row(self):
        self.add_row(KeyActionRule(key="f1", interval=2.0, jitter=0.1, enabled=True))

    def remove_row(self, row: RuleRow):
        if row in self.rows:
            self.rows.remove(row)
            row.destroy()
            self._sync_engine_rules()

    def clear_rows(self):
        for row in self.rows:
            row.destroy()
        self.rows.clear()
        self._sync_engine_rules()

    def toggle_engine(self):
        if self.engine.is_running():
            self.engine.stop()
        else:
            self._sync_engine_rules()
            has_active_rules = any(r.enabled for r in self.engine.rules)
            has_active_triggers = any(t.enabled for t in self.engine.pixel_triggers)
            has_afk = self.engine.anti_afk_enabled

            if not (has_active_rules or has_active_triggers or has_afk):
                messagebox.showwarning("Atención", "No hay ninguna tecla, trigger de vida o Anti-AFK activo. Marca alguna casilla 'Activo'.")
                return

            cd = self.countdown_var.get()
            self.engine.start(countdown_seconds=float(cd))

    def _threadsafe_state_change(self, running: bool):
        self.root.after(0, lambda: self._update_ui_state(running))

    def _update_ui_state(self, running: bool):
        hotkey = self.hotkey_var.get().upper()
        if running:
            self.status_lbl.configure(text="ESTADO: EN EJECUCIÓN 🟢", fg="#44ff44", bg="#1a331a")
            self.btn_toggle.configure(text=f"⏹ DETENER AUTOMATIZACIÓN (o presiona {hotkey})", style="BigStop.TButton")
        else:
            self.status_lbl.configure(text="ESTADO: DETENIDO 🛑", fg="#ff5555", bg="#331a1a")
            self.btn_toggle.configure(text=f"▶ INICIAR AUTOMATIZACIÓN (o presiona {hotkey})", style="BigStart.TButton")

    def _threadsafe_log(self, msg: str):
        self.root.after(0, lambda: self._append_log(msg))

    def _append_log(self, msg: str):
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)

    def clear_log(self):
        self.log_text.delete("1.0", tk.END)

    def load_preset_tibia(self):
        if messagebox.askyesno("Confirmar", "¿Deseas cargar la plantilla recomendada para Tibia?"):
            self.clear_rows()
            preset = [
                KeyActionRule("f1", 1.2, 0.1, True),   # Curación rápida
                KeyActionRule("1", 2.0, 0.15, True),   # Hechizo de ataque
                KeyActionRule("f2", 8.0, 0.4, True),   # Poción de maná
                KeyActionRule("f3", 30.0, 1.0, True),  # Buff de soporte
                KeyActionRule("f1, 1", 3.0, 0.2, False) # Combo rotación
            ]
            for rule in preset:
                self.add_row(rule)
            self.window_filter_var.set("Tibia")
            self.auto_focus_var.set(True)
            self.anti_afk_enabled_var.set(True)
            self._sync_engine_rules()
            self._append_log("Plantilla de Tibia cargada con rotaciones y Anti-AFK.")

    def save_config(self, filepath: str):
        data = {
            "hotkey": self.hotkey_var.get(),
            "countdown": self.countdown_var.get(),
            "window_filter": self.window_filter_var.get(),
            "auto_focus": self.auto_focus_var.get(),
            "always_on_top": self.always_on_top_var.get(),
            "anti_afk_enabled": self.anti_afk_enabled_var.get(),
            "anti_afk_minutes": self.anti_afk_mins_var.get(),
            "rules": [r.to_dict() for r in [row.get_rule() for row in self.rows]],
            "pixel_triggers": [t.to_dict() for t in [w.get_rule() for w in self.pixel_widgets]]
        }
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            self._append_log(f"Configuración guardada en: {filepath}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar la configuración: {e}")

    def save_config_dialog(self):
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("Archivos JSON", "*.json"), ("Todos los archivos", "*.*")])
        if path:
            self.save_config(path)

    def load_config(self, filepath: str):
        if not os.path.exists(filepath):
            data = DEFAULT_CONFIG
        else:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = DEFAULT_CONFIG

        self.hotkey_var.set(data.get("hotkey", "f12"))
        self.countdown_var.set(data.get("countdown", 0))
        self.window_filter_var.set(data.get("window_filter", ""))
        self.auto_focus_var.set(data.get("auto_focus", False))
        self.always_on_top_var.set(data.get("always_on_top", False))
        self._update_always_on_top()

        self.anti_afk_enabled_var.set(data.get("anti_afk_enabled", False))
        self.anti_afk_mins_var.set(data.get("anti_afk_minutes", 5))

        self.clear_rows()
        for rule_data in data.get("rules", []):
            self.add_row(KeyActionRule.from_dict(rule_data))

        # Cargar triggers de píxel
        for w in self.pixel_widgets:
            w.card.destroy()
        self.pixel_widgets.clear()

        for pt_data in data.get("pixel_triggers", DEFAULT_CONFIG["pixel_triggers"]):
            rule = PixelTriggerRule.from_dict(pt_data)
            widget = PixelTriggerWidget(self.healer_container, rule, self._sync_engine_rules, self.root)
            widget.card.pack(fill="x", pady=4)
            self.pixel_widgets.append(widget)

        self._sync_engine_rules()
        self._on_hotkey_changed()
        self.refresh_open_windows()

    def load_config_dialog(self):
        path = filedialog.askopenfilename(filetypes=[("Archivos JSON", "*.json"), ("Todos los archivos", "*.*")])
        if path:
            self.load_config(path)

    def on_closing(self):
        self.save_config(CONFIG_FILE)
        self.engine.shutdown()
        self.root.destroy()
