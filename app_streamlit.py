
# ...existing code...

import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.set_page_config(page_title="Análise de Custos: Orçado vs Realizado", layout="wide")
st.title("Análise de Custos: Orçado vs Realizado")



# Caminhos fixos para os arquivos
ORCADO_DIR = "orcados"
REALIZADO_DIR = "realizado"

orcado_dir_path = os.path.join(os.getcwd(), ORCADO_DIR)
realizado_dir_path = os.path.join(os.getcwd(), REALIZADO_DIR)

orcado_files = [os.path.join(orcado_dir_path, f) for f in os.listdir(orcado_dir_path) if f.endswith('.csv')]
realizado_files = [os.path.join(realizado_dir_path, f) for f in os.listdir(realizado_dir_path) if f.endswith('.csv')]

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

df_orcado = None
df_realizado = None

if orcado_files and realizado_files:
    # Concatenar todos os orçados, adicionando coluna 'Familia' com o nome do arquivo
    dfs_orcado = []
    for f in orcado_files:
        df = load_data(f)
        if df is not None:
            if 'Código' not in df.columns:
                st.error(f"O arquivo '{os.path.basename(f)}' não possui a coluna 'Código'. Corrija o arquivo e tente novamente.")
                continue
            familia_nome = os.path.splitext(os.path.basename(f))[0]
            df['Familia'] = familia_nome
            # Adiciona coluna com os últimos 4 dígitos do código
            df['Código_4d'] = df['Código'].astype(str).str[-4:]
            dfs_orcado.append(df)
    if not dfs_orcado:
        st.error("Nenhum arquivo de orçado válido carregado.")
    else:
        df_orcado = pd.concat(dfs_orcado, ignore_index=True)

    # Usar o primeiro arquivo de realizado encontrado
    df_realizado = load_data(realizado_files[0])
    if df_realizado is not None:
        if 'Código' not in df_realizado.columns:
            st.error("O arquivo de realizado não possui a coluna 'Código'. Corrija o arquivo e tente novamente.")
        else:
            df_realizado['Código_4d'] = df_realizado['Código'].astype(str).str[-4:]


    if df_orcado is not None and df_realizado is not None:
        # Padronização automática dos parâmetros de análise
        col_familia = 'Familia'  # já criada
        col_codigo_orcado = 'Código_4d'
        col_valor_orcado = 'Total'
        col_qtd_orcado = 'Quantidade'
        col_unit_orcado = 'Unit'
        col_codigo_realizado = 'Código_4d'

        # Detectar automaticamente a coluna de quantidade e total no realizado
        # Se não encontrar pelo nome, tenta pelo índice ou tipo
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
            # ORÇADO: soma da coluna da etapa, se existir, apenas para códigos da família
            col_orcado = colunas_orcado.get(etapa)
            if col_orcado in df_orcado_group.columns:
                codigos_familia = set(df_exibir[col_codigo_orcado].astype(str))
                gasto_orcado = pd.to_numeric(df_orcado_group[df_orcado_group[col_codigo_orcado].astype(str).isin(codigos_familia)][col_orcado], errors='coerce').sum()
            elif etapa == 'Verniz':
                familias_melissa = df_orcado_group[df_orcado_group['Familia'].str.contains('melissa', case=False, na=False)]
                if not familias_melissa.empty and len(df_orcado_group.columns) > 9:
                    codigos_familia = set(df_exibir[col_codigo_orcado].astype(str))
                    gasto_orcado = pd.to_numeric(familias_melissa[familias_melissa[col_codigo_orcado].astype(str).isin(codigos_familia)].iloc[:,9], errors='coerce').sum()
                else:
                    total_orcado = 0
                    total_realizado = 0
                    for etapa_key, etapa_label in etapas.items():
                        if etapa_key in df_orcado_group.columns:
                            mask_codigos = df_orcado_group[col_codigo_orcado].astype(str).isin(codigos_familia)
                            valor_orcado = pd.to_numeric(df_orcado_group.loc[mask_codigos, etapa_key], errors='coerce').fillna(0).sum()
                            valor_realizado = pd.to_numeric(df_realizado_group.loc[mask_codigos, etapa_key], errors='coerce').fillna(0).sum()
                            # Ajuste especial para Clichê
                            if etapa_key == 'Clichê':
                                if 'jardim' in familia_selecionada.lower():
                                    valor_realizado = valor_orcado + 1277.70
                                elif 'melissa' in familia_selecionada.lower():
                                    valor_realizado = valor_orcado + 1126
                                # Considera economia/prejuízo do clichê
                                total_orcado += valor_orcado
                                total_realizado += valor_realizado
                            else:
                                total_orcado += valor_orcado
                                total_realizado += valor_realizado
                    # return total_orcado, total_realizado  # Removido pois não pode retornar fora de função

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
    total_realizado = 0
    if 'Código_4d' in df_exibir.columns:
        codigos_familia = set(df_exibir[col_codigo_orcado].astype(str))
        df_realizado_fam = df_realizado_group[df_realizado_group['Código_4d'].astype(str).isin(codigos_familia)]
        if 'Total' in df_realizado_fam.columns:
            total_realizado = pd.to_numeric(df_realizado_fam['Total'], errors='coerce').fillna(0).sum()
        # Somar o valor do card de Clichê ao total realizado
        valor_cliche_card = 0
        if 'Clichê' in df_orcado_group.columns:
            mask_codigos = df_orcado_group[col_codigo_orcado].astype(str).isin(codigos_familia)
            valor_cliche_card = pd.to_numeric(df_orcado_group.loc[mask_codigos, 'Clichê'], errors='coerce').fillna(0).sum()
            if 'jardim' in familia_selecionada.lower():
                valor_cliche_card += 1277.70
            if 'melissa' in familia_selecionada.lower():
                valor_cliche_card += 1126
        total_realizado += valor_cliche_card
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






    # Cards de custo por etapa para a família selecionada (exceto 'Todas')
    if familia_selecionada != 'Todas':
        # Só mostrar Verniz para família Melissa
        mostrar_verniz = 'melissa' in familia_selecionada.lower()
        etapas_cards = [
            ('Hot', 'Hot'),
            ('Laminação', 'Laminação'),
            ('Impressão', 'Impressão'),
            ('Papel', 'Papel'),
        ]
        if mostrar_verniz:
            etapas_cards.insert(3, ('Verniz', 'Verniz'))  # inserir Verniz antes de Papel
        # Adicionar Clichê ao final
        etapas_cards.append(('Clichê', 'Clichê'))
        colunas_orcado_cards = {
            'Hot': 'Hot',
            'Laminação': 'Laminação',
            'Impressão': 'Impressão',
            'Verniz': 'Verniz',
            'Papel': 'Papel',
            'Clichê': 'Clichê',
        }
        colunas_realizado_cards = {
            'Hot': 'Hot',
            'Laminação': 'Laminação',
            'Impressão': 'Impressão',
            'Verniz': 'Verniz',
            'Papel': 'Papel',
            'Clichê': 'Clichê',
        }
        codigos_familia = set(df_exibir[col_codigo_orcado].astype(str))
        # Grid de 3 colunas por linha
        n_cards = len(etapas_cards)
        n_cols = 3
        rows = (n_cards + n_cols - 1) // n_cols
        card_idx = 0
        for row in range(rows):
            cols = st.columns(n_cols)
            for col_num in range(n_cols):
                if card_idx >= n_cards:
                    break
                etapa_key, etapa_nome = etapas_cards[card_idx]
                col_orcado = colunas_orcado_cards.get(etapa_key)
                col_realizado = colunas_realizado_cards.get(etapa_key)
                # Orçado: soma apenas dos códigos da família
                if col_orcado and col_orcado in df_orcado_group.columns:
                    valor_orcado = pd.to_numeric(df_orcado_group[df_orcado_group[col_codigo_orcado].astype(str).isin(codigos_familia)][col_orcado], errors='coerce').sum()
                else:
                    valor_orcado = 0
                # Realizado: soma da coluna 'Total' do realizado para os códigos da família
                if etapa_key == 'Clichê' and 'Clichê' in df_orcado_group.columns:
                    # No card, o realizado do clichê será igual ao orçado, exceto para Jardim e Melissa: soma adicional
                    mask_codigos = df_orcado_group[col_codigo_orcado].astype(str).isin(codigos_familia)
                    valor_realizado = pd.to_numeric(df_orcado_group.loc[mask_codigos, 'Clichê'], errors='coerce').fillna(0).sum()
                    if 'jardim' in familia_selecionada.lower():
                        valor_realizado += 1277.70
                    if 'melissa' in familia_selecionada.lower():
                        valor_realizado += 1126
                elif col_realizado and col_realizado in df_realizado_group.columns and 'Quantidade' in df_realizado_group.columns:
                    mask_codigos = df_realizado_group[col_codigo_realizado].astype(str).isin(codigos_familia)
                    valor_realizado = (pd.to_numeric(df_realizado_group.loc[mask_codigos, col_realizado], errors='coerce').fillna(0) * pd.to_numeric(df_realizado_group.loc[mask_codigos, 'Quantidade'], errors='coerce').fillna(0)).sum()
                else:
                    valor_realizado = 0
                cor_card = 'green' if (valor_orcado - valor_realizado) > 0 else 'red' if (valor_orcado - valor_realizado) < 0 else 'gray'
                with cols[col_num]:
                    st.markdown(f"""
                    <div style='background: #222; border-radius: 10px; padding: 1.2rem 2.2rem; box-shadow: 0 2px 8px #0002; text-align:center; min-width: 220px; margin-bottom: 0.5rem;'>
                        <span style='font-size:1.1em; font-weight:bold;'>Custo de {etapa_nome}</span><br>
                        <span style='color:#1f77b4; font-weight:bold;'>Orçado: R$ {valor_orcado:,.2f}</span> &nbsp;|&nbsp; 
                        <span style='color:#ff7f0e; font-weight:bold;'>Gasto: R$ {valor_realizado:,.2f}</span><br>
                        <span style='font-size:1.05em;'>Economia/Prejuízo: <span style='color:{cor_card}; font-weight:bold;'>R$ {valor_orcado - valor_realizado:,.2f}</span></span>
                    </div>
                    """, unsafe_allow_html=True)
                    # Detalhamento por código
                    with st.expander(f"Ver detalhamento de {etapa_nome}"):
                        # Orçado por código (com categoria)
                        categoria_col = None
                        for cat_col in ['CATEGORIA', 'TIPO']:
                            if cat_col in df_orcado_group.columns:
                                categoria_col = cat_col
                                break
                        cols_orcado = [col_codigo_orcado, col_orcado] + ([categoria_col] if categoria_col else [])
                        cols_orcado = [c for c in cols_orcado if c is not None]
                        if col_orcado and col_orcado in df_orcado_group.columns:
                            df_orcado_cod = df_orcado_group[df_orcado_group[col_codigo_orcado].astype(str).isin(codigos_familia)][cols_orcado].copy()
                            df_orcado_cod = df_orcado_cod.rename(columns={col_orcado: 'Orçado'})
                        else:
                            df_orcado_cod = pd.DataFrame(columns=[col_codigo_orcado, 'Orçado'] + ([categoria_col] if categoria_col else []))
                        # Realizado por código
                        if etapa_key == 'Clichê':
                            # Clichê: realizado igual ao orçado, exceto regras especiais
                            df_realizado_cod = df_orcado_cod.copy()
                            df_realizado_cod['Realizado'] = df_realizado_cod['Orçado']
                            if 'jardim' in familia_selecionada.lower():
                                codigos_duplicar = {'7899866829077','7899866829091','7899866829107','7899866829114','7899866829121','7899866829176'}
                                mask_dup = df_realizado_cod[col_codigo_orcado].astype(str).isin(codigos_duplicar)
                                df_realizado_cod.loc[mask_dup, 'Realizado'] = df_realizado_cod.loc[mask_dup, 'Orçado'] * 2
                            if 'melissa' in familia_selecionada.lower():
                                codigo_duplicar = '7899866829404'
                                mask_dup = df_realizado_cod[col_codigo_orcado].astype(str) == codigo_duplicar
                                df_realizado_cod.loc[mask_dup, 'Realizado'] = df_realizado_cod.loc[mask_dup, 'Orçado'] * 2
                            # Corrigir o valor_realizado do card para Jardim (soma dos realizados já duplicados)
                            if 'jardim' in familia_selecionada.lower():
                                valor_realizado = df_realizado_cod['Realizado'].sum()
                        elif col_realizado and col_realizado in df_realizado_group.columns and 'Quantidade' in df_realizado_group.columns:
                            mask_codigos = df_realizado_group[col_codigo_realizado].astype(str).isin(codigos_familia)
                            df_realizado_cod = df_realizado_group.loc[mask_codigos, [col_codigo_realizado, col_realizado, 'Quantidade']].copy()
                            df_realizado_cod['Realizado'] = pd.to_numeric(df_realizado_cod[col_realizado], errors='coerce').fillna(0) * pd.to_numeric(df_realizado_cod['Quantidade'], errors='coerce').fillna(0)
                            df_realizado_cod = df_realizado_cod.rename(columns={col_codigo_realizado: col_codigo_orcado})
                            df_realizado_cod = df_realizado_cod[[col_codigo_orcado, 'Realizado']]
                        else:
                            df_realizado_cod = pd.DataFrame(columns=[col_codigo_orcado, 'Realizado'])
                        # Merge orçado e realizado
                        df_det = pd.merge(df_orcado_cod, df_realizado_cod, on=col_codigo_orcado, how='outer').fillna(0)
                        # Garante que as colunas existem
                        if 'Orçado' not in df_det.columns:
                            df_det['Orçado'] = 0
                        if 'Realizado' not in df_det.columns:
                            df_det['Realizado'] = 0
                        # Converter para float antes de subtrair
                        df_det['Orçado'] = pd.to_numeric(df_det['Orçado'], errors='coerce').fillna(0)
                        df_det['Realizado'] = pd.to_numeric(df_det['Realizado'], errors='coerce').fillna(0)
                        df_det['Economia/Prejuízo'] = df_det['Orçado'] - df_det['Realizado']
                        df_det = df_det.rename(columns={col_codigo_orcado: 'Código'})
                        # Remover coluna de categoria da tabela, mas exibir como tooltip ao passar o mouse sobre o código
                        df_det = df_det[['Código', 'Orçado', 'Realizado', 'Economia/Prejuízo']]
                        # Criar dicionário de código -> categoria
                        tooltip_dict = {}
                        if categoria_col and categoria_col in df_orcado_cod.columns:
                            for _, row in df_orcado_cod.iterrows():
                                tooltip_dict[str(row[col_codigo_orcado])] = str(row[categoria_col])
                        def highlight_economia(val):
                            color = 'green' if val > 0 else 'red' if val < 0 else 'gray'
                            return f'color: {color}; font-weight: bold;'
                        styled = df_det.style.format({'Orçado': 'R$ {:,.2f}', 'Realizado': 'R$ {:,.2f}', 'Economia/Prejuízo': 'R$ {:,.2f}'}).applymap(highlight_economia, subset=['Economia/Prejuízo'])
                        # Adiciona tooltip na coluna Código
                        st.dataframe(styled, use_container_width=True)
                card_idx += 1

    # Gráfico de economia/prejuízo por categoria dentro da família selecionada
    if familia_selecionada != 'Todas':
        categoria_col = None
        for cat_col in ['CATEGORIA', 'TIPO']:
            if cat_col in df_orcado_group.columns:
                categoria_col = cat_col
                break
        if categoria_col:
            codigos_familia = set(df_exibir[col_codigo_orcado].astype(str))
            df_cat = df_orcado_group[df_orcado_group[col_codigo_orcado].astype(str).isin(codigos_familia)][[col_codigo_orcado, categoria_col]].drop_duplicates()
            etapas_soma = ['Hot', 'Laminação', 'Impressão', 'Papel']
            if 'melissa' in familia_selecionada.lower() and 'Verniz' in df_orcado_group.columns:
                etapas_soma.append('Verniz')
            if 'Clichê' in df_orcado_group.columns:
                etapas_soma.append('Clichê')
            df_orcado_sum = df_orcado_group[df_orcado_group[col_codigo_orcado].astype(str).isin(codigos_familia)].copy()
            df_orcado_sum['Orçado'] = df_orcado_sum[etapas_soma].apply(pd.to_numeric, errors='coerce').fillna(0).sum(axis=1)
            df_realizado_sum = df_realizado_group[df_realizado_group[col_codigo_realizado].astype(str).isin(codigos_familia)].copy()
            df_realizado_sum['Realizado'] = pd.to_numeric(df_realizado_sum['Unit'], errors='coerce').fillna(0) * pd.to_numeric(df_realizado_sum['Quantidade'], errors='coerce').fillna(0)
            df_cat_det = pd.merge(df_cat, df_orcado_sum[[col_codigo_orcado, 'Orçado']], on=col_codigo_orcado, how='left')
            df_cat_det = pd.merge(df_cat_det, df_realizado_sum[[col_codigo_realizado, 'Realizado']], left_on=col_codigo_orcado, right_on=col_codigo_realizado, how='left')
            df_cat_det['Orçado'] = pd.to_numeric(df_cat_det['Orçado'], errors='coerce').fillna(0)
            df_cat_det['Realizado'] = pd.to_numeric(df_cat_det['Realizado'], errors='coerce').fillna(0)
            df_cat_det['Economia/Prejuízo'] = df_cat_det['Orçado'] - df_cat_det['Realizado']
            df_cat_group = df_cat_det.groupby(categoria_col)[['Orçado', 'Realizado', 'Economia/Prejuízo']].sum().reset_index()
            import plotly.graph_objects as go
            # Define cor: verde para economia, vermelho para prejuízo
            df_cat_group['Cor'] = df_cat_group['Economia/Prejuízo'].apply(lambda x: '#2ecc40' if x > 0 else '#ff4136' if x < 0 else '#aaaaaa')
            fig_cat = go.Figure(go.Bar(
                y=df_cat_group[categoria_col],
                x=df_cat_group['Economia/Prejuízo'],
                orientation='h',
                marker_color=df_cat_group['Cor'],
                text=[f"R$ {v:,.2f}" for v in df_cat_group['Economia/Prejuízo']],
                textposition='outside',
                hovertemplate=f"Categoria: %{{y}}<br>Economia/Prejuízo: R$ %{{x:,.2f}}<extra></extra>"
            ))
            fig_cat.update_layout(
                title='Economia/Prejuízo por Categoria',
                xaxis_title='Economia/Prejuízo (R$)',
                yaxis_title='Categoria',
                # Remover fundo branco para respeitar tema escuro
                # plot_bgcolor='#fff',
                # paper_bgcolor='#fff',
                height=380,
                margin=dict(l=60, r=30, t=60, b=40),
                showlegend=False
            )
            st.plotly_chart(fig_cat, use_container_width=True)

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

    # Gráficos de pizza: proporção do orçado e do realizado por código
    if familia_selecionada != 'Todas':
        st.markdown(f"#### Proporção do Orçado e Realizado por Código — {titulo_familia}")
        df_pie = df_exibir.copy()
        df_pie = df_pie.sort_values('Total Orçado', ascending=True)
        from plotly.colors import sample_colorscale
        n = len(df_pie)
        blues = sample_colorscale('Blues', [i/(n-1) if n>1 else 0.5 for i in range(n)])
        fig_pie_orcado = px.pie(
            df_pie,
            names=col_codigo_orcado,
            values='Total Orçado',
            title=f'Orçado por Código',
            color_discrete_sequence=blues
        )
        fig_pie_orcado.update_traces(textinfo='percent+label', textposition='inside', pull=[0.05]*len(df_pie))
        fig_pie_orcado.update_layout(height=400, width=800, margin=dict(l=20, r=20, t=60, b=20))
        # Gráfico do Realizado
        show_realizado = 'Total Realizado' in df_pie.columns and df_pie['Total Realizado'].sum() > 0
        if show_realizado:
            df_pie = df_pie.sort_values('Total Realizado', ascending=True)
            oranges = sample_colorscale('Oranges', [i/(n-1) if n>1 else 0.5 for i in range(n)])
            fig_pie_real = px.pie(
                df_pie,
                names=col_codigo_orcado,
                values='Total Realizado',
                title=f'Realizado por Código',
                color_discrete_sequence=oranges
            )
            fig_pie_real.update_traces(textinfo='percent+label', textposition='inside', pull=[0.05]*len(df_pie))
            fig_pie_real.update_layout(height=400, width=800, margin=dict(l=20, r=20, t=60, b=20))
        # Exibição: lado a lado para família específica, um embaixo do outro para 'Todas'
        if familia_selecionada == 'Todas':
            pass  # Não exibe gráficos de pizza para 'Todas'
        else:
            if show_realizado:
                cols_pie = st.columns(2)
                with cols_pie[0]:
                    st.plotly_chart(fig_pie_orcado, use_container_width=True)
                with cols_pie[1]:
                    st.plotly_chart(fig_pie_real, use_container_width=True)
            else:
                st.plotly_chart(fig_pie_orcado, use_container_width=True)


    if familia_selecionada != 'Todas':
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
