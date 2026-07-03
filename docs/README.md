# Rashid Agent v2 — Quickstart (فارسی)

راهنمای کامل: [quickstart-fa.md](./quickstart-fa.md)

## یک خط

```powershell
.\scripts\setup-mirrors.ps1; .\scripts\infra-up.ps1; pip install -e ".[dev]"; .\scripts\dev.ps1
```

Frontend (ترمینال جدا):

```powershell
cd frontend; npm install; npm run dev
```
