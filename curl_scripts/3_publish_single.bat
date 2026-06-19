@echo off
echo === Mempublikasikan 1 Event (POST /publish) ===
curl.exe -s -X POST http://localhost:8080/publish ^
  -H "Content-Type: application/json" ^
  -d "{\"topic\": \"demo\", \"event_id\": \"id-tunggal-123\", \"timestamp\": \"2026-06-19T10:00:00Z\", \"source\": \"curl\", \"payload\": {\"pesan\": \"halo dunia\"}}"
echo.
echo.
