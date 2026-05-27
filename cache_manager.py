import os
import json
from sec_connector import SECConnector

WHALES = {
    "Vanguard": {"cik": "0000102909", "type": "Fundo/Gestor"},
    "BlackRock": {"cik": "0001364742", "type": "Fundo/Gestor"},
    "Berkshire Hathaway": {"cik": "0001067983", "type": " Warren Buffett (Holding)"},
    "Goldman Sachs": {"cik": "0000886982", "type": "Banco de Investimento"},
    "Morgan Stanley": {"cik": "0000895421", "type": "Banco de Investimento"},
    "JPMorgan Chase": {"cik": "0000019617", "type": "Banco de Investimento"}
}

CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

class CacheManager:
    def __init__(self):
        self.connector = SECConnector()
        
    def get_cache_path(self, name):
        clean_name = name.lower().replace(" ", "_")
        return os.path.join(CACHE_DIR, f"{clean_name}_holdings.json")
        
    def load_holdings(self, name):
        """Loads holdings of a whale from cache. If not cached, fetches from SEC."""
        path = self.get_cache_path(name)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error reading cache for {name}: {e}")
                
        # If cache doesn't exist, sync and return
        return self.sync_whale(name)
        
    def sync_whale(self, name):
        """Fetches fresh data from the SEC EDGAR API and writes it to the local JSON cache."""
        info = WHALES.get(name)
        if not info:
            return []
            
        cik = info["cik"]
        holdings = self.connector.get_latest_13f_holdings(cik, name)
        
        if holdings:
            # We cache only the top 150 holdings to keep loading times blazing fast and clean
            top_holdings = holdings[:150]
            
            # Add metadata info
            cache_data = {
                "name": name,
                "cik": cik,
                "type": info["type"],
                "last_updated": os.getenv("CURRENT_TIME", "2026-05-24"), # Standard timestamp fallback
                "total_holdings_count": len(holdings),
                "total_portfolio_value": sum(h["value"] for h in holdings),
                "data": top_holdings
            }
            
            path = self.get_cache_path(name)
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(cache_data, f, indent=4, ensure_ascii=False)
                return cache_data
            except Exception as e:
                print(f"Error writing cache for {name}: {e}")
                
        return {"name": name, "data": [], "total_portfolio_value": 0, "last_updated": "N/A", "total_holdings_count": 0}

    def get_overlapping_convictions(self):
        """
        Cross-analyzes the holdings of all 6 whales to find high conviction stocks.
        Returns a sorted list of stocks owned by the highest number of whales and their combined value.
        """
        combined_holdings = {}
        
        # Load all whales data
        for name in WHALES.keys():
            cache_data = self.load_holdings(name)
            holdings = cache_data.get("data", [])
            
            # Calculate weight inside each whale's top list
            total_val = cache_data.get("total_portfolio_value", 0)
            if total_val == 0:
                total_val = sum(h["value"] for h in holdings)
                
            for h in holdings:
                cusip = h.get("cusip")
                if not cusip:
                    continue
                # Evitar duplicar Alphabet (filtra Class C / GOOG, mantendo apenas Class A / GOOGL)
                if cusip == "02079K107":
                    continue
                    
                issuer = h.get("name", "UNKNOWN").upper().strip()
                # Clean up issuer name suffixes for better overlapping match
                clean_issuer = issuer.replace(" INC", "").replace(" CORP", "").replace(" CO", "").replace(" LTD", "").replace(" CLASS A", "").replace(" CL A", "").strip()
                
                value = h.get("value", 0)
                shares = h.get("shares", 0)
                weight = (value / total_val) * 100 if total_val > 0 else 0
                
                # Match primarily on CUSIP
                key = cusip
                if key not in combined_holdings:
                    combined_holdings[key] = {
                        "cusip": cusip,
                        "name": clean_issuer,
                        "original_names": {issuer},
                        "whales_involved": {name},
                        "total_value": value,
                        "total_shares": shares,
                        "weights": {name: weight}
                    }
                else:
                    combined_holdings[key]["whales_involved"].add(name)
                    combined_holdings[key]["original_names"].add(issuer)
                    combined_holdings[key]["total_value"] += value
                    combined_holdings[key]["total_shares"] += shares
                    combined_holdings[key]["weights"][name] = weight
                    
        # Filter and compile results
        convictions = []
        for key, info in combined_holdings.items():
            num_whales = len(info["whales_involved"])
            # Display best representative name (shortest original name is usually the cleanest)
            best_name = min(info["original_names"], key=len)
            
            convictions.append({
                "cusip": info["cusip"],
                "name": best_name,
                "whales_count": num_whales,
                "whales_list": sorted(list(info["whales_involved"])),
                "total_value": info["total_value"],
                "total_shares": info["total_shares"],
                "avg_weight": sum(info["weights"].values()) / num_whales
            })
            
        # Sort by: 1) Number of Whales descending, 2) Combined value descending
        convictions.sort(key=lambda x: (x["whales_count"], x["total_value"]), reverse=True)
        return convictions
