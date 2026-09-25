# Implementation Plan: Backend Core (02-backend-core)

## Overview

Implement the first real working backend for the PixelArt Trip Planner: a three-layer
FastAPI application (routes → services → repositories) exposing `POST /rooms` and
`POST /rooms/{room_code}/join`. Supabase access is isolated to the repository layer and
wired through FastAPI's `Depends()` mechanism. Domain exceptions translate cleanly to
HTTP error shapes so nothing sensitive escapes to a response body.

---

## Tasks

- [ ] 1. Update project dependencies and environment configuration
  - [ ] 1.1 Add `supabase>=2.4` to `[project] dependencies` in `backend/pyproject.toml`
    - Also add `pytest-mock>=3.12` and `hypothesis>=6.100` to `[project.optional-dependencies] dev`
    - Verify no version conflicts with existing `fastapi>=0.110`, `pydantic>=2.6`, `pydantic-settings>=2.2`
    - _Requirements: 18.1, 18.2, 18.3, 18.4_

  - [ ] 1.2 Extend `backend/.env.example` with Supabase placeholder values
    - Add `SUPABASE_URL=https://your-project.supabase.co` placeholder
    - Add `SUPABASE_SERVICE_ROLE_KEY=your-service-role-key-here` placeholder
    - _Requirements: 1.2_

- [ ] 2. Extend `app/core/config.py` with required Supabase settings
  - [ ] 2.1 Add `supabase_url: str` with a `@field_validator` that checks for a valid URL scheme and non-empty host, raising `ConfigError` on failure
    - Add `supabase_service_role_key: str` with `repr=False` so the value is never included in `str(settings)` or log output
    - Both fields must have no default value — absence at startup raises `ConfigError` via the existing `get_settings()` wrapper
    - _Requirements: 1.2, 1.5, 1.6_

- [ ] 3. Create `app/exceptions.py` — domain exception hierarchy
  - [ ] 3.1 Define the full exception hierarchy:
    - `BackendError(Exception)` — base class for all domain errors
    - `RoomNotFoundError(BackendError)` — maps to HTTP 404
    - `MemberAlreadyExistsError(BackendError)` — maps to HTTP 409
    - `InvalidDisplayNameError(BackendError)` — maps to HTTP 422
    - `RepositoryError(BackendError)` — wraps unexpected Supabase failures, maps to HTTP 503
    - `RoomCodeExhaustedError(BackendError)` — all 10 retries failed, maps to HTTP 500
    - `ValidationError(BackendError)` — repo-level input guard failures, maps to HTTP 422
    - Each exception accepts a human-readable `message` string safe for `{"detail": message}` responses
    - Add a module-level docstring to `app/exceptions.py` stating the architecture rule: "All backend error responses use the API_Error_Response envelope. The backend owns all business mutations; the frontend may only read/subscribe via Supabase anon key."
    - _Requirements: 1.3, 8.5, 12.1, 12.4, 15.4, 22.4_

  - [ ] 3.2 Create `app/schemas/errors.py` — standardized API error response schema
    - Define `ErrorDetail(BaseModel)` with fields `code: str` and `message: str`
    - Define `ErrorResponse(BaseModel)` with field `error: ErrorDetail`
    - This schema is registered in the OpenAPI output so frontend developers see the error envelope in `/docs`
    - _Requirements: 22.1, 22.2_

- [ ] 4. Create infrastructure layer — Supabase client factory
  - [ ] 4.1 Create `app/db/supabase_client.py` with `get_supabase_client() -> AsyncClient`
    - Import `acreate_client` from `supabase` and call it with `settings.supabase_url` and `settings.supabase_service_role_key`
    - This function is the sole FastAPI dependency that touches the Supabase credentials
    - _Requirements: 1.3, 1.4, 2.3_

- [ ] 5. Create `app/api/deps.py` — dependency injection providers
  - [ ] 5.1 Define one provider function for each repository (`get_guest_repo`, `get_room_repo`, `get_member_repo`, `get_character_repo`, `get_prefs_repo`) each accepting `client: AsyncClient = Depends(get_supabase_client)` and returning the corresponding repository instance
    - Define `get_room_service(guest_repo=Depends(...), room_repo=Depends(...), member_repo=Depends(...), character_repo=Depends(...), prefs_repo=Depends(...)) -> RoomService`
    - This file is the single place tests override with `app.dependency_overrides`
    - _Requirements: 1.4, 2.4_

- [ ] 6. Create repository base class
  - [ ] 6.1 Create `app/repositories/base.py` with `BaseRepository`
    - Constructor accepts `client: AsyncClient` and stores it as `self._client`
    - Implement `_handle_error(exc, operation: str, table: str) -> Never` that raises `RepositoryError` with a safe message of the form `"Database operation '{operation}' on '{table}' failed."` — never including raw Supabase internals
    - _Requirements: 2.3, 4.4, 15.1_

- [ ] 7. Implement `GuestRepository`
  - [ ] 7.1 Create `app/repositories/guest_repo.py` extending `BaseRepository`
    - `async def create_guest(self, display_name: str, avatar_url: str | None = None) -> dict`: validate input (empty / whitespace-only / > 50 chars → raise `ValidationError`), INSERT into `guests`, return dict with at minimum `id`, `display_name`, `created_at`
    - `async def get_guest_by_id(self, guest_id: str) -> dict | None`: validate UUID format (invalid → raise `ValidationError`), SELECT from `guests`, return dict or `None`
    - Wrap any Supabase exception via `self._handle_error()`
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_

- [ ] 8. Implement `RoomRepository`
  - [ ] 8.1 Create `app/repositories/room_repo.py` extending `BaseRepository`
    - `async def create_room(self, name: str, room_code: str) -> dict`: validate name (1–100 chars, non-whitespace-only) and room_code (`^[A-Z0-9]{4,12}$`) → raise `ValidationError` on failure; INSERT into `party_rooms`; return dict with `id`, `name`, `room_code`, `status`, `planning_stage`, `created_at`
    - `async def get_room_by_code(self, room_code: str) -> dict | None`: SELECT by `room_code`, return dict or `None`
    - `async def get_room_by_id(self, room_id: str) -> dict | None`: SELECT by `id`, return dict or `None`
    - Wrap Supabase exceptions via `self._handle_error()`
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6_

- [ ] 9. Implement `MemberRepository`
  - [ ] 9.1 Create `app/repositories/member_repo.py` extending `BaseRepository`
    - `async def create_member(self, room_id: str, guest_id: str, display_name: str, role: Literal["owner","member"]) -> dict`: validate all args (UUID format, display_name 1–50 chars, valid role) → raise domain exception on failure; INSERT into `room_members`; detect Postgres `23505` uniqueness error and raise `MemberAlreadyExistsError`; return dict with `id`, `room_id`, `guest_id`, `display_name`, `normalized_name`, `role`, `created_at`
    - `async def get_member_by_normalized_name(self, room_id: str, normalized_name: str) -> dict | None`: SELECT filtering by `room_id` AND `normalized_name`, return dict or `None`
    - `async def get_member_by_id(self, member_id: str) -> dict | None`: SELECT by `id`, return dict or `None`
    - `async def list_members_by_room(self, room_id: str) -> list[dict]`: SELECT all rows for `room_id`, return list (possibly empty)
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7_

- [ ] 10. Implement `CharacterRepository` and `PreferencesRepository`
  - [ ] 10.1 Create `app/repositories/character_repo.py` extending `BaseRepository`
    - `async def create_character(self, member_id: str, appearance: dict | None = None) -> dict`: validate `member_id` UUID format → raise `ValidationError`; INSERT into `characters` with `appearance` defaulting to `{}`; return dict with `id`, `member_id`, `appearance`, `created_at`
    - `async def get_character_by_member_id(self, member_id: str) -> dict | None`: validate UUID, SELECT by `member_id`, return dict or `None`
    - _Requirements: 7.1, 7.2, 7.5, 7.6, 7.7_

  - [ ] 10.2 Create `app/repositories/preferences_repo.py` extending `BaseRepository`
    - `async def create_preferences(self, member_id: str, available_dates: list | None = None, destinations: list | None = None, interests: list | None = None, activities: list | None = None, hard_constraints: list | None = None) -> dict`: validate UUID, INSERT into `travel_preferences` defaulting all list fields to `[]`; return dict with all required fields
    - `async def get_preferences_by_member_id(self, member_id: str) -> dict | None`: validate UUID, SELECT by `member_id`, return dict or `None`
    - _Requirements: 7.3, 7.4, 7.5, 7.6, 7.7_

- [ ] 11. Create Pydantic v2 schemas in `app/schemas/room.py`
  - [ ] 11.1 Define `_Base(BaseModel)` with `model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)`
    - Define `_non_empty_str` using `Annotated[str, AfterValidator(_no_whitespace_only)]` for fields that must not be whitespace-only
    - Define all five response schemas: `GuestSchema`, `PartyRoomSchema`, `RoomMemberSchema`, `CharacterSchema`, `TravelPreferencesSchema` with fields and constraints exactly matching `api-contracts.md`
    - Define `CreateRoomRequest`, `JoinRoomRequest` using `_non_empty_str` for name / display_name fields
    - Define `_RoomPayload(_Base)` base with all five response fields; derive `CreateRoomResponse(_RoomPayload)` and `JoinRoomResponse(_RoomPayload)` from it
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 3.10, 3.11, 3.12, 3.13_

- [ ] 12. Implement `app/services/room_service.py`
  - [ ] 12.1 Implement module-level utility functions
    - `generate_room_code(length: int = 6) -> str`: use `secrets.choice` over `string.ascii_uppercase + string.digits`; returned string must match `^[A-Z0-9]{4,12}$`
    - `normalize_display_name(name: str) -> str`: strip, collapse interior whitespace with `re.sub(r'\s+', ' ', ...)`, lower-case — mirrors the PostgreSQL `GENERATED ALWAYS AS` expression
    - _Requirements: 8.1, 8.3, 8.4, 10.2_

  - [ ] 12.2 Implement `RoomService.create_room(request: CreateRoomRequest) -> CreateRoomResponse`
    - Loop up to 10 times: call `generate_room_code()`, check `room_repo.get_room_by_code()` for collision; raise `RoomCodeExhaustedError` if all attempts fail
    - Create records in strict order: `party_rooms` → `guests` → `room_members` (role=`"owner"`) → `characters` (appearance=`{}`) → `travel_preferences` (all lists=`[]`)
    - Validate each result dict via `model_validate` into the corresponding Pydantic schema and return a `CreateRoomResponse`
    - Propagate any domain exception from repositories unchanged; do not swallow partial failures
    - _Requirements: 8.1, 8.2, 8.5, 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8, 9.9_

  - [ ] 12.3 Implement `RoomService.join_room(room_code: str, request: JoinRoomRequest) -> JoinRoomResponse`
    - Look up room by code; raise `RoomNotFoundError` if absent
    - Normalize display name; call `member_repo.get_member_by_normalized_name()`
    - **Resume path** (member found): fetch guest, character (may be `None`), preferences (may be `None`) via `get_*` methods; return `JoinRoomResponse` from existing records — do NOT call any `create_*` method
    - **New-member path** (member not found): validate display_name is non-empty; create guest → member (role=`"member"`) → character → preferences; return `JoinRoomResponse`
    - Propagate domain exceptions from repositories unchanged
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 11.1, 11.2, 11.3, 11.4, 11.5, 12.1_

- [ ] 13. Create `app/api/routes/rooms.py`
  - [ ] 13.1 Define `router = APIRouter(prefix="/rooms", tags=["rooms"])`
    - `POST ""` (`/rooms`): accept `CreateRoomRequest`, inject `RoomService` via `Depends(get_room_service)`, return `CreateRoomResponse` with HTTP 200
    - `POST "/{room_code}/join"`: `room_code` annotated as `Annotated[str, Path(pattern=r"^[A-Z0-9]{4,12}$")]` so FastAPI rejects non-conforming codes with 422 before route body runs; accept `JoinRoomRequest`; return `JoinRoomResponse`
    - Route functions delegate entirely to the service — no business logic in the route layer
    - _Requirements: 2.1, 13.1, 13.2, 13.3, 14.1, 14.2, 14.4, 14.6_

- [ ] 14. Update `app/main.py` — wire router and register exception handlers
  - [ ] 14.1 Include the rooms router: `app.include_router(rooms.router)`
    - Register `@app.exception_handler` for each domain exception using the status-code mapping: `RoomNotFoundError` → 404, `MemberAlreadyExistsError` → 409, `InvalidDisplayNameError` → 422, `ValidationError` → 422, `RepositoryError` → 503, `RoomCodeExhaustedError` → 500
    - Register a catch-all `Exception` handler last that returns 500 using the `_err("INTERNAL_ERROR", "An internal error occurred.")` helper — never `str(exc)` for unknown exceptions
    - Ensure no handler ever emits the `supabase_service_role_key` value in a response body
    - Override FastAPI's default `RequestValidationError` handler to return `{"error": {"code": "VALIDATION_ERROR", "message": "..."}}` instead of the default `{"detail": [...]}` shape
    - All exception handlers MUST use the `ErrorResponse` / `ErrorDetail` Pydantic models from `app/schemas/errors.py` via a shared `_err(code, message)` helper function — no handler may construct a raw dict directly
    - _Requirements: 12.2, 12.3, 12.4, 13.4, 13.5, 14.3, 14.5, 15.1, 15.2, 15.3, 15.4, 15.5, 22.1, 22.3, 22.4, 22.5, 22.6_

- [ ] 15. Write unit tests for `RoomService` (`tests/test_room_service.py`)
  - [ ] 15.1 Define `pytest` fixtures using `pytest-mock`: `AsyncMock` instances for all five repositories and a `room_service` fixture that composes them into a real `RoomService`
    - **`test_create_room_happy_path`**: mock repos return valid dicts; assert returned `CreateRoomResponse` has all five populated fields (`room`, `member`, `guest`, `character`, `travel_preferences`)
    - **`test_create_room_record_creation_order`**: use a `MagicMock` manager to track call order; assert `create_room` called before `create_guest`, `create_guest` before `create_member`, `create_member` before `create_character`, `create_character` before `create_preferences`
    - _Requirements: 16.1, 16.2, 16.6_

  - [ ] 15.2 Add join-room path tests and error propagation tests
    - **`test_join_room_resume_path`**: mock `get_member_by_normalized_name` to return an existing member dict; assert all four `create_*` methods called exactly 0 times
    - **`test_join_room_new_member_path`**: mock `get_member_by_normalized_name` to return `None`; assert `create_guest`, `create_member`, `create_character`, `create_preferences` each called exactly once
    - **`test_join_room_room_not_found`**: mock `get_room_by_code` to return `None`; assert `RoomNotFoundError` raised; assert no `create_*` called
    - **`test_create_room_repo_failure`**: mock any repo to raise `RepositoryError`; assert service propagates it unchanged
    - _Requirements: 16.3, 16.4, 16.5, 16.6_

- [ ] 16. Write integration tests for room endpoints (`tests/test_rooms_api.py`)
  - [ ] 16.1 Create a `test_client` fixture that overrides `get_room_service` via `app.dependency_overrides` with an `AsyncMock(spec=RoomService)` and yields `(TestClient(app), mock_service)`
    - **`test_post_rooms_200`**: POST `/rooms` with valid body; assert 200; assert response body contains `room`, `member`, `guest`, `character`, `travelPreferences` with their required sub-fields
    - **`test_post_rooms_422_empty_name`**: POST `/rooms` with `name: "   "`; assert 422
    - _Requirements: 17.1, 17.5_

  - [ ] 16.2 Add join-room integration tests
    - **`test_post_rooms_join_new_member_200`**: POST `/rooms/ABC123/join` with new display_name; mock service returns new-member response; assert 200; assert `member.role == "member"`
    - **`test_post_rooms_join_resume_200`**: POST same display_name twice; assert both return 200 and `member.id` is identical in both responses
    - **`test_post_rooms_join_404`**: mock service raises `RoomNotFoundError`; assert 404; assert response body is `{"error": {"code": "ROOM_NOT_FOUND", "message": ...}}`
    - **`test_post_rooms_join_422_bad_code`**: POST `/rooms/lowercase/join`; assert 422 (Path regex rejection before service is called)
    - **`test_post_rooms_join_409_conflict`**: mock service raises `MemberAlreadyExistsError`; assert 409; assert response body is `{"error": {"code": "MEMBER_ALREADY_EXISTS", "message": ...}}` and `message` contains no database constraint names
    - **`test_post_rooms_503_on_repo_error`**: mock service raises `RepositoryError`; assert 503; assert response body is `{"error": {"code": "DATABASE_ERROR", "message": ...}}` and `message` does not contain the service-role key value
    - _Requirements: 17.2, 17.3, 17.4, 17.5_

- [ ] 17. Write property-based tests (`tests/test_properties.py`)
  - [ ]* 17.1 Write property test for `normalize_display_name` idempotency (Property 1)
    - Use `@given(st.text())` with `max_examples=200`; assert `normalize_display_name(normalize_display_name(name)) == normalize_display_name(name)` for all generated strings
    - **Property 1: normalize_display_name is idempotent**
    - **Validates: Requirements 10.2, 10.4**

  - [ ]* 17.2 Write property test for `generate_room_code` format (Property 3)
    - Call `generate_room_code()` 200 times and assert each result matches `^[A-Z0-9]{4,12}$`
    - **Property 3: Generated room codes always match the required format**
    - **Validates: Requirements 8.1, 8.4**

  - [ ]* 17.3 Write property test for whitespace-only string rejection (Property 5)
    - Use `@given(st.text(alphabet=st.characters(whitelist_categories=("Zs",)), min_size=1))` with `max_examples=200`; assert `CreateRoomRequest(name=ws_string, owner_display_name="Valid Name")` raises Pydantic `ValidationError`
    - **Property 5: Whitespace-only strings are rejected by the non-empty validator**
    - **Validates: Requirements 3.13, 4.5, 11.4**

- [ ] 18. Document Supabase access boundary
  - [ ] 18.1 Add a `SUPABASE_ACCESS_BOUNDARY.md` file under `docs/` (or a comment block in `backend/README.md`) that documents:
    - The list of operations that MUST go through FastAPI (create room, join room, update preferences, submit votes, generate itinerary, refine itinerary, update planning state)
    - The approved direct frontend Supabase access patterns (Realtime subscriptions, non-sensitive reads) and the requirement to comment them in `src/services/*.ts` files
    - The key rule: service-role key is backend-only; frontend uses anon key only
    - _Requirements: 23.1, 23.2, 23.3, 23.5_

  - [ ] 18.2 Add integration test asserting that `POST /rooms` and `POST /rooms/{room_code}/join` error responses conform to the `{"error": {"code": "...", "message": "..."}}` envelope
    - **`test_error_response_shape_404`**: mock service raises `RoomNotFoundError`; assert status 404; assert response JSON equals `{"error": {"code": "ROOM_NOT_FOUND", "message": <any non-empty string>}}`; assert `"detail"` key is NOT present in response body
    - **`test_error_response_shape_409`**: mock service raises `MemberAlreadyExistsError`; assert status 409; assert response JSON equals `{"error": {"code": "MEMBER_ALREADY_EXISTS", "message": <any non-empty string>}}`; assert `"detail"` key is NOT present in response body
    - **`test_error_response_shape_422`**: POST with invalid body (whitespace-only name); assert status 422; assert response JSON equals `{"error": {"code": "VALIDATION_ERROR", "message": <any non-empty string>}}`; assert `"detail"` key is NOT present in response body
    - **`test_error_response_shape_503`**: mock service raises `RepositoryError`; assert status 503; assert response JSON equals `{"error": {"code": "DATABASE_ERROR", "message": <any non-empty string>}}`; assert `"detail"` key is NOT present in response body
    - _Requirements: 22.1, 22.3, 22.4_

- [ ] 19. Final checkpoint — ensure all tests pass
  - Run `pytest` from `backend/` and confirm no failures
  - Verify the app boots cleanly when `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are present in `.env`
  - Ensure `ruff check .` passes with no lint errors
  - Ask the user if any questions arise before marking complete

---

## Notes

- Tasks marked with `*` are optional property-based tests and can be skipped for a faster MVP
- Each task references specific requirements for traceability
- Repositories (tasks 7–10) share a common base (task 6) and can be worked in parallel once the base exists
- The service layer (task 12) must not be started until all five repositories and schemas are in place
- Routes and main.py wiring (tasks 13–14) must not be started until the service layer is complete
- Tests (tasks 15–17) must not be started until the routes and main.py wiring are in place
- Property tests use `hypothesis>=6.100` added in task 1.1
- The `supabase_service_role_key` must never appear in any test assertion string, log output, or HTTP response — verified in integration test `test_post_rooms_503_on_repo_error`
- Task 18 documents the Supabase access boundary (Requirement 23) and adds error-envelope conformance tests (Requirement 22)

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2"] },
    { "id": 1, "tasks": ["2.1", "3.1", "3.2"] },
    { "id": 2, "tasks": ["4.1"] },
    { "id": 3, "tasks": ["5.1", "6.1"] },
    { "id": 4, "tasks": ["7.1", "8.1", "9.1", "10.1", "10.2", "11.1"] },
    { "id": 5, "tasks": ["12.1"] },
    { "id": 6, "tasks": ["12.2", "12.3"] },
    { "id": 7, "tasks": ["13.1"] },
    { "id": 8, "tasks": ["14.1"] },
    { "id": 9, "tasks": ["15.1", "15.2", "16.1", "16.2"] },
    { "id": 10, "tasks": ["17.1", "17.2", "17.3"] },
    { "id": 11, "tasks": ["18.1", "18.2"] }
  ]
}
```
