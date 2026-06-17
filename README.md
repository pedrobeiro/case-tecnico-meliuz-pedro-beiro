# Analisador de Testes A/B de Cashback

Aplicação desenvolvida para analisar testes A/B de cashback a partir de arquivos CSV.

A solução interpreta solicitações em linguagem natural, compara grupos, identifica alertas de negócio, gera relatórios HTML e registra os resultados localmente e no Google Sheets no link: https://docs.google.com/spreadsheets/d/1XggGi-xdwQ1WcOGQejSepJ9CXXuR4eYWv3kUAE_TDHM/edit?usp=sharing.

## Configuração do `.env`

Copie o arquivo `.env.example` e renomeie a cópia para `.env`, via:

```powershell
Copy-Item .env.example .env
```

Garanta que arquivo .env está salvo no diretório.

Exemplo da .env:

```env
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash

GOOGLE_SHEETS_WEBHOOK_URL=https://script.google.com/macros/s/AKfycbwtSze1kO837TFDOqVRPDHG-BZegw8ajHmEC-kDrHFNEW8M7-fzYzlwG77ImKqSYU3pBQ/exec
GOOGLE_SHEETS_WEBHOOK_TOKEN=
```

Alguns parâmetros não foram atribuídos por motivo de segurança, já que GEMINI_API_KEY permite acesso ao gemini e GOOGLE_SHEETS_WEBHOOK_TOKEN permite acesso a aplicação do google sheets.

`GOOGLE_SHETS_WEBHOOK_TOKEN`: token enviado pelo email em resposta à proposta do case técnico, junto do link do repositório.

`GEMINI_API_KEY`: em https://aistudio.google.com/api-keys, logando conta Google com acesso ao Gemini, clicar em:
> 1. Criar chave de API.
> 2. Nomear (Optativo).
> 3. Selecionar projeto (Optativo, recomendo manter no default).
> 4. Copiar "Chave de API" (Manualmente ou apertando em "Copiar chave") --> Essa tela só aparece uma vez por chave, garantir que copiou a key. 

A chave do Gemini é necessária para interpretar as solicitações e gerar a resposta final em linguagem natural. Processo também pode ser executado sem acesso ao gemini, mas com qualidade reduzida.

A integração com o Google Sheets é opcional. Sem ela, os resultados continuam sendo registrados no arquivo CSV local, em ./outputs (pasta criada ao gerar algum teste A/B).

## Como executar

### Opção recomendada: `run.bat`

No Windows, execute o arquivo:

```text
run.bat
```

No linux, execute o arquivo:

```text
run.sh
```

O script realiza automaticamente:

- criação do ambiente virtual `.venv`;
- atualização do `pip`;
- instalação das bibliotecas do `requirements.txt`;
- execução da aplicação Streamlit.

`Atenção:` Antes da primeira execução, crie o arquivo `.env` a partir do `.env.example` e preencha as configurações necessárias, vide seção "Configuração do .env".

### Execução manual

Na pasta raiz do projeto, crie o ambiente virtual via PowerShell:

```powershell
python -m venv .venv
```

Ative o ambiente:

```powershell
.venv\Scripts\Activate.ps1
```
> Em caso de erro de execução de scripts desabilitado no sistema, rodar o comando: 
> Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
> Para liberar a janela do PowerShell

Atualize o `pip`:

```powershell
python -m pip install --upgrade pip
```

Instale as dependências:

```powershell
python -m pip install -r requirements.txt
```

Então, adicione .env e siga instruções da seção "Configuração do `.env`"

```powershell
Copy-Item .env.example .env
```

Execute a aplicação:

```powershell
python -m streamlit run scripts/app.py
```


Para encerrar o ambiente virtual:

```powershell
deactivate
```


## Como usar a aplicação

A aplicação aceita uma solicitação em linguagem natural e, opcionalmente, um arquivo CSV.

Exemplos:

```text
Qual grupo do Parceiro A maximiza as vendas totais?
```

```text
Qual grupo do Parceiro B minimiza a taxa de cashback?
```

```text
Mostre o relatório geral do Parceiro C.
```

Quando nenhum arquivo é enviado, a aplicação procura o dataset correspondente na pasta `data`.

Quando um CSV é carregado, ele é utilizado diretamente na análise.

`Para encerrar a aplicação:` Dois métodos:
> 1. Pode-se apertar em `Encerrar Aplicação`, ao final da aba deslizante à esquerda da tela, e confirmar ação.
> 2. Enviar comando `Ctrl+C` no console de execução.

## Modos de análise

### Ranking (exigido na proposta)

Compara os grupos usando uma métrica e um objetivo.

O resultado apresenta:

- grupo selecionado;
- ranking das variantes;
- diferenças entre os grupos;
- alertas financeiros;
- recomendação registrada.

### Relatório geral (função extra)

Apresenta uma visão consolidada dos grupos, sem selecionar um vencedor.

O relatório reúne os principais indicadores financeiros e operacionais do teste para que uma análise manual possa ser feita.

## Objetivos

### Maximizar

Seleciona o grupo com o maior valor para a métrica escolhida.

### Minimizar

Seleciona o grupo com o menor valor para a métrica escolhida.

## Métricas disponíveis

- compradores;
- comissão;
- cashback;
- vendas totais;
- receita líquida;
- vendas por comprador;
- comissão por comprador;
- cashback por comprador;
- receita líquida por comprador;
- taxa de comissão;
- taxa de cashback;
- margem líquida.

## Alertas de negócio

Após o ranking, o grupo selecionado também é avaliado em indicadores financeiros complementares.

A aplicação pode gerar:

- **ponto de atenção:** o grupo vence na métrica solicitada, mas apresenta desempenho financeiro inferior;
- **alerta crítico:** o resultado selecionado apresenta uma condição financeira que exige revisão antes do escalonamento.

Os alertas não alteram o ranking. Eles complementam a decisão.

## Uso do Gemini

O Gemini é utilizado para:

1. interpretar a solicitação em linguagem natural;
2. gerar a resposta final com base nos resultados calculados.

Os cálculos, rankings e alertas são realizados de forma determinística pelo Python.

Em caso de falha temporária da API, a aplicação realiza até três tentativas. 

> Durante testes, essas falhas de contato com a API do Gemini são relativamente frequentes, principalmente pelo fato de usar uma key grátis, que limita a quantidade de tokens por mensagem e quantidade de mensagens aceitas (erro 429: TooManyRequests), além do erro 503: ServiceUnavailable.

Se a interpretação continuar indisponível, é exibido um formulário para configuração manual da análise.

Se apenas a resposta final falhar, a aplicação utiliza uma resposta local.

`Para evitar falhas de contato com a API:`
> 1. Usar GEMINI_MODEL=gemini-2.5-flash-lite (padrão) - gemini-2.5-flash consume mais tokens. (resposta deve ser consistentemente melhor, em meus testes, não notei muita diferença)
> 2. Evitar enviar muitas solicitações em sequência. (evitando erro 429: TooManyRequests)
> 3. Se muitas falhas em sequência, espere alguns instantes e tente novamente.
> 4. Caso nunca consiga resposta gerada pela API, revisite a seção "Configuração do .env" e garanta que procedimento de obtenção da GEMINI_API_KEY foi seguido.


## Relatórios gerados

Cada análise gera um relatório HTML com:

- identidade visual;
- logo;
- resumo executivo;
- gráficos;
- ranking;
- alertas;
- tabelas de métricas;
- informações técnicas discretas no rodapé.

As imagens são incorporadas no próprio HTML. O relatório pode ser movido ou enviado sem depender da pasta de gráficos.

Os arquivos são criados automaticamente na pasta:

```text
outputs/
```

## Registros

Cada execução é registrada em:

```text
outputs/acompanhamento_testes.csv
```

Quando o webhook está configurado, a mesma análise também é enviada ao Google Sheets.

Uma falha na sincronização não interrompe a análise nem o registro local.

A interface informa:

- status do registro local;
- status da sincronização;
- aba utilizada;
- linha inserida;
- detalhes de possíveis erros.

## Estrutura do projeto

```text
case_tecnico_meliuz_pedro_beiro/
├── assets/
│   └── logo_meliuz.png
│
├── data/
│   ├── dataset_01_parceiroA.csv
│   ├── dataset_02_parceiroB.csv
│   └── dataset_03_parceiroC.csv
│
├── scripts/
│   ├── __init__.py
│   ├── app.py
│   ├── data_preparation_validation.py
│   ├── descriptive_ranking_analyzer.py
│   ├── google_sheets_logger.py
│   ├── integracao.py
│   ├── llm_client.py
│   ├── natural_language_response.py
│   ├── report_generator.py
│   ├── results_logger.py
│   └── warning_analyzer.py
│
├── .env.example
├── .gitignore
├── DescritivoProjeto.pdf
├── README.md
├── requirements.txt
└── run.bat
```

A pasta `outputs` é criada automaticamente durante a execução e não precisa estar presente no repositório.

## Fluxo da solução

```text
Solicitação em linguagem natural
        ↓
Interpretação pelo Gemini
        ↓
Preparação e validação do CSV
        ↓
Ranking ou relatório geral
        ↓
Análise de alertas
        ↓
Geração do relatório HTML
        ↓
Registro local e Google Sheets
        ↓
Resposta final em linguagem natural
```

## Formato esperado do CSV

O arquivo deve possuir as colunas:

```text
Data
Grupos de usuários
Parceiro
compradores
comissão
cashback
vendas totais
```

As métricas derivadas são calculadas automaticamente.

## Comportamento em caso de falhas

A aplicação mantém o fluxo principal disponível quando serviços externos falham.

- Falha na interpretação pelo Gemini: formulário manual.
- Falha na resposta final do Gemini: resposta local.
- Falha no Google Sheets: registro mantido no CSV local.
- CSV inválido: mensagem de validação para o usuário.

## Função dos scripts

Descrição aprofundada em arquivo `DescritivoProjeto.pdf`.

- `app.py`: interface Streamlit e interação com o usuário.
- `data_preparation_validation.py`: leitura, validação e preparação dos dados.
- `descriptive_ranking_analyzer.py`: consolidação das métricas, rankings e relatórios gerais.
- `warning_analyzer.py`: identificação de alertas financeiros e riscos de decisão.
- `report_generator.py`: geração dos gráficos e relatórios HTML.
- `results_logger.py`: registro dos resultados no histórico CSV local.
- `google_sheets_logger.py`: sincronização dos registros com o Google Sheets.
- `llm_client.py`: comunicação com o Gemini e interpretação das solicitações.
- `natural_language_response.py`: geração da resposta final em linguagem natural.
- `integracao.py`: coordenação de todas as etapas da análise.
- `__init__.py`: definição da pasta `scripts` como um pacote Python.

## Requisitos

- Python 3.11 ou superior;
- Windows para execução direta pelo `run.bat`;
- conexão com a internet para uso do Gemini e do Google Sheets.

A análise dos dados, a geração dos relatórios e o registro CSV local não dependem do Google Sheets.

## Autor

Case técnico realizado por **Pedro Moreira Beiro**.

## Agradecimento

Agradeço pela oportunidade de realizar essa etapa do processo seletivo "Estágio em Growth (IA e Automação) - Vaga Híbrida BH".

Espero que esse projeto esteja acima das expectativas e que possamos nos encontrar em breve nas próximas etapas.