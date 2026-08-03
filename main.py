import flet as ft
import websocket
import json
import threading
import time

# ESP8266 WebSocket Adresi
ESP_WS_URL = "ws://192.168.4.1:81"

def main(page: ft.Page):
    # Sayfa Genel Ayarları
    page.title = "ESP8266 Sensör Monitörü"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = ft.Colors.BLUE_GREY_900  # Varsayılan Arka Plan

    # Uygulama Durum Değişkenleri
    is_running = True

    # --- UI Bileşenleri ---
    title_text = ft.Text("ESP8266 A0 SENSÖR", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
    
    # Anlık A0 Değeri Göstergesi
    val_text = ft.Text("---", size=70, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
    
    # Eşik Bilgisi
    threshold_text = ft.Text("Eşik Değeri: ---", size=14, color=ft.Colors.WHITE70)

    # Durum / Uyarı Kutusu
    status_card = ft.Container(
        content=ft.Text("BAĞLANTI BEKLENİYOR", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
        bgcolor=ft.Colors.BLUE_GREY_700,
        padding=15,
        border_radius=10,
        alignment=ft.Alignment(0, 0), # Hata veren hizalama düzeltildi
        width=300
    )

    # UI Elemanlarını Sayfaya Ekle
    page.add(
        title_text,
        ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
        val_text,
        threshold_text,
        ft.Divider(height=30, color=ft.Colors.TRANSPARENT),
        status_card
    )

    # --- UI Güncelleme Mantığı ---
    def update_ui_alert(raw_val, threshold, is_alert):
        val_text.value = str(raw_val)
        threshold_text.value = f"Eşik Değeri: {threshold}"

        if is_alert:
            # 🚨 EŞİK AŞILDI: Ekran Kırmızı, Uyarı Aktif
            page.bgcolor = ft.Colors.RED_900
            status_card.bgcolor = ft.Colors.RED_700
            status_card.content.value = "⚠️ EŞİK AŞILDI! AKSIYON ALINIYOR"
        else:
            # ✅ NORMAL DURUM: Ekran Yeşil/Koyu Yeşil
            page.bgcolor = ft.Colors.GREEN_900
            status_card.bgcolor = ft.Colors.GREEN_700
            status_card.content.value = "DURUM: NORMAL"

        page.update()

    def update_ui_disconnected():
        page.bgcolor = ft.Colors.BLUE_GREY_900
        status_card.bgcolor = ft.Colors.AMBER_900
        status_card.content.value = "🔌 ESP8266 BAĞLANTISI KOPTU"
        val_text.value = "---"
        page.update()

    # --- WebSocket Arka Plan İşçisi ---
    def websocket_worker():
        nonlocal is_running
        while is_running:
            try:
                def on_message(ws, message):
                    try:
                        data = json.loads(message)
                        raw_val = data.get("raw_value", 0)
                        threshold = data.get("threshold", 600)
                        is_alert = data.get("alert", False)

                        # UI'ı güncelle
                        update_ui_alert(raw_val, threshold, is_alert)
                    except Exception as e:
                        print("JSON Ayrıştırma Hatası:", e)

                def on_error(ws, error):
                    print("WS Hata:", error)

                def on_close(ws, close_status_code, close_msg):
                    update_ui_disconnected()

                ws = websocket.WebSocketApp(
                    ESP_WS_URL,
                    on_message=on_message,
                    on_error=on_error,
                    on_close=on_close
                )
                ws.run_forever()

            except Exception as e:
                print("Bağlantı Hatası:", e)
            
            time.sleep(2)

    # Arka plan WebSocket iş parçacığını başlat
    ws_thread = threading.Thread(target=websocket_worker, daemon=True)
    ws_thread.start()

# Flet Uygulamasını Başlat
if __name__ == "__main__":
    ft.app(target=main)