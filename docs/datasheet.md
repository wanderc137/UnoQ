# Datasheet — UNO Q Lab

**Manual de usuario de los dos ejemplos del repositorio.**

| Campo | Valor |
|---|---|
| Proyecto | UNO Q Lab |
| Versión del documento | 1.0 |
| Placa objetivo | Arduino UNO Q (ABX00162) |
| MCU | STM32U585 (Cortex-M33, 160 MHz, 2 MB flash, 786 KB SRAM) |
| MPU | Qualcomm Dragonwing QRB2210 (4× Cortex-A53, Debian Linux) |
| RTOS del MCU | Zephyr |
| FQBN | `arduino:zephyr:unoq` |
| Contenido | `blink` (ejemplo mínimo) + `unoq_gpio_control` (servidor de comandos) |
| Licencia | MIT (c) 2026 wanderc137 |

---

## Índice

1. [Qué contiene el repositorio](#qué-contiene-el-repositorio)
2. [Especificaciones de la placa](#especificaciones-de-la-placa)
3. [Ejemplo 1 — blink](#ejemplo-1--blink)
4. [Ejemplo 2 — unoq_gpio_control](#ejemplo-2--unoq_gpio_control)
5. [Tabla de pines](#tabla-de-pines)
6. [Cableado](#cableado)
7. [Protocolo de comandos](#protocolo-de-comandos)
8. [La matriz LED](#la-matriz-led)
9. [Temperatura y LEDs onboard](#temperatura-y-leds-onboard)
10. [Calibración](#calibración)
11. [Solución de problemas](#solución-de-problemas)
12. [Compatibilidad con otras placas](#compatibilidad-con-otras-placas)
13. [Límites eléctricos](#límites-eléctricos)
14. [Glosario](#glosario)

---

## Qué contiene el repositorio

Dos carpetas independientes:

| Carpeta | Qué es | Para quién |
|---|---|---|
| `blink/unoq_blink/` | El sketch más pequeño posible: prender y apagar `LED_BUILTIN` cada segundo. | Quien acaba de sacar la placa de la caja y quiere saber si la toolchain funciona. |
| `unoq_gpio_control/` | Un sketch servidor de comandos + dos clientes Python + documentación de desarrollo. | Quien quiere controlar la placa desde la PC y entender un protocolo real. |

Cada una se compila por separado; no comparten código.

---

## Especificaciones de la placa

### Núcleos

| Especificación | MPU (QRB2210) | MCU (STM32U585) |
|---|---|---|
| Arquitectura | 4× Arm Cortex-A53 @ 2.0 GHz | Arm Cortex-M33 @ 160 MHz |
| GPU | Adreno (aceleración 3D) | — |
| ISP | 2× ISP (13+13 MP o 25 MP @ 30 fps) | — |
| Memoria | LPDDR4 (2 GB en la variante base; existe variante de 4 GB) + eMMC | 2 MB flash + 786 KB SRAM |
| Sistema operativo | Debian Linux (upstream) | Zephyr RTOS |
| FPU | — | Sí |
| TrustZone | — | Sí |

### Placa

| Especificación | Valor |
|---|---|
| Formato | UNO (compatible con shields) |
| Alimentación | 5 V por USB-C |
| Lógica | **3.3 V** |
| GPIO del header | D0–D13 (14) + A0–A5 (6, reutilizables como digitales) |
| ADC | **12 bits (0–4095)**, canales A0–A5 |
| PWM | 8 bits (0–255) en D3, D5, D6, D9, D10, D11 |
| Matriz LED | 12×8 integrada (canvas lógico 13×8) |
| Conectividad | Wi-Fi 5 dual-band 2.4/5 GHz + Bluetooth 5.1 (módulo WCBN3536A) |
| Conectores | USB-C, header UNO, Qwiic, conectores de alta velocidad inferiores (MIPI-CSI/DSI, audio) |
| USB ID | `2341:0078` |
| Programación | ADB + OpenOCD + SWD (sin bootloader) |

> **Memoria del sketch.** El core reporta el uso de RAM contra la región asignada al sketch (~256 KB), no contra los 786 KB totales del silicio. Cuando `arduino-cli` dice "10 % de memoria dinámica", ese porcentaje corresponde a esa región.

### Diferencias clave con el Arduino Uno clásico

| Aspecto | Uno R3 (ATmega328P) | UNO Q |
|---|---|---|
| Voltaje | 5 V | **3.3 V** |
| ADC | 10 bits (0–1023) | **12 bits (0–4095)** |
| LED en D13 | Sí | **No** |
| Sistema | Bare-metal / bootloader | **Zephyr RTOS + Linux en el MPU** |
| Carga | Bootloader por serie | **ADB + OpenOCD por SWD** |
| Reloj | 16 MHz | 160 MHz (MCU) + 2 GHz ×4 (MPU) |
| Memoria | 32 KB flash / 2 KB RAM | 2 MB flash / 786 KB SRAM |
| Matriz LED | No | **Sí, 12×8** |

---

## Ejemplo 1 — blink

### Qué hace

```cpp
void setup() {
  pinMode(LED_BUILTIN, OUTPUT);
}

void loop() {
  digitalWrite(LED_BUILTIN, HIGH);
  delay(1000);
  digitalWrite(LED_BUILTIN, LOW);
  delay(1000);
}
```

Conmuta el pin asociado a `LED_BUILTIN` con período de 2 segundos.

### Materiales

- Arduino UNO Q
- Cable USB-C de datos
- Opcional: LED + resistencia de 220 Ω

### Operación

```bash
cd blink/unoq_blink
arduino-cli compile --fqbn arduino:zephyr:unoq .
arduino-cli upload -p /dev/ttyACM0 --fqbn arduino:zephyr:unoq .
```

### Verificación

| Comprobación | Resultado esperado |
|---|---|
| `arduino-cli board list` | Placa listada con FQBN `arduino:zephyr:unoq` |
| Compilación | Sin errores |
| Carga | OpenOCD detecta STM32U585 y programa |
| LED externo en D13 | 1 s encendido, 1 s apagado |

### Advertencia importante

La UNO Q **no tiene LED físico en D13**. Si cargás el sketch y no ves nada, el firmware probablemente esté corriendo bien. Conectá un LED externo (D13 → 220 Ω → ánodo → cátodo → GND) o usá el ejemplo 2 para escribir en la matriz LED.

---

## Ejemplo 2 — unoq_gpio_control

### Qué hace

El sketch funciona como **servidor de comandos** por USB CDC ACM a 115200 baud. Los clientes Python envían líneas de texto y reciben respuestas también de texto.

Capacidades:

- Lectura y escritura de GPIO digital (D0–D19 lógicos).
- Lectura analógica de 12 bits en A0–A5.
- Salida PWM de 8 bits en seis pines.
- Texto en la matriz LED 12×8 (cuatro modos de render).
- Lectura experimental de la temperatura interna del MCU.

Además, `unoq_remote.py` controla los **LEDs onboard** y lee la **temperatura del SoC** a través de ADB, sin pasar por el sketch.

### Materiales

| Elemento | Uso |
|---|---|
| Arduino UNO Q | Hardware principal |
| Cable USB-C de datos | Alimentación + comunicación |
| LED + 220 Ω | Probar `WRITE` y `PWM` |
| Pulsador + 10 kΩ | Probar `READ` con pull-up |
| Potenciómetro 10 kΩ | Probar `ANALOG` |
| PC con Python 3 y `pyserial` | Ejecutar los clientes |

### Instalación

```bash
# 1. Core de Arduino para Zephyr
arduino-cli core update-index
arduino-cli core install arduino:zephyr

# 2. Dependencias del cliente
python3 -m pip install pyserial

# 3. ADB (solo para upload y para los LEDs onboard)
sudo apt install adb
adb devices
```

### Carga del firmware

```bash
cd unoq_gpio_control
arduino-cli compile --fqbn arduino:zephyr:unoq .
arduino-cli upload -p /dev/ttyACM0 --fqbn arduino:zephyr:unoq .
```

Si el upload exige el número de serie:

```bash
adb devices
arduino-cli upload -p /dev/ttyACM0 --fqbn arduino:zephyr:unoq \
  --upload-property upload.port.properties.serialNumber=<SERIAL> .
```

### Los tres modos de uso

| Modo | Comando | Cuándo usarlo |
|---|---|---|
| Comando único | `python3 unoq_gpio_control.py READ 13` | Scripts, automatización, pruebas rápidas |
| Interactivo | `python3 unoq_gpio_control.py -i` | Explorar el protocolo con submenús |
| Menú guiado | `python3 unoq_remote.py` | Primer uso, demos, LEDs onboard, temperatura |

#### Modo comando único

```bash
python3 unoq_gpio_control.py READ 13
python3 unoq_gpio_control.py WRITE 13 1
python3 unoq_gpio_control.py ANALOG A0
python3 unoq_gpio_control.py PWM 9 128
python3 unoq_gpio_control.py MATRIX "Hola"
python3 unoq_gpio_control.py TEXTO "Hola" --tamano tiny --velocidad 50
```

Opciones: `-p/--port` (default `/dev/ttyACM0`), `-b/--baud` (115200), `-t/--timeout` (2 s), `-i/--interactive`, `--tamano {tiny,grande}`, `--velocidad 10-500`.

#### Modo interactivo

Menú de seis opciones: texto en matriz, pines (READ/WRITE), analógico, PWM, comandos MATRIX y salida. Cada submenú acepta `volver` para regresar.

#### Menú guiado

Cinco opciones:

1. **Digital** — D0–D13, leer o escribir, con validación de rango.
2. **Analógico** — ADC con voltaje calculado y barra; PWM con porcentaje y barra.
3. **LEDs integrados** — seis LEDs vía ADB (`green:user`, `red:user`, `blue:user`, `green:wlan`, `red:panic`, `blue:bt`), con encender/apagar/parpadear.
4. **Texto en matriz** — elige fuente (3×4 o 5×7), velocidad y texto.
5. **Temperatura** — `thermal_zone0` vía ADB, con fallback al comando `TEMP`.

`unoq_remote.py` autodetecta el puerto recorriendo `/dev/ttyACM*`.

---

## Tabla de pines

| Pin | Lógico | Inicial | ADC | PWM | Observaciones |
|---|---|---|---|---|---|
| D0 | 0 | INPUT | — | — | RX USART1 |
| D1 | 1 | INPUT | — | — | TX USART1 |
| D2 | 2 | INPUT | — | — | GPIO — pulsador típico |
| D3 | 3 | OUTPUT (LOW) | — | Sí | PWM |
| D4 | 4 | INPUT | — | — | GPIO |
| D5 | 5 | OUTPUT (LOW) | — | Sí | PWM |
| D6 | 6 | OUTPUT (LOW) | — | Sí | PWM |
| D7 | 7 | INPUT | — | — | GPIO |
| D8 | 8 | INPUT | — | — | GPIO |
| D9 | 9 | OUTPUT (LOW) | — | Sí | PWM |
| D10 | 10 | OUTPUT (LOW) | — | Sí | PWM |
| D11 | 11 | OUTPUT (LOW) | — | Sí | PWM |
| D12 | 12 | INPUT | — | — | GPIO |
| D13 | 13 | INPUT | — | — | Sin LED onboard |
| A0 | 14 | INPUT | Sí | — | También digital |
| A1 | 15 | INPUT | Sí | — | También digital |
| A2 | 16 | INPUT | Sí | — | También digital |
| A3 | 17 | INPUT | Sí | — | También digital |
| A4 | 18 | INPUT | Sí | — | SDA I2C |
| A5 | 19 | INPUT | Sí | — | SCL I2C |
| GPIOF 0 | — | interno | — | — | Matriz LED 12×8 |

Notación aceptada por el sketch: `13`, `A0`, `a0`. `A6` y superiores se rechazan; `A` solo también.

---

## Cableado

### Conexión mínima

Solo USB-C entre la placa y la PC. Nada más.

### LED externo (D13 o cualquier GPIO)

```
D13 ──[220 Ω]──►|── GND
                 LED
```

Ánodo (pata larga) hacia la resistencia/pin; cátodo (pata corta) a GND.

### Pulsador con pull-up

```
3.3V ──[10 kΩ]──┬── D2
                │
             ┌──┴──┐
             │ SW  │
             └──┬──┘
                │
               GND
```

Sin pulsar: D2 lee `1`. Pulsado: `0`.

### Potenciómetro

```
3.3V ── extremo 1
A0   ── cursor (patita central)
GND  ── extremo 2
```

### LED con PWM

Igual que el LED simple, pero en D3, D5, D6, D9, D10 u D11.

> **Nunca** conectes un LED sin resistencia: la salida del GPIO no limita corriente y podés dañar el pin o el LED.

---

## Protocolo de comandos

### Formato

- Línea terminada en `\n`; se tolera `\r\n`.
- Verbo case-insensitive; el texto de la matriz conserva su case.
- Línea máxima: 128 bytes.
- Timeout de lectura del sketch: 1 segundo.

### Comandos

| Comando | Respuesta | Ejemplo |
|---|---|---|
| `READ <pin>` | `OK 0` / `OK 1` | `READ 13` |
| `WRITE <pin> <0\|1>` | `OK <estado leído>` | `WRITE 13 1` |
| `ANALOG <pin>` | `OK <0-4095>` | `ANALOG A0` |
| `PWM <pin> <0-255>` | `OK <valor>` | `PWM 9 128` |
| `TEMP` | `OK <°C> C (<raw> raw)` | `TEMP` |
| `MATRIX CLEAR` | `OK CLEAR` | — |
| `MATRIX LINE1 <txt>` | `OK LINE1: <txt>` | `MATRIX LINE1 Hola` |
| `MATRIX LINE2 <txt>` | `OK LINE2: <txt>` | `MATRIX LINE2 Mundo` |
| `MATRIX SHOW` / `MATRIX TINY` | `OK TINY` | — |
| `MATRIX TINYSCROLL <txt>` | `OK TINYSCROLL` | — |
| `MATRIX SPEED <10-500>` | `OK SPEED: <ms>ms` | `MATRIX SPEED 50` |
| `MATRIX <txt>` | `OK SCROLL` | `MATRIX Hola` |

### Arranque

Al finalizar `setup()`, el sketch envía `UNOQ_GPIO_READY`. Es la señal que los clientes usan para sincronizar.

### Errores

| Situación | Mensaje |
|---|---|
| Verbo o formato inválido | `ERROR: comando no reconocido` |
| Pin fuera de 0–19 | `ERROR: pin invalido` |
| `ANALOG` en pin no ADC | `ERROR: pin no soporta lectura analogica` |
| `PWM` en pin no PWM | `ERROR: pin no soporta PWM` |
| PWM fuera de 0–255 | `ERROR: valor PWM debe ser 0-255` |
| `MATRIX` sin subcomando | `ERROR: MATRIX requiere subcomando (...)` |
| `TINYSCROLL` sin texto | `ERROR: texto vacio para TINYSCROLL` |
| `SPEED` fuera de rango | `ERROR: velocidad 10-500 ms` |

---

## La matriz LED

### Modos de visualización

| Modo | Comando | Fuente | Comportamiento |
|---|---|---|---|
| Dos líneas estáticas | `MATRIX LINE1` + `LINE2` + `SHOW` | 3×4 propia | Línea 1 en filas 0–3, línea 2 en 4–7 |
| Marquesina centrada | `MATRIX TINYSCROLL <txt>` | 3×4 propia | Scroll horizontal, 2 px de margen arriba y abajo |
| Scroll grande | `MATRIX <txt>` | `Font_5x7` | Ocupa 7 de las 8 filas |

### Caracteres soportados por la fuente 3×4

`0-9`, `A-Z`, `!`, `-`, `.`, `:`, `_` y espacio. Las minúsculas se convierten a mayúsculas. Cualquier otro carácter se dibuja como espacio.

### Capacidad

- ~3 caracteres por línea en modo estático (13 columnas × 4 px por carácter).
- Hasta 64 caracteres en `TINYSCROLL` (tira de 256 columnas).
- `MATRIX SPEED` acepta 10–500 ms por frame; por defecto 70 ms.

### Comportamiento bloqueante

`MATRIX TINYSCROLL` y `MATRIX <texto>` no responden hasta terminar el scroll. Durante ese tiempo los comandos recibidos quedan en el buffer del STM32 y se procesan después. Si tu script tiene timeout de 2 s y mandás un texto largo con velocidad lenta, va a expirar: subí `-t` o bajá la velocidad en ms.

---

## Temperatura y LEDs onboard

### Temperatura — dos caminos

| Camino | Cómo | Precisión | Requiere |
|---|---|---|---|
| `sysfs` | `cat /sys/class/thermal/thermal_zone0/temp` vía ADB | Buena | ADB |
| `TEMP` | ADC1 canal 19 + `TS_CAL1`/`TS_CAL2` | Experimental | Build con canal 19 |

El valor de `sysfs` viene en miligrados: `38200` → 38.2 °C.

Umbrales que usa el menú: ≤ 40 °C normal, 41–55 °C elevada, > 55 °C caliente.

### LEDs onboard

| LED | Color | Uso |
|---|---|---|
| `green:user` | Verde | Usuario — el más seguro para pruebas |
| `red:user` | Rojo | Usuario |
| `blue:user` | Azul | Usuario |
| `green:wlan` | Verde | Actividad Wi-Fi |
| `blue:bt` | Azul | Actividad Bluetooth |
| `red:panic` | Rojo | Kernel panic |

Control:

```bash
echo none > /sys/class/leds/green:user/trigger
echo 255  > /sys/class/leds/green:user/brightness   # encender
echo 0    > /sys/class/leds/green:user/brightness   # apagar
```

`unoq_remote.py` hace exactamente esto con `adb shell`.

---

## Calibración

### ADC

```
voltaje = valor × 3.3 / 4095.0
```

| Valor | Voltaje |
|---|---|
| 0 | 0.00 V |
| 1024 | 0.825 V |
| 2048 | 1.650 V |
| 3072 | 2.475 V |
| 4095 | 3.300 V |

Un pin flotante devuelve ruido (típicamente 50–200). No es una falla.

### PWM

```
duty_% = valor × 100 / 255
```

| Valor | Duty |
|---|---|
| 0 | 0 % |
| 64 | ~25 % |
| 128 | ~50 % |
| 191 | ~75 % |
| 255 | 100 % |

### Temperatura

```
temp = ((raw - TS_CAL1) × (130 − 30)) / (TS_CAL2 - TS_CAL1) + 30
```

`TS_CAL1` en `0x0BFA0710` (30 °C) y `TS_CAL2` en `0x0BFA0742` (130 °C), leídos del flash de fábrica.

---

## Solución de problemas

| Síntoma | Causa | Solución |
|---|---|---|
| `board list` vacío | Cable de carga o regla udev | Cable de datos; regla para `2341:0078` |
| Upload con timeout | ADB no ve la placa | `adb devices`, reconectar, reinstalar core |
| Upload con error de permisos | Falta regla udev | Crear `99-arduino-unoq.rules` y recargar |
| "No se pudo abrir el puerto" | Puerto ocupado | Cerrar el monitor serie |
| No llega `UNOQ_GPIO_READY` | Baud incorrecto o sketch viejo | 115200; recargar firmware |
| `ERROR: pin invalido` | Pin > 19 o `A6`+ | Usar 0–19 / A0–A5 |
| `ERROR: pin no soporta PWM` | Pin sin PWM | 3, 5, 6, 9, 10, 11 |
| ADC con valores raros | Pin flotante | Conectar sensor o pull-down |
| LED no enciende | Polaridad o falta resistencia | Ánodo al pin, cátodo a GND, 220 Ω |
| Matriz con caracteres raros | Fuera del set 3×4 | A-Z, 0-9, `! - . : _` |
| Script bloqueado en TINYSCROLL | Scroll bloqueante | Esperar o subir `--timeout` |
| LEDs onboard no responden | ADB ausente | Instalar `adb`, verificar `adb devices` |
| Temperatura falla por Serial | Canal 19 no expuesto | Usar `sysfs` |
| Placa aparece como `ttyACM1` | Asignación del kernel | `unoq_remote.py` autodetecta; en los otros, usar `-p` |

---

## Compatibilidad con otras placas

| Placa | Nivel | Cambios necesarios |
|---|---|---|
| Arduino UNO Q | Nativa | Ninguno |
| Arduino Uno R3 | Baja | ADC 10 bits, sin matriz, sin Zephyr |
| Arduino Mega 2560 | Baja | Rango de pines distinto, sin matriz |
| Arduino Nano 33 BLE | Media | ADC 12 bits; quitar matriz |
| Arduino Zero | Media | ADC 12 bits; quitar matriz |
| Arduino Due | Media | 3.3 V; quitar matriz |
| Arduino GIGA R1 | Media | Tiene display/matriz distinta; adaptar |

Para portar: eliminar `#include "Arduino_LED_Matrix.h"`, el objeto `matrix` y toda la rama `MATRIX`; el resto del parseo GPIO es C++ estándar.

---

## Límites eléctricos

| Parámetro | Valor |
|---|---|
| Voltaje lógico | 3.3 V |
| Voltaje máximo en un pin | 3.6 V |
| Corriente por pin | 20 mA (recomendado) |
| Corriente total GPIO | 100 mA |
| Corriente del rail 3.3 V | ~500 mA (según variante) |
| Rango del ADC | 0–3.3 V |

No alimentes cargas inductivas desde un GPIO. No inyectes 5 V en un pin. Usá GND común.

---

## Glosario

| Término | Significado |
|---|---|
| **MPU** | Microprocesador de aplicaciones; corre Linux. |
| **MCU** | Microcontrolador; corre Zephyr y controla los pines. |
| **FQBN** | Fully Qualified Board Name; `arduino:zephyr:unoq`. |
| **Bridge** | Capa de RPC entre MPU y MCU. |
| **arduino-router** | Daemon que enruta mensajes MessagePack (TCP 7500). |
| **CDC ACM** | Clase USB que emula un puerto serie. |
| **SWD** | Interfaz de debug de Arm usada para flashear. |
| **OpenOCD** | Servidor de debug que maneja SWD. |
| **ADB** | Android Debug Bridge; acá se usa para entrar al Linux de la placa. |

---

## Licencia

MIT — Copyright (c) 2026 [wanderc137](https://github.com/wanderc137). Sin garantía.
