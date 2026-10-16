import csv
import io
from flask import Flask, render_template, request

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('upload.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        file = request.files.get('file')
        if file:
            content = file.read()
            
            # Try decoding utf-16 (Unicode Text) first, then fallback to utf-8-sig (CSV)
            try:
                decoded_text = content.decode('utf-16')
                delimiter = '\t'
            except (UnicodeDecodeError, Exception):
                decoded_text = content.decode('utf-8-sig', errors='replace')
                delimiter = ',' if ',' in decoded_text else '\t'
            
            # Read data dynamically
            stream = io.StringIO(decoded_text)
            csv_reader = csv.DictReader(stream, delimiter=delimiter)
            
            employees = []
            for row in csv_reader:
                # Clean headers and values safely
                cleaned_row = {
                    k.strip().lower(): v.strip() 
                    for k, v in row.items() 
                    if k is not None and v is not None
                }
                if cleaned_row:
                    employees.append(cleaned_row)
                
            return render_template('print_coupons.html', employees=employees)
            
    return render_template('upload.html')

if __name__ == '__main__':
    app.run(debug=True)