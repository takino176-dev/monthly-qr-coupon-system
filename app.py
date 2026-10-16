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
            # Read CSV file with UTF-8 encoding for Amharic characters
            stream = io.TextIOWrapper(file.stream, encoding='utf-8')
            csv_reader = csv.DictReader(stream)
            
            employees = []
            for row in csv_reader:
                employees.append(row)
                
            return render_template('print_coupons.html', employees=employees)
            
    return render_template('upload.html')

if __name__ == '__main__':
    app.run(debug=True)