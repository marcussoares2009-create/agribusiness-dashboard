"""
Dashboard Streamlit - Gestão de Originação de Grãos
Integrado com Google Cloud Storage e BigQuery
Desenvolvido para Marcus Pinheiro
VERSÃO 2.0 - PRONTO PARA PRODUÇÃO
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
from datetime import datetime, timedelta
import json
import io
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# CONFIGURAÇÃO INICIAL DO STREAMLIT
# ============================================================================
st.set_page_config(
    page_title="Agribusiness Origination Dashboard",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# TEMA EXECUTIVE DARK MODE
# ============================================================================
COLORS = {
    'background': '#1a1a1a',
    'surface': '#2d2d2d',
    'surface_light': '#3a3a3a',
    'text_primary': '#ffffff',
    'text_secondary': '#b0b0b0',
    'neon_green': '#00ff88',
    'neon_gold': '#ffd700',
    'accent_blue': '#00d4ff',
    'danger': '#ff4444',
    'success': '#44ff44',
    'warning': '#ffaa00'
}

# CSS customizado
st.markdown(f"""
    <style>
        :root {{
            --primary-color: {COLORS['neon_green']};
            --background-color: {COLORS['background']};
            --text-color: {COLORS['text_primary']};
        }}
        
        body {{
            background-color: {COLORS['background']};
            color: {COLORS['text_primary']};
        }}
        
        .stApp {{
            background-color: {COLORS['background']};
        }}
        
        .stTabs [data-baseweb="tab-list"] {{
            gap: 2px;
        }}
        
        .stTabs [data-baseweb="tab"] {{
            height: 50px;
            padding: 10px 20px;
            background-color: {COLORS['surface']};
            border-radius: 5px;
            border: 2px solid {COLORS['surface_light']};
            color: {COLORS['text_secondary']};
            font-weight: 600;
        }}
        
        .stTabs [aria-selected="true"] {{
            background-color: {COLORS['neon_green']};
            color: {COLORS['background']};
            border-color: {COLORS['neon_green']};
        }}
        
        .metric-card {{
            background-color: {COLORS['surface']};
            padding: 20px;
            border-radius: 10px;
            border-left: 4px solid {COLORS['neon_green']};
            margin-bottom: 10px;
        }}
        
        .metric-value {{
            font-size: 32px;
            font-weight: bold;
            color: {COLORS['neon_green']};
        }}
        
        .metric-label {{
            font-size: 14px;
            color: {COLORS['text_secondary']};
            margin-top: 5px;
        }}
        
        .header-title {{
            color: {COLORS['neon_green']};
            font-size: 28px;
            font-weight: bold;
            margin-bottom: 20px;
        }}
        
        .stDataFrame {{
            background-color: {COLORS['surface']};
        }}
        
        .alert-box {{
            background-color: {COLORS['surface']};
            padding: 15px;
            border-radius: 10px;
            border-left: 4px solid;
            margin: 10px 0;
        }}
        
        .alert-critical {{
            border-left-color: {COLORS['danger']};
        }}
        
        .alert-warning {{
            border-left-color: {COLORS['warning']};
        }}
        
        .alert-info {{
            border-left-color: {COLORS['accent_blue']};
        }}
    </style>
""", unsafe_allow_html=True)

# ============================================================================
# FUNÇÕES DE CARREGAMENTO DE DADOS
# ============================================================================

@st.cache_data(ttl=300)
def load_data():
    """Carrega dados - Cloud Storage ou arquivo local"""
    try:
        # Tentar carregar do Cloud Storage
        from google.cloud import storage
        storage_client = storage.Client()
        bucket = storage_client.bucket("agribusiness-dashboard-data")
        blob = bucket.blob("dados/originacao_latest.parquet")
        data = blob.download_as_bytes()
        df = pd.read_parquet(io.BytesIO(data))
        return df
    except:
        # Fallback: carregar arquivo local
        try:
            file_path = "/home/ubuntu/upload/posiçãodepedido27-03(1).XLSX"
            df = pd.read_excel(file_path, sheet_name="Sheet1")
            
            df['Data do Lançamento'] = pd.to_datetime(df['Data do Lançamento'], errors='coerce')
            df['Data Pagamento'] = pd.to_datetime(df['Data Pagamento'], errors='coerce')
            df['Prazo Entrega'] = pd.to_datetime(df['Prazo Entrega'], errors='coerce')
            df['Qtd. Contratado'] = pd.to_numeric(df['Qtd. Contratado'], errors='coerce')
            df['Preço Líquido em Reais'] = pd.to_numeric(df['Preço Líquido em Reais'], errors='coerce')
            df['Vlr. do Frete Orçado'] = pd.to_numeric(df['Vlr. do Frete Orçado'], errors='coerce')
            
            df['CidadeOD'] = df['CidadeOD'].fillna('Não Informado')
            df['Tipo Frete'] = df['Tipo Frete'].fillna('Não Especificado')
            df['Preço Líquido em Reais'] = df['Preço Líquido em Reais'].fillna(0)
            df['Vlr. do Frete Orçado'] = df['Vlr. do Frete Orçado'].fillna(0)
            df['Status'] = df['Status'].fillna('ATIVO')
            
            return df
        except:
            st.error("❌ Erro ao carregar dados")
            return None


@st.cache_data(ttl=300)
def calcular_kpis(data):
    """Calcula KPIs principais"""
    total_quantidade = data['Qtd. Contratado'].sum()
    total_valor = data['Preço Líquido em Reais'].sum()
    total_frete = data['Vlr. do Frete Orçado'].sum()
    
    ativos = len(data[data['Status'] == 'ATIVO'])
    encerrados = len(data[data['Status'] == 'ENCERRADO'])
    
    preco_medio = total_valor / total_quantidade if total_quantidade > 0 else 0
    margem_bruta = total_valor - total_frete
    
    fidelidade = data.groupby('Descrição Parceiro')['Qtd. Contratado'].sum().nlargest(1)
    top_fornecedor = fidelidade.index[0] if len(fidelidade) > 0 else "N/A"
    
    cidades = data['CidadeOD'].nunique()
    
    vila_rica = data[data['CidadeOD'] == 'VILA RICA']
    preco_vila = vila_rica['Preço Líquido em Reais'].mean() if len(vila_rica) > 0 else 0
    basis = preco_vila - preco_medio
    
    hoje = datetime.now()
    fluxo = data[data['Data Pagamento'].notna()].copy()
    fluxo['Dias_Vencimento'] = (fluxo['Data Pagamento'] - pd.Timestamp(hoje)).dt.days
    fluxo_30 = fluxo[fluxo['Dias_Vencimento'] <= 30]['Preço Líquido em Reais'].sum()
    
    return {
        'total_quantidade': total_quantidade,
        'total_valor': total_valor,
        'total_frete': total_frete,
        'margem_bruta': margem_bruta,
        'preco_medio': preco_medio,
        'contratos_ativos': ativos,
        'contratos_encerrados': encerrados,
        'top_fornecedor': top_fornecedor,
        'cidades': cidades,
        'preco_vila_rica': preco_vila,
        'basis_vila_rica': basis,
        'fluxo_caixa_30_dias': fluxo_30
    }


# ============================================================================
# FUNÇÕES DE VISUALIZAÇÃO
# ============================================================================

def criar_grafico_originacao_vs_meta(data):
    """Gráfico de área com curva de originação acumulada"""
    data_sorted = data.sort_values('Data do Lançamento')
    data_sorted['Acumulado'] = data_sorted['Qtd. Contratado'].cumsum()
    meta_total = data_sorted['Qtd. Contratado'].sum() * 0.8
    data_sorted['Meta_Acumulada'] = np.linspace(0, meta_total, len(data_sorted))
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=data_sorted['Data do Lançamento'],
        y=data_sorted['Acumulado'],
        fill='tozeroy',
        name='Originação Realizada',
        line=dict(color=COLORS['neon_green'], width=3),
        fillcolor='rgba(0, 255, 136, 0.2)'
    ))
    fig.add_trace(go.Scatter(
        x=data_sorted['Data do Lançamento'],
        y=data_sorted['Meta_Acumulada'],
        name='Meta (80%)',
        line=dict(color=COLORS['neon_gold'], width=2, dash='dash')
    ))
    
    fig.update_layout(
        title='Curva de Originação vs Meta',
        xaxis_title='Data de Lançamento',
        yaxis_title='Quantidade Acumulada (sc)',
        template='plotly_dark',
        hovermode='x unified',
        plot_bgcolor=COLORS['surface'],
        paper_bgcolor=COLORS['background'],
        font=dict(color=COLORS['text_primary'], size=12),
        height=400
    )
    return fig


def criar_grafico_fidelidade(data):
    """Gráfico de Curva ABC de fornecedores"""
    fidelidade = data.groupby('Descrição Parceiro')['Qtd. Contratado'].sum().nlargest(10).reset_index()
    fidelidade.columns = ['Fornecedor', 'Volume']
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=fidelidade['Fornecedor'],
        y=fidelidade['Volume'],
        marker=dict(color=COLORS['neon_green']),
        text=fidelidade['Volume'].apply(lambda x: f'{x/1e6:.1f}M'),
        textposition='outside'
    ))
    
    fig.update_layout(
        title='Top 10 Fornecedores',
        xaxis_title='Fornecedor',
        yaxis_title='Quantidade (sc)',
        template='plotly_dark',
        plot_bgcolor=COLORS['surface'],
        paper_bgcolor=COLORS['background'],
        font=dict(color=COLORS['text_primary'], size=11),
        height=400,
        xaxis_tickangle=-45
    )
    return fig


def criar_grafico_geografico(data):
    """Gráfico de bolhas por região/cidade"""
    cidade_stats = data.groupby('CidadeOD').agg({
        'Qtd. Contratado': 'sum',
        'Preço Líquido em Reais': 'mean',
        'Nº Contrato': 'count'
    }).reset_index()
    
    cidade_stats = cidade_stats[cidade_stats['CidadeOD'] != 'Não Informado'].sort_values('Qtd. Contratado', ascending=False)
    
    fig = px.scatter(
        cidade_stats,
        x='CidadeOD',
        y='Preço Líquido em Reais',
        size='Qtd. Contratado',
        color='Nº Contrato',
        title='Mapa de Exposição Geográfica'
    )
    
    fig.update_traces(marker=dict(line=dict(width=2, color=COLORS['neon_green'])))
    fig.update_layout(
        template='plotly_dark',
        plot_bgcolor=COLORS['surface'],
        paper_bgcolor=COLORS['background'],
        font=dict(color=COLORS['text_primary'], size=12),
        height=400,
        xaxis_tickangle=-45
    )
    return fig


def criar_grafico_fluxo_caixa(data):
    """Gráfico de barras com vencimentos financeiros"""
    hoje = datetime.now()
    fluxo = data[data['Data Pagamento'].notna()].copy()
    fluxo['Dias_Vencimento'] = (fluxo['Data Pagamento'] - pd.Timestamp(hoje)).dt.days
    
    fluxo_30 = fluxo[fluxo['Dias_Vencimento'] <= 30]['Preço Líquido em Reais'].sum()
    fluxo_60 = fluxo[(fluxo['Dias_Vencimento'] > 30) & (fluxo['Dias_Vencimento'] <= 60)]['Preço Líquido em Reais'].sum()
    fluxo_90 = fluxo[(fluxo['Dias_Vencimento'] > 60) & (fluxo['Dias_Vencimento'] <= 90)]['Preço Líquido em Reais'].sum()
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=['0-30 dias', '31-60 dias', '61-90 dias'],
        y=[fluxo_30, fluxo_60, fluxo_90],
        marker=dict(color=[COLORS['danger'], COLORS['warning'], COLORS['success']]),
        text=[f'R$ {v/1e6:.1f}M' for v in [fluxo_30, fluxo_60, fluxo_90]],
        textposition='outside'
    ))
    
    fig.update_layout(
        title='Alerta de Fluxo de Caixa',
        yaxis_title='Valor (R$)',
        template='plotly_dark',
        plot_bgcolor=COLORS['surface'],
        paper_bgcolor=COLORS['background'],
        font=dict(color=COLORS['text_primary'], size=12),
        height=400,
        showlegend=False
    )
    return fig


def criar_grafico_tipos_contrato(data):
    """Gráfico de distribuição por tipo de contrato"""
    contrato_dist = data.groupby('Desc Tipo Contrato')['Qtd. Contratado'].sum().reset_index()
    
    fig = px.pie(
        contrato_dist,
        values='Qtd. Contratado',
        names='Desc Tipo Contrato',
        title='Distribuição por Tipo de Contrato',
        color_discrete_sequence=[COLORS['neon_green'], COLORS['neon_gold'], COLORS['accent_blue'], 
                                 COLORS['warning'], COLORS['danger'], COLORS['success']]
    )
    
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor=COLORS['background'],
        font=dict(color=COLORS['text_primary'], size=11),
        height=400
    )
    return fig


def criar_grafico_status(data):
    """Gráfico de status dos contratos"""
    status_dist = data.groupby('Status').agg({
        'Qtd. Contratado': 'sum',
        'Nº Contrato': 'count'
    }).reset_index()
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=status_dist['Status'],
        y=status_dist['Qtd. Contratado'],
        marker=dict(color=[COLORS['success'] if x == 'ATIVO' else COLORS['danger'] for x in status_dist['Status']]),
        text=status_dist['Nº Contrato'],
        textposition='outside'
    ))
    
    fig.update_layout(
        title='Status dos Contratos',
        yaxis_title='Quantidade (sc)',
        template='plotly_dark',
        plot_bgcolor=COLORS['surface'],
        paper_bgcolor=COLORS['background'],
        font=dict(color=COLORS['text_primary'], size=12),
        height=300,
        showlegend=False
    )
    return fig


# ============================================================================
# HEADER PRINCIPAL
# ============================================================================

st.markdown(f"""
    <div style="text-align: center; margin-bottom: 30px;">
        <h1 style="color: {COLORS['neon_green']}; font-size: 40px; margin-bottom: 10px;">
            🌾 AGRIBUSINESS ORIGINATION DASHBOARD
        </h1>
        <p style="color: {COLORS['text_secondary']}; font-size: 14px;">
            Inteligência Comercial de Originação de Grãos | Executive Dark Mode | v2.0
        </p>
    </div>
""", unsafe_allow_html=True)

# ============================================================================
# SIDEBAR
# ============================================================================

with st.sidebar:
    st.markdown(f"<h2 style='color: {COLORS['neon_green']};'>⚙️ Controles</h2>", unsafe_allow_html=True)
    
    if st.button("🔄 Atualizar Dados"):
        st.cache_data.clear()
        st.rerun()
    
    st.markdown(f"""
        <div style="background-color: {COLORS['surface']}; padding: 15px; border-radius: 10px; margin-top: 20px;">
            <p style="color: {COLORS['text_secondary']}; margin: 0; font-size: 12px;">
                <strong>Status:</strong> ✅ Online<br>
                <strong>Última Atualização:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M')}<br>
                <strong>Versão:</strong> 2.0 Cloud
            </p>
        </div>
    """, unsafe_allow_html=True)

# ============================================================================
# CARREGAMENTO DE DADOS
# ============================================================================

df = load_data()

if df is None:
    st.error("❌ Erro ao carregar dados")
    st.stop()

kpis = calcular_kpis(df)

# ============================================================================
# ABAS PRINCIPAIS
# ============================================================================

tab1, tab2, tab3, tab4 = st.tabs(["📊 PANORAMA GERAL", "🗺️ MAPA DE EXPOSIÇÃO", "📦 INTELIGÊNCIA LOGÍSTICA", "⚠️ ALERTAS"])

# ============================================================================
# ABA 1: PANORAMA GERAL
# ============================================================================

with tab1:
    st.markdown(f"<h2 style='color: {COLORS['neon_green']};'>Panorama Geral de Originação</h2>", unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📦 Total Contratado", f"{kpis['total_quantidade']/1e6:.1f}M", "sacas")
    with col2:
        st.metric("💰 Valor Total", f"R$ {kpis['total_valor']/1e6:.1f}M", "reais")
    with col3:
        st.metric("💵 Preço Médio", f"R$ {kpis['preco_medio']:.2f}", "por saca")
    with col4:
        st.metric("✅ Contratos Ativos", f"{kpis['contratos_ativos']}", f"{kpis['contratos_encerrados']} encerrados")
    
    st.divider()
    
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(criar_grafico_originacao_vs_meta(df), use_container_width=True)
    with col2:
        st.plotly_chart(criar_grafico_fidelidade(df), use_container_width=True)
    
    st.divider()
    
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(criar_grafico_tipos_contrato(df), use_container_width=True)
    with col2:
        st.plotly_chart(criar_grafico_status(df), use_container_width=True)
    
    st.divider()
    
    st.markdown(f"<h3 style='color: {COLORS['neon_gold']};'>🎯 Vila Rica Basis Tracker</h3>", unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Preço Vila Rica", f"R$ {kpis['preco_vila_rica']:.2f}", "por saca")
    with col2:
        st.metric("Preço Geral", f"R$ {kpis['preco_medio']:.2f}", "por saca")
    with col3:
        st.metric("Basis", f"R$ {kpis['basis_vila_rica']:.2f}", "diferencial")
    with col4:
        st.metric("Cidades", f"{kpis['cidades']}", "regiões")

# ============================================================================
# ABA 2: MAPA DE EXPOSIÇÃO
# ============================================================================

with tab2:
    st.markdown(f"<h2 style='color: {COLORS['neon_green']};'>Mapa de Exposição Geográfica</h2>", unsafe_allow_html=True)
    
    st.plotly_chart(criar_grafico_geografico(df), use_container_width=True)
    
    st.divider()
    
    st.markdown(f"<h3 style='color: {COLORS['accent_blue']};'>Detalhamento por Cidade</h3>", unsafe_allow_html=True)
    
    cidade_detail = df.groupby('CidadeOD').agg({
        'Qtd. Contratado': 'sum',
        'Preço Líquido em Reais': ['mean', 'sum'],
        'Nº Contrato': 'count'
    }).round(2)
    
    cidade_detail.columns = ['Volume (sc)', 'Preço Médio (R$)', 'Valor Total (R$)', 'Qtd. Contratos']
    cidade_detail = cidade_detail.sort_values('Volume (sc)', ascending=False)
    
    st.dataframe(cidade_detail, use_container_width=True, height=300)

# ============================================================================
# ABA 3: INTELIGÊNCIA LOGÍSTICA
# ============================================================================

with tab3:
    st.markdown(f"<h2 style='color: {COLORS['neon_green']};'>Inteligência Logística</h2>", unsafe_allow_html=True)
    
    st.markdown(f"<h3 style='color: {COLORS['neon_gold']};'>⚙️ Simulador de Frete Dinâmico</h3>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        frete_ajuste = st.slider("Ajuste de Frete (R$/ton):", -50.0, 50.0, 0.0, 1.0)
    with col2:
        frete_original = df['Vlr. do Frete Orçado'].sum()
        st.metric("Frete Original", f"R$ {frete_original/1e6:.2f}M")
    with col3:
        novo_frete = frete_original + (frete_ajuste * df['Qtd. Contratado'].sum() / 1000)
        st.metric("Frete Ajustado", f"R$ {novo_frete/1e6:.2f}M")
    
    margem_original = df['Preço Líquido em Reais'].sum() - frete_original
    margem_ajustada = df['Preço Líquido em Reais'].sum() - novo_frete
    impacto = margem_ajustada - margem_original
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Margem Original", f"R$ {margem_original/1e6:.2f}M")
    with col2:
        cor = "🟢" if impacto > 0 else "🔴"
        st.metric(f"{cor} Impacto", f"R$ {impacto/1e6:.2f}M")
    with col3:
        pct = (impacto / margem_original * 100) if margem_original != 0 else 0
        st.metric("Variação %", f"{pct:.2f}%")
    
    st.divider()
    
    st.markdown(f"<h3 style='color: {COLORS['danger']};'>🚨 Alerta de Fluxo de Caixa</h3>", unsafe_allow_html=True)
    
    st.plotly_chart(criar_grafico_fluxo_caixa(df), use_container_width=True)
    
    st.divider()
    
    st.markdown(f"<h3 style='color: {COLORS['accent_blue']};'>📋 Terminal Bloomberg</h3>", unsafe_allow_html=True)
    
    tabela = df[[
        'Nº Contrato', 'Descrição Parceiro', 'CidadeOD', 'Desc Tipo Contrato',
        'Qtd. Contratado', 'Preço Líquido em Reais', 'Status'
    ]].copy()
    
    tabela.columns = ['Contrato', 'Fornecedor', 'Cidade', 'Tipo', 'Volume (sc)', 'Preço (R$)', 'Status']
    tabela['Preço (R$)'] = tabela['Preço (R$)'].apply(lambda x: f"R$ {x:,.2f}")
    tabela['Volume (sc)'] = tabela['Volume (sc)'].apply(lambda x: f"{x:,.0f}")
    
    st.dataframe(tabela.sort_values('Contrato', ascending=False), use_container_width=True, height=400)

# ============================================================================
# ABA 4: ALERTAS
# ============================================================================

with tab4:
    st.markdown(f"<h2 style='color: {COLORS['neon_green']};'>⚠️ Alertas e Anomalias</h2>", unsafe_allow_html=True)
    
    alerts_list = []
    
    if kpis['fluxo_caixa_30_dias'] > kpis['total_valor'] * 0.3:
        alerts_list.append(('CRÍTICO', 'FLUXO_CAIXA', f"R$ {kpis['fluxo_caixa_30_dias']/1e6:.1f}M vencendo em 30 dias"))
    
    if kpis['contratos_ativos'] < 50:
        alerts_list.append(('AVISO', 'ORIGINACAO_BAIXA', f"Apenas {kpis['contratos_ativos']} contratos ativos"))
    
    margem_pct = (kpis['margem_bruta'] / kpis['total_valor'] * 100) if kpis['total_valor'] > 0 else 0
    if margem_pct < 5:
        alerts_list.append(('CRÍTICO', 'MARGEM_BAIXA', f"Margem bruta em apenas {margem_pct:.2f}%"))
    
    if len(alerts_list) == 0:
        st.markdown(f"""
            <div class="alert-box alert-info">
                <strong>✅ Nenhum alerta crítico</strong><br>
                Dashboard operando normalmente
            </div>
        """, unsafe_allow_html=True)
    else:
        for severidade, tipo, mensagem in alerts_list:
            if severidade == 'CRÍTICO':
                st.markdown(f"""
                    <div class="alert-box alert-critical">
                        <strong>🔴 CRÍTICO</strong> | {tipo}<br>{mensagem}
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                    <div class="alert-box alert-warning">
                        <strong>🟠 AVISO</strong> | {tipo}<br>{mensagem}
                    </div>
                """, unsafe_allow_html=True)

# ============================================================================
# RODAPÉ
# ============================================================================

st.divider()
st.markdown(f"""
    <div style="text-align: center; color: {COLORS['text_secondary']}; font-size: 12px; margin-top: 20px;">
        <p>Dashboard de Originação de Grãos | Desenvolvido para Marcus Pinheiro | v2.0 Cloud Integrated</p>
        <p>Executive Dark Mode | Inteligência Comercial | Análise em Tempo Real</p>
    </div>
""", unsafe_allow_html=True)
