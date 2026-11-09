# Mobile guide: listing events

All paths below start at `/api/v1/` on the configured API host. Keep the trailing slash. Send JSON with `Content-Type: application/json`.

## Publishing and ownership

Creating an event publishes it immediately. There is no draft state, approval step, visibility switch, or separate publish endpoint. Label the create form's final action **Publish event** and explain that it becomes public immediately. Keep unfinished forms locally.

Each event belongs to exactly one listing. The listing ID comes from the provider endpoint URL; do not send it in the request body. It cannot be changed after creation. Event ownership follows the listing's current owner, including after an ownership transfer.

Provider endpoints require a valid Knox token:

```http
Authorization: Bearer <token>
```

The account must pass the provider role check (`TUTOR` or `MASTERCLASS`; managers also satisfy the project's role checks) and own the listing. A role alone never grants access to another account's listing. The event endpoints do not require provider verification or an ACTIVE listing.

Public endpoints accept anonymous requests. If the app has no valid token, omit the authentication header; an invalid or expired token can still cause a public request to fail authentication.

## Endpoint reference

Paths are relative to `/api/v1/`. `{listing_id}` and `{event_id}` are UUID strings.

| Method | Path | Access | Success |
| --- | --- | --- | --- |
| GET | `provider/listings/` | Existing provider listing permissions | 200, owned listings; use this to select a listing |
| GET | `provider/listings/{listing_id}/events/` | Provider + listing owner | 200, paginated events |
| POST | `provider/listings/{listing_id}/events/` | Provider + listing owner | 201, published event |
| GET | `provider/listings/{listing_id}/events/{event_id}/` | Provider + listing owner | 200, event |
| PATCH | `provider/listings/{listing_id}/events/{event_id}/` | Provider + listing owner | 200, updated event |
| DELETE | `provider/listings/{listing_id}/events/{event_id}/` | Provider + listing owner | 204, empty body |
| GET | `events/` | Public | 200, paginated events across all listings |
| GET | `events/{event_id}/` | Public | 200, event |
| GET | `listings/{listing_id}/events/` | Public | 200, paginated events for one listing |
| GET | `listings/{listing_id}/` | Existing public listing rules | 200, listing with an `events` array |

Provider event detail endpoints support PATCH, not PUT. Public event endpoints are read-only.

The existing provider listing picker has its own role permissions: it currently permits MASTERCLASS, MANAGER, and ADMIN accounts. TUTOR accounts granted listing ownership can use the event endpoints with a known listing ID, but cannot use that picker endpoint.

## Event fields

Every event response uses this shape:

```json
{
  "id": "d1234567-1234-4123-8123-123456789abc",
  "listing": "a1234567-1234-4123-8123-123456789abc",
  "title": "School open day",
  "description": "Meet the teachers and tour the school.",
  "starts_at": "2026-12-12T06:00:00Z",
  "ends_at": "2026-12-12T08:00:00Z",
  "location": "Main school hall",
  "registration_url": "https://example.com/open-day",
  "published_at": "2026-11-09T10:00:00Z",
  "updated_at": "2026-11-09T10:00:00Z"
}
```

| Field | Create | Rules |
| --- | --- | --- |
| `title` | Required | Nonblank string, maximum 200 characters |
| `starts_at` | Required | ISO 8601 datetime; send an explicit timezone offset or `Z` |
| `description` | Optional | String; defaults to `""` |
| `ends_at` | Optional | ISO 8601 datetime or `null`; defaults to `null`; must be strictly later than `starts_at` |
| `location` | Optional | String, maximum 500 characters; defaults to `""` |
| `registration_url` | Optional | Valid URL or `""`; maximum 200 characters; defaults to `""` |
| `id`, `listing`, `published_at`, `updated_at` | Server-managed | Read-only; supplied values are ignored |

Use `""` to clear optional text and URL fields; use `null` to clear `ends_at`. Other fields do not accept `null`. On PATCH, omitted fields retain their existing values. Date validation considers the saved value of the other date when only one date changes.

Dates in the past are currently allowed. There are no event image, price, capacity, booking, or attendance fields. `registration_url` is an external link; saving it does not create a registration in this API.

## Create and publish

```http
POST /api/v1/provider/listings/a1234567-1234-4123-8123-123456789abc/events/
Authorization: Bearer <token>
Content-Type: application/json

{
  "title": "School open day",
  "description": "Meet the teachers and tour the school.",
  "starts_at": "2026-12-12T09:00:00+03:00",
  "ends_at": "2026-12-12T11:00:00+03:00",
  "location": "Main school hall",
  "registration_url": "https://example.com/open-day"
}
```

A `201 Created` response contains the full event object shown above. Use its `id` for navigation and subsequent edits. Convert the user's local date/time into a timezone-aware timestamp and render response dates in the intended display timezone.

Disable repeated submission while publishing. Creation has no idempotency key or duplicate detection. If the connection fails after submission, reload the listing's events before offering a retry; the first request may already have created an event.

## Edit and delete

Send only the changed fields:

```http
PATCH /api/v1/provider/listings/a1234567-1234-4123-8123-123456789abc/events/d1234567-1234-4123-8123-123456789abc/
Authorization: Bearer <token>
Content-Type: application/json

{
  "title": "Updated open day",
  "ends_at": null
}
```

The `200 OK` response is the full updated event. Edits become public immediately. There is no optimistic locking/version field; refresh the event after saving.

To delete, send DELETE to the same detail URL with the authorization header. A successful response is `204 No Content`; do not try to decode a JSON body. Remove the event from local caches and refresh affected lists. Deleting the parent listing also deletes its events.

## Public discovery and listing details

Use `GET /api/v1/events/` for the global feed and `GET /api/v1/listings/{listing_id}/events/` for a listing's feed. Both include all events, including past events and events belonging to inactive listings. Events are ordered by `starts_at` ascending, then `id`.

Event list endpoints return page-number pagination with 20 events per page:

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "d1234567-1234-4123-8123-123456789abc",
      "listing": "a1234567-1234-4123-8123-123456789abc",
      "title": "School open day",
      "description": "Meet the teachers and tour the school.",
      "starts_at": "2026-12-12T06:00:00Z",
      "ends_at": "2026-12-12T08:00:00Z",
      "location": "Main school hall",
      "registration_url": "https://example.com/open-day",
      "published_at": "2026-11-09T10:00:00Z",
      "updated_at": "2026-11-09T10:00:00Z"
    }
  ]
}
```

Use `?page=2` or follow `next` until it is `null`. Custom page sizes, event date filtering, search, and custom sorting are not implemented. To select a listing, use its nested public event URL; `events/?listing=...` does not filter events.

The public listing detail response includes `events: [<full event objects>]`, or `events: []` when there are none. This embedded array is not paginated. Listing cards and provider listing responses do not embed events; use the event endpoints there.

Existing public listing detail rules still apply: only ACTIVE listings are returned, and authenticated owners are excluded from public listing retrieval. Use the dedicated public event endpoints for event access in those cases. Unlike listing detail, the nested public events endpoint returns an empty page for a nonexistent listing UUID.

## Error handling

| Status | Meaning | Mobile behavior |
| --- | --- | --- |
| 400 | Invalid/missing fields or invalid dates | Show field errors and keep the form contents |
| 401 | Missing, invalid, or expired token | Ask the user to sign in again for provider operations |
| 403 | Authenticated account fails the provider role check | Hide provider actions and show an access message |
| 404 | Provider listing missing/not owned; event missing or belongs to another listing; public event missing; invalid page | Refresh the relevant data; leave an inaccessible editor |
| 405 | Unsupported method, such as PUT | Check the endpoint/method pairing |

Validation errors are keyed by field, for example:

```json
{
  "ends_at": ["Must be later than starts_at."]
}
```

Other failures generally use `{"detail": "..."}`. Do not branch on exact error text. A provider's cross-owner access returns 404, including when the account has a manager role. If listing ownership changes while an editor is open, subsequent requests by the former owner return 404.
