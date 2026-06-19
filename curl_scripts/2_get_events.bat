@echo off
echo === Mengambil 100 Event Terakhir (GET /events) ===
curl.exe -s -X GET http://localhost:8080/events
echo.
echo.
