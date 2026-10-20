"""Permite ejecutar la ingesta con `python -m marketpulse.ingest`."""

import sys

from marketpulse.ingest.run import main

# sys.exit pasa el código de main() al sistema: 0 = éxito, 1 = alguna fuente falló
sys.exit(main())
