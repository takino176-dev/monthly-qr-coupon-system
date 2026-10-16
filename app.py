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
            # Read Unicode Text (tab-delimited) with utf-16 encoding
            stream = io.TextIOWrapper(file.stream, encoding='utf-16')
            csv_reader = csv.DictReader(stream, delimiter='\t')
            
            employees = []
            for row in csv_reader:
                cleaned_row = {k.strip().lower(): v.strip() for k, v in row.items() if k and v}
                employees.append(cleaned_row)
                
            return render_template('print_coupons.html', employees=employees)
            
    return render_template('upload.html')

if __name__ == '__main__':
    app.run(debug=True)