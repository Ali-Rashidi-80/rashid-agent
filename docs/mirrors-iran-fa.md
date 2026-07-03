# میرورهای ایران — رشید ایجنت

## گام ۰.۱ (اجباری)

```powershell
.\scripts\setup-mirrors.ps1
.\scripts\verify-mirrors.ps1
```

## پیش‌فرض: چابکان

| لایه | URL |
|------|-----|
| PyPI | `https://mirror2.chabokan.net/pypi/simple/` |
| npm | `https://mirror2.chabokan.net/npm/` |
| Docker | `mirror2.chabokan.net` |

## Docker Desktop (Windows)

Settings → Docker Engine → از `config/mirrors/daemon.json.template` کپی کنید.

## Fallback

- Docker: `https://docker.arvancloud.ir`
- پروفایل: `.\scripts\setup-mirrors.ps1 -Profile arvan`

## بدون میرور

```powershell
.\scripts\setup-mirrors.ps1 -Profile direct
```

نیاز به VPN یا دسترسی مستقیم.
