# Ojasvi Rudraksha

A Django storefront with a product catalog, cart, customer accounts, wishlists and an admin portal. Signed-in carts are saved to the account and restored after logout or on another device. Guest items merge into the account on login. Checkout and payments are not implemented yet.

## Run locally

Start Docker Desktop. On first setup, copy `.env.example` to `.env` if it does not
already exist. Edit `.env` for your database, app port, debug mode, allowed hosts,
timezone and email settings. Then run from this folder:

```sh
docker-compose up --build -d
```

Open http://127.0.0.1:8000/. Docker starts MySQL first, then runs migrations and loads the initial catalog; allow a moment for them to finish.

To use another port, change `OJASVIRUDRAKSHA_PORT` in `.env`. Docker Compose reads this file
and passes the settings to each service. Keep `.env` private; it is excluded from Git
and the Docker image.

For a public HTTPS domain, configure the **server's** `.env`:

```dotenv
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,rundra.online,www.rundra.online
DJANGO_CSRF_TRUSTED_ORIGINS=https://rundra.online,https://www.rundra.online
```

Allowed hosts are bare hostnames; trusted CSRF origins include `https://` with no
trailing slash or path. Deploy the updated `ojasvirudraksha/settings.py` as well as
editing `.env` so Django reads the CSRF setting. Rebuild and recreate the web container;
a restart alone does not reload `.env`:

```sh
docker-compose up --build -d --no-deps --force-recreate web
```

## Create an admin

Once the app is running:

```sh
docker-compose exec web python manage.py createsuperuser
```

Sign in at http://127.0.0.1:8000/admin/ to manage products, inventory, customers and site content. Use the port set in `.env`.

Run `docker-compose up --build -d` again after changing code or `.env`.
Startup also updates existing catalog and information-page branding, preserving
product IDs, carts and wishlists. Existing product links redirect to the renamed URLs.
Keep existing MySQL credentials when upgrading; the new example names apply to fresh databases.

## Useful commands

```sh
# View logs
docker-compose logs -f web

# Run tests with a temporary SQLite database
docker-compose exec -e MYSQL_HOST= -e DJANGO_DB_PATH=:memory: web python manage.py test store

# Stop the app
docker-compose down
```

User accounts, products and other application data are stored in the `mysql` service.
MySQL data persists in the `mysql_data` volume; the database port is only accessible
inside Docker. Database credentials are configured in `.env`; the example values are
for local development. Changing them after initialization does not update existing
MySQL users.

Existing SQLite data is not automatically imported. The old SQLite file/volume is
left intact; this setup starts a fresh MySQL database. Create a new admin account.

Docker stores the database, uploads and local settings in persistent volumes, separate from host files. Stopping the app preserves them; `docker-compose down -v` deletes them.

This Docker setup is for local development.
