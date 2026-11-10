# 🎮 Auto Key Presser - Suite Completa

Herramienta avanzada de automatización de teclado y macros para Windows, diseñada especialmente para **Tibia**, juegos DirectX y **navegadores web** (Chrome, Edge, Firefox, Brave, etc.).

---

## 🚀 Novedades y Todas las Funciones Incluidas

### 1. 🌐 Selección Específica de Ventana / Navegador
- **Selector Inteligente de Ventanas Abiertas:** Pulsa el botón **`🔄 Detectar Ventanas`** para listar todas las pestañas de navegadores y ventanas abiertas en tu PC.
- **Enfoque Automático (Auto-Focus):** Puedes activar la casilla para que el programa traiga automáticamente tu navegador o juego al frente al iniciar.
- **Botón `🎯 Probar Foco`:** Verifica al instante si el programa localiza y activa tu ventana elegida.
- **Pausa Inteligente:** Si cambias de ventana (ej: a Discord o WhatsApp), el bot detiene las pulsaciones para no interferir en tus conversaciones.

### 2. ⌨️ Teclas, Combinaciones y Secuencias (Combos)
- **Teclas Individuales:** `F1` a `F12`, números `0-9`, letras `A-Z`, `Espacio`, `Enter`, etc.
- **Combinaciones con Modificadores:** `ctrl+up`, `ctrl+down`, `shift+f1`, `alt+1`.
- **Secuencias / Rotaciones encadenadas:** Puedes escribir varias teclas separadas por comas (ej: `f1, 1, f2`). El programa las ejecutará en orden con una pequeña pausa entre cada una.
- **Intervalos y Variación (Jitter):** Intervalo personalizado en segundos y variación aleatoria (ej: `±0.15s`) para que parezca una pulsación humana natural.

### 3. 🩸 Auto-Healer Inteligente por Detección de Píxel (Color Bot)
- **Lectura en Tiempo Real:** Utiliza la API nativa de Windows GDI (`GetPixel`) sin ralentizar tu PC.
- **Captura Fácil con F8:** Haz clic en **`📍 Capturar con F8`**, coloca el ratón sobre tu barra de Vida o Maná y presiona **F8**. El bot memorizará la coordenada y el color RGB exacto.
- **Disparo Automático:** En cuanto la barra cambie de color (porque tu vida o maná bajaron), el bot activa inmediatamente la tecla de curación o la poción configurada con tiempo de cooldown.

### 4. 🛡️ Modo Anti-AFK (Auto-Dancer)
- Evita la desconexión automática por inactividad tras 15 minutos en Tibia.
- Gira periódicamente el personaje en su misma casilla usando `Ctrl + Flechas` cada X minutos (configurable entre 1 y 14 minutos).

### 5. ⚙️ Ajustes y Usabilidad
- **Atajo Rápido Global:** Inicia o pausa todo pulsando **`F12`** directamente desde el juego o navegador.
- **Mantener Siempre Encima (Always on Top):** Fija la ventana del bot sobre las demás para supervisar la actividad mientras juegas o navegas.
- **Guardado y Perfiles:** Guarda todas tus teclas, triggers y ventanas en archivos `.json` para cambiarlos según tu personaje o necesidad.

---

## 🏃 Cómo Iniciar

1. **Doble clic:** Ejecuta el archivo [**`iniciar.bat`**](file:///d:/programacion/tibia/iniciar.bat).
2. **O desde la consola:**
   ```bash
   python app.py
   ```

> [!TIP]
> **Permisos de Administrador:** Si tu juego o navegador corre como Administrador, ejecuta `iniciar.bat` haciendo clic derecho y seleccionando **"Ejecutar como administrador"** para que Windows permita el envío de teclas entre ambas aplicaciones.
