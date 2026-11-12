# Referencias — UNO Q Lab

Enlaces usados para construir y verificar este repositorio, con una nota sobre **para qué sirve cada uno**. No es una lista decorativa: cada entrada responde a una pregunta concreta que apareció durante el desarrollo.

> **Criterio de honestidad:** los enlaces marcados con ✅ fueron consultados durante la elaboración de esta documentación. Los marcados con 📚 son referencias generales recomendadas para profundizar, no necesariamente verificadas en esta sesión.

---

## 1. La placa

| Recurso | Enlace | Para qué sirve |
|---|---|---|
| Página oficial de la UNO Q ✅ | <https://docs.arduino.cc/hardware/uno-q> | Specs de ambos núcleos, variantes de RAM, conectividad, enlaces a pinout y esquemático |
| User Manual ✅ | <https://docs.arduino.cc/tutorials/uno-q/user-manual> | Guía oficial de uso; complementa este repositorio con el punto de vista del fabricante |
| Pinout PDF (ABX00162) 📚 | <https://docs.arduino.cc/resources/pinouts/ABX00162-full-pinout.pdf> | Mapa físico definitivo de los headers; consultar antes de cablear algo nuevo |
| Esquemático (ABX00162) 📚 | <https://docs.arduino.cc/resources/schematics/ABX00162-schematics.pdf> | Ver pull-ups, protecciones y rieles reales; imprescindible si vas a soldar |
| Foro UNO Q 📚 | <https://forum.arduino.cc/c/hardware/uno-familyd/uno-q/222> | Casos raros de la comunidad que no están en la documentación |
| Repositorio de docs ✅ | <https://github.com/arduino/docs-content> | Fuente de la documentación oficial; útil para ver cambios recientes |

### Qué se confirmó acá

- MPU **Qualcomm Dragonwing QRB2210**: 4× Cortex-A53 @ 2.0 GHz, GPU Adreno, 2× ISP.
- MCU **STM32U585**: Cortex-M33 @ 160 MHz, 2 MB flash, **786 KB SRAM**, FPU.
- Debian Linux como sistema del MPU.
- Wi-Fi 5 dual-band + Bluetooth 5.1 (módulo WCBN3536A).
- Existencia de la librería RPC integrada ("Arduino Bridge").

---

## 2. Entorno de desarrollo

| Recurso | Enlace | Para qué sirve |
|---|---|---|
| Arduino App Lab ✅ | <https://www.arduino.cc/en/software> | Descarga del entorno híbrido (MPU + MCU) |
| Quickstart de App Lab ✅ | <https://docs.arduino.cc/software/app-lab/getting-started/quickstart/> | Primer proyecto con Python + sketch + Bridge |
| Arduino CLI 📚 | <https://arduino.github.io/arduino-cli/> | Referencia de `compile`, `upload`, `monitor`, `board list` |
| Core `arduino:zephyr` 📚 | <https://github.com/arduino/arduino-zephyr> | Código del core; sirve para entender qué hay debajo de `pinMode()` |
| Arduino IDE 2 📚 | <https://www.arduino.cc/en/software> | Alternativa gráfica para programar solo el MCU |

### Comandos que salen de acá

```bash
arduino-cli core install arduino:zephyr
arduino-cli compile --fqbn arduino:zephyr:unoq .
arduino-cli upload -p /dev/ttyACM0 --fqbn arduino:zephyr:unoq .
```

---

## 3. RPC entre MPU y MCU

| Recurso | Enlace | Para qué sirve |
|---|---|---|
| `arduino-router` ✅ | <https://github.com/arduino/arduino-router> | Router MessagePack: protocolo `$/register`, topología en estrella, conexión serie, límites de mensaje |
| `arduino-router` README ✅ | <https://github.com/arduino/arduino-router/blob/main/README.md> | Detalle de los métodos del router y del manejo de IDs |
| MessagePack ✅ | <https://msgpack.org/> | Formato binario que usa el RPC; útil para depurar tramas |
| Documentación de Bridge 📚 | <https://docs.arduino.cc/software/app-lab/> | API `Bridge.call` / `Bridge.provide` en el contexto de App Lab |

### Qué se confirmó acá

- El router es un proceso en **Go**, licencia **GPL-3.0**, con topología en estrella.
- Expone `$/register`, `$/unregister`, `$/reset`, `$/serial/open`, `$/serial/close`, `$/setMaxMsgSize`.
- Remapea los IDs de mensaje para que no colisionen entre clientes.
- Si un cliente se desconecta, sus rutas se eliminan.
- El puerto serie se especifica con `-p PORT` y se reintenta cada 5 segundos.

**Puerto TCP 7500:** es el valor por defecto del servicio en la UNO Q (`127.0.0.1:7500`). Es un bus local: no debe exponerse a la red.

---

## 4. Firmware y librerías del MCU

| Recurso | Enlace | Para qué sirve |
|---|---|---|
| Zephyr Project ✅ | <https://zephyrproject.org> | RTOS del MCU; punto de entrada |
| Zephyr Docs 📚 | <https://docs.zephyrproject.org/latest/> | API de GPIO, ADC, PWM, USB CDC ACM, device tree |
| `Arduino_LED_Matrix` 📚 | <https://github.com/arduino/Arduino_LED_Matrix> | Matriz 12×8: `begin`, `loadPixels`, `beginText`, `endText` |
| `ArduinoGraphics` 📚 | <https://github.com/arduino/ArduinoGraphics> | Canvas y fuentes (`Font_5x7`) usadas por la matriz |
| STM32U585 — página de producto ✅ | <https://www.st.com/en/microcontrollers-microprocessors/stm32u585ai.html> | Familia, memorias, periféricos |
| STM32U585 — datasheet 📚 | <https://www.st.com/resource/en/datasheet/stm32u585ai.pdf> | Canales ADC, `TS_CAL1`/`TS_CAL2`, direcciones de calibración |

### Puntos concretos que resolved estos enlaces

- `loadPixels()` acepta un framebuffer de **13×8 bytes** (row-major, 1 byte por píxel). Es la base de la fuente 3×4.
- El canal **19** del ADC1 es el sensor de temperatura interno.
- Las constantes de calibración de fábrica viven en `0x0BFA0710` (30 °C) y `0x0BFA0742` (130 °C).
- `delay()` en Zephyr es `k_sleep()`, no busy-wait.

---

## 5. Host: Python y USB

| Recurso | Enlace | Para qué sirve |
|---|---|---|
| `pyserial` ✅ | <https://pypi.org/project/pyserial/> | API `Serial`, `readline`, `timeout`, `reset_input_buffer` |
| Documentación de `pyserial` 📚 | <https://pyserial.readthedocs.io/> | Detalles de configuración de puerto y plataformas |
| ADB (Android Platform Tools) ✅ | <https://developer.android.com/tools/adb> | `adb devices`, `adb shell`, `adb forward`; camino de carga y acceso al Linux |
| Reglas udev 📚 | <https://wiki.archlinux.org/title/udev> | Permisos de `/dev/ttyACM*`; base de la regla para `2341:0078` |

### Diagnóstico rápido

```bash
python3 -c "import serial; print(serial.__version__)"
adb devices
ls -l /dev/ttyACM*
```

---

## 6. Linux embebido (MPU)

| Recurso | Enlace | Para qué sirve |
|---|---|---|
| Debian ✅ | <https://www.debian.org> | Base del sistema del MPU |
| `sysfs` LEDs 📚 | <https://www.kernel.org/doc/html/latest/leds/leds-class.html> | `trigger` y `brightness` en `/sys/class/leds` |
| `thermal` sysfs 📚 | <https://www.kernel.org/doc/html/latest/driver-api/thermal/sysfs-api.html> | `thermal_zone0/temp` en miligrados |
| libgpiod 📚 | <https://git.kernel.org/pub/scm/libs/libgpiod/libgpiod.git/> | `gpiodetect`, `gpioinfo`, `gpioget`, `gpioset` |
| Qualcomm QRB2210 ✅ | <https://www.qualcomm.com/products/internet-of-things/robotics-processors/qrb2210> | Specs del MPU (Cortex-A53, GPU, ISP) |

---

## 7. Documentación del propio repositorio

| Documento | Ruta | Contenido |
|---|---|---|
| README raíz | [`../README.md`](../README.md) | Vista general, arquitectura, ambos ejemplos |
| Datasheet raíz | [`datasheet.md`](datasheet.md) | Manual de usuario integrado |
| Guía de desarrollo raíz | [`developer.md`](developer.md) | Código, API, extensión, deuda técnica |
| README del ejemplo | [`../unoq_gpio_control/README.md`](../unoq_gpio_control/README.md) | Protocolo completo y uso detallado |
| Bitácora | [`../unoq_gpio_control/BITACORA.md`](../unoq_gpio_control/BITACORA.md) | Hallazgos, errores y correcciones sobre hardware real |

---

## 8. Lectura recomendada, en orden

1. **Empezar:** página oficial de la UNO Q y quickstart de App Lab.
2. **Entender el modelo:** README de `arduino-router` (sección 3) y la explicación de Bridge.
3. **Tocar hardware:** pinout PDF y esquemático.
4. **Profundizar firmware:** docs de Zephyr (GPIO/ADC) y datasheet del STM32U585.
5. **Portar a producto:** guía de App Lab y API de Bridge.

---

## 9. Licencias de los componentes citados

| Componente | Licencia |
|---|---|
| `arduino-router` | GPL-3.0-or-later |
| Zephyr RTOS | Apache-2.0 |
| `Arduino_LED_Matrix` / `ArduinoGraphics` | LGPL-2.1 (verificar en el repo) |
| `pyserial` | BSD-3-Clause |
| ADB / platform-tools | Apache-2.0 |
| Este repositorio | MIT |

Las licencias se citan a título informativo. Si redistribuís binarios, verificá los términos exactos en cada proyecto.

---

## 10. Cómo mantener esta lista

- Un enlace por pregunta concreta; si no responde nada, sobra.
- Fecha de consulta implícita en el historial de Git.
- Si un enlace muere, reemplazarlo por la versión archivada o por la fuente primaria (datasheet, repo).
- No agregar mirrors no oficiales de documentación técnica.
