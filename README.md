# B3 Price Report API

API simples em Python para baixar, processar e disponibilizar em JSON o arquivo **BVBG.086.01 - Price Report** da B3 para uma data específica.

O projeto foi desenvolvido em um único arquivo Python e utiliza apenas bibliotecas nativas da linguagem, sem necessidade de Flask, FastAPI ou outras dependências externas.

## Funcionalidades

- Download do `BVBG.086.01 - Price Report` da B3 por data
- Extração automática de arquivos ZIP e ZIPs aninhados
- Leitura e conversão dos XMLs para JSON
- Consulta via API HTTP
- Consulta via linha de comando
- Filtro por ticker
- Filtro por prefixo de ticker
- Sem dependências externas
- Implementação em um único arquivo Python

## Requisitos

- Python 3.9+
- Acesso à internet

Não é necessário executar `pip install`.

## Estrutura do projeto

```text
.
├── b3_price_report_api.py
└── README.md
```

## Executando a API

```bash
python b3_price_report_api.py
```

Por padrão, o servidor será iniciado em:

```text
http://localhost:8000
```

Também é possível definir host e porta:

```bash
python b3_price_report_api.py --host 0.0.0.0 --port 8000
```

## Endpoints

### Health check

```http
GET /health
```

Exemplo:

```bash
curl "http://localhost:8000/health"
```

Resposta:

```json
{
  "status": "ok",
  "service": "B3 BVBG.086.01 PriceReport API"
}
```

### Price Report por data

```http
GET /price-report?date=YYYY-MM-DD
```

Exemplo:

```bash
curl "http://localhost:8000/price-report?date=2026-10-02"
```

Também existe o alias:

```http
GET /bvbg086?date=YYYY-MM-DD
```

## Filtrar por ticker

```bash
curl "http://localhost:8000/price-report?date=2026-10-02&ticker=PETR4"
```

Outro exemplo:

```bash
curl "http://localhost:8000/price-report?date=2026-10-02&ticker=VALE3"
```

## Filtrar por prefixo

Para retornar todos os instrumentos que começam com determinado código:

```bash
curl "http://localhost:8000/price-report?date=2026-10-02&prefix=DI1"
```

Exemplo para futuros de dólar:

```bash
curl "http://localhost:8000/price-report?date=2026-10-02&prefix=DOL"
```

## Formatos de data aceitos

```text
YYYY-MM-DD
DD/MM/YYYY
DD-MM-YYYY
```

Exemplos:

```text
2026-10-02
02/10/2026
02-10-2026
```

## Utilização via linha de comando

Também é possível utilizar o script sem iniciar o servidor HTTP.

### Consultar uma data

```bash
python b3_price_report_api.py --date 2026-10-02
```

### Consultar um ticker

```bash
python b3_price_report_api.py --date 2026-10-02 --ticker PETR4
```

### Consultar um prefixo

```bash
python b3_price_report_api.py --date 2026-10-02 --prefix DI1
```

O resultado será impresso diretamente em JSON.

## Exemplo de resposta

```json
{
  "source": "B3",
  "report": "BVBG.086.01 PriceReport",
  "trade_date": "2026-10-02",
  "source_file": "PR261002.zip",
  "source_xml_files": [
    "arquivo.xml"
  ],
  "filters": {
    "ticker": "PETR4",
    "prefix": null
  },
  "count": 1,
  "data": [
    {
      "TradDt": "2026-10-02",
      "TckrSymb": "PETR4",
      "TradQty": 123456,
      "NtlFinVol": 12345678.9,
      "BestBidPric": 32.7,
      "BestAskPric": 32.76,
      "FrstPric": 32.5,
      "MinPric": 31.9,
      "MaxPric": 33.1,
      "TradAvrgPric": 32.48,
      "LastPric": 32.75
    }
  ]
}
```

## Consumindo com Python

Exemplo utilizando `requests`:

```python
import requests

response = requests.get(
    "http://localhost:8000/price-report",
    params={
        "date": "2026-10-02",
        "ticker": "PETR4"
    }
)

response.raise_for_status()

data = response.json()

print(data)
```

Nesse caso, a aplicação cliente precisa ter `requests` instalado:

```bash
pip install requests
```

A API principal não depende dessa biblioteca.

## Como funciona

Fluxo simplificado:

```text
Cliente
  |
  v
GET /price-report?date=YYYY-MM-DD
  |
  v
Python API
  |
  v
B3
  |
  v
ZIP
  |
  +--> XML
  |
  +--> ZIP interno
         |
         v
        XML
  |
  v
Parser XML
  |
  v
JSON
```

A aplicação tenta localizar automaticamente arquivos utilizando as convenções:

```text
PRYYMMDD.zip
PRAYYMMDD.zip
```

Por exemplo, para 2 de outubro de 2026:

```text
PR261002.zip
PRA261002.zip
```

## Principais campos

Alguns dos campos processados pelo parser:

| Campo | Descrição |
|---|---|
| `TradDt` | Data de negociação |
| `TckrSymb` | Ticker |
| `TradQty` | Quantidade negociada |
| `NtlFinVol` | Volume financeiro |
| `OpnIntrst` | Contratos em aberto |
| `BestBidPric` | Melhor preço de compra |
| `BestAskPric` | Melhor preço de venda |
| `FrstPric` | Preço de abertura |
| `MinPric` | Preço mínimo |
| `MaxPric` | Preço máximo |
| `TradAvrgPric` | Preço médio |
| `LastPric` | Último preço |
| `AdjstdQt` | Preço de ajuste |
| `PrvsAdjstdQt` | Preço de ajuste anterior |
| `OscnPctg` | Oscilação percentual |
| `VartnPts` | Variação em pontos |

Campos não disponíveis para determinado instrumento podem ser retornados como `null`.

## Tratamento de erros

### Data inválida

```json
{
  "error": "Data invalida. Use YYYY-MM-DD, DD/MM/YYYY ou DD-MM-YYYY."
}
```

### Arquivo não encontrado

```json
{
  "error": "PriceReport nao encontrado/indisponivel para 2026-10-03.",
  "trade_date": "2026-10-03"
}
```

Isso pode ocorrer quando:

- a data não corresponde a um dia de pregão;
- o arquivo ainda não foi publicado;
- houve indisponibilidade temporária;
- a B3 alterou a forma de disponibilização do arquivo.

## BVBG.086.01 vs BVBG.087.01

Este projeto utiliza:

```text
BVBG.086.01 - Price Report
```

O relatório específico de índices da B3 é:

```text
BVBG.087.01 - Index Report
```

Portanto, consultas específicas de índices como IBOV, IFIX e IBrX podem exigir uma implementação adicional utilizando o `BVBG.087.01`.

## Performance

O arquivo diário pode conter milhares de registros.

Para reduzir o tamanho das respostas, prefira utilizar filtros como:

```text
ticker
prefix
```

Em produção, também é recomendável implementar cache para evitar baixar e processar repetidamente o mesmo arquivo da B3.

## Possíveis melhorias

- Cache local dos arquivos
- Redis
- PostgreSQL
- DuckDB
- Exportação para Parquet
- Consulta por intervalo de datas
- Paginação
- Docker
- Swagger / OpenAPI
- AWS Lambda
- Google Cloud Run
- Azure Functions
- Suporte ao `BVBG.087.01 - Index Report`

## Aviso

Este projeto não é afiliado à B3.

Os dados são obtidos a partir dos arquivos disponibilizados pela B3 e estão sujeitos à disponibilidade, alterações de formato, alterações de endereço e políticas de uso e distribuição de dados da própria B3.

Para utilização comercial ou redistribuição de dados, consulte os termos e regras aplicáveis da B3.

## Licença

Defina a licença do projeto de acordo com a finalidade do repositório.

Para projetos open source, uma opção comum é a MIT License.
