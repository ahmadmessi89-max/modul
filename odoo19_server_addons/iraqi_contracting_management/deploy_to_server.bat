@echo off
chcp 65001 > nul
echo =========================================================================
echo   تثبيت وتحديث موديول إدارة المقاولات العراقية في سيرفر Odoo 19 (Windows)
echo =========================================================================
echo.

set SOURCE_DIR=C:\Users\legion\.gemini\antigravity-ide\scratch\iraqi_contracting_management
set ODOO_SERVER_ADDONS=C:\Program Files\Odoo 19.0.20260913\server\odoo\addons\iraqi_contracting_management

echo 1. جاري نسخ الموديول إلى مجلد الإضافات الرئيسي (Odoo Addons)...
if not exist "%ODOO_SERVER_ADDONS%" mkdir "%ODOO_SERVER_ADDONS%"
xcopy "%SOURCE_DIR%\*" "%ODOO_SERVER_ADDONS%\" /E /I /Y /Q > nul

echo 2. جاري إيقاف خدمة سيرفر Odoo 19...
net stop odoo-server-19.0

echo 3. جاري ترقية قاعدة البيانات وتطبيق التعديلات البرمجية فوراً...
"C:\Program Files\Odoo 19.0.20260913\python\python.exe" "C:\Program Files\Odoo 19.0.20260913\server\odoo-bin" -c "C:\Program Files\Odoo 19.0.20260913\server\odoo.conf" -d Sag-odoo19 -u iraqi_contracting_management --stop-after-init

echo 4. جاري إعادة تشغيل خدمة سيرفر Odoo 19...
net start odoo-server-19.0

echo.
echo =========================================================================
echo   تم تحديث وترقية الموديول بنجاح في قاعدة البيانات والسيرفر!
echo =========================================================================
echo.
