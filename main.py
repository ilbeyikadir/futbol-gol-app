import flet as ft
import websocket
import json
import threading
import time

# ESP8266 WebSocket Sunucu Adresi
ESP_WS_URL = "ws://192.168.4.1:81"

def main(page: ft.Page):
    # 🌟 EKRANIN KAPANMASINI / UYKUYA GEÇMESİNİ ENGELLER
    page.keep_on = True

    # Sayfa Genel Yapılandırması
    page.title = "GOL MONİTÖRÜ & SKORBORD"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = ft.Colors.GREEN_900  # Stadyum Çim Yeşili

    # LOKAL SES OYNATICI (Kök dizindeki gol.mp3)
    goal_audio = ft.Audio(
        src="gol.mp3",
        autoplay=False
    )
    page.overlay.append(goal_audio)

    # Durum Takip Değişkenleri
    is_running = True
    was_alert = False  # Gol durumunun 1 kez tetiklenmesi için
    goal_count = 0     # Canlı Gol Sayacı

    # --- UI BİLEŞENLERİ ---
    stadium_icon = ft.Icon(
        name=ft.Icons.SPORTS_SOCCER,
        size=80,
        color=ft.Colors.WHITE
    )

    title_text = ft.Text(
        "STADYUM GOL MONİTÖRÜ",
        size=22,
        weight=ft.FontWeight.BOLD,
        color=ft.Colors.WHITE70
    )

    # CANLI SKORBOARD
    score_display = ft.Text(
        f"SKOR: {goal_count}",
        size=44,
        weight=ft.FontWeight.BOLD,
        color=ft.Colors.AMBER_300
    )

    status_text = ft.Text(
        "MAÇ DEVAM EDİYOR...",
        size=18,
        weight=ft.FontWeight.BOLD,
        color=ft.Colors.WHITE
    )

    val_text = ft.Text("---", size=70, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
    threshold_text = ft.Text("GOL EŞİĞİ: 600", size=13, color=ft.Colors.WHITE70)

    score_card = ft.Container(
        content=ft.Column(
            [
                ft.Text("CANLI A0 SENSÖR DEĞERİ", size=13, color=ft.Colors.WHITE60),
                val_text,
                threshold_text,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=ft.Colors.BLACK_48,
        padding=20,
        border_radius=20,
        border=ft.border.all(2, ft.Colors.WHITE24),
        width=300,
        alignment=ft.Alignment(0, 0)
    )

    # SKOR SIFIRLAMA BUTONU
    def reset_score(e):
        nonlocal goal_count
        goal_count = 0
        score_display.value = f"SKOR: {goal_count}"
        page.update()

    reset_button = ft.ElevatedButton(
        text="SKORU SIFIRLA",
        icon=ft.Icons.REFRESH,
        style=ft.ButtonStyle(
            color=ft.Colors.WHITE,
            bgcolor=ft.Colors.RED_800,
            padding=15
        ),
        on_click=reset_score
    )

    page.add(
        stadium_icon,
        title_text,
        score_display,
        ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
        status_text,
        ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
        score_card,
        ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
        reset_button
    )

    # --- GOL / SENSÖR TETİKLEME MANTIĞI ---
    def trigger_goal_ui(raw_val, threshold, is_alert):
        nonlocal was_alert, goal_count

        val_text.value = str(raw_val)
        threshold_text.value = f"GOL EŞİĞİ: {threshold}"

        # ⚽ GOL ANI! (Eşik İlk Kez Geçildiğinde)
        if is_alert:
            page.bgcolor = ft.Colors.GREEN_700
            status_text.value = "⚽ GOOOOLLLL! ⚽"
            status_text.color = ft.Colors.AMBER_300
            stadium_icon.color = ft.Colors.AMBER_300
            score_card.border = ft.border.all(3, ft.Colors.AMBER_400)

            # Gol sadece 1 kez sayılsın ve LOKAL SES 1 kez çalsın
            if not was_alert:
                was_alert = True
                goal_count += 1
                score_display.value = f"SKOR: {goal_count}"
                try:
                    goal_audio.play()
                except Exception as ex:
                    print("Lokal ses çalma hatası:", ex)

        else:
            # NORMAL SAHA DURUMU
            was_alert = False
            page.bgcolor = ft.Colors.GREEN_900
            status_text.value = "SENSÖR AKTİF - MAÇ DEVAM EDİYOR"
            status_text.color = ft.Colors.WHITE
            stadium_icon.color = ft.Colors.WHITE
            score_card.border = ft.border.all(2, ft.Colors.WHITE24)

        page.update()

    def update_ui_disconnected():
        page.bgcolor = ft.Colors.BLUE_GREY_900
        status_text.value = "🔌 ESP8266 İLE BAĞLANTI KOPTU"
        status_text.color = ft.Colors.RED_400
        val_text.value = "---"
        page.update()

    # --- WEBSOCKET ARKA PLAN DİNLEYİCİSİ ---
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

                        trigger_goal_ui(raw_val, threshold, is_alert)
                    except Exception:
                        pass

                def on_error(ws, error):
                    pass

                def on_close(ws, close_status_code, close_msg):
                    update_ui_disconnected()

                ws = websocket.WebSocketApp(
                    ESP_WS_URL,
                    on_message=on_message,
                    on_error=on_error,
                    on_close=on_close
                )
                ws.run_forever()

            except Exception:
                pass

            time.sleep(1)

    ws_thread = threading.Thread(target=websocket_worker, daemon=True)
    ws_thread.start()

if __name__ == "__main__":
    ft.app(target=main, assets_dir=".")
