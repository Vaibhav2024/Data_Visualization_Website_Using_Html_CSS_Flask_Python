from flask import Flask, render_template, request, send_file, make_response
import pandas as pd
import requests
from bs4 import BeautifulSoup
import io
import matplotlib.pyplot as plt
import seaborn as sns
import base64

app = Flask(__name__)

def fetch_table(url, column_name=None):
    # Fetch the webpage
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'lxml')

    # Extract all tables from the webpage
    tables = pd.read_html(str(soup))

    # If column_name is provided, find the correct table
    if column_name:
        for table in tables:
            if column_name in table.columns:
                return table
    else:
        # Return the first table if no column name is specified
        return tables[0]

@app.route("/", methods=["GET", "POST"])
def index():
    df_html = None
    csv_data = None
    columns = None
    
    if request.method == "POST":
        url = request.form.get("url")
        column_name = request.form.get("column_name")
        selected_columns = request.form.get("selected_columns")
        
        if url:  # If URL is provided, fetch table from URL
            try:
                df = fetch_table(url, column_name)
                
                if selected_columns:
                    columns = [col.strip() for col in selected_columns.split(",")]
                    df = df[columns]
                
                # Convert dataframe to HTML
                df_html = df.to_html(classes="table table-striped", index=False)

                # Convert dataframe to CSV in memory for download
                csv_data = io.StringIO()
                df.to_csv(csv_data, index=False)
                csv_data.seek(0)

            except Exception as e:
                return f"An error occurred: {str(e)}"
        
        elif 'file' in request.files and request.files['file'].filename:  # If file is uploaded
            file = request.files['file']
            if file and file.filename.endswith('.csv'):
                try:
                    # Read CSV file into DataFrame
                    df = pd.read_csv(file)
                    
                    if selected_columns:
                        columns = [col.strip() for col in selected_columns.split(",")]
                        df = df[columns]
                    
                    # Convert dataframe to HTML
                    df_html = df.to_html(classes="table table-striped", index=False)

                    # Convert dataframe to CSV in memory for download
                    csv_data = io.StringIO()
                    df.to_csv(csv_data, index=False)
                    csv_data.seek(0)

                except Exception as e:
                    return f"An error occurred: {str(e)}"

    response = make_response(render_template("index.html", table_html=df_html, csv_data=csv_data))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route("/download", methods=["POST"])
def download():
    csv_data = request.form.get("csv_data")

    return send_file(
        io.BytesIO(csv_data.encode()),
        mimetype="text/csv",
        as_attachment=True,
        download_name="table.csv"
    )

@app.route('/visualize', methods=['GET', 'POST'])
def visualize():
    plot_url = None

    if request.method == 'POST':
        plot_type = request.form.get('plot_type')
        x_column = request.form.get('x_column')
        y_column = request.form.get('y_column')
        color = request.form.get('color')
        file = request.files.get('csv_file')

        if file:
            df = pd.read_csv(file)
        else:
            return "No file uploaded.", 400

        if plot_type:
            plt.figure(figsize=(10, 6))
            if plot_type == 'line_plot':
                sns.lineplot(data=df, x=x_column, y=y_column, color=color)
            elif plot_type == 'bar_plot':
                sns.barplot(data=df, x=x_column, y=y_column, color=color)
            elif plot_type == 'histogram':
                sns.histplot(df[x_column], color=color)
            elif plot_type == 'scatter_plot':
                sns.scatterplot(data=df, x=x_column, y=y_column, color=color)
            elif plot_type == 'pie_chart':
                df[x_column].value_counts().plot.pie(autopct='%1.1f%%', colors=sns.color_palette(color))
            elif plot_type == 'box_plot':
                sns.boxplot(data=df, x=x_column, color=color)
            elif plot_type == 'violin_plot':
                sns.violinplot(data=df, x=x_column, color=color)
            elif plot_type == 'kde':
                sns.kdeplot(df[x_column], color=color)
            elif plot_type == 'pair_plot':
                sns.pairplot(df)
            elif plot_type == 'heatmap':
                corr = df.corr()
                sns.heatmap(corr, annot=True, cmap='coolwarm')
            elif plot_type == 'count_plot':
                sns.countplot(data=df, x=x_column, color=color)
            else:
                return "Invalid plot type.", 400

            buf = io.BytesIO()
            plt.savefig(buf, format='png')
            buf.seek(0)
            plot_url = base64.b64encode(buf.getvalue()).decode('utf-8')
            buf.close()
            plt.close()

    return render_template('visualize.html', plot_url=plot_url)

if __name__ == "__main__":
    app.run(debug=True)
