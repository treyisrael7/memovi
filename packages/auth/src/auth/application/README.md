# Auth Application Layer

The application layer coordinates auth use cases. It will load domain objects,
call domain behavior, use repository interfaces, and return DTOs.

Current contents are structural only:

- `commands` will contain write use-case requests.
- `queries` will contain read use-case requests.
- `dto` will contain application input and output records.
- `services` will contain use-case orchestration.
