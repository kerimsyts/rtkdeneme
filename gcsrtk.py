import serial
import time
from pymavlink import mavutil

# ==========================================
# 1. AYARLAR
# ==========================================
BASE_STATION_PORT = 'COM8'  
BASE_BAUD_RATE = 115200     

ESP_TELEMETRY_PORT = 'COM5' 
ESP_BAUD_RATE = 921600      

# ==========================================
# 2. BAĞLANTILARI KUR
# ==========================================
print(f"ESP Sürü Telemetri bağlantısı açılıyor ({ESP_TELEMETRY_PORT})...")
# Sürüdeki tüm ID'leri dinlemek için source_system ve source_component kısıtlaması yapmıyoruz
master = mavutil.mavlink_connection(ESP_TELEMETRY_PORT, baud=ESP_BAUD_RATE)

print(f"Baz istasyonu bağlantısı açılıyor ({BASE_STATION_PORT})...")
try:
    base_serial = serial.Serial(BASE_STATION_PORT, BASE_BAUD_RATE, timeout=0.1)
    print("Sistem hazır. RTCM yayını (Broadcast) başlıyor ve sürü dinleniyor...")
except Exception as e:
    print(f"Tripod bağlantı hatası: {e}")
    exit()

# ==========================================
# 3. VERİ AKTARIMI VE SÜRÜ DİNLEME DÖNGÜSÜ
# ==========================================
# Her drone'un kendi System ID'sine göre GPS durumunu tutacağımız sözlük (dictionary)
drone_durumlari = {} 

try:
    while True:
        # --- 1. KISIM: RTCM VERİSİNİ SÜRÜYE YAYINLA ---
        raw_rtcm_data = base_serial.read(180)
        
        if raw_rtcm_data:
            chunk_size = 180
            padded_chunk = bytearray(raw_rtcm_data)
            
            if len(padded_chunk) < chunk_size:
                padded_chunk.extend([0] * (chunk_size - len(padded_chunk)))
            
            master.mav.gps_rtcm_data_send(
                0, len(raw_rtcm_data), list(padded_chunk)
            )

        # --- 2. KISIM: SÜRÜDEN GELEN ONAYLARI AYRI AYRI DİNLE ---
        msg = master.recv_match(type='GPS_RAW_INT', blocking=False)
        
        if msg:
            # Mesajı gönderen drone'un kimliğini (System ID) al
            drone_id = msg.get_srcSystem()
            current_fix = msg.fix_type
            
            # Eğer bu drone'u ilk kez duyuyorsak veya durumu değiştiyse ekrana yazdır
            if drone_id not in drone_durumlari or drone_durumlari[drone_id] != current_fix:
                drone_durumlari[drone_id] = current_fix
                
                if current_fix == 6:
                    print(f"[DRONE {drone_id}] GÜVENLİ: RTK FIXED (Santimetre Hassasiyeti)")
                elif current_fix == 5:
                    print(f"[DRONE {drone_id}] BEKLE: RTK FLOAT (Düzeltme alınıyor...)")
                elif current_fix == 3:
                    print(f"[DRONE {drone_id}] DİKKAT: 3D FIX (Sadece normal GPS aktif)")
                elif current_fix <= 2:
                    print(f"[DRONE {drone_id}] UYARI: GPS Sinyali Yok!")
                
        time.sleep(0.01) 
        
except KeyboardInterrupt:
    print("\nİşlem durduruldu.")
finally:
    base_serial.close()
    master.close()