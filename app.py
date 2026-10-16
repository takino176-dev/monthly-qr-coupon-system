import csv
import io
import openpyxl
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
            filename = file.filename.lower()
            try:
                employees = []
                if filename.endswith('.xlsx'):
                    # Read modern Excel .xlsx files directly
                    wb = openpyxl.load_workbook(file)
                    sheet = wb.active
                    headers = [str(cell.value).strip().lower() for cell in sheet[1] if cell.value is not None]
                    
                    for row in sheet.iter_rows(min_row=2, values_only=True):
                        row_dict = {}
                        for i, header in enumerate(headers):
                            if i < len(row) and row[i] is not None:
                                row_dict[header] = str(row[i]).strip()
                            else:
                                row_dict[header] = ""
                        if any(row_dict.values()):
                            employees.append(row_dict)
                else:
                    # Fallback for CSV / text files
                    stream = io.TextIOWrapper(file.stream, encoding='utf-8-sig', errors='replace')
                    csv_reader = csv.DictReader(stream)
                    for row in csv_reader:
                        cleaned_row = {k.strip().lower(): v.strip() for k, v in row.items() if k and v}
                        if cleaned_row:
                            employees.append(cleaned_row)
                            
                return render_template('print_coupons.html', employees=employees)
            except Exception as e:
                return f"Error reading file: {str(e)}.<br><br><b>Tip:</b> Make sure your Excel file is saved as a modern <b>Excel Workbook (*.xlsx)</b>, not an old .xls file.", 500
                
    return render_template('upload.html')

if __name__ == '__main__':
    app.run(debug=True)