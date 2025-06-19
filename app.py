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


# --------------------- Shared Extraction Function ---------------------
def extract_structured_data(pdf_file):
    """Extracts structured invoice data from a given PDF file."""
    data = []
    with pdfplumber.open(pdf_file) as pdf:
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
    return pd.DataFrame(data)


# --------------------- TAB 1: Automatic Extraction ---------------------
with tab1:
    st.subheader("Automatic Extraction")
    uploaded_file = st.file_uploader("Upload your invoice PDF", type=["pdf"])

    if uploaded_file:
        with st.spinner("Processing invoice..."):
            df = extract_structured_data(uploaded_file)

        if not df.empty:
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


# --------------------- TAB 2: Custom Column Extractor ---------------------
with tab2:
    st.subheader("Custom Column Extractor")
    st.write("Enter the column names you'd like to include in the output (one per line).")
    custom_file = st.file_uploader("Upload a PDF invoice", type=["pdf"], key="custom")

    keyword_input = st.text_area("Enter column names (one per line)", height=150)
    extract_button = st.button("Extract Selected Columns", key="extract")

    if extract_button and custom_file and keyword_input:
        selected_columns = [kw.strip() for kw in keyword_input.splitlines() if kw.strip()]

        with st.spinner("Extracting and filtering data..."):
            df = extract_structured_data(custom_file)

        if not df.empty:
            # Filter only selected columns
            valid_cols = [col for col in selected_columns if col in df.columns]
            missing_cols = [col for col in selected_columns if col not in df.columns]

            if valid_cols:
                filtered_df = df[valid_cols]
                st.success(f"Extracted {len(filtered_df)} rows with {len(valid_cols)} selected columns.")
                st.dataframe(filtered_df)

                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    filtered_df.to_excel(writer, index=False, sheet_name='SelectedData')
                output.seek(0)

                st.download_button(
                    label="📥 Download Filtered Excel",
                    data=output,
                    file_name="filtered_invoice_data.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.warning("None of the entered column names matched the extracted data columns.")

            if missing_cols:
                st.info(f"The following columns were not found in the invoice data: {', '.join(missing_cols)}")
        else:
            st.warning("No invoice data found in the uploaded PDF.")
    elif extract_button:
        st.error("Please upload a PDF and enter at least one column name.")

