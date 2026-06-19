# Laporan Teknis UAS: Pub-Sub Log Aggregator Terdistribusi

## 1. Ringkasan Sistem dan Arsitektur
Sistem yang dibangun adalah sebuah agregator log terdistribusi dengan arsitektur **Publish-Subscribe**. Sistem diorkestrasi menggunakan **Docker Compose** dan berjalan dalam jaringan lokal yang terisolasi. Arsitektur terdiri dari:
- **Aggregator (FastAPI - Python)**: Menjadi inti utama (*API Service*) yang memiliki *endpoint* `/publish` untuk menerima data, `/events` untuk kueri data, dan `/stats` untuk memantau status agregasi. 
- **Worker (Asyncio)**: Bertugas sebagai *consumer* di latar belakang (*background*) yang menarik pesan asinkron dari antrean dan menyimpannya ke basis data secara atomik.
- **Broker (Redis)**: Berperan sebagai antrean pesan (*message queue*) *in-memory* dengan kinerja tinggi.
- **Storage (PostgreSQL)**: Berperan sebagai sistem penyimpanan persisten (*database* relasional) yang diakses menggunakan driver asinkron (`asyncpg`).
- **Publisher Simulator**: Komponen simulasi yang secara berkala mempublikasikan ribuan *event*, termasuk melakukan injeksi duplikasi data acak hingga 30% untuk menguji kekebalan deduplikasi.

## 2. Keputusan Desain Utama
- **Idempotency & Dedup Store**: Untuk memitigasi bahaya *double-processing*, sistem dirancang dengan konsep *Idempotent Consumer*. Deduplikasi dikawal kuat secara persisten di PostgreSQL melalui penguncian struktur data `UniqueConstraint('topic', 'event_id')`.
- **Transaksi & Konkurensi**: Dalam proses insersi data dan pembaruan hasil (*stats*), sistem menggunakan batas transaksi mutlak (ACID). Konkurensi *multi-worker* dijinakkan melalui fungsi pembaruan *in-place SQL update* atomik (contoh: `UPDATE stats SET unique_processed = unique_processed + 1`) sehingga sepenuhnya kebal terhadap skenario *lost-update*. Proses *insert* memanfaatkan UPSERT (`INSERT ... ON CONFLICT DO NOTHING`).
- **Ordering & Retry**: Ketersediaan disuplai oleh arsitektur pelolosan *At-least-once delivery* menggunakan logika blok `try-except retry` di *publisher*. Urutan *event* mengandalkan *Logical Ordering* lewat rekaman `timestamp` ISO8601 UTC. Arsitektur terdistribusi asinkron ini menolerir datangnya *out-of-order execution* sebab penyusunan logis pada tahap akhir dipasrahkan kepada bahasa SQL (`ORDER BY timestamp DESC`).

## 3. Analisis Performa & Metrik / Hasil Uji Konkurensi
Sebanyak **12 buah pengujian** (*unit dan integration tests*) diletakkan terpusat pada file `tests/test_api.py`. Pengujian mendalam telah mengkalkulasi kesiapan skalabilitasnya:
- **Uji Konkurensi Penuh (`test_concurrency_same_event_multiple_times`)**: Saat serbuan instruksi untuk mendaftarkan *event* tunggal sama persis ditembakkan asinkron hingga 10 lapis bersamaan ke ruang memori *worker*, status PostgreSQL secara eksklusif hanya me-mutasi 1 pendaftaran tunggal ke *disk*. 100% *idempotency* tersokong akurat.
- **Uji Konsistensi Batch Stress (`test_batch_stress_small`)**: Data tumpukan (*batch*) yang direkayasa sedemikian rupa memuat puluhan data dan 30% duplikasi disuntikkan bertubi-tubi. Indikator pemantauan `/stats` berhasil membuktikan relasi matematis presisi tanpa cacat kebocoran: Variabel komputasi `received`, `unique_processed`, dan `duplicate_dropped` selalu saling berkorelasi lurus dalam jumlah total. Tidak terdeteksi satupun anomali *race-condition*.

## 4. Keterkaitan ke Bab 1–13 (Referensi per Bagian)
Sistem log terdistribusi ini disarikan kuat dari literatur utama perancangan sistem terdistribusi (Coulouris et al., 2011), yakni:
- **Bab 1–2 (Karakteristik & Arsitektur)**: Menerapkan paradigma fleksibel *publish-subscribe* berbasis layanan majemuk (*microservices*).
- **Bab 3–5 (Komunikasi, Penamaan, Ordering)**: Memanfaatkan nama kategori terpusat (`topic`) yang diikat rapat skema UUID acak komputasi sisi pengirim (*collision-resistant*) serta orientasi kronologi riil *timestamp*.
- **Bab 6–7 (Toleransi & Konsistensi)**: Mempertahankan ritme *Eventual Consistency* asinkron melalui penengah Redis serta mengebalkan arsitektur terhadap keruntuhan mesin lewat sokongan rekaman basis data relasional bermedia wadah *volumes* persisten.
- **Bab 8–9 (Transaksi & Kontrol Konkurensi)**: Memenuhi kaidah jaminan ACID mutlak (*Atomicity, Consistency, Isolation, Durability*) melalui perintah *upsert optimistic concurrency* pada mode isolasi *read-committed* SQL.
- **Bab 10–13 (Infrastruktur & Orkestrasi)**: Keseluruhan topologi, isolasi internal jaringan komunikasi tanpa ancaman publisitas luar, dibungkus otonom dalam naskah simfoni *Docker Compose*.
*(Detail esai narasi teoretis komprehensif Bab 1-13 masing-masing terjawab utuh di dokumen terpisah: teori.md)*

## Daftar Pustaka
Coulouris, G., Dollimore, J., Kindberg, T., & Blair, G. (2011). *Distributed Systems: Concepts and Design*. Pearson.

 ## Video Demo: https://youtu.be/XeD9kbbGBdw