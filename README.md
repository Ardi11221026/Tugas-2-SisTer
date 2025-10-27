##### **1. Menjalankan Sistem dengan:**

**Perintahnya:**

docker compose up --build





##### **2. Cek Kesehatan Node:**

**Perintahnya:**

\- curl http://localhost:8001/health

\- curl http://localhost:8002/health

\- curl http://localhost:8003/health



**Outputnya:**

{"status":"ok","node":"node1"}

{"status":"ok","node":"node2"}

{"status":"ok","node":"node3"}





##### **3. Distributed Lock Manager**

###### **a. Acquire Exclusive Lock**

**Perintahnya:**

curl -X POST http://localhost:8001/lock/acquire \\

     -H "Content-Type: application/json" \\

     -d '{"name":"resource1","mode":"exclusive","owner":"clientA"}'



**Outputnya:** {"ok": true}



artinya Node1 berhasil mendapatkan exclusive lock untuk resource1 atas nama clientA.



###### **b. Coba Ambil Lock dari Node Lain**

**Perintahnya:**

curl -X POST http://localhost:8002/lock/acquire \\

     -H "Content-Type: application/json" \\

     -d '{"name":"resource1","mode":"exclusive","owner":"clientB"}'

**Outputnya:** {"ok": false, "reason": "locked"}



artinya Node2 gagal mengambil lock, karena resource tersebut sedang dikunci oleh clientA. Data lock ini disimpan di Redis, jadi semua node melihat status yang sama.



###### **c. Release Lock**

**Perintahnya:**

curl -X POST http://localhost:8001/lock/release \\

     -H "Content-Type: application/json" \\

     -d '{"name":"resource1","mode":"exclusive","owner":"clientA"}'



**Outputnya:** {"ok": true}



Lock dilepas dan sekarang bisa diambil lagi oleh node lain.





##### **4. Distributed Queue System**

Sekarang kita uji sistem antrean terdistribusi.

Konsepnya: pesan dikirim ke antrean dan disimpan di Redis.

Jika satu node gagal, pesan tetap dapat diambil oleh node lain.



###### **a. Push Pesan ke Queue**

**Perintahnya:**

curl -X POST http://localhost:8002/queue/push \\

     -H "Content-Type: application/json" \\

     -d '{"queue":"orders","payload":{"order\_id":1,"item":"book"}}'



**Outputnya:** {"ok": true}



###### **b. Pop Pesan dari Queue**

**Perintahnya:**

curl -X POST http://localhost:8003/queue/pop \\

     -H "Content-Type: application/json" \\

     -d '{"queue":"orders","payload":{}}'



**Outputnya:** {"ok": true, "item": {"order\_id": 1, "item": "book"}}



artinya Node3 berhasil mengambil pesan yang dikirim oleh Node2, menandakan bahwa state queue konsisten di seluruh cluster.



###### **c. Simulasi Node Failure**

**Perintahnya:**

docker stop distributed-sync-system-node2-1



Lalu kita ulangi push/pop melalui node1.

Sistem tetap berjalan karena Redis menyimpan antrean global.





##### **5. Distributed Cache Coherence (MESI)**

Selanjutnya kita uji cache coherence antar node.

###### **a. Write ke Cache**

**Perintahnya:**
curl -X POST http://localhost:8001/cache/write \\

     -H "Content-Type: application/json" \\

     -d '{"key":"temperature","value":25}'



**Outputnya:** {"ok": true}



###### **b. Read dari Node Lain**

**Perintahnya:**

curl "http://localhost:8003/cache/read?key=temperature"



**Outputnya:** {"ok": true, "value": {"state":"M","value":25}}



Nilai dibaca secara konsisten di node lain.

Jika ada penulisan baru, node lain akan menandai cache mereka sebagai invalid (state I) dan menarik nilai baru dari Redis.





##### **6. Monitoring \& Metrics**

**Perintahnya:**

curl http://localhost:8001/metrics



**Outputnya:** {"metrics": "see logs"}



Semua metrik juga dapat dilihat di log container, termasuk jumlah locks acquired, queue push/pop, dan aktivitas cache.





##### **7. Simulasi Recovery**

Terakhir, kita hidupkan kembali node2:

**Perintahnya:**

docker start distributed-sync-system-node2-1



Setelah node hidup, ia otomatis sinkron dengan Redis dan mulai menerima permintaan lagi.

Dengan demikian, sistem berhasil menunjukkan:

* Konsistensi data antar node
* Toleransi terhadap kegagalan node
* Mekanisme sinkronisasi yang stabil di lingkungan terdistribusi
