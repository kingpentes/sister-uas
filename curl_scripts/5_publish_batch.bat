@echo off
echo === Mempublikasikan Batch Event (POST /publish) ===
curl.exe -s -X POST http://localhost:8080/publish ^
  -H "Content-Type: application/json" ^
  -d "[{\"topic\": \"transaksi\", \"event_id\": \"batch-1\", \"timestamp\": \"2026-06-19T10:01:00Z\", \"source\": \"curl\", \"payload\": {\"jumlah\": 50000}}, {\"topic\": \"transaksi\", \"event_id\": \"batch-2\", \"timestamp\": \"2026-06-19T10:02:00Z\", \"source\": \"curl\", \"payload\": {\"jumlah\": 150000}}]"
echo.
echo.
