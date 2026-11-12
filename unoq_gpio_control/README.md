# UNO Q GPIO Control + Matriz LED

Sistema cliente-servidor para control remoto de la placa **Arduino UNO Q** (STM32U585 + Zephyr RTOS). Permite controlar **GPIO digital**, **entradas analógicas (ADC 12-bit)**, **salidas PWM**, la **matriz LED 12x8 integrada**, los **LEDs de la placa** y **monitoreo de temperatura del chip**, todo desde scripts Python en tu PC.

---

## Tabla de Contenidos

- [Placa y Especificaciones](#placa-y-especificaciones)
- [Principio de Funcionamiento](#principio-de-funcionamiento)
- [Forma de Operar](#forma-de-operar)
- [Tabla de Pines (Pinout)](#tabla-de-pines-pinout)
- [Diagrama de Conexión](#diagrama-de-conexión)
- [Instrucciones de Compilación y Carga](#instrucciones-de-compilación-y-carga)
- [Los 3 Scripts — Comparativa](#los-3-scripts--comparativa)
- [unoq_remote.py — Menú Remoto Unificado](#unoq_remotepy--menú-remoto-unificado)
- [Temperatura del Chip (Opción 5)](#temperatura-del-chip-opción-5)
- [Auto-Detección de Puerto](#auto-detección-de-puerto)
- [Protocolo de Comandos](#protocolo-de-comandos)
- [Comandos MATRIX (control de la matriz LED 12x8)](#comandos-matrix-control-de-la-matriz-led-12x8)
- [Ejemplos de Uso](#ejemplos-de-uso)
- [Calibración](#calibración)
- [Advertencias Específicas UNO Q](#advertencias-específicas-uno-q)
- [Solución de Problemas](#solución-de-problemas)
- [Estructura del Proyecto](#estructura-del-proyecto)

---

## Placa y Especificaciones

| Característica | Detalle |
|---|---|
| **Placa** | Arduino UNO Q |
| **Microcontrolador** | STM32U585QII6 (ARM Cortex-M33 con TrustZone) |
| **RTOS** | Zephyr RTOS |
| **Frecuencia de reloj** | 160 MHz |
| **RAM** | 262,144 bytes (262 KB) |
| **Flash** | 2,097,152 bytes (2 MB) |
| **Voltaje de operación** | 3.3V (lógica y GPIO) |
| **Voltaje de alimentación** | 5V vía USB-C |
| **ADC** | 12 bits (0–4095) en pines A0–A5 |
| **PWM** | 8 bits (0–255) en pines 3, 5, 6, 9, 10, 11 |
| **Matriz LED** | 12x8 píxeles integrada de fábrica |
| **FQBN** | `arduino:zephyr:unoq` |
| **Core Arduino** | `arduino:zephyr` |
| **Puerto Serial** | `/dev/ttyACM0` (USB CDC ACM) |
| **Baud Rate** | 115200 bps |
| **Upload** | ADB + OpenOCD vía SWD |
| **USB ID** | `2341:0078` |

---

## Principio de Funcionamiento

El proyecto implementa una arquitectura **cliente-servidor** sobre comunicación Serial USB:

```
┌───────────────────┐        Serial USB (115200 baud)        ┌──────────────────────────┐
│                   │  ──────── READ 13 ───────────────────►  │                          │
│   Script Python   │                                        │   Arduino UNO Q          │
│   (cliente)       │  ◄──────── OK 1 ─────────────────────  │   (servidor)             │
│                   │                                        │                          │
│   Modos:          │  ──────── MATRIX TINYSCROLL Hola ────►  │   STM32U585              │
│   - comando único │                                        │   Zephyr RTOS            │
│   - interactivo   │  ◄──────── OK TINYSCROLL ─────────────  │                          │
│   - menú remoto   │                                        │   Controla:              │
│                   │  ──────── MATRIX SPEED 80 ────────────►  │   - GPIO (0-19)         │
│   /dev/ttyACM0    │                                        │   - ADC (A0-A5)          │
│                   │  ◄──────── OK SPEED: 80ms ────────────  │   - PWM (3,5,6,9,10,11)  │
│                   │                                        │   - Matriz LED 12x8      │
└───────────────────┘                                        └──────────────────────────┘
```

1. **Arranque**: El sketch inicializa `Serial` a 115200 baud, configura todos los pines (0–19) como `INPUT` (estado seguro de alta impedancia), inicializa los pines PWM como `OUTPUT`, configura la matriz LED y envía `UNOQ_GPIO_READY`.

2. **Servidor de comandos**: En `loop()`, el sketch espera líneas de texto por Serial. Cada línea se parsea: primero se verifica si es un comando `MATRIX` (procesado en una rama especial); si no, se parsea como comando GPIO (`READ`, `WRITE`, `ANALOG`, `PWM`). Se ejecuta la acción y se responde por Serial.

3. **Cliente Python**: El script abre el puerto Serial, espera `UNOQ_GPIO_READY`, y envía comandos. Soporta tres modos en dos scripts:
   - **Modo comando único** (`unoq_gpio_control.py`): ejecuta un comando y sale.
   - **Modo interactivo (REPL)** (`unoq_gpio_control.py -i`): sesión persistente con menú de 6 opciones.
   - **Modo menú remoto** (`unoq_remote.py`): interfaz de menú navegable con 4 categorías.

4. **Matriz LED**: Controlada mediante la librería `Arduino_LED_Matrix` (diseñada para UNO Q/Zephyr). El canvas es de 13x8 (13 columnas x 8 filas). Soporta **dos modos de texto**:
   - **Fuente grande (5×7)**: Scroll horizontal con `Font_5x7`, ocupa 7 de 8 filas.
   - **Fuente chica (3×4)**: Dos líneas simultáneas (`TINY`) o marquesina centrada (`TINYSCROLL`), con fuente personalizada de 3×4 píxeles.

---

## Forma de Operar

### Requisitos previos

- Placa Arduino UNO Q con el firmware `unoq_gpio_control.ino` cargado
- Cable USB-C conectado al host
- Python 3.6+ con `pyserial`:
  ```bash
  pip install pyserial
  ```
- Regla udev configurada (USB ID `2341:0078`)
- Para LEDs integrados (`unoq_remote.py` opción 3): `adb` (Android Debug Bridge) funcional
- Librerías Arduino instaladas: `Arduino_LED_Matrix` y `ArduinoGraphics` (incluidas en el core `arduino:zephyr`)

### Flujo de trabajo típico

```bash
# 1. Verificar que la placa está visible
arduino-cli board list

# 2. Compilar y cargar el sketch
arduino-cli compile --fqbn arduino:zephyr:unoq .
arduino-cli upload -p /dev/ttyACM0 --fqbn arduino:zephyr:unoq .

# 3. Menú remoto unificado (RECOMENDADO para uso general)
python3 unoq_remote.py

# 4. Comandos rápidos vía línea de comandos
python3 unoq_gpio_control.py WRITE 13 1        # Encender LED en D13
python3 unoq_gpio_control.py READ 2            # Leer pulsador en D2
python3 unoq_gpio_control.py ANALOG A0         # Leer ADC 12-bit
python3 unoq_gpio_control.py PWM 9 128         # PWM al 50%
python3 unoq_gpio_control.py TEXTO "Hola"      # Marquesina fuente chica
python3 unoq_gpio_control.py TEXTO --tamano grande "Hola"  # Scroll fuente grande

# 5. Modo interactivo (REPL con submenús)
python3 unoq_gpio_control.py -i
```

---

## Tabla de Pines (Pinout)

### Pines GPIO expuestos al usuario (D0–D13, A0–A5)

| Pin UNO Q | Pin lógico | Modo inicial | Notación aceptada | PWM | ADC | Notas |
|---|---|---|---|---|---|---|
| D0 | 0 | INPUT | `0`, `D0` | No | No | RX USART1. Usar solo si no se usa `Serial1`. |
| D1 | 1 | INPUT | `1`, `D1` | No | No | TX USART1. Usar solo si no se usa `Serial1`. |
| D2 | 2 | INPUT | `2`, `D2` | No | No | GPIO propósito general |
| D3 | 3 | INPUT (PWM init) | `3`, `D3` | **Sí** | No | PWM 8-bit (0–255) |
| D4 | 4 | INPUT | `4`, `D4` | No | No | GPIO propósito general |
| D5 | 5 | INPUT (PWM init) | `5`, `D5` | **Sí** | No | PWM 8-bit (0–255) |
| D6 | 6 | INPUT (PWM init) | `6`, `D6` | **Sí** | No | PWM 8-bit (0–255) |
| D7 | 7 | INPUT | `7`, `D7` | No | No | GPIO propósito general |
| D8 | 8 | INPUT | `8`, `D8` | No | No | GPIO propósito general |
| D9 | 9 | INPUT (PWM init) | `9`, `D9` | **Sí** | No | PWM 8-bit (0–255) |
| D10 | 10 | INPUT (PWM init) | `10`, `D10` | **Sí** | No | PWM 8-bit (0–255) |
| D11 | 11 | INPUT (PWM init) | `11`, `D11` | **Sí** | No | PWM 8-bit (0–255) |
| D12 | 12 | INPUT | `12`, `D12` | No | No | GPIO propósito general |
| D13 | 13 | INPUT | `13`, `D13` | No | No | **Sin LED built-in** (a diferencia del Uno clásico) |
| A0 | 14 | INPUT | `14`, `A0`, `a0` | No | **Sí** | ADC 12-bit (0–4095), usable como digital |
| A1 | 15 | INPUT | `15`, `A1`, `a1` | No | **Sí** | ADC 12-bit (0–4095), usable como digital |
| A2 | 16 | INPUT | `16`, `A2`, `a2` | No | **Sí** | ADC 12-bit (0–4095), usable como digital |
| A3 | 17 | INPUT | `17`, `A3`, `a3` | No | **Sí** | ADC 12-bit (0–4095), usable como digital |
| A4 | 18 | INPUT | `18`, `A4`, `a4` | No | **Sí** | ADC 12-bit (0–4095), usable como digital, I2C SDA |
| A5 | 19 | INPUT | `19`, `A5`, `a5` | No | **Sí** | ADC 12-bit (0–4095), usable como digital, I2C SCL |

### Matriz LED (uso interno, gestionado automáticamente)

| Componente | Pin físico | Controlador | Notas |
|---|---|---|---|
| Matriz LED 12x8 | GPIOF 0 (puerto F del STM32U585) | Arduino_LED_Matrix (vía DTS) | Gestionado automáticamente por la librería. Sin conflicto con pines GPIO 0–19. |

### Sensores Internos (acceso vía Serial + ADB)

| Sensor | Canal/Lectura | Rango | Método | Notas |
|---|---|---|---|---|
| Temperatura del chip (sysfs) | `/sys/class/thermal/thermal_zone0/temp` | ~15–85°C | ADB (Linux embebido) | Preciso, no requiere sketch. Usado por `unoq_remote.py` opción 5 |
| Temperatura del chip (ADC) | ADC1 canal 19 | ~15–85°C | Comando `TEMP` vía Serial | Experimental. Usa calibración de fábrica TS_CAL1/TS_CAL2. Puede no funcionar en todas las builds de Zephyr |

---

## Diagrama de Conexión

La UNO Q se conecta al PC mediante un **único cable USB-C** que proporciona alimentación (5V) y comunicación Serial (USB CDC ACM). No se requieren cables adicionales para la operación básica. La matriz LED y los LEDs integrados son onboard.

### Conexión Serial (única conexión requerida)

```
┌──────────────────┐                         ┌──────────────────────┐
│                  │                         │                      │
│     TU PC        │    Cable USB-C          │   Arduino UNO Q      │
│                  │◄═══════════════════════►│                      │
│   /dev/ttyACM0   │    (datos + poder)      │   Puerto USB-C       │
│                  │                         │                      │
└──────────────────┘                         └──────────────────────┘
```

La placa se identifica en el PC como:
- **Puerto Serial**: `/dev/ttyACM0` (Linux), `COM3` (Windows), `/dev/tty.usbmodem*` (macOS)
- **ADB**: `adb devices` → `2480682956  device`
- **USB ID**: `2341:0078`

### Ejemplo: Conexión de un LED externo en D13 y un pulsador en D2

```
                    Arduino UNO Q (vista superior)
         ┌──────────────────────────────────────────────────────┐
         │                                                      │
         │   D13 ●────[R 220Ω]─────► LED (ánodo) ──── GND      │
         │               (LED externo opcional)                 │
         │                                                      │
         │   D2  ●────┬─────────────► Pulsador ──── GND        │
         │            │                                         │
         │            └─[R 10kΩ]──── 3.3V (pull-up)            │
         │                                                      │
         │   GND ●─────────────┘                                │
         │                                                      │
         │   3.3V ●──────┘                                      │
         │                                                      │
         │   Matriz LED 12x8 (integrada, onboard)               │
         │   ┌──────────────────────────────────────┐          │
         │   │ ● ● ● ● ● ● ● ● ● ● ● ●             │          │
         │   │ ● ● ● ● ● ● ● ● ● ● ● ●             │          │
         │   │  ... (12 cols x 8 rows) ...           │          │
         │   └──────────────────────────────────────┘          │
         │                                                      │
         │   Puerto USB-C ────► Cable USB-C ────► PC           │
         │                                                      │
         └──────────────────────────────────────────────────────┘
```

| Componente | Pin UNO Q | Conexión | Notas |
|---|---|---|---|
| LED externo (ánodo) | D13 | A través de resistor 220Ω | Cátodo a GND. La UNO Q **NO** tiene LED built-in en D13 |
| Resistor LED | — | 220Ω en serie con el LED | Limita corriente a ~15 mA a 3.3V |
| Pulsador | D2 | Entre D2 y GND | Normalmente abierto |
| Resistor pull-up | — | 10kΩ entre D2 y 3.3V | Mantiene D2 en HIGH con pulsador suelto |
| Matriz LED 12x8 | Interna | Controlada por librería | No requiere cableado externo |
| Alimentación | USB-C | Cable único al PC | 5V del USB regulado a 3.3V onboard |

### Ejemplo: Conexión de sensor analógico (potenciómetro) en A0

```
         A0 ●─────────────────────── Potenciómetro (cursor)
                                     │
         3.3V ●─── Potenciómetro (extremo 1)
                                     │
         GND ●──── Potenciómetro (extremo 2)
```

Lectura desde el script:
```bash
python3 unoq_gpio_control.py ANALOG A0
# → [UNOQ] OK 2048    (potenciómetro a la mitad: ~1.65V)
```

---

## Instrucciones de Compilación y Carga

### Verificar placa conectada

```bash
arduino-cli board list
```

Debe mostrar:
```
Port         Protocol Type              Board Name      FQBN                Core
/dev/ttyACM0 serial   Serial Port (USB) Arduino UNO Q   arduino:zephyr:unoq arduino:zephyr
```

### Instalar el core (si no está instalado)

```bash
arduino-cli core update-index
arduino-cli core install arduino:zephyr
```

### Compilar el sketch

```bash
arduino-cli compile --fqbn arduino:zephyr:unoq .
```

Salida esperada:
```
Sketch uses 74940 bytes (3%) of program storage space. Maximum is 2097152 bytes.
Global variables use 26964 bytes (10%) of dynamic memory.
```

### Transferir a la placa

```bash
arduino-cli upload -p /dev/ttyACM0 --fqbn arduino:zephyr:unoq .
```

Si requiere número de serie:
```bash
# Obtener serial
adb devices
# → 2480682956   device

arduino-cli upload -p /dev/ttyACM0 --fqbn arduino:zephyr:unoq \
    --upload-property upload.port.properties.serialNumber=2480682956 .
```

### Monitor Serial

```bash
arduino-cli monitor -p /dev/ttyACM0 --config baudrate=115200
```

Al abrir el monitor debe aparecer:
```
UNOQ_GPIO_READY
```

### Nota sobre permisos

Si `arduino-cli upload` o el monitor Serial reportan error de permisos, verifica las reglas udev:

```bash
cat /etc/udev/rules.d/99-arduino-unoq.rules
```

Debe existir una regla para USB ID `2341:0078`. Si no, créala:

```bash
echo 'SUBSYSTEM=="tty", ATTRS{idVendor}=="2341", ATTRS{idProduct}=="0078", MODE="0666", SYMLINK+="ttyACM_UNOQ"' | sudo tee /etc/udev/rules.d/99-arduino-unoq.rules
sudo udevadm control --reload-rules
sudo udevadm trigger
```

Desconecta y vuelve a conectar la placa.

---

## Los 3 Scripts — Comparativa

El proyecto incluye **3 scripts Python** con diferentes interfaces y propósitos. Aquí te ayudamos a elegir cuál usar:

| Característica | `unoq_gpio_control.py` (línea de comandos) | `unoq_gpio_control.py -i` (interactivo) | `unoq_remote.py` (menú remoto) |
|---|---|---|---|
| **Propósito** | Comandos rápidos, scripting, automatización | Exploración y depuración | Control completo con GUI de texto |
| **Interfaz** | `python3 script.py COMANDO ARGS` | Submenú de 6 opciones + REPL | Menú principal de 4 opciones con submenús |
| **Curva de aprendizaje** | Alta (memorizar comandos) | Media | **Baja** — ideal para primer uso |
| **GPIO digital** | ✅ READ/WRITE | ✅ Opción 2 del menú | ✅ Opción 1 (leer/escribir guiado) |
| **Analógico** | ✅ ANALOG/PWM | ✅ Opciones 3 y 4 | ✅ Opción 2 (con barras visuales) |
| **Matriz LED** | ✅ Todos los comandos MATRIX | ✅ Opciones 1 y 5 | ✅ Opción 4 (asistente guiado) |
| **TEXTO (fuente chica)** | ✅ `TEXTO "hola"` con flags | ✅ Opción 1 con prompts | ✅ Opción 4 (elige tamaño y velocidad) |
| **LEDs integrados** | ❌ No | ❌ No | ✅ Opción 3 (vía ADB, parpadeo) |
| **Temperatura chip** | ❌ No | ❌ No | ✅ Opción 5 (sysfs + fallback Serial) |
| **Auto-detección puerto** | ❌ No | ❌ No | ✅ Busca /dev/ttyACM* automáticamente |
| **Barras visuales** | ❌ No | ❌ No | ✅ Voltaje + duty cycle + temperatura |
| **Scripting/pipe** | ✅ Fácil (`$(python3 ...)`) | ❌ No | ❌ No |
| **Requiere ADB** | ❌ No | ❌ No | ✅ Solo para opción 3 (LEDs) y opción 5 (sysfs) |
| **Mejor para** | Automatización, CI/CD, scripts bash | Desarrolladores explorando el protocolo | **Usuarios finales**, demos, aprendizaje |

### ¿Cuál usar?

- **"Quiero encender un LED desde un script bash"** → `unoq_gpio_control.py WRITE 13 1`
- **"Quiero explorar todos los comandos disponibles"** → `unoq_gpio_control.py -i`
- **"Quiero una interfaz amigable sin memorizar comandos"** → `unoq_remote.py`

---

## unoq_remote.py — Menú Remoto Unificado

`unoq_remote.py` es la interfaz **más amigable** del proyecto. Presenta un menú navegable con 4 categorías y submenús guiados paso a paso.

### Pantalla principal

```
  ╔══════════════════════════════════════════════════╗
  ║            UNO Q — CONTROL REMOTO               ║
  ╚══════════════════════════════════════════════════╝

  1. Digital          (D0-D13: leer/escribir)
  2. Analógico        (A0-A5: ADC / PWM)
  3. LEDs integrados  (verde, rojo, azul de la placa)
  4. Texto en matriz  (marquesina en display LED)
  5. Temperatura      (sensor interno del chip)
  0. Salir

  Opción >
```

### Opción 1 — Digital (leer/escribir pines D0–D13)

```
  ╔══════════════════════════════════════════════════╗
  ║              CONTROL DIGITAL                     ║
  ╚══════════════════════════════════════════════════╝

  1. Leer pin
  2. Escribir pin
  0. Volver

  Opción >
```

**Leer pin**: Pregunta el número de pin (0–13), ejecuta `READ <pin>`, y muestra `HIGH (1)` o `LOW (0)`.

**Escribir pin**: Pregunta pin + valor (0=LOW, 1=HIGH), ejecuta `WRITE <pin> <valor>`, y confirma.

### Opción 2 — Analógico (ADC con barra de voltaje + PWM con barra de duty cycle)

```
  ╔══════════════════════════════════════════════════╗
  ║            CONTROL ANALÓGICO                     ║
  ╚══════════════════════════════════════════════════╝

  1. Leer ADC (entrada analógica)
  2. Escribir PWM (salida analógica)
  0. Volver
```

**Leer ADC**: Elige A0–A5, muestra valor (0–4095), voltaje calculado (0–3.3V) y **barra visual**:

```
  → Pin A0: 2048 / 4095
  → Voltaje: 1.65V
  → [███████████████                 ]
```

**Escribir PWM**: Elige pin (3,5,6,9,10,11) + duty cycle (0–255), muestra porcentaje y barra:

```
  → Pin D9: 128/255 (50%)
  → [███████████████                 ]
```

### Opción 3 — LEDs integrados (control vía ADB de los 6 LEDs de la placa)

Controla directamente los **6 LEDs físicos** de la UNO Q a través del Linux interno (ADB → sysfs). Muestra estado actual con iconos:

```
  ╔══════════════════════════════════════════════════╗
  ║          LEDS INTEGRADOS DE LA PLACA             ║
  ╚══════════════════════════════════════════════════╝

  Estos LEDs se controlan directamente vía Linux (ADB).

  1. 🟢  Verde usuario
  2. ⚫  Rojo usuario
  3. ⚫  Azul usuario
  4. 🟢  Verde WiFi
  5. ⚫  Rojo panic
  6. ⚫  Azul Bluetooth

  ──────────────────────────────────
  E. Encender todos
  A. Apagar todos
  0. Volver
```

Para cada LED individual:
```
  ╔══════════════════════════════════════════════════╗
  ║          CONTROL: Verde usuario                  ║
  ╚══════════════════════════════════════════════════╝

  Estado actual: ⚫ APAGADO

  1. Encender
  2. Apagar
  3. Parpadear (5 veces)
  0. Volver
```

### Opción 4 — Texto en matriz (NUEVO: asistente guiado)

**Asistente interactivo** que te guía para mostrar texto en la matriz LED 12×8 sin necesidad de conocer los comandos. Flujo paso a paso:

```
  ╔══════════════════════════════════════════════════╗
  ║            TEXTO EN MATRIZ LED                   ║
  ╚══════════════════════════════════════════════════╝

  Muestra texto deslizante en la matriz 12x8 de la UNO Q.

  Tamaño de fuente:
    1. Chica (3×4)  — centrada, con márgenes
    2. Grande (5×7) — ocupa toda la altura

  Opción [1-2] (default: 1) >
```

**Paso 1 — Elegir tamaño de fuente:**
- **Opción 1 — Chica (3×4)**: Fuente personalizada de 4 filas de alto, centrada verticalmente con márgenes de 2 píxeles arriba y abajo. Ideal para texto largo y legible. Usa `MATRIX TINYSCROLL`.
- **Opción 2 — Grande (5×7)**: Fuente estándar `Font_5x7` que ocupa 7 de las 8 filas. Texto grande e impactante. Usa `MATRIX <texto>` (scroll horizontal completo).

**Paso 2 — Velocidad (solo para fuente chica):**
```
  Velocidad [10-500 ms] (default: 70) >
```
Controla qué tan rápido se desplaza el texto. 10ms = muy rápido, 500ms = muy lento. Usa `MATRIX SPEED <ms>` internamente.

**Paso 3 — Texto:**
```
  Texto a mostrar: Hola UNO Q!
```
Escribe el texto que quieres ver en la matriz. Acepta espacios, números y letras (ASCII 32–95).

**Resultado:**
```
  → Mostrando: "Hola UNO Q!" | fuente=tiny | 70ms
  → OK TINYSCROLL
```

El texto aparece deslizándose de derecha a izquierda en la matriz LED.

### Opción 5 — Temperatura del chip (NUEVO v3.2)

Lee el sensor interno de temperatura del **STM32U585** usando dos métodos en cascada:

1. **Vía Linux sysfs (ADB)** — preferido: lee `/sys/class/thermal/thermal_zone0/temp` directamente del Linux embebido de la placa. Muestra temperatura con **barra visual** y advertencias contextuales.
2. **Fallback Serial (comando TEMP)** — si ADB no está disponible, envía el comando `TEMP` al sketch, que usa el ADC interno del STM32U585 (canal 19) con calibración de fábrica.

```
  ╔══════════════════════════════════════════════════╗
  ║          TEMPERATURA DEL CHIP                   ║
  ╚══════════════════════════════════════════════════╝

  Leyendo sensor interno del STM32U585...

  🌡️  Temperatura: 38.2 °C
  [████████████████████                ]
  ✅ Temperatura normal
```

**Niveles de advertencia**:
- **≤ 40°C** → ✅ Temperatura normal
- **41–55°C** → ⚡ Temperatura elevada
- **> 55°C** → ⚠️ ¡Caliente! El chip está a XX°C

### Auto-Detección de Puerto (NUEVO v3.2)

`unoq_remote.py` ahora busca automáticamente la UNO Q en **cualquier** `/dev/ttyACM*`, eliminando el problema de que la placa aparezca en `ttyACM1`, `ttyACM2`, etc.

```python
def _detectar_puerto():
    import glob
    for p in glob.glob("/dev/ttyACM*"):
        try:
            s = serial.Serial(p, BAUD, timeout=1)
            s.close()
            return p
        except:
            pass
    return "/dev/ttyACM0"  # fallback
```

Al conectar, muestra el puerto detectado:
```
  Conectado a /dev/ttyACM1
```

Ya no es necesario editar la variable `PORT` manualmente.

### Ejemplo completo de sesión con unoq_remote.py

```
$ python3 unoq_remote.py

  Conectado a la UNO Q. Cargando...

  ╔══════════════════════════════════════════════════╗
  ║            UNO Q — CONTROL REMOTO               ║
  ╚══════════════════════════════════════════════════╝

  1. Digital          (D0-D13: leer/escribir)
  2. Analógico        (A0-A5: ADC / PWM)
  3. LEDs integrados  (verde, rojo, azul de la placa)
  4. Texto en matriz  (marquesina en display LED)
  0. Salir

  Opción > 4                                     ← Elige "Texto en matriz"

  Tamaño de fuente:
    1. Chica (3×4)  — centrada, con márgenes
    2. Grande (5×7) — ocupa toda la altura

  Opción [1-2] (default: 1) > 1                  ← Chica

  Velocidad [10-500 ms] (default: 70) > 50        ← Rápido (50ms)

  Texto a mostrar: Arduino UNO Q ROCKS!           ← El texto

  → Mostrando: "Arduino UNO Q ROCKS!" | fuente=tiny | 50ms
  → OK TINYSCROLL

  Presiona ENTER para continuar...               ← Vuelve al menú principal
```

---

## Protocolo de Comandos

Todos los comandos viajan por Serial USB a 115200 baud, delimitados por `\n`. Son **case-insensitive** para el tipo de comando (`READ`, `read`, `Read` son equivalentes). Las líneas vacías se ignoran.

### Comandos GPIO

| Comando | Formato | Acción | Pines válidos | Respuesta |
|---|---|---|---|---|
| `READ` | `READ <pin>` | `digitalRead(pin)` | 0–19 | `OK 0` o `OK 1` |
| `WRITE` | `WRITE <pin> <0\|1>` | `pinMode(OUTPUT)` + `digitalWrite()` | 0–19 | `OK 0` o `OK 1` |
| `ANALOG` | `ANALOG <pin>` | `analogRead(pin)` — ADC 12-bit | 14–19 (A0–A5) | `OK <0-4095>` |
| `PWM` | `PWM <pin> <0-255>` | `analogWrite(pin, valor)` | 3, 5, 6, 9, 10, 11 | `OK <0-255>` |
| `TEMP` | `TEMP` | Lee temperatura interna del chip (experimental) | N/A (ADC interno canal 19) | `OK XX.X C (YYYY raw)` |

### Comandos MATRIX

| Comando | Acción | ¿Bloqueante? | Respuesta |
|---|---|---|---|
| `MATRIX CLEAR` | Apaga todos los LEDs y borra buffers | No | `OK CLEAR` |
| `MATRIX LINE1 <texto>` | Almacena texto en buffer de línea 1 | No | `OK LINE1: <texto>` |
| `MATRIX LINE2 <texto>` | Almacena texto en buffer de línea 2 | No | `OK LINE2: <texto>` |
| `MATRIX SHOW` | Muestra 2 líneas estáticas con fuente 3×4 (si hay texto en LINE1/LINE2) | No | `OK TINY` |
| `MATRIX TINY` | Muestra LINE1 y LINE2 simultáneamente con fuente 3×4 | No | `OK TINY` |
| `MATRIX TINYSCROLL <texto>` | Marquesina centrada con fuente 3×4 | **Sí** | `OK TINYSCROLL` |
| `MATRIX SPEED <ms>` | Configura velocidad de marquesina (10–500ms) | No | `OK SPEED: <ms>ms` |
| `MATRIX SPEED` | Consulta velocidad actual | No | `OK SPEED: <ms>ms` |
| `MATRIX <texto>` | Scroll inmediato con fuente grande 5×7 | **Sí** | `OK SCROLL` |

### Comando TEXTO (solo en unoq_gpio_control.py)

El comando `TEXTO` es una **capa de conveniencia** exclusiva del script Python (no es un comando Serial). Internamente traduce a comandos MATRIX:

| Comando Python | Traducción interna | Efecto |
|---|---|---|
| `TEXTO "hola"` | `MATRIX SPEED 70` → `MATRIX TINYSCROLL hola` | Marquesina fuente chica a 70ms |
| `TEXTO --tamano grande "hola"` | `MATRIX hola` | Scroll fuente grande |
| `TEXTO --velocidad 50 "hola"` | `MATRIX SPEED 50` → `MATRIX TINYSCROLL hola` | Marquesina chica a 50ms |
| `TEXTO --tamano grande --velocidad 100 "hola"` | `MATRIX hola` | Scroll grande (--velocidad ignorado) |

### Errores

| Condición | Respuesta |
|---|---|
| Comando no reconocido | `ERROR: comando no reconocido` |
| Pin fuera de rango (0–19) | `ERROR: pin invalido` |
| ANALOG en pin no analógico | `ERROR: pin no soporta lectura analogica` |
| PWM en pin sin PWM | `ERROR: pin no soporta PWM` |
| Valor PWM fuera de 0–255 | `ERROR: valor PWM debe ser 0-255` |
| MATRIX sin argumentos | `ERROR: MATRIX requiere subcomando (CLEAR, LINE1, LINE2, SHOW, o texto)` |
| TINYSCROLL sin texto | `ERROR: texto vacio para TINYSCROLL` |
| SPEED fuera de rango | `ERROR: velocidad 10-500 ms` |
| TEMP falla (experimental) | `ERROR: ADC no disponible`, `ERROR: lectura ADC` o `ERROR: config ADC` |

---

## Comandos MATRIX — Detalle Completo

### MATRIX CLEAR

Limpia la matriz LED y borra los buffers internos de `LINE1` y `LINE2`.

```bash
python3 unoq_gpio_control.py MATRIX CLEAR
# → [UNOQ] OK CLEAR
```

### MATRIX LINE1 / LINE2

Almacena texto para mostrarlo con `MATRIX SHOW` o `MATRIX TINY`. Longitud máxima: ~114 caracteres.

```bash
python3 unoq_gpio_control.py MATRIX LINE1 "Hola"
python3 unoq_gpio_control.py MATRIX LINE2 "Mundo"
```

### MATRIX SHOW / MATRIX TINY — Dos líneas simultáneas

Muestra las líneas 1 y 2 **simultáneamente** usando una fuente personalizada de **3×4 píxeles**. Línea 1 en las filas superiores (0–3), línea 2 en las inferiores (4–7). Si una línea está vacía, no se muestra.

```bash
python3 unoq_gpio_control.py MATRIX LINE1 "Temp:25C"
python3 unoq_gpio_control.py MATRIX LINE2 "Hum: 60%"
python3 unoq_gpio_control.py MATRIX SHOW
# → [UNOQ] OK TINY
# La matriz muestra ambas líneas estáticas simultáneamente.
```

**Características de la fuente 3×4:**
- 4 filas de alto × 3 columnas de ancho por carácter (+ 1px de espacio)
- Caracteres soportados: `0-9`, `A-Z`, `!`, `-`, `.`, `:`, `_`, espacio
- Mayúsculas automáticas (las minúsculas se convierten)
- Máximo ~3 caracteres por línea (13 columnas / 4px por carácter)
- La línea 1 usa filas 0-3, línea 2 usa filas 4-7 (sin solapamiento)

### MATRIX TINYSCROLL — Marquesina con fuente chica

Muestra texto con scroll horizontal usando la fuente 3×4, **centrado verticalmente** en la matriz (márgenes de 2 píxeles arriba y abajo). Ideal para mensajes más largos que no caben estáticos.

```bash
python3 unoq_gpio_control.py MATRIX SPEED 70
python3 unoq_gpio_control.py MATRIX TINYSCROLL "Arduino UNO Q"
# → [UNOQ] OK TINYSCROLL
```

**Ventajas sobre MATRIX grande:**
- Texto más pequeño pero más legible para frases largas
- Centrado vertical con márgenes (aspecto más pulido)
- Hasta 64 caracteres (buffer de 256 columnas)

### MATRIX SPEED — Velocidad de marquesina

Configura la velocidad en milisegundos por frame para `TINYSCROLL`. Rango: 10–500ms. Por defecto: 70ms.

```bash
python3 unoq_gpio_control.py MATRIX SPEED 100    # Lento
python3 unoq_gpio_control.py MATRIX SPEED 30     # Rápido
python3 unoq_gpio_control.py MATRIX SPEED        # Consultar velocidad actual
# → [UNOQ] OK SPEED: 30ms
```

### MATRIX <texto> — Scroll grande inmediato

Scroll horizontal con fuente `Font_5x7` (7 filas de alto). Ocupa casi toda la matriz.

```bash
python3 unoq_gpio_control.py MATRIX "Hello World!"
# → [UNOQ] OK SCROLL
```

---

## Ejemplos de Uso

### Ejemplo 1: GPIO — LED y pulsador

```bash
# Encender LED externo en D13
$ python3 unoq_gpio_control.py WRITE 13 1
[*] Conectando a /dev/ttyACM0 a 115200 baud...
[*] Placa detectada: UNOQ_GPIO_READY
[UNOQ] OK 1

# Leer pulsador en D2 (con pull-up: 1 = no presionado, 0 = presionado)
$ python3 unoq_gpio_control.py READ 2
[UNOQ] OK 1

# Apagar LED
$ python3 unoq_gpio_control.py WRITE 13 0
[UNOQ] OK 0
```

### Ejemplo 2: ADC — Lectura de potenciómetro

```bash
$ python3 unoq_gpio_control.py ANALOG A0
[UNOQ] OK 2048
# → 2048 / 4095 * 3.3V = ~1.65V (potenciómetro a la mitad)

$ python3 unoq_gpio_control.py ANALOG A0
[UNOQ] OK 4089
# → ~3.30V (giro completo)
```

### Ejemplo 3: PWM — Control de brillo LED

```bash
$ python3 unoq_gpio_control.py PWM 9 128    # 50% brillo
[UNOQ] OK 128

$ python3 unoq_gpio_control.py PWM 9 25     # 10% brillo
[UNOQ] OK 25

$ python3 unoq_gpio_control.py PWM 9 0      # Apagado
[UNOQ] OK 0
```

### Ejemplo 4: MATRIX — Dos líneas estáticas (fuente chica)

```bash
$ python3 unoq_gpio_control.py MATRIX LINE1 "T:25C"
[UNOQ] OK LINE1: T:25C

$ python3 unoq_gpio_control.py MATRIX LINE2 "H:60%"
[UNOQ] OK LINE2: H:60%

$ python3 unoq_gpio_control.py MATRIX SHOW
[UNOQ] OK TINY
# En la matriz: "T:25C" arriba, "H:60%" abajo (estáticas)
```

### Ejemplo 5: MATRIX — Marquesina rápida (fuente chica)

```bash
$ python3 unoq_gpio_control.py MATRIX SPEED 40
[UNOQ] OK SPEED: 40ms

$ python3 unoq_gpio_control.py MATRIX TINYSCROLL "Hola Arduino UNO Q!"
# El texto se desliza centrado a 40ms por frame
[UNOQ] OK TINYSCROLL
```

### Ejemplo 6: TEXTO — Comando amigable desde línea de comandos

```bash
# Marquesina chica (default)
$ python3 unoq_gpio_control.py TEXTO "Hola UNO Q"
[*] Conectando a /dev/ttyACM0 a 115200 baud...
[*] Placa detectada: UNOQ_GPIO_READY
[UNOQ] OK TINYSCROLL

# Marquesina chica con velocidad personalizada
$ python3 unoq_gpio_control.py TEXTO --velocidad 30 "Mensaje rápido!"

# Scroll grande
$ python3 unoq_gpio_control.py TEXTO --tamano grande "HOLA!"
[UNOQ] OK SCROLL
```

### Ejemplo 7: unoq_remote.py — Sesión completa

```
$ python3 unoq_remote.py

  Conectado a la UNO Q. Cargando...

  ╔══════════════════════════════════════════════════╗
  ║            UNO Q — CONTROL REMOTO               ║
  ╚══════════════════════════════════════════════════╝

  1. Digital          (D0-D13: leer/escribir)
  2. Analógico        (A0-A5: ADC / PWM)
  3. LEDs integrados  (verde, rojo, azul de la placa)
  4. Texto en matriz  (marquesina en display LED)
  0. Salir

  Opción > 4         ← Mostrar texto en la matriz
  Opción [1-2] > 1   ← Fuente chica
  Velocidad > 50      ← 50ms
  Texto: Hola!
  → OK TINYSCROLL    ← Texto aparece en la matriz
```

### Ejemplo 9: Temperatura del chip

```bash
# Vía unoq_remote.py (recomendado)
$ python3 unoq_remote.py
# → Opción 5 → Temperatura

# Vía comando directo TEMP (experimental)
$ python3 unoq_gpio_control.py TEMP
[*] Conectando a /dev/ttyACM0 a 115200 baud...
[*] Placa detectada: UNOQ_GPIO_READY
[UNOQ] OK 38.2 C (1892 raw)
```

### Ejemplo 10: Auto-detección de puerto

```bash
# La placa se reconectó en ttyACM1 — unoq_remote.py lo detecta automáticamente
$ python3 unoq_remote.py

  Conectado a /dev/ttyACM1

  Conectado a la UNO Q. Cargando...
  # ¡Sin errores! El script encontró la placa en ttyACM1.
```

### Ejemplo 11: Manejo de errores

```bash
# Pin fuera de rango
$ python3 unoq_gpio_control.py READ 20
[UNOQ] ERROR: pin invalido

# ANALOG en pin no analógico
$ python3 unoq_gpio_control.py ANALOG 13
[UNOQ] ERROR: pin no soporta lectura analogica

# PWM en pin sin PWM
$ python3 unoq_gpio_control.py PWM 2 128
[UNOQ] ERROR: pin no soporta PWM

# MATRIX sin argumentos
$ python3 unoq_gpio_control.py MATRIX
[UNOQ] ERROR: MATRIX requiere subcomando...

# TINYSCROLL sin texto
$ python3 unoq_gpio_control.py MATRIX TINYSCROLL
[UNOQ] ERROR: texto vacio para TINYSCROLL

# SPEED fuera de rango
$ python3 unoq_gpio_control.py MATRIX SPEED 600
[UNOQ] ERROR: velocidad 10-500 ms
```

---

## Calibración

### ADC (entradas analógicas — ANALOG)

El ADC de la UNO Q es de **12 bits** (0–4095):

```
voltaje = valor_adc × 3.3 / 4095.0
```

| Valor ADC | Voltaje aproximado |
|---|---|
| 0 | 0.00 V (GND) |
| 1024 | 0.825 V |
| 2048 | 1.65 V (mitad) |
| 3072 | 2.475 V |
| 4095 | 3.30 V (máximo) |

- **Precisión típica**: ±4 LSB (≈ 3.2 mV)
- **Pin flotante**: Valores de ruido (~50-200)

### PWM (salidas analógicas — PWM)

Resolución de **8 bits** (0–255):

```
duty_cycle_% = valor_pwm × 100 / 255
```

| Valor PWM | Duty cycle | Brillo LED equivalente |
|---|---|---|
| 0 | 0% | Apagado |
| 64 | ~25% | Bajo |
| 128 | ~50% | Medio |
| 191 | ~75% | Alto |
| 255 | 100% | Máximo |

---

## Advertencias Específicas UNO Q

### Voltaje de operación: 3.3V

La UNO Q opera a **3.3V** en todos sus pines GPIO. **NO conectes señales de 5V directamente** — usa **level shifters** al conectar periféricos de 5V. Alimenta sensores con el pin de **3.3V**, no 5V.

### ADC de 12 bits, no 10 bits

`analogRead()` retorna valores en **0–4095** (no 0–1023 como el Uno clásico). Ajusta cualquier cálculo de voltaje: `voltaje = valor × 3.3 / 4095.0`.

### Zephyr RTOS — Compatibilidad de librerías

- Las APIs estándar de Arduino **sí son compatibles**.
- Librerías que acceden a registros AVR (`PORTB`, `DDRB`, `ISR()`) **NO son compatibles**.
- `Arduino_LED_Matrix` v0.1.3 está diseñada específicamente para UNO Q sobre Zephyr.
- `delay()` en Zephyr duerme el thread (cede al scheduler), no es busy-wait.

### Upload vía ADB + OpenOCD

No usa bootloader tradicional. Usa **ADB** + **OpenOCD** para comunicarse con el debugger SWD. `arduino-cli upload` lo maneja automáticamente, pero requiere que `adb devices` muestre la placa.

### La UNO Q NO tiene LED built-in en D13

Conecta un LED externo con resistencia (220Ω). Los LEDs onboard se controlan desde el Linux interno vía sysfs.

### Operación bloqueante de TINYSCROLL y MATRIX <texto>

Los comandos de scroll son **bloqueantes**: durante el scroll no se procesan otros comandos. Los comandos enviados durante el scroll quedan encolados.

### Fuente 3×4 — Caracteres limitados

La fuente personalizada solo incluye: `0-9`, `A-Z`, `!`, `-`, `.`, `:`, `_`, espacio. Las minúsculas se convierten a mayúsculas automáticamente.

---

## Solución de Problemas

| Problema | Causa probable | Solución |
|---|---|---|
| `arduino-cli board list` no muestra la placa | Cable defectuoso/solo carga, falta regla udev | Usar cable de datos, verificar regla udev |
| `arduino-cli upload` falla con timeout | ADB no detecta la placa | Verificar `adb devices`, resetear placa |
| `arduino-cli upload` error de permisos | Regla udev faltante | Crear regla para USB ID `2341:0078` |
| Script: "No se pudo abrir el puerto" | Puerto ocupado/permisos | Cerrar Serial Monitor, verificar `board list` |
| No se recibe `UNOQ_GPIO_READY` | Baud rate incorrecto, sketch no cargado | Verificar 115200 baud, recargar sketch |
| `ERROR: comando no reconocido` | Formato incorrecto | `READ 13`, `WRITE 13 1`, `MATRIX CLEAR` |
| `ERROR: pin invalido` | Pin fuera de rango | Usar 0–19 o A0–A5 |
| LED externo no enciende | LED al revés, resistor incorrecto | Ánodo al pin, cátodo a GND, 220Ω |
| `ANALOG` devuelve ruido | Pin flotante | Conectar sensor o potenciómetro |
| `TINYSCROLL` no muestra nada | Texto vacío o caracteres no soportados | Usar ASCII imprimible (A-Z, 0-9) |
| `MATRIX SHOW` muestra caracteres raros | Caracteres fuera del set 3×4 | Solo A-Z, 0-9, !, -, ., :, _ |
| `unoq_remote.py` opción 3 no funciona | ADB no instalado o placa no detectada | `sudo apt install adb`, verificar `adb devices` |
| `unoq_remote.py` opción 5 no funciona | ADB no disponible, TEMP no implementado en sketch | Instalar ADB, recargar sketch con soporte TEMP |
| `TEMP` vía Serial retorna error | Zephyr build sin soporte ADC interno | Usar opción 5 de `unoq_remote.py` (vía sysfs), o verificar build de Zephyr |
| `_detectar_puerto()` no encuentra la placa | Placa no conectada o regla udev faltante | Verificar `arduino-cli board list`, crear regla udev para `2341:0078` |
| Placa se calienta excesivamente | Cortocircuito, consumo excesivo | Verificar conexiones, no exceder 20 mA por pin, monitorear temp con opción 5 |

---

## Estructura del Proyecto

```
unoq_gpio_control/
├── unoq_gpio_control.ino    # Sketch Arduino — servidor de comandos GPIO + MATRIX
├── unoq_gpio_control.py     # Cliente Python — comandos Serial (modo único + interactivo)
├── unoq_remote.py           # Menú interactivo unificado (digital, analógico, LEDs, matriz)
├── README.md                # Documentación principal (este archivo)
├── BITACORA.md              # Bitácora completa del desarrollo
├── PLAN.md                  # Plan de implementación
├── AUDIT_REPORT.md          # Informe de auditoría
├── .gitignore               # Exclusiones de Git
└── docs/
    ├── datasheet.md         # Documentación de usuario detallada
    └── developer.md         # Documentación para desarrolladores
```

---

## Licencia

Este proyecto es de uso libre para fines educativos y de prototipado.
