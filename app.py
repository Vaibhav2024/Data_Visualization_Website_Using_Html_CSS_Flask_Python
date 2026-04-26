import os
import uuid
from flask import Flask, render_template, request, send_file, session, flash, redirect, url_for
import pandas as pd
import requests
import io
import plotly.express as px
import plotly.io as pio

app = Flask(__name__)
app.secret_key = 'super_secret_key_for_flash_messages'

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def get_session_file():
    session_id = session.get('session_id')
    if not session_id:
        return None
    filepath = os.path.join(UPLOAD_FOLDER, f"{session_id}.csv")
    if os.path.exists(filepath):
        return filepath
    return None

def save_to_session(df):
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    filepath = os.path.join(UPLOAD_FOLDER, f"{session['session_id']}.csv")
    df.to_csv(filepath, index=False)

def get_dataframe():
    filepath = get_session_file()
    if filepath:
        try:
            return pd.read_csv(filepath)
        except Exception:
            return None
    return None

def fetch_table(url, column_name=None):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
    }
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch webpage. Status code: {response.status_code}")

    html_io = io.StringIO(response.text)
    try:
        tables = pd.read_html(html_io)
    except ValueError as e:
        if "No tables found" in str(e):
            raise Exception("No tables found. This usually happens if the website loads data dynamically using JavaScript, or doesn't use standard HTML <table> tags.")
        raise e

    if column_name:
        for table in tables:
            if column_name in table.columns:
                return table
        raise Exception(f"Table with column '{column_name}' not found.")
    else:
        if len(tables) == 0:
            raise Exception("No tables found on the webpage.")
        return tables[0]

def get_profile(df):
    if df is None:
        return None
    rows, cols = df.shape
    missing = df.isnull().sum().to_dict()
    dtypes = df.dtypes.astype(str).to_dict()
    return {
        'rows': rows,
        'cols': cols,
        'missing': missing,
        'dtypes': dtypes
    }

@app.route("/", methods=["GET", "POST"])
def index():
    df = get_dataframe()
    df_html = df.to_html(classes="table table-striped", index=False) if df is not None else None
    
    if request.method == "POST":
        url = request.form.get("url")
        column_name = request.form.get("column_name")
        selected_columns = request.form.get("selected_columns")
        
        try:
            new_df = None
            if url:
                new_df = fetch_table(url, column_name)
            elif 'file' in request.files and request.files['file'].filename:
                file = request.files['file']
                if file.filename.endswith('.csv'):
                    new_df = pd.read_csv(file)
                else:
                    flash("Please upload a valid CSV file.", "error")
            
            if new_df is not None:
                if selected_columns:
                    columns = [col.strip() for col in selected_columns.split(",")]
                    missing_cols = [c for c in columns if c not in new_df.columns]
                    if missing_cols:
                        avail_cols = ", ".join(new_df.columns.tolist())
                        flash(f"Error: Columns {missing_cols} not found. Available columns are: [{avail_cols}]", "error")
                        return redirect(url_for('index'))
                    new_df = new_df[columns]
                
                save_to_session(new_df)
                flash("Data successfully loaded and saved to your session!", "success")
                return redirect(url_for('index'))
                
        except Exception as e:
            flash(f"An error occurred: {str(e)}", "error")
            return redirect(url_for('index'))

    return render_template("index.html", table_html=df_html)

@app.route("/data_cleaning", methods=["GET", "POST"])
def data_cleaning():
    df = get_dataframe()
    
    if request.method == "POST":
        action = request.form.get('action')
        
        if 'file' in request.files and request.files['file'].filename:
            file = request.files['file']
            if file.filename.endswith('.csv'):
                try:
                    new_df = pd.read_csv(file)
                    new_df.replace('none', pd.NA, inplace=True)
                    save_to_session(new_df)
                    flash("New dataset uploaded successfully!", "success")
                    return redirect(url_for('data_cleaning'))
                except Exception as e:
                    flash(f"Upload failed: {str(e)}", "error")
        
        elif action and df is not None:
            try:
                if action == 'remove_null_rows':
                    initial_rows = len(df)
                    df.dropna(inplace=True)
                    removed = initial_rows - len(df)
                    flash(f"Removed {removed} rows containing missing values.", "success")
                elif action == 'replace_null_with_mean':
                    df_mean = df.mean(numeric_only=True)
                    if df_mean.empty:
                        flash("No numeric columns found to calculate mean.", "error")
                    else:
                        df.fillna(df_mean, inplace=True)
                        flash("Replaced missing values with column means.", "success")
                elif action == 'remove_duplicates':
                    initial_rows = len(df)
                    df.drop_duplicates(inplace=True)
                    removed = initial_rows - len(df)
                    flash(f"Removed {removed} duplicate rows.", "success")
                
                save_to_session(df)
                return redirect(url_for('data_cleaning'))
            except Exception as e:
                flash(f"Cleaning error: {str(e)}", "error")

    profile = get_profile(df)
    df_html = df.to_html(classes="table table-striped", index=False) if df is not None else None
    
    return render_template("data_cleaning.html", table_html=df_html, profile=profile, has_data=(df is not None))

@app.route('/visualize', methods=['GET', 'POST'])
def visualize():
    df = get_dataframe()
    plot_html = None
    
    if request.method == 'POST':
        if 'csv_file' in request.files and request.files['csv_file'].filename:
            try:
                df = pd.read_csv(request.files['csv_file'])
                save_to_session(df)
                flash("New dataset loaded for visualization.", "success")
            except Exception as e:
                flash(f"Failed to read file: {str(e)}", "error")
                return redirect(url_for('visualize'))
        
        if df is None:
            flash("No data available. Please upload a file or extract a table first.", "error")
            return redirect(url_for('visualize'))
            
        plot_type = request.form.get('plot_type')
        x_column = request.form.get('x_column')
        y_column = request.form.get('y_column')
        hue_column = request.form.get('hue_column')
        bins = request.form.get('bins')

        if plot_type:
            cols_to_check = [c for c in [x_column, y_column, hue_column] if c]
            missing_cols = [c for c in cols_to_check if c not in df.columns]
            if missing_cols:
                avail = ", ".join(df.columns.tolist())
                flash(f"Error: Columns {missing_cols} not found in the dataset. Available columns: [{avail}]", "error")
                return redirect(url_for('visualize'))

            try:
                fig = None
                if plot_type == 'bar_plot':
                    if x_column and y_column: fig = px.bar(df, x=x_column, y=y_column)
                elif plot_type == 'line_plot':
                    if x_column and y_column: fig = px.line(df, x=x_column, y=y_column, color=hue_column if hue_column else None)
                elif plot_type == 'histogram':
                    if x_column: fig = px.histogram(df, x=x_column, nbins=int(bins) if bins else None)
                elif plot_type == 'scatter_plot':
                    if x_column and y_column: fig = px.scatter(df, x=x_column, y=y_column, color=hue_column if hue_column else None)
                elif plot_type == 'pie_chart':
                    if x_column: fig = px.pie(df, names=x_column)
                elif plot_type == 'box_plot':
                    if x_column and y_column: fig = px.box(df, x=x_column, y=y_column)
                elif plot_type == 'violin_plot':
                    if x_column and y_column: fig = px.violin(df, x=x_column, y=y_column)
                elif plot_type == 'kde':
                    if x_column: fig = px.histogram(df, x=x_column, marginal="violin")
                elif plot_type == 'pair_plot':
                    numeric_df = df.select_dtypes(include=['number'])
                    if numeric_df.empty:
                        flash("Pair plot requires numeric columns.", "error")
                    else:
                        fig = px.scatter_matrix(numeric_df)
                elif plot_type == 'heatmap':
                    numeric_df = df.select_dtypes(include=['number'])
                    if numeric_df.empty:
                        flash("Heatmap requires numeric columns.", "error")
                    else:
                        corr = numeric_df.corr()
                        fig = px.imshow(corr, text_auto=True)
                elif plot_type == 'count_plot':
                    if x_column: fig = px.histogram(df, x=x_column)
                
                if fig:
                    fig.update_layout(
                        template="plotly_dark",
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        font=dict(family="Outfit, sans-serif", color="#e2e8f0")
                    )
                    plot_html = pio.to_html(fig, full_html=False)
                else:
                    flash("Please provide the required columns for this plot type.", "error")
            except Exception as e:
                flash(f"Plotting error: {str(e)}", "error")

    return render_template('visualize.html', plot_html=plot_html, has_data=(df is not None))

@app.route("/download", methods=["GET", "POST"])
def download():
    filepath = get_session_file()
    if filepath and os.path.exists(filepath):
        return send_file(
            filepath,
            mimetype="text/csv",
            as_attachment=True,
            download_name="dataset.csv"
        )
    flash("No data available to download.", "error")
    return redirect(request.referrer or url_for('index'))

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
