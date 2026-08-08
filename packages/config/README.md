# Memovi Config

Typed application configuration for Memovi: environment parsing, defaults,
validation, secret redaction, and startup fail-fast checks.

## Usage

```python
from memovi_config import load_settings, validate_configuration

settings = validate_configuration()
print(settings.database.safe_url)  # password redacted
```

See [`docs/architecture/CONFIGURATION.md`](../../docs/architecture/CONFIGURATION.md)
for the full environment variable contract.
