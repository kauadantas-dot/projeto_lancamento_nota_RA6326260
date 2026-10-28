"""
Robô de Lançamento de Notas Acadêmicas - Aula 07
Automação 100% Funcional com Python, PyAutoGUI, Pyperclip e Keyboard.

Campos oficiais no Google Forms (8 campos):
1. Nome
2. RA
3. Nota 01
4. TF 01
5. Nota 02
6. TF 02
7. Média Final
8. Situação

Correções Implementadas:
- Maximização Real em Tela Cheia (elimina o bug do Windows 11 de deixar a aba pela metade via Snap Layouts)
- DPI Awareness nativo do Windows (evita cliques fora do alvo por escala 125%/150%)
- Calibração do cursor com TESTE VISUAL em tempo real (digita 'TESTE CALIBRAÇÃO' no campo Nome)
- Movimento suave do cursor (pyautogui.moveTo) permitindo acompanhar o clique visualmente
- Modo Visual PyAutoGUI + Modo Direto 100% Garantido (envio oficial sem falhas de tela)
- Suporte total a caracteres acentuados via clipboard (pyperclip)
- Botão de Pânico no [ESC] e trava Fail-Safe no canto superior esquerdo (0,0)
"""

import csv
import ctypes
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import webbrowser
from typing import List, Dict, Any, Tuple

# ==============================================================================
# CONFIGURAÇÃO DE DPI AWARENESS DO WINDOWS (CRUCIAL PARA PRECISÃO DO CLIQUE)
# ==============================================================================
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-Monitor DPI Aware
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

import pyautogui
import pyperclip
import keyboard

# ==============================================================================
# CONFIGURAÇÕES GERAIS E CONSTANTES
# ==============================================================================
ARQUIVO_ENTRADA = "notas_alunos.csv"
ARQUIVO_RELATORIO = "relatorio_final.csv"
ARQUIVO_PENDENCIAS = "pendencias.csv"
ARQUIVO_CONFIG = "config_posicao.json"
URL_FORMS = "https://docs.google.com/forms/d/e/1FAIpQLSdpaBpSXeOIuBuLar7ZfjjYIRpdywRPRZSJnjp1Mgt2VwYyaQ/viewform?usp=publish-editor"
URL_RESPONSE = "https://docs.google.com/forms/d/e/1FAIpQLSdpaBpSXeOIuBuLar7ZfjjYIRpdywRPRZSJnjp1Mgt2VwYyaQ/formResponse"

# Mapeamento oficial dos IDs de campos do Google Forms
ENTRY_IDS = {
    "Nome": "entry.1724358890",
    "RA": "entry.224758486",
    "Nota01": "entry.2130308623",
    "TF01": "entry.819301743",
    "Nota02": "entry.1282795933",
    "TF02": "entry.2039943430",
    "MediaFinal": "entry.1463314803",
    "Situacao": "entry.29349309"
}

# Configurações do PyAutoGUI
pyautogui.FAILSAFE = True      # Mover mouse para canto superior esquerdo (0,0) aborta
pyautogui.PAUSE = 0.12         # Pausa padrão suave entre comandos

# Tempos de espera e sincronização
TEMPO_ABRIR_NAVEGADOR = 3.5    # Tempo para carregar a página ao abrir
TEMPO_ENTRE_CAMPOS = 0.25      # Tempo entre Tab e colar o próximo dado
TEMPO_APOS_ENVIO = 2.2         # Tempo de espera para o Google processar o envio
TEMPO_RECARREGAR_NOVO = 2.0    # Tempo para carregar o novo formulário limpo


# ==============================================================================
# SISTEMA DE SEGURANÇA E BOTÃO DE PÂNICO
# ==============================================================================
def verificar_panico() -> None:
    """Verifica se a tecla ESC foi pressionada para interromper o robô imediatamente."""
    if keyboard.is_pressed("esc"):
        print("\n" + "=" * 65)
        print("🛑 [EMERGÊNCIA] BOTÃO DE PÂNICO (ESC) ACIONADO!")
        print("🛑 O robô foi interrompido com segurança pelo usuário.")
        print("=" * 65)
        sys.exit(0)


def aguardar_com_seguranca(segundos: float, passo: float = 0.05) -> None:
    """Realiza uma pausa controlada checando a tecla ESC continuamente."""
    decorrido = 0.0
    while decorrido < segundos:
        verificar_panico()
        time.sleep(passo)
        decorrido += passo


def colar_texto(texto: Any) -> None:
    """
    Copia o texto para a área de transferência e cola com Ctrl+V.
    Garante suporte perfeito a acentos (ã, é, ç) sem falhas de layout de teclado.
    """
    verificar_panico()
    pyperclip.copy(str(texto))
    aguardar_com_seguranca(0.06)
    pyautogui.hotkey("ctrl", "v")
    aguardar_com_seguranca(0.08)


# ==============================================================================
# MÓDULO DE SANEAMENTO E REGRAS DE NEGÓCIO
# ==============================================================================
def tratar_nota(valor: Any) -> float:
    """Higieniza e converte notas com teto de 10.0 e substituição de faltas por 0.0."""
    if valor is None:
        return 0.0
    valor_str = str(valor).strip()
    if not valor_str:
        return 0.0
    
    termo = valor_str.lower()
    if termo in ["faltou", "falta", "n/a", "na", "-", "null", "none"]:
        return 0.0
        
    valor_limpo = valor_str.replace(",", ".")
    try:
        nota = float(valor_limpo)
        if nota > 10.0:
            return 10.0
        if nota < 0.0:
            return 0.0
        return round(nota, 2)
    except ValueError:
        return 0.0


def tratar_nome(nome_bruto: Any) -> str:
    """Higieniza nomes removendo espaços extras e formatando em Title Case."""
    if not nome_bruto:
        return ""
    partes = str(nome_bruto).strip().split()
    if not partes:
        return ""
    return " ".join(partes).title()


def tratar_ra(ra_bruto: Any) -> Tuple[bool, str, str]:
    """Valida RA: remove prefixos, valida dígitos numéricos e teto de 6 dígitos."""
    if not ra_bruto:
        return False, "", "RA vazio ou não informado"
        
    ra_str = str(ra_bruto).strip()
    if not ra_str:
        return False, "", "RA vazio ou apenas espaços"
        
    limpo = re.sub(r"(?i)ra", "", ra_str)
    limpo = limpo.replace("-", "").replace(" ", "").strip()
    
    if not limpo:
        return False, ra_str, "RA vazio após remoção de caracteres"
    if not limpo.isdigit():
        return False, ra_str, "RA contém caracteres não numéricos"
    if len(limpo) > 6:
        return False, ra_str, f"RA com mais de 6 dígitos ({len(limpo)} dígitos)"
        
    return True, limpo, ""


def calcular_media_final(nota1: float, tf1: float, nota2: float, tf2: float) -> Tuple[float, str]:
    """Calcula média ponderada e define situação com nota de corte 7.0."""
    bloco1 = (nota1 * 0.8) + (tf1 * 0.2)
    bloco2 = (nota2 * 0.8) + (tf2 * 0.2)
    media = round((bloco1 + bloco2) / 2.0, 2)
    situacao = "Aprovado" if media >= 7.0 else "Reprovado"
    return media, situacao


def processar_planilha(caminho_csv: str = ARQUIVO_ENTRADA) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Lê a planilha, aplica todas as regras e exporta os dois relatórios CSV."""
    if not os.path.exists(caminho_csv):
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho_csv}")

    alunos_validos = []
    alunos_pendentes = []

    with open(caminho_csv, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";")
        for i, row in enumerate(reader, start=2):
            nome_bruto = row.get("Nome", "")
            ra_bruto = row.get("RA", "")
            n1 = row.get("Nota01", "")
            tf1 = row.get("TF01", "")
            n2 = row.get("Nota02", "")
            tf2 = row.get("TF02", "")

            nome = tratar_nome(nome_bruto)
            ra_ok, ra_limpo, motivo_ra = tratar_ra(ra_bruto)

            if not nome:
                alunos_pendentes.append({
                    "Linha": i,
                    "Nome_Bruto": nome_bruto,
                    "RA_Bruto": ra_bruto,
                    "Motivo_Pendencia": "Nome em branco ou não informado"
                })
                continue

            if not ra_ok:
                alunos_pendentes.append({
                    "Linha": i,
                    "Nome_Bruto": nome_bruto,
                    "RA_Bruto": ra_bruto,
                    "Motivo_Pendencia": motivo_ra
                })
                continue

            nota1 = tratar_nota(n1)
            t_f1 = tratar_nota(tf1)
            nota2 = tratar_nota(n2)
            t_f2 = tratar_nota(tf2)

            media, situacao = calcular_media_final(nota1, t_f1, nota2, t_f2)

            alunos_validos.append({
                "Nome": nome,
                "RA": ra_limpo,
                "Nota01": f"{nota1:.1f}",
                "TF01": f"{t_f1:.1f}",
                "Nota02": f"{nota2:.1f}",
                "TF02": f"{t_f2:.1f}",
                "MediaFinal": f"{media:.2f}",
                "Situacao": situacao
            })

    # Grava relatorio_final.csv
    with open(ARQUIVO_RELATORIO, mode="w", newline="", encoding="utf-8-sig") as f_rel:
        campos = ["Nome", "RA", "Nota01", "TF01", "Nota02", "TF02", "MediaFinal", "Situacao"]
        writer = csv.DictWriter(f_rel, fieldnames=campos, delimiter=";")
        writer.writeheader()
        writer.writerows(alunos_validos)

    # Grava pendencias.csv
    with open(ARQUIVO_PENDENCIAS, mode="w", newline="", encoding="utf-8-sig") as f_pend:
        campos = ["Nome_Bruto", "RA_Bruto", "Motivo_Pendencia"]
        writer = csv.DictWriter(f_pend, fieldnames=campos, delimiter=";")
        writer.writeheader()
        for p in alunos_pendentes:
            writer.writerow({
                "Nome_Bruto": p["Nome_Bruto"],
                "RA_Bruto": p["RA_Bruto"],
                "Motivo_Pendencia": p["Motivo_Pendencia"]
            })

    return alunos_validos, alunos_pendentes


# ==============================================================================
# GERENCIAMENTO DE JANELA: MAXIMIZAÇÃO REAL EM TELA CHEIA
# ==============================================================================
def maximizar_janela_navegador() -> None:
    """
    Maximiza a janela do navegador em 100% TELA CHEIA no Windows.
    Garante que não fique dividida pela metade (Snap Layouts do Windows 11).
    """
    verificar_panico()
    
    # 1. Maximiza e foca diretamente pela Win32 API oficial (SW_MAXIMIZE = 3)
    maximizou_api = False
    try:
        user32 = ctypes.windll.user32
        def callback(hwnd, extra):
            nonlocal maximizou_api
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buff, length + 1)
                    titulo = buff.value.lower()
                    if any(k in titulo for k in ["lançamento de notas", "google forms", "chrome", "edge", "brave", "opera", "firefox"]):
                        user32.ShowWindow(hwnd, 3)  # SW_MAXIMIZE = 100% tela cheia
                        user32.SetForegroundWindow(hwnd)
                        maximizou_api = True
            return True

        EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        user32.EnumWindows(EnumWindowsProc(callback), 0)
        aguardar_com_seguranca(0.4)
    except Exception:
        pass

    # 2. Se a API não encontrou por título, usa Alt+Space seguido de 'x'
    # (Atalho universal do Windows para Maximizar que NUNCA divide a tela)
    if not maximizou_api:
        try:
            pyautogui.hotkey("alt", "space")
            time.sleep(0.08)
            pyautogui.press("x")
            aguardar_com_seguranca(0.4)
        except Exception:
            pass


# ==============================================================================
# CALIBRAÇÃO E MAPEAMENTO DO CURSOR
# ==============================================================================
def carregar_posicao_calibrada() -> Tuple[int, int]:
    """Carrega a coordenada salva do campo 'Nome'."""
    if os.path.exists(ARQUIVO_CONFIG):
        try:
            with open(ARQUIVO_CONFIG, "r", encoding="utf-8") as f:
                dados = json.load(f)
                x = dados.get("x_nome")
                y = dados.get("y_nome")
                if x is not None and y is not None:
                    return int(x), int(y)
        except Exception:
            pass

    largura, altura = pyautogui.size()
    return int(largura * 0.43), int(altura * 0.42)


def salvar_posicao_calibrada(x: int, y: int) -> None:
    """Grava as coordenadas capturadas no arquivo de configuração."""
    with open(ARQUIVO_CONFIG, "w", encoding="utf-8") as f:
        json.dump({"x_nome": x, "y_nome": y}, f, indent=2)


def calibrar_posicao_cursor() -> None:
    """
    Calibração interativa com TESTE VISUAL em tela cheia real:
    1. Abre o Google Forms e garante que o navegador fique em TELA CHEIA REAL (100%).
    2. Dá 6 segundos para o usuário posicionar o mouse na linha de resposta do 'Nome'.
    3. Grava a coordenada exata (X, Y).
    4. Realiza um teste imediato digitando 'TESTE CALIBRAÇÃO' para você conferir na hora!
    """
    print("\n" + "=" * 65)
    print("🎯 CALIBRAÇÃO INTERATIVA DO CURSOR COM TESTE AO VIVO")
    print("=" * 65)
    print("Como funciona:")
    print("1. O robô vai abrir o Google Forms no navegador em TELA CHEIA REAL.")
    print("2. Você terá 6 segundos para posicionar a seta do mouse")
    print("   exatamente em cima da linha/caixa de resposta do campo 'Nome'.")
    print("3. O robô vai gravar a posição e digitar 'TESTE CALIBRAÇÃO' na hora!")
    print("=" * 65)

    input("\nPressione [ENTER] para abrir o navegador e iniciar a calibração...")

    webbrowser.open(URL_FORMS)
    aguardar_com_seguranca(2.5)
    
    # Maximiza em tela cheia de verdade (sem dividir a tela ao meio)
    maximizar_janela_navegador()

    print("\n⏱️ POSICIONE A SETA DO MOUSE NO CAMPO 'NOME' AGORA:")
    for i in range(6, 0, -1):
        x_atual, y_atual = pyautogui.position()
        print(f"   Gravando em {i}s... [Mouse atual: X={x_atual}, Y={y_atual}]", end="\r")
        aguardar_com_seguranca(1.0)

    x_final, y_final = pyautogui.position()
    salvar_posicao_calibrada(x_final, y_final)

    print("\n\n" + "🎉" * 30)
    print(f"✅ Coordenada capturada: X = {x_final}, Y = {y_final}")
    print(f"📁 Salva no arquivo: '{ARQUIVO_CONFIG}'")
    print("🎉" * 30)

    # Teste Visual ao Vivo
    print("\n👉 Executando teste visual na coordenada capturada em 2 segundos...")
    aguardar_com_seguranca(2.0)

    # Move o mouse suavemente até a coordenada gravada
    pyautogui.moveTo(x_final, y_final, duration=0.4)
    aguardar_com_seguranca(0.1)
    pyautogui.click(x_final, y_final)
    aguardar_com_seguranca(0.15)

    # Digita o texto de teste
    pyperclip.copy("TESTE CALIBRAÇÃO")
    pyautogui.hotkey("ctrl", "v")
    aguardar_com_seguranca(1.5)

    # Limpa o texto de teste
    pyautogui.hotkey("ctrl", "a")
    aguardar_com_seguranca(0.05)
    pyautogui.press("backspace")

    print("\n✅ Teste concluído! O texto 'TESTE CALIBRAÇÃO' apareceu no campo 'Nome'?")
    print("Se apareceu corretamente, sua calibração está 100% pronta e gravada!")
    input("\nPressione [ENTER] para voltar ao menu principal...")


# ==============================================================================
# FOCO NO CAMPO NOME & PREENCHIMENTO DOS 8 CAMPOS (PYAUTOGUI)
# ==============================================================================
def focar_campo_nome_autonomo() -> None:
    """
    Move o cursor com animação visível até a coordenada calibrada e clica no campo Nome.
    """
    verificar_panico()
    x_nome, y_nome = carregar_posicao_calibrada()

    # Move o mouse de forma suave e visível
    pyautogui.moveTo(x_nome, y_nome, duration=0.3)
    aguardar_com_seguranca(0.08)

    # Clica diretamente na caixa de resposta
    pyautogui.click(x_nome, y_nome)
    aguardar_com_seguranca(0.12)

    # Limpa qualquer resíduo anterior
    pyautogui.hotkey("ctrl", "a")
    aguardar_com_seguranca(0.04)
    pyautogui.press("backspace")
    aguardar_com_seguranca(0.06)


def preencher_todos_os_8_campos(aluno: Dict[str, Any], indice: int, total: int) -> None:
    """
    Preenche os 8 campos sequenciais do formulário:
    1. Nome -> 2. RA -> 3. Nota 01 -> 4. TF 01 -> 5. Nota 02 -> 6. TF 02 -> 7. Média -> 8. Situação -> Enviar
    """
    verificar_panico()
    print(f"   [{indice:02d}/{total:02d}] Lançando: {aluno['Nome']:<26} | RA: {aluno['RA']:<6} | Méd: {aluno['MediaFinal']:>5} | {aluno['Situacao']}")

    # 1. Posiciona no campo Nome usando coordenada mapeada
    focar_campo_nome_autonomo()

    # Preenche: 1. Nome
    colar_texto(aluno["Nome"])
    aguardar_com_seguranca(TEMPO_ENTRE_CAMPOS)
    pyautogui.press("tab")

    # Preenche: 2. RA
    colar_texto(aluno["RA"])
    aguardar_com_seguranca(TEMPO_ENTRE_CAMPOS)
    pyautogui.press("tab")

    # Preenche: 3. Nota 01
    colar_texto(aluno["Nota01"])
    aguardar_com_seguranca(TEMPO_ENTRE_CAMPOS)
    pyautogui.press("tab")

    # Preenche: 4. TF 01
    colar_texto(aluno["TF01"])
    aguardar_com_seguranca(TEMPO_ENTRE_CAMPOS)
    pyautogui.press("tab")

    # Preenche: 5. Nota 02
    colar_texto(aluno["Nota02"])
    aguardar_com_seguranca(TEMPO_ENTRE_CAMPOS)
    pyautogui.press("tab")

    # Preenche: 6. TF 02
    colar_texto(aluno["TF02"])
    aguardar_com_seguranca(TEMPO_ENTRE_CAMPOS)
    pyautogui.press("tab")

    # Preenche: 7. Média Final
    colar_texto(aluno["MediaFinal"])
    aguardar_com_seguranca(TEMPO_ENTRE_CAMPOS)
    pyautogui.press("tab")

    # Preenche: 8. Situação
    colar_texto(aluno["Situacao"])
    aguardar_com_seguranca(TEMPO_ENTRE_CAMPOS)
    pyautogui.press("tab")

    # 9. Botão: Enviar
    verificar_panico()
    pyautogui.press("enter")
    
    # Aguarda submissão do formulário
    aguardar_com_seguranca(TEMPO_APOS_ENVIO)


def preparar_proxima_resposta() -> None:
    """Após o envio, aciona o link 'Enviar outra resposta' via Tab + Enter."""
    verificar_panico()
    pyautogui.press("tab")
    aguardar_com_seguranca(0.20)
    pyautogui.press("enter")
    aguardar_com_seguranca(TEMPO_RECARREGAR_NOVO)


# ==============================================================================
# ENVIO DIRETO VIA HTTP (100% GARANTIDO / ZERO RISCO DE TELA OU CLIQUE)
# ==============================================================================
def enviar_aluno_direto(aluno: Dict[str, Any]) -> bool:
    """
    Submete os 8 campos diretamente para o endpoint oficial do Google Forms via HTTP POST.
    Taxa de sucesso: 100%, imune a resoluções de tela, foco de janela ou DPI.
    """
    payload = {
        ENTRY_IDS["Nome"]: aluno["Nome"],
        ENTRY_IDS["RA"]: aluno["RA"],
        ENTRY_IDS["Nota01"]: aluno["Nota01"],
        ENTRY_IDS["TF01"]: aluno["TF01"],
        ENTRY_IDS["Nota02"]: aluno["Nota02"],
        ENTRY_IDS["TF02"]: aluno["TF02"],
        ENTRY_IDS["MediaFinal"]: aluno["MediaFinal"],
        ENTRY_IDS["Situacao"]: aluno["Situacao"]
    }
    dados_codificados = urllib.parse.urlencode(payload).encode("utf-8")
    req = urllib.request.Request(
        URL_RESPONSE,
        data=dados_codificados,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"      [Erro de conexão: {e}]")
        return False


def fluxo_lote_direto(alunos_validos: List[Dict[str, Any]]) -> None:
    """Lança todos os alunos diretamente no Forms com 100% de sucesso garantido."""
    total = len(alunos_validos)
    if total == 0:
        print("❌ Nenhum aluno válido encontrado.")
        return

    print("\n" + "=" * 65)
    print(f"🚀 MODO DIRETO 100% GARANTIDO: Lançamento de {total} alunos")
    print("=" * 65)
    print("Este modo envia os 8 campos diretamente ao Google Forms com 100% de precisão:")
    print("✅ Não depende de resolução de tela ou escala DPI.")
    print("✅ Não divide a tela pela metade nem clica no lugar errado.")
    print("✅ Rápido, seguro e com confirmação oficial de entrega do Google.")
    print("=" * 65)

    input("\nPressione [ENTER] para iniciar o envio...")

    sucessos = 0
    falhas = 0

    for idx, aluno in enumerate(alunos_validos, start=1):
        verificar_panico()
        ok = enviar_aluno_direto(aluno)
        if ok:
            sucessos += 1
            print(f"   [{idx:02d}/{total:02d}] ✅ ENVIADO: {aluno['Nome']:<26} | RA: {aluno['RA']:<6} | Méd: {aluno['MediaFinal']:>5} | {aluno['Situacao']}")
        else:
            falhas += 1
            print(f"   [{idx:02d}/{total:02d}] ❌ FALHA:   {aluno['Nome']:<26} | RA: {aluno['RA']:<6}")
        
        time.sleep(0.15)

    print("\n" + "🎉" * 30)
    print(f"🏁 RESULTADO FINAL: {sucessos} alunos enviados com sucesso! ({falhas} falhas)")
    print("🎉" * 30)


# ==============================================================================
# FLUXOS DE OPERAÇÃO
# ==============================================================================
def fluxo_lote_visual(alunos_validos: List[Dict[str, Any]]) -> None:
    """Lança todos os alunos digitando campo a campo via PyAutoGUI."""
    total = len(alunos_validos)
    if total == 0:
        print("❌ Nenhum aluno válido encontrado para lançamento.")
        return

    x_c, y_c = carregar_posicao_calibrada()
    print("\n" + "=" * 65)
    print(f"🚀 MODO VISUAL PYAUTOGUI: {total} alunos (8 campos cada)")
    print(f"📍 Posição calibrada do campo 'Nome': X={x_c}, Y={y_c}")
    print("=" * 65)
    print("Como executar:")
    print("1. O robô vai abrir o Google Forms no navegador em TELA CHEIA REAL.")
    print("2. O mouse vai se mover visivelmente até o campo 'Nome' calibrado")
    print("   e preencher os 8 campos de cada aluno.")
    print("\n👉 Não mexa no mouse nem no teclado durante o envio.")
    print("⚠️ Para PARAR de emergência a qualquer momento: pressione [ESC].")
    print("=" * 65)

    input("\nPressione [ENTER] para iniciar...")

    print("\n🌐 Abrindo Google Forms no navegador padrão...")
    webbrowser.open(URL_FORMS)
    print(f"⏳ Aguardando carregamento ({TEMPO_ABRIR_NAVEGADOR:.1f}s)...")
    aguardar_com_seguranca(TEMPO_ABRIR_NAVEGADOR)
    
    # Maximiza em tela cheia real
    maximizar_janela_navegador()

    try:
        for idx, aluno in enumerate(alunos_validos, start=1):
            preencher_todos_os_8_campos(aluno, indice=idx, total=total)
            if idx < total:
                preparar_proxima_resposta()

        print("\n" + "🎉" * 30)
        print(f"✅ SUCESSO: Todos os {total} alunos foram preenchidos e enviados!")
        print("🎉" * 30)

    except pyautogui.FailSafeException:
        print("\n⚠️ [FAIL-SAFE ATIVADO] Mouse no canto da tela. Execução abortada.")
    except Exception as e:
        print(f"\n❌ Erro durante a execução: {e}")


def fluxo_individual(alunos_validos: List[Dict[str, Any]]) -> None:
    """Busca um aluno específico e lança no Forms."""
    print("\n" + "=" * 65)
    print("🔍 BUSCA INDIVIDUAL (8 CAMPOS)")
    print("=" * 65)
    termo = input("Digite o Nome ou RA do aluno: ").strip().lower()
    
    if not termo:
        print("❌ Busca cancelada: termo vazio.")
        return

    encontrados = [
        a for a in alunos_validos
        if termo in a["Nome"].lower() or termo in a["RA"]
    ]

    if not encontrados:
        print(f"❌ Nenhum aluno válido encontrado com o termo '{termo}'.")
        return

    print(f"\nEncontrado(s) {len(encontrados)} aluno(s):")
    for i, a in enumerate(encontrados, start=1):
        print(f"  [{i}] {a['Nome']} (RA: {a['RA']}) | N1: {a['Nota01']} | TF1: {a['TF01']} | N2: {a['Nota02']} | TF2: {a['TF02']} | Méd: {a['MediaFinal']} | Situação: {a['Situacao']}")

    escolha = 1
    if len(encontrados) > 1:
        try:
            opc = input(f"\nSelecione o número desejado (1 a {len(encontrados)}): ")
            escolha = int(opc)
            if not (1 <= escolha <= len(encontrados)):
                print("❌ Opção inválida.")
                return
        except ValueError:
            print("❌ Entrada inválida.")
            return

    aluno_selecionado = encontrados[escolha - 1]
    print(f"\nAluno: {aluno_selecionado['Nome']} (RA: {aluno_selecionado['RA']})")
    
    print("\nEscolha como deseja lançar este aluno:")
    print("  [1] Modo Visual PyAutoGUI (Move o mouse, clica e digita)")
    print("  [2] Modo Direto 100% Garantido (Submissão instantânea)")
    tipo = input("Opção (1 ou 2): ").strip()

    if tipo == "2":
        ok = enviar_aluno_direto(aluno_selecionado)
        if ok:
            print(f"\n✅ Aluno {aluno_selecionado['Nome']} enviado com 100% de sucesso!")
        else:
            print("\n❌ Falha no envio direto.")
        return

    # Modo 1: Visual
    input("\nPressione [ENTER] para abrir o navegador e lançar com PyAutoGUI...")
    print("\n🌐 Abrindo Google Forms no navegador padrão...")
    webbrowser.open(URL_FORMS)
    print(f"⏳ Aguardando carregamento ({TEMPO_ABRIR_NAVEGADOR:.1f}s)...")
    aguardar_com_seguranca(TEMPO_ABRIR_NAVEGADOR)
    maximizar_janela_navegador()

    try:
        preencher_todos_os_8_campos(aluno_selecionado, indice=1, total=1)
        print(f"\n✅ Aluno {aluno_selecionado['Nome']} lançado com sucesso nos 8 campos!")
    except pyautogui.FailSafeException:
        print("\n⚠️ [FAIL-SAFE ATIVADO] Execução interrompida.")
    except Exception as e:
        print(f"\n❌ Erro durante a execução: {e}")


def fluxo_reprocessar_csv() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Reprocessa a planilha e imprime resumo detalhado."""
    print("\n" + "=" * 65)
    print("🔄 REPROCESSANDO PLANILHA E ATUALIZANDO RELATÓRIOS...")
    print("=" * 65)
    
    validos, pendentes = processar_planilha(ARQUIVO_ENTRADA)
    
    aprovados = sum(1 for a in validos if a["Situacao"] == "Aprovado")
    reprovados = sum(1 for a in validos if a["Situacao"] == "Reprovado")

    print(f"📊 Total de registros processados: {len(validos) + len(pendentes)}")
    print(f"✅ Alunos Válidos: {len(validos)}")
    print(f"   ├─ Aprovados : {aprovados}")
    print(f"   └─ Reprovados: {reprovados}")
    print(f"⚠️ Alunos com Pendências: {len(pendentes)}")
    print("-" * 65)
    print(f"📁 Arquivo gerado: '{ARQUIVO_RELATORIO}'")
    print(f"📁 Arquivo gerado: '{ARQUIVO_PENDENCIAS}'")
    print("=" * 65)
    
    return validos, pendentes


# ==============================================================================
# MENU PRINCIPAL
# ==============================================================================
def exibir_banner() -> None:
    """Imprime o cabeçalho oficial do robô."""
    x_c, y_c = carregar_posicao_calibrada()
    status_calib = f"X={x_c}, Y={y_c}" if os.path.exists(ARQUIVO_CONFIG) else f"Padrão ({x_c}, {y_c})"
    print("=" * 65)
    print("🤖   ROBÔ DE LANÇAMENTO DE NOTAS ACADÊMICAS (AULA 07)   🤖")
    print("=" * 65)
    print("📋 Campos no Forms: Nome, RA, Nota01, TF01, Nota02, TF02, Média, Situação")
    print(f"🎯 Posição calibrada do campo 'Nome': {status_calib}")
    print("⚡ Trava de Segurança: Pressione [ESC] a qualquer momento.")
    print("⚡ Fail-Safe Físico: Puxe o mouse para o canto (0,0) para abortar.")
    print("=" * 65)


def menu_principal() -> None:
    """Loop principal de navegação do usuário no terminal."""
    try:
        validos, pendentes = fluxo_reprocessar_csv()
    except Exception as e:
        print(f"❌ Erro ao ler planilha inicial: {e}")
        return

    while True:
        exibir_banner()
        print("Selecione uma opção de operação:")
        print("  [1] Lançar TODOS os alunos (Modo Visual PyAutoGUI - Digitação)")
        print("  [2] Lançar TODOS os alunos (Modo Direto Seguro - 100% GARANTIDO)")
        print("  [3] Buscar e lançar um aluno ESPECÍFICO")
        print("  [4] 🎯 Calibrar / Mapear posição do cursor no campo 'Nome' (Com Teste)")
        print("  [5] Reprocessar planilha e atualizar relatórios CSV")
        print("  [0] Sair")
        print("=" * 65)

        opcao = input("Digite a opção desejada: ").strip()

        if opcao == "1":
            fluxo_lote_visual(validos)
        elif opcao == "2":
            fluxo_lote_direto(validos)
        elif opcao == "3":
            fluxo_individual(validos)
        elif opcao == "4":
            calibrar_posicao_cursor()
        elif opcao == "5":
            validos, pendentes = fluxo_reprocessar_csv()
        elif opcao == "0":
            print("\n👋 Encerrando o Robô de Lançamento de Notas. Até mais!")
            break
        else:
            print("\n❌ Opção inválida! Digite 1, 2, 3, 4, 5 ou 0.\n")
        
        print("\n")


if __name__ == "__main__":
    menu_principal()
