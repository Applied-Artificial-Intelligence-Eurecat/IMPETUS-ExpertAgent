from pathlib import Path
import openparse
from openparse import TextElement, TableElement
import json

CHUNK_DUMP_PATH = "/app/other_data/chunk_inspection/chunks.json"
EXTRACTED_CATEGORIZED_NODES_PATH = "/app/other_data/categorized_nodes/extracted"
REVISED_CATEGORIZED_NODES_PATH = "/app/other_data/categorized_nodes/revised"

def get_unique_fontsize_examples(type_filtered_nodes):
    unique_fontsize_examples = {}
    
    for node in type_filtered_nodes:
        font_size = node['font_size']
        if font_size not in unique_fontsize_examples:
            unique_fontsize_examples[font_size] = node
    
    return list(unique_fontsize_examples.values())

def extract_texts_and_fonts_from_doc_elements(doc_elements):
    node_text_data = []
    for node in doc_elements.nodes:
        for element in node.elements:
            if isinstance(element, TextElement):
                texts_and_fonts = extract_texts_and_fonts_from_element(element) 
                node_text_data.extend(texts_and_fonts)
            elif isinstance(element, TableElement):
                node_text_data.extend([{"text":element.text, "type":"Table", "font_size":0, "page":element.bbox.page}])
            else:
                print("Node element not recognised")
    return node_text_data

def extract_texts_and_fonts_from_element(element):
    texts_and_fonts = []

    for line in element.lines:
        for span in line.spans:
            texts_and_fonts.append({
                'text':span.text.strip(),
                'font_size':span.size,
                'page':element.bbox.page,
                'type':"Text"
            })
    return texts_and_fonts

def merge_consecutive_text(data, has_category=False):
    merged_data = []
    current_text = ""
    current_font_size = None 
    current_pages = set()
    current_element_type = None

    for entry in data:
        text = entry['text'].strip()
        font_size = entry['font_size']
        page = entry['page'] 
        element_type = entry['type']
        category = None if not has_category else entry['category']

        
        if font_size == current_font_size:
            current_text += " " + text
            if not has_category:
                current_pages.add(page)
            else:
                current_pages.update(page)

        else:
            if current_text:
                current_entry = {
                    'text': current_text.strip(),
                    'font_size': current_font_size,
                    'page': sorted(list(current_pages)),
                    'type': current_element_type
                }
                if has_category:
                    current_entry['category'] = current_category
                merged_data.append(current_entry)

            current_text = text
            current_font_size = font_size
            current_pages = {page} if not has_category else set(page)
            current_element_type = element_type
            current_category = None if not has_category else category

    if current_text:
        current_entry = {
            'text': current_text.strip(),
            'font_size': current_font_size,
            'page': sorted(list(current_pages)),
            'type': current_element_type
        }
        if has_category:
            current_entry['category'] = current_category
        merged_data.append(current_entry)
    return merged_data

def filter_types(nodes, types):
    filtered_nodes = []
    for node in nodes:
        if node["type"] in types:
            filtered_nodes.append(node)
    return filtered_nodes

def categorize_nodes_parametrized(nodes, path_stem):
    with open(r'/app/other_data/files_fontsizes/files_font_categories.json') as f:
        pdf_parse_specifications = json.load(f)[path_stem]
    categories = pdf_parse_specifications['categories']
    categories = {float(k):v for k,v in categories.items()}
    filters = pdf_parse_specifications['filters']
    body_categories = pdf_parse_specifications['extended_body_text']
    font_bodytext = next(key for key, value in categories.items() if value == "BodyText")

    c_nodes = [
    {**node, 'category': categories[node['font_size']],
        'font_size': font_bodytext if categories[node['font_size']] in body_categories else node['font_size']}
    for node in nodes
    if categories[node['font_size']] not in filters
    ]
    return c_nodes

def categorize_nodes(nodes, filter = []):
    category_per_font_map = {
        18.0: "Header 1",
        15.96: "Header 2",
        14.04: "Header 3",
        12.0: "Header 4",
        11.04: "Bold text",
        10.56: "DOI",
        9.96: "Text",
        9.0: "Footer",
        6.48: "Superscript&Subscript",
        6 : "ReferenceNumber"
    }

    c_nodes = [
    {**node, 'category': category_per_font_map[node['font_size']],
        'font_size': 9.96 if category_per_font_map[node['font_size']] in ["Superscript&Subscript", "Bold text"] else node['font_size']}
    for node in nodes
    if category_per_font_map[node['font_size']] not in filter
    ]
    return c_nodes

def chunk_text_with_headers(data, pdf_path, min_chars, max_chars):
    headers = {}  
    chunks = []
    def split_text(text, min_len, max_len):
        if len(text) <= max_len:
            return [text]
        
        for i in range(min_len, max_len):
            if text[i] in '.!?;,':  
                return [text[:i + 1]] + split_text(text[i + 1:].strip(), min_len, max_len)
        
        return [text[:min_len]] + split_text(text[min_len:].strip(), min_len, max_len)
    
    def current_headers():
        return "\n".join(headers[level] for level in sorted(headers))
    
    for item in data:
        if item['category'].startswith('Header'):
            header_level = int(item['category'][-1])
            headers = {k: v for k, v in headers.items() if k <= header_level}  # Mantener solo los niveles de encabezado menores o iguales
            headers[header_level] = item['text']
        elif item['category'] == 'BodyText':
            text_chunks = split_text(item['text'], min_chars, max_chars)
            for chunk in text_chunks:
                chunks.append({'text':current_headers() + '\n' + chunk,
                                'pages':item['page'],
                                'pdf_path':pdf_path.stem})
    
    return chunks

def filter_chunks_by_text_reference(chunks, references):
    filtered_chunks = [chunk for chunk in chunks if all(ref not in chunk.get("text") for ref in references)]
    return filtered_chunks

def parse_pdf(pdf_path, min_chars=900, max_chars=1100):
    parser = openparse.DocumentParser(
        table_args={
                     "parsing_algorithm": "pymupdf",
                     "table_output_format": "markdown"
                 })

    node_text_data = []
    doc_elements_raw = parser.parse(pdf_path)
    node_text_data = extract_texts_and_fonts_from_doc_elements(doc_elements_raw)
    merged_nodes = merge_consecutive_text(node_text_data)
    type_filtered_nodes = filter_types(merged_nodes, types=["Text"])


    categorized_nodes = categorize_nodes(type_filtered_nodes, filter=["Footer"])
    chunks = chunk_text_with_headers(categorized_nodes, pdf_path=pdf_path, min_chars=min_chars,max_chars=max_chars)
    filtered_chunks = filter_chunks_by_text_reference(chunks, ["Table of contents", "Table of Contents"])

    with open(CHUNK_DUMP_PATH, 'w') as f:
        json.dump(categorized_nodes, f, indent=2)

    return filtered_chunks

def categorize_nodes_from_document(pdf_path):
    parser = openparse.DocumentParser(
        table_args={
                     "parsing_algorithm": "pymupdf",
                     "table_output_format": "markdown"
                 })

    node_text_data = []
    doc_elements_raw = parser.parse(pdf_path)
    node_text_data = extract_texts_and_fonts_from_doc_elements(doc_elements_raw)
    merged_nodes = merge_consecutive_text(node_text_data)
    type_filtered_nodes = filter_types(merged_nodes, types=["Text"])
    with open(r"/app/other_data/files_fontsizes/type_filtered_nodes_dump.json", "w") as f:
        json.dump(type_filtered_nodes, f, indent=2)
    categorized_nodes = categorize_nodes_parametrized(type_filtered_nodes, pdf_path.stem)
    with open(Path(EXTRACTED_CATEGORIZED_NODES_PATH).joinpath(pdf_path.stem + '_extracted.json'), 'w') as f:
        json.dump(categorized_nodes, f, indent=2)
    return categorized_nodes

def convert_nodes_to_chunks(extracted_nodes_path, pdf_path, categorized_nodes, min_chars=900, max_chars=1100):
    if extracted_nodes_path:
        with open(extracted_nodes_path, 'r') as f:
            categorized_nodes = json.load(f)
    chunks = chunk_text_with_headers(categorized_nodes, pdf_path=pdf_path, min_chars=min_chars,max_chars=max_chars)
    filtered_chunks = filter_chunks_by_text_reference(chunks, ["Table of contents", "Table of Contents"])

    return filtered_chunks

def chunk_directory(directory_path, min_chars=900, max_chars=1100):
    extracted_stem_files = [file.stem for file in Path(EXTRACTED_CATEGORIZED_NODES_PATH).iterdir()]
    revised_stem_files = [file.stem for file in Path(REVISED_CATEGORIZED_NODES_PATH).iterdir()]

    chunks = []
    for pdf_filename in list(Path(directory_path).rglob('*.pdf')):
        pdf_stem = pdf_filename.stem
        if pdf_stem + "_revised" in revised_stem_files:
            print('Getting revised nodes from ', pdf_stem)
            revised_nodes_path = Path(REVISED_CATEGORIZED_NODES_PATH).joinpath(pdf_stem + '_revised.json')
            chunks.extend(convert_nodes_to_chunks(revised_nodes_path, pdf_filename, categorized_nodes=None, min_chars=min_chars, max_chars=max_chars))
        elif pdf_stem + "_extracted" in extracted_stem_files:
            print('Getting extracted nodes from ', pdf_stem)
            extracted_nodes_path = Path(EXTRACTED_CATEGORIZED_NODES_PATH).joinpath(pdf_stem + '_extracted.json')
            chunks.extend(convert_nodes_to_chunks(extracted_nodes_path, pdf_filename, categorized_nodes=None, min_chars=min_chars, max_chars=max_chars))
        else: 
            print("Extracting nodes from", pdf_filename)
            categorized_nodes = categorize_nodes_from_document(pdf_filename)
            chunks.extend(convert_nodes_to_chunks(None, pdf_filename, categorized_nodes, min_chars=min_chars, max_chars=max_chars))

    return chunks