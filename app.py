"""
Punto de entrada principal para la aplicación Auto Key Presser.
Ejecución: python app.py
"""

import sys
import tkinter as tk
from gui import AutoKeyApp

def main():
    root = tk.Tk()
    # Centrar la ventana en la pantalla
    root.update_idletasks()
    width = 680
    height = 720
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = max(0, (screen_width - width) // 2)
    y = max(0, (screen_height - height) // 2)
    root.geometry(f"{width}x{height}+{x}+{y}")

    app = AutoKeyApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()

