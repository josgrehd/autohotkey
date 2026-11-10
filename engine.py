"""
Motor avanzado de automatización para Windows:
- Win32 SendInput con Hardware Scan Codes (DirectInput / DirectX compatible para Tibia y juegos).
- Soporte para teclas simples, combinaciones (ctrl+up, shift+f1) y secuencias (f1, 1, f2).
- Detección y enfoque de ventanas de navegadores (Chrome, Edge, Firefox) y juegos.
- Módulo Anti-AFK (Auto-Dancer con rotación por teclas).
- Módulo Auto-Healer por detección de píxel/color en pantalla (GetPixel nativo GDI).
- 100% biblioteca estándar de Python (ctypes, time, random, threading).
"""

import ctypes
import time
import random
import threading
from ctypes import wintypes
from typing import Callable, Dict, List, Optional, Tuple

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

# Constantes de Windows
INPUT_KEYBOARD = 1
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_SCANCODE = 0x0008
MAPVK_VK_TO_VSC = 0
SW_RESTORE = 9

# Estructuras de SendInput
class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t)
    ]

class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD)
    ]

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t)
    ]

class _INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT)
    ]

class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("union", _INPUT_UNION)
    ]

class POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)


# Mapa de teclas virtuales (insensible a mayúsculas)
VK_MAP = {
    # Teclas de función
    "f1": 0x70, "f2": 0x71, "f3": 0x72, "f4": 0x73,
    "f5": 0x74, "f6": 0x75, "f7": 0x76, "f8": 0x77,
    "f9": 0x78, "f10": 0x79, "f11": 0x7A, "f12": 0x7B,
    # Números principales
    "0": 0x30, "1": 0x31, "2": 0x32, "3": 0x33, "4": 0x34,
    "5": 0x35, "6": 0x36, "7": 0x37, "8": 0x38, "9": 0x39,
    # Teclado numérico
    "num0": 0x60, "num1": 0x61, "num2": 0x62, "num3": 0x63, "num4": 0x64,
    "num5": 0x65, "num6": 0x66, "num7": 0x67, "num8": 0x68, "num9": 0x69,
    # Letras A-Z
    **{chr(c).lower(): c for c in range(0x41, 0x5B)},
    # Modificadores
    "ctrl": 0x11, "control": 0x11,
    "shift": 0x10,
    "alt": 0x12,
    # Teclas especiales
    "space": 0x20, "espacio": 0x20,
    "enter": 0x0D, "intro": 0x0D,
    "tab": 0x09, "tabulador": 0x09,
    "escape": 0x1B, "esc": 0x1B,
    # Flechas
    "up": 0x26, "arriba": 0x26,
    "down": 0x28, "abajo": 0x28,
    "left": 0x27, "izquierda": 0x27,
    "right": 0x25, "derecha": 0x25,
}

EXTENDED_KEYS = {0x26, 0x28, 0x27, 0x25, 0x2D, 0x2E, 0x24, 0x23, 0x21, 0x22}


def get_virtual_key(key_name: str) -> Optional[int]:
    """Obtiene el Virtual Key code dado un nombre."""
    return VK_MAP.get(key_name.strip().lower())


def get_scan_code(vk: int) -> int:
    """Convierte un Virtual Key code a Scan Code de hardware."""
    return user32.MapVirtualKeyW(vk, MAPVK_VK_TO_VSC)


# --- Envío de Teclas y Combinaciones ---

def _key_event(scan: int, vk: int, is_up: bool = False):
    extra = ctypes.c_size_t(0)
    flags = KEYEVENTF_SCANCODE
    if is_up:
        flags |= KEYEVENTF_KEYUP
    if vk in EXTENDED_KEYS:
        flags |= KEYEVENTF_EXTENDEDKEY

    inp = INPUT(
        type=INPUT_KEYBOARD,
        union=_INPUT_UNION(ki=KEYBDINPUT(0, scan, flags, 0, ctypes.addressof(extra)))
    )
    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))


def send_single_key(key_name: str, hold_time: float = 0.04) -> bool:
    """Presiona y suelta una sola tecla con scan code de hardware."""
    vk = get_virtual_key(key_name)
    if vk is None:
        return False
    scan = get_scan_code(vk)
    if scan == 0 and vk not in (0x10, 0x11, 0x12):
        return False

    _key_event(scan, vk, is_up=False)
    time.sleep(max(0.02, hold_time))
    _key_event(scan, vk, is_up=True)
    return True


def send_combo(combo_str: str, hold_time: float = 0.04) -> bool:
    """
    Presiona una combinación con modificadores (ej: 'ctrl+up', 'shift+f1', 'alt+1').
    """
    parts = [p.strip().lower() for p in combo_str.split("+") if p.strip()]
    if not parts:
        return False

    vks_scans = []
    for part in parts:
        vk = get_virtual_key(part)
        if vk is None:
            return False
        scan = get_scan_code(vk)
        vks_scans.append((vk, scan))

    # Presionar en orden
    for vk, scan in vks_scans:
        _key_event(scan, vk, is_up=False)
        time.sleep(0.01)

    time.sleep(max(0.02, hold_time))

    # Soltar en orden inverso
    for vk, scan in reversed(vks_scans):
        _key_event(scan, vk, is_up=True)
        time.sleep(0.01)

    return True


def send_action(action_str: str, inter_key_delay: float = 0.15) -> bool:
    """
    Ejecuta una acción que puede ser:
    - Una tecla simple: 'f1'
    - Una combinación con '+': 'ctrl+up'
    - Una secuencia separada por comas: 'f1, 1, f2' (con pausa entre cada una).
    """
    sequence = [s.strip() for s in action_str.split(",") if s.strip()]
    if not sequence:
        return False

    all_ok = True
    for idx, item in enumerate(sequence):
        if "+" in item:
            ok = send_combo(item)
        else:
            ok = send_single_key(item)
        if not ok:
            all_ok = False
        if idx < len(sequence) - 1:
            time.sleep(inter_key_delay)
    return all_ok


# --- Gestión de Ventanas de Navegadores y Juegos ---

def get_active_window_title() -> str:
    """Devuelve el título de la ventana activa en Windows."""
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return ""
    length = user32.GetWindowTextLengthW(hwnd)
    if length <= 0:
        return ""
    buff = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buff, length + 1)
    return buff.value


def get_open_window_titles() -> List[str]:
    """Obtiene la lista de todas las ventanas visibles abiertas (Chrome, Edge, Firefox, Tibia, etc.)."""
    titles = []

    def enum_cb(hwnd, lparam):
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buff, length + 1)
                title = buff.value.strip()
                # Filtrar ventanas internas o vacías
                if title and title not in ("Program Manager", "Settings", "Configuración") and title not in titles:
                    titles.append(title)
        return True

    user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
    return sorted(titles, key=lambda s: s.lower())


def focus_window_by_title(substring: str) -> bool:
    """Busca una ventana cuyo título contenga 'substring' y la trae al frente."""
    if not substring.strip():
        return False
    target = substring.strip().lower()
    found_hwnd = None

    def enum_cb(hwnd, lparam):
        nonlocal found_hwnd
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buff, length + 1)
                if target in buff.value.lower():
                    found_hwnd = hwnd
                    return False
        return True

    user32.EnumWindows(WNDENUMPROC(enum_cb), 0)

    if found_hwnd:
        if user32.IsIconic(found_hwnd):
            user32.ShowWindow(found_hwnd, SW_RESTORE)
        user32.SetForegroundWindow(found_hwnd)
        return True
    return False


def is_key_pressed_globally(vk: int) -> bool:
    """Comprueba si una tecla física está presionada en cualquier parte del sistema."""
    return bool(user32.GetAsyncKeyState(vk) & 0x8000)


# --- Detección de Píxeles / Auto-Healer ---

def get_mouse_position() -> Tuple[int, int]:
    """Devuelve la posición actual del cursor (X, Y) en la pantalla."""
    pt = POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y


def get_pixel_color(x: int, y: int) -> Tuple[int, int, int]:
    """Lee el color RGB de un píxel en la pantalla utilizando GDI nativo."""
    hdc = user32.GetDC(0)
    color_ref = gdi32.GetPixel(hdc, x, y)
    user32.ReleaseDC(0, hdc)
    r = color_ref & 0xFF
    g = (color_ref >> 8) & 0xFF
    b = (color_ref >> 16) & 0xFF
    return r, g, b


def is_color_similar(c1: Tuple[int, int, int], c2: Tuple[int, int, int], tolerance: int = 35) -> bool:
    """Verifica si dos colores RGB son similares dentro de una tolerancia."""
    return (
        abs(c1[0] - c2[0]) <= tolerance and
        abs(c1[1] - c2[1]) <= tolerance and
        abs(c1[2] - c2[2]) <= tolerance
    )


# --- Clases de Reglas y Configuración ---

class KeyActionRule:
    """Regla para presionar una tecla, combo o secuencia periódicamente."""
    def __init__(self, key: str, interval: float, jitter: float = 0.0, enabled: bool = True):
        self.key = key.strip().lower()
        self.interval = max(0.05, float(interval))
        self.jitter = max(0.0, float(jitter))
        self.enabled = enabled
        self.next_run_time: float = 0.0

    def compute_next_run(self, from_time: float) -> None:
        delta = self.interval
        if self.jitter > 0:
            variation = random.uniform(-self.jitter, self.jitter)
            delta = max(0.05, delta + variation)
        self.next_run_time = from_time + delta

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "interval": self.interval,
            "jitter": self.jitter,
            "enabled": self.enabled
        }

    @classmethod
    def from_dict(cls, data: dict) -> "KeyActionRule":
        return cls(
            key=data.get("key", "1"),
            interval=data.get("interval", 1.0),
            jitter=data.get("jitter", 0.0),
            enabled=data.get("enabled", True)
        )


class PixelTriggerRule:
    """Regla de activación por color de píxel (Auto-Healer / Auto-Mana)."""
    def __init__(
        self,
        name: str,
        x: int,
        y: int,
        expected_color: Tuple[int, int, int],
        trigger_action: str,
        cooldown: float = 1.0,
        enabled: bool = False
    ):
        self.name = name
        self.x = int(x)
        self.y = int(y)
        self.expected_color = expected_color  # Color de la barra llena (ej: verde o azul)
        self.trigger_action = trigger_action.strip().lower() # Tecla a pulsar cuando la barra baje
        self.cooldown = max(0.2, float(cooldown))
        self.enabled = enabled
        self.last_triggered: float = 0.0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "x": self.x,
            "y": self.y,
            "expected_color": list(self.expected_color),
            "trigger_action": self.trigger_action,
            "cooldown": self.cooldown,
            "enabled": self.enabled
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PixelTriggerRule":
        return cls(
            name=data.get("name", "Trigger"),
            x=data.get("x", 0),
            y=data.get("y", 0),
            expected_color=tuple(data.get("expected_color", [0, 255, 0])),
            trigger_action=data.get("trigger_action", "f1"),
            cooldown=data.get("cooldown", 1.0),
            enabled=data.get("enabled", False)
        )


# --- Motor Principal de Automatización ---

class AutoKeyEngine:
    def __init__(
        self,
        on_log: Optional[Callable[[str], None]] = None,
        on_state_change: Optional[Callable[[bool], None]] = None
    ):
        self.rules: List[KeyActionRule] = []
        self.pixel_triggers: List[PixelTriggerRule] = []

        self.running: bool = False
        self._stop_event = threading.Event()
        self._worker_thread: Optional[threading.Thread] = None
        self._hotkey_thread: Optional[threading.Thread] = None

        # Atajos y Ventanas
        self.hotkey_vk: int = VK_MAP["f12"] # F12 por defecto
        self.target_window_filter: str = "" # Filtro de ventana objetivo
        self.auto_focus_window: bool = False # Traer ventana al frente al iniciar

        # Módulo Anti-AFK (Auto-Dancer)
        self.anti_afk_enabled: bool = False
        self.anti_afk_interval_sec: float = 300.0 # Cada 5 minutos por defecto
        self._next_anti_afk_time: float = 0.0

        self.on_log = on_log or (lambda msg: None)
        self.on_state_change = on_state_change or (lambda running: None)

        self._hotkey_listening = True
        self._start_hotkey_listener()

    def set_rules(self, rules: List[KeyActionRule]) -> None:
        self.rules = rules

    def set_pixel_triggers(self, triggers: List[PixelTriggerRule]) -> None:
        self.pixel_triggers = triggers

    def set_hotkey(self, key_name: str) -> bool:
        vk = get_virtual_key(key_name)
        if vk is not None:
            self.hotkey_vk = vk
            return True
        return False

    def is_running(self) -> bool:
        return self.running

    def start(self, countdown_seconds: float = 0.0) -> None:
        if self.running:
            return

        def _delayed_start():
            if countdown_seconds > 0:
                self.on_log(f"Iniciando en {countdown_seconds:.1f} segundos...")
                time.sleep(countdown_seconds)
                if self._stop_event.is_set():
                    return

            if self.auto_focus_window and self.target_window_filter.strip():
                focused = focus_window_by_title(self.target_window_filter)
                if focused:
                    self.on_log(f"🎯 Ventana '{self.target_window_filter}' traída al frente.")
                    time.sleep(0.3)
                else:
                    self.on_log(f"⚠️ No se encontró la ventana objetivo: '{self.target_window_filter}'.")

            self.running = True
            self._stop_event.clear()
            now = time.time()

            for rule in self.rules:
                rule.compute_next_run(now)

            self._next_anti_afk_time = now + self.anti_afk_interval_sec

            self.on_state_change(True)
            self.on_log("▶ Automatización INICIADA")

            self._run_loop()

        self._stop_event.clear()
        self._worker_thread = threading.Thread(target=_delayed_start, daemon=True)
        self._worker_thread.start()

    def stop(self) -> None:
        if not self.running and (not self._worker_thread or not self._worker_thread.is_alive()):
            return
        self.running = False
        self._stop_event.set()
        self.on_state_change(False)
        self.on_log("⏹ Automatización DETENIDA")

    def toggle(self) -> None:
        if self.running:
            self.stop()
        else:
            self.start(countdown_seconds=0.0)

    def _start_hotkey_listener(self) -> None:
        """Hilo de escucha de atajo global (F12, etc.) sin bloquear."""
        def _listener():
            was_pressed = False
            while self._hotkey_listening:
                try:
                    pressed = is_key_pressed_globally(self.hotkey_vk)
                    if pressed and not was_pressed:
                        self.toggle()
                    was_pressed = pressed
                except Exception:
                    pass
                time.sleep(0.05)

        self._hotkey_thread = threading.Thread(target=_listener, daemon=True)
        self._hotkey_thread.start()

    def _is_target_active(self) -> bool:
        """Verifica si la ventana activa coincide con el filtro establecido."""
        if not self.target_window_filter.strip():
            return True
        active_title = get_active_window_title()
        return self.target_window_filter.strip().lower() in active_title.lower()

    def _perform_anti_afk_dance(self) -> None:
        """Gira el personaje (Ctrl + Flechas) para evitar ser desconectado por inactividad."""
        self.on_log("🛡️ Anti-AFK: Ejecutando rotación de personaje (Auto-Dancer)...")
        dance_moves = ["ctrl+up", "ctrl+right", "ctrl+down", "ctrl+left"]
        for move in dance_moves:
            send_combo(move)
            time.sleep(0.12)

    def _run_loop(self) -> None:
        """Bucle principal con control de teclas periódicas, pixel triggers y anti-afk."""
        while self.running and not self._stop_event.is_set():
            now = time.time()
            target_active = self._is_target_active()

            if target_active:
                # 1. Verificar Pixel Triggers (Auto-Healer / Auto-Mana)
                for pt in self.pixel_triggers:
                    if not pt.enabled:
                        continue
                    if (now - pt.last_triggered) >= pt.cooldown:
                        current_color = get_pixel_color(pt.x, pt.y)
                        # Si el color ya no coincide con la barra llena -> Se ha consumido vida/mana!
                        if not is_color_similar(current_color, pt.expected_color, tolerance=40):
                            success = send_action(pt.trigger_action)
                            pt.last_triggered = now
                            if success:
                                self.on_log(f"🩸 [{pt.name}] Activado! Tecla: {pt.trigger_action.upper()}")

                # 2. Verificar Teclas y Secuencias programadas
                for rule in self.rules:
                    if not rule.enabled:
                        continue

                    if now >= rule.next_run_time:
                        success = send_action(rule.key)
                        if success:
                            self.on_log(f"[{time.strftime('%H:%M:%S')}] Pulsada: {rule.key.upper()}")
                        else:
                            self.on_log(f"[{time.strftime('%H:%M:%S')}] Error con tecla: {rule.key.upper()}")
                        rule.compute_next_run(now)

                # 3. Verificar Anti-AFK Dancer
                if self.anti_afk_enabled and now >= self._next_anti_afk_time:
                    self._perform_anti_afk_dance()
                    self._next_anti_afk_time = now + self.anti_afk_interval_sec

            # Pequeña pausa para no saturar la CPU
            time.sleep(0.015)

    def shutdown(self) -> None:
        self.stop()
        self._hotkey_listening = False
