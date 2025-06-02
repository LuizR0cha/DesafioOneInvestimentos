import sqlite3
import pandas as pd
import streamlit as st

def init_db():
    # inicialização da base em memório para não precisar tratar o acesso ao banco de dados
    conn = sqlite3.connect(':memory:') 
    cursor = conn.cursor()

    # Criando as tabelas conforme esquema e inserindo os valores presentes no desafio
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS clientes (
        `ID Cliente` TEXT PRIMARY KEY,
        Nome TEXT NOT NULL,
        `Perfil de Investimento` TEXT NOT NULL
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS investimentos (
        `ID Cliente` TEXT,
        `Cód. Ativo` TEXT,
        Quantidade INTEGER,
        `Preço Médio` REAL,
        FOREIGN KEY (`ID Cliente`) REFERENCES clientes(`ID Cliente`)
    )
    ''')

    cursor.execute('''
    CREATE TABLE `cotações` (
        `Cód. Ativo` TEXT PRIMARY KEY,
        `Cotação Atual` REAL
    )
    ''')

    cursor.execute('''
    INSERT INTO clientes (`ID Cliente`, Nome, `Perfil de Investimento`)
    VALUES ('C001', 'João da Silva', 'Conservador'),
           ('C002', 'Maria Oliveira', 'Moderado'),
           ('C003', 'Carlos Pereira', 'Arrojado')
    ''')

    cursor.execute('''
    INSERT INTO investimentos (`ID Cliente`, `Cód. Ativo`, Quantidade, `Preço Médio`)
    VALUES ('C001', 'PETR4', 500, 28.50),
           ('C001', 'BBAS3', 200, 35.00),
           ('C002', 'VALE3', 300, 72.00),
           ('C003', 'ITUB4', 1000, 25.00),
           ('C003', 'BBDC4', 800, 23)
    ''')
    
    cursor.execute('''
    INSERT INTO `cotações` (`Cód. Ativo`, `Cotação Atual`)
    VALUES ('PETR4', 30.00),
           ('BBAS3', 33.00),
           ('VALE3', 75.00),
           ('ITUB4', 27.00),
           ('BBDC4', 26.00)              
    ''')

    conn.commit()
    return conn

# Fazendo a consulta em SQL no Banco de Dados
def get_portfolio_data(conn):
    cursor = conn.cursor()
    cursor.execute('''
    SELECT 
        c.Nome as 'Nome',
        c.`Perfil de Investimento`,
        i.Quantidade,
        i.`Preço Médio`,
        co.`Cotação Atual` - i.`Preço Médio` as `Valorização por ativo`,
        i.Quantidade * i.`Preço Médio` as 'Valor Total Investido por ativo',           
        i.`Cód. Ativo`,
        co.`Cotação Atual` as 'Valor Atual por ativo'
    FROM clientes c
    LEFT JOIN investimentos i ON c.`ID Cliente` = i.`ID Cliente`
    LEFT JOIN `cotações` co ON i.`Cód. Ativo` = co.`Cód. Ativo`
    ''')
    
    colunas = [desc[0] for desc in cursor.description]
    dados = cursor.fetchall()
    df = pd.DataFrame(dados, columns=colunas).convert_dtypes()
    
    return df

# Fazendo a sumarização -> Total por clientes, carteira atual e a rentabilidade percentual
def calculate_summary(df):
    df["Valor atual da carteira"] = df["Quantidade"] * df["Valor Atual por ativo"]
    
    df_total_por_clientes = df.groupby("Nome").agg({
        "Valor Total Investido por ativo": "sum"
    }).reset_index()

    df_carteira_atual_clientes = df.groupby("Nome").agg({
        "Valor atual da carteira": "sum"
    }).reset_index()

    df_merged = df_carteira_atual_clientes.merge(
        df_total_por_clientes[["Nome", "Valor Total Investido por ativo"]],
        on="Nome",  
        how="left"
    )

    df_merged["Rentabilidade (%)"] = (
        (df_merged["Valor atual da carteira"] - df_merged["Valor Total Investido por ativo"])
        / df_merged["Valor Total Investido por ativo"]
    ) * 100

    df_merged["Rentabilidade (%)"] = df_merged["Rentabilidade (%)"].round(2)
    
    return df_merged[["Nome", "Valor atual da carteira", "Valor Total Investido por ativo", "Rentabilidade (%)"]]

# Defindo a função principal, montando a página via streamlit e chamado as funções
def main():

    st.set_page_config(layout="wide")

    st.title("Desafio 4")
    st.markdown("Carteiras de clientes automatizadas")
    

    conn = init_db()
    df = get_portfolio_data(conn)
    
    # Mostrando a table de contações, editável
    st.subheader("Tabela de cotações:")
    edited_df = st.data_editor(
        df[['Cód. Ativo', 'Valor Atual por ativo']],
        key="asset_editor",
        num_rows="dynamic",
        column_config={
            "Valor Atual por ativo": st.column_config.NumberColumn(
                "Cotação Atual (Editável)",
                format="%.2f"
            )
        }
    )
    
    # Atualizando o Banco de Dados com os valores editáveis
    cursor = conn.cursor()
    for index, row in edited_df.iterrows():
        cursor.execute(
            "UPDATE `cotações` SET `Cotação Atual` = ? WHERE `Cód. Ativo` = ?",
            (row['Valor Atual por ativo'], row['Cód. Ativo'])
        )
    conn.commit()
    
    # Pegando as atulizações e fazendo a sumarização
    updated_df = get_portfolio_data(conn)
    summary_df = calculate_summary(updated_df)
    
    # Fazendo a tabela para cada cliente
    st.subheader("Tabela informativa para cada cliente ativo")
    clients = updated_df['Nome'].unique()
    for client in clients:
        st.markdown(f"### Carteira do(a) {client}")
        client_df = updated_df[updated_df['Nome'] == client].copy()
        
        
        # Mostrando a tabela
        st.dataframe(
            client_df,
            column_config={
                "Valor Atual por ativo": st.column_config.NumberColumn(format="R$ %.2f"),
                "Valor Total Investido por ativo": st.column_config.NumberColumn(format="R$ %.2f"),
                "Valor atual da carteira": st.column_config.NumberColumn(format="R$ %.2f"),
                "Valorização por ativo": st.column_config.NumberColumn(format="R$ %.2f"),
                "Preço Médio": st.column_config.NumberColumn(format="R$ %.2f"),
                "Quantidade": st.column_config.NumberColumn(format="%.0f")
            },
            hide_index=True,
            use_container_width=True
        )
        st.divider()
        
    
    # Mostrando a sumarização
    st.subheader("Rentabilidade percentual por cliente")
    st.dataframe(
        summary_df,
        column_config={
            "Valor atual da carteira": st.column_config.NumberColumn(format="R$ %.2f"),
            "Valor Total Investido por ativo": st.column_config.NumberColumn(format="R$ %.2f"),
            "Rentabilidade (%)": st.column_config.NumberColumn(format="%.2f%%")
        },
        hide_index=True,
        use_container_width=True
    )
#Chamando o programa   
if __name__ == "__main__":
    main()