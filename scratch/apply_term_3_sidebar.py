import os

def main():
    app_path = "app.py"
    if not os.path.exists(app_path):
        print("app.py not found")
        return
        
    with open(app_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Update TRANSLATIONS titles and descriptions for Terminal III
    pt_target = '"term_3_title": "TERMINAL III: BALANCETES E B3 (BRAZIL)",\n        "term_3_desc": "Mapeamento de balanços de mega-caps, múltiplos corporativos e Graham value.",'
    pt_replace = '"term_3_title": "TERMINAL III: MÚLTIPLOS & BALANÇOS GLOBAIS (B3 & USA)",\n        "term_3_desc": "Análise fundamentalista profunda, Piotroski, Altman Z-Score e Graham Value de ações brasileiras e americanas.",'

    en_target = '"term_3_title": "TERMINAL III: CORPORATE BALANCES & B3 (BRAZIL)",\n        "term_3_desc": "Mega-caps balance sheets, corporate valuation, and Graham value mapping.",'
    en_replace = '"term_3_title": "TERMINAL III: GLOBAL FUNDAMENTALS & BALANCES (B3 & USA)",\n        "term_3_desc": "Deep fundamentalist analysis, Piotroski, Altman Z-Score, and Graham Value for Brazilian and American equities.",'

    es_target = '"term_3_title": "TERMINAL III: BALANCES Y B3 (BRAZIL)",\n        "term_3_desc": "Balances de mega-caps, múltiplos corporativos y mapeo de valor de Graham.",'
    es_replace = '"term_3_title": "TERMINAL III: ANÁLISIS FUNDAMENTALISTA GLOBAL (B3 & USA)",\n        "term_3_desc": "Análisis fundamentalista profundo, Piotroski, Altman Z-Score y Valor de Graham de acciones brasileñas y estadounidenses.",'

    if pt_target in content:
        content = content.replace(pt_target, pt_replace)
    else:
        # try with CRLF
        content = content.replace(pt_target.replace('\n', '\r\n'), pt_replace.replace('\n', '\r\n'))

    if en_target in content:
        content = content.replace(en_target, en_replace)
    else:
        content = content.replace(en_target.replace('\n', '\r\n'), en_replace.replace('\n', '\r\n'))

    if es_target in content:
        content = content.replace(es_target, es_replace)
    else:
        content = content.replace(es_target.replace('\n', '\r\n'), es_replace.replace('\n', '\r\n'))

    # 2. Update Sidebar Controls for Terminal III
    sidebar_target = """# --- CONTROLES DA SIDEBAR EXCLUSIVOS DO TERMINAL B3 ---
if st.session_state.active_terminal == "balance_sheets":
    # Sincronizar as planilhas do usuário a partir do Firestore ao inicializar a sessão
    if user_email and id_token and not st.session_state.get("b3_synced", False):
        with st.spinner("Sincronizando suas planilhas salvas..." if lang == "PT" else ("Syncing your saved spreadsheets..." if lang == "EN" else "Sincronizando suas planilhas...")):
            sync_user_spreadsheets_from_firestore(user_email, id_token, base_path_b3)
            st.session_state.b3_synced = True

    st.sidebar.markdown(f"<h3 style='font-size:16px; border:none; padding:0; text-align:center; color:#bf953f; font-weight:bold; margin-bottom:15px;'>{t['term_3_title']}</h3>", unsafe_allow_html=True)
    # UPLOAD DE NOVO ARQUIVO B3
    if "b3_uploader_key" not in st.session_state:
        st.session_state.b3_uploader_key = 0
    if "b3_upload_success" not in st.session_state:
        st.session_state.b3_upload_success = False

    uploaded_file = st.sidebar.file_uploader(
        "IMPORTAR PLANILHA (B3)" if lang == "PT" else ("IMPORT SPREADSHEET (B3)" if lang == "EN" else "IMPORTAR PLANILLA (B3)"), 
        type=["xls", "xlsx"],
        key=f"b3_uploader_{st.session_state.b3_uploader_key}"
    )
    if uploaded_file:
        try:
            with open(os.path.join(base_path_b3, uploaded_file.name), "wb") as f:
                f.write(uploaded_file.getbuffer())
                
            # Salvar backup permanente no Firestore do usuário
            if user_email and id_token:
                import requests
                import base64
                file_bytes = uploaded_file.getvalue()
                base64_content = base64.b64encode(file_bytes).decode("utf-8")
                safe_doc_id = uploaded_file.name.replace(".", "_")
                
                firestore_url = f"https://firestore.googleapis.com/v1/projects/perfect-life-82065/databases/(default)/documents/users/{user_email}/spreadsheets/{safe_doc_id}?updateMask.fieldPaths=filename&updateMask.fieldPaths=content"
                headers = {
                    "Authorization": f"Bearer {id_token}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "fields": {
                        "filename": {"stringValue": uploaded_file.name},
                        "content": {"stringValue": base64_content}
                    }
                }
                requests.patch(firestore_url, headers=headers, json=payload)
                
            st.session_state.b3_uploader_key += 1
            st.session_state.b3_upload_success = True
            st.rerun()
        except Exception as e:
            st.sidebar.error(f"Erro ao salvar planilha: {e}")
            
    if st.session_state.b3_upload_success:
        st.sidebar.success("Arquivo Importado com Sucesso!" if lang == "PT" else ("Spreadsheet Imported Successfully!" if lang == "EN" else "¡Planilla Importada con Éxito!"))
        st.session_state.b3_upload_success = False
    
    st.sidebar.write("---")
    
    # ENTRADA MANUAL DE DADOS (OVERRIDE)
    st.sidebar.subheader("AJUSTE DE MERCADO" if lang == "PT" else ("MARKET ADJUSTMENT" if lang == "EN" else "AJUSTE DE MERCADO"))
    manual_price = st.sidebar.number_input(
        "Preço da Ação (R$)" if lang == "PT" else ("Stock Price (R$)" if lang == "EN" else "Precio de Acción (R$)"), 
        min_value=0.0, 
        value=float(app_b3_state.get("price", 0.0)), 
        step=0.01
    )
    manual_shares_txt = st.sidebar.text_input(
        "Quantidade de Ações" if lang == "PT" else ("Shares Outstanding" if lang == "EN" else "Quantidade de Ações"), 
        value=str(app_b3_state.get("shares", "0"))
    )
    manual_dy = st.sidebar.number_input(
        "Dividend Yield Atual (%)" if lang == "PT" else ("Current Dividend Yield (%)" if lang == "EN" else "Dividend Yield Actual (%)"), 
        min_value=0.0, 
        value=float(app_b3_state.get("dy", 0.0)), 
        step=0.1
    )
    manual_selic = st.sidebar.number_input(
        "Taxa SELIC Atual (%)" if lang == "PT" else ("Current SELIC Rate (%)" if lang == "EN" else "Tasa SELIC Actual (%)"), 
        min_value=0.0, 
        value=float(app_b3_state.get("selic", 14.5)), 
        step=0.1
    )
    
    try:
        manual_shares = int(manual_shares_txt.replace('.', '').replace(' ', '').replace(',', '').strip())
    except:
        manual_shares = 0
        
    st.sidebar.write("---")
    
    # SELECIONAR A EMPRESA
    files_b3 = b3_parser.get_available_files()
    company_idx = files_b3.index(app_b3_state.get("company_name")) if app_b3_state.get("company_name") in files_b3 else 0
    
    selected_file = st.sidebar.selectbox(
        "SELECIONE A EMPRESA" if lang == "PT" else ("SELECT COMPANY" if lang == "EN" else "SELECCIONE LA EMPRESA"), 
        files_b3, 
        index=company_idx
    )
    
    st.sidebar.write("---")
    
    # SELECIONAR MÓDULO B3 (TRADUZIDO)
    b3_modules_list = {
        "PT": ["Radar de Comando", "Eficiência Operacional", "Análise de Lucratividade", "Solvência Patrimonial", "Valuation Intrínseco", "Tabela de Dados", "Radar de Aluguel (BTC)", "Recompras de Ações (Buybacks)"],
        "EN": ["Command Radar", "Operational Efficiency", "Profitability Analysis", "Asset Solvency", "Intrinsic Valuation", "Data Table", "Borrowing Radar (BTC)", "Share Buybacks (Buybacks)"],
        "ES": ["Radar de Comando", "Eficiencia Operacional", "Análisis de Lucratividad", "Solvencia Patrimonial", "Valuación Intrínseca", "Tabla de Datos", "Radar de Alquiler (BTC)", "Recompra de Acciones (Buybacks)"]
    }
    
    b3_module_map = {
        "Radar de Comando": "Radar de Comando",
        "Eficiência Operacional": "Eficiência Operacional",
        "Análise de Lucratividade": "Análise de Lucratividade",
        "Solvência Patrimonial": "Solvência Patrimonial",
        "Valuation Intrínseco": "Valuation Intrínseco",
        "Tabela de Dados": "Tabela de Dados",
        "Radar de Aluguel (BTC)": "Radar de Aluguel (BTC)",
        "Recompras de Ações (Buybacks)": "Recompras de Ações (Buybacks)",
        
        "Command Radar": "Radar de Comando",
        "Operational Efficiency": "Eficiência Operacional",
        "Profitability Analysis": "Análise de Lucratividade",
        "Asset Solvency": "Solvência Patrimonial",
        "Intrinsic Valuation": "Valuation Intrínseco",
        "Data Table": "Tabela de Dados",
        "Borrowing Radar (BTC)": "Radar de Aluguel (BTC)",
        "Share Buybacks (Buybacks)": "Recompras de Ações (Buybacks)",
        
        "Eficiencia Operacional": "Eficiência Operacional",
        "Análisis de Lucratividad": "Análise de Lucratividade",
        "Valuación Intrínseca": "Valuation Intrínseco",
        "Tabla de Datos": "Tabela de Dados",
        "Radar de Alquiler (BTC)": "Radar de Aluguel (BTC)",
        "Recompra de Acciones (Buybacks)": "Recompras de Ações (Buybacks)"
    }
    
    active_b3_mod_translated = app_b3_state.get("module", "Valuation Intrínseco")
    reverse_map = {v: k for k, v in b3_module_map.items()}
    default_translated_module = reverse_map.get(active_b3_mod_translated, b3_modules_list[lang][4])
    
    if default_translated_module not in b3_modules_list[lang]:
        b3_idx = 4
    else:
        b3_idx = b3_modules_list[lang].index(default_translated_module)
        
    selected_b3_mod_translated = st.sidebar.radio(
        "MÓDULOS ANALÍTICOS" if lang == "PT" else ("ANALYTICAL MODULES" if lang == "EN" else "MÓDULOS ANALÍTICOS"),
        b3_modules_list[lang],
        index=b3_idx
    )
    
    b3_module = b3_module_map.get(selected_b3_mod_translated, "Valuation Intrínseco")
    
    # Salvar estado atual se for diferente
    new_b3_state = {
        "company_name": selected_file,
        "price": manual_price,
        "shares": manual_shares_txt,
        "dy": manual_dy,
        "selic": manual_selic,
        "module": b3_module
    }
    if new_b3_state != app_b3_state:
        save_b3_state(new_b3_state)
        app_b3_state = new_b3_state"""

    sidebar_replace = """# --- CONTROLES DA SIDEBAR EXCLUSIVOS DO TERMINAL B3 & USA ---
if st.session_state.active_terminal == "balance_sheets":
    st.sidebar.markdown(f"<h3 style='font-size:16px; border:none; padding:0; text-align:center; color:#bf953f; font-weight:bold; margin-bottom:15px;'>{t['term_3_title']}</h3>", unsafe_allow_html=True)
    
    # Seletor de Cobertura Global (B3 vs USA)
    coverage_options = {
        "PT": ["🇧🇷 Brasil - B3 (Excel)", "🇺🇸 USA - Wall Street (Live)"],
        "EN": ["🇧🇷 Brazil - B3 (Excel)", "🇺🇸 USA - Wall Street (Live)"],
        "ES": ["🇧🇷 Brasil - B3 (Excel)", "🇺🇸 USA - Wall Street (Live)"]
    }
    if "term_3_coverage" not in st.session_state:
        st.session_state.term_3_coverage = "B3"
        
    selected_coverage_translated = st.sidebar.selectbox(
        "MERCADO / MARKET" if lang == "PT" else ("MARKET / COVERAGE" if lang == "EN" else "MERCADO / COBERTURA"),
        coverage_options[lang],
        index=0 if st.session_state.term_3_coverage == "B3" else 1
    )
    coverage_key = "B3" if selected_coverage_translated == coverage_options[lang][0] else "USA"
    st.session_state.term_3_coverage = coverage_key
    st.sidebar.write("---")

    if coverage_key == "B3":
        # Sincronizar as planilhas do usuário a partir do Firestore ao inicializar a sessão
        if user_email and id_token and not st.session_state.get("b3_synced", False):
            with st.spinner("Sincronizando suas planilhas salvas..." if lang == "PT" else ("Syncing your saved spreadsheets..." if lang == "EN" else "Sincronizando suas planilhas...")):
                sync_user_spreadsheets_from_firestore(user_email, id_token, base_path_b3)
                st.session_state.b3_synced = True

        # UPLOAD DE NOVO ARQUIVO B3
        if "b3_uploader_key" not in st.session_state:
            st.session_state.b3_uploader_key = 0
        if "b3_upload_success" not in st.session_state:
            st.session_state.b3_upload_success = False

        uploaded_file = st.sidebar.file_uploader(
            "IMPORTAR PLANILHA (B3)" if lang == "PT" else ("IMPORT SPREADSHEET (B3)" if lang == "EN" else "IMPORTAR PLANILLA (B3)"), 
            type=["xls", "xlsx"],
            key=f"b3_uploader_{st.session_state.b3_uploader_key}"
        )
        if uploaded_file:
            try:
                with open(os.path.join(base_path_b3, uploaded_file.name), "wb") as f:
                    f.write(uploaded_file.getbuffer())
                    
                # Salvar backup permanente no Firestore do usuário
                if user_email and id_token:
                    import requests
                    import base64
                    file_bytes = uploaded_file.getvalue()
                    base64_content = base64.b64encode(file_bytes).decode("utf-8")
                    safe_doc_id = uploaded_file.name.replace(".", "_")
                    
                    firestore_url = f"https://firestore.googleapis.com/v1/projects/perfect-life-82065/databases/(default)/documents/users/{user_email}/spreadsheets/{safe_doc_id}?updateMask.fieldPaths=filename&updateMask.fieldPaths=content"
                    headers = {
                        "Authorization": f"Bearer {id_token}",
                        "Content-Type": "application/json"
                    }
                    payload = {
                        "fields": {
                            "filename": {"stringValue": uploaded_file.name},
                            "content": {"stringValue": base64_content}
                        }
                    }
                    requests.patch(firestore_url, headers=headers, json=payload)
                    
                st.session_state.b3_uploader_key += 1
                st.session_state.b3_upload_success = True
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"Erro ao salvar planilha: {e}")
                
        if st.session_state.b3_upload_success:
            st.sidebar.success("Arquivo Importado com Sucesso!" if lang == "PT" else ("Spreadsheet Imported Successfully!" if lang == "EN" else "¡Planilla Importada con Éxito!"))
            st.session_state.b3_upload_success = False
        
        st.sidebar.write("---")
        
        # ENTRADA MANUAL DE DADOS (OVERRIDE)
        st.sidebar.subheader("AJUSTE DE MERCADO" if lang == "PT" else ("MARKET ADJUSTMENT" if lang == "EN" else "AJUSTE DE MERCADO"))
        manual_price = st.sidebar.number_input(
            "Preço da Ação (R$)" if lang == "PT" else ("Stock Price (R$)" if lang == "EN" else "Precio de Acción (R$)"), 
            min_value=0.0, 
            value=float(app_b3_state.get("price", 0.0)), 
            step=0.01
        )
        manual_shares_txt = st.sidebar.text_input(
            "Quantidade de Ações" if lang == "PT" else ("Shares Outstanding" if lang == "EN" else "Quantidade de Ações"), 
            value=str(app_b3_state.get("shares", "0"))
        )
        manual_dy = st.sidebar.number_input(
            "Dividend Yield Atual (%)" if lang == "PT" else ("Current Dividend Yield (%)" if lang == "EN" else "Dividend Yield Actual (%)"), 
            min_value=0.0, 
            value=float(app_b3_state.get("dy", 0.0)), 
            step=0.1
        )
        manual_selic = st.sidebar.number_input(
            "Taxa SELIC Atual (%)" if lang == "PT" else ("Current SELIC Rate (%)" if lang == "EN" else "Taxa SELIC Atual (%)"), 
            min_value=0.0, 
            value=float(app_b3_state.get("selic", 14.5)), 
            step=0.1
        )
        
        try:
            manual_shares = int(manual_shares_txt.replace('.', '').replace(' ', '').replace(',', '').strip())
        except:
            manual_shares = 0
            
        st.sidebar.write("---")
        
        # SELECIONAR A EMPRESA
        files_b3 = b3_parser.get_available_files()
        company_idx = files_b3.index(app_b3_state.get("company_name")) if app_b3_state.get("company_name") in files_b3 else 0
        
        selected_file = st.sidebar.selectbox(
            "SELECIONE A EMPRESA" if lang == "PT" else ("SELECT COMPANY" if lang == "EN" else "SELECCIONE LA EMPRESA"), 
            files_b3, 
            index=company_idx
        )
        
        st.sidebar.write("---")
        
        # SELECIONAR MÓDULO B3 (TRADUZIDO)
        b3_modules_list = {
            "PT": ["Radar de Comando", "Eficiência Operacional", "Análise de Lucratividade", "Solvência Patrimonial", "Valuation Intrínseco", "Tabela de Dados", "Radar de Aluguel (BTC)", "Recompras de Ações (Buybacks)"],
            "EN": ["Command Radar", "Operational Efficiency", "Profitability Analysis", "Asset Solvency", "Intrinsic Valuation", "Data Table", "Borrowing Radar (BTC)", "Share Buybacks (Buybacks)"],
            "ES": ["Radar de Comando", "Eficiencia Operacional", "Análisis de Lucratividad", "Solvencia Patrimonial", "Valuación Intrínseca", "Tabla de Datos", "Radar de Alquiler (BTC)", "Recompra de Acciones (Buybacks)"]
        }
        
        b3_module_map = {
            "Radar de Comando": "Radar de Comando",
            "Eficiência Operacional": "Eficiência Operacional",
            "Análise de Lucratividade": "Análise de Lucratividade",
            "Solvência Patrimonial": "Solvência Patrimonial",
            "Valuation Intrínseco": "Valuation Intrínseco",
            "Tabela de Dados": "Tabela de Dados",
            "Radar de Aluguel (BTC)": "Radar de Aluguel (BTC)",
            "Recompras de Ações (Buybacks)": "Recompras de Ações (Buybacks)",
            
            "Command Radar": "Radar de Comando",
            "Operational Efficiency": "Eficiência Operacional",
            "Profitability Analysis": "Análise de Lucratividade",
            "Asset Solvency": "Solvência Patrimonial",
            "Intrinsic Valuation": "Valuation Intrínseco",
            "Data Table": "Tabela de Dados",
            "Borrowing Radar (BTC)": "Radar de Aluguel (BTC)",
            "Share Buybacks (Buybacks)": "Recompras de Ações (Buybacks)",
            
            "Eficiencia Operacional": "Eficiência Operacional",
            "Análisis de Lucratividad": "Análise de Lucratividade",
            "Valuación Intrínseca": "Valuation Intrínseco",
            "Tabla de Datos": "Tabela de Dados",
            "Radar de Alquiler (BTC)": "Radar de Aluguel (BTC)",
            "Recompra de Acciones (Buybacks)": "Recompras de Ações (Buybacks)"
        }
        
        active_b3_mod_translated = app_b3_state.get("module", "Valuation Intrínseco")
        reverse_map = {v: k for k, v in b3_module_map.items()}
        default_translated_module = reverse_map.get(active_b3_mod_translated, b3_modules_list[lang][4])
        
        if default_translated_module not in b3_modules_list[lang]:
            b3_idx = 4
        else:
            b3_idx = b3_modules_list[lang].index(default_translated_module)
            
        selected_b3_mod_translated = st.sidebar.radio(
            "MÓDULOS ANALÍTICOS" if lang == "PT" else ("ANALYTICAL MODULES" if lang == "EN" else "MÓDULOS ANALÍTICOS"),
            b3_modules_list[lang],
            index=b3_idx
        )
        
        b3_module = b3_module_map.get(selected_b3_mod_translated, "Valuation Intrínseco")
        
        # Salvar estado atual se for diferente
        new_b3_state = {
            "company_name": selected_file,
            "price": manual_price,
            "shares": manual_shares_txt,
            "dy": manual_dy,
            "selic": manual_selic,
            "module": b3_module
        }
        if new_b3_state != app_b3_state:
            save_b3_state(new_b3_state)
            app_b3_state = new_b3_state
            
    else: # USA
        if "usa_ticker" not in st.session_state:
            st.session_state.usa_ticker = "AAPL"
            
        usa_ticker_input = st.sidebar.text_input(
            "TICKER DA AÇÃO (USA)" if lang == "PT" else ("STOCK TICKER (USA)" if lang == "EN" else "TICKER DE ACCIÓN (USA)"),
            value=st.session_state.usa_ticker
        ).strip().upper()
        
        st.session_state.usa_ticker = usa_ticker_input if usa_ticker_input else "AAPL"
        
        usa_modules_list = {
            "PT": ["Radar de Comando", "Eficiência Operacional", "Análise de Lucratividade", "Solvência Patrimonial", "Valuation Intrínseco", "Tabela de Dados"],
            "EN": ["Command Radar", "Operational Efficiency", "Profitability Analysis", "Asset Solvency", "Intrinsic Valuation", "Data Table"],
            "ES": ["Radar de Comando", "Eficiencia Operacional", "Análisis de Lucratividad", "Solvencia Patrimonial", "Valuación Intrínseca", "Tabla de Datos"]
        }
        
        usa_module_map = {
            "Radar de Comando": "Radar de Comando",
            "Eficiência Operacional": "Eficiência Operacional",
            "Análise de Lucratividade": "Análise de Lucratividade",
            "Solvência Patrimonial": "Solvência Patrimonial",
            "Valuation Intrínseco": "Valuation Intrínseco",
            "Tabela de Dados": "Tabela de Dados",
            
            "Command Radar": "Radar de Comando",
            "Operational Efficiency": "Eficiência Operacional",
            "Profitability Analysis": "Análise de Lucratividade",
            "Asset Solvency": "Solvência Patrimonial",
            "Intrinsic Valuation": "Valuation Intrínseco",
            "Data Table": "Tabela de Dados",
            
            "Eficiencia Operacional": "Eficiência Operacional",
            "Análisis de Lucratividad": "Análise de Lucratividade",
            "Valuación Intrínseca": "Valuation Intrínseco",
            "Tabla de Datos": "Tabela de Dados",
        }
        
        if "usa_module" not in st.session_state:
            st.session_state.usa_module = "Valuation Intrínseco"
            
        active_usa_mod_translated = st.session_state.usa_module
        reverse_usa_map = {v: k for k, v in usa_module_map.items()}
        default_usa_translated_module = reverse_usa_map.get(active_usa_mod_translated, usa_modules_list[lang][4])
        
        usa_idx = usa_modules_list[lang].index(default_usa_translated_module) if default_usa_translated_module in usa_modules_list[lang] else 4
        
        selected_usa_mod_translated = st.sidebar.radio(
            "MÓDULOS ANALÍTICOS" if lang == "PT" else ("ANALYTICAL MODULES" if lang == "EN" else "MÓDULOS ANALÍTICOS"),
            usa_modules_list[lang],
            index=usa_idx
        )
        st.session_state.usa_module = usa_module_map.get(selected_usa_mod_translated, "Valuation Intrínseco")"""

    if sidebar_target in content:
        content = content.replace(sidebar_target, sidebar_replace)
        print("Successfully updated Sidebar controls in app.py!")
    else:
        # try with CRLF
        content = content.replace(sidebar_target.replace('\n', '\r\n'), sidebar_replace.replace('\n', '\r\n'))
        print("Successfully updated Sidebar controls in app.py with CRLF!")

    with open(app_path, "w", encoding="utf-8") as f:
        f.write(content)

if __name__ == "__main__":
    main()
