"""Punto de entrada de JARVIS.

La experiencia principal es la Hub de escritorio. El backend sigue separado
para poder añadir despues vision y control de pantalla sin mezclarlo con la UI.
"""

from app import main


if __name__ == "__main__":
    raise SystemExit(main())
