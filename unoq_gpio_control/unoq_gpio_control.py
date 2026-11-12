#!/usr/bin/env python3
"""
UNO Q GPIO Control — Cliente Python
====================================
Se comunica con la placa Arduino UNO Q vía Serial (USB CDC ACM)
para controlar GPIO, PWM, ADC y la matriz LED integrada.

Protocolo (115200 baud):
  GPIO:
    READ <pin>         → responde "OK 0" o "OK 1"
    WRITE <pin> <0|1>  → responde "OK 0" o "OK 1"
    ANALOG <pin>       → responde "OK <valor 0-4095>"
    PWM <pin> <0-255>  → responde "OK <valor>"
  Matriz LED:
    MATRIX CLEAR        → limpia la matriz        → "OK CLEAR"
    MATRIX LINE1 <txt>  → guarda texto línea 1     → "OK LINE1: <txt>"
    MATRIX LINE2 <txt>  → guarda texto línea 2     → "OK LINE2: <txt>"
    MATRIX SHOW         → muestra ambas líneas     → "OK SHOW"
    MATRIX <texto>      → atajo: scroll inmediato  → "OK SCROLL"

Uso:
  python unoq_gpio_control.py READ 13                 # Leer pin 13
  python unoq_gpio_control.py WRITE 13 1              # Encender pin 13
  python unoq_gpio_control.py MATRIX LINE1 Hola       # Guardar línea 1
  python unoq_gpio_control.py MATRIX LINE2 __mundo__  # Guardar línea 2
  python unoq_gpio_control.py MATRIX SHOW             # Mostrar ambas
  python unoq_gpio_control.py MATRIX "Hola mundo"     # Scroll inmediato
  python unoq_gpio_control.py TEXTO "Hola"              # Marquesina fuente chica
  python unoq_gpio_control.py TEXTO --tamano tiny --velocidad 50 "Hola"
  python unoq_gpio_control.py --interactive            # Modo interactivo
  python unoq_gpio_control.py -i                        # Modo interactivo (abreviado)
  python unoq_gpio_control.py -p /dev/ttyACM1 READ 2   # Puerto específico

Requisito: pyserial (pip install pyserial)
"""

import argparse
import sys
import time

try:
    import serial
except ImportError:
    print("ERROR: pyserial no está instalado.")
    print("       Instálalo con: pip install pyserial")
    sys.exit(1)

# ─── Constantes ───────────────────────────────────────────────────
DEFAULT_PORT    = "/dev/ttyACM0"
DEFAULT_BAUD    = 115200
DEFAULT_TIMEOUT = 2.0
READY_MESSAGE   = "UNOQ_GPIO_READY"
EXIT_COMMANDS   = {"quit", "exit", "q"}


# ─── Conexión Serial ──────────────────────────────────────────────
def connect_serial(port: str, baud: int, timeout: float) -> serial.Serial:
    """Abre la conexión serial con la UNO Q."""
    try:
        ser = serial.Serial(port, baud, timeout=timeout)
        # Esperar a que la placa se inicialice y envíe READY
        print(f"[*] Conectando a {port} a {baud} baud...")
        time.sleep(0.5)
        return ser
    except serial.SerialException as e:
        print(f"ERROR: No se pudo abrir el puerto {port}: {e}")
        print("       Verifica que la placa esté conectada y el puerto sea correcto.")
        print("       Puedes especificar el puerto con --port o -p.")
        sys.exit(1)


def wait_ready(ser: serial.Serial) -> bool:
    """Espera el mensaje UNOQ_GPIO_READY de la placa."""
    start = time.time()
    while time.time() - start < DEFAULT_TIMEOUT:
        line = ser.readline().decode("utf-8", errors="replace").strip()
        if line == READY_MESSAGE:
            print(f"[*] Placa detectada: {line}")
            return True
        if line:
            print(f"[!] Mensaje inesperado: {line}")
    return False


def send_command(ser: serial.Serial, command: str) -> str:
    """Envía un comando a la placa y retorna la respuesta."""
    ser.write((command + "\n").encode("utf-8"))
    ser.flush()
    response = ser.readline().decode("utf-8", errors="replace").strip()
    return response


# ─── Modo comando único ───────────────────────────────────────────
def run_single_command(args):
    """Ejecuta un solo comando y sale."""
    if len(args.command) == 0:
        print("ERROR: Debes especificar un comando.")
        print("       GPIO: READ <pin> | WRITE <pin> <0|1> | ANALOG <pin> | PWM <pin> <0-255>")
        print("       MATRIZ: CLEAR | LINE1 <txt> | LINE2 <txt> | SHOW | TINY | TINYSCROLL <txt> | <txt>")
        print("       TEXTO: <texto> [--tamano tiny|grande] [--velocidad 10-500]")
        sys.exit(1)

    cmd = args.command[0].upper()
    params = args.command[1:]

    # TEXTO: comando amigable para marquesina
    if cmd == "TEXTO":
        if len(params) == 0:
            print("ERROR: TEXTO requiere el texto a mostrar.")
            sys.exit(1)
        texto = " ".join(params)
        if args.tamano == "grande":
            full_cmd = f'MATRIX {texto}'
        else:
            # tiny: configurar velocidad y lanzar marquesina
            ser = connect_serial(args.port, args.baud, args.timeout)
            wait_ready(ser)
            send_command(ser, f"MATRIX SPEED {args.velocidad}")
            response = send_command(ser, f"MATRIX TINYSCROLL {texto}")
            print(f"[UNOQ] {response}")
            ser.close()
            return

    # Construir el comando completo para enviar a la placa
    full_cmd = f"{cmd} {' '.join(params)}"

    ser = connect_serial(args.port, args.baud, args.timeout)

    # Esperar READY (opcional, no bloqueante si ya está enviado)
    ready = wait_ready(ser)
    if not ready:
        print("[!] No se recibió UNOQ_GPIO_READY. Intentando enviar comando de todas formas...")

    response = send_command(ser, full_cmd)
    print(f"[UNOQ] {response}")

    ser.close()


# ─── Modo interactivo ─────────────────────────────────────────────
def run_interactive(args):
    """Entra en modo REPL interactivo."""
    ser = connect_serial(args.port, args.baud, args.timeout)

    ready = wait_ready(ser)
    if not ready:
        print("[!] No se recibió UNOQ_GPIO_READY. Puede que la placa ya estuviera iniciada.")
        print("    Los comandos deberían funcionar igualmente.")

    print("\n" + "=" * 60)
    print("  UNO Q GPIO Control — Modo Interactivo")
    print("=" * 60)

    while True:
        print()
        print("  1. Imprimir texto en matriz LED")
        print("  2. Control de pines (READ / WRITE)")
        print("  3. Lectura analógica (ANALOG)")
        print("  4. Control PWM")
        print("  5. Comandos MATRIX (CLEAR, LINE1/2, SHOW, TINY...)")
        print("  6. Salir")
        print()

        try:
            opcion = input("  Opción [1-6]: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[*] Saliendo...")
            break

        # ── 1: Imprimir texto ──────────────────────────────
        if opcion == "1":
            tam = input("    Tamaño [tiny/grande] (default: tiny): ").strip().lower()
            if tam not in ("tiny", "grande"):
                tam = "tiny"
            vel = 70
            if tam == "tiny":
                vel_str = input("    Velocidad ms [10-500] (default: 70): ").strip()
                if vel_str.isdigit():
                    v = int(vel_str)
                    if 10 <= v <= 500:
                        vel = v
            texto = input("    Texto: ").strip()
            if not texto:
                print("    → Cancelado.")
                continue
            print(f"    → \"{texto}\" | {tam} | {vel}ms")
            if tam == "grande":
                resp = send_command(ser, f"MATRIX {texto}")
            else:
                send_command(ser, f"MATRIX SPEED {vel}")
                resp = send_command(ser, f"MATRIX TINYSCROLL {texto}")
            print(f"    → {resp}")
            continue

        # ── 2: Control de pines ────────────────────────────
        if opcion == "2":
            print("\n  ── READ <pin> | WRITE <pin> <0|1> ──")
            print("  Pines: 0-19 | 'volver' para regresar\n")
            while True:
                try:
                    cmd = input("  pin> ").strip()
                except (EOFError, KeyboardInterrupt):
                    break
                if not cmd:
                    continue
                if cmd.lower() == "volver":
                    break
                resp = send_command(ser, cmd)
                print(f"  → {resp}")
            continue

        # ── 3: Analógico ───────────────────────────────────
        if opcion == "3":
            print("\n  ── ANALOG <pin> (A0-A5 = pines 14-19) ──")
            print("  'volver' para regresar\n")
            while True:
                try:
                    cmd = input("  adc> ").strip()
                except (EOFError, KeyboardInterrupt):
                    break
                if not cmd:
                    continue
                if cmd.lower() == "volver":
                    break
                resp = send_command(ser, f"ANALOG {cmd}")
                print(f"  → {resp}")
            continue

        # ── 4: PWM ─────────────────────────────────────────
        if opcion == "4":
            print("\n  ── PWM <pin> <0-255> (pines 3,5,6,9,10,11) ──")
            print("  'volver' para regresar\n")
            while True:
                try:
                    cmd = input("  pwm> ").strip()
                except (EOFError, KeyboardInterrupt):
                    break
                if not cmd:
                    continue
                if cmd.lower() == "volver":
                    break
                resp = send_command(ser, f"PWM {cmd}")
                print(f"  → {resp}")
            continue

        # ── 5: MATRIX ──────────────────────────────────────
        if opcion == "5":
            print("\n  ── MATRIX ──")
            print("  CLEAR | LINE1 <txt> | LINE2 <txt>")
            print("  SHOW | TINY | TINYSCROLL <txt>")
            print("  SPEED <ms> | <texto>")
            print("  'volver' para regresar\n")
            while True:
                try:
                    cmd = input("  matrix> ").strip()
                except (EOFError, KeyboardInterrupt):
                    break
                if not cmd:
                    continue
                if cmd.lower() == "volver":
                    break
                resp = send_command(ser, f"MATRIX {cmd}")
                print(f"  → {resp}")
            continue

        # ── 6: Salir ───────────────────────────────────────
        if opcion == "6":
            print("[*] Saliendo...")
            break

        print("  ⚠ Opción inválida. Elige 1-6.")

    ser.close()


# ─── Entry point ──────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="UNO Q GPIO Control — Cliente Python para controlar GPIO vía Serial",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python unoq_gpio_control.py READ 13
  python unoq_gpio_control.py WRITE 13 1
  python unoq_gpio_control.py MATRIX LINE1 Hola
  python unoq_gpio_control.py MATRIX LINE2 "__mundo__"
  python unoq_gpio_control.py MATRIX SHOW
  python unoq_gpio_control.py MATRIX "Hola mundo"
  python unoq_gpio_control.py --interactive
  python unoq_gpio_control.py -p /dev/ttyACM1 -b 9600 READ 2
        """
    )

    parser.add_argument(
        "-p", "--port",
        default=DEFAULT_PORT,
        help=f"Puerto serial (default: {DEFAULT_PORT})"
    )
    parser.add_argument(
        "-b", "--baud",
        type=int,
        default=DEFAULT_BAUD,
        help=f"Baud rate (default: {DEFAULT_BAUD})"
    )
    parser.add_argument(
        "-t", "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
        help=f"Timeout de lectura en segundos (default: {DEFAULT_TIMEOUT})"
    )
    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="Modo interactivo (REPL)"
    )
    parser.add_argument(
        "--tamano",
        choices=["tiny", "grande"],
        default="tiny",
        help="Tamaño de fuente para TEXTO (default: tiny)"
    )
    parser.add_argument(
        "--velocidad",
        type=int,
        default=70,
        help="Velocidad marquesina en ms (10-500, default: 70)"
    )
    parser.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="Comando: READ | WRITE | ANALOG | PWM | MATRIX | TEXTO"
    )

    args = parser.parse_args()

    if args.interactive:
        run_interactive(args)
    else:
        run_single_command(args)


if __name__ == "__main__":
    main()
