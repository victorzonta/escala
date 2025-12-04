import streamlit as st
import pandas as pd
from datetime import date, timedelta, datetime
import locale
import random

# Locale pt-BR
try:
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_TIME, 'Portuguese_Brazil')
    except locale.Error:
        st.warning("⚠️ Locale 'pt_BR' não disponível neste sistema. Os meses podem aparecer em inglês.")

st.set_page_config(page_title="Escala", layout="wide", page_icon=":church:")

# (opcional) estilo
try:
    with open("style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    pass

# ---- ESTADO ----
if "gerar_tabela" not in st.session_state:
    st.session_state.gerar_tabela = False
if "seed" not in st.session_state:
    st.session_state.seed = None

# Lista base de membros (será unida com nomes da disponibilidade)
membros_base = [
    "Ana Júlia", "Beatriz", "Bruna", "Davi", "Gi Sylos", "Henrique",
    "Isa Tomazini", "Zonta", "Laís",  "Samantha", "Tavares",
    "Vanessa", "Iza Silva", "Nicolly", "Rafaela"
]

# ---- DISPONIBILIDADE ---- (edite aqui)
disponibilidade = {
    "sábado": ["Beatriz", "Gi Sylos", "Henrique", "Samantha", "Tavares", "Iza Silva", "Rafaela"],
    "7h": ["Ana Júlia", "Beatriz", "Bruna", "Davi", "Gi Sylos", "Henrique","Isa Tomazini", "Zonta", "Laís", "Samantha", "Tavares","Vanessa", "Iza Silva", "Nicolly", "Rafaela"],
    "9h": ["Ana Júlia", "Beatriz", "Bruna", "Davi", "Gi Sylos", "Henrique","Isa Tomazini", "Laís", "Samantha", "Tavares","Vanessa", "Iza Silva", "Nicolly", "Rafaela"],
    "11h": ["Ana Júlia", "Beatriz", "Bruna", "Davi", "Gi Sylos", "Henrique","Isa Tomazini", "Zonta", "Laís", "Samantha", "Tavares","Vanessa", "Iza Silva", "Nicolly", "Rafaela"],
    "19h": ["Beatriz", "Bruna", "Gi Sylos", "Isa Tomazini", "Tavares", "Rafaela"]
}

# Garante que todos os nomes citados na disponibilidade existam na contagem
membros = sorted(set(membros_base) | set(sum(disponibilidade.values(), [])))

# ---- FUNÇÕES AUX ----
def proximo_no_ou_apos(d: date, alvo_weekday: int) -> date:
    dias = (alvo_weekday - d.weekday()) % 7
    return d + timedelta(days=dias)

inicio_default = proximo_no_ou_apos(date.today(), 5)   # próximo sábado
fim_base = date.today() + timedelta(days=90)
final_default = proximo_no_ou_apos(fim_base, 6)        # próximo domingo após +90d

# ---- SIDEBAR ----
st.sidebar.header("Configurações")
data_inicial = st.sidebar.date_input("Data inicial", value=inicio_default)
data_final = st.sidebar.date_input("Data final", value=final_default)

col1, col2 = st.sidebar.columns(2)
with col1:
    if st.button("Gerar tabela", type="primary", use_container_width=True):
        st.session_state.gerar_tabela = True
        if st.session_state.seed is None:
            st.session_state.seed = random.randrange(1_000_000_000)
with col2:
    if st.button("Reiniciar fluxo", use_container_width=True):
        st.session_state.gerar_tabela = False
        st.session_state.seed = None

# ---- CORPO ----
st.title("Escala dos Acólitos")

if not st.session_state.gerar_tabela:
    st.info("👋 Clique em **Gerar tabela**. A distribuição é balanceada e evita fins de semana consecutivos.")
    st.markdown(
        """
**Regras**
- Sábado 15h → 1 pessoa  
- Domingo: 7h (1), 9h (2), 11h (2), 19h (1)  
- Evita repetir nomes **no mesmo fim de semana**.  
- **Sem fins de semana consecutivos:** quem serviu no último fim de semana não serve no seguinte.  
- **Balanceamento:** prioriza quem tem **menos convocações** no período.
        """
    )
else:
    if data_final < data_inicial:
        st.error("⚠️ A 'Data final' não pode ser anterior à 'Data inicial'.")
        st.stop()

    intervalo = pd.date_range(start=pd.to_datetime(data_inicial),
                              end=pd.to_datetime(data_final),
                              freq="D")

    sabados = intervalo[intervalo.weekday == 5]
    domingos = intervalo[intervalo.weekday == 6]

    sab_fmt = [d.strftime("%d/%b") for d in sabados]
    dom_fmt = [d.strftime("%d/%b") for d in domingos]
    max_len = max(len(sab_fmt), len(dom_fmt))

    rng = random.Random(st.session_state.seed or 0)
    avisos = []

    # contagem global por pessoa
    contagem = {m: 0 for m in membros}
    # última semana ISO em que cada pessoa serviu (tupla (ano, semana))
    ultima_semana = {m: None for m in membros}

    def week_key_from_date(dt: pd.Timestamp):
        iso = dt.isocalendar()
        return (int(iso.year), int(iso.week))

    # helper: escolhe 1 nome "leve", evitando semana anterior; relaxa se necessário
    def escolher_um(pool, usados, label, semana_atual_key, semana_anterior_key):
        # 1) candidatos disponíveis, não repetidos no mesmo fds e que NÃO serviram na semana anterior
        cand = [m for m in pool if m not in usados and ultima_semana.get(m) != semana_anterior_key]
        if not cand:
            # 2) relaxa restrição de "semana anterior" se não houver ninguém
            cand = [m for m in pool if m not in usados]
            if not cand:
                avisos.append(f"Disponibilidade insuficiente ({label}): faltou 1.")
                return "—"
            else:
                avisos.append(f"Regra relaxada por falta de candidatos ({label}): alguém pode ter servido no fds anterior.")

        # desempate aleatório estável
        rng.shuffle(cand)
        # ordenar por menor contagem
        cand.sort(key=lambda x: contagem.get(x, 0))
        escolhido = cand[0]
        contagem[escolhido] = contagem.get(escolhido, 0) + 1
        ultima_semana[escolhido] = semana_atual_key  # marca que serviu neste fds
        usados.add(escolhido)
        return escolhido

    # helper: escolhe 'qtd' nomes balanceados
    def escolher_balanceado(qtd, pool, usados, label, semana_atual_key, semana_anterior_key):
        nomes = []
        for _ in range(qtd):
            nomes.append(escolher_um(pool, usados, label, semana_atual_key, semana_anterior_key))
        faltas = nomes.count("—")
        if faltas:
            avisos.append(f"Disponibilidade insuficiente ({label}): faltaram {faltas}.")
        return nomes

    col_sab, col_15h = [], []
    col_dom, col_7h, col_9h, col_11h, col_19h = [], [], [], [], []

    for i in range(max_len):
        # define a "data de referência" do fim de semana (usa o domingo se houver, senão o sábado)
        ref_dt = domingos[i] if i < len(domingos) else (sabados[i] if i < len(sabados) else None)
        if ref_dt is not None:
            semana_atual = week_key_from_date(ref_dt)
            semana_anterior = week_key_from_date(ref_dt - pd.Timedelta(days=7))
        else:
            semana_atual = semana_anterior = None

        sab_data = sab_fmt[i] if i < len(sab_fmt) else ""
        dom_data = dom_fmt[i] if i < len(dom_fmt) else ""
        usados = set()

        # sábado 15h
        if sab_data:
            n_sab = escolher_balanceado(1, disponibilidade["sábado"], usados,
                                        f"{sab_data} - Sábado 15h", semana_atual, semana_anterior)
            col_sab.append(sab_data)
            col_15h.append(n_sab[0])
        else:
            col_sab.append("")
            col_15h.append("")

        # domingo
        if dom_data:
            col_dom.append(dom_data)

            n7  = escolher_balanceado(1, disponibilidade["7h"], usados,  f"{dom_data} - Domingo 7h",  semana_atual, semana_anterior)
            n9  = escolher_balanceado(2, disponibilidade["9h"], usados,  f"{dom_data} - Domingo 9h",  semana_atual, semana_anterior)
            n11 = escolher_balanceado(2, disponibilidade["11h"], usados, f"{dom_data} - Domingo 11h", semana_atual, semana_anterior)
            n19 = escolher_balanceado(1, disponibilidade["19h"], usados, f"{dom_data} - Domingo 19h", semana_atual, semana_anterior)

            col_7h.append(n7[0])
            col_9h.append(" + ".join(n9))
            col_11h.append(" + ".join(n11))
            col_19h.append(n19[0])
        else:
            col_dom.append("")
            col_7h.append("")
            col_9h.append("")
            col_11h.append("")
            col_19h.append("")

    df = pd.DataFrame({
        "Sábado": col_sab,
        "15h": col_15h,
        "Domingo": col_dom,
        "7h": col_7h,
        "9h": col_9h,
        "11h": col_11h,
        "19h": col_19h,
    })

    st.subheader(f"Sábados e Domingos no intervalo {data_inicial} a {data_final}")
    if df[["Sábado", "Domingo"]].replace("", pd.NA).dropna(how="all").empty:
        st.info("Não há sábados ou domingos no intervalo selecionado.")
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)

    if avisos:
        st.warning("⚠️ Observações:")
        for a in sorted(set(avisos)):
            st.write(f"- {a}")

with st.expander("Ver contagem por pessoa"):
    cont_df = pd.DataFrame(
        sorted(contagem.items(), key=lambda x: (x[1], x[0])),
        columns=["Membro", "Convocações"]
    )
    st.dataframe(cont_df, hide_index=True, use_container_width=True)
