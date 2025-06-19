import streamlit as st
import pdfplumber
import pandas as pd
import re
from io import BytesIO

# Page config
st.set_page_config(page_title="Invoice Data Extractor", layout="wide")

# Custom CSS for styling
st.markdown(
    """
    <style>
    .main > div {
        max-width: 900px;
        margin: auto;
    }
    h1 {
        color: #2E86C1;
        font-weight: 700;
    }
    .stButton > button {
        background-color: #117A65;
        color: white;
        font-weight: 600;
        border-radius: 8px;
        padding: 10px 25px;
    }
    .stDownloadButton > button {
        background-color: #148F77;
        color: white;
        font-weight: 600;
        border-radius: 8px;
        padding: 10px 25px;
    }
    .stFileUploader > label {
        font-weight: 600;
        font-size: 18px;
        color: #117A65;
    }
    </style>
    """, unsafe_allow_html=True
)

# Title and description
st.title("Invoice Data Extractor")
st.markdown("""
Upload your **EV Charging Invoice PDF** below.  
The app will extract detailed invoice entries, including dates, prices, and more.  
You can view the data and download it as an Excel file.  
""")

uploaded_file = st.file_uploader("Choose your invoice PDF", type=["pdf"], label_visibility="visible")

if uploaded_file:
    with st.spinner("⏳ Processing your invoice..."):
        data = []

        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue
                lines = text.split('\n')
                i = 0
                while i < len(lines) - 2:
                    line1 = lines[i].strip()
                    line2 = lines[i + 1].strip()
                    line3 = lines[i + 2].strip()

                    match = re.match(r'^(Home Charging Basic.*?)\s+(\d{2}\.\d{2}\.\d{4}) - (\d{2}\.\d{2}\.\d{4})$', line1)
                    if match and \
                       re.match(r'^\d+ St [\d,]+ [\d,]+$', line2) and \
                       "Ladepunktnummer:" in line3:

                        beschreibung = match.group(1)
                        startdatum = match.group(2)
                        enddatum = match.group(3)

                        menge, preis, betrag = re.findall(r'([\d,]+)', line2)

                        ladepunktnummer_match = re.search(r'Ladepunktnummer:\s*(\S+)', line3)
                        vermerk_match = re.search(r'Vermerk:\s*(.*)', line3)

                        ladepunktnummer = ladepunktnummer_match.group(1) if ladepunktnummer_match else ""
                        vermerk = vermerk_match.group(1) if vermerk_match else ""

                        data.append({
                            "Beschreibung": beschreibung,
                            "Startdatum": startdatum,
                            "Enddatum": enddatum,
                            "Menge": "1",
                            "Preis pro Einheit (EUR)": preis.replace(',', '.'),
                            "Betrag in EUR": betrag.replace(',', '.'),
                            "Ladepunktnummer": ladepunktnummer,
                            "Vermerk": vermerk
                        })
                        i += 3
                    else:
                        i += 1

        if data:
            df = pd.DataFrame(data)

            # Convert price columns to numeric for formatting
            df["Preis pro Einheit (EUR)"] = pd.to_numeric(df["Preis pro Einheit (EUR)"], errors='coerce')
            df["Betrag in EUR"] = pd.to_numeric(df["Betrag in EUR"], errors='coerce')

            st.success(f"✅ Successfully extracted {len(df)} entries.")
            st.dataframe(df.style.format({
                "Preis pro Einheit (EUR)": "{:.2f}",
                "Betrag in EUR": "{:.2f}"
            }), height=400)

            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='InvoiceData')
            output.seek(0)

            st.download_button(
                label="📥 Download Excel",
                data=output,
                file_name="extracted_invoice_data.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.warning("⚠️ No matching invoice data found. Please check your PDF.")
else:
    st.info("ℹ️ Please upload a PDF invoice file to get started.")
