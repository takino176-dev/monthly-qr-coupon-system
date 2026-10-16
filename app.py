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
            # Load the Excel workbook directly from the uploaded file stream
            wb = openpyxl.load_workbook(file)
            sheet = wb.active
            
            # Get headers from the first row and normalize them to lowercase
            headers = [str(cell.value).strip().lower() for cell in sheet[1] if cell.value is not None]
            
            employees = []
            # Read rows starting from row 2
            for row in sheet.iter_rows(min_row=2, values_only=True):
                row_dict = {}
                for i, header in enumerate(headers):
                    if i < len(row) and row[i] is not None:
                        row_dict[header] = str(row[i]).strip()
                    else:
                        row_dict[header] = ""
                
                # Append only if row has data
                if any(row_dict.values()):
                    employees.append(row_dict)
                    
            return render_template('print_coupons.html', employees=employees)
            
    return render_template('upload.html')

if __name__ == '__main__':
    app.run(debug=True)