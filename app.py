import streamlit as st
import pandas as pd

# ==========================================
# 1. Configurações da Página
# ==========================================
st.set_page_config(
    page_title="Daigaku Dojo - Portal do Aluno",
    page_icon="🥋",
    layout="wide"
)

SENSEI_EMAIL = "dojodaigakuufu@gmail.com"
SENSEI_SENHA = "admin"

# Cole os links CSV das abas correspondentes aqui
URL_FREQUENCIA = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQ6gHkJJz3jWTzh_uYGJe38a8tCUYJBDGF0riZ4zVs28liCx1l13u1Yd5zwFh-M6lw5dbX1Xd_RUqJk/pub?gid=2126799096&single=true&output=csv"
URL_GRADUACAO = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQ6gHkJJz3jWTzh_uYGJe38a8tCUYJBDGF0riZ4zVs28liCx1l13u1Yd5zwFh-M6lw5dbX1Xd_RUqJk/pub?gid=659980360&single=true&output=csv" # Deixe vazio "" se ainda não tiver publicado esta aba

# ==========================================
# 2. Processamento de Dados (Pandas)
# ==========================================
@st.cache_data(ttl=60)
def carregar_dados():
    try:
        # Carrega a aba de Frequência
        df_freq = pd.read_csv(URL_FREQUENCIA)
        df_freq.columns = df_freq.columns.str.strip() # Limpa espaços ocultos nos nomes das colunas
        
        # Filtra para remover linhas vazias no final da planilha
        df_freq = df_freq.dropna(subset=['Nome do Aluno', 'PIN'], how='all')
        
        # Limpa e converte a Frequência de "84,2%" para 84.2 numérico
        if 'Frequência %' in df_freq.columns:
            df_freq['Frequência Num'] = (
                df_freq['Frequência %']
                .astype(str)
                .str.replace('%', '')
                .str.replace(',', '.')
                .apply(lambda x: float(x) if x.replace('.', '', 1).isdigit() else 0.0)
            )

        # Se houver uma aba de graduação fornecida, faz o merge (cruzamento) dos dados
        if URL_GRADUACAO.startswith("http"):
            df_grad = pd.read_csv(URL_GRADUACAO)
            df_grad.columns = df_grad.columns.str.strip()
            # Usa o Nome do Aluno como chave para unir a faixa com a frequência
            df_final = pd.merge(df_freq, df_grad, on='Nome do Aluno', how='left')
        else:
            df_final = df_freq
            df_final['Faixa Atual'] = "Dados não conectados"
            df_final['Próxima Faixa'] = "Dados não conectados"
            df_final['Status do Exame'] = "Aguardando avaliação"
            
        return df_final
        
    except Exception as e:
        st.error(f"Erro ao carregar a planilha. Verifique se os links estão como CSV. Detalhe: {e}")
        return pd.DataFrame()

df_alunos = carregar_dados()

# ==========================================
# 3. Controle de Sessão
# ==========================================
if "logado" not in st.session_state:
    st.session_state.update({"logado": False, "perfil": None, "nome_usuario": None, "pin_usuario": None})

def fazer_login(credencial, senha=None):
    if df_alunos.empty:
        return False
        
    # Login Sensei (Usa e-mail e senha)
    if "@" in credencial:
        if credencial == SENSEI_EMAIL and senha == SENSEI_SENHA:
            st.session_state.update({"logado": True, "perfil": "Sensei", "nome_usuario": "Sensei", "pin_usuario": "admin"})
            return True
    
    # Login Aluno (Usa apenas o PIN)
    else:
        # Garante que o PIN seja tratado como texto para evitar erros de formatação
        df_alunos['PIN'] = df_alunos['PIN'].astype(str).str.strip()
        credencial_limpa = str(credencial).strip()
        
        usuario = df_alunos[df_alunos['PIN'] == credencial_limpa]
        if not usuario.empty:
            st.session_state.update({
                "logado": True, 
                "perfil": "Aluno", 
                "nome_usuario": usuario.iloc[0]['Nome do Aluno'],
                "pin_usuario": credencial_limpa
            })
            return True
            
    return False

# ==========================================
# 4. Interface da Barra Lateral
# ==========================================
st.sidebar.title("Login - Daigaku Dojo")

if not st.session_state["logado"]:
    with st.sidebar.form("form_login"):
        st.write("🥋 **Alunos:** Digite seu PIN abaixo.\n\n🧑‍🏫 **Sensei:** Digite seu E-mail e Senha.")
        input_credencial = st.text_input("PIN ou E-mail")
        input_senha = st.text_input("Senha (Apenas para Sensei)", type="password")
        
        if st.form_submit_button("Entrar"):
            if fazer_login(input_credencial, input_senha):
                st.rerun()
            else:
                st.sidebar.error("Credenciais inválidas. Verifique seu PIN.")
else:
    st.sidebar.success(f"Bem-vindo(a),\n**{st.session_state['nome_usuario']}**")
    if st.sidebar.button("Sair do Portal"):
        st.session_state.update({"logado": False, "perfil": None, "nome_usuario": None, "pin_usuario": None})
        st.rerun()

# ==========================================
# 5. Interface Principal
# ==========================================
st.title("🥋 Daigaku Dojo - Portal do Aluno")
st.divider()

if not st.session_state["logado"]:
    st.info("Insira seu PIN na barra lateral para acessar o seu progresso.")
    
elif not df_alunos.empty:
    
    # --- VISÃO DO SENSEI ---
    if st.session_state["perfil"] == "Sensei":
        st.subheader("Painel de Controle Geral")
        
        col1, col2 = st.columns(2)
        col1.metric("Total de Alunos Matriculados", len(df_alunos))
        media_freq = df_alunos['Frequência Num'].mean() if 'Frequência Num' in df_alunos.columns else 0
        col2.metric("Frequência Média do Dojo", f"{media_freq:.1f}%")
        
        st.markdown("### Histórico e Situação dos Alunos")
        # Exibe dados focando nas colunas mais importantes, evitando cores de baixo contraste
        colunas_exibicao = ['Nome do Aluno', 'PIN', 'Frequência %', 'Faixa Atual', 'Status do Exame']
        colunas_disponiveis = [col for col in colunas_exibicao if col in df_alunos.columns]
        
        st.dataframe(df_alunos[colunas_disponiveis], use_container_width=True)

    # --- VISÃO DO ALUNO ---
    elif st.session_state["perfil"] == "Aluno":
        st.subheader(f"Olá, {st.session_state['nome_usuario']}! Oss!")
        
        aluno_info = df_alunos[df_alunos['PIN'] == st.session_state['pin_usuario']].iloc[0]
        
        st.markdown("### Seu Progresso")
        c1, c2, c3, c4 = st.columns(4)
        
        with c1:
            faixa = aluno_info.get('Faixa Atual', 'N/A')
            st.metric("Faixa Atual", str(faixa))
        with c2:
            prox_faixa = aluno_info.get('Próxima Faixa', 'N/A')
            st.metric("Próxima Faixa", str(prox_faixa))
        with c3:
            freq = aluno_info.get('Frequência Num', 0)
            cor_delta = "normal" if freq >= 75 else "inverse"
            st.metric("Frequência Geral", f"{freq:.1f}%", "Atenção" if freq < 75 else "Boa", delta_color=cor_delta)
        with c4:
            status = aluno_info.get('Status do Exame', 'N/A')
            st.metric("Status do Exame", str(status))
            
        st.divider()
        
        # Extrai as datas de presença (todas as colunas após 'Frequência %')
        st.markdown("### Suas Últimas Aulas")
        idx_freq = df_alunos.columns.get_loc('Frequência %')
        colunas_datas = df_alunos.columns[idx_freq+1:-1] # Ignora colunas calculadas no final
        
        if len(colunas_datas) > 0:
            datas_recentes = colunas_datas[-5:] # Pega as 5 últimas aulas
            cols_presenca = st.columns(len(datas_recentes))
            
            for i, data in enumerate(datas_recentes):
                status_aula = aluno_info.get(data, "-")
                with cols_presenca[i]:
                    # Exibe P (Presença) ou F (Falta)
                    if str(status_aula).strip().upper() == 'P':
                        st.success(f"**{data}**\n\n✅ Presente")
                    elif str(status_aula).strip().upper() == 'F':
                        st.error(f"**{data}**\n\n❌ Falta")
                    else:
                        st.info(f"**{data}**\n\n{status_aula}")