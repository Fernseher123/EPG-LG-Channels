import requests
import json
from datetime import datetime, timezone, timedelta
import xml.etree.ElementTree as ET
from xml.dom import minidom

# Configurações para a região dos EUA
COUNTRY_CODE = 'US'
LANGUAGE_CODE = 'en'
USER_AGENT = 'Mozilla/5.0 (Web0S; Linux/SmartTV) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36 LG Browser/8.0.0 WebOS.TV-2024/04.00.00 (LG; OLED65C4PUA;)'

# Vamos capturar as próximas 6 horas de programação para o EPG
agora = datetime.now(timezone.utc)
futuro = agora + timedelta(hours=6)

start_time = agora.strftime('%Y-%m-%dT%H:%M:%SZ')
end_time = futuro.strftime('%Y-%m-%dT%H:%M:%SZ')

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

print("Conectando à API da LG e baixando dados completos (Canais + EPG)...")

try:
    response = requests.get(url, headers=headers, params=params, timeout=15)
    
    if response.status_code == 200:
        dados = response.json()
        
        # ----------------------------------------------------
        # FASE 1: GERAR O ARQUIVO M3U (LISTA DE CANAIS)
        # ----------------------------------------------------
        total_canais = 0
        with open("lg_channels_us.m3u", "w", encoding="utf-8") as f_m3u:
            f_m3u.write("#EXTM3U\n")
            
            for categoria in dados.get("categories", []):
                nome_categoria = categoria.get("categoryName", "General")
                
                for canal in categoria.get("channels", []):
                    channel_id = canal.get("channelId")
                    nome_canal = canal.get("channelName")
                    logo = canal.get("channelLogoUrl", "")
                    url_stream = canal.get("mediaStaticUrl", "")
                    
                    if url_stream and channel_id:
                        url_limpa = url_stream.split('?')[0]
                        # ADICIONADO: tvg-id para sincronizar com o XML do EPG
                        f_m3u.write(f'#EXTINF:-1 tvg-id="{channel_id}" tvg-logo="{logo}" group-title="{nome_categoria}",{nome_canal}\n')
                        f_m3u.write(f'{url_limpa}\n')
                        total_canais += 1
                        
        print(f"[SUCESSO] Lista 'lg_channels_us.m3u' gerada com {total_canais} canais mapeados.")

        # ----------------------------------------------------
        # FASE 2: GERAR O ARQUIVO XMLTV (GUIA DE PROGRAMAÇÃO)
        # ----------------------------------------------------
        tv = ET.Element('tv', generator_info_name="LG Channels EPG Extractor")
        
        # Criando o cabeçalho de canais no XML
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

        # Inserindo os programas de cada canal
        total_programas = 0
        for categoria in dados.get("categories", []):
            for canal in categoria.get("channels", []):
                channel_id = canal.get("channelId")
                
                for programa in canal.get("programs", []):
                    # Formata as datas para o padrão XMLTV (Ex: 20260523183000 +0000)
                    prog_start = programa.get("startTime", "").replace("-", "").replace(":", "").replace("T", "").replace("Z", " +0000")
                    prog_end = programa.get("endTime", "").replace("-", "").replace(":", "").replace("T", "").replace("Z", " +0000")
                    
                    titulo = programa.get("programName", "No Information")
                    descricao = programa.get("programDescription", "")
                    
                    if channel_id and prog_start and prog_end:
                        programme_node = ET.SubElement(tv, 'programme', start=prog_start, stop=prog_end, channel=channel_id)
                        
                        title_node = ET.SubElement(programme_node, 'title', lang="en")
                        title_node.text = titulo
                        
                        if descricao:
                            desc_node = ET.SubElement(programme_node, 'desc', lang="en")
                            desc_node.text = descricao
                        
                        total_programas += 1

        # Formata o XML para ficar estruturado com quebras de linha corretas
        xml_string = ET.tostring(tv, encoding='utf-8')
        reparsed = minidom.parseString(xml_string)
        xml_bonito = reparsed.toprettyxml(indent="  ")
        
        with open("lg_epg_us.xml", "w", encoding="utf-8") as f_xml:
            f_xml.write(xml_bonito)
            
        print(f"[SUCESSO] Guia de programação 'lg_epg_us.xml' gerado com {total_programas} programas listados.")
        print("\nPronto! Agora você tem o ecossistema completo para rodar no seu player IPTV.")

    else:
        print(f"[ERRO] Falha na resposta da API: {response.status_code}")

except Exception as e:
    print(f"[FALHA] Ocorreu um erro durante a execução: {e}")
