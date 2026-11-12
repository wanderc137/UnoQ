# Guía del Desarrollador — UNO Q GPIO Control + Matriz LED

## Arquitectura del Sistema

El proyecto sigue una arquitectura **cliente-servidor** sobre comunicación Serial, complementada con acceso directo al Linux embebido de la placa vía ADB para funciones avanzadas (LEDs onboard, temperatura vía sysfs):

```
┌─────────────────────────────────────────────────────────────────────┐
│                            HOST (PC)                                  │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  unoq_gpio_control.py (Cliente Python)                        │   │
│  │                                                               │   │
│  │  • argparse: procesa argumentos de línea de comandos         │   │
│  │  • pyserial: maneja la comunicación Serial                    │   │
│  │  • Modos: comando único / interactivo (6 opciones)            │   │
│  │  • Comando TEXTO: capa de conveniencia para MATRIX           │   │
│  │  • Soporta: READ, WRITE, ANALOG, PWM, MATRIX, TEXTO          │   │
│  │  • Formato de salida: [UNOQ] <respuesta>                     │   │
│  └───────────────────────┬──────────────────────────────────────┘   │
│                          │                                           │
│  ┌───────────────────────┴──────────────────────────────────────┐   │
│  │  unoq_remote.py (Menú interactivo unificado — 5 opciones)    │   │
│  │                                                               │   │
│  │  • Menú principal: Digital | Analógico | LEDs | Texto | Temp │   │
│  │  • Opción 1: Digital — leer/escribir D0-D13                  │   │
│  │  • Opción 2: Analógico — ADC (barra voltaje) + PWM (barra %) │   │
│  │  • Opción 3: LEDs integrados — control vía ADB → sysfs       │   │
│  │  • Opción 4: Texto en matriz — asistente guiado              │   │
│  │    • Elige tamaño (chica/grande), velocidad, texto           │   │
│  │    • Traduce a MATRIX TINYSCROLL o MATRIX <texto>            │   │
│  │  • Opción 5: Temperatura — sysfs (ADB) + fallback Serial     │   │
│  │    • Lee /sys/class/thermal/thermal_zone0/temp vía ADB       │   │
│  │    • Fallback: comando TEMP por Serial                       │   │
│  │    • Barra visual + advertencias contextuales                │   │
│  │  • _detectar_puerto(): busca /dev/ttyACM* automáticamente    │   │
│  └───────────────────────┬──────────────────────────────────────┘   │
│                          │                                           │
│               USB CDC ACM (115200 baud)                              │
│                          │                                           │
└──────────────────────────┼───────────────────────────────────────────┘
                            │
┌──────────────────────────┼───────────────────────────────────────────┐
│                 ARDUINO UNO Q (STM32U585)                            │
│                          │                                           │
│  ┌───────────────────────┴──────────────────────────────────────┐   │
│  │  unoq_gpio_control.ino (Servidor GPIO + Matriz LED)          │   │
│  │                                                               │   │
│  │  setup():                                                     │   │
│  │    Serial.begin(115200)                                       │   │
│  │    matrix.begin() + matrix.textFont(Font_5x7)                │   │
│  │    matrix.textScrollSpeed(100)                                │   │
│  │    Todos los pines como INPUT, PWM pins como OUTPUT           │   │
│  │    → Serial.println("UNOQ_GPIO_READY")                       │   │
│  │                                                               │   │
│  │  loop():                                                      │   │
│  │    leerLinea() → si "MATRIX", rama MATRIX                    │   │
│  │              → si "TEMP", ejecutarTemp()                     │   │
│  │              → si no, parsear GPIO (READ/WRITE/ANALOG/PWM)  │   │
│  │                                                               │   │
│  │  ┌──────────────────────────────────────────────────┐        │   │
│  │  │  Rama MATRIX (7 subcomandos)                     │        │   │
│  │  │  ├─ MATRIX CLEAR       → ejecutarMatrixClear()  │        │   │
│  │  │  ├─ MATRIX LINE1       → ejecutarMatrixLine1()  │        │   │
│  │  │  ├─ MATRIX LINE2       → ejecutarMatrixLine2()  │        │   │
│  │  │  ├─ MATRIX SHOW        → ejecutarMatrixTiny()   │        │   │
│  │  │  ├─ MATRIX TINY        → ejecutarMatrixTiny()   │        │   │
│  │  │  ├─ MATRIX TINYSCROLL  → ejecutarMatrixTinyScroll()  │   │
│  │  │  ├─ MATRIX SPEED <ms>  → configurar tinySpeed    │        │   │
│  │  │  └─ MATRIX <txt>       → ejecutarMatrixScroll() │        │   │
│  │  └──────────────────────────────────────────────────┘        │   │
│  │                                                               │   │
│  │  ┌──────────────────────────────────────────────────┐        │   │
│  │  │  Rama GPIO                                       │        │   │
│  │  │  ├─ READ <pin>    → ejecutarRead(pin)            │        │   │
│  │  │  ├─ WRITE <pin>   → ejecutarWrite(pin, val)      │        │   │
│  │  │  ├─ ANALOG <pin>  → ejecutarAnalog(pin)          │        │   │
│  │  │  └─ PWM <pin>     → ejecutarPwm(pin, val)        │        │   │
│  │  └──────────────────────────────────────────────────┘        │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  Zephyr RTOS                                                         │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  • GPIO driver, USB CDC ACM, ADC 12-bit, PWM                 │   │
│  │  • k_sleep(): implementación de delay()                      │   │
│  │  • Arduino_LED_Matrix: controla GPIOF 0 vía DTS              │   │
│  └──────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Diagrama de Flujo de la Lógica Principal

### Sketch Arduino — `loop()`

```
                       ┌──────────────────────────┐
                       │       loop()              │
                       │                           │
                       │  Serial.available() > 0?  │
                       │         │                 │
                       │    ┌────┴────┐            │
                       │    │ NO      │ SI         │
                       │    ▼         ▼            │
                       │  return   leerLinea()     │
                       │                           │
                       │  ¿línea vacía? ──SÍ──► return
                       │         │                 │
                       │         NO                │
                       │         ▼                 │
                       │  firstToken = primera     │
                       │  palabra en mayúsculas    │
                       │         │                 │
                        │    ┌────┴─────────────┐   │
                        │    │ firstToken        │   │
                        │    │ == "MATRIX"?      │   │
                        │    ├──────┬────────────┤   │
                        │    │ SI   │ NO         │   │
                        │    ▼      ▼            │   │
                        │ ┌──────┐ ┌───────────┐ │   │
                        │ │Rama  │ │¿"TEMP"?   │ │   │
                        │ │MATRIX│ └──┬────┬───┘ │   │
                        │ │      │    │ SI │ NO  │   │
                        │ └──────┘    ▼    ▼     │   │
                        │        ejecutarTemp()  │   │
                        │        Parsear GPIO    │   │
                       └──────────────────────────┘

 Rama MATRIX (ampliada):
 ┌────────────────────────────────────────────────────────────┐
 │  payload = línea sin "MATRIX " (resto del texto)            │
 │                                                             │
 │  ¿payload == ""? ──► ERROR (sin argumentos)                │
 │                                                             │
 │  ¿payload.startsWith("SPEED")?                              │
 │    ├─ sin número → consultar tinySpeed actual               │
 │    └─ con número → validar 10-500 → tinySpeed = valor       │
 │                                                             │
 │  ¿payload == "CLEAR"? ──► ejecutarMatrixClear()            │
 │  ¿payload.startsWith("LINE1")? ──► ejecutarMatrixLine1()   │
 │  ¿payload.startsWith("LINE2")? ──► ejecutarMatrixLine2()   │
 │  ¿payload == "SHOW"? ──► ejecutarMatrixTiny()              │
 │  ¿payload == "TINY"? ──► ejecutarMatrixTiny()              │
 │  ¿payload.startsWith("TINYSCROLL")?                         │
 │    ├─ sin texto → usar linea1 existente                     │
 │    └─ con texto → ejecutarMatrixTinyScroll(texto)           │
 │                                                             │
 │  else ──► ejecutarMatrixScroll(payload)                    │
 │    (atajo: cualquier texto → scroll grande 5×7)            │
 └────────────────────────────────────────────────────────────┘

 Rama GPIO:
 ┌──────────────────────────────────────────────────┐
 │  Buscar primer espacio → cmd (READ/WRITE/etc)    │
 │  Buscar segundo espacio → tokenPin, tokenValor   │
 │                                                   │
 │  pin = parsearPin(tokenPin)                       │
 │  ¿pin válido (0-19)? ──NO──► ERROR pin invalido  │
 │                                                   │
 │  switch(cmd):                                     │
 │    "READ"   → ejecutarRead(pin)                   │
 │    "WRITE"  → validar valor → ejecutarWrite()     │
 │    "ANALOG" → ¿pin analógico? → ejecutarAnalog()  │
 │    "PWM"    → ¿pin PWM? → validar 0-255 → PWM()   │
 │    default  → ERROR comando no reconocido         │
 └──────────────────────────────────────────────────┘
```

### Scripts Python — Flujo de `unoq_remote.py`

```
main()
  │
  ├── conectar() → Serial a /dev/ttyACM0, 115200 baud
  │
  └── while True:  ← Menú principal (4 opciones)
        │
        ├── op "1" → menu_digital(ser)
        │              ├─ 1. Leer pin → leer_digital(ser)
        │              │     └─ enviar("READ {pin}") → muestra HIGH/LOW
        │              └─ 2. Escribir pin → escribir_digital(ser)
        │                    └─ enviar("WRITE {pin} {val}") → confirma
        │
        ├── op "2" → menu_analogico(ser)
        │              ├─ 1. Leer ADC → leer_adc(ser)
        │              │     └─ enviar("ANALOG {pin}") → valor+voltaje+barra
        │              └─ 2. Escribir PWM → escribir_pwm(ser)
        │                    └─ enviar("PWM {pin} {duty}") → %+barra
        │
        ├── op "3" → menu_leds()  ← NO usa Serial (vía ADB)
        │              ├─ Muestra 6 LEDs con estado (🟢/⚫)
        │              ├─ 1-6: submenú por LED
        │              │     ├─ 1. Encender → _led_escribir(nombre, 255)
        │              │     ├─ 2. Apagar  → _led_escribir(nombre, 0)
        │              │     └─ 3. Parpadear → loop ×5 on/off 200ms
        │              ├─ E: encender todos
        │              └─ A: apagar todos
        │
        ├── op "4" → menu_texto_matriz(ser)  ← NUEVO
        │              ├─ Elegir tamaño (1=chica, 2=grande)
        │              ├─ Si chica: elegir velocidad (10-500ms)
        │              ├─ Ingresar texto
        │              └─ Si grande → enviar("MATRIX {texto}")
        │                 Si chica  → enviar("MATRIX SPEED {vel}")
        │                             enviar("MATRIX TINYSCROLL {texto}")
        │
        ├── op "5" → menu_temperatura(ser)  ← NUEVO v3.2
        │              ├─ Intenta ADB: cat /sys/class/thermal/thermal_zone0/temp
        │              │   → temp_c = valor / 1000.0
        │              │   → barra visual + advertencia (normal/elevada/caliente)
        │              └─ Fallback: enviar("TEMP") → parsear respuesta Serial
        │
        └── op "0" → salir
```

---

## Explicación del Código Fuente

### Sketch Arduino (`unoq_gpio_control.ino`)

#### Constantes y Configuración

```cpp
const long BAUD_RATE = 115200;
const int  PIN_MIN   = 0;
const int  PIN_MAX   = 19;
const int  MAX_LINE  = 128;

const int  PWM_PINS[]  = {3, 5, 6, 9, 10, 11};
const int  PWM_COUNT   = 6;

Arduino_LED_Matrix matrix;
char linea1[129] = "";       // Buffer línea 1
char linea2[129] = "";       // Buffer línea 2
int  tinySpeed    = 70;      // Velocidad marquesina (ms, configurable vía SPEED)
```

#### Fuente 3×4 Personalizada (`FONT_3X4`)

Array de 96 glifos × 4 bytes cada uno. Cada glifo tiene 4 filas (top→bottom), 3 bits bajos por fila = columnas (izq→der). Índice = carácter ASCII (32–95). Caracteres no definidos = espacio.

```cpp
static const uint8_t FONT_3X4[96][4] = {
  {0,0,0,0}, // 32 ' '
  {2,2,0,2}, // 33 '!'
  // ...
  {2,5,7,5}, // 65 'A'
  {6,5,6,7}, // 66 'B'
  // ...
};
```

Soporta: `0-9`, `A-Z`, `!`, `-`, `.`, `:`, `_`, espacio. Las minúsculas se convierten a mayúsculas automáticamente en `getGlyph()`.

#### `setup()` — Inicialización

```cpp
void setup() {
  Serial.begin(BAUD_RATE);
  matrix.begin();
  matrix.textFont(Font_5x7);
  matrix.textScrollSpeed(100);

  for (int p = PIN_MIN; p <= PIN_MAX; p++) {
    pinMode(p, INPUT);
  }
  for (int i = 0; i < PWM_COUNT; i++) {
    pinMode(PWM_PINS[i], OUTPUT);
    digitalWrite(PWM_PINS[i], LOW);
  }

  delay(500);
  Serial.println(READY_MSG);
}
```

#### `loop()` — Bucle Principal

El orden de procesamiento es crítico:
1. **Primero** se verifica si es un comando `MATRIX`.
2. **Luego** se verifica si es un comando `TEMP`.
3. **Finalmente** se parsea como comando GPIO.

**Flujo de parsing MATRIX** (7 subcomandos):
1. `payload = linea.substring(6)` → quita "MATRIX ".
2. `payload.trim()`.
3. `SPEED` → configura o consulta `tinySpeed`.
4. `CLEAR` → `ejecutarMatrixClear()`.
5. `LINE1` / `LINE2` → almacena en buffers.
6. `SHOW` / `TINY` → `ejecutarMatrixTiny()` (2 líneas estáticas 3×4).
7. `TINYSCROLL` → `ejecutarMatrixTinyScroll()` (marquesina centrada).
8. Sino → atajo: `ejecutarMatrixScroll(payload)` (scroll grande 5×7).

#### `leerLinea()` — Lectura con Timeout

Buffer acotado a 128 bytes, timeout de 1 segundo con `millis()`, tolera `\r\n`, reset de timeout por byte.

#### `parsearPin()` — Conversión de Token

| Entrada | Salida |
|---|---|
| `"13"` | `13` |
| `"A0"` | `14` |
| `"a5"` | `19` |
| `"A"` | `-1` (inválido) |
| `"A6"` | `-1` (no existe) |

#### Funciones GPIO

- **`ejecutarRead(pin)`**: `digitalRead()` → `OK 0/1`.
- **`ejecutarWrite(pin, valor)`**: `pinMode(OUTPUT)` + `digitalWrite()` + readback.
- **`ejecutarAnalog(pin)`**: `analogRead()` 12-bit → `OK <0-4095>`.
- **`ejecutarPwm(pin, valor)`**: `analogWrite(pin, 0-255)` → `OK <valor>`.

#### Funciones de Temperatura (NUEVO v3.2)

**`ejecutarTemp()`** — Lectura de temperatura interna del STM32U585:

```cpp
#define TEMP_ADC_CHANNEL  19
#define TEMP_CAL1_ADDR    ((uint16_t*)0x0BFA0710UL)  // TS_CAL1 (30°C)
#define TEMP_CAL2_ADDR    ((uint16_t*)0x0BFA0742UL)  // TS_CAL2 (130°C)
#define TEMP_AVG_SLOPE    2.5f   // mV/°C típico del STM32U5

void ejecutarTemp() {
  // 1. Obtener binding del dispositivo ADC1 de Zephyr
  const struct device *adc_dev = device_get_binding("ADC1");

  // 2. Configurar canal 19 (sensor de temperatura interno)
  struct adc_channel_cfg ch_cfg = {
    .gain = ADC_GAIN_1,
    .reference = ADC_REF_INTERNAL,
    .acquisition_time = ADC_ACQ_TIME_MAX,
    .channel_id = TEMP_ADC_CHANNEL,
  };

  // 3. Leer ADC con calibración
  struct adc_sequence seq = {
    .channels = BIT(TEMP_ADC_CHANNEL),
    .resolution = 12,
    .calibrate = 1,
  };
  uint16_t buf = 0;
  seq.buffer = &buf;
  adc_read(adc_dev, &seq);

  // 4. Conversión usando calibración de fábrica
  uint16_t cal1 = *TEMP_CAL1_ADDR;   // Valor ADC @ 30°C
  uint16_t cal2 = *TEMP_CAL2_ADDR;   // Valor ADC @ 130°C
  float temp = ((float)(buf - cal1) * (130.0f - 30.0f))
             / (float)(cal2 - cal1) + 30.0f;
}
```

**Notas importantes**:
- Usa la API nativa de Zephyr (`device_get_binding`, `adc_channel_setup`, `adc_read`) porque `analogRead()` de Arduino solo funciona con pines externos.
- Accede a las direcciones flash de calibración de fábrica (`0x0BFA0710` y `0x0BFA0742`) para interpolar la temperatura.
- **Experimental**: Puede fallar si la build de Zephyr no incluye el driver ADC con el canal 19 habilitado. Errores posibles: `ERROR: ADC no disponible`, `ERROR: config ADC`, `ERROR: lectura ADC`.
- El fallback en `unoq_remote.py` (leer `/sys/class/thermal/thermal_zone0/temp` vía ADB) es más confiable.

#### Funciones de Matriz LED

**`ejecutarMatrixClear()`**:
```cpp
void ejecutarMatrixClear() {
  matrix.clear();
  linea1[0] = '\0';
  linea2[0] = '\0';
  responder("OK CLEAR");
}
```

**`ejecutarMatrixLine1(texto)` / `ejecutarMatrixLine2(texto)`**: Copian texto a `char[129]`.

**`ejecutarMatrixShow()`**: Delega a `ejecutarMatrixTiny()` (dos líneas estáticas 3×4).

**`ejecutarMatrixTiny()`** — **NUEVO** (dos líneas simultáneas):
```cpp
void ejecutarMatrixTiny() {
  uint8_t fb[104] = {0};               // 13×8 = 104 bytes, row-major

  if (strlen(linea1) > 0) {
    renderTinyText(linea1, 0, fb);     // Línea 1: filas 0-3
  }
  if (strlen(linea2) > 0) {
    renderTinyText(linea2, 4, fb);     // Línea 2: filas 4-7
  }

  matrix.loadPixels(fb, sizeof(fb));   // Carga directa al canvas
  responder("OK TINY");
}
```

Usa `matrix.loadPixels()` para cargar un framebuffer de 104 bytes (13 columnas × 8 filas, 1 byte por píxel, row-major order). Cada byte es 0 (apagado) o 1 (encendido).

**`renderTinyText(texto, y_offset, fb)`** — Función auxiliar:
1. Limpia la banda de 4 filas (`memset` de 52 bytes = 13 cols × 4 filas).
2. Itera caracteres, obtiene glifo de 3×4, escribe columnas en el framebuffer.
3. Avance de 4px por carácter (3px glifo + 1px espacio).

**`ejecutarMatrixTinyScroll(texto)`** — **NUEVO** (marquesina centrada 3×4):
```cpp
#define TINYSCROLL_BUF_COLS 256

void ejecutarMatrixTinyScroll(const String &texto) {
  // 1. Pre-renderizar todo el texto en una tira horizontal
  int totalCols = texto.length() * 4;
  static uint8_t strip[TINYSCROLL_BUF_COLS * 4];  // 4 filas × 256 cols

  // Renderizar cada carácter en la tira
  int x = 0;
  for (unsigned int i = 0; i < texto.length(); i++) {
    uint8_t glyph[4];
    getGlyph(texto.charAt(i), glyph);
    for (int col = 0; col < 3 && (x + col) < totalCols; col++) {
      for (int row = 0; row < 4; row++) {
        if (glyph[row] & (1 << (2 - col))) {
          strip[row * totalCols + (x + col)] = 1;
        }
      }
    }
    x += 4;
  }

  // 2. Scroll: deslizar ventana de 13 columnas
  for (int window = -13; window < totalCols + 13; window++) {
    uint8_t fb[104] = {0};
    for (int r = 0; r < 4; r++) {
      for (int c = 0; c < 13; c++) {
        int srcCol = window + c;
        if (srcCol >= 0 && srcCol < totalCols) {
          fb[(2 + r) * 13 + c] = strip[r * totalCols + srcCol];
        }
      }
    }
    matrix.loadPixels(fb, sizeof(fb));
    delay(tinySpeed);  // Configurable vía MATRIX SPEED
  }

  matrix.clear();
  responder("OK TINYSCROLL");
}
```

**Algoritmo**:
1. Pre-renderiza todo el texto en una "tira" de 4 filas × N columnas.
2. Desliza una ventana de 13 columnas de izquierda a derecha sobre la tira.
3. Cada frame: copia la ventana al framebuffer centrado verticalmente (y_offset=2).
4. `delay(tinySpeed)` entre frames (configurable, default 70ms).
5. El texto "entra" desde la derecha y "sale" por la izquierda.

**`ejecutarMatrixScroll(texto)`** — Scroll grande 5×7:
```cpp
void ejecutarMatrixScroll(const String &texto) {
  matrix.clear();
  matrix.beginText(0, 0, 127, 127, 127);
  matrix.print(texto);
  matrix.endText(SCROLL_LEFT);
  responder("OK SCROLL");
}
```

---

### Script Python (`unoq_gpio_control.py`)

#### `connect_serial(port, baud, timeout)` → `Serial`

Abre conexión Serial con pausa de 0.5s para sincronizar con `delay(500)` del sketch.

#### `wait_ready(ser)` → `bool`

Espera `UNOQ_GPIO_READY` hasta 2 segundos. Si no llega, warning pero continúa.

#### `send_command(ser, command)` → `str`

Envía comando + `\n`, flush, lee respuesta hasta `\n` o timeout.

#### Comando TEXTO — Capa de conveniencia

```python
if cmd == "TEXTO":
    texto = " ".join(params)
    if args.tamano == "grande":
        full_cmd = f'MATRIX {texto}'
    else:
        # tiny: configurar velocidad y lanzar marquesina
        ser = connect_serial(...)
        wait_ready(ser)
        send_command(ser, f"MATRIX SPEED {args.velocidad}")
        response = send_command(ser, f"MATRIX TINYSCROLL {texto}")
```

Traducción:
| Comando Python | Serial enviado |
|---|---|
| `TEXTO "hola"` | `MATRIX SPEED 70` → `MATRIX TINYSCROLL hola` |
| `TEXTO --tamano grande "hola"` | `MATRIX hola` |
| `TEXTO --velocidad 30 "hola"` | `MATRIX SPEED 30` → `MATRIX TINYSCROLL hola` |

#### `run_single_command(args)`

Construye `full_cmd` a partir de `args.command[0]` + `args.command[1:]`. Para `MATRIX`, `args.command = ["MATRIX", "LINE1", "Hola Mundo"]` → `full_cmd = "MATRIX LINE1 Hola Mundo"`.

#### `run_interactive(args)`

Menú de 6 opciones:
1. **Imprimir texto** — asistente de tamaño/velocidad/texto → `TINYSCROLL` o `MATRIX <texto>`.
2. **Control de pines** — sub-REPL con prompt `pin>` para READ/WRITE.
3. **Lectura analógica** — sub-REPL con prompt `adc>` para ANALOG.
4. **Control PWM** — sub-REPL con prompt `pwm>` para PWM.
5. **Comandos MATRIX** — sub-REPL con prompt `matrix>` para acceso directo a todos los subcomandos.
6. **Salir**.

### Script Python (`unoq_remote.py`) — Arquitectura del Menú

#### Estructura de funciones

| Función | Propósito |
|---|---|
| `conectar()` | Abre Serial `/dev/ttyACM0` 115200, `reset_input_buffer()` |
| `enviar(ser, cmd)` | Envía comando, retorna respuesta |
| `limpiar()` | `clear` / `cls` para limpiar terminal |
| `titulo(texto)` | Renderiza encabezado con bordes ╔═╗ |
| `esperar()` | Pausa hasta ENTER |
| `leer_numero(mensaje, min, max)` | Input numérico validado con cancelación (`q`) |

#### Opción 1 — `menu_digital(ser)`

```
menu_digital(ser)
  ├─ leer_digital(ser): pin 0-13 → READ → HIGH(1)/LOW(0)
  └─ escribir_digital(ser): pin + 0/1 → WRITE → confirma
```

#### Opción 2 — `menu_analogico(ser)`

```
menu_analogico(ser)
  ├─ leer_adc(ser): pin A0-A5 → ANALOG → valor+voltaje+barra [████    ]
  └─ escribir_pwm(ser): pin PWM + 0-255 → PWM → %+barra [████    ]
```

**Barra de voltaje**: `"█" * int(valor / 4095 * 30)` (30 caracteres de ancho).
**Barra de PWM**: `"█" * int(duty / 255 * 30)` + porcentaje.

#### Opción 3 — `menu_leds()` (vía ADB, sin Serial)

```python
LEDS = {
    "1": ("green:user",  "Verde usuario"),
    "2": ("red:user",    "Rojo usuario"),
    "3": ("blue:user",   "Azul usuario"),
    "4": ("green:wlan",  "Verde WiFi"),
    "5": ("red:panic",   "Rojo panic"),
    "6": ("blue:bt",     "Azul Bluetooth"),
}

def _adb(cmd):
    subprocess.run(["adb", "shell", cmd], capture_output=True, text=True, timeout=5)

def _liberar_led(nombre):
    _adb(f"echo none > /sys/class/leds/{nombre}/trigger")

def _led_escribir(nombre, valor):
    _adb(f"echo {valor} > /sys/class/leds/{nombre}/brightness")
```

Flujo:
1. `_liberar_led(nombre)` — suelta el LED del kernel (`trigger = none`).
2. `_led_escribir(nombre, "255")` — enciende.
3. `_led_escribir(nombre, "0")` — apaga.
4. Parpadeo: loop ×5: encender 200ms → apagar 200ms.

#### Opción 4 — `menu_texto_matriz(ser)` (NUEVO)

```python
def menu_texto_matriz(ser):
    # Paso 1: Elegir tamaño
    print("  1. Chica (3×4)  — centrada, con márgenes")
    print("  2. Grande (5×7) — ocupa toda la altura")
    tam = input("  Opción [1-2] > ")
    fuente = "grande" if tam == "2" else "tiny"

    # Paso 2: Velocidad (solo fuente chica)
    vel = 70
    if fuente == "tiny":
        vel_str = input("  Velocidad [10-500 ms] (default: 70) > ")
        if vel_str.isdigit() and 10 <= int(vel_str) <= 500:
            vel = int(vel_str)

    # Paso 3: Texto
    texto = input("  Texto a mostrar: ")

    # Paso 4: Enviar comando
    if fuente == "grande":
        resp = enviar(ser, f"MATRIX {texto}")
    else:
        enviar(ser, f"MATRIX SPEED {vel}")
        resp = enviar(ser, f"MATRIX TINYSCROLL {texto}")
```

**Lógica de traducción**:
- Fuente grande → `MATRIX <texto>` (scroll con Font_5x7).
- Fuente chica → `MATRIX SPEED <vel>` + `MATRIX TINYSCROLL <texto>`.

#### Opción 5 — `menu_temperatura(ser)` (NUEVO v3.2)

```python
def menu_temperatura(ser):
    # Método 1: Leer vía Linux sysfs (ADB)
    temp_str = _adb("cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null")
    if temp_str and temp_str.isdigit():
        temp_c = float(temp_str) / 1000.0  # sysfs reporta en miligrados
        barra = "█" * min(int((temp_c - 15) / 45 * 30), 30)
        print(f"  Temperatura: {temp_c:.1f} °C")
        print(f"  [{barra}...]")  # barra visual
        if temp_c > 55:
            print("  ¡Caliente! El chip está a {:.0f}°C")
        elif temp_c > 40:
            print("  Temperatura elevada")
        else:
            print("  Temperatura normal")
        return

    # Método 2: Fallback — intentar vía Serial (comando TEMP)
    resp = enviar(ser, "TEMP")
    # ...
```

**Lógica de dos vías**:
1. **Vía rápida (ADB → sysfs)**: Lee directamente del kernel Linux embebido. Más rápido y preciso. No depende del sketch.
2. **Fallback (Serial → TEMP)**: Si ADB no está disponible, envía `TEMP\n` al sketch, que usa el ADC interno con calibración de fábrica.

#### Auto-Detección de Puerto — `_detectar_puerto()` (NUEVO v3.2)

```python
import glob

def _detectar_puerto():
    """Busca automáticamente cualquier /dev/ttyACM* disponible."""
    for p in glob.glob("/dev/ttyACM*"):
        try:
            s = serial.Serial(p, BAUD, timeout=1)
            s.close()
            return p
        except:
            pass
    return "/dev/ttyACM0"  # fallback por defecto
```

**Uso en `conectar()`**:
```python
def conectar():
    global PORT
    PORT = _detectar_puerto()  # ← busca automáticamente
    try:
        ser = serial.Serial(PORT, BAUD, timeout=2)
        time.sleep(1)
        ser.reset_input_buffer()
        print(f"\n  Conectado a {PORT}")  # ← muestra puerto detectado
        return ser
    except Exception as e:
        # ...
```

**Ventajas**:
- Si el kernel asigna `ttyACM1` o `ttyACM2` en lugar de `ttyACM0`, el script lo encuentra automáticamente.
- Ya no es necesario editar manualmente la variable `PORT` en el código fuente.

---

## API de Funciones

### Sketch Arduino

| Función | Firma | Descripción |
|---|---|---|
| `setup()` | `void setup()` | Inicializa Serial, matriz LED, configura pines, envía READY |
| `loop()` | `void loop()` | Bucle principal: lectura, parsing MATRIX/GPIO, dispatch |
| `leerLinea()` | `String leerLinea()` | Lee bytes del Serial hasta `\n` o timeout 1s |
| `parsearPin()` | `int parsearPin(const String &token)` | "13"→13, "A0"→14, "a5"→19, inválido→-1 |
| `esPinPwm()` | `bool esPinPwm(int pin)` | Verifica {3,5,6,9,10,11} |
| `esPinAnalog()` | `bool esPinAnalog(int pin)` | Verifica {14–19} |
| `ejecutarRead()` | `void ejecutarRead(int pin)` | `digitalRead()` → `OK 0/1` |
| `ejecutarWrite()` | `void ejecutarWrite(int pin, int valor)` | `pinMode(OUTPUT)` + `digitalWrite()` + readback |
| `ejecutarAnalog()` | `void ejecutarAnalog(int pin)` | `analogRead()` 12-bit → `OK <0-4095>` |
| `ejecutarPwm()` | `void ejecutarPwm(int pin, int valor)` | `analogWrite(pin, 0-255)` → `OK <valor>` |
| `ejecutarTemp()` | `void ejecutarTemp()` | Lee ADC1 canal 19, convierte con calibración fábrica → `OK XX.X C (YYYY raw)` (v3.2) |
| `ejecutarMatrixClear()` | `void ejecutarMatrixClear()` | `matrix.clear()`, vacía buffers → `OK CLEAR` |
| `ejecutarMatrixLine1()` | `void ejecutarMatrixLine1(const String &texto)` | Almacena en `linea1` → `OK LINE1: <texto>` |
| `ejecutarMatrixLine2()` | `void ejecutarMatrixLine2(const String &texto)` | Almacena en `linea2` → `OK LINE2: <texto>` |
| `ejecutarMatrixShow()` | `void ejecutarMatrixShow()` | Delega a `ejecutarMatrixTiny()` |
| `ejecutarMatrixTiny()` | `void ejecutarMatrixTiny()` | Renderiza 2 líneas 3×4 en framebuffer, `loadPixels()` → `OK TINY` |
| `ejecutarMatrixTinyScroll()` | `void ejecutarMatrixTinyScroll(const String &texto)` | Pre-renderiza tira, desliza ventana centrada → `OK TINYSCROLL` |
| `ejecutarMatrixScroll()` | `void ejecutarMatrixScroll(const String &texto)` | Scroll con Font_5x7 → `OK SCROLL` |
| `renderTinyText()` | `void renderTinyText(const char *texto, uint8_t y_offset, uint8_t *fb)` | Renderiza texto 3×4 en banda del framebuffer |
| `getGlyph()` | `static void getGlyph(char c, uint8_t glyph[4])` | Convierte carácter a glifo 3×4, mayúsculas automáticas |
| `responder()` | `void responder(const String &msg)` | `Serial.println(msg)` |

### Script Python (`unoq_gpio_control.py`)

| Función | Firma | Descripción |
|---|---|---|
| `connect_serial()` | `connect_serial(port, baud, timeout) -> Serial` | Abre conexión Serial |
| `wait_ready()` | `wait_ready(ser) -> bool` | Espera `UNOQ_GPIO_READY` |
| `send_command()` | `send_command(ser, command) -> str` | Envía comando, retorna respuesta |
| `run_single_command()` | `run_single_command(args)` | Modo comando único, soporta TEXTO |
| `run_interactive()` | `run_interactive(args)` | Menú de 6 opciones |
| `main()` | `main()` | Entry point: argparse → dispatch |

### Script Python (`unoq_remote.py`)

| Función | Firma | Descripción |
|---|---|---|
| `conectar()` | `conectar() -> Serial` | Abre Serial, `reset_input_buffer()` |
| `enviar()` | `enviar(ser, cmd) -> str` | Envía comando, retorna respuesta |
| `limpiar()` | `limpiar()` | Limpia terminal |
| `titulo()` | `titulo(texto)` | Renderiza encabezado ╔═╗ |
| `esperar()` | `esperar()` | Pausa hasta ENTER |
| `leer_numero()` | `leer_numero(msg, min, max) -> int\|None` | Input validado con cancelación |
| `menu_digital()` | `menu_digital(ser)` | Submenú digital (leer/escribir) |
| `leer_digital()` | `leer_digital(ser)` | READ + muestra HIGH/LOW |
| `escribir_digital()` | `escribir_digital(ser)` | WRITE + confirma |
| `menu_analogico()` | `menu_analogico(ser)` | Submenú analógico (ADC/PWM) |
| `leer_adc()` | `leer_adc(ser)` | ANALOG + voltaje + barra |
| `escribir_pwm()` | `escribir_pwm(ser)` | PWM + % + barra |
| `menu_leds()` | `menu_leds()` | Submenú LEDs vía ADB |
| `_adb()` | `_adb(cmd) -> str` | Ejecuta comando en Linux de la placa |
| `_liberar_led()` | `_liberar_led(nombre)` | `trigger = none` |
| `_led_escribir()` | `_led_escribir(nombre, valor)` | `brightness = valor` |
| `_led_leer()` | `_led_leer(nombre) -> str` | Lee `brightness` |
| `menu_texto_matriz()` | `menu_texto_matriz(ser)` | **NUEVO** — asistente de texto en matriz |
| `menu_temperatura()` | `menu_temperatura(ser)` | **NUEVO v3.2** — lee temp vía ADB (sysfs) con fallback Serial TEMP |
| `_detectar_puerto()` | `_detectar_puerto() -> str` | **NUEVO v3.2** — busca automáticamente /dev/ttyACM* disponible |
| `main()` | `main()` | Menú principal 5 opciones |

---

## Guía de Modificación y Extensión

### Cómo Agregar un Nuevo Comando GPIO

Ejemplo: comando `TOGGLE <pin>`:

```cpp
// 1. Prototipo
void ejecutarToggle(int pin);

// 2. Rama en loop() (después de los else if de GPIO)
else if (cmd == "TOGGLE") {
  ejecutarToggle(pin);
}

// 3. Implementación
void ejecutarToggle(int pin) {
  pinMode(pin, OUTPUT);
  int current = digitalRead(pin);
  int newState = (current == HIGH) ? LOW : HIGH;
  digitalWrite(pin, newState);
  responder("OK " + String(newState));
}
```

### Cómo Agregar un Nuevo Subcomando MATRIX

Ejemplo: `MATRIX INVERT` que invierte los píxeles:

```cpp
// En loop(), dentro de la rama MATRIX:
if (payload == "INVERT") {
  ejecutarMatrixInvert();
  return;
}

// Implementación:
void ejecutarMatrixInvert() {
  uint8_t fb[104];
  // Leer estado actual (requiere soporte de la librería o tracking manual)
  // ... invertir bits ...
  matrix.loadPixels(fb, sizeof(fb));
  responder("OK INVERT");
}
```

### Cómo Agregar una Nueva Opción al Menú de unoq_remote.py

Ejemplo: opción 6 "Secuencia de prueba":

```python
def menu_test_sequence(ser):
    limpiar()
    titulo("SECUENCIA DE PRUEBA")
    print("  Ejecutando secuencia de prueba...\n")

    tests = [
        ("WRITE 13 1", "LED D13 ON"),
        ("PWM 9 128", "PWM D9 50%"),
        ("MATRIX TINYSCROLL Test OK!", "Matriz LED"),
    ]
    for cmd, desc in tests:
        resp = enviar(ser, cmd)
        print(f"  {desc}: {resp}")
        time.sleep(1)

    esperar()

# En main(), agregar al menú:
print("  5. Secuencia de prueba")
# Y en el dispatch:
elif op == "5":
    menu_test_sequence(ser)
```

### Cómo Agregar un Nuevo Glifo a la Fuente 3×4

Editar `FONT_3X4` en el sketch. Cada glifo son 4 bytes (4 filas, 3 bits bajos = columnas):

```cpp
// Ejemplo: carácter '@' (índice 64)
{2,5,7,2}, // 64 '@' →  ■□■
           //            ■□■
           //            ■■■
           //            ■□■
```

Formato visual para diseñar:
```
Byte 0 (fila 0): bits[2:0] = columnas 0,1,2  →  010 = 2
Byte 1 (fila 1): bits[2:0] = columnas 0,1,2  →  101 = 5
Byte 2 (fila 2): bits[2:0] = columnas 0,1,2  →  111 = 7
Byte 3 (fila 3): bits[2:0] = columnas 0,1,2  →  010 = 2
```

---

## Notas sobre Zephyr RTOS y Diferencias con Arduino AVR

### APIs Compatibles

| API Arduino | Comportamiento en Zephyr (UNO Q) | Diferencias con AVR |
|---|---|---|
| `pinMode()` | `INPUT`, `OUTPUT`, `INPUT_PULLUP` | Igual |
| `digitalRead()` | `HIGH` o `LOW` | Igual |
| `digitalWrite()` | `HIGH` o `LOW` | Igual |
| `analogRead()` | **12 bits (0–4095)** | 10 bits (0–1023) en AVR |
| `analogWrite()` | PWM 8-bit (0–255) | Igual |
| `Serial` | USB CDC ACM | UART hardware en AVR |
| `delay(ms)` | `k_sleep()` — duerme el thread | Busy-wait en AVR |
| `millis()` | System tick de Zephyr | Timer0 en AVR |
| `memset()` | Estándar C | Igual |
| `strlen()` | Estándar C | Igual |

### APIs NO Compatibles

- **Registros AVR**: `PORTB`, `DDRB`, `PINB` — **no existen**.
- **Interrupciones bare-metal**: `ISR()`, `cli()`, `sei()` — **no disponibles**.
- **Timers hardware**: Configuración directa **no funciona**.
- **Librerías AVR-specific**: Cualquier `#include <avr/...>` **no compila**.

### Implicaciones de Zephyr RTOS

- **Concurrencia real**: Múltiples threads en paralelo.
- **`delay()` cede el control**: El thread se duerme, no busy-wait.
- **Mayor overhead en GPIO**: Capas de abstracción (Arduino → Zephyr → HAL → HW).

### Arduino_LED_Matrix y Zephyr

- v0.1.3, `architectures=zephyr`. Diseñada exclusivamente para UNO Q.
- Usa `__RBIT` del Cortex-M33 para operaciones bitmap.
- Controla GPIOF 0 vía Device Tree.
- **Sin conflicto** con pines GPIO 0–19.

### `matrix.loadPixels()` — API clave para renderizado personalizado

```cpp
uint8_t fb[104];  // 13 columnas × 8 filas, row-major
// fb[row * 13 + col] = 1  → píxel encendido
// fb[row * 13 + col] = 0  → píxel apagado
matrix.loadPixels(fb, sizeof(fb));
```

Esta API permite bypass del sistema de texto de `ArduinoGraphics` y escribir directamente en el canvas de la matriz. Es la base de `ejecutarMatrixTiny()` y `ejecutarMatrixTinyScroll()`.

---

## Dependencias y Versiones

| Componente | Versión mínima | Versión probada |
|---|---|---|
| `arduino-cli` | 0.35.0 | 0.35.0+ |
| Core `arduino:zephyr` | Última estable | 0.90.0 |
| `Arduino_LED_Matrix` | 0.1.3 | 0.1.3 |
| `ArduinoGraphics` | (incluida en core) | — |
| Python | 3.6 | 3.10+ |
| `pyserial` | 3.0 | 3.5 |
| ADB | Cualquiera | Platform-tools |

---

## Estructura de Archivos y Convenciones

```
unoq_gpio_control/
├── unoq_gpio_control.ino    # Sketch Arduino — servidor de comandos
├── unoq_gpio_control.py     # Cliente Python — comandos Serial (modo único + interactivo)
├── unoq_remote.py           # Menú interactivo unificado (5 opciones)
├── README.md                # Documentación principal
├── BITACORA.md              # Bitácora de desarrollo
├── PLAN.md                  # Plan de implementación
├── AUDIT_REPORT.md          # Informe de auditoría
├── .gitignore
└── docs/
    ├── datasheet.md         # Documentación de usuario
    └── developer.md         # Guía del desarrollador (este archivo)
```

**Convenciones de código:**
- **C++ (Arduino)**: camelCase para funciones, UPPER_SNAKE_CASE para constantes, 2 espacios de indentación.
- **Python**: snake_case para funciones, UPPER_SNAKE_CASE para constantes, type hints, 4 espacios.
- **Comentarios**: En español, explicando el "por qué".
- **Buffers de texto**: `char[N]` en vez de `String` para variables globales (evita fragmentación de heap).
- **Framebuffer 13×8**: 104 bytes, row-major (`fb[row * 13 + col]`).

## Licencia y Contribuciones

Este proyecto es de código abierto. Para contribuir:

1. Asegúrate de que los cambios sean compatibles con Zephyr RTOS.
2. No uses APIs específicas de AVR (registros, interrupciones bare-metal).
3. Mantén el protocolo de comandos hacia atrás compatible.
4. Actualiza la documentación (README.md, datasheet.md, developer.md).
5. Agrega casos de prueba para nuevas funcionalidades.
6. Verifica compilación con `arduino-cli compile --fqbn arduino:zephyr:unoq .`
7. La rama MATRIX debe ejecutarse **antes** que el parseo GPIO en `loop()`.
