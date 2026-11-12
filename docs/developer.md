# Guía del desarrollador — UNO Q Lab

**Cómo está construido el código de los dos ejemplos, por qué está así y cómo extenderlo sin romperlo.**

| Campo | Valor |
|---|---|
| Alcance | `blink/unoq_blink/unoq_blink.ino` · `unoq_gpio_control/` (`.ino` + 2 scripts Python) |
| FQBN | `arduino:zephyr:unoq` |
| Core | `arduino:zephyr` (Zephyr RTOS) |
| Librerías | `Arduino_LED_Matrix` 0.1.3 · `ArduinoGraphics` |
| Python | 3.6+ · `pyserial` 3.0+ |
| Licencia | MIT (c) 2026 wanderc137 |

---

## Índice

1. [Modelo mental: dos planos de ejecución](#modelo-mental-dos-planos-de-ejecución)
2. [Mapa del repositorio](#mapa-del-repositorio)
3. [Sistema de build y carga](#sistema-de-build-y-carga)
4. [Ejemplo 1: anatomía de blink](#ejemplo-1-anatomía-de-blink)
5. [Ejemplo 2: arquitectura del sketch](#ejemplo-2-arquitectura-del-sketch)
6. [El parser de comandos](#el-parser-de-comandos)
7. [Subsistema de matriz LED](#subsistema-de-matriz-led)
8. [Temperatura interna](#temperatura-interna)
9. [Clientes Python](#clientes-python)
10. [Flujo completo de un comando](#flujo-completo-de-un-comando)
11. [API de funciones](#api-de-funciones)
12. [Cómo extender](#cómo-extender)
13. [Migrar a Bridge (RPC)](#migrar-a-bridge-rpc)
14. [Pruebas manuales](#pruebas-manuales)
15. [Zephyr vs. AVR](#zephyr-vs-avr)
16. [Decisiones de diseño y deuda técnica](#decisiones-de-diseño-y-deuda-técnica)

---

## Modelo mental: dos planos de ejecución

Hay que separar tres programas que suelen confundirse:

```
┌─ PC host ──────────────────────────────────────────────┐
│  unoq_gpio_control.py   (cliente CLI/REPL)             │
│  unoq_remote.py         (menú + ADB)                   │
└───────────────┬────────────────────────────────────────┘
                │ USB CDC ACM, 115200 8N1, líneas ASCII
┌───────────────▼────────────────────────────────────────┐
│  MCU · STM32U585 · Zephyr                              │
│  unoq_gpio_control.ino  →  parsea y ejecuta            │
│  controla D0–D19, ADC, PWM, matriz 12×8                │
└────────────────────────────────────────────────────────┘

┌─ Placa, lado Linux (MPU · QRB2210) ────────────────────┐
│  Debian · /sys/class/leds · thermal_zone0 · gpiod       │
│  accesible por `adb shell` desde el host                │
└────────────────────────────────────────────────────────┘
```

Los dos planos **no se hablan entre sí en este proyecto**. El sketch no sabe que existe Linux; los LEDs onboard no saben que existe el sketch. El único punto en común es el host, que habla serie con uno y ADB con el otro. Esa independencia es intencional: permite usar el ejemplo 2 aunque el MPU no haya terminado de bootear, y permite tocar los LEDs aunque el sketch esté colgado.

El **Bridge** (sección 13) es la alternativa que sí conecta ambos planos, y se documenta como camino de migración.

---

## Mapa del repositorio

| Ruta | Rol | Se compila |
|---|---|---|
| `blink/unoq_blink/unoq_blink.ino` | Sketch mínimo | Sí |
| `unoq_gpio_control/unoq_gpio_control.ino` | Servidor de comandos | Sí |
| `unoq_gpio_control/unoq_gpio_control.py` | Cliente CLI + REPL | No (script) |
| `unoq_gpio_control/unoq_remote.py` | Menú + ADB | No (script) |
| `unoq_gpio_control/docs/*.md` | Documentación del ejemplo | No |
| `unoq_gpio_control/BITACORA.md` | Registro de desarrollo | No |
| `docs/*.md`, `docs/assets/*.svg` | Documentación raíz | No |

Convención de nombres Arduino: la carpeta debe llamarse igual que el `.ino`. Por eso `blink/unoq_blink/unoq_blink.ino` y no `blink/blink.ino`.

---

## Sistema de build y carga

### Compilación

```bash
arduino-cli compile --fqbn arduino:zephyr:unoq <carpeta_del_sketch>
```

El core `arduino:zephyr` aporta:

- Toolchain Arm GNU para Cortex-M33.
- Zephyr como RTOS y sus drivers (GPIO, ADC, PWM, USB CDC ACM).
- Las capas Arduino (`Arduino.h`, `Serial`, `pinMode`, etc.).
- `Arduino_LED_Matrix` y `ArduinoGraphics` dentro del paquete de hardware.

El sketch **no** incluye `Arduino.h` explícitamente: el preprocesado de Arduino lo agrega.

### Upload

```bash
arduino-cli upload -p /dev/ttyACM0 --fqbn arduino:zephyr:unoq <carpeta>
```

Cadena real:

```
arduino-cli  →  adb  →  Linux de la placa  →  OpenOCD  →  SWD  →  flash del STM32U585
```

Consecuencias para el desarrollo:

1. No hay puerto serie de bootloader: `avrdude` no aplica.
2. Si `adb devices` no lista la placa, el upload falla sin importar el sketch.
3. El flasheo usa programación dual-bank; interrumpirlo puede dejar el firmware inconsistente.
4. El número de serie se puede pasar con `--upload-property upload.port.properties.serialNumber=<SERIAL>`.

### Monitor

```bash
arduino-cli monitor -p /dev/ttyACM0 --config baudrate=115200
# alternativa directa:
stty -F /dev/ttyACM0 115200 && cat /dev/ttyACM0
```

El monitor compite con los scripts Python por el puerto: solo uno a la vez.

---

## Ejemplo 1: anatomía de blink

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

| Elemento | Qué hace en Zephyr |
|---|---|
| `pinMode(pin, OUTPUT)` | Configura el GPIO vía driver de Zephyr; deja de ser alta impedancia |
| `digitalWrite(pin, HIGH)` | Escribe el nivel lógico (3.3 V) |
| `delay(1000)` | `k_sleep()`: duerme el thread 1000 ms y cede el CPU |

No hay `Serial`, así que el sketch no produce salida observable por monitor. La única verificación posible es eléctrica (LED externo) o por instrumento.

**Por qué existe este ejemplo:** aísla las variables. Si `blink` no carga, el problema es toolchain/ADB/placa, nunca el protocolo ni la matriz. Es el primer test de la pirámide.

---

## Ejemplo 2: arquitectura del sketch

### Estructura general

```
┌─────────────── estado global ───────────────┐
│ matrix, linea1[129], linea2[129], tinySpeed │
│ FONT_3X4[96][4] (384 bytes en flash)        │
│ PWM_PINS[6], constantes de protocolo        │
└──────────────────┬──────────────────────────┘
                   │
setup() ───────────┤ Serial 115200
                   │ matrix.begin(), Font_5x7, scroll 100 ms
                   │ 20 pines → INPUT
                   │ 6 pines PWM → OUTPUT + LOW
                   │ delay(500) + "UNOQ_GPIO_READY"
                   │
loop() ────────────┤ Serial.available()? → leerLinea()
                   │   ├─ MATRIX  → subcomandos
                   │   ├─ TEMP    → ADC interno
                   │   └─ GPIO    → READ/WRITE/ANALOG/PWM
                   └─ vuelve a loop()
```

### Estado global

| Variable | Tipo | Tamaño | Propósito |
|---|---|---|---|
| `matrix` | `Arduino_LED_Matrix` | objeto | Canvas 13×8 |
| `linea1`, `linea2` | `char[129]` | 258 B | Texto de cada línea |
| `tinySpeed` | `int` | 4 B | ms por frame de la marquesina (10–500) |
| `FONT_3X4` | `const uint8_t[96][4]` | 384 B | Glifos 3×4, índice ASCII 32–95 |
| `PWM_PINS` | `const int[6]` | 24 B | D3, D5, D6, D9, D10, D11 |

Se usan `char[]` y no `String` en el estado global a propósito: `String` reserva en heap y un firmware que corre días puede fragmentarlo. El parser sí usa `String` porque su vida es corta y la comodidad de `substring`/`trim`/`toInt` compensa.

### `setup()`

```cpp
Serial.begin(115200);
matrix.begin();
matrix.textFont(Font_5x7);
matrix.textScrollSpeed(100);

for (int p = 0; p <= 19; p++) pinMode(p, INPUT);

for (int i = 0; i < 6; i++) {
  pinMode(PWM_PINS[i], OUTPUT);
  digitalWrite(PWM_PINS[i], LOW);
}

delay(500);
Serial.println("UNOQ_GPIO_READY");
```

Detalles:

- **20 pines a INPUT primero.** Estado seguro: nadie queda manejando una salida que no corresponde.
- **Los 6 PWM quedan en OUTPUT LOW desde el arranque.** Excepción deliberada a la regla anterior: son pines de salida por contrato. Si conectás algo ahí, asumí que arranca apagado.
- **`delay(500)`** da tiempo a que el CDC ACM del host se enumere. Sin eso, el `READY` se pierde si el puerto se abre tarde.
- **`matrix.begin()`** toma el control de GPIOF 0 según el device tree; no hay que configurar el pin a mano.

### `loop()`

No hay máquina de estados: cada iteración procesa **una** línea. El bloqueo del scroll es la única excepción. Es un diseño secuencial simple, adecuado para un protocolo de comandos y suficiente para 100 comandos/s.

---

## El parser de comandos

### `leerLinea()`

```cpp
String leerLinea() {
  char buffer[MAX_LINE + 1];        // 129
  int idx = 0;
  unsigned long start = millis();
  const unsigned long TIMEOUT = 1000;

  while (idx < MAX_LINE) {
    if (Serial.available() > 0) {
      char c = Serial.read();
      if (c == '\n') break;
      if (c == '\r') continue;
      buffer[idx++] = c;
      start = millis();             // reset por byte
    } else if (millis() - start > TIMEOUT) {
      break;
    }
  }
  buffer[idx] = '\0';
  return String(buffer);
}
```

| Propiedad | Valor |
|---|---|
| Buffer | 128 caracteres + NUL |
| Delimitador | `\n`; ignora `\r` |
| Timeout | 1 s sin recibir bytes |
| Comportamiento si se llena | Devuelve lo leído; el resto queda para la próxima |

El reset del timeout en cada byte es lo que evita cortar comandos largos que llegan de a poco (USB puede fragmentar).

### Orden de dispatch

```
1. ¿Primer token == "MATRIX"?   → rama matriz, return
2. ¿Primer token == "TEMP"?     → temperatura, return
3. Parseo "CMD PIN [VALOR]"     → GPIO
```

El orden es obligatorio: si `MATRIX` se evaluara después del parser de pines, `MATRIX LINE1 hola` intentaría convertir `LINE1` a número.

### `parsearPin()`

```cpp
int parsearPin(const String &token) {
  String t = token; t.trim();
  if (t.length() == 0) return -1;

  if (t.charAt(0) == 'A' || t.charAt(0) == 'a') {
    String numStr = t.substring(1);
    if (numStr.length() == 0) return -1;      // fix I-001
    int i = numStr.toInt();
    if (i >= 0 && i <= 5) return 14 + i;
    return -1;
  }
  return t.toInt();
}
```

| Entrada | Salida |
|---|---|
| `"13"` | 13 |
| `"A0"` | 14 |
| `"a5"` | 19 |
| `"A"` | −1 |
| `"A6"` | −1 |
| `"abc"` | 0 (comportamiento de `String::toInt`) |

La última fila es una **deuda conocida**: un token no numérico cae en D0 en vez de error. Se dejó así por compatibilidad con el comportamiento preexistente; si lo querés estricto, validá que todos los caracteres sean dígitos antes de convertir.

### Validación y dispatch

```
pin = parsearPin(tokenPin)
if (pin < 0 || pin > 19) → "ERROR: pin invalido"

READ    → digitalRead → "OK 0|1"
WRITE   → valida 0/1/HIGH/LOW → pinMode(OUTPUT) + digitalWrite + readback
ANALOG  → exige 14..19 → analogRead → "OK <0-4095>"
PWM     → exige {3,5,6,9,10,11} → valida 0..255 → analogWrite
default → "ERROR: comando no reconocido"
```

El `readback` de `WRITE` es una decisión útil: devuelve el estado eléctrico real, no el que se quiso escribir. Si el pin está forzado externamente, se nota.

---

## Subsistema de matriz LED

### Canvas y framebuffer

La matriz física es de **12×8**; la librería expone un canvas de **13×8** (una columna extra para el scroll). El framebuffer que consume `loadPixels()` es:

```cpp
uint8_t fb[104];              // 13 columnas × 8 filas
// fb[fila * 13 + columna] = 0 | 1
matrix.loadPixels(fb, sizeof(fb));
```

Es row-major y un byte por píxel (no empaquetado). 104 bytes es un costo trivial y simplifica el render.

### Fuente 3×4

```cpp
static const uint8_t FONT_3X4[96][4] = {
  {2,5,7,5}, // 'A'
  ...
};
```

Cada glifo son **4 bytes = 4 filas**; los **3 bits bajos** de cada byte son las columnas (izquierda a derecha). Ejemplo `'A'`:

```
0b010 = 2   →  . # .
0b101 = 5   →  # . #
0b111 = 7   →  # # #
0b101 = 5   →  # . #
```

`getGlyph()` convierte minúsculas a mayúsculas y manda fuera de rango a espacio. La tabla cubre ASCII 32–95; `a–z` se mapea a `A–Z` restando 32.

### Dos líneas simultáneas (`TINY`)

```cpp
void renderTinyText(const char *texto, uint8_t y_offset, uint8_t *fb) {
  memset(fb + y_offset * 13, 0, 52);   // 4 filas × 13 columnas
  int x = 0;
  while (*texto && x < 13) {
    uint8_t glyph[4];
    getGlyph(*texto, glyph);
    for (int col = 0; col < 3 && (x + col) < 13; col++) {
      uint8_t colBits = 0;
      for (int row = 0; row < 4; row++)
        colBits |= ((glyph[row] >> (2 - col)) & 1) << row;
      for (int row = 0; row < 4; row++)
        fb[(y_offset + row) * 13 + (x + col)] = (colBits >> row) & 1;
    }
    x += 4;   // 3 px de glifo + 1 px de separación
  }
}
```

- Línea 1: `y_offset = 0` (filas 0–3).
- Línea 2: `y_offset = 4` (filas 4–7).
- No hay separación vertical: 4 + 4 = 8 filas exactas.
- Entran 3 caracteres por línea (13 / 4 = 3,25).

### Marquesina 3×4 (`TINYSCROLL`)

```cpp
#define TINYSCROLL_BUF_COLS 256
static uint8_t strip[256 * 4];        // 1 KB estático

// 1. Renderizar todo el texto en una tira de 4 filas × N columnas
// 2. Deslizar una ventana de 13 columnas desde -13 hasta totalCols+13
// 3. Copiar la ventana al framebuffer con y_offset = 2 (centrado)
// 4. loadPixels() + delay(tinySpeed)
```

El `static` evita 1 KB en el stack, que en un RTOS con stack de thread acotado es importante. El texto se recorta a 256 columnas (64 caracteres). El scroll "entra" desde la derecha porque la ventana arranca en `-13`.

### Scroll 5×7 (`MATRIX <texto>`)

Delegado a la librería:

```cpp
matrix.clear();
matrix.beginText(0, 0, 127, 127, 127);
matrix.print(texto);
matrix.endText(SCROLL_LEFT);
```

`endText()` bloquea hasta terminar. La fuente ocupa 7 de 8 filas: no se pueden apilar dos líneas con ella. De ahí la fuente propia.

---

## Temperatura interna

```cpp
#define TEMP_ADC_CHANNEL 19
#define TEMP_CAL1_ADDR   ((uint16_t*)0x0BFA0710UL)  // 30 °C
#define TEMP_CAL2_ADDR   ((uint16_t*)0x0BFA0742UL)  // 130 °C
```

Secuencia:

1. `device_get_binding("ADC1")`.
2. `adc_channel_setup()` con `channel_id = 19`, `ADC_REF_INTERNAL`, `ADC_ACQ_TIME_MAX`.
3. `adc_read()` con resolución 12, `calibrate = 1`; si falla, reintenta con `calibrate = 0`.
4. Lee `TS_CAL1`/`TS_CAL2` del flash y aplica la recta de dos puntos.
5. Responde `OK <temp> C (<raw> raw)`.

Por qué no `analogRead(A0)` con el canal interno: la capa Arduino del core solo mapea los pines externos. Para el sensor interno hay que bajar a la API de Zephyr.

**Estado:** experimental. Depende de que el device tree exponga ADC1 con el canal 19. Si `device_get_binding` devuelve `NULL`, responde `ERROR: ADC no disponible`. El camino estable es `thermal_zone0` por ADB.

---

## Clientes Python

### `unoq_gpio_control.py`

| Función | Firma | Responsabilidad |
|---|---|---|
| `connect_serial` | `(port, baud, timeout) -> Serial` | Abre el puerto, pausa 0.5 s |
| `wait_ready` | `(ser) -> bool` | Espera `UNOQ_GPIO_READY` hasta 2 s |
| `send_command` | `(ser, cmd) -> str` | Escribe `cmd + "\n"`, flush, lee una línea |
| `run_single_command` | `(args)` | Un comando y sale |
| `run_interactive` | `(args)` | REPL de 6 opciones |
| `main` | `()` | `argparse` y dispatch |

Flujo de `run_single_command`:

```
cmd = args.command[0].upper()
params = args.command[1:]
if cmd == "TEXTO": ... (ver deuda técnica)
full_cmd = f"{cmd} {' '.join(params)}"
abrir puerto → wait_ready → send → imprimir "[UNOQ] <resp>" → cerrar
```

`argparse` con `nargs=REMAINDER` permite `MATRIX LINE1 Hola Mundo` sin comillas: cada palabra llega como argumento y se recompone con `" ".join`.

### `unoq_remote.py`

| Función | Responsabilidad |
|---|---|
| `_detectar_puerto()` | Recorre `/dev/ttyACM*`, prueba abrir, devuelve el primero |
| `conectar()` | Asigna el puerto detectado y abre a 115200 |
| `enviar(ser, cmd)` | Envía y devuelve respuesta |
| `limpiar()`, `titulo()`, `esperar()` | Cosmética de terminal |
| `leer_numero(msg, min, max)` | Input validado; `q` cancela |
| `menu_digital()` / `leer_digital()` / `escribir_digital()` | Opción 1 |
| `menu_analogico()` / `leer_adc()` / `escribir_pwm()` | Opción 2 |
| `menu_leds()` + `_adb` / `_liberar_led` / `_led_escribir` / `_led_leer` | Opción 3 (ADB) |
| `menu_texto_matriz()` | Opción 4 |
| `menu_temperatura()` | Opción 5 (sysfs + fallback) |
| `main()` | Menú principal |

Conversiones que hace el cliente y no el firmware:

- ADC → voltaje: `valor / 4095.0 * 3.3`.
- PWM → porcentaje: `duty / 255.0 * 100`.
- Temperatura sysfs: `valor / 1000.0`.
- Barras ASCII de 30 caracteres.

`_adb()` ejecuta `subprocess.run(["adb","shell",cmd], timeout=5)` y devuelve `""` ante cualquier excepción: el menú nunca se cae por ADB.

---

## Flujo completo de un comando

```
Usuario: python3 unoq_gpio_control.py WRITE 13 1
   │
   ├─ argparse → cmd="WRITE", params=["13","1"]
   ├─ connect_serial("/dev/ttyACM0", 115200, 2.0)
   ├─ wait_ready() ← "UNOQ_GPIO_READY"
   ├─ send_command("WRITE 13 1")
   │      │
   │      └─ USB CDC → MCU
   │             ├─ Serial.available() > 0
   │             ├─ leerLinea() → "WRITE 13 1"
   │             ├─ firstToken = "WRITE" ≠ MATRIX/TEMP
   │             ├─ parsearPin("13") → 13
   │             ├─ tokenValor = "1" → HIGH
   │             ├─ pinMode(13, OUTPUT)
   │             ├─ digitalWrite(13, HIGH)
   │             ├─ digitalRead(13) → 1
   │             └─ Serial.println("OK 1")
   │
   ├─ readline() → "OK 1"
   └─ print("[UNOQ] OK 1")
```

Latencia típica: 1–10 ms por round-trip, dominada por la enumeración USB y el timeout de `readline`, no por el MCU.

---

## API de funciones

### Sketch `unoq_gpio_control.ino`

| Función | Firma | Devuelve |
|---|---|---|
| `setup` | `void setup()` | — |
| `loop` | `void loop()` | — |
| `leerLinea` | `String leerLinea()` | Línea sin `\r\n` |
| `parsearPin` | `int parsearPin(const String&)` | 0–19 o −1 |
| `esPinPwm` | `bool esPinPwm(int)` | true si está en la lista |
| `esPinAnalog` | `bool esPinAnalog(int)` | true si 14–19 |
| `ejecutarRead` | `void ejecutarRead(int)` | — (responde) |
| `ejecutarWrite` | `void ejecutarWrite(int,int)` | — |
| `ejecutarAnalog` | `void ejecutarAnalog(int)` | — |
| `ejecutarPwm` | `void ejecutarPwm(int,int)` | — |
| `ejecutarTemp` | `void ejecutarTemp()` | — |
| `responder` | `void responder(const String&)` | — |
| `ejecutarMatrixClear` | `void` | — |
| `ejecutarMatrixLine1/2` | `void(const String&)` | — |
| `ejecutarMatrixShow` | `void` | — (delega a Tiny) |
| `ejecutarMatrixTiny` | `void` | — |
| `ejecutarMatrixTinyScroll` | `void(const String&)` | — |
| `ejecutarMatrixScroll` | `void(const String&)` | — |
| `renderTinyText` | `void(const char*, uint8_t, uint8_t*)` | — |
| `getGlyph` | `static void(char, uint8_t[4])` | — |

### `unoq_gpio_control.py`

Ver tabla de la sección 9. Ninguna función lanza excepciones hacia `main`: los errores de puerto terminan en `sys.exit(1)` con mensaje.

### `unoq_remote.py`

Ver tabla de la sección 9. `main()` captura `KeyboardInterrupt` para salir limpio.

---

## Cómo extender

### Añadir un comando GPIO

Ejemplo: `TOGGLE <pin>`.

```cpp
// 1. Prototipo junto a los demás
void ejecutarToggle(int pin);

// 2. Rama en el dispatch
else if (cmd == "TOGGLE") {
  ejecutarToggle(pin);
}

// 3. Implementación
void ejecutarToggle(int pin) {
  pinMode(pin, OUTPUT);
  int actual = digitalRead(pin);
  int nuevo = (actual == HIGH) ? LOW : HIGH;
  digitalWrite(pin, nuevo);
  responder("OK " + String(nuevo));
}
```

Reglas: validar el pin antes de tocar hardware, responder **siempre** una línea, y no bloquear más de lo necesario.

### Añadir un subcomando MATRIX

```cpp
// Dentro de la rama MATRIX, antes del atajo final
if (payload == "INVERT") {
  uint8_t fb[104];
  for (int i = 0; i < 104; i++) fb[i] = !fb_actual[i];   // requiere tracking
  matrix.loadPixels(fb, sizeof(fb));
  responder("OK INVERT");
  return;
}
```

Ojo: la librería no expone lectura del canvas; si necesitás invertir, mantené tu propio framebuffer espejo.

### Añadir un glifo a la fuente 3×4

Editá `FONT_3X4` en el índice del carácter (32–95). Cada byte es una fila, bits 2..0 son columnas:

```
'@' (64):
  fila 0: 0b010 = 2   . # .
  fila 1: 0b101 = 5   # . #
  fila 2: 0b111 = 7   # # #
  fila 3: 0b010 = 2   . # .
→ {2,5,7,2}
```

Para caracteres fuera de 32–95 (acentos, `ñ`), hay que ampliar la tabla y cambiar `getGlyph()`, que hoy descarta todo lo que no esté en ese rango.

### Añadir una opción al menú

```python
def menu_secuencia(ser):
    limpiar()
    titulo("SECUENCIA DE PRUEBA")
    for cmd, desc in [("WRITE 13 1","LED ON"), ("PWM 9 128","PWM 50%")]:
        print(f"  {desc}: {enviar(ser, cmd)}")
        time.sleep(1)
    esperar()
```

Agregá el `print` en el menú principal y el `elif op == "6"` en el dispatch. Subí el número de la opción de salida.

### Añadir un cliente en otro lenguaje

El protocolo es texto: alcanza con abrir el puerto a 115200, escribir `CMD ...\n` y leer hasta `\n`. En Node:

```js
const { SerialPort } = require('serialport');
const port = new SerialPort({ path: '/dev/ttyACM0', baudRate: 115200 });
port.on('open', () => port.write('READ 13\n'));
port.on('data', d => console.log(d.toString().trim()));
```

---

## Migrar a Bridge (RPC)

El protocolo actual se puede reemplazar por RPC sin tocar la lógica de pines. Del lado MCU:

```cpp
#include <Arduino_RouterBridge.h>

int gpio_read(int pin)  { return digitalRead(pin); }

void gpio_write(int pin, int value) {
  pinMode(pin, OUTPUT);
  digitalWrite(pin, value);
  return digitalRead(pin);
}

int adc_read(int pin)   { return analogRead(pin); }

void setup() {
  Bridge.begin();
  Bridge.provide("gpio_read",  gpio_read);
  Bridge.provide("gpio_write", gpio_write);
  Bridge.provide("adc_read",   adc_read);
}
```

Del lado MPU (`python/main.py` dentro de un app de App Lab):

```python
from arduino.app_utils import Bridge

print(Bridge.call("gpio_read", 13))
Bridge.call("gpio_write", 13, 1)
print(Bridge.call("adc_read", 14))
```

Qué cambia y qué no:

| Aspecto | Serial actual | Bridge |
|---|---|---|
| Validación de pin | En el sketch | En el sketch (recomendado) |
| Formato de mensajes | Texto ASCII | MessagePack binario |
| Descubrimiento | `UNOQ_GPIO_READY` | `$/register` en el router |
| Cliente | PC por USB | Proceso en el MPU |
| Depuración | `cat /dev/ttyACM0` | Logs del router |
| Seguridad | Bus local | TCP 7500 local (no exponer) |

No migres a Bridge si necesitás controlar la placa desde otra máquina sin Linux arriba: el router vive en el MPU.

---

## Pruebas manuales

Checklist mínima antes de dar por bueno un cambio:

| # | Prueba | Esperado |
|---|---|---|
| 1 | `arduino-cli board list` | Placa y FQBN correctos |
| 2 | `compile` | Sin warnings nuevos |
| 3 | `upload` | OpenOCD programa y resetea |
| 4 | Monitor 115200 | `UNOQ_GPIO_READY` |
| 5 | `READ 13` | `OK 0` o `OK 1` |
| 6 | `WRITE 13 1` → `READ 13` | `OK 1`, `OK 1` |
| 7 | `READ A` | `ERROR: pin invalido` |
| 8 | `ANALOG A0` | Número 0–4095 |
| 9 | `ANALOG 13` | Error de ADC |
| 10 | `PWM 9 128` | `OK 128` |
| 11 | `PWM 9 300` | Error de rango |
| 12 | `MATRIX LINE1 Hola` + `LINE2 Mundo` + `SHOW` | Dos líneas |
| 13 | `MATRIX SPEED 30` + `TINYSCROLL Test` | Marquesina rápida |
| 14 | `MATRIX "Hola"` | Scroll 5×7 |
| 15 | `WRITE` tras `MATRIX` | El parser no se corrompe |
| 16 | Desconectar/reconectar USB | El cliente reconecta (o falla limpio) |

No hay suite automatizada. Si agregás una, el punto natural es un script que abra el puerto y compare respuestas literales.

---

## Zephyr vs. AVR

### Compatible

| API | Nota |
|---|---|
| `pinMode`, `digitalRead`, `digitalWrite` | Igual |
| `analogRead` | **12 bits** |
| `analogWrite` | 0–255 |
| `Serial` | USB CDC ACM, no UART |
| `delay` | Duerme el thread |
| `millis` | Tick del sistema |
| `String`, `memset`, `strlen` | Libc estándar |

### No compatible

- `PORTB`, `DDRB`, `PINB`, `TIMSK0`, cualquier registro AVR.
- `ISR(TIMER0_OVF_vect)`, `cli()`, `sei()`.
- `#include <avr/io.h>` y librerías que lo usen.
- `avrdude`, bootloaders optiboot.

### Implicaciones

- **Concurrencia real:** hay scheduler; `delay()` no quema CPU.
- **Overhead de GPIO:** Arduino → Zephyr → HAL → registro. No esperes la latencia de un AVR a 16 MHz, pero sí un jitter mucho menor que en Linux.
- **Device tree:** los periféricos onboard (matriz, ADC interno) se describen ahí; por eso `Arduino_LED_Matrix` "sabe" qué pin usar.
- **Memoria:** 2 MB de flash y 786 KB de SRAM dan aire, pero el sketch comparte región con el resto del firmware.

---

## Decisiones de diseño y deuda técnica

### Decisiones

| Decisión | Motivo | Costo |
|---|---|---|
| Protocolo ASCII | Depurable con `cat`, portable | Más bytes y parsing |
| `String` en parser, `char[]` en estado | Comodidad sin fragmentación | Dos estilos conviviendo |
| `loadPixels()` en vez del motor de texto | Control total, dos líneas | Renderizador propio |
| Fuente 3×4 propia | `Font_5x7` no permite 2 líneas | 384 B de tabla y mantenimiento |
| Scroll bloqueante | Simple, sin scheduler | No atiende comandos durante el scroll |
| Todo INPUT salvo PWM | Seguridad eléctrica | Hay que hacer `WRITE` antes de `READ` útil en un pin de salida |
| `TEMP` vía ADC de Zephyr | Única vía al canal interno | Experimental y dependiente de la build |

### Deuda técnica conocida

| # | Problema | Impacto | Workaround |
|---|---|---|---|
| 1 | `TEXTO --tamano grande` recompone `full_cmd` como `TEXTO …` y el sketch responde error | La opción "grande" del CLI no funciona | Usar `MATRIX <texto>` o el menú de `unoq_remote.py` |
| 2 | `parsearPin("abc")` → 0 | Un typo lee D0 en vez de fallar | Validar dígitos si se necesita estricto |
| 3 | Subcomandos `MATRIX` case-sensitive | `matrix clear` se interpreta como texto | Usar mayúsculas |
| 4 | `MATRIX SHOW` con buffers vacíos responde igual | Sin feedback de "nada que mostrar" | Verificar con `LINE1`/`LINE2` |
| 5 | `TEMP` puede fallar según build | Función no disponible | Usar `sysfs` |
| 6 | Sin autenticación | Cualquiera con el puerto controla pines | No exponer; es bus local |
| 7 | Sin tests automatizados | Regresiones silenciosas | Checklist de la sección 14 |

Documentar la deuda es parte del contrato: quien lea esto sabe exactamente qué está probado y qué no.

---

## Licencia

MIT — Copyright (c) 2026 [wanderc137](https://github.com/wanderc137).
