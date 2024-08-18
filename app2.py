from flask import Flask, request, render_template, redirect, url_for
import pandas as pd
import io

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('data_cleaning.html')

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files['file']
    if file and file.filename.endswith('.csv'):
        df = pd.read_csv(file)
        table_data = df.head().to_html(classes='data', header="true")
        describe_stats = df.describe().to_html()
        return render_template('data_cleaning.html', table_data=table_data, describe_stats=describe_stats)
    return redirect(url_for('index'))

@app.route('/remove_null_rows', methods=['POST'])
def remove_null_rows():
    # Implement logic to remove rows with null values
    pass

@app.route('/replace_null_mean', methods=['POST'])
def replace_null_mean():
    # Implement logic to replace null values with mean
    pass

@app.route('/remove_duplicates', methods=['POST'])
def remove_duplicates():
    # Implement logic to remove duplicates
    pass

if __name__ == '__main__':
    app.run(debug=True)
