# Wdrożenie EkstraBet na VPS (SZP-70 — host, nginx, sekrety)

Dokument opisuje przygotowanie hosta Ubuntu/Debian pod produkcyjny stack
z [compose.production.yml](../compose.production.yml): nginx z TLS na hoście,
Next.js na `127.0.0.1:3000`, FastAPI i MySQL tylko w prywatnej sieci Compose.

Pełny runbook wydania/rollbacku: etap SZP-72 (ten dokument — host i dostęp).
Backup i restore: sekcja 9 (SZP-71).

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

Dodatkowo przy starcie Compose ustaw `APP_ORIGIN=https://twoja-domena`
(w shellu lub w pliku `.env` obok `compose.production.yml`) — interpolacja
Compose wymaga tej zmiennej poza samym `frontend.env`.

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

Szybki smoke konfiguracji (bez sekretów w logach):

```bash
cd /path/to/EkstraBet
export EKSTRABET_ENV_DIR=/etc/ekstrabet
export APP_ORIGIN=https://example.com
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
Environment=APP_ORIGIN=https://twoja-domena
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
