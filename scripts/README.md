# Database Sync Scripts

## 1. Full Sync (Replace All Data)

### Usage

To completely replace Azure database with local data:

```bash
./scripts/sync-db-to-azure.sh
```

### What it does

1. **Exports** local database data from Docker container
2. **Exports** documents as CSV (handles large text content)
3. **Uploads** files to Azure App Service
4. **Imports** data into Azure PostgreSQL database (replaces existing)
5. **Verifies** row counts

### When to use

- Initial deployment
- Complete database refresh needed
- Reverting Azure to match local state exactly

---

## 2. Incremental Sync (Append Only)

### Usage

To add only new/missing records to Azure database:

```bash
./scripts/append-db-to-azure.sh
```

### What it does

1. **Exports** local database as JSON
2. **Uploads** to Azure App Service
3. **Compares** local vs Azure by ID
4. **Inserts** only missing records (preserves existing data)
5. **Reports** what was added vs what already existed

### When to use

- Adding new countries, elections, parties, or documents
- Safe incremental updates without data loss
- Daily/regular syncs to keep Azure up-to-date

### How it works

The script compares IDs between local and Azure:
- **Existing records**: Skipped (not modified)
- **New records**: Inserted
- **Order**: Respects foreign keys (countries → elections → parties → documents)

### Example Output

```
Step 1: Importing countries...
  ✓ Added: France
  country_table: 1 new, 2 existing

Step 2: Importing elections...
  election_table: 0 new (all 2 already exist)

Step 3: Importing parties...
  ✓ Added: En Marche
  ✓ Added: National Rally
  party_table: 2 new, 11 existing

Step 4: Importing documents...
  ✓ Added: En_Marche_manifesto.pdf
  document_table: 1 new, 10 existing

Total new records added: 4
```

---

## Prerequisites (Both Scripts)

- Docker Compose running locally with `electomate-postgres` container
- Azure CLI installed and authenticated (`az login`)
- Local database in `em_dev` database

## Troubleshooting

If either script fails:
1. Ensure Docker Compose is running: `docker compose ps`
2. Verify Azure CLI login: `az account show`
3. Check local database is accessible: `docker compose exec postgres psql -U postgres -d em_dev -c "\dt"`

## Manual Import

If you need to manually run imports in Azure SSH:

```bash
az webapp ssh --resource-group em-backend-rg --name em-backend
```

Then run the generated Python script:
- Full sync: `/home/site/wwwroot/tmp/import_db.py`
- Incremental: `/home/site/wwwroot/tmp/append_db.py`

## Comparison

| Feature | Full Sync | Incremental Sync |
|---------|-----------|------------------|
| **Command** | `sync-db-to-azure.sh` | `append-db-to-azure.sh` |
| **Existing data** | ⚠️ May be replaced | ✅ Preserved |
| **New records** | ✅ Added | ✅ Added |
| **Use case** | Initial setup, full refresh | Regular updates |
| **Safe to re-run** | ⚠️ Yes, but may lose Azure-only data | ✅ Yes, completely safe |
