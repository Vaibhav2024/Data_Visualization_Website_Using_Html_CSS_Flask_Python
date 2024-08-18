from flask import Flask, render_template, request, send_file, make_response
import pandas as pd
import requests
from bs4 import BeautifulSoup
import io
import matplotlib.pyplot as plt
import seaborn as sns
import base64

app = Flask(__name__)
dataframe = None

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


@app.route('/visualize', methods=['GET', 'POST'])
def visualize():
    if request.method == 'POST':
        plot_type = request.form.get('plot_type')
        x_column = request.form.get('x_column')
        y_column = request.form.get('y_column')
        hue_column = request.form.get('hue_column')
        bins = request.form.get('bins')
        color = request.form.get('color')
        file = request.files.get('csv_file')

        if file:
            df = pd.read_csv(file)
        else:
            return "No file uploaded.", 400

        if plot_type:
            plt.figure(figsize=(10, 6))
            
            try:
                if plot_type == 'bar_plot':
                    if x_column and y_column:
                        sns.barplot(data=df, x=x_column, y=y_column, palette=color or 'viridis')
                        plt.xlabel(x_column)
                        plt.ylabel(y_column)
                        plt.title(f'Bar Plot of {y_column} by {x_column}')
                
                elif plot_type == 'line_plot':
                    if x_column and y_column:
                        sns.lineplot(data=df, x=x_column, y=y_column, hue=hue_column or None, palette=color or 'viridis')
                        plt.xlabel(x_column)
                        plt.ylabel(y_column)
                        plt.title(f'Line Plot of {y_column} vs {x_column}')
                
                elif plot_type == 'histogram':
                    if x_column and bins:
                        sns.histplot(df[x_column], bins=int(bins) if bins else 10, color=color or 'blue')
                        plt.xlabel(x_column)
                        plt.ylabel('Frequency')
                        plt.title(f'Histogram of {x_column}')
                
                elif plot_type == 'scatter_plot':
                    if x_column and y_column:
                        sns.scatterplot(data=df, x=x_column, y=y_column, hue=hue_column or None, palette=color or 'viridis')
                        plt.xlabel(x_column)
                        plt.ylabel(y_column)
                        plt.title(f'Scatter Plot of {y_column} vs {x_column}')
                
                elif plot_type == 'pie_chart':
                    if x_column:
                        df[x_column].value_counts().plot.pie(autopct='%1.1f%%', colors=sns.color_palette(color or 'pastel'))
                        plt.title(f'Pie Chart of {x_column}')
                
                elif plot_type == 'box_plot':
                    if x_column and y_column:
                        sns.boxplot(data=df, x=x_column, y=y_column, palette=color or 'viridis')
                        plt.xlabel(x_column)
                        plt.ylabel(y_column)
                        plt.title(f'Box Plot of {y_column} by {x_column}')
                
                elif plot_type == 'violin_plot':
                    if x_column and y_column:
                        sns.violinplot(data=df, x=x_column, y=y_column, palette=color or 'viridis')
                        plt.xlabel(x_column)
                        plt.ylabel(y_column)
                        plt.title(f'Violin Plot of {y_column} by {x_column}')
                
                elif plot_type == 'kde':
                    if x_column:
                        sns.kdeplot(df[x_column], color=color or 'blue')
                        plt.xlabel(x_column)
                        plt.title(f'KDE Plot of {x_column}')
                
                elif plot_type == 'pair_plot':
                    sns.pairplot(df, hue=hue_column or None, palette=color or 'viridis')
                    plt.title('Pair Plot')
                
                elif plot_type == 'heatmap':
                    corr = df.corr()
                    sns.heatmap(corr, annot=True, cmap=color or 'viridis')
                    plt.title('Heatmap of Correlation Matrix')
                
                elif plot_type == 'count_plot':
                    if x_column:
                        sns.countplot(data=df, x=x_column, palette=color or 'viridis')
                        plt.xlabel(x_column)
                        plt.ylabel('Count')
                        plt.title(f'Count Plot of {x_column}')
                
                else:
                    return "Invalid plot type.", 400

                # Save plot to a buffer
                buf = io.BytesIO()
                plt.savefig(buf, format='png')
                buf.seek(0)
                plot_data = buf.getvalue()
                buf.close()
                plt.close()

                plot_url = base64.b64encode(plot_data).decode('utf-8')

                return render_template('visualize.html', plot_url=plot_url)

            except Exception as e:
                return f"An error occurred: {str(e)}", 500

    return render_template('visualize.html')

@app.route("/download", methods=["POST"])
def download():
    csv_data = request.form.get("csv_data")

    return send_file(
        io.BytesIO(csv_data.encode()),
        mimetype="text/csv",
        as_attachment=True,
        download_name="table.csv"
    )

@app.route('/download_plot', methods=['POST'])
def download_plot():
    plot_url = request.form.get('plot_url')
    if not plot_url:
        return "No plot URL provided.", 400

    # Decode the base64 plot image
    plot_data = base64.b64decode(plot_url)

    return send_file(
        io.BytesIO(plot_data),
        mimetype='image/png',
        as_attachment=True,
        download_name='plot.png'
    )


@app.route("/data_cleaning", methods=["GET", "POST"])
def data_cleaning():
    global dataframe
    df_html = None
    csv_data = None
    
    if request.method == "POST":
        if 'file' in request.files and request.files['file'].filename:
            file = request.files['file']
            if file and file.filename.endswith('.csv'):
                try:
                    dataframe = pd.read_csv(file)
                    # Replace 'none' strings with actual NaN values
                    dataframe.replace('none', pd.NA, inplace=True)
                    
                    df_html = dataframe.to_html(classes="table table-striped", index=False)
                    
                    # Convert dataframe to CSV for download
                    csv_buffer = io.StringIO()
                    dataframe.to_csv(csv_buffer, index=False)
                    csv_data = csv_buffer.getvalue()  # Convert to string
                except Exception as e:
                    return f"An error occurred: {str(e)}"

        elif request.form.get('action') == 'remove_null_rows':
            if dataframe is not None:
                # Remove rows where any cell has NaN value (including 'none' replaced with NaN)
                dataframe.dropna(inplace=True)
                df_html = dataframe.to_html(classes="table table-striped", index=False)
                csv_buffer = io.StringIO()
                dataframe.to_csv(csv_buffer, index=False)
                csv_data = csv_buffer.getvalue()
        
        elif request.form.get('action') == 'replace_null_with_mean':
            if dataframe is not None:
                # Calculate mean of numeric columns only
                df_mean = dataframe.mean(numeric_only=True)
                # Replace NaN values with column mean
                dataframe.fillna(df_mean, inplace=True)
                df_html = dataframe.to_html(classes="table table-striped", index=False)
                csv_buffer = io.StringIO()
                dataframe.to_csv(csv_buffer, index=False)
                csv_data = csv_buffer.getvalue()
        
        elif request.form.get('action') == 'remove_duplicates':
            if dataframe is not None:
                # Remove duplicate rows
                dataframe.drop_duplicates(inplace=True)
                df_html = dataframe.to_html(classes="table table-striped", index=False)
                csv_buffer = io.StringIO()
                dataframe.to_csv(csv_buffer, index=False)
                csv_data = csv_buffer.getvalue()
    
    return render_template(
        "data_cleaning.html",
        table_html=df_html,
        csv_data=csv_data
    )

if __name__ == '__main__':
    app.run(debug=True)
