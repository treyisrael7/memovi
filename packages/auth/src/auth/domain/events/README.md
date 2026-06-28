# Auth Domain Events

Domain events describe auth facts that have already happened. They are part of
the domain language and remain independent of transport, persistence, and worker
implementation details.

Current event definitions:

- `UserRegistered`
- `UserLoggedIn`
