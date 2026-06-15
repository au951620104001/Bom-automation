import pdfplumber

pdf_path = "0202 Frame Tapak Tangki.pdf"
print("--- EXTRACTING TEXT ---")
with pdfplumber.open(pdf_path) as pdf:
    page = pdf.pages[0]
    print(page.extract_text())

print("\n--- EXTRACTING TABLES ---")
with pdfplumber.open(pdf_path) as pdf:
    page = pdf.pages[0]
    tables = page.extract_tables()
    print(f"Found {len(tables)} tables")
    for i, table in enumerate(tables):
        print(f"Table {i}:")
        for row in table:
            print(row)
