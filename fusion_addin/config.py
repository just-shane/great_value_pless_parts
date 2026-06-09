"""Add-in configuration shared across modules."""

# Identity (used to build unique UI element ids)
ADDIN_NAME = "GreatValuePlessParts"
COMPANY_NAME = "GreatValue"

# Verbose logging to the Fusion Text Commands console when True.
DEBUG = True

# ---- Quoting backend --------------------------------------------------------
# Point this at wherever the FastAPI service is running.
API_BASE_URL = "http://127.0.0.1:8000"
QUOTE_ENDPOINT = "/api/v1/quote"
HTTP_TIMEOUT_SECONDS = 20

# ---- Quote defaults ---------------------------------------------------------
DEFAULT_MATERIAL = "aluminum_6061"
DEFAULT_QUANTITY = 1
DEFAULT_PROCESS = "cnc_milling"
