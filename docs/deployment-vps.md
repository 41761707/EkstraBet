# Wdrożenie EkstraBet na VPS

Dokument opisuje przygotowanie hosta Ubuntu/Debian pod produkcyjny stack
z [compose.production.yml](../compose.production.yml): nginx z TLS na hoście,
Next.js na `127.0.0.1:3000`, FastAPI i MySQL tylko w prywatnej sieci Compose.

- Host, nginx, sekrety, firewall: sekcje 1–8 (SZP-70).
- Backup i restore: sekcja 9 (SZP-71).
- Runbook wydania, smoke test i rollback: sekcja 10 (SZP-72).

## 1. Założenia

- Publiczne porty VPS: wyłącznie `22`, `80`, `443` (`80` tylko redirect na HTTPS).
- Aplikacja dostępna wyłącznie przez nginx → `127.0.0.1:3000`.
- FastAPI (`8000`) i MySQL (`3306`) **nie** są mapowane na host — brak dostępu z Internetu.
- Certyfikat TLS dostarcza operator (istniejące pliki lub certbot) — ścieżki w nginx.

## 2. Użytkownik systemowy i katalog sekretów

```bash
sudo adduser --disabled-password --gecos "" ekstrabet
sudo usermod -aG docker ekstrabet   # po instalacji Dockera
sudo mkdir -p /etc/ekstrabet/tls
sudo chown root:ekstrabet /etc/ekstrabet
sudo chmod 750 /etc/ekstrabet
sudo chown root:ekstrabet /etc/ekstrabet/tls
sudo chmod 750 /etc/ekstrabet/tls
```

Pliki env (po skopiowaniu z szablonów w repo):

| Plik | Szablon | Zawartość |
|------|---------|-----------|
| `/etc/ekstrabet/mysql.env` | [deploy/mysql.env.example](../deploy/mysql.env.example) | `MYSQL_ROOT_PASSWORD`, `MYSQL_DATABASE` |
| `/etc/ekstrabet/api.env` | [.env.example](../.env.example) | API/backend, konto DB API (nie-root) |
| `/etc/ekstrabet/frontend.env` | [frontend/.env.local.example](../frontend/.env.local.example) | frontend / BFF |
| `/etc/ekstrabet/backup.env` | sekcja 9 (SZP-71) | konto dump, passphrase, `BACKUP_DIR`, off-site |

```bash
# Po uzupełnieniu wartości (same KEY=value, bez komentarzy):
sudo chown root:ekstrabet /etc/ekstrabet/*.env
sudo chmod 640 /etc/ekstrabet/*.env
```

Compose wymaga `APP_ORIGIN` przy każdym `config` / `up` (interpolacja
`${APP_ORIGIN:?…}` w [compose.production.yml](../compose.production.yml)) —
**poza** samym `frontend.env`. Trwałe źródło (obowiązkowe na produkcji,
runbook SZP-72): plik `.env` w katalogu repozytorium obok Compose
(Compose ładuje go automatycznie; plik jest w `.gitignore`):

```bash
# /path/to/EkstraBet/.env — same KEY=value, bez komentarzy w pliku docelowym
APP_ORIGIN=https://twoja-domena
# EKSTRABET_ENV_DIR=/etc/ekstrabet   # tylko gdy nie używasz domyślnego /etc/ekstrabet
```

```bash
sudo chown root:ekstrabet /path/to/EkstraBet/.env
sudo chmod 640 /path/to/EkstraBet/.env
```

Nie polegaj wyłącznie na `export` w sesji shell — po restarcie VPS / nowej
sesji SSH Compose musi nadal widzieć `APP_ORIGIN`.

**Nie** commituj prawdziwych sekretów. **Nie** kopiuj ich do obrazów Docker.

## 3. SSH (klucz, bez hasła i bez roota)

1. Dodaj swój klucz publiczny do `~ekstrabet/.ssh/authorized_keys` (tryb `600`, katalog `.ssh` → `700`).
2. Sprawdź logowanie kluczem na konto `ekstrabet` **w drugiej sesji**, zanim wyłączysz hasła.
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

Opcjonalnie fail2ban (SSH):

```bash
sudo apt install -y fail2ban
sudo systemctl enable --now fail2ban
```

Włącz unattended-upgrades albo inny proces aktualizacji bezpieczeństwa dystrybucji.

## 5. Docker i Compose

Zainstaluj Docker Engine oraz wtyczkę Compose zgodnie z dokumentacją Docker
dla Ubuntu/Debian. Użytkownik `ekstrabet` musi móc uruchamiać `docker`
(grupa `docker` lub rootless — wybór operatora).

Szybki smoke konfiguracji (bez sekretów w logach). `APP_ORIGIN` powinien już
być w trwałym `.env` obok Compose (sekcja 2); poniżej tylko jeśli testujesz
bez tego pliku:

```bash
cd /path/to/EkstraBet
# preferowane: wartości z .env; awaryjnie:
# export EKSTRABET_ENV_DIR=/etc/ekstrabet
# export APP_ORIGIN=https://example.com
docker compose -f compose.production.yml config
```

## 6. Konta MySQL (ręcznie)

Kontener MySQL startuje z hasłem z `mysql.env`. Konta aplikacji **zakłada
operator ręcznie** (brak skryptów bootstrap/migracji w tym wydaniu):

- konto API — tylko odczyt (`SELECT`, ewentualnie `SHOW VIEW`); hasło w `api.env` jako `DB_USER` / `DB_PASSWORD`;
- konto modeli — odczyt + ograniczony zapis na tabelach pipeline; osobne hasło (nie w `api.env` produkcyjnym, jeśli job idzie poza Compose API);
- konto backup — minimalne prawa pod dump (sekcja 9); osobne hasło w `backup.env`.

`DB_USER=root` w produkcji jest odrzucane przez fail-closed API. Root MySQL
nie powinien być dostępny zdalnie ani używany przez aplikację.

## 7. nginx i TLS

Szablon: [deploy/nginx/ekstrabet.conf.example](../deploy/nginx/ekstrabet.conf.example).

```bash
sudo apt install -y nginx
# Skopiuj certyfikat i klucz wskazane przez operatora, np.:
#   /etc/ekstrabet/tls/fullchain.pem
#   /etc/ekstrabet/tls/privkey.pem
sudo chmod 640 /etc/ekstrabet/tls/*
sudo chown root:ekstrabet /etc/ekstrabet/tls/*

# Strefy limit_req_zone muszą być w kontekście http {} — jeśli sites-available
# nie może ich zawierać, przenieś je do /etc/nginx/conf.d/ekstrabet-limits.conf
sudo cp deploy/nginx/ekstrabet.conf.example /etc/nginx/sites-available/ekstrabet
# Edytuj: server_name, ścieżki certyfikatu
sudo ln -sf /etc/nginx/sites-available/ekstrabet /etc/nginx/sites-enabled/ekstrabet
sudo nginx -t
sudo systemctl reload nginx
```

Sprawdzenia:

- `curl -I http://example.com` → `301` na HTTPS;
- `curl -IK https://example.com` → `200`/`3xx` z Next.js; nagłówki
  `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`, `X-Frame-Options`, CSP;
- z zewnątrz zamknięte: `3000`, `8000`, `3306` (np. skan portów / `nc`);
- brak publicznego location nginx do FastAPI.

**HSTS:** w szablonie jest zakomentowane. Włącz `Strict-Transport-Security`
dopiero po potwierdzeniu poprawnego HTTPS, potem `nginx -t` i reload.

Limity `limit_req` obejmują m.in.:

- `/api/auth/login`
- `/api/chat` (i podścieżki)
- `/api/backend/predictions/preview`

## 8. Minimalna weryfikacja hosta (checklista SZP-70)

- [ ] SSH: tylko klucz, `PermitRootLogin no`, hasła wyłączone (po teście drugiej sesji)
- [ ] UFW: otwarte tylko 22/80/443
- [ ] `/etc/ekstrabet/*.env`: `root:ekstrabet`, `0640`; brak sekretów w Git/obrazach
- [ ] `mysql.env` zawiera wyłącznie sekrety MySQL Compose
- [ ] nginx `-t` OK; ruch HTTPS kończy się w Next.js na `127.0.0.1:3000`
- [ ] HSTS świadomie wyłączone albo włączone po weryfikacji TLS
- [ ] Porty `3000` / `8000` / `3306` niedostępne z Internetu
- [ ] Konta MySQL API/model/backup utworzone ręcznie; API nie używa `root`

## 9. Backup, restore i retencja off-site (SZP-71)

MySQL nie ma mapowanego portu — dump i restore idą przez
`docker compose exec` do usługi `mysql` w [compose.production.yml](../compose.production.yml).
Skrypty: [scripts/backup_mysql.sh](../scripts/backup_mysql.sh),
[scripts/restore_mysql.sh](../scripts/restore_mysql.sh).

### 9.1 Konto backup i sekrety

Na hoście utwórz `/etc/ekstrabet/backup.env` (`root:ekstrabet`, `0640`), same linie
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

Minimalne uprawnienia konta dump (InnoDB, `--single-transaction`):

```sql
CREATE USER 'ekstrabet_backup'@'%' IDENTIFIED BY '…';
GRANT SELECT, SHOW VIEW, TRIGGER, EVENT, LOCK TABLES
  ON ekstrabet.* TO 'ekstrabet_backup'@'%';
FLUSH PRIVILEGES;
```

Hasło szyfrowania (`BACKUP_ENCRYPTION_PASSPHRASE`) trzymaj osobno od haseł DB —
obrót jednego sekretu nie wymaga zmiany pozostałych. Katalog
`BACKUP_DIR` powinien należeć do użytkownika uruchamiającego timer (np. `ekstrabet`),
tryb katalogu `700`.

### 9.2 Codzienny backup

```bash
cd /path/to/EkstraBet
sudo -u ekstrabet -E \
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

### 9.3 Harmonogram (systemd timer)

Przykład jednostek (dostosuj ścieżki):

`/etc/systemd/system/ekstrabet-backup.service`:

```ini
[Unit]
Description=EkstraBet MySQL encrypted backup
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
User=ekstrabet
Group=ekstrabet
WorkingDirectory=/path/to/EkstraBet
Environment=BACKUP_ENV_FILE=/etc/ekstrabet/backup.env
# APP_ORIGIN: Compose czyta trwały .env z WorkingDirectory (sekcja 2);
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

Alternatywa cron (użytkownik `ekstrabet`):  
`30 2 * * * cd /path/to/EkstraBet && BACKUP_ENV_FILE=/etc/ekstrabet/backup.env ./scripts/backup_mysql.sh`

### 9.4 Test restore (obowiązkowy przed produkcją)

1. Upewnij się, że masz świeży plik `.sql.gz.enc` i `.sha256`.
2. Odtwórz **najpierw do pustej bazy testowej** (nie do `ekstrabet`).
   Przy `MYSQL_ADMIN_*` skrypt robi `DROP DATABASE` + `CREATE DATABASE`
   (bezpieczne przy VIEW-ach, powtarzalne):

```bash
cd /path/to/EkstraBet
sudo -u ekstrabet -E \
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

### 9.5 Checklista SZP-71

- [ ] `/etc/ekstrabet/backup.env` istnieje, `0640`, osobne hasło backup + passphrase
- [ ] Konto MySQL backup ma tylko prawa do dump (bez zbędnego zapisu aplikacji)
- [ ] `backup_mysql.sh` tworzy `.sql.gz.enc` + `.sha256` (bez plaintextu); pliki `600`
- [ ] Retencja lokalna: daily/weekly/monthly zgodnie z polityką
- [ ] Kopia off-site skonfigurowana; `REQUIRE_OFFSITE=1` egzekwowane
- [ ] Timer/cron codzienny włączony (`systemctl list-timers` lub crontab)
- [ ] Restore do `ekstrabet_restore_test` OK dwa razy z rzędu (checksum + liczba tabel)
- [ ] Celowo zły / brakujący off-site target kończy backup niezerowym kodem wyjścia

## 10. Runbook wydania i rollbacku (SZP-72)

Cel: drugi operator ma wykonać release i rollback **wyłącznie** z tej sekcji
(oraz powiązanych sekcji 1–9), bez wiedzy autora. Pierwsze wydanie jest
kontrolowanym wdrożeniem z **oznaczonego tagu Git** — nie z każdego pusha.
Brak procedury migracji schematu SQL w tym runbooku (schemat poza Git;
ochrona danych = backup/restore z sekcji 9).

### 10.1 Warunki wstępne

Przed pierwszym lub kolejnym wydaniem muszą być spełnione:

1. Host, Docker, UFW, SSH, nginx/TLS, katalog `/etc/ekstrabet` — sekcje 1–8.
2. Pliki `mysql.env`, `api.env`, `frontend.env` (i `backup.env`) uzupełnione,
   `0640`, `root:ekstrabet`.
3. **Trwały** plik `/path/to/EkstraBet/.env` z `APP_ORIGIN=https://…`
   (`root:ekstrabet`, `0640`) — sekcja 2. Bez niego `compose config` / `up`
   kończy się błędem interpolacji; sam `export` w shellu nie wystarcza po
   restarcie ani w systemd.
4. Konta MySQL API / model / backup założone ręcznie (sekcja 6 i 9.1).
5. Backup + off-site + udany test restore do bazy testowej (sekcja 9.4–9.5).
6. Znany tag wydania (np. `v1.0.0`) oraz poprzedni działający tag (do rollbacku).

Zanotuj przed startem (do rollbacku):

```bash
cd /path/to/EkstraBet
git rev-parse --short HEAD
git describe --tags --exact-match 2>/dev/null || true
# APP_ORIGIN pochodzi z .env obok Compose (sekcja 2 / punkt 3 powyżej)
grep -E '^(APP_ORIGIN|EKSTRABET_ENV_DIR)=' .env
docker compose -f compose.production.yml images
```

### 10.2 Preflight backupu

Przed każdym `up --build` na produkcji:

```bash
cd /path/to/EkstraBet
sudo -u ekstrabet -E \
  BACKUP_ENV_FILE=/etc/ekstrabet/backup.env \
  ./scripts/backup_mysql.sh
```

Sprawdź: świeży plik w `BACKUP_DIR/daily/*.sql.gz.enc` + `.sha256`, kod wyjścia `0`,
wpis w logu bez sekretów, kopia off-site przyjęta. Przy pierwszym wydaniu na
pustej bazie (brak danych do ochrony) preflight dump nadal warto uruchomić
po pierwszym udanym starcie MySQL — przed przełączeniem DNS.

### 10.3 Checkout tagu, build i start

```bash
cd /path/to/EkstraBet
sudo -u ekstrabet -H bash   # lub sesja jako ekstrabet
git fetch --tags origin
git checkout <TAG>          # np. v1.0.0 — tylko oznaczony tag wydania

# APP_ORIGIN / EKSTRABET_ENV_DIR z trwałego .env (10.1) — bez export w sesji
docker compose -f compose.production.yml config >/dev/null
# --wait: blokuj do healthy (unikaj fałszywego faila curl w start_period)
docker compose -f compose.production.yml up -d --build --wait
docker compose -f compose.production.yml ps
```

Oczekiwane: `up --wait` kończy się kodem 0; `ps` pokazuje `mysql`, `api`,
`frontend` jako healthy. Dopiero wtedy przejdź do smoke (10.4).
Przy błędzie startu API sprawdź fail-closed (sekrety, `AUTH_ENABLED`, CORS, `DB_USER`)
w `docker compose -f compose.production.yml logs api --tail 100` — **bez**
kopiowania sekretów do ticketów.

Pierwsze wydanie: uruchom stack **bez** publicznego DNS (lub z tymczasową
nazwą / hosts), dokończ smoke (10.4), dopiero potem sekcja 10.6.

### 10.4 Health i smoke test

Dopiero po udanym `up --wait` z 10.3 (wszystkie healthy). Domenę zastąp swoją;
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
sesji** — pełna macierz to SZP-73; w smoke SZP-72 wystarczy krok 5 (401 bez cookie).

Nie oczekuj publicznego `/docs` ani `/openapi.json` (OpenAPI produkcyjnie wyłączone).
Nginx nie proxy’uje do FastAPI — smoke API tylko przez BFF lub `compose exec`.

### 10.5 Obserwacja logów

Po udanym smoke obserwuj przez co najmniej kilka minut (po DNS — dłużej):

```bash
docker compose -f compose.production.yml logs -f --tail=200 frontend api
```

Szukaj: powtarzających się 5xx, restartów kontenerów, błędów DB/auth.
Logi kontenerów rotują się (`max-size` / `max-file` w Compose). Aplikacja nie
powinna logować haseł, JWT ani pełnych zapytań z danymi. `docker compose logs`
nie zapisuj do repozytorium.

### 10.6 Przełączenie DNS i HSTS

1. Smoke (10.4) OK na stacku z poprawnym TLS.
2. Ustaw DNS A/AAAA na publiczny IP VPS (TTL świadomie krótki przy pierwszym cutover).
3. Po propagacji powtórz `curl -fsSI https://twoja-domena/` oraz login w przeglądarce.
4. Dopiero wtedy włącz HSTS w nginx (sekcja 7), `nginx -t`, `systemctl reload nginx`.
5. Włącz / potwierdź timer backupu (sekcja 9.3), jeśli jeszcze nie działał na tym hoście.

### 10.7 Rollback aplikacji (kod / obrazy)

Gdy regresja jest w aplikacji (nie w danych), **bez** restore DB:

```bash
cd /path/to/EkstraBet
# Zanotuj objawy i bieżący tag (ticket / log operatorski)
git fetch --tags origin
git checkout <POPRZEDNI_TAG>    # ostatni znany dobry tag
# APP_ORIGIN z trwałego .env (10.1)

# Preflight backup przed rollbackiem (stan DB „po” złym wydaniu też warto mieć)
sudo -u ekstrabet -E \
  BACKUP_ENV_FILE=/etc/ekstrabet/backup.env \
  ./scripts/backup_mysql.sh

docker compose -f compose.production.yml up -d --build --wait
docker compose -f compose.production.yml ps
# Powtórz smoke z 10.4
```

Compose zbuduje obrazy z checkoutu poprzedniego tagu. Nie używaj `docker compose down -v`
przy zwykłym rollbacku aplikacji — flaga `-v` usuwa wolumen MySQL.

Jeśli po rollbacku aplikacji dane są niespójne lub uszkodzone, przejdź do 10.8.

### 10.8 Odtworzenie DB z backupu

**Bez migracji schematu** — odtwarzasz dump z sekcji 9, nie stosujesz skryptów DDL z Git.

1. Wybierz plik `.sql.gz.enc` (preferuj backup **sprzed** awarii; zweryfikuj `.sha256`).
2. Zatrzymaj ruch aplikacyjny (API/frontend), żeby nie pisać w trakcie restore:

```bash
cd /path/to/EkstraBet
# APP_ORIGIN z trwałego .env (10.1)
docker compose -f compose.production.yml stop api frontend
```

3. Najpierw (jeśli czas pozwala) odtwórz ten sam plik do `ekstrabet_restore_test`
   (sekcja 9.4) i sprawdź liczbę tabel / próbki.
4. Restore produkcyjny — jawny cel i potwierdzenie:

```bash
sudo -u ekstrabet -E \
  BACKUP_ENV_FILE=/etc/ekstrabet/backup.env \
  ./scripts/restore_mysql.sh \
    --file /var/backups/ekstrabet/daily/ekstrabet_YYYY-MM-DD.sql.gz.enc \
    --target-database ekstrabet \
    --confirm YES_I_UNDERSTAND_DATA_LOSS
```

5. Wznów stack i smoke:

```bash
docker compose -f compose.production.yml up -d --wait
# smoke 10.4 + login
```

### 10.9 Restart VPS

Po rebootcie hosta usługi Compose mają `restart: unless-stopped`, nginx i Docker
powinny wrócić z systemd. Weryfikacja:

```bash
sudo systemctl is-active docker nginx
cd /path/to/EkstraBet
# Compose / kolejne up czytają APP_ORIGIN z trwałego .env (10.1) — bez export
docker compose -f compose.production.yml ps
curl -fsS http://127.0.0.1:3000/api/health
curl -fsSI https://twoja-domena/api/health | head -n 15
```

### 10.10 Checklista SZP-72

- [ ] Zanotowany tag wydania i poprzedni dobry tag (oraz `git rev-parse`)
- [ ] Trwały `/path/to/EkstraBet/.env` z `APP_ORIGIN` (`0640`); nie tylko `export` w sesji
- [ ] Preflight `backup_mysql.sh` OK (lokalnie + off-site) przed `up --build`
- [ ] `git checkout <TAG>` → `compose config` → `up -d --build --wait` → wszystkie healthy
- [ ] Smoke dopiero po healthy: `/api/health`, `/ready`, HTTPS, `401` bez cookie na `/api/backend/leagues`, porty zamknięte
- [ ] Logi bez sekretów; brak cascade 5xx po starcie
- [ ] DNS przełączony dopiero po smoke; HSTS dopiero po poprawnym HTTPS
- [ ] Rollback aplikacji na poprzedni tag sprawdzony (staging lub window utrzymaniowy)
- [ ] Procedura restore DB znana; test na `ekstrabet_restore_test` przed produkcją
- [ ] Po restarcie VPS stack wraca zdrowy bez ręcznej interwencji (`restart: unless-stopped` + trwały `.env`)
- [ ] Drugi operator wykonał release i rollback wyłącznie z tego runbooka
