import requests
import xml.etree.ElementTree as ET
import time

class SECConnector:
    def __init__(self):
        self.headers = {
            "User-Agent": "PerfectLife carlos@perfectlife.app"
        }
        
    def get_latest_13f_holdings(self, cik, whale_name="Whale"):
        """
        Fetches and parses the latest 13F-HR filing for a given CIK.
        Returns a list of parsed holdings, sorted by value in descending order.
        """
        try:
            # 1. Fetch company submissions to find latest 13F-HR
            url = f"https://data.sec.gov/submissions/CIK{cik.zfill(10)}.json"
            print(f"[{whale_name}] Fetching submissions from SEC...")
            res = requests.get(url, headers=self.headers, timeout=10)
            if res.status_code != 200:
                print(f"[{whale_name}] Error fetching submissions: {res.status_code}")
                return []
                
            data = res.json()
            recent_filings = data.get("filings", {}).get("recent", {})
            forms = recent_filings.get("form", [])
            acc_nums = recent_filings.get("accessionNumber", [])
            filing_dates = recent_filings.get("filingDate", [])
            report_dates = recent_filings.get("reportDate", [])
            
            # Find the latest 13F-HR
            found_idx = -1
            for i, form in enumerate(forms):
                if form == "13F-HR":
                    found_idx = i
                    break
                    
            if found_idx == -1:
                print(f"[{whale_name}] No 13F-HR filings found.")
                return []
                
            acc_num = acc_nums[found_idx]
            filing_date = filing_dates[found_idx]
            report_date = report_dates[found_idx] if report_dates else filing_date
            print(f"[{whale_name}] Latest 13F-HR: AccNum={acc_num}, FilingDate={filing_date}, ReportDate={report_date}")
            
            # 2. Fetch index of filing to find the XML file
            acc_num_no_hyphens = acc_num.replace("-", "")
            index_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc_num_no_hyphens}/index.json"
            
            # Rate limiter friendly delay
            time.sleep(0.1)
            
            res_index = requests.get(index_url, headers=self.headers, timeout=10)
            if res_index.status_code != 200:
                print(f"[{whale_name}] Error fetching filing directory: {res_index.status_code}")
                return []
                
            index_data = res_index.json()
            files = index_data.get("directory", {}).get("item", [])
            
            xml_file = None
            # Standard naming patterns for holdings XML
            for f in files:
                name = f.get("name", "").lower()
                if name.endswith(".xml") and ("table" in name or "infotable" in name or "13f" in name):
                    xml_file = f.get("name")
                    break
                    
            # Fallback to look for any XML that is not form13f primary doc
            if not xml_file:
                for f in files:
                    name = f.get("name", "").lower()
                    if name.endswith(".xml") and not name.startswith("form13f") and not name.startswith("primary_doc"):
                        xml_file = f.get("name")
                        break
                        
            if not xml_file:
                print(f"[{whale_name}] Could not locate holdings XML file.")
                return []
                
            # 3. Download and parse XML file
            xml_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc_num_no_hyphens}/{xml_file}"
            print(f"[{whale_name}] Downloading holdings XML from {xml_url}...")
            
            # Rate limiter friendly delay
            time.sleep(0.1)
            
            res_xml = requests.get(xml_url, headers=self.headers, timeout=15)
            if res_xml.status_code != 200:
                print(f"[{whale_name}] Error downloading XML: {res_xml.status_code}")
                return []
                
            print(f"[{whale_name}] Parsing XML content...")
            root = ET.fromstring(res_xml.content)
            
            # Find all infoTable elements using namespace wildcards
            nodes = root.findall('.//{*}infoTable')
            print(f"[{whale_name}] Found {len(nodes)} raw holding records.")
            
            aggregated = {}
            for node in nodes:
                name_node = node.find('.//{*}nameOfIssuer')
                class_node = node.find('.//{*}titleOfClass')
                cusip_node = node.find('.//{*}cusip')
                value_node = node.find('.//{*}value')
                shares_node = node.find('.//{*}sshPrnamt')
                
                name = name_node.text.strip().upper() if name_node is not None and name_node.text else "UNKNOWN"
                title = class_node.text.strip().upper() if class_node is not None and class_node.text else "COMMON STOCK"
                cusip = cusip_node.text.strip().upper() if cusip_node is not None and cusip_node.text else ""
                
                # SEC value is reported in thousands ($000s)
                val_thousands = float(value_node.text) if value_node is not None and value_node.text else 0.0
                value_usd = val_thousands * 1000.0
                
                shares = int(shares_node.text) if shares_node is not None and shares_node.text else 0
                
                if value_usd > 0:
                    # Agrupar por CUSIP (ou nome+classe se CUSIP estiver vazio) para evitar duplicatas institucionais
                    key = cusip if cusip else f"{name}_{title}"
                    if key in aggregated:
                        aggregated[key]["value"] += value_usd
                        aggregated[key]["shares"] += shares
                    else:
                        aggregated[key] = {
                            "name": name,
                            "class": title,
                            "cusip": cusip,
                            "value": value_usd,
                            "shares": shares
                        }
            
            holdings = list(aggregated.values())
            
            # Sort holdings by value descending
            holdings.sort(key=lambda x: x["value"], reverse=True)
            print(f"[{whale_name}] Successfully parsed and sorted {len(holdings)} valid holdings.")
            return holdings
            
        except Exception as e:
            print(f"[{whale_name}] Critical error parsing 13F: {e}")
            return []
