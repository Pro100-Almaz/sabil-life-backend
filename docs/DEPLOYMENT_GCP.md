# Deploying Sabil Life backend to Google Cloud (single VM)

This guide deploys the whole stack onto **one Compute Engine VM** running
`docker-compose.prod.yml`, in the **me-central1 (Doha)** region. Uploaded media
goes to a **Google Cloud Storage** bucket so it survives VM rebuilds.

Architecture on the VM:

```
Compute Engine VM (me-central1)
 └─ docker compose -f docker-compose.prod.yml up -d
     ├─ caddy       :80/:443  (TLS + reverse proxy)  ── public
     ├─ backend     :8000     (gunicorn + Django)    ── internal
     ├─ worker                (celery worker)         ── internal
     ├─ beat                  (celery beat)           ── internal
     ├─ db                    (postgres, volume)      ── internal
     └─ redis                 (cache + broker)        ── internal

Google Cloud Storage bucket  ── uploaded media (public read)
```

Only ports **80, 443, and 22 (SSH)** are open. Postgres and Redis are never
exposed to the internet.

---

## 0. Prerequisites (one-time, on your laptop)

1. A Google Cloud account with **billing enabled**.
2. A **domain name** you control (e.g. `api.example.com`) — needed for HTTPS.
3. Install the `gcloud` CLI: <https://cloud.google.com/sdk/docs/install>, then:
   ```bash
   gcloud auth login
   gcloud projects create sabil-life-prod --name="Sabil Life Prod"   # or reuse an existing project
   gcloud config set project sabil-life-prod
   ```
   > If you prefer clicking, everything below is also doable in the Cloud Console UI.

Set some shell variables you'll reuse:

```bash
export PROJECT=sabil-life-prod
export REGION=me-central1
export ZONE=me-central1-a
export VM=sabil-backend
```

Enable the APIs you'll touch:

```bash
gcloud services enable compute.googleapis.com storage.googleapis.com --project=$PROJECT
```

---

## 1. Create the media bucket + access key (GCS)

```bash
export BUCKET=sabil-life-media-prod   # must be globally unique; change if taken

# Create the bucket in the Doha region.
gcloud storage buckets create gs://$BUCKET \
  --project=$PROJECT --location=$REGION --uniform-bucket-level-access

# Make objects publicly readable (media URLs work without signing).
gcloud storage buckets add-iam-policy-binding gs://$BUCKET \
  --member=allUsers --role=roles/storage.objectViewer
```

Create an **HMAC key** so the S3-compatible storage backend can write to it. First
make a service account for the app, then an HMAC key for that account:

```bash
gcloud iam service-accounts create sabil-storage \
  --display-name="Sabil media writer" --project=$PROJECT

export SA=sabil-storage@$PROJECT.iam.gserviceaccount.com

gcloud storage buckets add-iam-policy-binding gs://$BUCKET \
  --member=serviceAccount:$SA --role=roles/storage.objectAdmin

gcloud storage hmac create $SA --project=$PROJECT
```

The last command prints an **access ID** and **secret**. Save both — they go into
`AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` in your `.env`.

---

## 2. Reserve a static IP and create the VM

```bash
# Static external IP so your DNS never breaks on reboot.
gcloud compute addresses create sabil-ip --region=$REGION --project=$PROJECT
gcloud compute addresses describe sabil-ip --region=$REGION --project=$PROJECT \
  --format='value(address)'
# → note this IP; you'll point DNS at it.

# The VM. e2-small (2 vCPU shared, 2 GB) is a fine starting point; bump to
# e2-medium (4 GB) if memory is tight with worker+beat+postgres+redis.
gcloud compute instances create $VM \
  --project=$PROJECT --zone=$ZONE \
  --machine-type=e2-medium \
  --image-family=debian-12 --image-project=debian-cloud \
  --boot-disk-size=30GB --boot-disk-type=pd-balanced \
  --address=$(gcloud compute addresses describe sabil-ip --region=$REGION --project=$PROJECT --format='value(address)') \
  --tags=http-server,https-server
```

Open the firewall (Debian images + the `http-server`/`https-server` tags usually
open 80/443 automatically, but make it explicit):

```bash
gcloud compute firewall-rules create allow-web \
  --project=$PROJECT --allow=tcp:80,tcp:443 \
  --target-tags=http-server,https-server --source-ranges=0.0.0.0/0
```

> SSH (port 22) is allowed by GCP's default rules for `gcloud compute ssh`.

---

## 3. Point your domain at the VM

In your DNS provider, create an **A record**:

```
api.example.com  →  <the static IP from step 2>
```

Wait for it to propagate (`dig api.example.com` should return your IP). Caddy
can't issue the HTTPS certificate until DNS resolves.

---

## 4. Install Docker on the VM

```bash
gcloud compute ssh $VM --zone=$ZONE --project=$PROJECT
```

Then, on the VM:

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
exit           # log out and back in so the docker group applies
```

Reconnect: `gcloud compute ssh $VM --zone=$ZONE --project=$PROJECT`.

---

## 5. Get the code and configure it (on the VM)

```bash
# Clone your repo. For a private repo, add a GitHub deploy key to the VM
# (ssh-keygen on the VM, add the .pub to the repo's Deploy keys), or use HTTPS
# with a personal access token.
git clone git@github.com:Pro100-Almaz/sabil-life-backend.git
cd sabil-life-backend

# Create the production env file from the template.
cp .env.production.example .env
nano .env                  # fill in every CHANGE_ME value
```

Fill in `.env`:
- `DJANGO_SECRET_KEY` — generate with
  `python3 -c "import secrets; print(secrets.token_urlsafe(64))"`
- `ALLOWED_HOSTS=api.example.com`
- `CORS_ALLOWED_ORIGINS` — your frontend origin(s)
- `POSTGRES_PASSWORD` and the matching password inside `DATABASE_URL`
- The four `AWS_*` values from step 1 (HMAC key + bucket name)
- Email + Sentry if you use them

Firebase push credentials:

```bash
mkdir -p secrets
nano secrets/sabil-life-firebase-adminsdk.json   # paste the service-account JSON
```

Set the domain + email in the Caddyfile:

```bash
nano Caddyfile
# replace api.example.com with your domain, and you@example.com with your email
```

---

## 6. Launch

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

This builds the image, runs migrations, collects static files, and starts all six
services. Watch it come up:

```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f backend caddy
```

Create your admin user:

```bash
docker compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser
```

Now visit:
- `https://api.example.com/admin-panel/` — the Unfold admin
- `https://api.example.com/api/v1/...` — your API

Caddy fetches the TLS certificate automatically on first request; the first load
may take a few seconds.

---

## 7. Day-2 operations

**Deploy a new version:**
```bash
cd ~/sabil-life-backend
git pull
docker compose -f docker-compose.prod.yml up -d --build
```
Migrations and `collectstatic` run automatically on the `backend` container's boot.

**Logs:**
```bash
docker compose -f docker-compose.prod.yml logs -f backend        # web
docker compose -f docker-compose.prod.yml logs -f worker beat    # celery
```

**Database backup (run from the VM; copy off-box or to GCS):**
```bash
docker compose -f docker-compose.prod.yml exec -T db \
  pg_dump -U sabil sabil | gzip > backup-$(date +%F).sql.gz
# then, e.g.:  gcloud storage cp backup-*.sql.gz gs://$BUCKET-backups/
```
Consider a cron job for this, plus GCP scheduled **snapshots** of the boot disk.

**Restart / stop:**
```bash
docker compose -f docker-compose.prod.yml restart backend
docker compose -f docker-compose.prod.yml down          # stop all (data volumes persist)
```

---

## Notes & gotchas

- **Swagger/OpenAPI is disabled in production** — the schema and swagger-ui routes
  are only registered when `DEBUG=True` (see `conf/urls.py`). This is intentional in
  the current codebase; if you want docs in prod, move those routes out of the
  `if settings.DEBUG:` block.
- **`SECURE_SSL_REDIRECT` is on** when `DEBUG=False`. Caddy terminates TLS and sets
  `X-Forwarded-Proto`, which Django trusts via `SECURE_PROXY_SSL_HEADER`, so there's
  no redirect loop. Don't disable TLS at Caddy without adjusting this.
- **This is a single point of failure.** One VM means downtime during reboots and no
  automatic failover. That's an acceptable trade for an early launch; when traffic
  grows, the migration path is: move Postgres to **Cloud SQL**, Redis to
  **Memorystore**, and the web/worker/beat containers to **Cloud Run**. The image and
  env you build here transfer directly.
- **Backups are your responsibility** on this setup — the Postgres data lives in a
  Docker volume on the VM disk. Do the `pg_dump` cron above and enable disk
  snapshots.
```
