# ASTROL Django — Approved Mockup Edition

This version rebuilds the local website to closely match the Astrol Rudraksha mockup approved in chat.

## Run with Docker

Build and start the application:

```bash
docker-compose up --build -d --wait
```

Open http://127.0.0.1:8000/. Migrations and the catalog bootstrap run automatically
when the `web` container starts. View logs with `docker-compose logs -f web` and
stop the application with `docker-compose down`.

## Fresh setup

```bash
docker-compose up --build -d --wait
```

The product-photo assets in `static/images/exact/` were extracted from the Astrol mockup approved by the project owner, so the local page visually matches that approved concept.

Note: certification/authenticity text is currently prototype storefront copy. Confirm every commercial claim before publishing the site publicly.

## Full catalog

The saved public catalog snapshot from Rudradhyay.com (11 September 2026) is in
`store/data/rudradhyay_catalog.json`. It contains product names, source links,
prices, options and availability. Product descriptions are concise ASTROL copy;
source reviews, medical-benefit claims and policy text are not imported. One
product photo per reference listing is stored locally in `static/images/catalog/`.

The expanded catalog is imported automatically when the `web` container starts.
To rerun it manually after editing catalog data, use:

```bash
docker-compose exec web python manage.py import_reference_catalog
```

The import adds 412 reference products and 645 variants, preserving the 14 original
ASTROL listings. It also adds 7 clearly marked samples for gemstones, rings and
shankh using the existing illustrated assets. Samples cannot be added to the cart.
Dhan Yog is a secondary collection of 6 products; those items also appear in their
primary categories. `/shop/` lists all products and searches across categories;
`/` is the ASTROL homepage; the Rudraksha collection is at `/shop/?category=rudraksha`. Lists display 25 products per page.

The import is repeatable: existing source IDs and sample slugs are skipped, so it
will not overwrite subsequent admin edits. Prices and availability are a snapshot,
not a live inventory connection. Edit products, variants and sample flags through
Django admin. To create a local administrator, run
`docker-compose exec web python manage.py createsuperuser`.

Validation: `docker-compose exec web python manage.py test store`.

## Customer and admin portals

- Customer storefront: http://127.0.0.1:8000/
- Admin login and inventory dashboard: http://127.0.0.1:8000/admin/
- Product management: `/admin/store/product/`
- Variant stock and prices: `/admin/store/productvariant/`
- Categories: `/admin/store/category/`

The first local owner account can be created with
`docker-compose exec web python manage.py setup_local_admin`. This creates a random password and
writes it to `.local/admin-access.txt` with owner-only file permissions. Existing
superuser accounts are never overwritten. Change the generated password using the
admin **Change password** link. The `.local/` folder is excluded from version control.

The admin portal uses Django staff login and model permissions. Regular storefront
visitors and non-staff users cannot access it. The owner can create additional staff
accounts and assign product, variant and category permissions under Users / Groups.

For a product without options, edit its stock quantity directly. For a product with
options, edit quantities and prices on the variant rows (or the Variant stock page).
The product starting price follows the lowest-priced purchasable variant. Blank
quantity means **not tracked**, preserving the imported catalog's unknown counts;
zero means **sold out**. Low-stock filters show quantities from 1 to 5. Stock caps
are checked when adding to the cart and rechecked when viewing the cart.

Cart additions do not reserve or deduct stock. Checkout, payment processing and
order-based inventory deductions are not implemented yet. Published and available
are separate controls: Published makes a product visible; Available allows sales
subject to stock and sample restrictions. Samples cannot be purchased.

Upload new product photos in the admin's Photos section. Uploaded photos take
precedence over legacy static images. They are stored under `media/`, served by
Django for local development, and excluded from version control. Back up both
`db.sqlite3` and `media/` to preserve your catalog and uploads.

## Customer accounts

The Account header link now opens `/account/`. Guests are sent to the customer
sign-in page; customers can register with their name, email and password.

- `/account/register/` — create a customer account (never staff/admin).
- `/account/login/` — email and password login, with optional 14-day session.
- `/account/` — account overview.
- `/account/profile/` — name and phone number.
- `/account/addresses/` — add, edit and delete saved addresses; choose a default.
- `/account/wishlist/` — database-backed wishlist, shared across signed-in devices.
- `/account/password/` — change password while signed in.
- `/account/password/reset/` — request a token-based password reset.
- `/account/orders/` — empty order-history page; checkout/orders are not connected.
- `/account/logout/` — POST-only sign out.

SQLite stores login records in Django's `auth_user` table, and customer details in
`store_customerprofile`, `store_customeraddress` and `store_wishlistitem`. Passwords
are hashed by Django. Customer forms cannot grant staff privileges; address and
wishlist operations are scoped to the signed-in user. Account pages are not cached.
The local login and registration forms limit repeated failed attempts per IP using
Django's local-memory cache (reset on server restart).

Guest favourites remain browser-local. On sign-in, up to 100 guest favourites merge
into the account, and the guest storage is cleared. Customer wishlists are kept out
of guest storage. Existing guest cart items remain in the session after login.

Manage customers at `/admin/store/customerprofile/`, saved addresses at
`/admin/store/customeraddress/`, and wishlists at `/admin/store/wishlistitem/`.
Use Django's Users page for login status, names and email. Customer usernames are
their lowercase sign-in email; when changing an email administratively, update both
Username and Email address together. Staff/model permissions control this access.

### Local password recovery and email setup

By default, reset emails are written to `.local/emails/` instead of sent. For local
testing, open the generated file and follow its reset link. Messages never reveal
passwords. Unknown email addresses receive the same request confirmation.

To deliver messages through your email provider, set environment variables before
starting Django:

- `DJANGO_EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`
- `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`
- `EMAIL_USE_TLS=true` and `DEFAULT_FROM_EMAIL` for your verified sender.

Do not commit these credentials. The application signing key is generated once in
`.local/django-secret-key` with owner-only permissions; `DJANGO_SECRET_KEY` can
override it. The local key persists across restarts. Back it up privately alongside
your database. Replacing it signs out existing sessions and invalidates reset links.

Product descriptions are stored in SQLite and remain editable in the product admin.
Original ASTROL copy and its research links are saved in `store/data/product_descriptions.json`.
The catalog matches reference products by source ID and original/sample products by slug.
Descriptions cover product details, traditional use and care; sample specifications remain unconfirmed.

To populate missing or original placeholder descriptions after a fresh setup:

```sh
docker-compose exec web python manage.py update_product_descriptions --dry-run
docker-compose exec web python manage.py update_product_descriptions
```

The seed/import commands also apply these descriptions. Later merchant edits are preserved by
this description command unless `--overwrite` is supplied. Each update first saves the previous
description fields to `.local/description-backups/`. Prices, inventory, images and customer data
are not changed. The catalog is an editorial snapshot, not a live supplier specifications feed.

Country and currency display
----------------------------
The storefront country selector remembers a visitor's choice in a one-year cookie.
Country/region mappings and currency precision use Babel's CLDR data. Product and
variant prices in SQLite/admin remain INR; converted storefront prices are estimates,
not payment quotes or shipping eligibility. Unsupported currencies fall back to USD,
or INR if no cached USD rate exists. Cart totals sum rounded converted unit prices.

Fetch exchange rates after installation and schedule this command once daily:

```sh
docker-compose exec web python manage.py refresh_exchange_rates
```

Rates come from https://www.exchangerate-api.com/docs/free and are cached privately in
`.local/exchange-rates.json`. Storefront requests never depend on an external API call.
Failed refreshes preserve the previous cache; the displayed date and a stale-rate note
identify older estimates. Without a cache the store remains usable in INR. The refresh
command is provided; no operating-system scheduler has been installed. Country selection
does not add checkout, payment processing, taxes, or international delivery rules.

Footer help and enquiries
------------------------
Footer links lead to `/pages/refund-policy/`, `/pages/privacy-policy/`,
`/pages/shipping-policy/`, `/pages/cancellation-policy/`, `/pages/terms-of-services/`,
`/pages/faqs/`, `/contact/` and `/newsletter/`.

Admin > Information pages lets the owner edit each help page. Policy pages explicitly
mark unconfirmed business terms; finalize these for ASTROL before accepting orders.
Admin > Store contacts controls the support email, WhatsApp number and social URLs.
Blank contact/social values are not shown; no reference-site contact details are used.
Support enquiries and Newsletter subscribers are saved in SQLite and managed in admin.
These forms do not send email or start marketing campaigns. Newsletter consent is required.

## Docker Compose development

Install/start Docker Desktop (or Docker Engine with Compose). From this folder:

```sh
docker-compose up --build -d --wait
```

Open **http://127.0.0.1:8000/** (admin: `/admin/`). Optionally copy `.env.example`
to `.env` and change `ASTROL_PORT` if another host port is needed.

First startup runs migrations and loads all 433 catalog listings into a **separate**
SQLite database. Existing catalog entries are never reseeded on restart. Existing
host customer accounts, contact settings, uploaded files and admin edits are not
imported. Create a container administrator and refresh currency rates with:

```sh
docker-compose exec web python manage.py createsuperuser
docker-compose exec web python manage.py refresh_exchange_rates
```

Until rates are fetched, currency display falls back to INR. Contact details can be
entered in the container's admin under Store contacts.

Useful commands:

```sh
docker-compose logs -f web
docker-compose exec web python manage.py test store
docker-compose down
docker-compose up --build --watch
```

Watch mode syncs source/templates/assets and restarts after Python changes; dependency
changes rebuild the image. Requires Docker Compose 2.23+ for sync-and-restart.
Normal `up --build` is available without watch mode.

Named volumes persist SQLite (`database`), uploads (`uploads`), and secrets/rate cache/
file-based email (`local_state`). `docker-compose down` preserves them; **adding `-v`
deletes the container's saved data**. The image excludes the host database, `.local`,
`.env`, uploads and credentials. The application runs as a non-root user. This is a
local development setup using Django's development server, with access bound to
127.0.0.1; it is not an internet-facing production deployment.
