@echo off
echo === Mengambil Statistik (GET /stats) ===
curl.exe -s -X GET http://localhost:8080/stats
echo.
echo.
