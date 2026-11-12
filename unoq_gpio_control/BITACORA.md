# Bitácora del Proyecto — UNO Q GPIO Control

## Sesión: 8 de agosto de 2026

---

## 🎯 Objetivo original

Crear un sistema para controlar remotamente los pines GPIO de la placa **Arduino UNO Q** (STM32U585 + Zephyr RTOS) desde un **script Python** en la PC, vía comunicación Serial USB.

---

## 🧱 Fase 1 — Servidor de comandos GPIO (Arduino + Python)

### 1.1 Sketch Arduino — `unoq_gpio_control.ino`

Se creó un sketch que actúa como **servidor de comandos** escuchando por Serial a 115200 baud.

**Protocolo:**
```
READ <pin>         → lee estado digital          → "OK 0" / "OK 1"
WRITE <pin> <0|1>  → escribe estado digital       → "OK 0" / "OK 1"
Comando inválido   → "ERROR: comando no reconocido"
Pin fuera de rango → "ERROR: pin invalido"
```

**Pines disponibles:** 0–19 (D0–D13 físicos, A0–A5 mapeados como 14–19).  
**Notación aceptada:** numérica (`0`, `13`, `14`) y con prefijo A (`A0`, `A1`, ..., `A5`).

**Funciones implementadas:**
| Función | Descripción |
|---------|-------------|
| `setup()` | Inicializa Serial, todos los pines como INPUT, envía `UNOQ_GPIO_READY` |
| `loop()` | Lee línea, parsea comando, despacha READ/WRITE |
| `leerLinea()` | Lee buffer Serial con timeout de 1s (anti-bloqueo) |
| `parsearPin()` | Convierte `"13"` → 13, `"A0"` → 14, rechaza `"A"` solo |
| `ejecutarRead()` | `digitalRead(pin)` → `"OK 0"` / `"OK 1"` |
| `ejecutarWrite()` | `pinMode(OUTPUT)` + `digitalWrite()` + confirmación |
| `responder()` | Envía respuesta por Serial con `println()` |

**Compilación:**
```bash
arduino-cli compile --fqbn arduino:zephyr:unoq unoq_gpio_control/
```
```
Sketch uses 74940 bytes (9%) of program storage space.
Global variables use 26964 bytes (10%) of dynamic memory.
```

**Transferencia a la placa:**
```bash
arduino-cli upload --fqbn arduino:zephyr:unoq \
  -p /dev/ttyACM0 \
  --upload-property upload.port.properties.serialNumber=2480682956 \
  unoq_gpio_control/
```
Transferencia vía **OpenOCD + SWD** (ADB + GPIO bitbang). STM32U585 detectado correctamente, flash de 2048 KiB, programación dual-bank.

**Verificación en hardware:**
```
READ 13     → OK 0      (LOW inicial)
WRITE 13 1  → OK 1      (HIGH)
READ 13     → OK 1      (confirmado)
```

### 1.2 Script Python cliente — `unoq_gpio_control.py`

Cliente Python usando `pyserial` con dos modos:

**Modo comando único:**
```bash
python3 unoq_gpio_control.py READ 13
python3 unoq_gpio_control.py WRITE 13 1
```

**Modo interactivo (REPL):**
```bash
python3 unoq_gpio_control.py -i
unoq> READ 13
  → OK 1
unoq> quit
```

**Opciones de línea de comandos:**
| Flag | Descripción | Default |
|------|-------------|---------|
| `-p`, `--port` | Puerto serial | `/dev/ttyACM0` |
| `-b`, `--baud` | Baud rate | `115200` |
| `-t`, `--timeout` | Timeout lectura | `2.0` seg |
| `-i`, `--interactive` | Modo REPL | — |

### 1.3 Correcciones post-auditoría

La auditoría estática encontró 3 incidencias:

| ID | Severidad | Problema | Corrección |
|----|-----------|----------|------------|
| **I-001** | Media | `parsearPin("A")` mapeaba a pin 14 (A0) en vez de rechazarse | Mover validación `numStr.length()==0` antes del chequeo de rango |
| **I-002** | Media | `leerLinea()` hacía busy-waiting sin timeout | Timeout de 1s con `millis()`, reset en cada byte recibido |
| **I-003** | Baja | Uso de clase `String` con riesgo de fragmentación | Documentado — bajo impacto con 262 KB RAM |

Ambas correcciones (I-001, I-002) verificadas en hardware:
```
READ A   → ERROR: pin invalido     ✅
READ A0  → OK 0                    ✅
```

---

## 🧪 Fase 2 — Acceso al Linux interno de la UNO Q

### 2.1 Descubrimiento

La placa UNO Q no solo ejecuta Zephyr RTOS con el sketch Arduino — también corre un **Debian 13 (trixie)** completo accesible vía ADB:

```bash
adb shell
```
```
arduino@x11:~$ cat /etc/debian_version
13.2

arduino@x11:~$ free -h
              total   used   free   shared   buff/cache   available
Mem:          1.7Gi   468Mi  825Mi  40Mi     561Mi        1.2Gi
```

**Datos del Linux interno:**
| Dato | Valor |
|------|-------|
| Hostname | `x11` |
| Usuario | `arduino` |
| Sistema | Debian GNU/Linux 13 (trixie) |
| Kernel | Linux (arm64) |
| RAM | 1.7 GB |
| IP ZeroTier | `192.168.196.62` |
| WiFi | `wlan0` (configurable) |

### 2.2 Acceso SSH

**Método 1 — ADB Port Forwarding:**
```bash
adb forward tcp:2222 tcp:22
ssh -i ~/.ssh/unoq_key arduino@localhost -p 2222
```

**Método 2 — Directo por ZeroTier:**
```bash
ssh arduino@192.168.196.62
```

**Método 3 — WiFi local:**
```bash
adb shell
nmcli radio wifi on
nmcli device wifi connect "SSID" password "PASSWORD"
```

### 2.3 GPIOs desde Linux

La placa expone los GPIOs del STM32U585 al Linux vía `gpiod`:

```bash
gpiodetect
# gpiochip0 [PMIC] (10 líneas)
# gpiochip1 [500000.pinctrl] (127 líneas)
# gpiochip2 [a7c0000.pinctrl] (19 líneas)
```

**Comandos disponibles:**
```bash
gpioget -c gpiochip1 27         # Leer estado
gpioset -c gpiochip1 27=1       # Escribir HIGH (se mantiene hasta Ctrl+C)
gpioset -t0 -c gpiochip1 27=1   # Escribir y salir
gpioinfo                         # Ver todos los pines y sus consumidores
```

### 2.4 LEDs integrados via sysfs

Los LEDs físicos de la placa se controlan desde Linux:

```bash
ls /sys/class/leds/
# blue:bt  blue:user  green:user  green:wlan  mmc0::  red:panic  red:user

# Liberar LED del kernel
echo none > /sys/class/leds/green:user/trigger

# Encender
echo 255 > /sys/class/leds/green:user/brightness

# Apagar
echo 0 > /sys/class/leds/green:user/brightness
```

**LEDs disponibles:**
| Nombre | Color | Notas |
|--------|-------|-------|
| `green:user` | Verde | Usuario — ideal para pruebas |
| `red:user` | Rojo | Usuario |
| `blue:user` | Azul | Usuario |
| `green:wlan` | Verde | Actividad WiFi |
| `blue:bt` | Azul | Actividad Bluetooth |
| `red:panic` | Rojo | Kernel panic |

---

## ⚡ Fase 3 — Entradas analógicas y PWM

### 3.1 Extensión del sketch Arduino

Se agregaron dos nuevos comandos al protocolo Serial:

**ANALOG — Lectura ADC (12 bits, 0–4095):**
```
ANALOG <pin> → analogRead(pin) → "OK <0-4095>"
```

Pines válidos: A0–A5 (pines lógicos 14–19).  
Si el pin no es analógico → `ERROR: pin no soporta lectura analogica`.

**PWM — Salida analógica (0–255):**
```
PWM <pin> <0-255> → analogWrite(pin, valor) → "OK <valor>"
```

Pines válidos: 3, 5, 6, 9, 10, 11.  
Si el pin no soporta PWM → `ERROR: pin no soporta PWM`.  
Si el valor está fuera de 0–255 → `ERROR: valor PWM debe ser 0-255`.

**Nuevas funciones en el sketch:**
| Función | Descripción |
|---------|-------------|
| `esPinPwm(pin)` | Verifica si el pin está en {3,5,6,9,10,11} |
| `esPinAnalog(pin)` | Verifica si el pin está en {14–19} |
| `ejecutarAnalog(pin)` | `analogRead(pin)` → `"OK <valor>"` |
| `ejecutarPwm(pin, valor)` | `analogWrite(pin, valor)` → `"OK <valor>"` |

**Inicialización PWM en `setup()`:**
```cpp
const int PWM_PINS[] = {3, 5, 6, 9, 10, 11};
for (int i = 0; i < 6; i++) {
    pinMode(PWM_PINS[i], OUTPUT);
    digitalWrite(PWM_PINS[i], LOW);
}
```

**Pruebas en hardware:**
```
ANALOG A0        → OK 106       (pin flotante, ~0.085V)
ANALOG A1        → OK 89        (pin flotante)
ANALOG 13        → ERROR: pin no soporta lectura analogica
PWM 9 128        → OK 128       (50% duty cycle)
PWM 9 0          → OK 0         (apagado)
PWM 9 255        → OK 255       (100%)
PWM 9 300        → ERROR: valor PWM debe ser 0-255
PWM 2 128        → ERROR: pin no soporta PWM
```

### 3.2 Límite de la UNO Q

**La UNO Q NO tiene LED built-in conectado a D13** (a diferencia del Arduino Uno clásico). Los LEDs de la placa solo son accesibles desde el Linux interno, no desde los pines GPIO del sketch Arduino.

---

## 🎮 Fase 4 — Script de control remoto unificado

### 4.1 `unoq_remote.py`

Se creó un script Python con **menú interactivo** que unifica todo:

```
╔══════════════════════════════════════════════════╗
║          UNO Q — CONTROL REMOTO                 ║
╚══════════════════════════════════════════════════╝

  1. Digital          (D0-D13: leer/escribir)
  2. Analógico        (A0-A5: ADC / PWM)
  3. LEDs integrados  (verde, rojo, azul de la placa)
  0. Salir
```

### 4.2 Opción 1 — Digital

**Submenú:**
- Leer pin → elige D0–D13 → muestra HIGH/LOW
- Escribir pin → elige pin + valor (0/1)

**Comandos Serial equivalentes:**
```
READ <pin>
WRITE <pin> <0|1>
```

### 4.3 Opción 2 — Analógico

**Submenú:**
- Leer ADC → elige A0–A5 → muestra valor (0-4095), voltaje (0-3.3V), barra visual
- Escribir PWM → elige pin (3,5,6,9,10,11) + duty (0-255) → barra de porcentaje

**Comandos Serial equivalentes:**
```
ANALOG <pin>
PWM <pin> <0-255>
```

### 4.4 Opción 3 — LEDs integrados

Controla los **6 LEDs físicos de la placa** vía ADB → Linux sysfs.

**Submenú por LED:**
- Encender
- Apagar
- Parpadear (5 veces)

**Comandos globales:**
- `E` — Encender todos los LEDs
- `A` — Apagar todos los LEDs

**Implementación interna:**
```python
def _adb(cmd):
    subprocess.run(["adb", "shell", cmd], ...)

def _liberar_led(nombre):
    _adb(f"echo none > /sys/class/leds/{nombre}/trigger")

def _led_escribir(nombre, valor):
    _adb(f"echo {valor} > /sys/class/leds/{nombre}/brightness")
```

---

## 📊 Resumen de comandos totales

### Desde el sketch Arduino (vía Serial USB)

| Comando | Pines | Rango | Respuesta | Ejemplo |
|---------|-------|-------|-----------|---------|
| `READ <pin>` | 0–19 | 0/1 | `OK 0` / `OK 1` | `READ 13` |
| `WRITE <pin> <v>` | 0–19 | 0/1 | `OK 0` / `OK 1` | `WRITE 13 1` |
| `ANALOG <pin>` | 14–19 (A0–A5) | 0–4095 | `OK <valor>` | `ANALOG A0` |
| `PWM <pin> <v>` | 3,5,6,9,10,11 | 0–255 | `OK <valor>` | `PWM 9 128` |

### Desde el script Python unificado

```bash
# Menú completo
python3 unoq_remote.py

# Comandos rápidos
python3 unoq_gpio_control.py READ 13
python3 unoq_gpio_control.py WRITE 13 1
python3 unoq_gpio_control.py ANALOG A0
python3 unoq_gpio_control.py PWM 9 128
python3 unoq_gpio_control.py -i    # Modo interactivo
```

### Desde el Linux de la placa (ADB)

```bash
adb shell                              # Entrar al Linux
python3 /home/arduino/led.py           # Control del LED verde
gpioset -c gpiochip1 27=1             # GPIO directo
```

---

## 🗂️ Estructura final del proyecto

```
unoq_gpio_control/
├── unoq_gpio_control.ino    # Sketch Arduino — servidor de comandos
├── unoq_gpio_control.py     # Cliente Python — comandos Serial
├── unoq_remote.py           # Menú interactivo unificado
├── led.py                   # (en placa) Control LEDs vía sysfs
├── README.md                # Documentación principal
├── BITACORA.md              # Este archivo
├── PLAN.md                  # Plan de implementación (no se publica)
├── AUDIT_REPORT.md          # Reporte de auditoría (no se publica)
├── .gitignore               # Exclusiones Git
└── docs/
    ├── datasheet.md         # Ficha técnica de usuario
    └── developer.md         # Guía para desarrolladores
```

---

## 🔧 Comandos de compilación y carga

### Compilar
```bash
arduino-cli compile --fqbn arduino:zephyr:unoq unoq_gpio_control/
```

### Transferir a la placa
```bash
arduino-cli upload --fqbn arduino:zephyr:unoq \
  -p /dev/ttyACM0 \
  --upload-property upload.port.properties.serialNumber=<SERIAL> \
  unoq_gpio_control/
```

Donde `<SERIAL>` se obtiene con:
```bash
adb devices
# 2480682956   device
```

### Monitor Serial
```bash
stty -F /dev/ttyACM0 115200
cat /dev/ttyACM0
```

---

## ⚠️ Advertencias y notas importantes

1. **Voltaje:** La UNO Q opera a 3.3V. No conectar señales de 5V directamente a los pines.
2. **LED D13:** A diferencia del Arduino Uno clásico, la UNO Q NO tiene LED en D13. Usar `led.py` o `unoq_remote.py` opción 3 para los LEDs de la placa.
3. **ADC:** 12 bits (0-4095). Rango de voltaje: 0-3.3V.
4. **PWM:** Pines 3, 5, 6, 9, 10, 11. Resolución: 8 bits (0-255).
5. **ADB:** Necesario para acceder al Linux interno y los LEDs. El sketch Arduino usa Serial independiente.
6. **OpenOCD:** La transferencia de firmware usa SWD vía GPIO bitbang. No desconectar durante el flasheo.
7. **Zephyr RTOS:** Solo APIs estándar de Arduino. No usar registros AVR ni librerías específicas de arquitectura.
