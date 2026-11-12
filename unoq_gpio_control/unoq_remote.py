#!/usr/bin/env python3
"""
UNO Q Remote Control — Menú interactivo
Controla GPIO digital, ADC y PWM de la UNO Q desde la terminal.
"""

import serial
import time
import sys
import os
import subprocess

PORT = "/dev/ttyACM0"
BAUD = 115200

# Auto-detectar el puerto de la UNO Q
def _detectar_puerto():
    import glob
    for p in glob.glob("/dev/ttyACM*"):
        try:
            s = serial.Serial(p, BAUD, timeout=1)
            s.close()
            return p
        except:
            pass
    return PORT

DIGITAL_PINS = list(range(0, 14))   # D0-D13
ANALOG_PINS  = list(range(14, 20))  # A0-A5 (14-19)
PWM_PINS     = [3, 5, 6, 9, 10, 11]

# ─── Conexión ─────────────────────────────────────────────────────
def conectar():
    global PORT
    PORT = _detectar_puerto()
    try:
        ser = serial.Serial(PORT, BAUD, timeout=2)
        time.sleep(1)
        ser.reset_input_buffer()
        print(f"\n  Conectado a {PORT}")
        return ser
    except Exception as e:
        print(f"\n  ERROR: No se pudo conectar a {PORT}")
        print(f"  {e}")
        sys.exit(1)

def enviar(ser, cmd):
    ser.write((cmd + "\n").encode())
    ser.flush()
    resp = ser.readline().decode().strip()
    return resp

# ─── Utilidades ────────────────────────────────────────────────────
def limpiar():
    os.system("clear 2>/dev/null || cls 2>/dev/null || true")

def titulo(texto):
    print()
    print("  ╔" + "═" * 48 + "╗")
    print(f"  ║  {texto.center(44)}║")
    print("  ╚" + "═" * 48 + "╝")
    print()

def esperar():
    input("\n  Presiona ENTER para continuar...")

def leer_numero(mensaje, minimo, maximo):
    while True:
        try:
            val = input(mensaje)
            if val.lower() in ("q", "quit", "salir"):
                return None
            n = int(val)
            if minimo <= n <= maximo:
                return n
            print(f"  Debe ser entre {minimo} y {maximo}")
        except ValueError:
            print("  Ingresa un número válido")

# ─── Digital ───────────────────────────────────────────────────────
def menu_digital(ser):
    limpiar()
    titulo("CONTROL DIGITAL")
    print("  1. Leer pin")
    print("  2. Escribir pin")
    print("  0. Volver")
    print()

    op = input("  Opción > ").strip()
    if op == "1":
        leer_digital(ser)
    elif op == "2":
        escribir_digital(ser)
    elif op == "0":
        return
    else:
        print("  Opción inválida")
        esperar()

def leer_digital(ser):
    limpiar()
    titulo("LEER PIN DIGITAL")
    print("  Pines disponibles: D0 a D13\n")
    pin = leer_numero("  Número de pin (0-13) o 'q' para cancelar > ", 0, 13)
    if pin is None:
        return

    resp = enviar(ser, f"READ {pin}")
    estado = "HIGH (1)" if "OK 1" in resp else "LOW (0)" if "OK 0" in resp else resp
    print(f"\n  → Pin D{pin}: {estado}")
    esperar()

def escribir_digital(ser):
    limpiar()
    titulo("ESCRIBIR PIN DIGITAL")
    print("  Pines disponibles: D0 a D13\n")
    pin = leer_numero("  Número de pin (0-13) o 'q' para cancelar > ", 0, 13)
    if pin is None:
        return

    print("\n  0 = LOW (apagar)")
    print("  1 = HIGH (encender)")
    val = leer_numero("\n  Valor (0 o 1) o 'q' para cancelar > ", 0, 1)
    if val is None:
        return

    resp = enviar(ser, f"WRITE {pin} {val}")
    print(f"\n  → {resp}")
    esperar()

# ─── Analógico ─────────────────────────────────────────────────────
def menu_analogico(ser):
    limpiar()
    titulo("CONTROL ANALÓGICO")
    print("  1. Leer ADC (entrada analógica)")
    print("  2. Escribir PWM (salida analógica)")
    print("  0. Volver")
    print()

    op = input("  Opción > ").strip()
    if op == "1":
        leer_adc(ser)
    elif op == "2":
        escribir_pwm(ser)
    elif op == "0":
        return
    else:
        print("  Opción inválida")
        esperar()

def leer_adc(ser):
    limpiar()
    titulo("LEER ENTRADA ANALÓGICA (ADC)")
    print("  Pines disponibles: A0, A1, A2, A3, A4, A5\n")
    pin = leer_numero("  Número de pin analógico (0-5) o 'q' para cancelar > ", 0, 5)
    if pin is None:
        return

    pin_logico = 14 + pin
    resp = enviar(ser, f"ANALOG {pin_logico}")

    if "OK" in resp:
        try:
            valor = int(resp.split()[-1])
            voltaje = (valor / 4095.0) * 3.3
            barra = "█" * int(valor / 4095 * 30)
            print(f"\n  → Pin A{pin}: {valor} / 4095")
            print(f"  → Voltaje: {voltaje:.2f}V")
            print(f"  → [{barra}{' '*(30-len(barra))}]")
        except:
            print(f"\n  → {resp}")
    else:
        print(f"\n  → {resp}")
    esperar()

def escribir_pwm(ser):
    limpiar()
    titulo("ESCRIBIR PWM (DUTY CYCLE)")
    print("  Pines con PWM: D3, D5, D6, D9, D10, D11")
    print("  Duty cycle: 0 (apagado) a 255 (máximo)\n")

    pin = leer_numero("  Número de pin PWM (3,5,6,9,10,11) o 'q' para cancelar > ", 3, 11)
    if pin is None:
        return
    if pin not in PWM_PINS:
        print(f"\n  ERROR: Pin D{pin} no soporta PWM")
        esperar()
        return

    duty = leer_numero("\n  Duty cycle (0-255) o 'q' para cancelar > ", 0, 255)
    if duty is None:
        return

    resp = enviar(ser, f"PWM {pin} {duty}")

    if "OK" in resp:
        pct = (duty / 255.0) * 100
        barra = "█" * int(duty / 255 * 30)
        print(f"\n  → Pin D{pin}: {duty}/255 ({pct:.0f}%)")
        print(f"  → [{barra}{' '*(30-len(barra))}]")
    else:
        print(f"\n  → {resp}")
    esperar()

# ─── LEDs Integrados (vía ADB → Linux) ────────────────────────────

LEDS = {
    "1": ("green:user",  "Verde usuario"),
    "2": ("red:user",    "Rojo usuario"),
    "3": ("blue:user",   "Azul usuario"),
    "4": ("green:wlan",  "Verde WiFi"),
    "5": ("red:panic",   "Rojo panic"),
    "6": ("blue:bt",     "Azul Bluetooth"),
}

def _adb(cmd):
    """Ejecuta un comando en el Linux de la placa vía ADB."""
    try:
        r = subprocess.run(["adb", "shell", cmd],
                          capture_output=True, text=True, timeout=5)
        return r.stdout.strip()
    except Exception:
        return ""

def _liberar_led(nombre):
    """Suelta el LED del kernel para poder controlarlo nosotros."""
    _adb(f"echo none > /sys/class/leds/{nombre}/trigger")

def _led_escribir(nombre, valor):
    """Enciende (255) o apaga (0) un LED."""
    _adb(f"echo {valor} > /sys/class/leds/{nombre}/brightness")

def _led_leer(nombre):
    """Lee el estado actual del LED."""
    val = _adb(f"cat /sys/class/leds/{nombre}/brightness")
    return val

def menu_leds():
    while True:
        limpiar()
        titulo("LEDS INTEGRADOS DE LA PLACA")
        print("  Estos LEDs se controlan directamente vía Linux (ADB).\n")

        for k, (nombre, desc) in LEDS.items():
            val = _led_leer(nombre)
            icono = "🟢" if val and val != "0" else "⚫"
            print(f"  {k}. {icono}  {desc}")

        print()
        print("  ──────────────────────────────────")
        print("  E. Encender todos")
        print("  A. Apagar todos")
        print("  0. Volver")
        print()

        op = input("  Opción > ").strip()

        if op == "0":
            return
        elif op.upper() == "E":
            for nombre, _ in LEDS.values():
                _liberar_led(nombre)
                _led_escribir(nombre, "255")
            print("\n  → Todos ENCENDIDOS")
            esperar()
        elif op.upper() == "A":
            for nombre, _ in LEDS.values():
                _liberar_led(nombre)
                _led_escribir(nombre, "0")
            print("\n  → Todos APAGADOS")
            esperar()
        elif op in LEDS:
            nombre, desc = LEDS[op]
            _liberar_led(nombre)

            limpiar()
            titulo(f"CONTROL: {desc}")
            val = _led_leer(nombre)
            icono = "🟢 ENCENDIDO" if val and val != "0" else "⚫ APAGADO"
            print(f"\n  Estado actual: {icono}\n")
            print("  1. Encender")
            print("  2. Apagar")
            print("  3. Parpadear (5 veces)")
            print("  0. Volver")
            print()

            sub = input("  Opción > ").strip()
            if sub == "1":
                _led_escribir(nombre, "255")
                print(f"\n  → {desc}: ENCENDIDO")
                esperar()
            elif sub == "2":
                _led_escribir(nombre, "0")
                print(f"\n  → {desc}: APAGADO")
                esperar()
            elif sub == "3":
                for _ in range(5):
                    _led_escribir(nombre, "255")
                    time.sleep(0.2)
                    _led_escribir(nombre, "0")
                    time.sleep(0.2)
                print(f"\n  → {desc}: parpadeo completado")
                esperar()
        else:
            print("  Opción inválida")
            time.sleep(0.8)

# ─── Texto en Matriz LED ────────────────────────────────────────────
def menu_texto_matriz(ser):
    limpiar()
    titulo("TEXTO EN MATRIZ LED")
    print("  Muestra texto deslizante en la matriz 12×8 de la UNO Q.\n")

    # Tamaño de fuente
    print("  Tamaño de fuente:")
    print("    1. Chica (3×4)  — centrada, con márgenes")
    print("    2. Grande (5×7) — ocupa toda la altura")
    tam = input("\n  Opción [1-2] (default: 1) > ").strip()
    if tam == "2":
        fuente = "grande"
    else:
        fuente = "tiny"

    # Velocidad
    vel = 70
    if fuente == "tiny":
        vel_str = input("  Velocidad [10-500 ms] (default: 70) > ").strip()
        if vel_str.isdigit():
            v = int(vel_str)
            if 10 <= v <= 500:
                vel = v

    # Texto
    texto = input("  Texto a mostrar: ").strip()
    if not texto:
        print("\n  → Cancelado.")
        esperar()
        return

    print(f"\n  → Mostrando: \"{texto}\" | fuente={fuente} | {vel}ms")

    if fuente == "grande":
        resp = enviar(ser, f"MATRIX {texto}")
    else:
        enviar(ser, f"MATRIX SPEED {vel}")
        resp = enviar(ser, f"MATRIX TINYSCROLL {texto}")

    print(f"  → {resp}")
    esperar()


# ─── Temperatura ────────────────────────────────────────────────────
def menu_temperatura(ser):
    limpiar()
    titulo("TEMPERATURA DEL CHIP")
    print("  Leyendo sensor interno del STM32U585...\n")

    # Intentar vía Linux (ADB) primero
    temp_str = _adb("cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null")
    if temp_str and temp_str.isdigit():
        temp_c = float(temp_str) / 1000.0
        barra = "█" * min(int((temp_c - 15) / 45 * 30), 30)
        print(f"  🌡️  Temperatura: {temp_c:.1f} °C")
        print(f"  [{barra}{' '*(30-len(barra))}]")
        if temp_c > 55:
            print(f"  ⚠️  ¡Caliente! El chip está a {temp_c:.0f}°C")
        elif temp_c > 40:
            print(f"  ⚡ Temperatura elevada ({temp_c:.0f}°C)")
        else:
            print(f"  ✅ Temperatura normal")
        esperar()
        return

    # Fallback: intentar vía Serial (comando TEMP)
    print("  ADB no disponible, intentando vía Serial...")
    resp = enviar(ser, "TEMP")
    if "OK" in resp:
        print(f"  {resp}")
    else:
        print(f"  ❌ No se pudo leer temperatura ({resp})")
    esperar()


# ─── Principal ─────────────────────────────────────────────────────
def main():
    ser = conectar()
    print("\n  Conectado a la UNO Q. Cargando...")
    time.sleep(0.5)

    while True:
        limpiar()
        titulo("UNO Q — CONTROL REMOTO")
        print("  1. Digital          (D0-D13: leer/escribir)")
        print("  2. Analógico        (A0-A5: ADC / PWM)")
        print("  3. LEDs integrados  (verde, rojo, azul de la placa)")
        print("  4. Texto en matriz  (marquesina en display LED)")
        print("  5. Temperatura      (sensor interno del chip)")
        print("  0. Salir")
        print()

        op = input("  Opción > ").strip()

        if op == "1":
            menu_digital(ser)
        elif op == "2":
            menu_analogico(ser)
        elif op == "3":
            menu_leds()
        elif op == "4":
            menu_texto_matriz(ser)
        elif op == "5":
            menu_temperatura(ser)
        elif op == "0":
            limpiar()
            print("\n  ¡Hasta luego!\n")
            break
        else:
            print("  Opción inválida")
            time.sleep(0.8)

    ser.close()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        limpiar()
        print("\n  ¡Hasta luego!\n")
