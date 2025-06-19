import streamlit as st
import pdfplumber
import pandas as pd
import re
from io import BytesIO

# Page config
st.set_page_config(page_title="Invoice Data Extractor", layout="wide")

# App title
st.title("Invoice Data Extractor")
st.markdown("""
Use this tool to upload EV Charging invoice PDFs and extract billing information.
Choose between automatic extraction or a custom column match.
""")

# Tabs for two modes
tab1, tab2 = st.tabs(["📤 Upload Invoice", "📝 Custom Column Extractor"])

with tab1:
    st.subheader("Automatic Extraction")
    uploaded_file = st.file_uploader("Upload your invoice PDF", type=["pdf"])

    if uploaded_file:
        with st.spinner("Processing invoice..."):
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
                df["Preis pro Einheit (EUR)"] = pd.to_numeric(df["Preis pro Einheit (EUR)"], errors='coerce')
                df["Betrag in EUR"] = pd.to_numeric(df["Betrag in EUR"], errors='coerce')

                st.success(f"Extracted {len(df)} entries.")
                st.dataframe(df.style.format({
                    "Preis pro Einheit (EUR)": "{:.2f}",
                    "Betrag in EUR": "{:.2f}"
                }), height=400)

                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='InvoiceData')
                output.seek(0)

                st.download_button("📥 Download as Excel", data=output, file_name="invoice_data.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            else:
                st.warning("No matching invoice data found.")

with tab2:
    st.subheader("Custom Column Extractor")
    st.write("Define keywords you'd like to extract from the invoice.")
    custom_file = st.file_uploader("Upload a PDF invoice", type=["pdf"], key="custom")

    keyword_input = st.text_area("Enter keywords or column names (one per line)", height=150)
    extract_button = st.button("Extract from PDF", key="extract")

    if extract_button and custom_file and keyword_input:
        keywords = [kw.strip() for kw in keyword_input.splitlines() if kw.strip()]

        with st.spinner("Scanning for keywords..."):
            results = []

            with pdfplumber.open(custom_file) as pdf:
                for page in pdf.pages:
                    lines = page.extract_text().split("\n")
                    for line in lines:
                        for kw in keywords:
                            if kw.lower() in line.lower():
                                results.append({"Keyword": kw, "Line": line})

            if results:
                results_df = pd.DataFrame(results)
                st.dataframe(results_df)
            else:
                st.info("No matching lines found for provided keywords.")
    elif extract_button:
        st.error("Please upload a PDF and enter at least one keyword.")

