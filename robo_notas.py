"""
Robô de Lançamento de Notas Acadêmicas - Aula 07
Automação com Python, PyAutoGUI, Pyperclip e Keyboard.

Campos oficiais no Google Forms (8 campos):
1. Nome
2. RA
3. Nota 01
4. TF 01
5. Nota 02
6. TF 02
7. Média Final
8. Situação

Recursos e Melhorias Implementadas:
- Calibração de coordenada do primeiro campo (Nome) com teste visual
- Checkpoint de Progresso (permite retomar de onde parou em caso de interrupção)
- Formatação de Nomes (preposições em minúsculas: 'da', 'de', 'do', etc.)
- Hook Global de Pânico no [ESC] (interrupção assíncrona a qualquer momento)
- Reset de Zoom do Navegador (Ctrl+0 para manter escala padrão)
- Maximização da Janela em Tela Cheia (evita divisão de tela do Windows 11)
- Sistema de Retentativas no Modo Direto via Web
- Seletor de Perfis de Velocidade (Rápido, Normal ou Seguro)
- DPI Awareness do Windows (melhor alinhamento de coordenadas)
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
from typing import List, Dict, Any, Tuple, Set

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
ARQUIVO_PROGRESSO = "progresso_envio.json"
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
pyautogui.PAUSE = 0.10         # Pausa padrão suave entre comandos

# Perfis de Velocidade
PERFIS_VELOCIDADE = {
    "rapido": {
        "nome": "Rápido (PCs e Conexões Ágeis)",
        "abrir_nav": 2.5,
        "entre_campos": 0.18,
        "apos_envio": 1.6,
        "recarregar_novo": 1.5
    },
    "normal": {
        "nome": "Normal (Equilibrado e Seguro - Padrão)",
        "abrir_nav": 3.5,
        "entre_campos": 0.25,
        "apos_envio": 2.2,
        "recarregar_novo": 2.0
    },
    "seguro": {
        "nome": "Seguro (Para PCs Lentos ou Internet Instável)",
        "abrir_nav": 5.0,
        "entre_campos": 0.40,
        "apos_envio": 3.2,
        "recarregar_novo": 2.8
    }
}

# Perfil ativo padrão
PERFIL_ATIVO = "normal"


def obter_tempos() -> Dict[str, float]:
    """Retorna os tempos configurados no perfil atual de velocidade."""
    return PERFIS_VELOCIDADE[PERFIL_ATIVO]


# ==============================================================================
# SISTEMA DE SEGURANÇA E BOTÃO DE PÂNICO GLOBAL
# ==============================================================================
INTERRUPCAO_ACIONADA = False

def parada_de_emergencia() -> None:
    """Disparada instantaneamente ao tocar a tecla ESC a qualquer momento."""
    global INTERRUPCAO_ACIONADA
    INTERRUPCAO_ACIONADA = True
    print("\n" + "=" * 65)
    print("🛑 [EMERGÊNCIA] BOTÃO DE PÂNICO (ESC) ACIONADO INSTANTANEAMENTE!")
    print("🛑 O robô foi interrompido com segurança pelo usuário.")
    print("=" * 65)
    sys.exit(0)

# Registra hook assíncrono global no ESC
try:
    keyboard.add_hotkey("esc", parada_de_emergencia)
except Exception:
    pass


def verificar_panico() -> None:
    """Checa se o pânico foi acionado."""
    if INTERRUPCAO_ACIONADA or keyboard.is_pressed("esc"):
        parada_de_emergencia()


def aguardar_com_seguranca(segundos: float, passo: float = 0.05) -> None:
    """Realiza uma pausa controlada checando o pânico continuamente."""
    decorrido = 0.0
    while decorrido < segundos:
        verificar_panico()
        time.sleep(passo)
        decorrido += passo


def colar_texto(texto: Any) -> None:
    """
    Copia o texto para a área de transferência e cola com Ctrl+V.
    Preserva acentuação (ã, é, ç) evitando incompatibilidades de layout de teclado.
    """
    verificar_panico()
    pyperclip.copy(str(texto))
    aguardar_com_seguranca(0.05)
    pyautogui.hotkey("ctrl", "v")
    aguardar_com_seguranca(0.06)


# ==============================================================================
# SISTEMA DE CHECKPOINT INTELIGENTE (RETOMADA DE ONDE PAROU)
# ==============================================================================
def carregar_progresso() -> Set[str]:
    """Carrega o conjunto de RAs que já foram enviados com sucesso."""
    if os.path.exists(ARQUIVO_PROGRESSO):
        try:
            with open(ARQUIVO_PROGRESSO, "r", encoding="utf-8") as f:
                dados = json.load(f)
                return set(dados.get("enviados", []))
        except Exception:
            return set()
    return set()


def salvar_aluno_enviado(ra: str) -> None:
    """Registra o RA do aluno como concluído no arquivo de progresso."""
    enviados = carregar_progresso()
    enviados.add(str(ra))
    try:
        with open(ARQUIVO_PROGRESSO, "w", encoding="utf-8") as f:
            json.dump({"enviados": list(enviados), "ultima_atualizacao": time.strftime("%Y-%m-%d %H:%M:%S")}, f, indent=2)
    except Exception:
        pass


def limpar_progresso() -> None:
    """Apaga o arquivo de progresso para reiniciar o lote do zero."""
    if os.path.exists(ARQUIVO_PROGRESSO):
        try:
            os.remove(ARQUIVO_PROGRESSO)
        except Exception:
            pass


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
    """
    Higieniza nomes de forma gramaticalmente elegante:
    - Remove múltiplos espaços internos e das pontas
    - Mantém preposições em minúsculas (da, de, do, das, dos, e)
    - Primeira e última palavra sempre em Maiúscula
    """
    if not nome_bruto:
        return ""
    partes = str(nome_bruto).strip().split()
    if not partes:
        return ""
    
    preposicoes = {"de", "da", "do", "das", "dos", "e"}
    palavras_formatadas = []
    
    for idx, p in enumerate(partes):
        p_lower = p.lower()
        # Se for preposição no meio do nome, fica minúscula
        if idx > 0 and idx < len(partes) - 1 and p_lower in preposicoes:
            palavras_formatadas.append(p_lower)
        else:
            palavras_formatadas.append(p.capitalize())
            
    return " ".join(palavras_formatadas)


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
# GERENCIAMENTO DE JANELA: MAXIMIZAÇÃO REAL E RESET DE ZOOM
# ==============================================================================
def maximizar_janela_navegador() -> None:
    """
    Maximiza a janela do navegador em tela cheia no Windows.
    Evita que fique dividida pela metade (Snap Layouts do Windows 11).
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
                        user32.ShowWindow(hwnd, 3)  # SW_MAXIMIZE = tela cheia
                        user32.SetForegroundWindow(hwnd)
                        maximizou_api = True
            return True

        EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        user32.EnumWindows(EnumWindowsProc(callback), 0)
        aguardar_com_seguranca(0.4)
    except Exception:
        pass

    # 2. Se a API não encontrou por título, usa Alt+Space seguido de 'x'
    if not maximizou_api:
        try:
            pyautogui.hotkey("alt", "space")
            time.sleep(0.08)
            pyautogui.press("x")
            aguardar_com_seguranca(0.4)
        except Exception:
            pass

    # 3. Reseta o zoom do navegador para o padrão (Ctrl+0)
    try:
        pyautogui.hotkey("ctrl", "0")
        aguardar_com_seguranca(0.2)
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
    Calibração interativa com teste visual em tela cheia:
    1. Abre o Google Forms e posiciona o navegador em tela cheia.
    2. Dá 6 segundos para o usuário posicionar o mouse na linha de resposta do 'Nome'.
    3. Grava a coordenada exata (X, Y).
    4. Realiza um teste imediato digitando 'TESTE CALIBRAÇÃO' para você conferir na hora!
    """
    print("\n" + "=" * 65)
    print("🎯 CALIBRAÇÃO INTERATIVA DO CURSOR COM TESTE AO VIVO")
    print("=" * 65)
    print("Como funciona:")
    print("1. O robô vai abrir o Google Forms no navegador em tela cheia.")
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

    pyautogui.moveTo(x_final, y_final, duration=0.4)
    aguardar_com_seguranca(0.1)
    pyautogui.click(x_final, y_final)
    aguardar_com_seguranca(0.15)

    pyperclip.copy("TESTE CALIBRAÇÃO")
    pyautogui.hotkey("ctrl", "v")
    aguardar_com_seguranca(1.5)

    pyautogui.hotkey("ctrl", "a")
    aguardar_com_seguranca(0.05)
    pyautogui.press("backspace")

    print("\n✅ Teste concluído! O texto 'TESTE CALIBRAÇÃO' apareceu no campo 'Nome'?")
    print("Se apareceu corretamente, sua calibração está pronta e gravada!")
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
    pyautogui.moveTo(x_nome, y_nome, duration=0.28)
    aguardar_com_seguranca(0.06)

    # Clica diretamente na caixa de resposta
    pyautogui.click(x_nome, y_nome)
    aguardar_com_seguranca(0.10)

    # Limpa qualquer resíduo anterior
    pyautogui.hotkey("ctrl", "a")
    aguardar_com_seguranca(0.04)
    pyautogui.press("backspace")
    aguardar_com_seguranca(0.05)


def preencher_todos_os_8_campos(aluno: Dict[str, Any], indice: int, total: int) -> None:
    """
    Preenche os 8 campos sequenciais do formulário:
    1. Nome -> 2. RA -> 3. Nota 01 -> 4. TF 01 -> 5. Nota 02 -> 6. TF 02 -> 7. Média -> 8. Situação -> Enviar
    """
    verificar_panico()
    tempos = obter_tempos()
    print(f"   [{indice:02d}/{total:02d}] Lançando: {aluno['Nome']:<26} | RA: {aluno['RA']:<6} | Méd: {aluno['MediaFinal']:>5} | {aluno['Situacao']}")

    # 1. Posiciona no campo Nome usando coordenada mapeada
    focar_campo_nome_autonomo()

    # Preenche: 1. Nome
    colar_texto(aluno["Nome"])
    aguardar_com_seguranca(tempos["entre_campos"])
    pyautogui.press("tab")

    # Preenche: 2. RA
    colar_texto(aluno["RA"])
    aguardar_com_seguranca(tempos["entre_campos"])
    pyautogui.press("tab")

    # Preenche: 3. Nota 01
    colar_texto(aluno["Nota01"])
    aguardar_com_seguranca(tempos["entre_campos"])
    pyautogui.press("tab")

    # Preenche: 4. TF 01
    colar_texto(aluno["TF01"])
    aguardar_com_seguranca(tempos["entre_campos"])
    pyautogui.press("tab")

    # Preenche: 5. Nota 02
    colar_texto(aluno["Nota02"])
    aguardar_com_seguranca(tempos["entre_campos"])
    pyautogui.press("tab")

    # Preenche: 6. TF 02
    colar_texto(aluno["TF02"])
    aguardar_com_seguranca(tempos["entre_campos"])
    pyautogui.press("tab")

    # Preenche: 7. Média Final
    colar_texto(aluno["MediaFinal"])
    aguardar_com_seguranca(tempos["entre_campos"])
    pyautogui.press("tab")

    # Preenche: 8. Situação
    colar_texto(aluno["Situacao"])
    aguardar_com_seguranca(tempos["entre_campos"])
    pyautogui.press("tab")

    # 9. Botão: Enviar
    verificar_panico()
    pyautogui.press("enter")
    
    # Aguarda submissão do formulário
    aguardar_com_seguranca(tempos["apos_envio"])


def preparar_proxima_resposta() -> None:
    """Após o envio, aciona o link 'Enviar outra resposta' via Tab + Enter."""
    verificar_panico()
    tempos = obter_tempos()
    pyautogui.press("tab")
    aguardar_com_seguranca(0.20)
    pyautogui.press("enter")
    aguardar_com_seguranca(tempos["recarregar_novo"])


# ==============================================================================
# ENVIO DIRETO VIA REQUISIÇÃO WEB COM RETENTATIVAS
# ==============================================================================
def enviar_aluno_direto(aluno: Dict[str, Any], max_tentativas: int = 3) -> bool:
    """
    Submete os 8 campos diretamente para o endpoint oficial do Google Forms via HTTP POST.
    Inclui sistema de até 3 tentativas automáticas com tolerância a instabilidade de rede.
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
    
    for tentativa in range(1, max_tentativas + 1):
        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                if resp.status == 200:
                    salvar_aluno_enviado(aluno["RA"])
                    return True
        except Exception as e:
            if tentativa < max_tentativas:
                time.sleep(1.0)
            else:
                print(f"      [Erro de conexão na tentativa {tentativa}: {e}]")
                return False
    return False


# ==============================================================================
# FLUXOS DE OPERAÇÃO
# ==============================================================================
def filtrar_alunos_por_checkpoint(alunos_validos: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], int]:
    """Verifica se há alunos já enviados e permite retomar de onde parou."""
    enviados = carregar_progresso()
    if not enviados:
        return alunos_validos, 0

    pendentes_envio = [a for a in alunos_validos if a["RA"] not in enviados]
    qtd_enviados = len(alunos_validos) - len(pendentes_envio)

    if 0 < qtd_enviados < len(alunos_validos):
        print("\n" + "=" * 65)
        print(f"📍 CHECKPOINT IDENTIFICADO: {qtd_enviados} de {len(alunos_validos)} alunos já foram enviados!")
        print("=" * 65)
        resp = input("Deseja CONTINUAR de onde parou (s) ou REINICIAR do zero (r)? [S/r]: ").strip().lower()
        if resp in ["r", "reiniciar"]:
            limpar_progresso()
            return alunos_validos, 0
        else:
            return pendentes_envio, qtd_enviados
    elif qtd_enviados >= len(alunos_validos):
        print("\n" + "=" * 65)
        print("✅ Todos os 73 alunos já constam como enviados no checkpoint anterior!")
        resp = input("Deseja reenviar todos do zero? (s/n): ").strip().lower()
        if resp in ["s", "sim", "y"]:
            limpar_progresso()
            return alunos_validos, 0
        else:
            return [], qtd_enviados

    return alunos_validos, 0


def fluxo_lote_direto(alunos_validos: List[Dict[str, Any]]) -> None:
    """Lança alunos diretamente no Forms via requisição web com retentativas."""
    alunos_para_enviar, ja_enviados = filtrar_alunos_por_checkpoint(alunos_validos)
    total = len(alunos_para_enviar)
    
    if total == 0:
        print("❌ Nenhum aluno pendente para envio.")
        return

    print("\n" + "=" * 65)
    print(f"🚀 MODO DIRETO VIA WEB: {total} alunos a enviar (Já enviados: {ja_enviados})")
    print("=" * 65)
    print("Vantagens deste modo:")
    print("✅ Não depende de resolução de tela, posição do mouse ou zoom.")
    print("✅ Não clica fora do campo nem divide a tela.")
    print("✅ Sistema de até 3 retentativas automáticas em caso de oscilação de Wi-Fi.")
    print("✅ Salva o progresso a cada aluno enviado (pode pausar a qualquer momento).")
    print("=" * 65)

    input("\nPressione [ENTER] para iniciar o envio...")

    sucessos = 0
    falhas = 0

    for idx, aluno in enumerate(alunos_para_enviar, start=1 + ja_enviados):
        verificar_panico()
        ok = enviar_aluno_direto(aluno)
        if ok:
            sucessos += 1
            print(f"   [{idx:02d}/{len(alunos_validos):02d}] ✅ ENVIADO: {aluno['Nome']:<26} | RA: {aluno['RA']:<6} | Méd: {aluno['MediaFinal']:>5} | {aluno['Situacao']}")
        else:
            falhas += 1
            print(f"   [{idx:02d}/{len(alunos_validos):02d}] ❌ FALHA:   {aluno['Nome']:<26} | RA: {aluno['RA']:<6}")
        
        time.sleep(0.12)

    if sucessos + ja_enviados == len(alunos_validos):
        limpar_progresso()

    print("\n" + "🎉" * 30)
    print(f"🏁 RESULTADO: {sucessos} alunos enviados agora! (Total concluído: {sucessos + ja_enviados}/{len(alunos_validos)})")
    print("🎉" * 30)


def fluxo_lote_visual(alunos_validos: List[Dict[str, Any]]) -> None:
    """Lança alunos digitando campo a campo via PyAutoGUI com suporte a retomada."""
    alunos_para_enviar, ja_enviados = filtrar_alunos_por_checkpoint(alunos_validos)
    total = len(alunos_para_enviar)

    if total == 0:
        print("❌ Nenhum aluno pendente para envio.")
        return

    x_c, y_c = carregar_posicao_calibrada()
    tempos = obter_tempos()
    
    print("\n" + "=" * 65)
    print(f"🚀 MODO VISUAL PYAUTOGUI: {total} alunos a enviar (Já enviados: {ja_enviados})")
    print(f"📍 Posição calibrada do campo 'Nome': X={x_c}, Y={y_c}")
    print(f"⚡ Perfil de Velocidade Ativo: {PERFIS_VELOCIDADE[PERFIL_ATIVO]['nome']}")
    print("=" * 65)
    print("Como executar:")
    print("1. O robô vai abrir o Google Forms no navegador em TELA CHEIA REAL.")
    print("2. O mouse vai se mover suavemente até o campo 'Nome' calibrado")
    print("   e preencher os 8 campos de cada aluno.")
    print("\n👉 Não mexa no mouse nem no teclado durante o envio.")
    print("⚠️ Para PARAR de emergência a qualquer momento: pressione [ESC].")
    print("=" * 65)

    input("\nPressione [ENTER] para iniciar...")

    print("\n🌐 Abrindo Google Forms no navegador padrão...")
    webbrowser.open(URL_FORMS)
    print(f"⏳ Aguardando carregamento ({tempos['abrir_nav']:.1f}s)...")
    aguardar_com_seguranca(tempos["abrir_nav"])
    
    maximizar_janela_navegador()

    try:
        for idx, aluno in enumerate(alunos_para_enviar, start=1 + ja_enviados):
            preencher_todos_os_8_campos(aluno, indice=idx, total=len(alunos_validos))
            salvar_aluno_enviado(aluno["RA"])
            if idx < len(alunos_validos):
                preparar_proxima_resposta()

        limpar_progresso()
        print("\n" + "🎉" * 30)
        print(f"✅ SUCESSO: Todos os {len(alunos_validos)} alunos foram preenchidos e enviados!")
        print("🎉" * 30)

    except pyautogui.FailSafeException:
        print("\n⚠️ [FAIL-SAFE ATIVADO] Mouse no canto da tela. Execução abortada.")
        print(f"💾 O progresso até o último aluno enviado foi salvo no checkpoint!")
    except Exception as e:
        print(f"\n❌ Erro durante a execução: {e}")
        print(f"💾 O progresso foi salvo. Você poderá continuar de onde parou.")


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
    print("  [2] Modo Direto via Web (Submissão via requisição)")
    tipo = input("Opção (1 ou 2): ").strip()

    if tipo == "2":
        ok = enviar_aluno_direto(aluno_selecionado)
        if ok:
            print(f"\n✅ Aluno {aluno_selecionado['Nome']} enviado com sucesso!")
        else:
            print("\n❌ Falha no envio direto.")
        return

    # Modo 1: Visual
    tempos = obter_tempos()
    input("\nPressione [ENTER] para abrir o navegador e lançar com PyAutoGUI...")
    print("\n🌐 Abrindo Google Forms no navegador padrão...")
    webbrowser.open(URL_FORMS)
    print(f"⏳ Aguardando carregamento ({tempos['abrir_nav']:.1f}s)...")
    aguardar_com_seguranca(tempos["abrir_nav"])
    maximizar_janela_navegador()

    try:
        preencher_todos_os_8_campos(aluno_selecionado, indice=1, total=1)
        print(f"\n✅ Aluno {aluno_selecionado['Nome']} lançado com sucesso nos 8 campos!")
    except pyautogui.FailSafeException:
        print("\n⚠️ [FAIL-SAFE ATIVADO] Execução interrompida.")
    except Exception as e:
        print(f"\n❌ Erro durante a execução: {e}")


def configurar_velocidade() -> None:
    """Permite ao usuário alternar o perfil de velocidade do robô."""
    global PERFIL_ATIVO
    print("\n" + "=" * 65)
    print("⚙️ CONFIGURAÇÃO DE VELOCIDADE DA AUTOMAÇÃO")
    print("=" * 65)
    print(f"Perfil atual: [{PERFIL_ATIVO.upper()}] - {PERFIS_VELOCIDADE[PERFIL_ATIVO]['nome']}")
    print("\nOpções disponíveis:")
    print("  [1] Rápido  (Pausas curtas - ideal para computadores rápidos)")
    print("  [2] Normal   (Equilibrado e seguro - recomendado)")
    print("  [3] Seguro   (Pausas maiores - ideal para internet ou PCs lentos)")
    print("=" * 65)
    
    opc = input("Escolha a velocidade desejada (1, 2 ou 3): ").strip()
    if opc == "1":
        PERFIL_ATIVO = "rapido"
    elif opc == "2":
        PERFIL_ATIVO = "normal"
    elif opc == "3":
        PERFIL_ATIVO = "seguro"
    else:
        print("Opção inalterada.")
        return

    print(f"\n✅ Velocidade alterada com sucesso para: {PERFIS_VELOCIDADE[PERFIL_ATIVO]['nome']}")
    aguardar_com_seguranca(1.2)


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
    progresso = carregar_progresso()
    status_progresso = f"📍 {len(progresso)}/73 enviados" if progresso else "Nenhum (Lote limpo)"
    
    print("=" * 65)
    print("🤖       ROBÔ DE LANÇAMENTO DE NOTAS ACADÊMICAS (AULA 07)      🤖")
    print("=" * 65)
    print("📋 Campos no Forms: Nome, RA, Nota01, TF01, Nota02, TF02, Média, Situação")
    print(f"🎯 Posição calibrada do campo 'Nome': {status_calib}")
    print(f"⚡ Velocidade: {PERFIS_VELOCIDADE[PERFIL_ATIVO]['nome'].split('(')[0].strip()} | Checkpoint: {status_progresso}")
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
        print("  [1] 🎯 Calibrar posição do mouse no campo 'Nome' (Recomendado)")
        print("  [2] Lançar TODOS os alunos (Modo Visual PyAutoGUI - Digitação)")
        print("  [3] Lançar TODOS os alunos (Modo Direto via Web - Rápido e Estável)")
        print("  [4] Buscar e lançar um aluno ESPECÍFICO")
        print("  [5] ⚙️ Configurar Velocidade do Robô")
        print("  [6] 🔄 Limpar Checkpoint de Progresso (Recomeçar do zero)")
        print("  [7] Reprocessar planilha e atualizar relatórios CSV")
        print("  [0] Sair")
        print("=" * 65)

        opcao = input("Digite a opção desejada: ").strip()

        if opcao == "1":
            calibrar_posicao_cursor()
        elif opcao == "2":
            fluxo_lote_visual(validos)
        elif opcao == "3":
            fluxo_lote_direto(validos)
        elif opcao == "4":
            fluxo_individual(validos)
        elif opcao == "5":
            configurar_velocidade()
        elif opcao == "6":
            limpar_progresso()
            print("\n✅ Checkpoint de progresso zerado com sucesso!\n")
            aguardar_com_seguranca(1.0)
        elif opcao == "7":
            validos, pendentes = fluxo_reprocessar_csv()
        elif opcao == "0":
            print("\n👋 Encerrando o Robô de Lançamento de Notas. Até mais!")
            break
        else:
            print("\n❌ Opção inválida! Digite uma opção de 0 a 7.\n")
        
        print("\n")


if __name__ == "__main__":
    menu_principal()
