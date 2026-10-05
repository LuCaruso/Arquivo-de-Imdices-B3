#!/usr/bin/env python3
"""
b3_price_report_api.py

API/CLI em um unico arquivo para baixar e converter o
B3 BVBG.086.01 PriceReport para JSON por data.

Sem dependencias externas: usa apenas a biblioteca padrao do Python.

USO COMO API:
    python b3_price_report_api.py --host 0.0.0.0 --port 8000

    GET http://localhost:8000/price-report?date=2026-10-02
    GET http://localhost:8000/price-report?date=2026-10-02&ticker=PETR4
    GET http://localhost:8000/price-report?date=2026-10-02&prefix=DI1
    GET http://localhost:8000/health

USO COMO CLI:
    python b3_price_report_api.py --date 2026-10-02
    python b3_price_report_api.py --date 2026-10-02 --ticker PETR4
    python b3_price_report_api.py --date 2026-10-02 --prefix DI1

Observacao:
    O BVBG.086.01 e o PriceReport (Boletim de Negociacao).
    O arquivo especifico de indices e o BVBG.087.01 IndexReport.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from datetime import date, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from zipfile import BadZipFile, ZipFile


B3_DOWNLOAD_URL = "https://www.b3.com.br/pesquisapregao/download?filelist={filename}"

# A B3 / implementacoes de mercado aparecem com as duas convencoes.
# O codigo tenta ambas automaticamente.
FILE_PATTERNS = (
    "PR{yymmdd}.zip",
    "PRA{yymmdd}.zip",
)

USER_AGENT = (
    "Mozilla/5.0 (compatible; B3PriceReportAPI/1.0; "
    "+https://www.b3.com.br/)"
)

TIMEOUT_SECONDS = 30


# Campos do BVBG.086.01 mais uteis em formato tabular.
# O parser usa o nome local da tag XML, portanto funciona mesmo com namespace.
FIELD_TYPES = {
    "TradDt": "date",
    "TckrSymb": "str",
    "Id": "str",
    "Prtry": "str",
    "MktIdrCd": "str",
    "DaysToSttlm": "int",
    "TradQty": "int",
    "MktDataStrmId": "str",
    "NtlFinVol": "float",
    "IntlFinVol": "float",
    "OpnIntrst": "int",
    "FinInstrmQty": "int",
    "BestBidPric": "float",
    "BestAskPric": "float",
    "FrstPric": "float",
    "MinPric": "float",
    "MaxPric": "float",
    "TradAvrgPric": "float",
    "LastPric": "float",
    "RglrTxsQty": "int",
    "NonRglrTxsQty": "int",
    "RglrTraddCtrcts": "int",
    "NonRglrTraddCtrcts": "int",
    "NtlRglrVol": "float",
    "NtlNonRglrVol": "float",
    "IntlRglrVol": "float",
    "IntlNonRglrVol": "float",
    "AdjstdQt": "float",
    "AdjstdQtTax": "float",
    "AdjstdQtStin": "str",
    "PrvsAdjstdQt": "float",
    "PrvsAdjstdQtTax": "float",
    "PrvsAdjstdQtStin": "str",
    "OscnPctg": "float",
    "VartnPts": "float",
    "EqvtVal": "float",
    "AdjstdValCtrct": "float",
    "MaxTradLmt": "float",
    "MinTradLmt": "float",
}


class B3PriceReportError(Exception):
    """Erro controlado da integracao com o PriceReport da B3."""


def parse_date(value: str) -> date:
    """Aceita YYYY-MM-DD, DD/MM/YYYY ou DD-MM-YYYY."""
    value = value.strip()
    formats = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y")

    for fmt in formats:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass

    raise ValueError(
        "Data invalida. Use YYYY-MM-DD, DD/MM/YYYY ou DD-MM-YYYY."
    )


def _download(url: str) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "*/*",
            "Referer": "https://www.b3.com.br/",
        },
        method="GET",
    )

    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as response:
            content = response.read()
    except urllib.error.HTTPError as exc:
        raise B3PriceReportError(
            f"B3 respondeu HTTP {exc.code} para {url}"
        ) from exc
    except urllib.error.URLError as exc:
        raise B3PriceReportError(
            f"Falha de conexao com a B3: {exc.reason}"
        ) from exc

    if not content:
        raise B3PriceReportError("A B3 retornou resposta vazia.")

    return content


def _is_zip(content: bytes) -> bool:
    return len(content) >= 4 and content[:4] == b"PK\x03\x04"


def download_price_report(trade_date: date) -> tuple[bytes, str]:
    """
    Baixa o ZIP do BVBG.086.01 para a data informada.

    Tenta PRyymmdd.zip e PRAyymmdd.zip.
    Retorna (conteudo_zip, nome_do_arquivo).
    """
    yymmdd = trade_date.strftime("%y%m%d")
    errors: list[str] = []

    for pattern in FILE_PATTERNS:
        filename = pattern.format(yymmdd=yymmdd)
        url = B3_DOWNLOAD_URL.format(
            filename=urllib.parse.quote(filename, safe="")
        )

        try:
            content = _download(url)
        except B3PriceReportError as exc:
            errors.append(str(exc))
            continue

        if _is_zip(content):
            try:
                with ZipFile(io.BytesIO(content)) as zf:
                    # Validacao estrutural simples
                    if zf.namelist():
                        return content, filename
            except BadZipFile:
                pass

        errors.append(
            f"{filename}: resposta recebida, mas nao era um ZIP valido."
        )

    raise B3PriceReportError(
        "PriceReport nao encontrado/indisponivel para "
        f"{trade_date.isoformat()}. "
        "A data pode nao ter sido dia de pregao ou o arquivo ainda nao "
        "ter sido publicado. Tentativas: " + " | ".join(errors)
    )


def _local_name(tag: str) -> str:
    """Remove namespace XML: {namespace}Tag -> Tag."""
    return tag.rsplit("}", 1)[-1]


def _convert_value(value: str | None, kind: str) -> Any:
    if value is None:
        return None

    value = value.strip()
    if value == "":
        return None

    try:
        if kind == "int":
            return int(value)
        if kind == "float":
            return float(value.replace(",", "."))
        return value
    except (TypeError, ValueError):
        # Preserva o valor bruto se houver alguma excecao de formato.
        return value


def _flatten_price_report_element(element: ET.Element) -> dict[str, Any]:
    """
    Converte um elemento PricRpt em um dicionario plano.

    Se existirem tags repetidas com o mesmo nome, a primeira ocorrencia
    e usada para manter uma estrutura simples e previsivel.
    """
    found: dict[str, str | None] = {}

    for node in element.iter():
        tag = _local_name(node.tag)
        if tag in FIELD_TYPES and tag not in found:
            found[tag] = node.text

    row: dict[str, Any] = {}
    for field, kind in FIELD_TYPES.items():
        row[field] = _convert_value(found.get(field), kind)

    return row


def _parse_xml_bytes(xml_bytes: bytes) -> list[dict[str, Any]]:
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        raise B3PriceReportError(f"XML invalido: {exc}") from exc

    rows: list[dict[str, Any]] = []

    # Layout documentado do BVBG.086.01: mensagem PriceReport / PricRpt.
    for element in root.iter():
        if _local_name(element.tag) == "PricRpt":
            rows.append(_flatten_price_report_element(element))

    # Fallback para algumas versoes/empacotamentos que usam Istrm.
    # So e utilizado se nenhum PricRpt tiver sido localizado.
    if not rows:
        for element in root.iter():
            if _local_name(element.tag) == "Istrm":
                row = _flatten_price_report_element(element)
                if row.get("TckrSymb"):
                    rows.append(row)

    return rows


def _extract_xmls_from_zip(content: bytes) -> list[tuple[str, bytes]]:
    """
    Extrai XMLs do ZIP externo, inclusive ZIPs aninhados.
    """
    xmls: list[tuple[str, bytes]] = []

    def walk_zip(zip_bytes: bytes, prefix: str = "") -> None:
        try:
            with ZipFile(io.BytesIO(zip_bytes)) as zf:
                for info in zf.infolist():
                    if info.is_dir():
                        continue

                    name = info.filename
                    lower = name.lower()
                    data = zf.read(info)

                    display_name = f"{prefix}{name}"

                    if lower.endswith(".xml"):
                        xmls.append((display_name, data))
                    elif lower.endswith(".zip") or _is_zip(data):
                        walk_zip(data, prefix=f"{display_name}::")
        except BadZipFile as exc:
            raise B3PriceReportError(
                "Falha ao abrir ZIP retornado pela B3."
            ) from exc

    walk_zip(content)
    return xmls


def get_price_report(
    trade_date: date,
    ticker: str | None = None,
    prefix: str | None = None,
) -> dict[str, Any]:
    """
    Baixa, extrai e transforma o BVBG.086.01 em JSON serializavel.
    """
    zip_content, source_file = download_price_report(trade_date)
    xmls = _extract_xmls_from_zip(zip_content)

    if not xmls:
        raise B3PriceReportError(
            "ZIP baixado, mas nenhum XML foi encontrado dentro do arquivo."
        )

    records: list[dict[str, Any]] = []
    source_xmls: list[str] = []

    for xml_name, xml_bytes in xmls:
        parsed = _parse_xml_bytes(xml_bytes)
        if parsed:
            records.extend(parsed)
            source_xmls.append(xml_name)

    ticker_norm = ticker.upper().strip() if ticker else None
    prefix_norm = prefix.upper().strip() if prefix else None

    if ticker_norm:
        records = [
            row for row in records
            if str(row.get("TckrSymb") or "").upper() == ticker_norm
        ]

    if prefix_norm:
        records = [
            row for row in records
            if str(row.get("TckrSymb") or "").upper().startswith(prefix_norm)
        ]

    records.sort(key=lambda row: str(row.get("TckrSymb") or ""))

    return {
        "source": "B3",
        "report": "BVBG.086.01 PriceReport",
        "trade_date": trade_date.isoformat(),
        "source_file": source_file,
        "source_xml_files": source_xmls,
        "filters": {
            "ticker": ticker_norm,
            "prefix": prefix_norm,
        },
        "count": len(records),
        "data": records,
    }


def json_bytes(payload: dict[str, Any], status: int = 200) -> tuple[int, bytes]:
    body = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return status, body


class APIHandler(BaseHTTPRequestHandler):
    server_version = "B3PriceReportAPI/1.0"

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        _, body = json_bytes(payload, status)

        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "public, max-age=300")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: Any) -> None:
        print(
            f"[{self.log_date_time_string()}] "
            f"{self.client_address[0]} - {fmt % args}",
            file=sys.stderr,
        )

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        params = urllib.parse.parse_qs(parsed.query)

        if path == "/health":
            self._send_json(
                200,
                {
                    "status": "ok",
                    "service": "B3 BVBG.086.01 PriceReport API",
                },
            )
            return

        if path not in ("/price-report", "/bvbg086"):
            self._send_json(
                404,
                {
                    "error": "Endpoint nao encontrado.",
                    "endpoints": [
                        "/health",
                        "/price-report?date=YYYY-MM-DD",
                        "/price-report?date=YYYY-MM-DD&ticker=PETR4",
                        "/price-report?date=YYYY-MM-DD&prefix=DI1",
                    ],
                },
            )
            return

        date_value = (params.get("date") or [None])[0]
        ticker = (params.get("ticker") or [None])[0]
        prefix = (params.get("prefix") or [None])[0]

        if not date_value:
            self._send_json(
                400,
                {
                    "error": "Parametro 'date' e obrigatorio.",
                    "example": "/price-report?date=2026-10-02",
                },
            )
            return

        try:
            trade_date = parse_date(date_value)
            payload = get_price_report(
                trade_date=trade_date,
                ticker=ticker,
                prefix=prefix,
            )
            self._send_json(200, payload)

        except ValueError as exc:
            self._send_json(400, {"error": str(exc)})
        except B3PriceReportError as exc:
            self._send_json(
                404,
                {
                    "error": str(exc),
                    "trade_date": date_value,
                },
            )
        except Exception as exc:
            self._send_json(
                500,
                {
                    "error": "Erro interno inesperado.",
                    "detail": str(exc),
                },
            )


def run_server(host: str, port: int) -> None:
    server = ThreadingHTTPServer((host, port), APIHandler)

    print(
        f"B3 PriceReport API rodando em http://{host}:{port}\n"
        f"Exemplo: http://localhost:{port}/price-report?date=2026-10-02",
        file=sys.stderr,
    )

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nEncerrando servidor...", file=sys.stderr)
    finally:
        server.server_close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Baixa o B3 BVBG.086.01 PriceReport por data e retorna JSON, "
            "via HTTP ou linha de comando."
        )
    )

    parser.add_argument(
        "--date",
        help="Data do pregao: YYYY-MM-DD, DD/MM/YYYY ou DD-MM-YYYY.",
    )
    parser.add_argument(
        "--ticker",
        help="Filtra por ticker exato, por exemplo PETR4.",
    )
    parser.add_argument(
        "--prefix",
        help="Filtra por prefixo do ticker, por exemplo DI1.",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host da API. Padrao: 127.0.0.1",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Porta da API. Padrao: 8000",
    )

    args = parser.parse_args()

    if args.date:
        try:
            trade_date = parse_date(args.date)
            payload = get_price_report(
                trade_date=trade_date,
                ticker=args.ticker,
                prefix=args.prefix,
            )
            print(
                json.dumps(
                    payload,
                    ensure_ascii=False,
                    indent=2,
                    default=str,
                )
            )
            return 0

        except (ValueError, B3PriceReportError) as exc:
            print(
                json.dumps(
                    {"error": str(exc)},
                    ensure_ascii=False,
                    indent=2,
                ),
                file=sys.stderr,
            )
            return 1

    run_server(args.host, args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
