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

## Password reset emails

Both customer and admin sign-in pages offer password reset by email. Admin resets
require an active staff account with an email address saved under Admin → Users.
Customer signup accepts an optional phone number, saved in the customer profile;
password reset continues to use email.

The default email backend writes messages to `.local/emails` for local development.
It does **not** deliver them to an inbox. To enable delivery, configure your SMTP
provider in the server's private `.env`:

```dotenv
DJANGO_EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.your-provider.example
EMAIL_PORT=587
EMAIL_HOST_USER=your-sending-account
EMAIL_HOST_PASSWORD=your-provider-app-password
EMAIL_USE_TLS=true
DEFAULT_FROM_EMAIL=Ojasvi Rudraksha <your-verified-sender@example.com>
```

Use your provider's actual settings and a verified sender. Recreate the container
after changing `.env`: `docker-compose up -d --no-deps --force-recreate web`.
Request resets from the public HTTPS site when testing delivery so the emailed
links point to the correct domain. Reset links expire and stop working after use.

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

Country selection converts displayed prices using exchange rates downloaded at web
startup and saved in the persistent local settings volume. If a refresh fails,
previous rates are retained. Without cached rates, prices fall back to INR.
For an already running installation, fetch rates without restarting:

```sh
docker-compose exec -T web python manage.py refresh_exchange_rates
```

Schedule that command daily on the host to keep estimates current during long
running deployments. Local installations can run `python manage.py refresh_exchange_rates`.

This Docker setup is for local development.
