import os

def main():
    app_path = "app.py"
    if not os.path.exists(app_path):
        return
        
    with open(app_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Find the lines
    start_line = -1
    for i, line in enumerate(lines):
        if "# Seletor de Idiomas na Barra Lateral" in line:
            start_line = i
            break
            
    if start_line == -1:
        print("Start line not found")
        return
        
    # Replace the block from start_line up to start_line + 13
    # Constructing using chr(0xfffd) to avoid unicodeescape SyntaxErrors
    new_block = (
        "# Seletor de Idiomas na Barra Lateral\n"
        'lang_options = {"Portugu" + chr(0xfffd) + "s (PT)": "PT", "English (EN)": "EN", "Espa" + chr(0xfffd) + "ol (ES)": "ES"}\n'
        'url_lang = st.query_params.get("lang", "PT").strip().upper()\n\n'
        'if "prev_url_lang" not in st.session_state or st.session_state.prev_url_lang != url_lang:\n'
        '    st.session_state.prev_url_lang = url_lang\n'
        '    inv_map = {v: k for k, v in lang_options.items()}\n'
        '    if url_lang in inv_map:\n'
        '        st.session_state.selected_lang_key = inv_map[url_lang]\n\n'
        'if "selected_lang_key" not in st.session_state:\n'
        '    inv_map = {v: k for k, v in lang_options.items()}\n'
        '    st.session_state.selected_lang_key = inv_map.get(url_lang, "Portugu" + chr(0xfffd) + "s (PT)")\n\n'
        'selected_lang = st.sidebar.selectbox("IDIOMA / LANGUAGE", list(lang_options.keys()), key="selected_lang_key")\n'
        'lang = lang_options[selected_lang]\n'
        'st.session_state.language = lang\n'
        't = TRANSLATIONS[lang]\n'
    )

    # We replace from index start_line to start_line + 13 (which covers lines 1022 to 1034)
    lines_replaced = lines[:start_line] + [new_block] + lines[start_line + 13:]
    
    with open(app_path, "w", encoding="utf-8") as f:
        f.writelines(lines_replaced)
        
    print("Successfully synchronized language binding in app.py!")

if __name__ == "__main__":
    main()
