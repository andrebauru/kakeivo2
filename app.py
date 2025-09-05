import streamlit as st
import mysql.connector
from datetime import datetime, date
import calendar
from streamlit_calendar import calendar as st_calendar

# --- 1. Conexão com o Banco de Dados ---
@st.cache_resource
def init_connection():
    try:
        return mysql.connector.connect(**st.secrets["mysql"])
    except Exception as e:
        st.error(f"Erro ao conectar ao banco de dados. Verifique suas credenciais em .streamlit/secrets.toml. Erro: {e}")
        st.stop()

conn = init_connection()

# --- 2. Funções de Backend (Interação com o DB) ---
def get_db_value(name):
    """Busca um valor da tabela de configurações."""
    cursor = conn.cursor()
    cursor.execute("SELECT valor FROM configuracoes WHERE nome = %s", (name,))
    result = cursor.fetchone()
    cursor.close()
    return result[0] if result else None

def update_db_value(name, value):
    """Atualiza um valor na tabela de configurações."""
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE configuracoes SET valor = %s WHERE nome = %s", (value, name))
        conn.commit()
        st.success(f"Configuração '{name}' atualizada com sucesso!")
        return True
    except Exception as e:
        st.error(f"Erro ao atualizar a configuração '{name}': {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()

def insert_transaction(data, valor, tipo, categoria, descricao, forma_pagamento):
    """Insere uma nova transação no banco de dados."""
    cursor = conn.cursor()
    try:
        sql = "INSERT INTO transacoes (data, valor, tipo, categoria, descricao, forma_pagamento) VALUES (%s, %s, %s, %s, %s, %s)"
        cursor.execute(sql, (data, valor, tipo, categoria, descricao, forma_pagamento))
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Erro ao registrar a transação: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()

def update_transaction(id, data, valor, tipo, categoria, descricao, forma_pagamento):
    """Atualiza uma transação existente no banco de dados."""
    cursor = conn.cursor()
    try:
        sql = "UPDATE transacoes SET data = %s, valor = %s, tipo = %s, categoria = %s, descricao = %s, forma_pagamento = %s WHERE id = %s"
        cursor.execute(sql, (data, valor, tipo, categoria, descricao, forma_pagamento, id))
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Erro ao atualizar a transação: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()

def get_transactions_by_month(year, month):
    """Busca todas as transações de um mês e ano específicos."""
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM transacoes WHERE YEAR(data) = %s AND MONTH(data) = %s ORDER BY data DESC", (year, month))
    records = cursor.fetchall()
    cursor.close()
    return records

def get_total_by_type(year, month, transaction_type):
    """Calcula o valor total de receitas ou despesas para um mês."""
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(valor) FROM transacoes WHERE YEAR(data) = %s AND MONTH(data) = %s AND tipo = %s", (year, month, transaction_type))
    result = cursor.fetchone()
    cursor.close()
    return int(result[0]) if result[0] else 0

def get_paginated_transactions(page_number, page_size=10):
    """Busca transações com paginação e total de registros."""
    offset = (page_number - 1) * page_size
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT COUNT(*) FROM transacoes")
    total_records = cursor.fetchone()['COUNT(*)']
    
    sql = "SELECT * FROM transacoes ORDER BY data DESC LIMIT %s OFFSET %s"
    cursor.execute(sql, (page_size, offset))
    records = cursor.fetchall()
    cursor.close()
    
    return records, total_records

# --- 3. Lógica de Autenticação com `st.session_state` ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "current_page" not in st.session_state:
    st.session_state.current_page = "Home"
if "selected_date" not in st.session_state:
    st.session_state.selected_date = date.today()
if "current_page_num" not in st.session_state:
    st.session_state.current_page_num = 1
if "editing_transaction_id" not in st.session_state:
    st.session_state.editing_transaction_id = None

def check_password():
    """Formulário de login para autenticação."""
    if not st.session_state.authenticated:
        st.title("Login do Kakeibo")
        with st.form("login_form"):
            password = st.text_input("Insira a senha:", type="password")
            submit_button = st.form_submit_button("Entrar")

        if submit_button:
            db_password = get_db_value("senha")
            if password == db_password:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Senha incorreta. Tente novamente.")
    
    return st.session_state.authenticated

# --- 4. Renderização da Interface (Front-end) ---
if check_password():
    st.title("📊 Kakeibo - Gestor Financeiro")
    page = st.sidebar.radio("Navegação", ["Home", "Registros", "Configurações"])

    # --- Página Home ---
    if page == "Home":
        st.session_state.current_page = "Home"
        st.header("Visão Geral do Mês")

        today = date.today()
        selected_month = today.month
        selected_year = today.year

        total_receita = get_total_by_type(selected_year, selected_month, 'receita')
        total_despesa = get_total_by_type(selected_year, selected_month, 'despesa')

        st.markdown("---")
        st.subheader("Resumo Financeiro (JPY)")
        col_res1, col_res2, col_res3 = st.columns(3)
        col_res1.metric("Total de Receitas", f"¥{total_receita:,.0f}")
        col_res2.metric("Total de Despesas", f"¥{total_despesa:,.0f}")
        col_res3.metric("Saldo do Mês", f"¥{total_receita - total_despesa:,.0f}")
        st.markdown("---")

        st.subheader("Selecione um dia:")
        # Uso do componente streamlit-calendar
        calendar_options = {
            "headerToolbar": {
                "left": "today prev,next",
                "center": "title",
                "right": "dayGridMonth"
            }
        }
        
        # O `event_click_data` vai conter as informações do evento clicado.
        # No nosso caso, vamos usar o `day_click_data` para obter a data selecionada.
        calendar_data = st_calendar(
            events=[],
            options=calendar_options,
            key="calendar"
        )

        # Se uma data for clicada no calendário, atualiza o estado da sessão
        if calendar_data:
            if "start" in calendar_data:
                selected_date_str = calendar_data["start"]
                st.session_state.selected_date = datetime.fromisoformat(selected_date_str.replace("Z", "")).date()
                st.rerun()

        st.divider()
        st.subheader("Registrar Transação")
        
        with st.expander(f"Registrar para o dia: {st.session_state.selected_date.strftime('%d/%m/%Y')}", expanded=True):
            with st.form("transaction_form"):
                valor = st.number_input("Valor (JPY)", min_value=1, step=1)
                tipo = st.radio("Tipo", ["despesa", "receita"], horizontal=True)
                
                raw_categories = get_db_value("categorias")
                categories = raw_categories.split(',') if raw_categories else []
                categoria = st.selectbox("Categoria", categories)

                raw_payment_methods = get_db_value("formas_pagamento")
                payment_methods = raw_payment_methods.split(',') if raw_payment_methods else []
                forma_pagamento = st.selectbox("Forma de Pagamento", payment_methods)

                descricao = st.text_area("Descrição (opcional)")
                
                submit_transaction = st.form_submit_button("Registrar")

            if submit_transaction:
                if valor <= 0:
                    st.warning("O valor deve ser maior que zero.")
                else:
                    if insert_transaction(st.session_state.selected_date, valor, tipo, categoria, descricao, forma_pagamento):
                        st.success("Transação registrada com sucesso!")
                        st.session_state.selected_date = today 
                        st.rerun()

    # --- Página de Registros ---
    elif page == "Registros":
        st.session_state.current_page = "Registros"
        st.header("Histórico de Transações")

        records, total_records = get_paginated_transactions(st.session_state.current_page_num)
        
        if records:
            cols = st.columns([0.1, 1, 1, 1, 1, 1, 1])
            headers = ["", "Data", "Valor", "Tipo", "Categoria", "Descrição", "Pagamento"]
            for i, header in enumerate(headers):
                with cols[i]:
                    st.markdown(f"**{header}**")

            for record in records:
                col_edit, col_date, col_value, col_type, col_cat, col_desc, col_pay = st.columns([0.1, 1, 1, 1, 1, 1, 1])
                
                with col_edit:
                    if st.button("✏️", key=f"edit_{record['id']}"):
                        st.session_state.editing_transaction_id = record['id']
                        st.session_state.edit_data = record
                        st.rerun()

                with col_date:
                    st.write(record['data'].strftime('%Y-%m-%d'))
                with col_value:
                    st.write(f"¥{record['valor']:,}")
                with col_type:
                    st.write(record['tipo'])
                with col_cat:
                    st.write(record['categoria'])
                with col_desc:
                    st.write(record['descricao'])
                with col_pay:
                    st.write(record['forma_pagamento'])
            
            total_pages = (total_records + 9) // 10
            pagination_col1, pagination_col2, pagination_col3 = st.columns([1,2,1])
            with pagination_col1:
                if st.button("Página Anterior", disabled=(st.session_state.current_page_num == 1)):
                    st.session_state.current_page_num -= 1
                    st.session_state.editing_transaction_id = None
                    st.rerun()
            with pagination_col2:
                st.write(f"Página **{st.session_state.current_page_num}** de **{total_pages}**")
            with pagination_col3:
                if st.button("Próxima Página", disabled=(st.session_state.current_page_num == total_pages)):
                    st.session_state.current_page_num += 1
                    st.session_state.editing_transaction_id = None
                    st.rerun()
        else:
            st.info("Nenhum registro de transação encontrado.")

        if st.session_state.editing_transaction_id is not None:
            st.divider()
            st.subheader("Editar Transação")
            with st.expander("Formulário de Edição", expanded=True):
                edit_record = st.session_state.edit_data
                with st.form("edit_transaction_form"):
                    edit_valor = st.number_input("Valor (JPY)", min_value=1, step=1, value=int(edit_record['valor']))
                    edit_tipo = st.radio("Tipo", ["despesa", "receita"], horizontal=True, index=0 if edit_record['tipo'] == 'despesa' else 1)
                    
                    raw_categories = get_db_value("categorias")
                    categories = raw_categories.split(',') if raw_categories else []
                    cat_index = categories.index(edit_record['categoria']) if edit_record['categoria'] in categories else 0
                    edit_categoria = st.selectbox("Categoria", categories, index=cat_index)

                    raw_payment_methods = get_db_value("formas_pagamento")
                    payment_methods = raw_payment_methods.split(',') if raw_payment_methods else []
                    pay_index = payment_methods.index(edit_record['forma_pagamento']) if edit_record['forma_pagamento'] in payment_methods else 0
                    edit_forma_pagamento = st.selectbox("Forma de Pagamento", payment_methods, index=pay_index)

                    edit_descricao = st.text_area("Descrição (opcional)", value=edit_record['descricao'])
                    
                    col_save, col_cancel = st.columns([1,1])
                    with col_save:
                        save_button = st.form_submit_button("Salvar Edição")
                    with col_cancel:
                        cancel_button = st.form_submit_button("Cancelar")

                if save_button:
                    if edit_valor <= 0:
                        st.warning("O valor deve ser maior que zero.")
                    else:
                        if update_transaction(edit_record['id'], edit_record['data'], edit_valor, edit_tipo, edit_categoria, edit_descricao, edit_forma_pagamento):
                            st.success("Transação atualizada com sucesso!")
                            st.session_state.editing_transaction_id = None
                            st.rerun()
                
                if cancel_button:
                    st.session_state.editing_transaction_id = None
                    st.rerun()

    # --- Página de Configurações ---
    elif page == "Configurações":
        st.session_state.current_page = "Configurações"
        st.header("⚙️ Configurações do Sistema")

        st.subheader("Alterar Senha de Acesso")
        with st.form("password_form"):
            new_password = st.text_input("Nova Senha", type="password")
            confirm_password = st.text_input("Confirme a Nova Senha", type="password")
            update_password_btn = st.form_submit_button("Atualizar Senha")

        if update_password_btn:
            if new_password and new_password == confirm_password:
                if update_db_value("senha", new_password):
                    st.success("Senha alterada com sucesso!")
            else:
                st.error("As senhas não coincidem ou estão vazias.")
            st.rerun()

        st.subheader("Gerenciar Categorias")
        with st.form("category_form"):
            new_category = st.text_input("Adicionar Nova Categoria")
            add_category_btn = st.form_submit_button("Adicionar Categoria")
        
        if add_category_btn:
            if new_category:
                raw_categories = get_db_value("categorias")
                categories = raw_categories.split(',') if raw_categories else []
                if new_category not in categories:
                    categories.append(new_category)
                    updated_categories = ','.join(categories)
                    if update_db_value("categorias", updated_categories):
                        st.success(f"Categoria '{new_category}' adicionada com sucesso!")
                else:
                    st.warning(f"A categoria '{new_category}' já existe.")
            else:
                st.error("O nome da categoria não pode ser vazio.")
            st.rerun()

        st.markdown("---")
        st.subheader("Categorias Atuais")
        current_categories = get_db_value("categorias")
        st.write(f"**{current_categories}**")

        st.subheader("Gerenciar Formas de Pagamento")
        with st.form("payment_form"):
            new_payment_method = st.text_input("Adicionar Nova Forma de Pagamento")
            add_payment_btn = st.form_submit_button("Adicionar Forma de Pagamento")
        
        if add_payment_btn:
            if new_payment_method:
                raw_payment_methods = get_db_value("formas_pagamento")
                payment_methods = raw_payment_methods.split(',') if raw_payment_methods else []
                if new_payment_method not in payment_methods:
                    payment_methods.append(new_payment_method)
                    updated_payment_methods = ','.join(payment_methods)
                    if update_db_value("formas_pagamento", updated_payment_methods):
                        st.success(f"Forma de pagamento '{new_payment_method}' adicionada com sucesso!")
                else:
                    st.warning(f"A forma de pagamento '{new_payment_method}' já existe.")
            else:
                st.error("O nome da forma de pagamento não pode ser vazio.")
            st.rerun()

        st.markdown("---")
        st.subheader("Formas de Pagamento Atuais")
        current_payment_methods = get_db_value("formas_pagamento")
        st.write(f"**{current_payment_methods}**")