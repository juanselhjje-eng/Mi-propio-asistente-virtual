"""Punto de entrada de Milo.

La Hub de escritorio sigue separada del runtime para poder añadir despues
vision, voz y control de pantalla sin mezclar esas capas con la UI.
"""

import app as _app

from runtime import install

install(_app)


if __name__ == "__main__":
    raise SystemExit(_app.main())
