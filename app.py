import streamlit as st
import mysql.connector
from mysql.connector.errors import OperationalError
from datetime import datetime, date
import calendar
from streamlit_calendar import calendar as st_calendar
import pandas as pd
import time
from functools import wraps
import logging
import altair as alt

# --- Configuração do Logger ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('app_logger')
logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler('app.log')
file_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# --- 1. Conexão com o Banco de Dados e Decorador de Reconexão ---

def init_connection():
    logger.debug("Tentando inicializar a conexão com o banco de dados...")
    try:
        conn = mysql.connector.connect(**st.secrets["mysql"])
        logger.info("Conexão com o banco de dados estabelecida com sucesso.")
        return conn
    except Exception as e:
        logger.error(f"Erro ao conectar ao banco de dados: {e}")
        st.error(f"Erro ao conectar ao banco de dados. Verifique suas credenciais. Erro: {e}")
        st.stop()

def reconnect_on_error(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except OperationalError as e:
            if e.errno == 2006:
                logger.warning("Conexão com o MySQL foi perdida. Tentando reconectar...")
                st.session_state.conn = init_connection()
                return func(*args, **kwargs)
            else:
                logger.error(f"Erro operacional não esperado: {e}")
                raise e
    return wrapper

if "conn" not in st.session_state:
    st.session_state.conn = init_connection()

# --- 2. Funções de Backend (Interação com o DB) ---

@reconnect_on_error
def get_db_value(name):
    """Busca um valor da tabela de configurações."""
    cursor = st.session_state.conn.cursor()
    cursor.execute("SELECT valor FROM configuracoes WHERE nome = %s", (name,))
    result = cursor.fetchone()
    cursor.close()
    return result[0] if result else None

@reconnect_on_error
def update_db_value(name, value):
    """Atualiza um valor na tabela de configurações."""
    cursor = st.session_state.conn.cursor()
    try:
        cursor.execute("UPDATE configuracoes SET valor = %s WHERE nome = %s", (value, name))
        st.session_state.conn.commit()
        return True
    except Exception as e:
        logger.error(f"Erro ao atualizar a configuração '{name}': {e}")
        st.session_state.conn.rollback()
        return False
    finally:
        cursor.close()

@reconnect_on_error
def insert_transaction(data, valor, tipo, categoria, descricao, forma_pagamento, pago):
    """Insere uma nova transação no banco de dados."""
    cursor = st.session_state.conn.cursor()
    try:
        sql = "INSERT INTO transacoes (data, valor, tipo, categoria, descricao, forma_pagamento, pago) VALUES (%s, %s, %s, %s, %s, %s, %s)"
        cursor.execute(sql, (data, valor, tipo, categoria, descricao, forma_pagamento, pago))
        st.session_state.conn.commit()
        return True
    except Exception as e:
        logger.error(f"Erro ao registrar a transação: {e}")
        st.session_state.conn.rollback()
        return False
    finally:
        cursor.close()

@reconnect_on_error
def update_transaction(id, data, valor, tipo, categoria, descricao, forma_pagamento, pago):
    """Atualiza uma transação existente no banco de dados, incluindo o status de pago."""
    cursor = st.session_state.conn.cursor()
    try:
        sql = "UPDATE transacoes SET data = %s, valor = %s, tipo = %s, categoria = %s, descricao = %s, forma_pagamento = %s, pago = %s WHERE id = %s"
        cursor.execute(sql, (data, valor, tipo, categoria, descricao, forma_pagamento, pago, id))
        st.session_state.conn.commit()
        return True
    except Exception as e:
        logger.error(f"Erro ao atualizar a transação: {e}")
        st.session_state.conn.rollback()
        return False
    finally:
        cursor.close()

@reconnect_on_error
def mark_transaction_as_paid(id):
    """Marca uma transação específica como paga."""
    cursor = st.session_state.conn.cursor()
    try:
        sql = "UPDATE transacoes SET pago = 1 WHERE id = %s"
        cursor.execute(sql, (id,))
        st.session_state.conn.commit()
        return True
    except Exception as e:
        logger.error(f"Erro ao marcar como pago: {e}")
        st.session_state.conn.rollback()
        return False
    finally:
        cursor.close()

@reconnect_on_error
def delete_transaction(id):
    """Exclui uma transação do banco de dados."""
    cursor = st.session_state.conn.cursor()
    try:
        sql = "DELETE FROM transacoes WHERE id = %s"
        cursor.execute(sql, (id,))
        st.session_state.conn.commit()
        return True
    except Exception as e:
        logger.error(f"Erro ao excluir a transação: {e}")
        st.session_state.conn.rollback()
        return False
    finally:
        cursor.close()

@reconnect_on_error
def get_transactions_by_month(year, month):
    """Busca todas as transações de um mês e ano específicos."""
    cursor = st.session_state.conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM transacoes WHERE YEAR(data) = %s AND MONTH(data) = %s ORDER BY data DESC", (year, month))
    records = cursor.fetchall()
    cursor.close()
    return records

@reconnect_on_error
def get_total_by_type(year, month, transaction_type):
    """Calcula o valor total de receitas ou despesas para um mês."""
    cursor = st.session_state.conn.cursor()
    cursor.execute("SELECT SUM(valor) FROM transacoes WHERE YEAR(data) = %s AND MONTH(data) = %s AND tipo = %s", (year, month, transaction_type))
    result = cursor.fetchone()
    cursor.close()
    return int(result[0]) if result[0] else 0

@reconnect_on_error
def get_paginated_transactions(page_number, page_size=10):
    """Busca transações com paginação e total de registros."""
    offset = (page_number - 1) * page_size
    cursor = st.session_state.conn.cursor(dictionary=True)
    cursor.execute("SELECT COUNT(*) FROM transacoes")
    total_records = cursor.fetchone()['COUNT(*)']
    
    sql = "SELECT * FROM transacoes ORDER BY data DESC LIMIT %s OFFSET %s"
    cursor.execute(sql, (page_size, offset))
    records = cursor.fetchall()
    cursor.close()
    
    return records, total_records

@reconnect_on_error
def get_expenses_by_category(year, month):
    """Busca o total de despesas por categoria para um mês e ano específicos."""
    cursor = st.session_state.conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT categoria, SUM(valor) AS total
        FROM transacoes
        WHERE YEAR(data) = %s AND MONTH(data) = %s AND tipo = 'despesa'
        GROUP BY categoria
        ORDER BY total DESC
    """, (year, month))
    records = cursor.fetchall()
    cursor.close()
    return records

def get_calendar_events(year, month):
    """Converte as transações para o formato de eventos do calendário com cores."""
    transactions = get_transactions_by_month(year, month)
    events = []
    today = date.today()

    for t in transactions:
        event_title = f"¥{t['valor']:,} | {t['categoria']}"

        if t['tipo'] == 'receita':
            event_color = "#34A853" # Verde
            event_title = f"Entrada: {event_title}"
        elif t['tipo'] == 'despesa':
            if t['pago'] == 1:
                event_color = "#4285F4" # Azul para Pago
                event_title = f"Pago: {event_title}"
            elif t['data'] < today:
                event_color = "#EA4335" # Vermelho para Atrasado
                event_title = f"⚠ Atrasado: {event_title}"
            else:
                event_color = "#FBBC04" # Amarelo para A Pagar

        events.append({
            "title": event_title,
            "start": t['data'].strftime('%Y-%m-%d'),
            "end": t['data'].strftime('%Y-%m-%d'),
            "color": event_color
        })
    return events

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
if "edit_data" not in st.session_state:
    st.session_state.edit_data = {}

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

    page = st.sidebar.radio("Navegação", ["Home", "Gastos", "Registros", "Configurações"])

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
        
        events = get_calendar_events(selected_year, selected_month)

        calendar_options = {
            "headerToolbar": {
                "left": "today prev,next",
                "center": "title",
                "right": "dayGridMonth"
            }
        }
        
        calendar_data = st_calendar(
            events=events,
            options=calendar_options,
            key="calendar"
        )

        if calendar_data:
            if "start" in calendar_data:
                selected_date_str = calendar_data["start"]
                st.session_state.selected_date = datetime.fromisoformat(selected_date_str.replace("Z", "")).date()
                st.rerun()

        st.markdown("---")
        st.subheader("Legenda do Calendário")
        st.markdown("""
        - <span style="color:#34A853;">**Verde:** Receita</span>
        - <span style="color:#FBBC04;">**Amarelo:** Despesa a Pagar</span>
        - <span style="color:#EA4335;">**Vermelho:** Despesa Atrasada</span>
        - <span style="color:#4285F4;">**Azul:** Conta Paga</span>
        """, unsafe_allow_html=True)
        st.markdown("---")

        st.subheader("Registrar Transação")
        
        with st.expander(f"Registrar para o dia: {st.session_state.selected_date.strftime('%d/%m/%Y')}", expanded=True):
            with st.form(key="transaction_form"):
                
                form_date = st.date_input("Data da Transação", value=st.session_state.selected_date)

                valor = st.number_input("Valor (JPY)", min_value=1, step=1)
                tipo = st.radio("Tipo", ["despesa", "receita"], horizontal=True)
                
                raw_categories = get_db_value("categorias")
                categories = raw_categories.split(',') if raw_categories else []
                categoria = st.selectbox("Categoria", categories)

                raw_payment_methods = get_db_value("formas_pagamento")
                payment_methods = raw_payment_methods.split(',') if raw_payment_methods else []
                forma_pagamento = st.selectbox("Forma de Pagamento", payment_methods)

                descricao = st.text_area("Descrição (opcional)")

                pago = st.checkbox("Marcar como Pago")
                
                submit_transaction = st.form_submit_button("Registrar")

            if submit_transaction:
                if valor <= 0:
                    st.warning("O valor deve ser maior que zero.")
                else:
                    if insert_transaction(form_date, valor, tipo, categoria, descricao, forma_pagamento, pago):
                        st.success("Transação registrada com sucesso!")
                        st.session_state.selected_date = today 
                        st.rerun()

    # --- Página Gastos ---
    elif page == "Gastos":
        st.session_state.current_page = "Gastos"
        st.header("Gráfico de Gastos por Categoria")
        
        logger.debug("Renderizando página Gastos.")
        today = date.today()
        col1, col2 = st.columns(2)
        with col1:
            month_options = list(calendar.month_name)[1:]
            selected_month_name = st.selectbox("Mês", month_options, index=today.month - 1, key="gastos_month")
            selected_month = month_options.index(selected_month_name) + 1
        with col2:
            selected_year = st.selectbox("Ano", range(today.year - 5, today.year + 5), index=5, key="gastos_year")

        logger.debug(f"Selecionado: Mês={selected_month}, Ano={selected_year}")
        expenses_data = get_expenses_by_category(selected_year, selected_month)

        if expenses_data:
            df_expenses = pd.DataFrame(expenses_data)
            logger.debug(f"Dados brutos do banco de dados: {expenses_data}")
            logger.debug(f"DataFrame do Pandas: \n{df_expenses}")
            
            # Converte 'total' para int para o gráfico, pois o Decimal pode causar problemas
            df_expenses['total'] = df_expenses['total'].astype(int)
            
            chart = alt.Chart(df_expenses).mark_bar().encode(
                x=alt.X('categoria', sort='-y'),
                y='total'
            ).properties(
                title=f"Gastos por Categoria - {selected_month_name} {selected_year}"
            )
            st.altair_chart(chart, use_container_width=True)
            
            st.write("Dados de gastos por categoria:")
            st.dataframe(df_expenses, use_container_width=True)
        else:
            st.info("Nenhuma despesa encontrada para o mês e ano selecionados.")
            logger.info("Nenhuma despesa encontrada para o período selecionado. Não foi possível gerar o gráfico.")


    # --- Página de Registros ---
    elif page == "Registros":
        st.session_state.current_page = "Registros"
        st.header("Histórico de Transações")

        records, total_records = get_paginated_transactions(st.session_state.current_page_num)
        
        if records:
            st.markdown("---")
            for record in records:
                st.subheader(f"{record['data'].strftime('%Y-%m-%d')} - {record['categoria']}")
                
                col_info, col_actions = st.columns([2, 1])
                
                with col_info:
                    st.write(f"**Valor:** ¥{record['valor']:,}")
                    st.write(f"**Tipo:** {record['tipo']}")
                    st.write(f"**Pagamento:** {record['forma_pagamento']}")
                    st.write(f"**Status:** {'Pago' if record['pago'] else 'A Pagar'}")
                    if record['descricao']:
                        st.write(f"**Descrição:** {record['descricao']}")
                
                with col_actions:
                    if st.button("✏️ Editar", key=f"edit_{record['id']}", use_container_width=True):
                        st.session_state.editing_transaction_id = record['id']
                        st.session_state.edit_data = record
                        st.rerun()

                    if not record['pago'] and record['tipo'] == 'despesa':
                        if st.button("✅ Pagar", key=f"mark_{record['id']}", use_container_width=True):
                            if mark_transaction_as_paid(record['id']):
                                st.success("Transação marcada como paga!")
                                st.rerun()
                    
                    if st.button("🗑️ Excluir", key=f"delete_{record['id']}", use_container_width=True):
                        if delete_transaction(record['id']):
                            st.success("Transação excluída com sucesso!")
                            st.rerun()

                st.markdown("---")

            
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
                with st.form(key=f"edit_form_{st.session_state.editing_transaction_id}"):
                    
                    edit_date = st.date_input("Data da Transação", value=edit_record['data'])
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
                    
                    edit_pago = st.checkbox("Marcar como Pago", value=bool(edit_record['pago']))

                    col_save, col_cancel = st.columns([1,1])
                    with col_save:
                        save_button = st.form_submit_button("Salvar Edição")
                    with col_cancel:
                        cancel_button = st.form_submit_button("Cancelar")

                if save_button:
                    if edit_valor <= 0:
                        st.warning("O valor deve ser maior que zero.")
                    else:
                        if update_transaction(edit_record['id'], edit_date, edit_valor, edit_tipo, edit_categoria, edit_descricao, edit_forma_pagamento, edit_pago):
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