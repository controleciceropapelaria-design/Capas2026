
import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.set_page_config(page_title="Análise de Custos: Orçado vs Realizado", layout="wide")
st.title("Análise de Custos: Orçado vs Realizado")




# URLs dos arquivos CSV no GitHub
orcado_urls = [
    "https://raw.githubusercontent.com/controleciceropapelaria-design/Capas2026/refs/heads/main/orcados/capasbossanova.csv",
    "https://raw.githubusercontent.com/controleciceropapelaria-design/Capas2026/refs/heads/main/orcados/capasdoceflorada.csv",
    "https://raw.githubusercontent.com/controleciceropapelaria-design/Capas2026/refs/heads/main/orcados/capasfabula.csv",
    "https://raw.githubusercontent.com/controleciceropapelaria-design/Capas2026/refs/heads/main/orcados/capasjardim.csv",
    "https://raw.githubusercontent.com/controleciceropapelaria-design/Capas2026/refs/heads/main/orcados/capaskraft.csv",
    "https://raw.githubusercontent.com/controleciceropapelaria-design/Capas2026/refs/heads/main/orcados/capaslibelulas.csv",
    "https://raw.githubusercontent.com/controleciceropapelaria-design/Capas2026/refs/heads/main/orcados/capasmelissa.csv",
    "https://raw.githubusercontent.com/controleciceropapelaria-design/Capas2026/refs/heads/main/orcados/capasorigens.csv",
    "https://raw.githubusercontent.com/controleciceropapelaria-design/Capas2026/refs/heads/main/orcados/capaspraia.csv"
]
realizado_url = "https://raw.githubusercontent.com/controleciceropapelaria-design/Capas2026/refs/heads/main/realizado/custorelaizadoreal.csv"

def load_data(file):
    try:
        # Para pandas >=1.3, use on_bad_lines='skip'. Para versões antigas, use error_bad_lines=False
        import pandas as pd
        import inspect
        if 'on_bad_lines' in inspect.signature(pd.read_csv).parameters:
            df = pd.read_csv(file, on_bad_lines='skip')
        else:
            df = pd.read_csv(file, error_bad_lines=False)
        return df
    except Exception as e:
        st.error(f"Erro ao ler o arquivo {file}: {e}")
        return None


orcado_dfs = []
for url in orcado_urls:
    df = load_data(url)
    if df is not None:
        familia_nome = url.split('/')[-1].replace('.csv', '')
        df['Familia'] = familia_nome
        orcado_dfs.append(df)
if orcado_dfs:
    df_orcado = pd.concat(orcado_dfs, ignore_index=True)
else:
    df_orcado = None
    st.error("Nenhum arquivo de orçado válido carregado das URLs.")

df_realizado = load_data(realizado_url)
if df_realizado is not None:
    if 'Código' not in df_realizado.columns:
        st.error("O arquivo de realizado não possui a coluna 'Código'. Corrija o arquivo e tente novamente.")
        df_realizado = None
else:
    st.error("Arquivo de realizado não encontrado ou inválido na URL.")

# Debug: mostrar shapes dos dataframes
st.write('Shape df_orcado:', df_orcado.shape if df_orcado is not None else None)
st.write('Shape df_realizado:', df_realizado.shape if df_realizado is not None else None)

# Só executa o app se ambos os dataframes existem e têm dados
if df_orcado is not None and not df_orcado.empty and df_realizado is not None and not df_realizado.empty:
    # Padronização automática dos parâmetros de análise
    col_familia = 'Familia'  # já criada
    col_codigo_orcado = 'Código_4d'
    col_valor_orcado = 'Total'
    col_qtd_orcado = 'Quantidade'
    col_unit_orcado = 'Unit'
    col_codigo_realizado = 'Código_4d'
    # ...existing code...
        col_valor_realizado = None
        col_qtd_realizado = None
        # Procurar coluna de quantidade (segunda coluna numérica)
        for c in df_realizado.columns:
            if 'qtd' in c.lower() or 'quant' in c.lower():
                col_qtd_realizado = c
                break
        if col_qtd_realizado is None and len(df_realizado.columns) > 1:
            # Tenta pegar a segunda coluna
            col_qtd_realizado = df_realizado.columns[1]
        # Procurar coluna de total (última coluna numérica)
        for c in reversed(df_realizado.columns):
            if 'total' in c.lower():
                col_valor_realizado = c
                break
        if col_valor_realizado is None:
            # Tenta pegar a última coluna
            col_valor_realizado = df_realizado.columns[-1]

        # Renomear para padronizar
        df_realizado_group = df_realizado.copy()
        if col_valor_realizado != 'Total':
            df_realizado_group['Total'] = df_realizado_group[col_valor_realizado]
            col_valor_realizado = 'Total'
        if col_qtd_realizado != 'Quantidade':
            df_realizado_group['Quantidade'] = df_realizado_group[col_qtd_realizado]
            col_qtd_realizado = 'Quantidade'


        # Calcular custo unitário realizado ANTES do merge
        if col_valor_realizado in df_realizado_group.columns and col_qtd_realizado in df_realizado_group.columns:
            # Converter para numérico, valores inválidos viram 0
            df_realizado_group['__valor_tmp'] = pd.to_numeric(df_realizado_group[col_valor_realizado], errors='coerce').fillna(0)
            df_realizado_group['__qtd_tmp'] = pd.to_numeric(df_realizado_group[col_qtd_realizado], errors='coerce').fillna(0)
            df_realizado_group['Custo Unitário Realizado'] = df_realizado_group.apply(
                lambda x: x['__valor_tmp']/x['__qtd_tmp'] if x['__qtd_tmp'] else 0, axis=1)
            df_realizado_group.drop(['__valor_tmp', '__qtd_tmp'], axis=1, inplace=True)
        else:
            st.error("Não foi possível calcular o custo unitário realizado: coluna de total ou quantidade não encontrada no realizado.")
            df_realizado_group['Custo Unitário Realizado'] = 0

        # Garantir que a coluna existe antes de acessar
        if 'Custo Unitário Realizado' not in df_realizado_group.columns:
            st.error("A coluna 'Custo Unitário Realizado' não foi criada corretamente. Verifique o arquivo de realizado.")
            df_realizado_group['Custo Unitário Realizado'] = 0


        # Calcular custo unitário no orçado
        df_orcado_group = df_orcado.copy()
        if col_qtd_orcado and col_qtd_orcado != 'None':
            df_orcado_group['Qtd'] = pd.to_numeric(df_orcado_group[col_qtd_orcado], errors='coerce').fillna(0)
            df_orcado_group['ValorTotal'] = pd.to_numeric(df_orcado_group[col_valor_orcado], errors='coerce').fillna(0)
            df_orcado_group['Custo Unitário Orçado'] = df_orcado_group.apply(lambda x: x['ValorTotal']/x['Qtd'] if x['Qtd'] else 0, axis=1)
        else:
            df_orcado_group['Custo Unitário Orçado'] = pd.to_numeric(df_orcado_group[col_unit_orcado], errors='coerce').fillna(0)

        # Calcular custo unitário no realizado

        df_realizado_group = df_realizado.copy()
        if col_valor_realizado not in df_realizado_group.columns:
            # Tentar usar a coluna de índice 9 (coluna 10, zero-based)
            if len(df_realizado_group.columns) > 8:
                col_fallback = df_realizado_group.columns[8]
                df_realizado_group['Total'] = df_realizado_group[col_fallback]
                col_valor_realizado = 'Total'
            else:
                st.error(f"A coluna '{col_valor_realizado}' não existe no realizado e não foi possível encontrar a coluna 8. Verifique o cabeçalho do arquivo de realizado.")
        if col_valor_realizado in df_realizado_group.columns:
            if col_qtd_realizado and col_qtd_realizado != 'None':
                df_realizado_group['Qtd'] = pd.to_numeric(df_realizado_group[col_qtd_realizado], errors='coerce').fillna(0)
                df_realizado_group['ValorTotal'] = pd.to_numeric(df_realizado_group[col_valor_realizado], errors='coerce').fillna(0)
                df_realizado_group['Custo Unitário Realizado'] = df_realizado_group.apply(lambda x: x['ValorTotal']/x['Qtd'] if x['Qtd'] else 0, axis=1)
            else:
                df_realizado_group['Custo Unitário Realizado'] = pd.to_numeric(df_realizado_group[col_valor_realizado], errors='coerce').fillna(0)


        # Merge por código, só se as colunas existirem
        cols_realizado_merge = [col_codigo_realizado, 'Custo Unitário Realizado']
        cols_realizado_exist = [c for c in cols_realizado_merge if c in df_realizado_group.columns]
        if len(cols_realizado_exist) < 2:
            st.error(f"Colunas não encontradas no realizado para o merge: {set(cols_realizado_merge) - set(cols_realizado_exist)}. Verifique o arquivo de realizado.")
            # Criar DataFrame vazio para evitar erro
            df_merged = pd.merge(
                df_orcado_group[[col_codigo_orcado, col_familia, 'Custo Unitário Orçado']],
                pd.DataFrame(columns=cols_realizado_merge),
                left_on=col_codigo_orcado,
                right_on=col_codigo_realizado,
                how='outer',
                suffixes=('_orcado', '_realizado')
            )
            df_merged['Diferença Unitária'] = None
        else:
            df_merged = pd.merge(
                df_orcado_group[[col_codigo_orcado, col_familia, 'Custo Unitário Orçado']],
                df_realizado_group[cols_realizado_merge],
                left_on=col_codigo_orcado,
                right_on=col_codigo_realizado,
                how='outer',
                suffixes=('_orcado', '_realizado')
            )
            df_merged['Diferença Unitária'] = df_merged['Custo Unitário Realizado'] - df_merged['Custo Unitário Orçado']

        # Caixa de seleção para família

        # Mapeamento nomes técnicos para amigáveis
        familia_map = {
            'capasbossanova': 'Bossa nova',
            'capasdoceflorada': 'Doce Florada',
            'capasfabula': 'Fábula',
            'capasjardim': 'Jardim',
            'capaskraft': 'Kraft',
            'capaslibelulas': 'Libélulas',
            'capasmelissa': 'Melissa',
            'capasorigens': 'Origens',
            'capaspraia': 'Praia'
        }
        familias = df_merged[col_familia].dropna().unique().tolist()
        familias.sort()
        familias_amigaveis = [familia_map.get(f, f) for f in familias]
        familia_selecionada_amigavel = st.selectbox('Selecione a família para análise:', ['Todas'] + familias_amigaveis)
        # Descobrir o nome técnico selecionado
        if familia_selecionada_amigavel == 'Todas':
            familia_selecionada = 'Todas'
        else:
            familia_selecionada = familias[familias_amigaveis.index(familia_selecionada_amigavel)]

        if familia_selecionada == 'Todas':
            # Remover códigos sem família
            df_exibir = df_merged[df_merged[col_familia].notnull() & (df_merged[col_familia] != '')].copy()
            titulo_familia = 'Todas as Famílias'
        else:
            df_exibir = df_merged[df_merged[col_familia] == familia_selecionada]
            titulo_familia = f'Família: {familia_selecionada}'


        # Garantir que as colunas de totais existam antes de qualquer análise
        if 'Total Orçado' not in df_exibir.columns:
            orcado_agg = df_orcado_group.groupby(col_codigo_orcado)[col_valor_orcado].sum()
            df_exibir['Total Orçado'] = df_exibir[col_codigo_orcado].map(orcado_agg).fillna(0)
        if 'Total Realizado' not in df_exibir.columns:
            if col_valor_realizado in df_realizado_group.columns:
                realizado_agg = df_realizado_group.groupby(col_codigo_realizado)[col_valor_realizado].sum()
                df_exibir['Total Realizado'] = df_exibir[col_codigo_orcado].map(realizado_agg).fillna(0)
            else:
                st.warning(f"Coluna '{col_valor_realizado}' não encontrada no realizado. 'Total Realizado' será preenchido com 0.")
                df_exibir['Total Realizado'] = 0

        # --- Análise por etapa (Hot, Papel, Laminação, Impressão) ---
        etapas = ['Hot', 'Papel', 'Laminação', 'Impressão', 'Verniz']
        st.markdown('---')
        st.markdown('### Análise por Etapa de Produção')
        resumo_etapas = []
        # Mapear colunas de cada etapa para orçado e realizado
        colunas_orcado = {
            'Impressão': 'Impressão',
            'Papel': 'Papel',
            'Laminação': 'Laminação',
            'Hot': 'Hot',
            'Verniz': 'Verniz',
        }
        colunas_realizado = {
            'Papel': 'Papel',
            'Impressão': 'Impressão',
            'Laminação': 'Laminação',
            'Hot': 'Hot',
            'Verniz': 'Verniz',
        }
        for etapa in etapas:
            # ORÇADO: soma da coluna da etapa, se existir
            col_orcado = colunas_orcado.get(etapa)
            if col_orcado in df_orcado_group.columns:
                gasto_orcado = pd.to_numeric(df_orcado_group[col_orcado], errors='coerce').sum()
            elif etapa == 'Verniz':
                # Caso especial: só existe em capasmelissa, coluna 10
                familias_melissa = df_orcado_group[df_orcado_group['Familia'].str.contains('melissa', case=False, na=False)]
                if not familias_melissa.empty and len(df_orcado_group.columns) > 9:
                    gasto_orcado = pd.to_numeric(familias_melissa.iloc[:,9], errors='coerce').sum()
                else:
                    gasto_orcado = 0
            else:
                gasto_orcado = 0
            # REALIZADO: soma da coluna da etapa, se existir
            col_realizado = colunas_realizado.get(etapa)
            if col_realizado in df_realizado_group.columns:
                gasto_realizado = pd.to_numeric(df_realizado_group[col_realizado], errors='coerce').sum()
            else:
                gasto_realizado = 0
            economia = gasto_orcado - gasto_realizado
            resumo_etapas.append({
                'Etapa': etapa,
                'Orçado': gasto_orcado,
                'Realizado': gasto_realizado,
                'Economia': economia
            })
        # Cards de economia/gasto por etapa
        cols = st.columns(len(etapas))
        # Mapear colunas de cada etapa para orçado e realizado
        colunas_orcado = {
            'Impressão': 'Impressão',
            'Papel': 'Papel',
            'Laminação': 'Laminação',
            'Hot': 'Hot',
            'Verniz': 'Verniz', # pode não existir em todos
        }
        colunas_realizado = {
            'Papel': 'Papel',
            'Impressão': 'Impressão',
            'Laminação': 'Laminação',
            'Hot': 'Hot',
            'Verniz': 'Verniz',
        }
        # Ajustar para os índices informados pelo usuário
        # Realizado: Papel(2), Impressão(3), Laminação(4), Hot(5), Verniz(6)
        # Orcado: Impressão(5), Papel(6), Laminação(7), Hot(8), Verniz(10 em capasmelissa)
        # Tentar encontrar as colunas pelo nome, se não, pelo índice
        for etapa in etapas:
            # ORÇADO
            col_orcado = colunas_orcado.get(etapa)
            if col_orcado not in df_orcado_group.columns:
                # Tentar pelo índice
                idx = None
                if etapa == 'Impressão': idx = 4
                elif etapa == 'Papel': idx = 5
                elif etapa == 'Laminação': idx = 6
                elif etapa == 'Hot': idx = 7
                elif etapa == 'Verniz' and 'capasmelissa' in df_orcado_group['Familia'].unique(): idx = 9
                if idx is not None and idx < len(df_orcado_group.columns):
                    col_orcado = df_orcado_group.columns[idx]
            # REALIZADO
            col_realizado = colunas_realizado.get(etapa)
            if col_realizado not in df_realizado_group.columns:
                idx = None
                if etapa == 'Papel': idx = 2
                elif etapa == 'Impressão': idx = 3
                elif etapa == 'Laminação': idx = 4
                elif etapa == 'Hot': idx = 5
                elif etapa == 'Verniz': idx = 6
                if idx is not None and idx < len(df_realizado_group.columns):
                    col_realizado = df_realizado_group.columns[idx]
            # Calcular valores (só soma se a coluna existir e for numérica)
            if col_orcado in df_orcado_group.columns:
                try:
                    gasto_orcado = pd.to_numeric(df_orcado_group[col_orcado], errors='coerce').sum()
                except Exception:
                    gasto_orcado = 0
            else:
                gasto_orcado = 0
            if col_realizado in df_realizado_group.columns:
                try:
                    gasto_realizado = pd.to_numeric(df_realizado_group[col_realizado], errors='coerce').sum()
                except Exception:
                    gasto_realizado = 0
            else:
                gasto_realizado = 0
            economia = gasto_orcado - gasto_realizado

            resumo_etapas.append({
                'Etapa': etapa,
                'Orçado': gasto_orcado,
                'Realizado': gasto_realizado,
                'Economia': economia
            })

    # Gráfico comparativo principal
    st.markdown(f"### Comparativo de Custos Unitários — {titulo_familia}")
    st.write("Gráfico comparando o custo unitário orçado e realizado para cada código.")

    # Filtrar apenas códigos com informação (custo orçado ou realizado > 0)
    df_grafico = df_exibir[(df_exibir['Custo Unitário Orçado'] > 0) | (df_exibir['Custo Unitário Realizado'] > 0)].copy()
    codigos_ordenados = df_grafico[col_codigo_orcado].astype(str).unique().tolist()
    # Garantir que as colunas do gráfico são numéricas
    for col in ['Custo Unitário Orçado', 'Custo Unitário Realizado']:
        if col in df_grafico.columns:
            df_grafico[col] = pd.to_numeric(df_grafico[col], errors='coerce').fillna(0)

    fig = px.bar(
        df_grafico,
        x=col_codigo_orcado,
        y=['Custo Unitário Orçado', 'Custo Unitário Realizado'],
        barmode='group',
        title=f'Custo Unitário Orçado x Realizado — {titulo_familia}',
        labels={col_codigo_orcado: 'Código', 'value': 'Custo Unitário (R$)', 'variable': 'Tipo'},
        color_discrete_map={
            'Custo Unitário Orçado': '#1f77b4',
            'Custo Unitário Realizado': '#ff7f0e'
        }
    )
    fig.update_layout(
        legend_title_text='Legenda',
        xaxis_title='Código',
        yaxis_title='Custo Unitário (R$)',
        xaxis=dict(type='category', categoryorder='array', categoryarray=codigos_ordenados)
    )
    # Linha de tendência removida conforme solicitado
    st.plotly_chart(fig, use_container_width=True)

    media_dif = df_exibir['Diferença Unitária'].mean()
    st.metric("Diferença Unitária Média", f"{media_dif:,.2f}", help="Média da diferença entre o custo unitário realizado e o orçado.")

    # Comparativo de custo total orçado vs realizado

    total_orcado = df_exibir['Total Orçado'].sum() if 'Total Orçado' in df_exibir.columns else 0
    # Calcular total gasto: soma do custo unitário realizado * quantidade do orçado para cada código
    if 'Custo Unitário Realizado' in df_exibir.columns and 'Quantidade' in df_orcado_group.columns:
        qtd_map = df_orcado_group.groupby(col_codigo_orcado)['Quantidade'].sum()
        df_exibir['Qtd_Orcado'] = df_exibir[col_codigo_orcado].map(qtd_map).fillna(0)
        total_realizado = (df_exibir['Custo Unitário Realizado'] * df_exibir['Qtd_Orcado']).sum()
    else:
        total_realizado = 0
    diferenca = total_orcado - total_realizado
    cor = 'green' if diferenca > 0 else 'red' if diferenca < 0 else 'gray'


    st.markdown(f"""
    <div style='display: flex; justify-content: center; margin: 2rem 0;'>
        <div style='background: #222; border-radius: 10px; padding: 1.5rem 3rem; box-shadow: 0 2px 8px #0002; text-align:center;'>
            <span style='font-size:1.2em; font-weight:bold;'>Comparativo de Custo Total</span><br>
            <span style='color:#1f77b4; font-weight:bold;'>Orçado: R$ {total_orcado:,.2f}</span> &nbsp;|&nbsp; 
            <span style='color:#ff7f0e; font-weight:bold;'>Gasto: R$ {total_realizado:,.2f}</span><br>
            <span style='font-size:1.1em;'>Economia/Prejuízo: <span style='color:{cor}; font-weight:bold;'>R$ {diferenca:,.2f}</span></span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Gráfico de colunas de família com linha de tendência
    if familia_selecionada == 'Todas':
        df_familia = df_exibir.groupby(col_familia).agg({
            'Total Orçado': 'sum',
            'Total Realizado': 'sum'
        }).reset_index()
        # Substituir nomes técnicos por nomes amigáveis
        familia_map = {
            'capasbossanova': 'Bossa nova',
            'capasdoceflorada': 'Doce Florada',
            'capasfabula': 'Fábula',
            'capasjardim': 'Jardim',
            'capaskraft': 'Kraft',
            'capaslibelulas': 'Libélulas',
            'capasmelissa': 'Melissa',
            'capasorigens': 'Origens',
            'capaspraia': 'Praia'
        }
        df_familia[col_familia] = df_familia[col_familia].replace(familia_map)
        df_familia = df_familia.sort_values('Total Orçado', ascending=False)
        import plotly.graph_objects as go
        fig_fam = go.Figure()
        fig_fam.add_trace(go.Bar(
            x=df_familia[col_familia],
            y=df_familia['Total Orçado'],
            name='Total Orçado',
            marker_color='#1f77b4',
        ))
        fig_fam.add_trace(go.Bar(
            x=df_familia[col_familia],
            y=df_familia['Total Realizado'],
            name='Total Realizado',
            marker_color='#ff7f0e',
        ))
        # Linha de tendência removida conforme solicitado
        fig_fam.update_layout(
            barmode='group',
            title='Custos Totais por Família com Tendência',
            xaxis_title='Família',
            yaxis_title='Valor (R$)',
            legend_title_text='Legenda',
            height=420
        )
        st.plotly_chart(fig_fam, use_container_width=True)





    # Comparativo de Quantidade por Família: mostrar apenas quando uma família específica for selecionada
    if familia_selecionada != 'Todas':
        qtd_orcada_fam = df_exibir['Qtd_Orcado'].sum() if 'Qtd_Orcado' in df_exibir.columns else 0
        codigos_fam = df_exibir[col_codigo_orcado].unique().tolist()
        qtd_realizada_fam = df_realizado_group[df_realizado_group[col_codigo_realizado].isin(codigos_fam)]['Quantidade'].sum() if 'Quantidade' in df_realizado_group.columns else 0
        dif_qtd_fam = qtd_orcada_fam - qtd_realizada_fam
        cor_qtd_fam = 'green' if dif_qtd_fam > 0 else 'red' if dif_qtd_fam < 0 else 'gray'
        st.markdown(f"""
        <div style='display: flex; justify-content: center; margin: 0.5rem 0;'>
            <div style='background: #333; border-radius: 8px; padding: 1rem 2rem; box-shadow: 0 1px 4px #0002; text-align:center;'>
                <span style='font-size:1em; font-weight:bold;'>Comparativo de Quantidade</span><br>
                <span style='color:#1f77b4; font-weight:bold;'>Orçada: {qtd_orcada_fam:,.0f}</span> &nbsp;|&nbsp; 
                <span style='color:#ff7f0e; font-weight:bold;'>Realizada: {qtd_realizada_fam:,.0f}</span><br>
                <span style='font-size:1em;'>Diferença: <span style='color:{cor_qtd_fam}; font-weight:bold;'>{dif_qtd_fam:,.0f}</span></span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(f"#### Estatísticas Descritivas — {titulo_familia}")
    desc = df_exibir[['Custo Unitário Orçado', 'Custo Unitário Realizado', 'Diferença Unitária']].describe().T
    desc = desc.rename(columns={
        'mean': 'Média',
        'std': 'Desvio Padrão',
        'min': 'Mínimo',
        '25%': '1º Quartil',
        '50%': 'Mediana',
        '75%': '3º Quartil',
        'max': 'Máximo',
        'count': 'Qtd. Códigos'
    })
    st.dataframe(desc[['Qtd. Códigos', 'Média', 'Desvio Padrão', 'Mínimo', '1º Quartil', 'Mediana', '3º Quartil', 'Máximo']])

    # Gráfico de pizza: proporção do total orçado por código
    st.markdown(f"#### Proporção do Orçado por Código — {titulo_familia}")
    fig_pie = px.pie(
        df_exibir,
        names=col_codigo_orcado,
        values='Total Orçado',
        title=f'Proporção do Orçado por Código — {titulo_familia}',
        color_discrete_sequence=px.colors.sequential.Blues
    )
    fig_pie.update_traces(textinfo='percent+label', pull=[0.05]*len(df_exibir))
    st.plotly_chart(fig_pie, use_container_width=True)


    st.markdown(f"#### Dispersão Orçado x Realizado — {titulo_familia}")
    fig_scatter = px.scatter(
        df_exibir,
        x='Custo Unitário Orçado',
        y='Custo Unitário Realizado',
        hover_data=[col_codigo_orcado],
        title=f'Dispersão Orçado x Realizado — {titulo_familia}',
        labels={'Custo Unitário Orçado': 'Orçado (R$)', 'Custo Unitário Realizado': 'Realizado (R$)'}
    )
    fig_scatter.update_traces(marker=dict(size=10, color='#1f77b4', line=dict(width=1, color='DarkSlateGrey')))


    # Gráfico de linha de tendência dos custos unitários por código (usando mesma base filtrada do gráfico de colunas)
    st.markdown(f"#### Tendência dos Custos Unitários — {titulo_familia}")
    # Forçar eixo x categórico e ordenado para evitar buracos
    codigos_ordenados = df_grafico[col_codigo_orcado].astype(str).unique().tolist()
    fig_line = px.line(
        df_grafico,
        x=col_codigo_orcado,
        y=['Custo Unitário Orçado', 'Custo Unitário Realizado'],
        markers=True,
        title=f'Tendência dos Custos Unitários por Código — {titulo_familia}',
        labels={col_codigo_orcado: 'Código', 'value': 'Custo Unitário (R$)', 'variable': 'Tipo'}
    )
    fig_line.update_layout(
        height=320,
        xaxis=dict(type='category', categoryorder='array', categoryarray=codigos_ordenados)
    )
    st.plotly_chart(fig_line, use_container_width=True, key="fig_line")
