"""
Paquete src · Pork to China.

Al importarse (cualquier `python -m src.xxx` pasa por aquí) fuerza UTF-8 en la salida.
Motivo: en Windows, cuando la salida de Python va a una tubería (| Select-String, > archivo),
Python usa cp1252, que no tiene caracteres como "→" o "≤" y falla con UnicodeEncodeError.
"""
import sys

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):   # flujos sin reconfigure (p. ej. capturados por pytest)
        pass
