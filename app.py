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
            try:
                # Wrap file read into BytesIO for openpyxl
                file_stream = io.BytesIO(file.read())
                wb = openpyxl.load_workbook(file_stream)
                sheet = wb.active
                
                # Get headers from the first row and normalize them to lowercase
                headers = [str(cell.value).strip().lower() for cell in sheet[1] if cell.value is not None]
                
                employees = []
                for row in sheet.iter_rows(min_row=2, values_only=True):
                    row_dict = {}
                    for i, header in enumerate(headers):
                        if i < len(row) and row[i] is not None:
                            row_dict[header] = str(row[i]).strip()
                        else:
                            row_dict[header] = ""
                    
                    if any(row_dict.values()):
                        employees.append(row_dict)
                        
                return render_template('print_coupons.html', employees=employees)
            except Exception as e:
                return f"Error: {str(e)}", 500
                
    return render_template('upload.html')

if __name__ == '__main__':
    app.run(debug=True)