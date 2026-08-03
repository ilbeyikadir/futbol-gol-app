import flet as ft
import websocket
import json
import threading
import time

ESP_WS_URL = "ws://192.168.4.1:81"

def main(page: ft.Page):
    # EKRAN UYANIK KALMA (0.21.2 Uyumlu)
    try:
        page.keep_on = True
    except Exception:
        pass

    page.title = "GOL MONİTÖRÜ & SKORBORD"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = ft.colors.GREEN_900

    # LOKAL SES BİLEŞENİ
    goal_audio = None
    try:
        goal_audio = ft.Audio(
            src="gol.mp3",
            autoplay=False,
            volume=1.0
        )
        page.overlay.append(goal_audio)
    except Exception as e:
        print("Ses yükleme uyarısı:", e)

    was_alert = False
    goal_count = 0

    stadium_icon = ft.Icon(
        ft.icons.SPORTS_SOCCER,
        size=80,
        color=ft.colors.WHITE
    )

    title_text = ft.Text(
        "STADYUM GOL MONİTÖRÜ",
        size=22,
        weight=ft.FontWeight.BOLD,
        color=ft.colors.WHITE70
    )

    score_display = ft.Text(
        f"SKOR: {goal_count}",
        size=44,
        weight=ft.FontWeight.BOLD,
        color=ft.colors.AMBER_300
    )

    status_text = ft.Text(
        "MAÇ DEVAM EDİYOR...",
        size=18,
        weight=ft.FontWeight.BOLD,
        color=ft.colors.WHITE
    )

    val_text = ft.Text("---", size=70, weight=ft.FontWeight.BOLD, color=ft.colors.WHITE)
    threshold_text = ft.Text("GOL EŞİĞİ: 600", size=13, color=ft.colors.WHITE70)

    score_card = ft.Container(
        content=ft.Column(
            [
                ft.Text("CANLI A0 SENSÖR DEĞERİ", size=13, color=ft.colors.WHITE60),
                val_text,
                threshold_text,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=ft.colors.BLACK45,
        padding=20,
        border_radius=20,
        width=300,
        alignment=ft.alignment.center
    )

    def reset_score(e):
        nonlocal goal_count
        goal_count = 0
        score_display.value = f"SKOR: {goal_count}"
        page.update()

    reset_button = ft.ElevatedButton(
        text="SKORU SIFIRLA",
        icon=ft.icons.REFRESH,
        style=ft.ButtonStyle(
            color=ft.colors.WHITE,
            bgcolor=ft.colors.RED_800,
            padding=15
        ),
        on_click=reset_score
    )

    page.add(
        stadium_icon,
        title_text,
        score_display,
        ft.Divider(height=10, color=ft.colors.TRANSPARENT),
        status_text,
        ft.Divider(height=10, color=ft.colors.TRANSPARENT),
        score_card,
        ft.Divider(height=20, color=ft.colors.TRANSPARENT),
        reset_button
    )

    def trigger_goal_ui(raw_val, threshold, is_alert):
        nonlocal was_alert, goal_count

        val_text.value = str(raw_val)
        threshold_text.value = f"GOL EŞİĞİ: {threshold}"

        if is_alert:
            page.bgcolor = ft.colors.GREEN_700
            status_text.value = "⚽ GOOOOLLLL! ⚽"
            status_text.color = ft.colors.AMBER_300
            stadium_icon.color = ft.colors.AMBER_300

            if not was_alert:
                was_alert = True
                goal_count += 1
                score_display.value = f"SKOR: {goal_count}"
                
                # SESİ ÇAL (Güvenli Tetikleme)
                if goal_audio:
                    try:
                        goal_audio.play()
                    except Exception as ex:
                        print("Ses çalma hatası:", ex)
        else:
            was_alert = False
            page.bgcolor = ft.colors.GREEN_900
            status_text.value = "SENSÖR AKTİF - MAÇ DEVAM EDİYOR"
            status_text.color = ft.colors.WHITE
            stadium_icon.color = ft.colors.WHITE

        page.update()

    def update_ui_disconnected():
        page.bgcolor = ft.colors.BLUE_GREY_900
        status_text.value = "🔌 ESP8266 İLE BAĞLANTI KOPTU"
        status_text.color = ft.colors.RED_400
        val_text.value = "---"
        page.update()

    def websocket_worker():
        while True:
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

                def on_close(ws, close_status_code, close_msg):
                    update_ui_disconnected()

                ws = websocket.WebSocketApp(
                    ESP_WS_URL,
                    on_message=on_message,
                    on_close=on_close
                )
                ws.run_forever()
            except Exception:
                pass
            time.sleep(1)

    ws_thread = threading.Thread(target=websocket_worker, daemon=True)
    ws_thread.start()

# assets_dir="." ekleyerek ses dosyasının okunmasını garantiliyoruz
if __name__ == "__main__":
    ft.app(target=main, assets_dir=".")
