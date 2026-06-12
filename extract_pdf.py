try:
    from PyPDF2 import PdfReader
    print("Using PyPDF2...")
    with open('SenAI_Advanced_Technical_Test.pdf', 'rb') as f:
        reader = PdfReader(f)
        for i, page in enumerate(reader.pages):
            print(f'--- Page {i+1} ---')
            text = page.extract_text()
            print(text)
            print("\n")
except ImportError:
    print('PyPDF2 not installed, trying pdfplumber...')
    try:
        import pdfplumber
        with pdfplumber.open('SenAI_Advanced_Technical_Test.pdf') as pdf:
            for i, page in enumerate(pdf.pages):
                print(f'--- Page {i+1} ---')
                text = page.extract_text()
                print(text)
                print("\n")
    except ImportError:
        print('pdfplumber not installed either')
        import subprocess
        result = subprocess.run(['pdftotext', 'SenAI_Advanced_Technical_Test.pdf', '-'], capture_output=True, text=True)
        print(result.stdout)
