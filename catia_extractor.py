import os
import glob
import re
import pandas as pd
try:
    import win32com.client
    import pythoncom
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

def extract_part_info_catia(catia_app, drawing_path):
    filename = os.path.basename(drawing_path)
    part_no_match = re.match(r'^([A-Za-z0-9-]+)', filename)
    fallback_part_no = part_no_match.group(1) if part_no_match else 'Unknown'
    fallback_desc = filename.replace('.CATDrawing', '').replace(fallback_part_no, '').strip()

    parts = []
    try:
        # CATIA needs the full absolute path
        abs_path = os.path.abspath(drawing_path)
        doc = catia_app.Documents.Open(abs_path)
        drawing = doc.DrawingRoot
        
        all_texts = []
        table_data = []
        standalone_texts = []
        
        for sheet in drawing.Sheets:
            for view in sheet.Views:
                # 1. Look for native CATIA Tables
                try:
                    for table in view.Tables:
                        rows = table.NumberOfRows
                        cols = table.NumberOfColumns
                        for r in range(1, rows + 1):
                            row_text = []
                            for c in range(1, cols + 1):
                                try:
                                    cell_text = table.GetCellString(r, c).replace('\n', ' ').replace('\r', '').strip()
                                    row_text.append(cell_text)
                                except:
                                    row_text.append("")
                            table_data.append(row_text)
                            all_texts.append(" ".join(row_text))
                except Exception:
                    pass
                
                # 2. Look for standalone texts
                try:
                    for text in view.Texts:
                        t_val = text.Text.replace('\n', ' ').replace('\r', '').strip()
                        if t_val:
                            all_texts.append(t_val)
                            standalone_texts.append({
                                'text': t_val,
                                'x': text.x,
                                'y': text.y
                            })
                except Exception:
                    pass

        # === DEBUG DUMP ===
        debug_dump_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug_dump.txt")
        with open(debug_dump_path, "a", encoding="utf-8") as dump_file:
            dump_file.write(f"\n\n--- DUMP FOR {filename} ---\n")
            dump_file.write("TABLE DATA:\n")
            for r in table_data:
                dump_file.write(str(r) + "\n")
            dump_file.write("\nSTANDALONE TEXTS:\n")
            for t in standalone_texts:
                dump_file.write(f"{t['text']} (x={t['x']}, y={t['y']})\n")
            dump_file.write("\nALL TEXTS:\n")
            dump_file.write(" \n ".join(all_texts) + "\n")
        # ==================

        # Strategy 1: Parse table data natively if it has headers
        header_map = {}
        for i, row in enumerate(table_data):
            row_upper = [str(c).upper() for c in row]
            if any(x in " ".join(row_upper) for x in ["ITEM", "QTY", "QUANTITY", "MATERIAL", "MASS", "WEIGHT"]):
                for col_idx, cell in enumerate(row_upper):
                    if "QTY" in cell or "QUANTITY" in cell: header_map['Qty'] = col_idx
                    elif "ITEM" in cell: header_map['Item'] = col_idx
                    elif "MAT" in cell: header_map['Material'] = col_idx
                    elif "MASS" in cell or "WEIGHT" in cell: header_map['Weight'] = col_idx
                    elif "DESC" in cell or "PART" in cell: header_map['Description'] = col_idx
                    elif "SIZE" in cell: header_map['Size'] = col_idx
                    elif "PART" in cell and "NUM" in cell: header_map['Part No'] = col_idx
                
                if 'Qty' in header_map and len(header_map) >= 2:
                    for r in range(i + 1, len(table_data)):
                        data_row = table_data[r]
                        if not any(data_row): continue
                        
                        qty_str = data_row[header_map['Qty']] if 'Qty' in header_map and header_map['Qty'] < len(data_row) else "1"
                        try: 
                            qty_match = re.search(r'\d+', qty_str)
                            qty = int(qty_match.group()) if qty_match else 1
                        except: continue
                        
                        material = data_row[header_map['Material']] if 'Material' in header_map and header_map['Material'] < len(data_row) else ""
                        weight_str = data_row[header_map['Weight']] if 'Weight' in header_map and header_map['Weight'] < len(data_row) else "0"
                        desc = data_row[header_map['Description']] if 'Description' in header_map and header_map['Description'] < len(data_row) else fallback_desc
                        size = data_row[header_map['Size']] if 'Size' in header_map and header_map['Size'] < len(data_row) else ""
                        item_no = data_row[header_map['Item']] if 'Item' in header_map and header_map['Item'] < len(data_row) else ""
                        p_no = data_row[header_map['Part No']] if 'Part No' in header_map and header_map['Part No'] < len(data_row) else fallback_part_no
                        
                        weight = 0.0
                        if weight_str:
                            w_match = re.search(r'([\d.,]+)', weight_str)
                            if w_match:
                                try: weight = float(w_match.group(1).replace(',', '.'))
                                except: pass
                                
                        parts.append({
                            'Part No': p_no,
                            'Item': item_no,
                            'Description': desc,
                            'Material': material,
                            'Size': size,
                            'Qty': qty,
                            'Weight': weight,
                            'Source File': filename
                        })
                    break

        # Strategy 2: Coordinate-based Table Parser for standalone texts
        if not parts and standalone_texts:
            lines_dict = {}
            tolerance = 2.0
            for item in standalone_texts:
                y_rounded = round(item['y'] / tolerance) * tolerance
                if y_rounded not in lines_dict: lines_dict[y_rounded] = []
                lines_dict[y_rounded].append(item)
                
            sorted_y = sorted(lines_dict.keys(), reverse=True)
            header_y = None
            col_map = {}
            
            # Find Header Row
            for y in sorted_y:
                row_texts = [w['text'].upper() for w in lines_dict[y]]
                row_str = " ".join(row_texts)
                if ("QTY" in row_str or "QUANTITY" in row_str) and ("MATERIAL" in row_str or "MASS" in row_str or "WEIGHT" in row_str):
                    header_y = y
                    headers = sorted(lines_dict[y], key=lambda i: i['x'])
                    for h in headers:
                        txt = h['text'].upper()
                        if "PART" in txt and "NUM" in txt: col_map['Part No'] = h['x']
                        elif "ITEM" in txt: col_map['Item'] = h['x']
                        elif "QTY" in txt: col_map['Qty'] = h['x']
                        elif "DESC" in txt: col_map['Description'] = h['x']
                        elif "MAT" in txt: col_map['Material'] = h['x']
                        elif "SIZE" in txt: col_map['Size'] = h['x']
                        elif "MASS" in txt or "WEIGHT" in txt: col_map['Weight'] = h['x']
                    break
                    
            if col_map:
                # Parse Rows
                for y in sorted_y:
                    if y == header_y: continue
                    row_items = sorted(lines_dict[y], key=lambda i: i['x'])
                    row_data = {k: "" for k in col_map.keys()}
                    
                    for item in row_items:
                        closest_col = None
                        min_dist = 9999
                        for col_name, col_x in col_map.items():
                            dist = abs(item['x'] - col_x)
                            if dist < min_dist:
                                min_dist = dist
                                closest_col = col_name
                        
                        if closest_col and min_dist < 40:
                            if row_data[closest_col]:
                                row_data[closest_col] += " " + item['text']
                            else:
                                row_data[closest_col] = item['text']
                                
                # If valid row
                    if row_data.get('Qty') and (row_data.get('Part No') or row_data.get('Description') or row_data.get('Material')):
                        try: qty = int(re.search(r'\d+', row_data['Qty']).group())
                        except: continue
                        
                        p_no = row_data.get('Part No') or fallback_part_no
                        desc = row_data.get('Description', '')
                        mat = row_data.get('Material', '')
                        size = row_data.get('Size', '')
                        item_no = row_data.get('Item', '')
                        
                        weight = 0.0
                        w_str = row_data.get('Weight', '')
                        if w_str:
                            w_match = re.search(r'([\d.,]+)', w_str)
                            if w_match:
                                try: weight = float(w_match.group(1).replace(',', '.'))
                                except: pass
                                
                        parts.append({
                            'Part No': p_no,
                            'Item': item_no,
                            'Description': desc,
                            'Material': mat,
                            'Size': size,
                            'Qty': qty,
                            'Weight': weight,
                            'Source File': filename
                        })

        # Strategy 3: Fallback to single-part text extraction
        if not parts:
            full_text = " \n ".join(all_texts)
            if full_text.strip():
                material = ''
                qty = 1
                weight = 0.0
                
                mat_match = re.search(r'Material\s*:\s*([^\n\r]+)', full_text, re.IGNORECASE)
                if mat_match: material = mat_match.group(1).strip()
                    
                qty_match = re.search(r'Qty\s*:\s*(\d+)', full_text, re.IGNORECASE)
                if qty_match: qty = int(qty_match.group(1))
                    
                w_match = re.search(r'(?:Weight|Mass)\s*:\s*([\d.]+)', full_text, re.IGNORECASE)
                if w_match: weight = float(w_match.group(1))
                    
                parts.append({
                    'Part No': fallback_part_no,
                    'Item': '',
                    'Description': fallback_desc,
                    'Material': material,
                    'Size': '',
                    'Qty': qty,
                    'Weight': weight,
                    'Source File': filename
                })

        doc.Close()
        
    except Exception as e:
        print(f"Error reading {filename} in CATIA: {e}")

    return parts

def process_folder_catia(input_dir):
    if not HAS_WIN32:
        return None, "CATIA automation is only supported on Windows because it requires the pywin32 library and a local CATIA V5 software installation. It cannot run on a remote server like Vercel."

    catdrawing_files = glob.glob(os.path.join(input_dir, '*.CATDrawing'))
    if not catdrawing_files:
        return None, "No .CATDrawing files found in the specified directory."
        
    try:
        pythoncom.CoInitialize()
        catia = win32com.client.Dispatch("CATIA.Application")
        catia.Visible = True
    except Exception as e:
        return None, f"Could not connect to CATIA V5. Ensure it is installed and running. Error: {str(e)}"
        
    all_parts = []
    for f in catdrawing_files:
        parts = extract_part_info_catia(catia, f)
        all_parts.extend(parts)

    if not all_parts:
        return None, "No data could be extracted from the .CATDrawing files."

    df = pd.DataFrame(all_parts)
    
    # Ensure desired columns are included in aggregation
    group_cols = ['Part No', 'Description', 'Material']
    if 'Item' in df.columns: group_cols.append('Item')
    if 'Size' in df.columns: group_cols.append('Size')
    
    agg_df = df.groupby(group_cols, as_index=False).agg({
        'Qty': 'sum',
        'Weight': 'sum'
    })
    
    # Reorder columns to a logical BOM order
    final_cols = ['Item', 'Part No', 'Description', 'Size', 'Material', 'Qty', 'Weight']
    # Filter to only columns that exist
    final_cols = [c for c in final_cols if c in agg_df.columns]
    
    agg_df = agg_df[final_cols].sort_values(by=['Part No', 'Item'])
    
    output_file = os.path.join(input_dir, 'master_bom.xlsx')
    agg_df.to_excel(output_file, index=False)
    
    return output_file, f"Successfully processed {len(catdrawing_files)} CATIA drawings and generated the BOM!"
