# Lab 07: Projeto — Sistema de Lançamento de Notas Acadêmicas

**Aluno / RA:** Matheus Henrique (RA: 6326090)  
**Repositório:** `projeto_lancamento_nota_RA6326090`

---

## 🎯 Objetivos de Aprendizagem
- Integrar lógica de dados em memória (listas de dicionários) com automação desktop.
- Construir formulários simulados de entrada e atalhos de navegação.
- Calcular e exibir estatísticas consolidadas.

---

## 💼 Cenário e Desafio
Coordenadores e professores gastam horas digitando manualmente notas de turmas em portais acadêmicos legados que não possuem suporte a upload de planilhas. Este projeto desenvolve um robô em Python que lê os dados de entrada, higieniza as informações, calcula médias e situações, e realiza a digitação e submissão automatizada no Google Forms.

---

## 📊 Regras de Negócio e Cálculos

1. **Higienização de Dados**:
   - Tratamento de notas ausentes ou textuais (`FALTOU`, `-`, `N/A`), convertendo-as para `0.0`.
   - Limitação superior ao teto de `10.0`.
   - Formatação gramatical de nomes com preposições minúsculas (*da*, *de*, *do*, etc.).
   - Validação estrita de RA numérico (máximo 6 dígitos).
2. **Cálculo da Média Ponderada**:
   - $\text{Bloco 1} = (\text{Nota 01} \times 0.8) + (\text{TF 01} \times 0.2)$
   - $\text{Bloco 2} = (\text{Nota 02} \times 0.8) + (\text{TF 02} \times 0.2)$
   - $\text{Média Final} = \frac{\text{Bloco 1} + \text{Bloco 2}}{2}$
3. **Critério de Aprovação**:
   - Média Final $\ge 7.0$: **Aprovado**
   - Média Final $< 7.0$: **Reprovado**

---

## ⚙️ Arquitetura e Recursos do Robô

- **Menu Interativo**:
  - `[1] 🎯 Calibrar posição do mouse no campo 'Nome' (Recomendado)`: Calibração de coordenadas com teste visual ao vivo.
  - `[2] Lançar TODOS os alunos (Modo Visual PyAutoGUI - Digitação)`: Automação completa simulando digitação humana na tela.
  - `[3] Lançar TODOS os alunos (Modo Direto via Web - Rápido e Estável)`: Submissão via endpoint com retry automático.
  - `[4] Buscar e lançar aluno ESPECÍFICO`: Localiza alunos por Nome ou RA e exibe suas notas e situação.
  - `[5] ⚙️ Configurar Velocidade do Robô`: Perfis Rápido, Normal ou Seguro.
  - `[6] 🔄 Limpar Checkpoint de Progresso`: Gerenciamento do checkpoint de envio.
  - `[7] Reprocessar planilha e atualizar relatórios CSV`: Estatísticas atualizadas em tempo real.
- **Segurança Operacional**:
  - Trava de emergência assíncrona no botão **`[ESC]`**.
  - Fail-Safe do PyAutoGUI (mover o mouse para o canto `(0,0)` aborta a execução).
  - Maximiza a janela em tela cheia evitando o Snap Layout do Windows 11.
  - Reset de zoom padrão (`Ctrl+0`) para precisão de clique.

---

## 📁 Estrutura de Arquivos

```text
├── robo_notas.py           # Código-fonte principal da automação
├── notas_alunos.csv        # Planilha original fornecida
├── relatorio_final.csv     # Alunos válidos higienizados com média e situação (73 registros)
├── pendencias.csv          # Registros com pendências e motivos de descarte (27 registros)
├── config_posicao.json     # Coordenadas calibradas do mouse
├── README.md               # Documentação técnica do projeto
└── .gitignore              # Arquivos ignorados pelo controle de versão
```

---

## 🚀 Como Executar

1. Instale as dependências necessárias:
   ```bash
   pip install pyautogui pyperclip keyboard
   ```
2. Execute o robô:
   ```bash
   python robo_notas.py
   ```
