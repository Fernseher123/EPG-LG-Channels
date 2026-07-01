import requests
import json
from datetime import datetime, timezone, timedelta
import xml.etree.ElementTree as ET
from xml.dom import minidom

# ----------------------------------------------------
# KONFIGURATION - für deutsche LG Channels angepasst
# ----------------------------------------------------
COUNTRY_CODE = 'DE'
LANGUAGE_CODE = 'de'
USER_AGENT = 'Mozilla/5.0 (Web0S; Linux/SmartTV) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36 LG Browser/8.0.0 WebOS.TV-2024/04.00.00 (LG; OLED65C4PUA;)'

# WICHTIG: Trage hier deinen GitHub-Benutzernamen und Repo-Namen ein,
# damit die x-tvg-url im M3U korrekt auf DEIN Repo zeigt.
GITHUB_USER = "Fernseher123"
GITHUB_REPO = "EPG-LG-Channels"

OUTPUT_M3U = "lg_channels_de.m3u"
OUTPUT_XML = "lg_epg_de.xml"

# Definition der Zeiten in UTC
jetzt = datetime.now(timezone.utc)
vergangenheit = jetzt - timedelta(hours=6)
zukunft = jetzt + timedelta(hours=12)

start_time = vergangenheit.strftime('%Y-%m-%dT%H:%M:%SZ')
end_time = zukunft.strftime('%Y-%m-%dT%H:%M:%SZ')

url = "https://api.lgchannels.com/api/v1.0/schedulelist"

params = {
    'region': COUNTRY_CODE,
    'language': LANGUAGE_CODE,
    'startTime': start_time,
    'endTime': end_time
}

headers = {
    'User-Agent': USER_AGENT,
    'X-Device-Country': COUNTRY_CODE,
    'X-Device-Language': LANGUAGE_CODE,
    'X-Authentication': 'lg-tv-services-key'
}

print("Verbinde mit der LG-API und lade offizielle Daten (Region: DE)...")

try:
    response = requests.get(url, headers=headers, params=params, timeout=15)

    if response.status_code == 200:
        dados = response.json()

        # ----------------------------------------------------
        # PHASE 1: M3U-DATEI ERZEUGEN (MIT X-TVG-URL)
        # ----------------------------------------------------
        total_canais = 0
        with open(OUTPUT_M3U, "w", encoding="utf-8") as f_m3u:
            tvg_url = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/refs/heads/main/{OUTPUT_XML}"
            f_m3u.write(f'#EXTM3U x-tvg-url="{tvg_url}"\n')

            for categoria in dados.get("categories", []):
                nome_categoria = categoria.get("categoryName", "Allgemein")

                for canal in categoria.get("channels", []):
                    channel_id = canal.get("channelId")
                    nome_canal = canal.get("channelName")
                    logo = canal.get("channelLogoUrl", "")
                    url_stream = canal.get("mediaStaticUrl", "")

                    if url_stream and channel_id:
                        url_limpa = url_stream.split('?')[0]
                        f_m3u.write(f'#EXTINF:-1 tvg-id="{channel_id}" tvg-logo="{logo}" group-title="{nome_categoria}",{nome_canal}\n')
                        f_m3u.write(f'{url_limpa}\n')
                        total_canais += 1

        print(f"[ERFOLG] Liste '{OUTPUT_M3U}' mit {total_canais} Sendern erstellt.")

        # ----------------------------------------------------
        # PHASE 2: XMLTV-DATEI ERZEUGEN (EPG)
        # ----------------------------------------------------
        tv = ET.Element('tv', generator_info_name="LG Channels EPG Extractor DE")

        for categoria in dados.get("categories", []):
            for canal in categoria.get("channels", []):
                channel_id = canal.get("channelId")
                nome_canal = canal.get("channelName")
                if channel_id:
                    channel_node = ET.SubElement(tv, 'channel', id=channel_id)
                    display_name = ET.SubElement(channel_node, 'display-name')
                    display_name.text = nome_canal
                    if canal.get("channelLogoUrl"):
                        ET.SubElement(channel_node, 'icon', src=canal.get("channelLogoUrl"))

        total_programas = 0
        for categoria in dados.get("categories", []):
            for canal in categoria.get("channels", []):
                channel_id = canal.get("channelId")
                for programa in canal.get("programs", []):
                    prog_start = programa.get("startDateTime", "").replace("-", "").replace(":", "").replace("T", "").replace("Z", " +0000")
                    prog_end = programa.get("endDateTime", "").replace("-", "").replace(":", "").replace("T", "").replace("Z", " +0000")
                    titulo = (programa.get("programTitle") or "Kein Titel").replace('&', '&amp;')
                    descricao = (programa.get("description") or "").replace('&', '&amp;')

                    if channel_id and prog_start and prog_end:
                        programme_node = ET.SubElement(tv, 'programme', start=prog_start, stop=prog_end, channel=channel_id)
                        title_node = ET.SubElement(programme_node, 'title', lang="de")
                        title_node.text = titulo
                        if descricao:
                            desc_node = ET.SubElement(programme_node, 'desc', lang="de")
                            desc_node.text = descricao
                        total_programas += 1

        xml_string = ET.tostring(tv, encoding='utf-8')
        reparsed = minidom.parseString(xml_string)
        xml_bonito = reparsed.toprettyxml(indent=" ")

        with open(OUTPUT_XML, "w", encoding="utf-8") as f_xml:
            f_xml.write(xml_bonito)

        print(f"[ERFOLG] Programmführer '{OUTPUT_XML}' mit {total_programas} Sendungen erstellt.")

        if total_canais == 0:
            print("[WARNUNG] 0 Sender gefunden. Die Region 'DE' wird von der LG-API vermutlich nicht unterstützt.")

    else:
        print(f"[FEHLER] API-Antwort fehlgeschlagen: {response.status_code}")
        print(response.text[:500])

except Exception as e:
    print(f"[FEHLER] Ausnahme während der Ausführung: {e}")
