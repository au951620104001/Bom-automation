import glob
import pdfplumber

pdf_files = glob.glob('*.pdf')[:5]  # Just check first 5
for pdf_path in pdf_files:
    print(f"\n--- {pdf_path} ---")
    with pdfplumber.open(pdf_path) as pdf:
        if pdf.pages:
            text = pdf.pages[0].extract_text()
            if text:
                lines = text.split('\n')
                print('\n'.join(lines[:6]))  # Print first 6 lines
