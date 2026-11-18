"""Monta e executa o notebook de análise. Uso: python montar_notebook.py <pasta do projeto>"""
import sys
from pathlib import Path

import nbformat as nbf
from nbclient import NotebookClient

pasta = Path(sys.argv[1])
nb = nbf.v4.new_notebook()
c = []
md = lambda s: c.append(nbf.v4.new_markdown_cell(s))
py = lambda s: c.append(nbf.v4.new_code_cell(s))

md("""# Onde estão as empresas e os empregos no Polo Petrolina–Juazeiro

**Problema de negócio:** uma assessoria empresarial do Vale do São Francisco quer decidir onde prospectar. Quais setores concentram mais estabelecimentos e empregos na região, em quais a região é mais especializada que o Brasil e o que cresceu entre 2022 e 2024?

**Dados:** Cadastro Central de Empresas do IBGE (SIDRA, tabelas 9509 e 9510), baixados por `baixar.py`.""")

py("""import duckdb
import pandas as pd
import matplotlib.pyplot as plt

pd.set_option("display.float_format", "{:,.2f}".format)
db = duckdb.connect()
db.execute("create table totais as select * from read_csv_auto('dados/totais_9509.csv')")
db.execute("create table setores as select * from read_csv_auto('dados/setores_9510.csv')")
COR, CINZA = "#2563eb", "#9ca3af"
def salvar(fig, nome):
    fig.tight_layout(); fig.savefig(f"imagens/{nome}.png", dpi=150); plt.show()""")

md("""## 1. Quanto os três maiores municípios representam da região

O IBGE só abre os dados por setor para municípios com 50 mil habitantes ou mais. Na RIDE, são Petrolina, Juazeiro e Casa Nova. Antes de seguir, vale medir quanto eles representam.""")

py("""peso = db.sql('''
    select ano,
           sum(valor) filter (where codigo_local in (2611101, 2918407, 2907202)) as tres_maiores,
           sum(valor) filter (where codigo_local <> 1) as ride
    from totais where variavel = 'pessoal_ocupado' group by ano order by ano
''').df()
peso["participacao_%"] = 100 * peso.tres_maiores / peso.ride
peso""")

md("## 2. Os setores que mais empregam (Petrolina + Juazeiro + Casa Nova, 2024)")

py("""regiao = db.sql('''
    select setor,
           sum(valor) filter (where variavel = 'pessoal_ocupado') as pessoal,
           sum(valor) filter (where variavel = 'unidades_locais') as unidades
    from setores
    where ano = 2024 and codigo_local <> 1 and setor <> 'Total'
    group by setor order by pessoal desc
''').df()
regiao["setor_curto"] = regiao.setor.str.slice(0, 45)
top = regiao.head(10).iloc[::-1]
fig, ax = plt.subplots(figsize=(9, 5))
ax.barh(top.setor_curto, top.pessoal, color=COR)
ax.set_title("Pessoal ocupado por setor, 2024 (3 maiores municípios da RIDE)")
ax.set_xlabel("pessoas ocupadas")
salvar(fig, "1-setores-que-mais-empregam")
regiao.head(10)[["setor", "pessoal", "unidades"]]""")

md("""## 3. Em que a região é especializada (quociente locacional)

QL = (participação do setor no emprego da região) ÷ (participação do setor no emprego do Brasil). QL acima de 1 indica que a região emprega proporcionalmente mais naquele setor do que o país.""")

py("""ql = db.sql('''
    with base as (
        select case when codigo_local = 1 then 'brasil' else 'regiao' end as onde, setor, sum(valor) as pessoal
        from setores where ano = 2024 and variavel = 'pessoal_ocupado'
        group by all
    ), part as (
        select b.onde, b.setor, b.pessoal / t.pessoal as fatia
        from base b join base t on t.onde = b.onde and t.setor = 'Total'
        where b.setor <> 'Total'
    )
    select r.setor, r.fatia * 100 as fatia_regiao_pct, b.fatia * 100 as fatia_brasil_pct, r.fatia / b.fatia as ql
    from part r join part b on b.setor = r.setor and b.onde = 'brasil'
    where r.onde = 'regiao' and b.fatia > 0
    order by ql desc
''').df()
ql["setor_curto"] = ql.setor.str.slice(0, 45)
q = ql[ql.fatia_regiao_pct >= 1].sort_values("ql")
fig, ax = plt.subplots(figsize=(9, 6))
ax.barh(q.setor_curto, q.ql, color=[COR if v >= 1 else CINZA for v in q.ql])
ax.axvline(1, color="black", linewidth=0.8)
ax.set_title("Quociente locacional do emprego, 2024")
ax.set_xlabel("QL (1 = igual ao Brasil)")
salvar(fig, "2-quociente-locacional")
ql[["setor", "fatia_regiao_pct", "fatia_brasil_pct", "ql"]]""")

md("## 4. O que cresceu entre 2022 e 2024")

py("""cres = db.sql('''
    select setor,
           sum(valor) filter (where ano = 2022 and variavel = 'pessoal_ocupado') as pessoal_2022,
           sum(valor) filter (where ano = 2024 and variavel = 'pessoal_ocupado') as pessoal_2024,
           sum(valor) filter (where ano = 2022 and variavel = 'unidades_locais') as unidades_2022,
           sum(valor) filter (where ano = 2024 and variavel = 'unidades_locais') as unidades_2024
    from setores where codigo_local <> 1 group by setor
''').df()
cres["variacao_pessoal"] = cres.pessoal_2024 - cres.pessoal_2022
cres["variacao_pessoal_%"] = 100 * cres.variacao_pessoal / cres.pessoal_2022
cres["variacao_unidades_%"] = 100 * (cres.unidades_2024 - cres.unidades_2022) / cres.unidades_2022
cres["setor_curto"] = cres.setor.str.slice(0, 45)
g = cres[cres.setor != "Total"].sort_values("variacao_pessoal").tail(10)
fig, ax = plt.subplots(figsize=(9, 5))
ax.barh(g.setor_curto, g.variacao_pessoal, color=COR)
ax.set_title("Pessoas ocupadas a mais em 2024 do que em 2022, por setor")
ax.set_xlabel("variação em pessoas")
salvar(fig, "3-crescimento-2022-2024")
cres.sort_values("variacao_pessoal", ascending=False)[["setor", "pessoal_2022", "pessoal_2024", "variacao_pessoal_%", "unidades_2022", "unidades_2024", "variacao_unidades_%"]]""")

md("## 5. Petrolina e Juazeiro lado a lado")

py("""lado = db.sql('''
    select setor,
           sum(valor) filter (where codigo_local = 2611101) as petrolina,
           sum(valor) filter (where codigo_local = 2918407) as juazeiro
    from setores where ano = 2024 and variavel = 'pessoal_ocupado' and setor <> 'Total'
    group by setor order by petrolina + juazeiro desc limit 8
''').df()
lado["setor_curto"] = lado.setor.str.slice(0, 40)
l = lado.iloc[::-1]
fig, ax = plt.subplots(figsize=(9, 5))
y = range(len(l))
ax.barh([i + 0.2 for i in y], l.petrolina, height=0.4, color=COR, label="Petrolina")
ax.barh([i - 0.2 for i in y], l.juazeiro, height=0.4, color=CINZA, label="Juazeiro")
ax.set_yticks(list(y), l.setor_curto)
ax.legend(); ax.set_title("Pessoal ocupado por setor, 2024")
salvar(fig, "4-petrolina-e-juazeiro")
lado[["setor", "petrolina", "juazeiro"]]""")

md("""## 6. Onde prospectar

Para uma assessoria, o número de **unidades locais** é o tamanho da lista de possíveis clientes, e o **crescimento** indica onde há empresas abrindo ou contratando. A tabela junta as duas coisas.""")

py("""alvo = cres[cres.setor != "Total"].merge(ql[["setor", "ql"]], on="setor", how="left")
alvo = alvo[alvo.unidades_2024 >= 100].sort_values(["unidades_2024"], ascending=False)
alvo[["setor", "unidades_2024", "variacao_unidades_%", "pessoal_2024", "variacao_pessoal_%", "ql"]].head(10)""")

md("""## Limitações

- O IBGE só publica a abertura por setor para municípios com 50 mil habitantes ou mais. Os outros 5 municípios da RIDE entram apenas nos totais (seção 1).
- Os dados vêm do cadastro de CNPJs (inclui órgãos públicos e entidades sem fins lucrativos) e não incluem trabalho informal, que é relevante na agricultura irrigada da região.
- "Unidades locais" contam estabelecimentos, não empresas: uma rede com três lojas vale três.
- A série 9509/9510 começa em 2022; para períodos anteriores, a metodologia muda (tabelas 6449 e 6450).""")

nb.cells = c
nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
(pasta / "imagens").mkdir(exist_ok=True)
NotebookClient(nb, timeout=300, kernel_name="python3", resources={"metadata": {"path": str(pasta)}}).execute()
nbf.write(nb, pasta / "analise.ipynb")
print("ok")
