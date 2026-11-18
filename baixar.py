"""Baixa do IBGE (SIDRA, Cadastro Central de Empresas) os dados da RIDE Petrolina-Juazeiro, de 2022 a 2024.

- Tabela 9509: totais de unidades locais e pessoal ocupado dos 8 municípios da RIDE e do Brasil.
- Tabela 9510: os mesmos indicadores por seção da CNAE 2.0. O IBGE só publica essa abertura para municípios
  com 50 mil habitantes ou mais; na RIDE, Petrolina, Juazeiro e Casa Nova.

Uso: python baixar.py   (gera dados/totais_9509.csv e dados/setores_9510.csv)
"""
import csv
import json
import urllib.request
from pathlib import Path

RIDE = {
    "2611101": "Petrolina (PE)", "2608750": "Lagoa Grande (PE)", "2612604": "Santa Maria da Boa Vista (PE)",
    "2609808": "Orocó (PE)", "2918407": "Juazeiro (BA)", "2907202": "Casa Nova (BA)",
    "2909901": "Curaçá (BA)", "2930774": "Sobradinho (BA)",
}
COM_SETORES = ["2611101", "2918407", "2907202"]
SECOES = [117897, 116830, 116880, 116910, 117296, 117307, 117329, 117363, 117484, 117543, 117555, 117608,
          117666, 117673, 117714, 117774, 117788, 117810, 117838, 117861, 117888, 117892]
VARIAVEIS = {"706": "unidades_locais", "707": "pessoal_ocupado"}
ANOS = "2022,2023,2024"
PASTA = Path(__file__).parent / "dados"


def sidra(caminho: str) -> list[dict]:
    with urllib.request.urlopen("https://apisidra.ibge.gov.br/values" + caminho, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))[1:]


def valor(v: str) -> str:
    # "-" é zero; "X" é valor omitido por sigilo; ".." e "..." são não disponíveis
    return "0" if v == "-" else ("" if v in ("X", "..", "...") else v)


def salvar(nome: str, cab: list[str], linhas: list[list]) -> None:
    PASTA.mkdir(exist_ok=True)
    with (PASTA / nome).open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cab)
        w.writerows(linhas)
    print(f"{len(linhas)} linhas em dados/{nome}")


totais = sidra(f"/t/9509/n6/{','.join(RIDE)}/n1/all/v/{','.join(VARIAVEIS)}/p/{ANOS}")
salvar("totais_9509.csv", ["codigo_local", "local", "ano", "variavel", "valor"],
       [[l["D1C"], l["D1N"], l["D3N"], VARIAVEIS[l["D2C"]], valor(l["V"])] for l in totais])

setores = sidra(f"/t/9510/n6/{','.join(COM_SETORES)}/n1/all/v/{','.join(VARIAVEIS)}/p/{ANOS}"
                f"/c12762/{','.join(map(str, SECOES))}")
salvar("setores_9510.csv", ["codigo_local", "local", "ano", "variavel", "setor", "valor"],
       [[l["D1C"], l["D1N"], l["D3N"], VARIAVEIS[l["D2C"]], l["D4N"], valor(l["V"])] for l in setores])
