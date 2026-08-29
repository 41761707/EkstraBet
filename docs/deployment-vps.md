# Wdrożenie EkstraBet na VPS

Dokument opisuje przygotowanie hosta Ubuntu/Debian pod produkcyjny stack
z [compose.production.yml](../compose.production.yml): nginx z TLS na hoście,
Next.js na `127.0.0.1:3000`, FastAPI i MySQL tylko w prywatnej sieci Compose.

Idź **sekcja po sekcji** przy pierwszym wdrożeniu — każda zakłada, że
poprzednie są zrobione. Nie uzupełniaj wszystkich plików env „na zapas”
na początku: hasła DB najpierw **wymyslasz** (sekcja 7), a konta MySQL
zakładasz **później** tymi samymi wartościami (sekcja 9.3).

| Etap | Sekcje | Co dostajesz |
|------|--------|--------------|
| Host | 1–5 | użytkownik, SSH, UFW, Docker |
| Kod i sekrety | 6–7 | repo, `APP_ORIGIN`, `mysql.env` / `api.env` / `frontend.env` |
| Proxy | 8 | nginx + TLS |
| Baza i stack | 9 | MySQL → import `.sql` → konta → `api`/`frontend` |
| Odbiór hosta | 10 | checklista SZP-70 |
| Backup | 11 | `backup.env`, timer, restore (SZP-71) |
| Wydania | 12 | runbook release/rollback (SZP-72) |
| Bezpieczeństwo | 13 | checklista SZP-73 |

## 1. Założenia

- Publiczne porty VPS: wyłącznie `22`, `80`, `443` (`80` tylko redirect na HTTPS).
- Aplikacja dostępna wyłącznie przez nginx → `127.0.0.1:3000`.
- FastAPI (`8000`) i MySQL (`3306`) **nie** są mapowane na host — brak dostępu z Internetu.
- W sieci Compose: API łączy się z MySQL jako host `mysql`, port `3306`
  (nazwa usługi + standardowy port obrazu). Operator **nie** wybiera wolnego
  portu na VPS.
- Certyfikat TLS dostarcza operator (istniejące pliki lub certbot) — ścieżki w nginx.

## 2. Użytkownik systemowy i katalog sekretów

Wdrożenie zakłada **jedno konto operatorskie** na VPS (domyślnie `radikey`) — logowanie
kluczem SSH, Docker i Compose z tego samego użytkownika. Osobne konto `ekstrabet`
**nie jest wymagane**.

Na tym etapie tworzysz katalog sekretów (pliki `*.env` w sekcji 7, `backup.env` w 11).
Jeśli `radikey` już istnieje, pomiń `adduser`.

```bash
DEPLOY_USER=radikey   # dostosuj, jeśli inna nazwa

# Tylko gdy konto jeszcze nie istnieje:
# sudo adduser --disabled-password --gecos "" "${DEPLOY_USER}"

# Grupę docker dodaj po instalacji Dockera (sekcja 5):
# sudo usermod -aG docker "${DEPLOY_USER}"

sudo mkdir -p /etc/ekstrabet/tls
sudo chown -R "${DEPLOY_USER}:${DEPLOY_USER}" /etc/ekstrabet
sudo chmod 700 /etc/ekstrabet /etc/ekstrabet/tls
```

Docelowe pliki env (powstaną później):

| Plik | Kiedy | Szablon |
|------|-------|---------|
| `/etc/ekstrabet/mysql.env` | sekcja 7.1 | [deploy/mysql.env.example](../deploy/mysql.env.example) |
| `/etc/ekstrabet/api.env` | sekcja 7.2 | [.env.example](../.env.example) |
| `/etc/ekstrabet/frontend.env` | sekcja 7.3 | [frontend/.env.local.example](../frontend/.env.local.example) |
| `/etc/ekstrabet/backup.env` | sekcja 11.1 | przykłady w sekcji 11 |
| `/path/to/EkstraBet/.env` | sekcja 6 | tylko `APP_ORIGIN` (+ opcjonalnie `EKSTRABET_ENV_DIR`) |

**Nie** commituj prawdziwych sekretów. **Nie** kopiuj ich do obrazów Docker.

## 3. SSH (klucz, bez hasła i bez roota)

1. Dodaj swój klucz publiczny do `~radikey/.ssh/authorized_keys` (tryb `600`, katalog `.ssh` → `700`).
2. Sprawdź logowanie kluczem na konto `radikey` **w drugiej sesji**, zanim wyłączysz hasła.
3. W `/etc/ssh/sshd_config` (lub drop-in w `sshd_config.d/`):

```
PermitRootLogin no
PasswordAuthentication no
KbdInteractiveAuthentication no
PubkeyAuthentication yes
```

4. `sudo sshd -t && sudo systemctl reload ssh` (lub `ssh.service`).

## 4. Firewall (UFW) i aktualizacje

```bash
sudo apt update && sudo apt upgrade -y
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status verbose
```

Oczekiwane defaults: `deny (incoming)`, `allow (outgoing)`; otwarte tylko
22 / 80 / 443 (IPv4 + IPv6). Duplikat `Nginx Full` obok `80/tcp`+`443/tcp`
jest nieszkodliwy.

Opcjonalnie fail2ban (SSH):

```bash
sudo apt install -y fail2ban
sudo systemctl enable --now fail2ban
```

Włącz unattended-upgrades albo inny proces aktualizacji bezpieczeństwa dystrybucji.

## 5. Docker i Compose

Zainstaluj Docker Engine oraz wtyczkę Compose zgodnie z dokumentacją Docker
dla Ubuntu/Debian. Potem:

```bash
sudo usermod -aG docker radikey
# Wyloguj się i zaloguj ponownie (albo newgrp docker), żeby grupa zadziałała
```

Użytkownik deploy (`radikey`) musi móc uruchamiać `docker` (grupa `docker` lub
rootless — wybór operatora). Smoke `compose config` zrób **po** sekcji 6–7
(gdy są `APP_ORIGIN` i pliki env).

## 6. Repozytorium i `APP_ORIGIN`

Sklonuj / skopiuj repozytorium na VPS (np. `/home/radikey/projects/EkstraBet`).
Checkout oznaczonego tagu wydania — szczegóły w sekcji 12; przy pierwszym setupie
wystarczy tag lub branch, z którego budujesz.

Compose wymaga `APP_ORIGIN` przy każdym `config` / `up` (interpolacja
`${APP_ORIGIN:?…}` w [compose.production.yml](../compose.production.yml)).
Trwałe źródło: plik `.env` **w katalogu repozytorium obok** Compose
(Compose ładuje go automatycznie; plik jest w `.gitignore`):

```bash
cd /path/to/EkstraBet
# Plik .env — same KEY=value, bez komentarzy:
# APP_ORIGIN=https://twoja-domena
# EKSTRABET_ENV_DIR=/etc/ekstrabet   # tylko gdy nie używasz domyślnego /etc/ekstrabet

chown radikey:radikey /path/to/EkstraBet/.env
chmod 600 /path/to/EkstraBet/.env
```

Nie polegaj wyłącznie na `export` w sesji shell — po restarcie VPS / nowej
sesji SSH Compose musi nadal widzieć `APP_ORIGIN`. Plik `.env` musi być czytelny
dla użytkownika deploy (`radikey`) — stąd `radikey:radikey` i `600`, nie `root`-only.

## 7. Pliki env przed pierwszym startem

Uzupełnij trzy pliki poniżej **zanim** odpalisz MySQL. Hasła kont aplikacji
w `api.env` **wymyslasz teraz** (silne, losowe) i zapisujesz — w sekcji 9.3
użyjesz **tych samych** wartości w `CREATE USER`. Nie musisz „znać” portu
MySQL z hosta: w Compose zawsze `DB_HOST=mysql`, `DB_PORT=3306`.

Po uzupełnieniu:

```bash
sudo chown radikey:radikey /etc/ekstrabet/*.env
sudo chmod 600 /etc/ekstrabet/*.env
```

### 7.1 `mysql.env` — root kontenera MySQL

Szablon: [deploy/mysql.env.example](../deploy/mysql.env.example) →
`/etc/ekstrabet/mysql.env` (same `KEY=value`, bez komentarzy).

```bash
MYSQL_ROOT_PASSWORD=…silne_hasło_które_TY_wymyslasz…
MYSQL_DATABASE=ekstrabet
```

Obraz `mysql:8.4` przy **pierwszym** starcie (pusty volume) sam zakłada
użytkownika MySQL `root` z tym hasłem oraz pustą bazę `MYSQL_DATABASE`.
To **nie** jest root Linux/SSH. Konta `ekstrabet_api` / backup **nie** trafiają
do tego pliku.

### 7.2 `api.env` — API / backend

Szablon: [.env.example](../.env.example) → `/etc/ekstrabet/api.env`.

Compose **nadpisuje** przy starcie: `DB_HOST=mysql`, `DB_PORT=3306`,
`DB_NAME` (z `MYSQL_DATABASE` / domyślnie `ekstrabet`), `ENVIRONMENT`,
`TRUSTED_HOSTS`. W pliku i tak ustaw spójne wartości produkcyjne:

```bash
ENVIRONMENT=production
DEBUG=false
OPENAPI_ENABLED=false

# Sieć Compose — nie localhost, nie publiczny IP VPS:
DB_HOST=mysql
DB_PORT=3306
DB_NAME=ekstrabet
# Konto, które założysz w MySQL w sekcji 9.3 (NIE root):
DB_USER=ekstrabet_api
DB_PASSWORD=…to_samo_hasło_pójdzie_do_CREATE_USER…

SECRET_KEY=…losowy_sekret_≥32_znaki…
AUTH_ENABLED=true
AUTH_COOKIE_NAME=ekstrabet_token
ACCESS_TOKEN_EXPIRE_MINUTES=1440
EKSTRABET_ML_PREVIEW=false

# Ten sam origin co APP_ORIGIN z sekcji 6 (JSON list, bez *):
CORS_ORIGINS=["https://twoja-domena"]
CORS_METHODS=["GET","POST","PUT","DELETE"]
# Compose i tak ustawi TRUSTED_HOSTS; dla jasności możesz mieć:
TRUSTED_HOSTS=["api","127.0.0.1","localhost"]
```

Runtime API używa **`CORS_ORIGINS`**. Pole `FRONTEND_ORIGIN` w szablonie
**nie jest używane** przez kod — nie polegaj na nim.
`DB_USER=root` w production jest odrzucane (fail-closed).

### 7.3 `frontend.env`

Szablon: [frontend/.env.local.example](../frontend/.env.local.example) →
`/etc/ekstrabet/frontend.env`.

Compose nadpisuje `API_BASE_URL=http://api:8000` oraz `APP_ORIGIN` z pliku
`.env` Compose (sekcja 6). W `frontend.env` ustaw m.in.:

```bash
ENVIRONMENT=production
AUTH_ENABLED=true
AUTH_COOKIE_NAME=ekstrabet_token
# Dla czytelności (Compose i tak nadpisze API_BASE_URL):
API_BASE_URL=http://api:8000
# NIE ustawiaj NEXT_PUBLIC_API_BASE_URL w production
CHAT_ENABLE_CURSOR=false
NEXT_PUBLIC_CHAT_ENABLE_CURSOR=false
# + klucze chat / OpenRouter według potrzeb
```

Produkcja fail-closed odrzuca `CHAT_ENABLE_CURSOR=true` /
`NEXT_PUBLIC_CHAT_ENABLE_CURSOR=true`.

### 7.4 Smoke konfiguracji Compose

```bash
cd /path/to/EkstraBet
docker compose -f compose.production.yml config >/dev/null
```

Bez sekretów w logach. Błąd interpolacji `APP_ORIGIN` → wróć do sekcji 6.
Brak pliku env → uzupełnij 7.1–7.3.

## 8. nginx i TLS

Szablony:

- [deploy/nginx/ekstrabet-site.conf.example](../deploy/nginx/ekstrabet-site.conf.example)
  → `sites-available/` (redirect HTTP→HTTPS, proxy na `127.0.0.1:3000`)
- [deploy/nginx/ekstrabet-limits.conf.example](../deploy/nginx/ekstrabet-limits.conf.example)
  → `/etc/nginx/conf.d/` — **opcjonalnie** (`limit_req` na login/chat; SZP-70)

Monolit [deploy/nginx/ekstrabet.conf.example](../deploy/nginx/ekstrabet.conf.example)
jest **obsolete** — nie kopiuj go do `sites-available`.

Pełny test HTTPS z Next.js zrobisz po sekcji 9.4. Teraz wystarczy poprawny
`nginx -t` i certyfikaty na miejscu.

**Cloudflare:** w Dashboard ustaw **Full (strict)**. Cert na VPS jak zwykle (np.
`/etc/ssl/domena.crt`) — osobna konfiguracja nginx pod CF nie jest potrzebna.

```bash
sudo apt install -y nginx

cd /path/to/EkstraBet
sudo cp deploy/nginx/ekstrabet-site.conf.example \
  /etc/nginx/sites-available/ekstrabet
# Edytuj: server_name, ścieżki ssl_certificate / ssl_certificate_key
sudo ln -sf /etc/nginx/sites-available/ekstrabet /etc/nginx/sites-enabled/ekstrabet
sudo nginx -t
sudo systemctl reload nginx
```

W `location /` szablon ma `proxy_http_version 1.1`, `proxy_buffering off`
i `proxy_read_timeout 60s` — Next.js streamuje RSC; buffering nginx psuje
nawigację po loginie i zmianie filtrów. Jeśli site na VPS powstał ze
starszej kopii, dopisz te dyrektywy i `sudo nginx -t && sudo systemctl reload nginx`.

Sprawdzenia (po starcie frontendu w 9.4):

- `curl -I http://example.com` → `301` na HTTPS;
- `curl -IK https://example.com` → `200`/`3xx` z Next.js; nagłówki
  `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`, `X-Frame-Options`, CSP;
- z zewnątrz zamknięte: `3000`, `8000`, `3306` (np. skan portów / `nc`);
- brak publicznego location nginx do FastAPI.

**HSTS:** w szablonie jest zakomentowane. Włącz `Strict-Transport-Security`
dopiero po potwierdzeniu poprawnego HTTPS (sekcja 12.6), potem `nginx -t`
i reload.

Limity `limit_req` obejmują m.in.:

- `/api/auth/login`
- `/api/chat` (i podścieżki)
- `/api/backend/predictions/preview`

## 9. Pierwszy start: MySQL → dane → konta → stack

Kolejność jest ważna: najpierw sama baza, potem import, potem konta aplikacji,
na końcu `api`/`frontend`.

### 9.1 Start tylko MySQL

```bash
cd /path/to/EkstraBet
docker compose -f compose.production.yml up -d mysql
docker compose -f compose.production.yml ps
# Czekaj aż mysql = healthy (healthcheck w Compose)
```

Przy pierwszym starcie obraz tworzy `root` z hasła z `mysql.env` i bazę
`ekstrabet` (lub inną z `MYSQL_DATABASE`).

### 9.2 Pierwsze wgranie lokalnej bazy (jednorazowo)

**W skrócie:** na VPS baza startuje pusta. Twoje dane (tabele + zawartość)
są w pliku SQL z komputera — np. `ekstrabet_backup_31_07_2026.sql`.
Trzeba ten plik skopiować na serwer i wczytać do kontenera MySQL.
Sekcja 11 (codzienny backup `.sql.gz.enc`) to **coś innego**: działa dopiero
**po** tym, gdy dane już są na VPS.

Konta API / model / backup (9.3) zakładaj **po** imporcie — dump zwykle nie
przenosi użytkowników MySQL, tylko tabele i dane.

**Krok 1 — skopiuj dump na VPS** (z komputera, w katalogu z plikiem):

```bash
scp ekstrabet_backup_31_07_2026.sql radikey@ADRES_VPS:~/
```

**Krok 2 — na VPS wczytaj plik.** Hasło = `MYSQL_ROOT_PASSWORD` z
`/etc/ekstrabet/mysql.env`. Nazwa bazy = `MYSQL_DATABASE` (domyślnie `ekstrabet`).

```bash
cd /path/to/EkstraBet
# api/frontend i tak jeszcze nie działają przy pierwszym setupie; przy ponownym imporcie:
docker compose -f compose.production.yml stop api frontend 2>/dev/null || true

cat ~/ekstrabet_backup_31_07_2026.sql | docker compose -f compose.production.yml exec -T \
  -e MYSQL_PWD='…hasło_root_z_mysql.env…' \
  mysql mysql -uroot ekstrabet
```

Jeśli dump zaczyna się od `CREATE DATABASE` / `USE inna_nazwa`, albo
import kończy się błędem „Unknown database”, dopasuj nazwę bazy w komendzie
albo w pliku SQL do tej z `mysql.env` (zwykle `ekstrabet`).

**Krok 3 — sprawdź dane:**

```bash
docker compose -f compose.production.yml exec -T \
  -e MYSQL_PWD='…hasło_root_z_mysql.env…' \
  mysql mysql -uroot ekstrabet \
  -e "SHOW TABLES; SELECT COUNT(*) AS tables_ok FROM information_schema.tables WHERE table_schema='ekstrabet';"
```

**Krok 4 — posprzątaj plaintext:**

```bash
shred -u ~/ekstrabet_backup_31_07_2026.sql   # albo: rm ~/ekstrabet_backup_31_07_2026.sql
```

Nie commituj dumpa do Gita.

### 9.3 Konta MySQL (ręcznie)

Zaloguj się jako `root` MySQL (hasło z `mysql.env`) i załóż konta **z hasłami
już zapisanymi** w `api.env` (i później w `backup.env`). Brak skryptów
bootstrap/migracji w tym wydaniu.

Przykład konta API (odczyt całej bazy + zapis tylko na tabelach konta;
hasło = `DB_PASSWORD` z `api.env`). Na istniejącym VPS, gdzie konto było
SELECT-only, uruchom [sql/grant_ekstrabet_api_app_writes.sql](../sql/grant_ekstrabet_api_app_writes.sql):

```sql
CREATE USER 'ekstrabet_api'@'%' IDENTIFIED BY '…to_samo_co_DB_PASSWORD_w_api.env…';
GRANT SELECT, SHOW VIEW ON ekstrabet.* TO 'ekstrabet_api'@'%';
GRANT UPDATE (username, password_hash, display_name, first_login, updated_at)
  ON ekstrabet.users TO 'ekstrabet_api'@'%';
GRANT INSERT, UPDATE ON ekstrabet.user_preferences TO 'ekstrabet_api'@'%';
GRANT INSERT, UPDATE, DELETE
  ON ekstrabet.user_favorite_leagues TO 'ekstrabet_api'@'%';
FLUSH PRIVILEGES;
```

- konto modeli — odczyt + ograniczony zapis na tabelach pipeline; osobne hasło
  (nie w `api.env` produkcyjnym, jeśli job idzie poza Compose API);
- konto backup — minimalne prawa pod dump (sekcja 11.1); osobne hasło w
  `backup.env` (możesz założyć konto już teraz albo przy konfiguracji backupu).

Root MySQL nie powinien być dostępny zdalnie ani używany przez aplikację.
Z hosta VPS port `3306` i tak nie jest opublikowany.

Wejście do klienta MySQL:

```bash
docker compose -f compose.production.yml exec -it \
  -e MYSQL_PWD='…hasło_root_z_mysql.env…' \
  mysql mysql -uroot ekstrabet
```

### 9.4 Start API i frontendu

```bash
cd /path/to/EkstraBet
docker compose -f compose.production.yml up -d --build --wait
docker compose -f compose.production.yml ps
```

Oczekiwane: `mysql`, `api`, `frontend` = healthy. Przy błędzie startu API
sprawdź fail-closed (`SECRET_KEY`, `AUTH_ENABLED`, CORS, `DB_USER`) w
`docker compose -f compose.production.yml logs api --tail 100` — **bez**
kopiowania sekretów do ticketów.

Szybki smoke (pełny: sekcja 12.4):

```bash
curl -fsS http://127.0.0.1:3000/api/health
docker compose -f compose.production.yml exec -T api \
  python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/ready', timeout=5)"
```

Potem: checklista sekcji 10 → backup (11) → runbook / DNS (12).

### 9.5 Cykliczny sync lokal → produkcja

Po pierwszym imporcie (9.2) scrapery nadal piszą do bazy lokalnej. Skrypt
[scripts/sync_local_to_prod.py](../scripts/sync_local_to_prod.py) dogania produkcję
**bez** otwierania MySQL na świat (SSH + `docker compose exec`).

Strategie:

- **słowniki** (`teams`, `players`, `leagues`, …): `id > max(id)` na prod; okresowo `--full-dict`
- **mecze**: okno `game_date` (domyślnie 3 dni) **oraz** nowe `id`
- **dzieci meczów** (`odds`, stats, `predictions`, …): to samo okno przez `match_id`
- **append-only** (`transfers`): tylko `id > max(id)`
- **wykluczone**: `users`, `gamblers`, `gambler_parlays`, `parlay_events`

Konfiguracja: skopiuj [deploy/sync.env.example](../deploy/sync.env.example)
do `deploy/sync.env` (w `.gitignore`) i uzupełnij `SYNC_SSH_HOST` /
`SYNC_REMOTE_REPO`. Lokalne `DB_*` biorą się z `.env`.

```bash
# z maszyny deweloperskiej (dry-run — tylko zlicza wiersze)
python scripts/sync_local_to_prod.py

# zapis na produkcję
python scripts/sync_local_to_prod.py --apply

# pelny reconcile slownikow + węższe/szersze okno
python scripts/sync_local_to_prod.py --apply --full-dict --window-days 3
```

Transport `direct` (tunel `ssh -L`) ustawia się przez `SYNC_TRANSPORT=direct`
i `PROD_DB_*` w `sync.env`.

## 10. Minimalna weryfikacja hosta (checklista SZP-70)

- [ ] SSH: tylko klucz, `PermitRootLogin no`, hasła wyłączone (po teście drugiej sesji)
- [ ] UFW: otwarte tylko 22/80/443; `default deny incoming`
- [ ] `/etc/ekstrabet/*.env`: `radikey:radikey`, `0600`; brak sekretów w Git/obrazach
- [ ] `mysql.env` zawiera wyłącznie `MYSQL_ROOT_PASSWORD` + `MYSQL_DATABASE`
- [ ] Trwały `/path/to/EkstraBet/.env` z `APP_ORIGIN` (sekcja 6)
- [ ] nginx `-t` OK; ruch HTTPS kończy się w Next.js na `127.0.0.1:3000`
- [ ] HSTS świadomie wyłączone albo włączone po weryfikacji TLS
- [ ] Porty `3000` / `8000` / `3306` niedostępne z Internetu
- [ ] Pierwsze wgranie lokalnego dumpa `.sql` wykonane (sekcja 9.2), plaintext usunięty z VPS
- [ ] Konta MySQL API/model/backup utworzone ręcznie; API nie używa `root`
- [ ] Stack `up --wait` healthy (sekcja 9.4)

## 11. Backup, restore i retencja off-site (SZP-71)

Ta sekcja dotyczy **codziennych kopii na już działającym VPS** (plik
`.sql.gz.enc`). **Nie** służy do pierwszego przeniesienia bazy z laptopa —
to jest sekcja 9.2 (zwykły plik `.sql`).

MySQL nie ma mapowanego portu — dump i restore idą przez
`docker compose exec` do usługi `mysql` w [compose.production.yml](../compose.production.yml).
Skrypty: [scripts/backup_mysql.sh](../scripts/backup_mysql.sh),
[scripts/restore_mysql.sh](../scripts/restore_mysql.sh).

### 11.1 Konto backup i sekrety

Na hoście utwórz `/etc/ekstrabet/backup.env` (`radikey:radikey`, `0600`), same linie
`KEY=value` (bez komentarzy). Przykładowe klucze:

```bash
MYSQL_BACKUP_USER=ekstrabet_backup
MYSQL_BACKUP_PASSWORD=change_me_strong_backup_password
MYSQL_DATABASE=ekstrabet
BACKUP_DIR=/var/backups/ekstrabet
BACKUP_ENCRYPTION_PASSPHRASE=change_me_long_random_passphrase
EKSTRABET_ENV_DIR=/etc/ekstrabet
REQUIRE_OFFSITE=1
# Opcjonalnie do restore (DROP/CREATE pustej bazy testowej):
# MYSQL_ADMIN_USER=root
# MYSQL_ADMIN_PASSWORD=...   # tylko na hoście, nigdy w api.env
# Off-site (wymagane przy REQUIRE_OFFSITE=1 — domyślnie włączone):
OFFSITE_RSYNC_TARGET=backup-host:/var/backups/ekstrabet/
# OFFSITE_SYNC_CMD='rclone copy "$1" remote:ekstrabet-backups/'
RETENTION_DAILY=7
RETENTION_WEEKLY=4
RETENTION_MONTHLY=6
```

Minimalne uprawnienia konta dump (InnoDB, `--single-transaction`) — jeśli
jeszcze nie założyłeś w 9.3:

```sql
CREATE USER 'ekstrabet_backup'@'%' IDENTIFIED BY '…';
GRANT SELECT, SHOW VIEW, TRIGGER, EVENT, LOCK TABLES
  ON ekstrabet.* TO 'ekstrabet_backup'@'%';
FLUSH PRIVILEGES;
```

Hasło szyfrowania (`BACKUP_ENCRYPTION_PASSPHRASE`) trzymaj osobno od haseł DB —
obrót jednego sekretu nie wymaga zmiany pozostałych. Katalog
`BACKUP_DIR` powinien należeć do użytkownika uruchamiającego timer (np. `radikey`),
tryb katalogu `700`.

### 11.2 Codzienny backup

```bash
cd /path/to/EkstraBet
BACKUP_ENV_FILE=/etc/ekstrabet/backup.env \
  ./scripts/backup_mysql.sh
```

Skrypt: strumień `mysqldump | gzip | openssl` (AES-256-CBC, PBKDF2) — **bez**
plaintext SQL na dysku — do `BACKUP_DIR/daily/ekstrabet_YYYY-MM-DD.sql.gz.enc`
(+ `.sha256`). `umask 077`, katalogi `700`, pliki `600`. W niedzielę (UTC)
kopiuje też do `weekly/`, pierwszego dnia miesiąca do `monthly/`, potem przycina
retencję (domyślnie 7 / 4 / 6). Log w `BACKUP_DIR/logs/` **bez** haseł i passphrase.
Niezerowy kod wyjścia przy błędzie dump/compress/encrypt/sync.

`REQUIRE_OFFSITE=1` (domyślnie): brak `OFFSITE_SYNC_CMD` / `OFFSITE_RSYNC_TARGET`
kończy backup kodem ≠ 0. Lokalne próby: `REQUIRE_OFFSITE=0`.

### 11.3 Harmonogram (systemd timer)

Przykład jednostek (dostosuj ścieżki):

`/etc/systemd/system/ekstrabet-backup.service`:

```ini
[Unit]
Description=EkstraBet MySQL encrypted backup
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
User=radikey
Group=radikey
WorkingDirectory=/path/to/EkstraBet
Environment=BACKUP_ENV_FILE=/etc/ekstrabet/backup.env
# APP_ORIGIN: Compose czyta trwały .env z WorkingDirectory (sekcja 6);
# Environment= poniżej tylko jeśli .env jeszcze nie ma APP_ORIGIN
# Environment=APP_ORIGIN=https://twoja-domena
ExecStart=/path/to/EkstraBet/scripts/backup_mysql.sh
Nice=10
```

`/etc/systemd/system/ekstrabet-backup.timer`:

```ini
[Unit]
Description=Daily EkstraBet MySQL backup

[Timer]
OnCalendar=*-*-* 02:30:00
Persistent=true
RandomizedDelaySec=10m

[Install]
WantedBy=timers.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now ekstrabet-backup.timer
sudo systemctl list-timers ekstrabet-backup.timer
```

Alternatywa cron (użytkownik `radikey`):  
`30 2 * * * cd /path/to/EkstraBet && BACKUP_ENV_FILE=/etc/ekstrabet/backup.env ./scripts/backup_mysql.sh`

### 11.4 Test restore (obowiązkowy przed produkcją)

1. Upewnij się, że masz świeży plik `.sql.gz.enc` i `.sha256`.
2. Odtwórz **najpierw do pustej bazy testowej** (nie do `ekstrabet`).
   Przy `MYSQL_ADMIN_*` skrypt robi `DROP DATABASE` + `CREATE DATABASE`
   (bezpieczne przy VIEW-ach, powtarzalne):

```bash
cd /path/to/EkstraBet
BACKUP_ENV_FILE=/etc/ekstrabet/backup.env \
  ./scripts/restore_mysql.sh \
    --file /var/backups/ekstrabet/daily/ekstrabet_YYYY-MM-DD.sql.gz.enc \
    --target-database ekstrabet_restore_test \
    --confirm YES_I_UNDERSTAND_DATA_LOSS
```

3. Sprawdź `table_count` w stdout oraz przykładowe `SELECT COUNT(*)` na kluczowych
   tabelach względem produkcji / dokumentacji schematu. Powtórz restore do tej
   samej bazy testowej — drugi przebieg też musi przejść.
4. Symulacja błędu miejsca docelowego: ustaw `OFFSITE_RSYNC_TARGET` na
   nieistniejący host — `backup_mysql.sh` musi zakończyć się kodem ≠ 0.
   Brak jakiegokolwiek targetu off-site przy `REQUIRE_OFFSITE=1` również ≠ 0.
5. Dopiero po udanym teście rozważ restore produkcyjny (osobne wywołanie z
   `--target-database ekstrabet` i ponownym `--confirm`). Preferuj restore na
   czystym wolumenie / po zatrzymaniu API, nie „w locie” na żywej aplikacji.

Skrypt **odmawia** działania bez dokładnej frazy `--confirm YES_I_UNDERSTAND_DATA_LOSS`.

### 11.5 Checklista SZP-71

- [ ] `/etc/ekstrabet/backup.env` istnieje, `0600`, osobne hasło backup + passphrase
- [ ] Konto MySQL backup ma tylko prawa do dump (bez zbędnego zapisu aplikacji)
- [ ] `backup_mysql.sh` tworzy `.sql.gz.enc` + `.sha256` (bez plaintextu); pliki `600`
- [ ] Retencja lokalna: daily/weekly/monthly zgodnie z polityką
- [ ] Kopia off-site skonfigurowana; `REQUIRE_OFFSITE=1` egzekwowane
- [ ] Timer/cron codzienny włączony (`systemctl list-timers` lub crontab)
- [ ] Restore do `ekstrabet_restore_test` OK dwa razy z rzędu (checksum + liczba tabel)
- [ ] Celowo zły / brakujący off-site target kończy backup niezerowym kodem wyjścia

## 12. Runbook wydania i rollbacku (SZP-72)

Cel: drugi operator ma wykonać release i rollback **wyłącznie** z tej sekcji
(oraz powiązanych sekcji 1–11), bez wiedzy autora. Pierwsze wydanie jest
kontrolowanym wdrożeniem z **oznaczonego tagu Git** — nie z każdego pusha.
Brak procedury migracji schematu SQL w tym runbooku (schemat poza Git).
Pierwsze dane: sekcja 9.2 (lokalny plik `.sql`). Późniejsza ochrona =
backup/restore z sekcji 11.

### 12.1 Warunki wstępne

Przed pierwszym lub kolejnym wydaniem muszą być spełnione:

1. Host, Docker, UFW, SSH, nginx/TLS, katalog `/etc/ekstrabet` — sekcje 1–8, 10.
2. Pliki `mysql.env`, `api.env`, `frontend.env` (i `backup.env`) uzupełnione,
   `0600`, `radikey:radikey`. W `api.env`: `CORS_ORIGINS=["https://…"]`
   **zgodne z** `APP_ORIGIN` (sekcja 7.2); `ACCESS_TOKEN_EXPIRE_MINUTES=1440`;
   `EKSTRABET_ML_PREVIEW=false`. W `frontend.env`: Cursor chat wyłączony.
3. **Trwały** plik `/path/to/EkstraBet/.env` z `APP_ORIGIN=https://…`
   (`radikey:radikey`, `600`) — sekcja 6. Bez niego `compose config` / `up`
   kończy się błędem interpolacji; sam `export` w shellu nie wystarcza po
   restarcie ani w systemd.
4. Lokalna baza wgrana na VPS (sekcja 9.2); plaintext dump usunięty z serwera.
5. Konta MySQL API / model / backup założone ręcznie (sekcja 9.3 i 11.1).
6. Backup + off-site + udany test restore do bazy testowej (sekcja 11.4–11.5).
7. Znany tag wydania (np. `v1.0.0`) oraz poprzedni działający tag (do rollbacku).

Zanotuj przed startem (do rollbacku):

```bash
cd /path/to/EkstraBet
git rev-parse --short HEAD
git describe --tags --exact-match 2>/dev/null || true
# APP_ORIGIN pochodzi z .env obok Compose (sekcja 6)
grep -E '^(APP_ORIGIN|EKSTRABET_ENV_DIR)=' .env
docker compose -f compose.production.yml images
```

### 12.2 Preflight backupu

Przed każdym `up --build` na produkcji:

```bash
cd /path/to/EkstraBet
BACKUP_ENV_FILE=/etc/ekstrabet/backup.env \
  ./scripts/backup_mysql.sh
```

Sprawdź: świeży plik w `BACKUP_DIR/daily/*.sql.gz.enc` + `.sha256`, kod wyjścia `0`,
wpis w logu bez sekretów, kopia off-site przyjęta. Przy pierwszym wydaniu na
pustej bazie (brak danych do ochrony) preflight dump nadal warto uruchomić
po pierwszym udanym starcie MySQL — przed przełączeniem DNS.

### 12.3 Checkout tagu, build i start

```bash
cd /path/to/EkstraBet
# sesja SSH jako radikey
git fetch --tags origin
git checkout <TAG>          # np. v1.0.0 — tylko oznaczony tag wydania

# APP_ORIGIN / EKSTRABET_ENV_DIR z trwałego .env (12.1) — bez export w sesji
docker compose -f compose.production.yml config >/dev/null
# --wait: blokuj do healthy (unikaj fałszywego faila curl w start_period)
docker compose -f compose.production.yml up -d --build --wait
docker compose -f compose.production.yml ps
```

Oczekiwane: `up --wait` kończy się kodem 0; `ps` pokazuje `mysql`, `api`,
`frontend` jako healthy. Dopiero wtedy przejdź do smoke (12.4).
Przy błędzie startu API sprawdź fail-closed (sekrety, `AUTH_ENABLED`, CORS, `DB_USER`)
w `docker compose -f compose.production.yml logs api --tail 100` — **bez**
kopiowania sekretów do ticketów.

Pierwsze wydanie: uruchom stack **bez** publicznego DNS (lub z tymczasową
nazwą / hosts), dokończ smoke (12.4), dopiero potem sekcja 12.6.
Przy **pierwszym** setupie zamiast pełnego `up` od razu użyj kolejności z
sekcji 9 (MySQL → import → konta → stack).

### 12.4 Health i smoke test

Dopiero po udanym `up --wait` z 12.3 (wszystkie healthy). Domenę zastąp swoją;
lokalnie: `127.0.0.1` / `curl --resolve`.

```bash
# 1) Stan Compose (potwierdzenie po --wait)
docker compose -f compose.production.yml ps

# 2) Liveness Next.js (host → loopback; api/health jest wyłączone z auth middleware)
curl -fsS http://127.0.0.1:3000/api/health

# 3) Readiness API (tylko sieć Compose — nie z Internetu)
docker compose -f compose.production.yml exec -T api \
  python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/ready', timeout=5)"

# 4) HTTPS przez nginx (po podłączeniu certyfikatu)
curl -fsSI https://twoja-domena/ | head -n 20
curl -fsS https://twoja-domena/api/health

# 5) Bez cookie → 401 (middleware Next łapie /api/* poza api/health i api/auth
#    zanim BFF oceni allowlistę — bez sesji zawsze 401, nie 403)
curl -sS -o /dev/null -w '%{http_code}\n' \
  https://twoja-domena/api/backend/leagues
# Oczekiwane: 401 (nie 502/504)

# 6) Login (konta zamkniętej grupy) — ręcznie w przeglądarce:
#    formularz logowania → cookie HttpOnly → strona główna / predykcje

# 7) Porty z zewnątrz zamknięte (z innego hosta / skan):
#    3000, 8000, 3306 — connection refused / filtered
```

Weryfikacja 403 BFF (ścieżka poza allowlistą / zła metoda) wymaga **ważnej
sesji** — pełna macierz odbioru to sekcja 13 (SZP-73); w smoke SZP-72
wystarczy krok 5 (401 bez cookie).

Nie oczekuj publicznego `/docs` ani `/openapi.json` (OpenAPI produkcyjnie wyłączone).
Nginx nie proxy’uje do FastAPI — smoke API tylko przez BFF lub `compose exec`.

### 12.5 Obserwacja logów

Po udanym smoke obserwuj przez co najmniej kilka minut (po DNS — dłużej):

```bash
docker compose -f compose.production.yml logs -f --tail=200 frontend api
```

Szukaj: powtarzających się 5xx, restartów kontenerów, błędów DB/auth.
Logi kontenerów rotują się (`max-size` / `max-file` w Compose). Aplikacja nie
powinna logować haseł, JWT ani pełnych zapytań z danymi. `docker compose logs`
nie zapisuj do repozytorium.

### 12.6 Przełączenie DNS i HSTS

1. Smoke (12.4) OK na stacku z poprawnym TLS.
2. Ustaw DNS A/AAAA na publiczny IP VPS (TTL świadomie krótki przy pierwszym cutover).
3. Po propagacji powtórz `curl -fsSI https://twoja-domena/` oraz login w przeglądarce.
4. Dopiero wtedy włącz HSTS w nginx (sekcja 8), `nginx -t`, `systemctl reload nginx`.
5. Włącz / potwierdź timer backupu (sekcja 11.3), jeśli jeszcze nie działał na tym hoście.

### 12.7 Rollback aplikacji (kod / obrazy)

Gdy regresja jest w aplikacji (nie w danych), **bez** restore DB:

```bash
cd /path/to/EkstraBet
# Zanotuj objawy i bieżący tag (ticket / log operatorski)
git fetch --tags origin
git checkout <POPRZEDNI_TAG>    # ostatni znany dobry tag
# APP_ORIGIN z trwałego .env (12.1)

# Preflight backup przed rollbackiem (stan DB „po” złym wydaniu też warto mieć)
BACKUP_ENV_FILE=/etc/ekstrabet/backup.env ./scripts/backup_mysql.sh

docker compose -f compose.production.yml up -d --build --wait
docker compose -f compose.production.yml ps
# Powtórz smoke z 12.4
```

Compose zbuduje obrazy z checkoutu poprzedniego tagu. Nie używaj `docker compose down -v`
przy zwykłym rollbacku aplikacji — flaga `-v` usuwa wolumen MySQL.

Jeśli po rollbacku aplikacji dane są niespójne lub uszkodzone, przejdź do 12.8.

### 12.8 Odtworzenie DB z backupu

**Bez migracji schematu** — odtwarzasz dump z sekcji 11, nie stosujesz skryptów DDL z Git.

1. Wybierz plik `.sql.gz.enc` (preferuj backup **sprzed** awarii; zweryfikuj `.sha256`).
2. Zatrzymaj ruch aplikacyjny (API/frontend), żeby nie pisać w trakcie restore:

```bash
cd /path/to/EkstraBet
# APP_ORIGIN z trwałego .env (12.1)
docker compose -f compose.production.yml stop api frontend
```

3. Najpierw (jeśli czas pozwala) odtwórz ten sam plik do `ekstrabet_restore_test`
   (sekcja 11.4) i sprawdź liczbę tabel / próbki.
4. Restore produkcyjny — jawny cel i potwierdzenie:

```bash
BACKUP_ENV_FILE=/etc/ekstrabet/backup.env \
  ./scripts/restore_mysql.sh \
    --file /var/backups/ekstrabet/daily/ekstrabet_YYYY-MM-DD.sql.gz.enc \
    --target-database ekstrabet \
    --confirm YES_I_UNDERSTAND_DATA_LOSS
```

5. Wznów stack i smoke:

```bash
docker compose -f compose.production.yml up -d --wait
# smoke 12.4 + login
```

### 12.9 Restart VPS

Po rebootcie hosta usługi Compose mają `restart: unless-stopped`, nginx i Docker
powinny wrócić z systemd. Weryfikacja:

```bash
sudo systemctl is-active docker nginx
cd /path/to/EkstraBet
# Compose / kolejne up czytają APP_ORIGIN z trwałego .env (12.1) — bez export
docker compose -f compose.production.yml ps
curl -fsS http://127.0.0.1:3000/api/health
curl -fsSI https://twoja-domena/api/health | head -n 15
```

### 12.10 Checklista SZP-72

- [ ] Zanotowany tag wydania i poprzedni dobry tag (oraz `git rev-parse`)
- [ ] Trwały `/path/to/EkstraBet/.env` z `APP_ORIGIN` (`radikey:radikey`, `600`); nie tylko `export` w sesji
- [ ] `api.env`: `CORS_ORIGINS` zgodne z `APP_ORIGIN` (sekcja 7.2); `FRONTEND_ORIGIN` nie jest źródłem prawdy
- [ ] Preflight `backup_mysql.sh` OK (lokalnie + off-site) przed `up --build`
- [ ] `git checkout <TAG>` → `compose config` → `up -d --build --wait` → wszystkie healthy
- [ ] Smoke dopiero po healthy: `/api/health`, `/ready`, HTTPS, `401` bez cookie na `/api/backend/leagues`, porty zamknięte
- [ ] Logi bez sekretów; brak cascade 5xx po starcie
- [ ] DNS przełączony dopiero po smoke; HSTS dopiero po poprawnym HTTPS
- [ ] Rollback aplikacji na poprzedni tag sprawdzony (staging lub window utrzymaniowy)
- [ ] Procedura restore DB znana; test na `ekstrabet_restore_test` przed produkcją
- [ ] Po restarcie VPS stack wraca zdrowy bez ręcznej interwencji (`restart: unless-stopped` + trwały `.env`)
- [ ] Drugi operator wykonał release i rollback wyłącznie z tego runbooka
- [ ] Pełny odbiór bezpieczeństwa podpisany w sekcji 13 (SZP-73) przed wydaniem

## 13. Checklista odbioru bezpieczeństwa (SZP-73)

Podpisz **przed** przełączeniem ruchu produkcyjnego. Krytyczny brak = blokada
wydania. Smoke z sekcji 12.4 nie zastępuje tej checklisty.

Operator / data: ________________ / __________

### 13.1 CI i build

- [ ] Python: `pytest` (backend/api) OK
- [ ] Frontend: `npm test`, `npm run lint`, `npm run build` OK
- [ ] `docker compose -f compose.production.yml config` OK
- [ ] Build obrazów API i frontendu OK

### 13.2 Sieć, auth, OpenAPI

- [ ] Skan portów z zewnątrz: `3000`, `8000`, `3306` zamknięte (tylko 22/80/443)
- [ ] Chroniony endpoint przez BFF bez cookie → `401`
  (np. `https://domena/api/backend/leagues`)
- [ ] OpenAPI produkcyjnie wyłączone: `/docs`, `/redoc`, `/openapi.json`
  niedostępne publicznie

### 13.3 Konfiguracja i uprawnienia

- [ ] Granty DB: konto API SELECT na całą bazę; zapis tylko `users` (UPDATE first-login), `user_preferences`, `user_favorite_leagues`. Reszta `INSERT`/`UPDATE`/`DELETE` odrzucona
- [ ] `EKSTRABET_ML_PREVIEW=false` na VPS; start z `true` kończy się błędem fail-closed
- [ ] Cursor chat wyłączony (`CHAT_ENABLE_CURSOR` /
  `NEXT_PUBLIC_CHAT_ENABLE_CURSOR`); start z `true` kończy się błędem fail-closed
- [ ] `ACCESS_TOKEN_EXPIRE_MINUTES=1440`
- [ ] `CORS_ORIGINS` w `api.env` = `APP_ORIGIN` (sekcja 7.2)

### 13.4 Operacje

- [ ] Pierwsze dane z lokalnego dumpa `.sql` wgrane (sekcja 9.2); plaintext usunięty
- [ ] Backup + udokumentowany restore do bazy testowej (sekcja 11)
- [ ] Restart VPS przywraca zdrowy stack
- [ ] Smoke HTTPS: cert, nagłówki bezpieczeństwa, login, podstawowa nawigacja

### 13.5 Decyzja wydania

- [ ] Wszystkie punkty powyżej odhaczone z dowodem (log / zrzut / ticket)
- [ ] Brak otwartych krytycznych usterek — wydanie **zatwierdzone**

Podpis odbioru: ________________
