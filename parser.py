import pandas as pd
import numpy as np
import os

class EliteB3Parser:
    def __init__(self, folder_path):
        self.folder_path = folder_path

    def get_available_files(self):
        return [f for f in os.listdir(self.folder_path) if f.endswith('.xls')]

    def parse_file(self, file_name):
        full_path = os.path.join(self.folder_path, file_name)
        
        # Parse DRE
        # --- Extração e Alinhamento de Datas ---
        # DRE
        dre = pd.read_excel(full_path, sheet_name='Dem. Result.', header=None)
        dre_dates_raw = dre.iloc[1].values
        dre_dates = []
        dre_col_indices = []
        for idx, val in enumerate(dre_dates_raw):
            d_str = str(val).split(' ')[0]
            if ('/' in d_str or '-' in d_str) and len(d_str) >= 8:
                dre_dates.append(d_str)
                dre_col_indices.append(idx)
        
        dates = dre_dates
        num_cols = len(dates)

        # BP
        bp = pd.read_excel(full_path, sheet_name='Bal. Patrim.', header=None)
        bp_dates_raw = bp.iloc[1].values
        bp_col_map = {}
        for idx, val in enumerate(bp_dates_raw):
            d_str = str(val).split(' ')[0]
            if ('/' in d_str or '-' in d_str) and len(d_str) >= 8:
                bp_col_map[d_str] = idx

        def parse_val(val):
            if pd.isna(val): return 0.0
            if isinstance(val, (int, float)): return float(val) * 1000
            s = str(val).strip()
            if s == '': return 0.0
            try:
                if ',' in s and '.' in s: s = s.replace('.', '')
                s = s.replace(',', '.')
                return float(s) * 1000
            except:
                return 0.0

        def get_dre_row(keywords):
            for i, row in dre.iterrows():
                full_line = " ".join([str(val).lower() for val in row[:3]])
                if all(k.lower() in full_line for k in keywords):
                    return [parse_val(row[idx]) for idx in dre_col_indices]
            return [0.0] * num_cols

        def get_bp_row(keywords, fallback_idx=None):
            has_labels = any(isinstance(x, str) and len(x) > 3 for x in bp[0].dropna())
            found_idx = fallback_idx
            if has_labels:
                for i, row in bp.iterrows():
                    full_line = " ".join([str(val).lower() for val in row[:3]])
                    if all(k.lower() in full_line for k in keywords):
                        found_idx = i
                        break
            if found_idx is not None and found_idx < len(bp):
                row = bp.iloc[found_idx]
                return [parse_val(row[bp_col_map[d]]) if d in bp_col_map else 0.0 for d in dates]
            return [0.0] * num_cols

        # --- DRE (Dem. Result.) ---
        revenue = get_dre_row(["receita", "quida"])
        if sum(revenue) == 0: revenue = get_dre_row(["receita", "vendas"])
        if sum(revenue) == 0: revenue = get_dre_row(["receita", "intermedia"]) # Bancos
        
        profit = get_dre_row(["lucro", "preju", "per"])
        if sum(profit) == 0: profit = get_dre_row(["lucro", "quido"])
        if sum(profit) == 0: profit = get_dre_row(["lucro", "preju"]) # Fallback Bancos
        
        ebitda = get_dre_row(["ebitda"])
        if sum(ebitda) == 0: ebitda = get_dre_row(["resultado", "bruto"])
        
        # --- Balanço (Bal. Patrim.) ---
        equity = get_bp_row(["patrim", "quido"], fallback_idx=47)
        if equity[-1] == 0: equity = get_bp_row(["patrim", "quido"], fallback_idx=51) # Fallback Bancos PINE
        cash = get_bp_row(["caixa", "equivalentes"], fallback_idx=4)
        
        debt_cp = get_bp_row(["empr", "financ", "circulante"], fallback_idx=31)
        debt_lp = get_bp_row(["empr", "financ", "n", "o", "circulante"], fallback_idx=38)
        debt = [a + b for a, b in zip(debt_cp, debt_lp)]

        df = pd.DataFrame({
            "Data": dates,
            "Receita": revenue,
            "EBITDA": ebitda,
            "Lucro": profit,
            "Patrimonio": equity,
            "Caixa": cash,
            "Divida": debt
        })
        
        # Inverter para ordem cronológica se necessário
        # Assumindo que o Excel vem do mais recente para o mais antigo (comum na B3)
        # Vamos checar se a primeira data é maior que a última
        if dates[0] > dates[-1]:
            df = df.iloc[::-1].reset_index(drop=True)
            
        return df

if __name__ == "__main__":
    parser = EliteB3Parser(r"C:\Users\padua\OneDrive\Área de Trabalho\balanços empresas B3")
    data = parser.parse_file("balanco cmig4.xls")
    print(data.tail())
