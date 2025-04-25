from playground.pdf_parser import PDFParser

parser = PDFParser(
    "./pdfs/alz-13509.pdf", model="mistralai/Mistral-7B-Instruct-v0.1", tokenLimit=8192
)
parser.initialize_generator()
jsonObj = parser.to_json()
