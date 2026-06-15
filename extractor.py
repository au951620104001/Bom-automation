import os
import glob
import re
import pdfplumber
import pandas as pd

def extract_lines(page, tolerance=2):
    words = page.extract_words()
    lines = {}
    for w in words:
        top = round(w['top'] / tolerance) * tolerance
        if top not in lines: lines[top] = []
        lines[top].append(w)
    sorted_lines = []
    for top in sorted(lines.keys()):
        words_in_line = sorted(lines[top], key=lambda x: x['x0'])
        sorted_lines.append(' '.join([w['text'] for w in words_in_line]))
    return sorted_lines

def extract_part_info(pdf_path):
    filename = os.path.basename(pdf_path)
    part_no_match = re.match(r'^([A-Za-z0-9-]+)', filename)
    fallback_part_no = part_no_match.group(1) if part_no_match else 'Unknown'
    fallback_desc = filename.replace('.pdf', '').replace(fallback_part_no, '').strip()

    parts = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            if not pdf.pages: return []
            
            # 1. Advanced Multi-Item Line Scanner for Assemblies
            lines = extract_lines(pdf.pages[0])
            for line in lines:
                # Find repeating pattern of [Item] [Qty] [Text...]
                matches = re.finditer(r'(?<![\w.-])(\d{1,3})\s+(\d+)\s+([A-Z].+?)(?=\s+(?:\d{1,3}\s+\d+\s+[A-Z]|$))', line)
                for match in matches:
                    qty = int(match.group(2))
                    rest = match.group(3).strip()
                    
                    # Extract weight from the end of the rest string
                    weight_match = re.search(r'([\d.,]+)$', rest)
                    weight = 0.0
                    material = ''
                    desc_partno = rest
                    
                    if weight_match:
                        weight_str = weight_match.group(1).replace(',', '.')
                        try: weight = float(weight_str)
                        except: pass
                        
                        desc_partno = rest[:weight_match.start()].strip()
                        
                        # Guess material (last word before weight)
                        words = desc_partno.split()
                        if len(words) > 1:
                            material = words[-1]
                            desc_partno = " ".join(words[:-1])
                            
                    parts.append({
                        'Part No': fallback_part_no, 
                        'Description': desc_partno,
                        'Material': material,
                        'Qty': qty,
                        'Weight': weight,
                        'Source File': filename
                    })
            
            # 2. If NO parts found from multi-item scanner, fallback to single-part text extraction
            if not parts:
                text = pdf.pages[0].extract_text()
                if text:
                    material = ''
                    qty = 1
                    weight = 0.0
                    
                    mat_match = re.search(r'Material\s*:\s*(.*)', text, re.IGNORECASE)
                    if mat_match: material = mat_match.group(1).strip()
                        
                    qty_match = re.search(r'Qty\s*:\s*(\d+)', text, re.IGNORECASE)
                    if qty_match: qty = int(qty_match.group(1))
                        
                    w_match = re.search(r'Weight\s*:\s*([\d.]+)', text, re.IGNORECASE)
                    if w_match: weight = float(w_match.group(1))
                        
                    parts.append({
                        'Part No': fallback_part_no,
                        'Description': fallback_desc,
                        'Material': material,
                        'Qty': qty,
                        'Weight': weight,
                        'Source File': filename
                    })
    except Exception as e:
        print(f"Error reading {filename}: {e}")

    return parts

def process_folder(input_dir):
    pdf_files = glob.glob(os.path.join(input_dir, '*.pdf'))
    if not pdf_files:
        return None, "No PDF files found in the specified directory."
        
    all_parts = []
    for pdf_file in pdf_files:
        parts = extract_part_info(pdf_file)
        all_parts.extend(parts)

    if not all_parts:
        return None, "No data could be extracted from the PDFs."

    df = pd.DataFrame(all_parts)
    
    # Aggregate data
    agg_df = df.groupby(['Part No', 'Description', 'Material'], as_index=False).agg({
        'Qty': 'sum',
        'Weight': 'sum'
    })
    
    agg_df = agg_df.sort_values(by='Part No')
    
    output_file = os.path.join(input_dir, 'master_bom.xlsx')
    agg_df.to_excel(output_file, index=False)
    
    return output_file, f"Successfully processed {len(pdf_files)} drawings and generated the BOM!"
