import streamlit as st
import pandas as pd
import plotly.express as px # Gráficos interativos
from datetime import datetime, timedelta

# Importando o cérebro do seu robô
import monitor_definitivo as monitor
import cerebro_ia
import dados_ruas

# Configuração da Página
st.set_page_config(
    page_title="Monitor Rio Piracicaba",
    page_icon="🌊",
    layout="wide"
)

# Título e Atualização
st.title("🌊 Monitoramento em Tempo Real - Cachoeira do Vale")
st.markdown("---")

# Função para carregar dados (com Cache para não travar a ANA)
@st.cache_data(ttl=300) # Guarda os dados por 5 minutos (300s)
def carregar_dados():
    # Busca Timóteo
    d_timoteo = monitor.buscar_dados_xml(monitor.ESTACAO_TIMOTEO)
    # Busca Nova Era (para a IA)
    d_nova_era = monitor.buscar_dados_xml(monitor.ESTACAO_NOVA_ERA)
    
    return d_timoteo, d_nova_era

# Botão de Atualizar Manual
if st.button('🔄 Atualizar Dados Agora'):
    st.cache_data.clear()

# Carregando...
with st.spinner('Consultando satélites da ANA...'):
    d_timoteo, d_nova_era = carregar_dados()

if not d_timoteo:
    st.error("Não foi possível obter dados da ANA no momento.")
    st.stop()

# =========================================================
# 1. KPI's (NÚMEROS GRANDES)
# =========================================================
atual = d_timoteo[0]
nivel_cm = atual['nivel']
data_leitura = atual['data']

# Cálculos Auxiliares
tendencia = monitor.analisar_tendencia(d_timoteo)
velocidade = monitor.calcular_velocidade_rio(nivel_cm, data_leitura)

# IA Previsão
texto_ia = "Calculando..."
delta_ia = None
if len(d_timoteo) >= 5:
    prev, vel_ia = cerebro_ia.prever_proxima_hora(d_timoteo[:6])
    if prev:
        texto_ia = f"{prev:.0f} cm"
        delta_ia = prev - nivel_cm

# Colunas de Indicadores
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Nível Atual", f"{nivel_cm:.0f} cm", f"{tendencia}")

with col2:
    st.metric("Velocidade", velocidade)

with col3:
    st.metric("Previsão IA (1h)", texto_ia, delta=f"{delta_ia:+.0f} cm" if delta_ia else None)

with col4:
    # Status Nova Era
    if d_nova_era:
        ne_atual = d_nova_era[0]['nivel']
        ne_anterior = d_nova_era[-1]['nivel']
        var = ne_atual - ne_anterior
        st.metric("Nova Era (Cabeceira)", f"{ne_atual:.0f} cm", f"{var:+.0f} cm (24h)")
    else:
        st.metric("Nova Era", "Sem dados")

st.markdown(f"*Última leitura: {data_leitura.strftime('%d/%m/%Y às %H:%M')}*")

# =========================================================
# 2. GRÁFICO INTERATIVO
# =========================================================
st.subheader("📈 Comportamento do Rio (Últimas 24h)")

# Prepara dados para o gráfico
df = pd.DataFrame(d_timoteo)
# Filtra últimas 48 leituras (aprox 12h-24h dependendo da frequencia)
df = df.head(48) 

# Cria gráfico com Plotly (Interativo: dá para passar o mouse)
fig = px.line(df, x='data', y='nivel', markers=True, title='Nível em Timóteo (cm)')
fig.update_traces(line_color='#00E5FF', line_width=3)
fig.add_hline(y=760, line_dash="dash", line_color="red", annotation_text="Cota de Alerta (760)")
fig.add_hline(y=600, line_dash="dash", line_color="orange", annotation_text="Atenção (600)")

st.plotly_chart(fig, use_container_width=True)

# =========================================================
# 3. RISCO POR RUA
# =========================================================
st.subheader("🏘️ Situação das Ruas")

riscos = dados_ruas.calcular_risco_por_rua(nivel_cm)
df_ruas = pd.DataFrame(riscos)

# Formata para mostrar bonito
if not df_ruas.empty:
    # --- CORREÇÃO AQUI: SELEÇÃO SEGURA DE COLUNAS ---
    # Define as colunas que gostaríamos de ver
    colunas_desejadas = ['nome', 'apelido', 'cota_cheia', 'cota', 'porcentagem']
    
    # Filtra apenas as que REALMENTE existem nos dados que vieram
    colunas_existentes = [col for col in colunas_desejadas if col in df_ruas.columns]
    
    df_show = df_ruas[colunas_existentes]
    
    # Prepara a formatação (só formata o que existe)
    formatacao = {'porcentagem': "{:.1f}%"}
    if 'cota_cheia' in colunas_existentes:
        formatacao['cota_cheia'] = "{:.0f} cm"
    if 'cota' in colunas_existentes:
        formatacao['cota'] = "{:.0f} cm"
    
    # Exibe a tabela
    st.dataframe(
        df_show.style.background_gradient(subset=['porcentagem'], cmap='Reds', vmin=0, vmax=100)
               .format(formatacao),
        use_container_width=True
    )
else:
    st.info("Nenhuma rua monitorada cadastrada ou dados indisponíveis.")

# Rodapé
st.markdown("---")
st.caption("Sistema desenvolvido pelo Monitor Rio Piracicaba | Dados da ANA (Agência Nacional de Águas)")