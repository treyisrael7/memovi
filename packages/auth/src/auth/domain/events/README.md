# Auth Domain Events

Domain events describe auth facts that have already happened. They are part of
the domain language and remain independent of transport, persistence, and worker
implementation details.

No event types are defined yet. Registration uses an optional application
callback (`UserRegisteredHandler`); login/logout update session state directly.
