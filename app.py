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

# COLE OS SEUS LINKS DO GOOGLE SHEETS AQUI NOVAMENTE
URL_FREQUENCIA = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQ6gHkJJz3jWTzh_uYGJe38a8tCUYJBDGF0riZ4zVs28liCx1l13u1Yd5zwFh-M6lw5dbX1Xd_RUqJk/pub?gid=2126799096&single=true&output=csv"
URL_GRADUACAO = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQ6gHkJJz3jWTzh_uYGJe38a8tCUYJBDGF0riZ4zVs28liCx1l13u1Yd5zwFh-M6lw5dbX1Xd_RUqJk/pub?gid=659980360&single=true&output=csv"

# ==========================================
# 2. Processamento de Dados (Pandas)
# ==========================================
@st.cache_data(ttl=60)
def carregar_dados():
    try:
        df_freq = pd.read_csv(URL_FREQUENCIA)
        df_freq.columns = df_freq.columns.str.strip()
        df_freq = df_freq.dropna(subset=['Nome do Aluno', 'PIN'], how='all')
        
        if 'Frequência %' in df_freq.columns:
            df_freq['Frequência Num'] = (
                df_freq['Frequência %']
                .astype(str)
                .str.replace('%', '')
                .str.replace(',', '.')
                .apply(lambda x: float(x) if x.replace('.', '', 1).isdigit() else 0.0)
            )

        df_grad = pd.DataFrame()
        if URL_GRADUACAO.startswith("http"):
            df_grad = pd.read_csv(URL_GRADUACAO)
            df_grad.columns = df_grad.columns.str.strip()
            df_final = pd.merge(df_freq, df_grad, on='Nome do Aluno', how='left')
        else:
            df_final = df_freq
            df_final['Faixa Atual'] = "Não conectada"
            df_final['Próxima Faixa'] = "Não conectada"
            df_final['Status do Exame'] = "Aguardando"
            
        return df_final, df_freq, df_grad
        
    except Exception as e:
        st.error(f"Erro ao carregar a planilha. Detalhe: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

df_alunos, df_frequencia_bruta, df_graduacao_bruta = carregar_dados()

# ==========================================
# 3. Controle de Sessão
# ==========================================
if "logado" not in st.session_state:
    st.session_state.update({"logado": False, "perfil": None, "nome_usuario": None, "pin_usuario": None})

def fazer_login(credencial, senha=None):
    if df_alunos.empty:
        return False
        
    if "@" in credencial:
        if credencial == SENSEI_EMAIL and senha == SENSEI_SENHA:
            st.session_state.update({"logado": True, "perfil": "Sensei", "nome_usuario": "Sensei", "pin_usuario": "admin"})
            return True
    else:
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
st.sidebar.title("Entrar - Daigaku Dojo")

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
    st.sidebar.success(f"Bem-vindo(a), {st.session_state['nome_usuario']}")
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
        
        # --- CÁLCULO DE FREQUÊNCIA MÉDIA REAL (ALUNOS ATIVOS) ---
        media_freq_real = 0.0
        qtd_ativos = 0
        
        if 'Frequência %' in df_frequencia_bruta.columns:
            idx_freq = df_frequencia_bruta.columns.get_loc('Frequência %')
            colunas_datas = [col for col in df_frequencia_bruta.columns[idx_freq+1:] if col != 'Frequência Num']
            
            alunos_ativos_pins = []
            
            for index, row in df_frequencia_bruta.iterrows():
                # Extrai apenas presenças e faltas daquele aluno (ignora vazios)
                status_list = [str(row.get(col, '')).strip().upper() for col in colunas_datas]
                status_list = [s for s in status_list if s in ['P', 'F', 'C']]
                
                # Regra 1: Tem pelo menos 2 presenças no total histórico? (Isso engloba quem vai 1x na semana)
                teve_duas_presencas = status_list.count('P') >= 2
                        
                # Regra 2: O aluno está com 4 faltas seguidas ativas no momento?
                esta_inativo = False
                if len(status_list) >= 4:
                    if status_list[-1] == 'F' and status_list[-2] == 'F' and status_list[-3] == 'F' and status_list[-4] == 'F':
                        esta_inativo = True
                        
                # Se for engajado, adiciona ao cálculo
                if teve_duas_presencas and not esta_inativo:
                    alunos_ativos_pins.append(str(row['PIN']).strip())
            
            # Filtra a base apenas com os ativos e calcula a nova média
            df_alunos['PIN'] = df_alunos['PIN'].astype(str).str.strip()
            df_ativos = df_alunos[df_alunos['PIN'].isin(alunos_ativos_pins)]
            
            if not df_ativos.empty:
                media_freq_real = df_ativos['Frequência Num'].mean()
                qtd_ativos = len(df_ativos)

        col2.metric(
            "Frequência Média (Ativos)", 
            f"{media_freq_real:.1f}%", 
            f"Calculado com base em {qtd_ativos} alunos", 
            help="A média reflete o tatame real: desconsidera alunos com menos de 2 presenças na história ou que estejam com 4 ou mais faltas consecutivas no momento."
        )
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        aba1, aba2, aba3 = st.tabs(["📊 Visão Geral (Resumo)", "📅 Controle de Frequência (Datas)", "🥋 Relatório de Graduação"])
        
        with aba1:
            st.markdown("### Histórico e Situação Atualizada")
            colunas_exibicao = ['Nome do Aluno', 'PIN', 'Frequência %', 'Faixa Atual', 'Status do Exame']
            colunas_disponiveis = [col for col in colunas_exibicao if col in df_alunos.columns]
            st.dataframe(df_alunos[colunas_disponiveis], use_container_width=True)
            
        with aba2:
            st.markdown("### Planilha Bruta de Frequência")
            st.dataframe(df_frequencia_bruta, use_container_width=True)
            
        with aba3:
            st.markdown("### Planilha Bruta de Graduação")
            if not df_graduacao_bruta.empty:
                st.dataframe(df_graduacao_bruta, use_container_width=True)
            else:
                st.info("Planilha de graduação não conectada ou vazia.")

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
        
        # --- TABELA DE HISTÓRICO DE AULAS ---
        st.markdown("### 📅 Seu Histórico Diário de Presença")
        st.write("Acompanhe aqui o registro cronológico das suas aulas computadas.")
        
        aluno_freq_bruta = df_frequencia_bruta[df_frequencia_bruta['PIN'] == st.session_state['pin_usuario']].iloc[0]
        
        if 'Frequência %' in df_frequencia_bruta.columns:
            idx_freq = df_frequencia_bruta.columns.get_loc('Frequência %')
            colunas_datas = [col for col in df_frequencia_bruta.columns[idx_freq+1:] if col != 'Frequência Num']
            
            if len(colunas_datas) > 0:
                historico_lista = []
                
                for data in colunas_datas:
                    status_aula = str(aluno_freq_bruta.get(data, "-")).strip().upper()
                    
                    if status_aula in ['NAN', '-', '']:
                        continue
                        
                    if status_aula == 'P':
                        status_formatado = "✅ Presente"
                    elif status_aula == 'F':
                        status_formatado = "❌ Falta"
                    elif status_aula == 'C':
                        status_formatado = "🔵 Cancelado / Feriado"
                    else:
                        status_formatado = status_aula
                        
                    historico_lista.append({"Data da Aula": data, "Status": status_formatado})
                
                if len(historico_lista) > 0:
                    df_historico_aluno = pd.DataFrame(historico_lista)
                    st.dataframe(df_historico_aluno, use_container_width=True, hide_index=True)
                else:
                    st.info("Nenhuma aula foi computada para você até o momento.")
            else:
                st.info("Nenhuma coluna de datas encontrada na planilha.")
