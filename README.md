# Pub-Sub Log Aggregator Terdistribusi

Sistem ini adalah aggregator log pub-sub terdistribusi yang dibangun dengan menggunakan arsitektur microservices melalui Docker Compose. Proyek ini mendemonstrasikan penanganan event yang handal, pencegahan data duplikat (idempotency dan deduplication), serta transaksional / konkurensi kontrol yang kuat.

## Arsitektur
Proyek ini terdiri dari beberapa komponen:
1. **Aggregator (FastAPI)**: Menangani API publik untuk mempublikasikan dan melihat event log, serta memiliki *consumer worker* di background untuk memproses event.
2. **Publisher (Python)**: Sebuah skrip simulasi yang terus-menerus mem-publish event ke aggregator. Mensimulasikan terjadinya 30% pengiriman ulang (duplikat).
3. **Broker (Redis)**: Bertindak sebagai perantara antrean pesan internal yang memisahkan endpoint API dari pemrosesan di database.
4. **Storage (PostgreSQL)**: Database relasional yang memelihara data persisten event yang diproses beserta status metrik, dengan konstrain unik pada kombinasi `(topic, event_id)` untuk memastikan deduplikasi tingkat data.

## Keterkaitan dengan Materi (Bab 1-13)

- **Bab 8 & 9 (Transaksi dan Konkurensi)**: 
  Sistem ini menerapkan isolation level standar pada PostgreSQL (`READ COMMITTED` by default), namun memaksakan *consistency* pada skenario duplikasi menggunakan atomic constraint (Unique Constraint pada `topic` dan `event_id`). 
  Pada sisi *worker*, kami menggunakan klausa `INSERT ... ON CONFLICT DO NOTHING`. Ini mengeliminasi masalah *race condition* (misalnya, *lost update*) saat beberapa consumer memproses event yang sama pada saat bersamaan. Update ke tabel `Stats` juga dilakukan secara atomik melalui SQLAlchemy.

- **Bab 1 & 2 (Karakteristik Sistem & Arsitektur)**: 
  Arsitektur sistem menggunakan pub-sub dengan komponen microservice yang secara lokal terisolasi dalam *network* Docker Compose.

- **Bab 6 (Toleransi Kegagalan)**:
  Terdapat mekanisme *at-least-once delivery* dari publisher. Redis dan PostgreSQL disematkan pada volume persisten. Jika aggregator atau database crash, data antrean (sejauh yang belum diambil) dan data terproses akan dipertahankan. Data ter-dedup pada PostgreSQL mencegah terulangnya pemrosesan (*crash recovery*).

## Menjalankan Aplikasi

Pastikan Anda telah menginstal **Docker** dan **Docker Compose**.

1. Clone repositori ini.
2. Jalankan perintah build dan up:
   ```bash
   docker compose up --build -d
   ```
3. Akses API pada: `http://localhost:8080`
   - **GET /stats**: Mengecek jumlah event unik yang diproses dan drop duplikat.
   - **GET /events?topic=...**: Melihat daftar event log.

## Menjalankan Unit Tests (Integration)

1. Pastikan Docker Compose stack sedang berjalan (seperti instruksi di atas).
2. Install requirement di lokal atau di virtual environment:
   ```bash
   pip install -r tests/requirements.txt
   ```
3. Jalankan *test suite*:
   ```bash
   pytest tests/test_api.py -v
   ```
   *Test ini mencakup 12 *test cases* mulai dari verifikasi skema hingga stress test konkurensi (multi-worker race condition proof).*

 ## Video Demo: https://youtu.be/XeD9kbbGBdw