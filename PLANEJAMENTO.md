# 📋 Planejamento do Projeto: Robô de Lançamento de Notas Acadêmicas (Aula 07)

**Status:** 🚀 100% Alinhado e pronto para início do código!

---

## 1. Objetivo do Projeto
Automatizar com **Python** e **PyAutoGUI** a leitura da planilha `notas_alunos.csv`, o saneamento de dados com "pegadinhas", o cálculo das médias finais e o preenchimento autônomo no Google Forms, além de gerar os relatórios de fechamento e pendências.

---

## 2. Regras de Negócio e Tratamento de Dados

### 📊 Tratamento de Notas (Nota01, TF01, Nota02, TF02):
* Textos no lugar de números (`FALTOU`, `falta`, `N/A`, `-`, vazios) $\rightarrow$ convertidos em `0.0`.
* Espaços soltos e vírgulas $\rightarrow$ limpos e convertidos para ponto decimal (`float`).
* Notas maiores que 10.0 $\rightarrow$ limitadas ao teto de `10.0`.

### 👤 Tratamento de Nomes:
* Remoção de múltiplos espaços internos e espaços nas pontas.
* Formatação padronizada em Title Case (ex: `Lucas Rodrigues`).
* Se o nome estiver em branco $\rightarrow$ Aluno vai para `pendencias.csv`.

### 🆔 Tratamento de RA (Registro Acadêmico):
* Remoção de textos (`"RA"`), hífens (`"-"`) e espaços.
* **Validação de dígitos:** Máximo de **6 dígitos** estritamente numéricos.
* Se estiver vazio, tiver caracteres inválidos ou passar de 6 dígitos $\rightarrow$ Aluno vai para `pendencias.csv`.

---

## 3. Fórmulas e Critérios

* **Fórmula da Média Final:**
  $$\text{Média Final} = \frac{(\text{Nota01} \times 0.8 + \text{TF01} \times 0.2) + (\text{Nota02} \times 0.8 + \text{TF02} \times 0.2)}{2}$$
* **Nota de Corte:**
  * $\ge 7.0 \rightarrow$ **Aprovado**
  * $< 7.0 \rightarrow$ **Reprovado**

---

## 4. Arquivos Gerados

1. **`relatorio_final.csv`**:
   * Contém apenas alunos com cadastro válido (Nome e RA OK).
   * Colunas: `Nome;RA;Nota01;TF01;Nota02;TF02;MediaFinal;Situacao`.
2. **`pendencias.csv`**:
   * Alunos que não puderam ser enviados ao Forms (sem Nome, sem RA ou RA $> 6$ dígitos).
   * Colunas: `Nome_Bruto;RA_Bruto;Motivo_Pendencia`.

---

## 5. Google Forms de Destino
* **Link Oficial:** [Visualizar Formulário](https://docs.google.com/forms/d/e/1FAIpQLSdpaBpSXeOIuBuLar7ZfjjYIRpdywRPRZSJnjp1Mgt2VwYyaQ/viewform?usp=publish-editor)
* **Estrutura dos Campos (em ordem):**
  1. `Nome` (Texto)
  2. `RA` (Texto)
  3. `Nota 01` (Texto)
  4. `TF 01` (Texto)
  5. `Nota 02` (Texto)
  6. `TF 02` (Texto)
  7. `Média Final` (Texto)
  8. `Situação` (Texto)

---

## 6. Mecanismos do Robô e Segurança

* **Botão de Pânico:** Pressionar a tecla **`ESC`** a qualquer momento interrompe o robô imediatamente.
* **Fail-Safe Físico:** Puxar o mouse para a coordenada `(0, 0)` (canto superior esquerdo) aciona a trava nativa do PyAutoGUI.
* **Digitação Confiável:** Uso do `pyperclip` para colar nomes com acentos (`ã`, `é`, `ç`) sem falhas de teclado.
* **Modos de Operação (Menu no Terminal):**
  * `[1]` Lançar todos os alunos válidos no Forms (Lote automático).
  * `[2]` Buscar e lançar aluno específico (por Nome ou RA).
  * `[3]` Apenas reprocessar a planilha e atualizar relatórios CSV.
  * `[0]` Sair.

---

## 7. Próximo Passo ao Retomar
* Quando você chegar em casa e mandar um *"Pode começar"*, criaremos o arquivo principal `robo_notas.py` implementando todo esse fluxo passo a passo!
