import flet as ft
import websocket
import json
import threading
import time

ESP_WS_URL = "ws://192.168.4.1:81"

def main(page: ft.Page):
    # EKRAN UYANIK KALMA
    try:
        page.keep_on = True
    except Exception:
        pass

    page.title = "GOL MONİTÖRÜ & OYUNCU YÖNETİMİ"
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = ft.Colors.GREEN_900
    page.scroll = ft.ScrollMode.AUTO

    # SES BİLEŞENİ
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

    # STATE DEĞİŞKENLERİ
    was_alert = False
    custom_threshold = 600  # Varsayılan Dinamik Eşik
    
    # Oyuncu Yapısı: {"İsim": Skor}
    players = {"Oyuncu 1": 0, "Oyuncu 2": 0}
    selected_player = ["Oyuncu 1"]  # Aktif Gol Yazılacak Oyuncu

    # --- UI BİLEŞENLERİ ---
    
    stadium_icon = ft.Icon(
        ft.Icons.SPORTS_SOCCER,
        size=50,
        color=ft.Colors.WHITE
    )

    title_text = ft.Text(
        "STADYUM GOL MONİTÖRÜ",
        size=20,
        weight=ft.FontWeight.BOLD,
        color=ft.Colors.WHITE70
    )

    status_text = ft.Text(
        "MAÇ DEVAM EDİYOR...",
        size=15,
        weight=ft.FontWeight.BOLD,
        color=ft.Colors.WHITE
    )

    # DİNAMİK SENSÖR & EŞİK KARTI
    val_text = ft.Text("---", size=45, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
    threshold_label = ft.Text(f"GOL EŞİĞİ: {custom_threshold}", size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.AMBER_300)

    def update_threshold(delta):
        nonlocal custom_threshold
        custom_threshold = max(50, min(1023, custom_threshold + delta))
        threshold_label.value = f"GOL EŞİĞİ: {custom_threshold}"
        page.update()

    threshold_controls = ft.Row(
        [
            ft.IconButton(
                ft.Icons.REMOVE_CIRCLE_OUTLINE,
                icon_color=ft.Colors.RED_400,
                on_click=lambda e: update_threshold(-50)
            ),
            threshold_label,
            ft.IconButton(
                ft.Icons.ADD_CIRCLE_OUTLINE,
                icon_color=ft.Colors.GREEN_400,
                on_click=lambda e: update_threshold(50)
            ),
        ],
        alignment=ft.MainAxisAlignment.CENTER
    )

    score_card = ft.Container(
        content=ft.Column(
            [
                ft.Text("CANLI A0 SENSÖR DEĞERİ", size=11, color=ft.Colors.WHITE60),
                val_text,
                threshold_controls,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=ft.Colors.BLACK45,
        padding=12,
        border_radius=15,
        width=320,
        alignment=ft.Alignment(0, 0)
    )

    # SEÇİLİ OYUNCU BİLGİ ETİKETİ
    active_player_text = ft.Text(
        f"⚽ GOL YAZILACAK: {selected_player[0]}",
        size=15,
        weight=ft.FontWeight.BOLD,
        color=ft.Colors.AMBER_300
    )

    player_list_column = ft.Column(spacing=8)

    def select_player_action(p_name):
        selected_player[0] = p_name
        active_player_text.value = f"⚽ GOL YAZILACAK: {p_name}"
        render_players_ui()

    def render_players_ui():
        player_list_column.controls.clear()
        
        # Seçili oyuncunun listede kalmasını kontrol et
        if selected_player[0] not in players and len(players) > 0:
            selected_player[0] = list(players.keys())[0]
            active_player_text.value = f"⚽ GOL YAZILACAK: {selected_player[0]}"
        elif len(players) == 0:
            active_player_text.value = "⚠️ OYUNCU EKLENMEDİ"

        for p_name, score in players.items():
            is_selected = (p_name == selected_player[0])
            
            # GÜNCEL BUTTON YAZIMI ('text=' kaldırıldı)
            select_btn = ft.ElevatedButton(
                "SEÇİLİ" if is_selected else "SEÇ",
                icon=ft.Icons.CHECK_CIRCLE if is_selected else ft.Icons.RADIO_BUTTON_UNCHECKED,
                style=ft.ButtonStyle(
                    color=ft.Colors.BLACK if is_selected else ft.Colors.WHITE,
                    bgcolor=ft.Colors.AMBER_400 if is_selected else ft.Colors.WHITE24,
                ),
                on_click=lambda e, name=p_name: select_player_action(name)
            )

            player_list_column.controls.append(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Column(
                                [
                                    ft.Text(p_name, size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                                    ft.Text(f"SKOR: {score}", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.AMBER_200),
                                ],
                                spacing=2
                            ),
                            ft.Row(
                                [
                                    select_btn,
                                    ft.IconButton(
                                        ft.Icons.DELETE_OUTLINE,
                                        icon_color=ft.Colors.RED_400,
                                        data=p_name,
                                        on_click=delete_player
                                    )
                                ],
                                spacing=5
                            )
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                    ),
                    bgcolor=ft.Colors.GREEN_800 if is_selected else ft.Colors.BLACK26,
                    padding=ft.padding.symmetric(horizontal=12, vertical=8),
                    border_radius=12,
                    border=ft.border.all(2, ft.Colors.AMBER_400) if is_selected else None,
                    width=320
                )
            )
        page.update()

    def delete_player(e):
        p_name = e.control.data
        if p_name in players:
            del players[p_name]
            render_players_ui()

    new_player_input = ft.TextField(
        hint_text="Yeni Oyuncu Adı",
        width=200,
        height=45,
        text_size=14
    )

    def add_player(e):
        name = new_player_input.value.strip()
        if name and name not in players:
            players[name] = 0
            new_player_input.value = ""
            if len(players) == 1:
                selected_player[0] = name
            render_players_ui()

    add_player_row = ft.Row(
        [
            new_player_input,
            ft.ElevatedButton(
                "Ekle",
                icon=ft.Icons.ADD,
                style=ft.ButtonStyle(bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE),
                on_click=add_player
            )
        ],
        alignment=ft.MainAxisAlignment.CENTER
    )

    def reset_all_scores(e):
        for p in players:
            players[p] = 0
        render_players_ui()

    # DÜZELTİLDİ: 'text=' parametresi kaldırıldı, doğrudan string verildi
    reset_button = ft.ElevatedButton(
        "TÜM SKORLARI SIFIRLA",
        icon=ft.Icons.REFRESH,
        style=ft.ButtonStyle(
            color=ft.Colors.WHITE,
            bgcolor=ft.Colors.RED_800,
            padding=12
        ),
        on_click=reset_all_scores
    )

    # İLK UI RENDER
    render_players_ui()

    page.add(
        stadium_icon,
        title_text,
        status_text,
        ft.Divider(height=5, color=ft.Colors.TRANSPARENT),
        score_card,
        ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
        active_player_text,
        ft.Divider(height=5, color=ft.Colors.TRANSPARENT),
        player_list_column,
        ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
        add_player_row,
        ft.Divider(height=15, color=ft.Colors.TRANSPARENT),
        reset_button
    )

    # --- GOL / SENSÖR MANTIĞI ---
    def trigger_goal_ui(raw_val, is_alert):
        nonlocal was_alert

        val_text.value = str(raw_val)

        if is_alert:
            page.bgcolor = ft.Colors.GREEN_700
            status_text.value = "⚽ GOOOOLLLL! ⚽"
            status_text.color = ft.Colors.AMBER_300
            stadium_icon.color = ft.Colors.AMBER_300

            if not was_alert:
                was_alert = True
                
                # Seçili Oyuncunun Skorunu Arttır
                curr_p = selected_player[0]
                if curr_p and curr_p in players:
                    players[curr_p] += 1
                    render_players_ui()

                # Ses Çal
                if goal_audio:
                    try:
                        goal_audio.play()
                    except Exception as ex:
                        print("Ses çalma hatası:", ex)
        else:
            was_alert = False
            page.bgcolor = ft.Colors.GREEN_900
            status_text.value = "SENSÖR AKTİF - MAÇ DEVAM EDİYOR"
            status_text.color = ft.Colors.WHITE
            stadium_icon.color = ft.Colors.WHITE

        page.update()

    def update_ui_disconnected():
        page.bgcolor = ft.Colors.BLUE_GREY_900
        status_text.value = "🔌 ESP8266 İLE BAĞLANTI KOPTU"
        status_text.color = ft.Colors.RED_400
        val_text.value = "---"
        page.update()

    # --- WEBSOCKET ARKA PLAN DİNLEYİCİSİ ---
    def websocket_worker():
        while True:
            try:
                def on_message(ws, message):
                    try:
                        data = json.loads(message)
                        raw_val = data.get("raw_value", 0)
                        is_alert = raw_val >= custom_threshold
                        trigger_goal_ui(raw_val, is_alert)
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

if __name__ == "__main__":
    ft.app(target=main, assets_dir=".")
