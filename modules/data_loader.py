import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "Data"

class DataLoader:
    def __init__(self, pattern="TP_Qualifications_Merged"):
        # find the latest file matching pattern
        files = sorted(DATA_DIR.glob(f"*{pattern}*.xlsx"))
        if not files:
            raise FileNotFoundError(f"No file matching *{pattern}*.xlsx in {DATA_DIR}")
        self.file_path = files[-1]
        self.xls = pd.ExcelFile(self.file_path)
    
    def list_status_sheets(self):
        # sheets starting with Qual_
        return [s for s in self.xls.sheet_names if s.startswith("Qual_")]
    
    def load_status(self, status: str) -> pd.DataFrame:
        # map selection to sheet name
        mapping = {
            "Commencements": "Qual_Commenced",
            "In-training":   "Qual_In-training",
            "Completions":   "Qual_Completed"
        }
        sheet = mapping.get(status)
        if sheet not in self.xls.sheet_names:
            raise KeyError(f"Expected sheet {sheet} not in workbook")
        df = pd.read_excel(self.xls, sheet_name=sheet)
        return df
