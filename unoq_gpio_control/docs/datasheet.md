# Datasheet — UNO Q GPIO Control + Matriz LED

## Información General

| Campo | Valor |
|---|---|
| **Nombre del proyecto** | UNO Q GPIO Control + Matriz LED |
| **Versión** | 3.2.0 |
| **Placa objetivo** | Arduino UNO Q |
| **Microcontrolador** | STM32U585QII6 (ARM Cortex-M33 + TrustZone) |
| **RTOS** | Zephyr RTOS |
| **Tipo de proyecto** | Control remoto de GPIO y matriz LED vía Serial |
| **Arquitectura** | Cliente-Servidor (Python ↔ Arduino) |
| **Librerías requeridas** | `Arduino_LED_Matrix` v0.1.3, `ArduinoGraphics` |

---

## Especificaciones Técnicas

### Placa Arduino UNO Q

| Especificación | Valor |
|---|---|
| **Microcontrolador** | STM32U585QII6 |
| **Arquitectura** | ARM Cortex-M33 con TrustZone |
| **Frecuencia de reloj** | 160 MHz |
| **Memoria Flash** | 2 MB (2,097,152 bytes) |
| **Memoria RAM** | 262 KB (262,144 bytes) |
| **Pines digitales GPIO** | 14 (D0–D13) |
| **Pines de entrada analógica** | 6 (A0–A5), reutilizables como digitales |
| **Resolución ADC** | 12 bits (0–4095) |
| **Resolución PWM** | 8 bits (0–255), pines 3, 5, 6, 9, 10, 11 |
| **Matriz LED** | 12x8 píxeles integrada, canvas lógico 13x8 |
| **Voltaje de operación** | 3.3V (lógica y GPIO) |
| **Voltaje de alimentación** | 5V vía USB-C |
| **Corriente máxima por pin** | 20 mA (recomendada), 40 mA (máxima absoluta) |
| **Interfaces** | USB-C (CDC ACM, SWD), UART, I2C, SPI, CAN |
| **Conectividad** | Wi-Fi + BLE (módulo integrado) |
| **Sistema operativo** | Zephyr RTOS |
| **Debug** | SWD vía USB-C (ADB + OpenOCD) |

### Protocolo de Comunicación Serial

| Parámetro | Valor |
|---|---|
| **Interfaz física** | USB 2.0 CDC ACM |
| **Baud rate** | 115200 bps |
| **Data bits** | 8 |
| **Paridad** | Ninguna |
| **Stop bits** | 1 |
| **Control de flujo** | Ninguno |
| **Puerto Linux** | `/dev/ttyACM0` (configurable) |
| **Puerto Windows** | `COM3` (variable) |
| **Puerto macOS** | `/dev/tty.usbmodem*` (variable) |
| **Delimitador** | `\n` (LF, 0x0A) |
| **Tolerancia** | `\r\n` (CRLF), líneas vacías ignoradas |
| **Longitud máxima de línea** | 128 bytes |

### Formato de Mensajes

| Tipo | Formato | Ejemplo |
|---|---|---|
| **Mensaje de inicialización** | `UNOQ_GPIO_READY` | `UNOQ_GPIO_READY` |
| **Comando READ** | `READ <pin>\n` | `READ 13\n` |
| **Comando WRITE** | `WRITE <pin> <0\|1>\n` | `WRITE 13 1\n` |
| **Comando ANALOG** | `ANALOG <pin>\n` | `ANALOG A0\n` |
| **Comando PWM** | `PWM <pin> <0-255>\n` | `PWM 9 128\n` |
| **Comando MATRIX CLEAR** | `MATRIX CLEAR\n` | — |
| **Comando MATRIX LINE1** | `MATRIX LINE1 <texto>\n` | `MATRIX LINE1 Hola\n` |
| **Comando MATRIX LINE2** | `MATRIX LINE2 <texto>\n` | `MATRIX LINE2 Mundo\n` |
| **Comando MATRIX SHOW** | `MATRIX SHOW\n` | → 2 líneas estáticas 3×4 |
| **Comando MATRIX TINY** | `MATRIX TINY\n` | → 2 líneas estáticas 3×4 |
| **Comando MATRIX TINYSCROLL** | `MATRIX TINYSCROLL <texto>\n` | → marquesina 3×4 centrada |
| **Comando MATRIX SPEED** | `MATRIX SPEED <ms>\n` | `MATRIX SPEED 80\n` |
| **Comando MATRIX atajo** | `MATRIX <texto>\n` | `MATRIX Hola Mundo\n` |
| **Comando TEMP (experimental)** | `TEMP\n` | `TEMP\n` → `OK 38.2 C (1892 raw)\n` |
| **Respuesta OK** | `OK <detalle>\n` | `OK 1\n`, `OK CLEAR\n`, `OK TINYSCROLL\n` |
| **Error** | `ERROR: <mensaje>\n` | `ERROR: pin invalido\n` |

### Rendimiento

| Métrica | Valor |
|---|---|
| **Tasa de comandos sostenida** | ~100 comandos/segundo |
| **Latencia comando-respuesta** | < 10 ms (típica, comandos no bloqueantes) |
| **Latencia MATRIX TINYSCROLL** | 2–10 segundos (depende del texto y velocidad) |
| **Velocidad de marquesina** | 10–500 ms por frame (configurable, default 70ms) |
| **Velocidad de scroll grande** | 100 ms por frame (constante) |
| **Timeout de lectura (sketch)** | 1 segundo |
| **Timeout de lectura (Python)** | 2 segundos (configurable) |
| **Uso de RAM** | ~35 KB (~13% del total) |
| **Uso de Flash** | ~93 KB (~4% del total) |
| **Consumo de energía** | ~50 mA (típico, sin periféricos externos) |

---

## Instalación y Configuración

### Requisitos del Sistema

**Hardware:**
- Arduino UNO Q
- Cable USB-C (datos + poder)
- Computadora con Linux, macOS o Windows

**Software (host):**
- Python 3.6 o superior
- `pyserial` (`pip install pyserial`)
- `arduino-cli` 0.35.0 o superior
- Core `arduino:zephyr` instalado
- ADB (Android Debug Bridge) — para upload y opción LEDs de `unoq_remote.py`
- Reglas udev (Linux) o drivers (Windows)

**Librerías Arduino (instaladas automáticamente con el core):**
- `Arduino_LED_Matrix` v0.1.3
- `ArduinoGraphics` (dependencia)

### Instalación Paso a Paso

#### 1. Instalar arduino-cli

```bash
# Linux/macOS
curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | sh

# Verificar instalación
arduino-cli version
```

#### 2. Instalar el core Zephyr para UNO Q

```bash
arduino-cli core update-index
arduino-cli core install arduino:zephyr
```

#### 3. Instalar pyserial

```bash
pip install pyserial
```

#### 4. Configurar reglas udev (solo Linux)

```bash
echo 'SUBSYSTEM=="tty", ATTRS{idVendor}=="2341", ATTRS{idProduct}=="0078", MODE="0666", SYMLINK+="ttyACM_UNOQ"' | sudo tee /etc/udev/rules.d/99-arduino-unoq.rules
sudo udevadm control --reload-rules
sudo udevadm trigger
```

#### 5. Compilar y cargar el sketch

```bash
cd unoq_gpio_control/
arduino-cli compile --fqbn arduino:zephyr:unoq .
arduino-cli upload -p /dev/ttyACM0 --fqbn arduino:zephyr:unoq .
```

#### 6. Verificar funcionamiento

```bash
arduino-cli monitor -p /dev/ttyACM0 --config baudrate=115200
# Debe aparecer: UNOQ_GPIO_READY

# En otra terminal:
python3 unoq_gpio_control.py MATRIX TINYSCROLL "Hola UNO Q!"
```

---

## Guía de Operación

### Los 3 Scripts — Guía de Selección

| Característica | `unoq_gpio_control.py` (línea de comandos) | `unoq_gpio_control.py -i` (interactivo) | `unoq_remote.py` (menú remoto) |
|---|---|---|---|
| **Complejidad** | Alta (memorizar comandos) | Media | **Baja** (guiado) |
| **GPIO** | ✅ | ✅ | ✅ Con barras visuales |
| **Matriz LED** | ✅ Todos los comandos | ✅ Menú guiado | ✅ Asistente paso a paso |
| **LEDs integrados** | ❌ | ❌ | ✅ 6 LEDs vía ADB |
| **Automatización** | ✅ Scripts bash | ❌ | ❌ |
| **Mejor para** | CI/CD, scripting | Desarrolladores | **Usuarios finales** |

### Modo Comando Único (`unoq_gpio_control.py`)

Ejecuta un comando y sale. Ideal para scripts y automatización:

```bash
python3 unoq_gpio_control.py READ 13
python3 unoq_gpio_control.py WRITE 13 1
python3 unoq_gpio_control.py ANALOG A0
python3 unoq_gpio_control.py PWM 9 128
python3 unoq_gpio_control.py TEXTO "Hola"                       # Marquesina chica
python3 unoq_gpio_control.py TEXTO --tamano grande "HOLA"       # Scroll grande
python3 unoq_gpio_control.py TEXTO --velocidad 30 "Rápido!"     # Marquesina rápida
python3 unoq_gpio_control.py MATRIX CLEAR
python3 unoq_gpio_control.py MATRIX TINYSCROLL "Arduino UNO Q"
python3 unoq_gpio_control.py MATRIX SPEED 50
```

### Modo Interactivo (`unoq_gpio_control.py -i`)

Sesión persistente con menú de 6 opciones:

```bash
python3 unoq_gpio_control.py -i
```

```
==============================================================
  UNO Q GPIO Control — Modo Interactivo
==============================================================

  1. Imprimir texto en matriz LED
  2. Control de pines (READ / WRITE)
  3. Lectura analógica (ANALOG)
  4. Control PWM
  5. Comandos MATRIX (CLEAR, LINE1/2, SHOW, TINY...)
  6. Salir

  Opción [1-6]:
```

- **Opción 1**: Asistente de texto — elige tamaño (tiny/grande), velocidad, y texto.
- **Opción 2**: Sub-REPL para READ/WRITE con prompt `pin>`.
- **Opción 3**: Sub-REPL para ANALOG con prompt `adc>`.
- **Opción 4**: Sub-REPL para PWM con prompt `pwm>`.
- **Opción 5**: Sub-REPL para comandos MATRIX con prompt `matrix>` (acceso directo a CLEAR, LINE1/2, SHOW, TINY, TINYSCROLL, SPEED).

### Menú Remoto (`unoq_remote.py`) — Guía Paso a Paso

`unoq_remote.py` es la interfaz más amigable. Sigue estos pasos para cada operación:

#### Paso 1: Iniciar

```bash
python3 unoq_remote.py
```

Verás el menú principal con 4 opciones.

#### Paso 2 — Usar la Opción 1 (Digital)

1. Selecciona `1` en el menú principal.
2. Elige `1` (Leer pin) o `2` (Escribir pin).
3. Ingresa el número de pin (0–13).
4. Para escritura: ingresa `0` (LOW/apagar) o `1` (HIGH/encender).
5. El resultado se muestra inmediatamente.
6. Presiona ENTER para volver al submenú.

#### Paso 3 — Usar la Opción 2 (Analógico)

1. Selecciona `2` en el menú principal.
2. **Leer ADC**: Elige `1`, luego el número de pin analógico (0–5 para A0–A5). Verás el valor crudo (0–4095), voltaje calculado, y una barra visual.
3. **Escribir PWM**: Elige `2`, luego el pin (3,5,6,9,10,11), luego el duty cycle (0–255). Verás el porcentaje y una barra visual.

#### Paso 4 — Usar la Opción 3 (LEDs integrados)

1. Selecciona `3` en el menú principal.
2. Verás los 6 LEDs con su estado actual (🟢 encendido, ⚫ apagado).
3. Elige un número (1–6) para controlar un LED individual.
4. En el submenú del LED: `1` encender, `2` apagar, `3` parpadear 5 veces.
5. O usa `E` para encender todos, `A` para apagar todos.

**Requisito**: ADB debe estar instalado y la placa visible (`adb devices`).

#### Paso 5 — Usar la Opción 4 (Texto en matriz)

1. Selecciona `4` en el menú principal.
2. **Elige tamaño**: `1` = fuente chica (3×4, centrada), `2` = fuente grande (5×7).
3. **Velocidad** (solo fuente chica): ingresa un valor entre 10 y 500 ms. Default: 70.
4. **Texto**: escribe lo que quieras mostrar (ASCII: letras, números, espacios).
5. El texto aparece inmediatamente en la matriz LED.

### Control de la Matriz LED 12x8

La matriz LED soporta **dos modos de visualización**:

#### Modo 1: Dos líneas estáticas (fuente 3×4)

Usa `MATRIX SHOW` o `MATRIX TINY`. Muestra `LINE1` en las filas superiores y `LINE2` en las inferiores, ambas estáticas y simultáneas.

```
┌──────────────────────────┐
│ T : 2 5 C                │  ← Línea 1 (filas 0-3)
│ H : 6 0 %                │  ← Línea 2 (filas 4-7)
└──────────────────────────┘
```

**Limitaciones**: ~3 caracteres por línea (13 columnas / 4px por carácter). Solo ASCII: A-Z, 0-9, !, -, ., :, _.

#### Modo 2: Marquesina centrada (fuente 3×4)

Usa `MATRIX TINYSCROLL <texto>`. Texto más largo se desplaza horizontalmente, centrado verticalmente con márgenes:

```
  ┌──────────────────────────┐
  │                          │  ← margen superior (2px)
  │■■■ ■ ■■■ ■■■             │  ← texto 3×4 centrado
  │                          │  ← margen inferior (2px)
  └──────────────────────────┘
        ← scroll izquierda
```

Velocidad configurable con `MATRIX SPEED <10-500>`.

#### Modo 3: Scroll grande (fuente 5×7)

Usa `MATRIX <texto>`. Texto en fuente grande que ocupa 7 de 8 filas, con scroll horizontal completo.

#### Flujo de trabajo típico

```
1. MATRIX LINE1 "T:25C"          → Almacena línea 1
2. MATRIX LINE2 "H:60%"          → Almacena línea 2
3. MATRIX SHOW                   → Muestra ambas líneas estáticas
   ...o...
3. MATRIX CLEAR                  → Limpia y empieza de nuevo
4. MATRIX SPEED 50               → Configura velocidad rápida
5. MATRIX TINYSCROLL "Hola!"     → Marquesina centrada
```

### Lectura de Temperatura del Chip (NUEVO v3.2)

El STM32U585 tiene un sensor de temperatura interno que se puede leer por dos vías:

#### Método 1: Vía Linux sysfs (preferido)

La UNO Q ejecuta Linux internamente y expone la temperatura en `/sys/class/thermal/thermal_zone0/temp`. `unoq_remote.py` lo lee directamente vía ADB:

```
Valor en sysfs: 38200 → 38.2°C
```

Este método es el más preciso y no depende del firmware Arduino. Solo requiere ADB funcional.

#### Método 2: Vía comando TEMP (experimental)

El sketch envía el comando `TEMP` por Serial, que usa el ADC interno del STM32U585:

- **Canal ADC**: ADC1, canal 19 (sensor de temperatura interno)
- **Calibración**: Valores de fábrica `TS_CAL1` (30°C) y `TS_CAL2` (130°C) en direcciones flash `0x0BFA0710` y `0x0BFA0742`
- **Pendiente promedio**: 2.5 mV/°C (típico STM32U5)
- **VREF**: 3.0V
- **Resolución**: 12 bits

**Fórmula de conversión**:
```
temp = ((adc_raw - TS_CAL1) * (130.0 - 30.0)) / (TS_CAL2 - TS_CAL1) + 30.0
```

**Rango típico de operación**:
| Temperatura | Valor ADC (aprox.) | Estado |
|---|---|---|
| 20°C | ~1750 | Frío (tras arranque) |
| 30°C | ~1830 | Normal |
| 40°C | ~1910 | Normal-elevado |
| 55°C | ~2030 | ⚠️ Caliente |
| 70°C | ~2150 | 🔥 Muy caliente |

**Nota importante**: El comando `TEMP` es **experimental**. Depende del acceso directo a la API de ADC de Zephyr y puede no funcionar en todas las builds del core `arduino:zephyr`. Si falla, usa el método de sysfs (opción 5 de `unoq_remote.py`).

### Auto-Detección de Puerto (NUEVO v3.2)

`unoq_remote.py` incluye la función `_detectar_puerto()` que busca automáticamente cualquier `/dev/ttyACM*` disponible. Ya no es necesario que la placa esté en `ttyACM0` — si el kernel le asigna `ttyACM1`, `ttyACM2` u otro, el script lo encuentra.

```
$ python3 unoq_remote.py
  Conectado a /dev/ttyACM2    ← detectado automáticamente
```

Si ningún puerto está disponible, usa el fallback `/dev/ttyACM0`.

### Casos de Uso Típicos — GPIO

#### 1. Control de LEDs

```
Conexión: LED + resistor 220Ω en cualquier pin GPIO

python3 unoq_gpio_control.py WRITE 13 1   # Encender
python3 unoq_gpio_control.py WRITE 13 0   # Apagar

# Parpadeo desde bash
for i in {1..10}; do
  python3 unoq_gpio_control.py WRITE 13 1
  sleep 0.5
  python3 unoq_gpio_control.py WRITE 13 0
  sleep 0.5
done
```

#### 2. Lectura de pulsadores

```
Conexión: Pulsador entre D2 y GND, resistor 10kΩ entre D2 y 3.3V (pull-up)

python3 unoq_gpio_control.py READ 2
# OK 1 = no presionado, OK 0 = presionado
```

#### 3. Lectura de sensores analógicos

```
Conexión: Potenciómetro entre 3.3V y GND, cursor a A0

python3 unoq_gpio_control.py ANALOG A0
# → OK 2048 (mitad del recorrido, ~1.65V)
```

#### 4. Control de brillo LED con PWM

```
Conexión: LED + resistor 220Ω en D9

python3 unoq_gpio_control.py PWM 9 128   # 50% brillo
python3 unoq_gpio_control.py PWM 9 25    # 10% brillo
python3 unoq_gpio_control.py PWM 9 0     # Apagado
```

---

## Guía de Solución de Problemas

### Problemas de Conexión

| Síntoma | Diagnóstico | Solución |
|---|---|---|
| Placa no aparece en `arduino-cli board list` | Cable solo de carga, falta regla udev | Usar cable de datos, verificar regla udev |
| `arduino-cli upload` falla con timeout | ADB no detecta la placa | `adb devices`, resetear placa, reinstalar core |
| Script Python: "No se pudo abrir el puerto" | Puerto ocupado, permisos | Cerrar Serial Monitor, verificar `board list` |
| No se recibe `UNOQ_GPIO_READY` | Baud rate incorrecto, sketch no cargado | Verificar 115200 baud, recargar sketch |

### Problemas de Comandos

| Síntoma | Diagnóstico | Solución |
|---|---|---|
| `ERROR: comando no reconocido` | Formato incorrecto | Usar formato exacto del protocolo |
| `ERROR: pin invalido` | Pin fuera de rango 0–19 | Usar pines 0–19 o notación A0–A5 |
| `ERROR: pin no soporta lectura analogica` | ANALOG en pin no ADC | Solo A0–A5 (14–19) |
| `ERROR: pin no soporta PWM` | PWM en pin sin capacidad | Solo 3, 5, 6, 9, 10, 11 |
| `ERROR: valor PWM debe ser 0-255` | Valor fuera de rango | Usar 0–255 |
| `ERROR: velocidad 10-500 ms` | SPEED fuera de rango | Usar 10–500 |
| `ERROR: texto vacio para TINYSCROLL` | Sin texto | Agregar texto al comando |
| MATRIX SHOW muestra caracteres raros | Caracteres no soportados en fuente 3×4 | Solo A-Z, 0-9, !, -, ., :, _ |
| Sin respuesta durante TINYSCROLL | Comando bloqueante | Esperar a que termine |

### Problemas de Hardware

| Síntoma | Diagnóstico | Solución |
|---|---|---|
| LED no enciende con `WRITE` | LED al revés, resistor incorrecto | Ánodo al pin, cátodo a GND, 220Ω |
| Lectura errática en pin de entrada | Pin flotante | Agregar pull-up (10kΩ a 3.3V) o pull-down |
| ADC devuelve ruido | Pin analógico flotante | Conectar sensor o pull-down |
| Componentes de 5V no funcionan | UNO Q opera a 3.3V | Usar level shifter o componentes 3.3V |
| `unoq_remote.py` opción 3 no funciona | ADB no instalado/detectado | `sudo apt install adb`, verificar `adb devices` |
| Temperatura no se lee (opción 5) | ADB no disponible y TEMP no implementado | Instalar ADB o recargar sketch |
| `TEMP` vía Serial: `ERROR: ADC no disponible` | Build de Zephyr sin soporte ADC interno | Usar sysfs (opción 5) o verificar build |
| Placa en ttyACM1 no detectada | Puerto distinto a ttyACM0 | **Resuelto en v3.2**: `_detectar_puerto()` busca automáticamente |

---

## Compatibilidad con Otras Placas

| Placa | Compatibilidad | Modificaciones necesarias |
|---|---|---|
| **Arduino UNO Q** | Nativa | Ninguna — FQBN `arduino:zephyr:unoq` |
| **Arduino Uno R3 (ATmega328P)** | Baja | ADC 10-bit. **No tiene matriz LED**. Eliminar MATRIX. |
| **Arduino Mega 2560** | Baja | Rango de pines 0–69. **No tiene matriz LED**. |
| **Arduino Nano 33 BLE** | Media | ADC 12-bit. **No tiene matriz LED**. |
| **Arduino Zero (SAMD21)** | Media | ADC 12-bit. **No tiene matriz LED**. |
| **Arduino Due (SAM3X)** | Media | 3.3V nativo. **No tiene matriz LED**. |

**Notas de portabilidad:**
- Las APIs GPIO estándar funcionan en cualquier placa Arduino.
- La matriz LED (`Arduino_LED_Matrix`) es **exclusiva de la UNO Q** (arquitectura `zephyr`).
- La fuente 3×4 personalizada (`FONT_3X4`) y el renderizado `renderTinyText()` son código C++ portable.
- Para portar: eliminar includes de `Arduino_LED_Matrix`, el objeto `matrix`, y toda la rama MATRIX del `loop()`.

---

## Librerías Requeridas

### Sketch Arduino

| Librería | Versión | Arquitectura | Propósito | Instalación |
|---|---|---|---|---|
| `Arduino_LED_Matrix` | 0.1.3 | `zephyr` | Control de la matriz LED 12x8 | Incluida en core `arduino:zephyr` |
| `ArduinoGraphics` | (incluida) | `zephyr` | Renderizado de texto y gráficos | Dependencia de `Arduino_LED_Matrix` |

**APIs built-in de Arduino usadas:**
- `pinMode()`, `digitalRead()`, `digitalWrite()` — GPIO
- `analogRead()` — ADC 12-bit (0–4095)
- `analogWrite()` — PWM 8-bit (0–255)
- `Serial` — USB CDC ACM
- `String`, `delay()`, `millis()`, `memset()`, `strlen()`

**APIs de Arduino_LED_Matrix usadas:**
- `matrix.begin()`, `matrix.textFont()`, `matrix.textScrollSpeed()`
- `matrix.clear()`, `matrix.beginText()`, `matrix.print()`, `matrix.endText()`
- `matrix.loadPixels()` — para renderizado de fuente 3×4 personalizada

### Scripts Python

| Paquete | Versión mínima | Instalación |
|---|---|---|
| `pyserial` | 3.0 | `pip install pyserial` |

Módulos de biblioteca estándar usados:
- `argparse`, `sys`, `time` — todos los scripts
- `subprocess`, `os` — solo `unoq_remote.py` (para ADB y limpieza de terminal)

---

## Seguridad y Mejores Prácticas

### Seguridad Eléctrica

1. **No exceder 3.3V** en ningún pin de entrada. La UNO Q es una placa de 3.3V.
2. Usar **resistencias limitadoras de corriente** (220Ω–1kΩ) con LEDs.
3. Usar **resistencias pull-up** (10kΩ) o **pull-down** (10kΩ) en pines de entrada.
4. No conectar cargas inductivas directamente a GPIO. Usar transistores, MOSFETs o módulos relé.
5. La corriente máxima por pin GPIO es **20 mA**. Total de todos los pines ≤ **100 mA**.

### Seguridad de Comunicación

1. **No hay autenticación ni cifrado** en el protocolo Serial.
2. **No usar este protocolo sobre redes** sin capa de seguridad adicional.
3. Precaución al controlar actuadores de alto voltaje.

### Mejores Prácticas

1. Siempre inicia los pines como `INPUT` (el sketch ya lo hace).
2. Usa el modo interactivo (`-i`) para explorar antes de automatizar.
3. Para la matriz LED, usa `MATRIX CLEAR` al terminar.
4. Recuerda que `TINYSCROLL` y `MATRIX <texto>` son bloqueantes.
5. La fuente 3×4 solo soporta A-Z, 0-9, !, -, ., :, _. Usa mayúsculas.

---

## Especificaciones de Alimentación

| Parámetro | Mínimo | Típico | Máximo | Unidad |
|---|---|---|---|---|
| Voltaje de alimentación (USB-C) | 4.5 | 5.0 | 5.5 | V |
| Voltaje de alimentación (VIN) | 3.7 | — | 5.0 | V |
| Voltaje de operación GPIO | 0 | 3.3 | 3.6 | V |
| Corriente de salida 3.3V | — | — | 500 | mA |
| Corriente por pin GPIO | — | — | 20 | mA |
| Corriente total GPIOs | — | — | 100 | mA |
| Consumo de la placa (sin periféricos) | — | 50 | — | mA |
| Consumo adicional con matriz LED activa | — | 10 | 20 | mA |

---

## Garantía y Soporte

Este proyecto es de código abierto y se proporciona **sin garantía**. El uso es bajo tu propia responsabilidad.

Para soporte, consulta:
- La [documentación de Arduino UNO Q](https://docs.arduino.cc/hardware/uno-q)
- La [documentación de Zephyr RTOS](https://docs.zephyrproject.org/)
- La [documentación de Arduino_LED_Matrix](https://github.com/arduino/Arduino_LED_Matrix)
- El [repositorio del core arduino:zephyr](https://github.com/arduino/arduino-zephyr)
