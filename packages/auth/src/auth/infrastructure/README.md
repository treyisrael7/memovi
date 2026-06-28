# Auth Infrastructure Layer

The infrastructure layer implements external concerns for the auth domain while
keeping those details out of domain and application code.

Current contents are empty extension points:

- `persistence` will contain storage mappings.
- `repositories` will contain repository implementations.
- `security` will contain credential and token adapters.
- `providers` will contain external identity provider adapters.
