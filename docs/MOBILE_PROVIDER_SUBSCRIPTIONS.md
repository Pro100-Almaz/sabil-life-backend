# Provider subscriptions

These are free follows of a provider account, separate from paid listing subscriptions.
All paths start with `/api/v1/` and require `Authorization: Bearer <token>`.
Provider identifiers are public user UUIDs (`owner_id` on listing details or
`user_id` on tutor profiles), never integer user IDs.

## Clients

Family accounts can subscribe to active, nondeleted TUTOR or MASTERCLASS accounts.
Following yourself is rejected. Accounts with multiple roles can use this API if
they hold the FAMILY role.

| Method | Path | Behavior |
| --- | --- | --- |
| POST | `provider-subscriptions/` | JSON: `{"provider_id": "<provider UUID>"}`. Returns 201 when created, 200 if already subscribed. |
| GET | `provider-subscriptions/` | Paginated list of the authenticated client's followed providers. |
| DELETE | `provider-subscriptions/{provider_id}/` | Unsubscribe; returns 204, or 404 if not subscribed. |

POST and list entries contain only `provider_id` and `display_name`. Lists use the
standard `count`, `next`, `previous`, `results` pagination envelope. A client's
identity always comes from authentication; supplying another client ID does not
change which account subscribes. Duplicate follows are also blocked by a database
constraint. Missing or malformed provider IDs return 400; nonexistent, nonprovider,
inactive, and deleted targets return 404.

## Providers and privacy

| Method | Path | Behavior |
| --- | --- | --- |
| GET | `provider/subscribers/count/` | `{"count": 12}` for the authenticated provider. |
| GET | `provider/subscribers/` | Paginated subscriber records for the authenticated provider. |
| GET | `provider/subscribers/{id}/` | One of that provider's subscriber records. |

Subscriber records contain `id` (subscription record ID), `client_id` (public user
UUID), `full_name`, and `created_at`. They are read-only and restricted to the
provider receiving the subscription. Providers cannot retrieve another provider's
records (404). Query parameters cannot select another provider's data or count.
Manager role inheritance does not bypass the ownership restriction. Family-only
accounts receive 403 for these endpoints. Unauthenticated requests receive 401.

## Event alerts

Publishing a new listing event queues a Celery task after the event transaction
commits. The original publisher's followers receive a `PROVIDER_EVENT` notification
in the existing `notifications/` inbox, plus a best-effort device push when enabled.
The notification body is the event title; its `data` contains `event_id`,
`listing_id`, and `provider_id` for navigation.

Only subscriptions created before publication and still present when the task
runs qualify. Unsubscribed, inactive, and deleted clients are excluded. Following
after publication does not send historical alerts. An ownership transfer does not
change the publisher used for a queued notification. Event edits do not trigger
alerts. Replaying the task does not duplicate inbox entries or resend pushes for
entries already created. A push failure does not remove the inbox entry or stop
delivery to other subscribers.

Deploy the included migrations before running the updated backend and workers.
Celery workers and the broker must be running for alerts to be delivered.
