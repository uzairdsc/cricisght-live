import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from io import BytesIO
import boto3
from botocore.exceptions import NoCredentialsError
import zipfile
import os
import time

# Set your custom password here
APP_PASSWORD = st.secrets["auth"]["password"]

# Session state for authentication
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("⭐ Live - Private Cricket App Login")
    password_input = st.text_input("Enter Access Password:", type="password")

    if password_input == APP_PASSWORD:
        st.success("Access granted.")
        st.session_state.authenticated = True
        st.rerun()
    elif password_input:
        st.error("Invalid password. Try again.")
    st.stop()

# Import your plotting methods
from SpikeUpd import spike_graph_plot as spike_plot_custom, spike_graph_plot_descriptive
from WagonUpd import wagon_zone_plot, wagon_zone_plot_descriptive
from DismissalPlot import dismissal_plot

st.set_page_config(page_title="Live Cricket Wagon Wheel App" ,page_icon="🏏" ,layout="wide")
st.title("🏏 Live - Wagons Analysis Dashboard")


def normalize_data(df):
    """Convert wagonX and wagonY to numeric to prevent type errors in plotting"""
    if df is None:
        return None
    
    df = df.copy()
    
    # Fill NaN values in wagonX and wagonY with 0.0 (represents dot balls)
    if 'wagonX' in df.columns:
        df['wagonX'] = df['wagonX'].fillna(0.0)
    if 'wagonY' in df.columns:
        df['wagonY'] = df['wagonY'].fillna(0.0)
    
    # Convert wagonX and wagonY to numeric (handles strings, ints, floats)
    if 'wagonX' in df.columns:
        df['wagonX'] = pd.to_numeric(df['wagonX'], errors='coerce')
    if 'wagonY' in df.columns:
        df['wagonY'] = pd.to_numeric(df['wagonY'], errors='coerce')
    
    return df


@st.cache_data(ttl=60)  # Cache for 1 min
def load_from_s3(bucket_name, file_key, aws_access_key, aws_secret_key, region_name='us-east-1'):
    """Load CSV from S3 bucket"""
    try:
        s3_client = boto3.client(
            's3',
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=region_name
        )
        
        with st.spinner(f"Loading data from S3: {file_key}..."):
            obj = s3_client.get_object(Bucket=bucket_name, Key=file_key)
            df = pd.read_csv(obj['Body'], low_memory=False, )
            df = normalize_data(df)  # Ensure wagonX/Y are numeric
            st.success(f"Loaded {len(df)} rows from S3")
            return df
    except NoCredentialsError:
        st.error("AWS credentials not found. Check your secrets.toml file.")
        return None
    except Exception as e:
        st.error(f"Error loading from S3: {str(e)}")
        return None
    
# zip files of figures
def create_zip_of_plots(figures_dict):
    """
    Create a ZIP file containing all generated plots
    
    Args:
        figures_dict: Dictionary with format {'filename': figure_object}
    
    Returns:
        BytesIO object containing the ZIP file
    """
    zip_buffer = BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for filename, fig in figures_dict.items():
            if fig is not None:
                # Save figure to a BytesIO buffer
                img_buffer = BytesIO()
                
                # Determine if transparent based on filename
                is_transparent = 'transparent' in filename.lower()
                
                fig.savefig(img_buffer, format='png', transparent=is_transparent, 
                           dpi=300, bbox_inches='tight')
                img_buffer.seek(0)
                
                # Add to ZIP with .png extension
                png_filename = f"{filename}.png"
                zip_file.writestr(png_filename, img_buffer.getvalue())
                img_buffer.close()
    
    zip_buffer.seek(0)
    return zip_buffer

# ===== Dataset Selection =====
st.sidebar.header("📂 Select Dataset Source")
# data_source = st.sidebar.selectbox(
#     "Choose data source:",
#     ["Upload Data File", "S3_since24", "S3_PSL-26", "S3_all", "Cache_all", "Cache_since24"]
# )

# Remove the selectbox - just use default
DEFAULT_DATA_SOURCE = "S3_Live-bbb"

# Initialize session state for df
if 'df' not in st.session_state:
    st.session_state.df = None

df = st.session_state.df

# Initialize title_components early so it's available to batch section
if 'title_components' not in st.session_state:
    st.session_state.title_components = ['title', 'filters']
title_components = st.session_state.title_components

# ===== INITIALIZE FILTER SESSION STATE (before batch section) =====
# This prevents filters from being overwritten when main app logic reruns
if 'filter_competition' not in st.session_state:
    st.session_state['filter_competition'] = None
if 'filter_team_bat' not in st.session_state:
    st.session_state['filter_team_bat'] = None
if 'filter_team_bowl' not in st.session_state:
    st.session_state['filter_team_bowl'] = None
if 'filter_inns' not in st.session_state:
    st.session_state['filter_inns'] = None
if 'filter_match' not in st.session_state:
    st.session_state['filter_match'] = None
if 'filter_bowler' not in st.session_state:
    st.session_state['filter_bowler'] = None
if 'filter_bowler_id' not in st.session_state:
    st.session_state['filter_bowler_id'] = None
if 'filter_bat_hand' not in st.session_state:
    st.session_state['filter_bat_hand'] = []
if 'filter_mcode' not in st.session_state:
    st.session_state['filter_mcode'] = None
if 'filter_ground' not in st.session_state:
    st.session_state['filter_ground'] = None
if 'filter_bowl_type' not in st.session_state:
    st.session_state['filter_bowl_type'] = None
if 'filter_bowl_kind' not in st.session_state:
    st.session_state['filter_bowl_kind'] = None
if 'filter_bowl_arm' not in st.session_state:
    st.session_state['filter_bowl_arm'] = None
if 'filter_over_values' not in st.session_state:
    st.session_state['filter_over_values'] = None
if 'filter_phase' not in st.session_state:
    st.session_state['filter_phase'] = None
if 'filter_phase_display' not in st.session_state:
    st.session_state['filter_phase_display'] = []
if 'date_range_filter' not in st.session_state:
    st.session_state['date_range_filter'] = (None, None)

if DEFAULT_DATA_SOURCE == "S3_Live-bbb":
    if "aws" in st.secrets:
        bucket = st.secrets["aws"]["bucket_name"]
        access_key = st.secrets["aws"]["access_key_id"]
        secret_key = st.secrets["aws"]["secret_access_key"]
        region = st.secrets["aws"].get("region_name", "ap-south-1")
        
        s3_file_key = st.sidebar.text_input(
            "Enter S3 file path:",
            value = "WWT20-26_1490682-Comm.csv"
            # value="PSL-26_1527563-Comm.csv"
            # value="PSL_26_bbb.csv"
        )
        
        # if st.sidebar.button("Load from S3", key="load_2025"):
        loaded_df = load_from_s3(bucket, s3_file_key, access_key, secret_key, region)
        if loaded_df is not None:
            st.session_state.df = loaded_df
            df = loaded_df
        
        # Show current loaded data info
        if st.session_state.df is not None:
            st.sidebar.info(f"Current data: {len(st.session_state.df):,} rows")
    else:
        st.sidebar.warning("⚠️ AWS credentials not configured in secrets.toml")


# if data_source == "Upload Data File":
#     uploaded_file = st.sidebar.file_uploader("Upload CSV File", type=["csv"])
#     if uploaded_file:
#         df = pd.read_csv(uploaded_file, low_memory=False)
#         df = normalize_data(df)  # Ensure wagonX/Y are numeric
#         st.session_state.df = df
#         st.sidebar.success(f"Loaded {len(df):,} rows")

# elif data_source == "S3_since24":
#     if "aws" in st.secrets:
#         bucket = st.secrets["aws"]["bucket_name"]
#         access_key = st.secrets["aws"]["access_key_id"]
#         secret_key = st.secrets["aws"]["secret_access_key"]
#         region = st.secrets["aws"].get("region_name", "ap-south-1")
        
#         s3_file_key = st.sidebar.text_input(
#             "Enter S3 file path:",
#             value="t20_bbb_since_2024.csv"
#         )
        
#         if st.sidebar.button("Load from S3", key="load_2025"):
#             loaded_df = load_from_s3(bucket, s3_file_key, access_key, secret_key, region)
#             if loaded_df is not None:
#                 st.session_state.df = loaded_df
#                 df = loaded_df
        
#         # Show current loaded data info
#         if st.session_state.df is not None:
#             st.sidebar.info(f"Current data: {len(st.session_state.df):,} rows")
#     else:
#         st.sidebar.warning("⚠️ AWS credentials not configured in secrets.toml")

# elif data_source == "S3_PSL-26":
#     if "aws" in st.secrets:
#         bucket = st.secrets["aws"]["bucket_name"]
#         access_key = st.secrets["aws"]["access_key_id"]
#         secret_key = st.secrets["aws"]["secret_access_key"]
#         region = st.secrets["aws"].get("region_name", "ap-south-1")
        
#         s3_file_key = st.sidebar.text_input(
#             "Enter S3 file path:",
#             value="PSL_26_bbb.csv"
#         )
        
#         if st.sidebar.button("Load from S3", key="load_2025"):
#             loaded_df = load_from_s3(bucket, s3_file_key, access_key, secret_key, region)
#             if loaded_df is not None:
#                 st.session_state.df = loaded_df
#                 df = loaded_df
        
#         # Show current loaded data info
#         if st.session_state.df is not None:
#             st.sidebar.info(f"Current data: {len(st.session_state.df):,} rows")
#     else:
#         st.sidebar.warning("⚠️ AWS credentials not configured in secrets.toml")


# elif data_source == "S3_all":
#     if "aws" in st.secrets:
#         bucket = st.secrets["aws"]["bucket_name"]
#         access_key = st.secrets["aws"]["access_key_id"]
#         secret_key = st.secrets["aws"]["secret_access_key"]
#         region = st.secrets["aws"].get("region_name", "ap-south-1")
        
#         s3_file_key = st.sidebar.text_input(
#             "Enter S3 file path:",
#             # value="t20_bbb.csv"
#             value="t20_bbb_wt20.csv"
#         )
        
#         if st.sidebar.button("Load from S3", key="load_complete"):
#             loaded_df = load_from_s3(bucket, s3_file_key, access_key, secret_key, region)
#             if loaded_df is not None:
#                 st.session_state.df = loaded_df
#                 df = loaded_df
        
#         # Show current loaded data info
#         if st.session_state.df is not None:
#             st.sidebar.info(f"Current data: {len(st.session_state.df):,} rows")
#     else:
#         st.sidebar.warning("⚠️ AWS credentials not configured in secrets.toml")
        
# elif data_source == "Cache_all":
#     local_file_path = st.sidebar.text_input(
#         "Enter local file path:",
#         value="E:/Cricket Related Projects/HG-Datasets/t20_bbb.csv"
#     )
    
#     if st.sidebar.button("Load from Local Storage", key="load_local_complete"):
#         try:
#             with st.spinner(f"Loading data from {local_file_path}..."):
#                 loaded_df = pd.read_csv(local_file_path, low_memory=False)
#                 loaded_df = normalize_data(loaded_df)  # Ensure wagonX/Y are numeric
#                 st.session_state.df = loaded_df
#                 df = loaded_df
#                 st.sidebar.success(f"Loaded {len(loaded_df):,} rows from local storage")
#         except FileNotFoundError:
#             st.sidebar.error(f"File not found: {local_file_path}")
#         except Exception as e:
#             st.sidebar.error(f"Error loading file: {str(e)}")
    
#     # Show current loaded data info
#     if st.session_state.df is not None:
#         st.sidebar.info(f"Current data: {len(st.session_state.df):,} rows")

# elif data_source == "Cache_since24":
#     local_file_path = st.sidebar.text_input(
#         "Enter local file path:",
#         value="E:/Cricket Related Projects/HG-Datasets/t20_bbb_since_2024.csv"
#     )
    
#     if st.sidebar.button("Load from Local Storage", key="load_local_complete"):
#         try:
#             with st.spinner(f"Loading data from {local_file_path}..."):
#                 loaded_df = pd.read_csv(local_file_path, low_memory=False)
#                 loaded_df = normalize_data(loaded_df)  # Ensure wagonX/Y are numeric
#                 st.session_state.df = loaded_df
#                 df = loaded_df
#                 st.sidebar.success(f"Loaded {len(loaded_df):,} rows from local storage")
#         except FileNotFoundError:
#             st.sidebar.error(f"File not found: {local_file_path}")
#         except Exception as e:
#             st.sidebar.error(f"Error loading file: {str(e)}")
    
#     # Show current loaded data info
#     if st.session_state.df is not None:
#         st.sidebar.info(f"Current data: {len(st.session_state.df):,} rows")

# Add a clear data button
# if st.session_state.df is not None:
#     if st.sidebar.button("🗑️ Clear Loaded Data"):
#         st.cache_data.clear()
#         st.session_state.df = None
#         st.rerun()
        

# Add refresh and clear data buttons
if st.session_state.df is not None:
    col_refresh, col_clear = st.sidebar.columns(2)
    
    with col_refresh:
        if st.sidebar.button("🔄 Refresh Data", key="refresh_data_btn"):
            st.cache_data.clear()
            st.rerun()
    
    with col_clear:
        if st.sidebar.button("🗑️ Clear Data", key="clear_data_btn"):
            st.cache_data.clear()
            st.session_state.df = None
            st.rerun()
        
# Add this after loading data
if st.session_state.df is not None:
    df_stats = st.session_state.df
    
    # Get the latest/max inning
    max_inns = int(df_stats['inns'].max())
    total_innings = df_stats['inns'].nunique()
    
    # Filter for that inning
    latest_inns_data = df_stats[df_stats['inns'] == max_inns]
    
    # For the recent/latest inning
    latest_inning = df['inns'].max()
    total_overs_in_latest = df[df['inns'] == latest_inning]['over'].max()
    
    # Get max overs in that inning
    # max_overs = int(latest_inns_data['oversActual'].max())
    max_overs = latest_inns_data['oversActual'].max()
    
    # Get unique teams batting in that inning
    unique_teams = sorted(latest_inns_data['team_bat'].dropna().unique())
    
    # Display in sidebar
    # st.sidebar.markdown("---")
    # st.sidebar.subheader("📊 Data Statistics")
    
    col_inns, col_overs = st.sidebar.columns(2)
    with col_inns:
        st.metric("Recent Inning", max_inns)
    with col_overs:
        st.metric("Recent Over Ball", f"{max_overs:.1f}")
    
    st.sidebar.write("**Batting Team in Inning " + str(max_inns) + ":**")
    for team in unique_teams:
        st.sidebar.markdown(f"## • {team}")
        # st.sidebar.write(f"  • {team}")
    
    col_total, col_toal_overs = st.sidebar.columns(2)
    with col_total:
        st.metric("Total Inninga", total_innings)
    with col_toal_overs:
        st.metric("Overs in Recent Inns", total_overs_in_latest)
    # # Optional: Show total rows and date range
    # st.sidebar.divider()
    # st.sidebar.write(f"**Total Records:** {len(df_stats):,}")
    # if 'date' in df_stats.columns:
    #     min_date = pd.to_datetime(df_stats['date']).min()
    #     max_date = pd.to_datetime(df_stats['date']).max()
    #     st.sidebar.write(f"**Date Range:** {min_date.date()} to {max_date.date()}")

# ===== BATCH PLOT GENERATION SECTION =====
if st.session_state.df is not None:
    st.sidebar.markdown("---")
    st.sidebar.header("📋 Batch Plot Generation")
    
    # Squad file upload
    # squad_file = st.sidebar.file_uploader(
    #     "Upload Squad File (Excel/CSV)", 
    #     type=["xlsx", "csv"],
    #     key="squad_upload"
    # )
    
    # squad_file = "data//2026-WT20-Squads.xlsx"
    # squad_file = "../data/daily_updated_t20_data/2026-WT20-Squads.xlsx"

    
    # # List of possible file paths (in order of preference)
    # possible_paths = [
    #     "data/S2026_PSL.xlsx",
    #     "data/S2026_IPL.xlsx",
    #     "../data/daily_updated_t20_data/S2026_PSL.xlsx",
    # ]

    # squad_file = None
    # for path in possible_paths:
    #     if os.path.exists(path):
    #         squad_file = path
    #         break

    # New Dropdown option
    # List of possible file paths (in order of preference)
    possible_paths = [
        "data/S2026_WWT20.xlsx",
        "data/S2026_PSL.xlsx",
        # "data/S2026_IPL.xlsx",
    ]

    # Find which files actually exist
    existing_squad_files = [path for path in possible_paths if os.path.exists(path)]

    if existing_squad_files:
        # Show dropdown to let user select
        selected_squad_path = st.sidebar.selectbox(
            "Select Squad File:",
            existing_squad_files,
            help="Choose which squad file to use for batch generation"
        )
        squad_file = selected_squad_path
        st.sidebar.success(f"✓ Selected: {squad_file}")
    else:
        st.sidebar.error("⚠️ No squad files found!")
        squad_file = None

    if squad_file:
        # Read squad file
        try:
            if squad_file.endswith('.xlsx'):
                squad_df = pd.read_excel(squad_file, sheet_name="Squads")
            else:
                squad_df = pd.read_csv(squad_file)
            
            st.sidebar.success(f"Loaded {len(squad_df)} players")
            
            # Get unique teams
            if 'Team' in squad_df.columns:
                teams = sorted(squad_df['Team'].unique())
                selected_squad_team = st.sidebar.selectbox(
                    "Select Team",
                    teams,
                    key="squad_team_select"
                )
                
                # Get PIDs for selected team
                if 'Bt-ID' in squad_df.columns:
                    team_pids = squad_df[squad_df['Team'] == selected_squad_team]['Bt-ID'].astype(str).tolist()
                    st.sidebar.info(f"{len(team_pids)} players in {selected_squad_team}")
                    
                    # Plot type selection
                    batch_plot_types = st.sidebar.multiselect(
                        "Select plots to generate:",
                    ["Wagon Wheel","Wagon Zone", "Dismissal Plot"],
                    # ["Wagon Wheel R", "Wagon Wheel", "Wagon Zone R", "Wagon Zone", "Dismissal Plot"],
                    )
                    
                    # Transparent option
                    batch_transparent = st.sidebar.checkbox(
                        "Generate Transparent Plots", 
                        value=False,
                        key="batch_transparent"
                    )
                    
                    # Apply filters option
                    apply_filters_to_batch = st.sidebar.checkbox(
                        "Apply current filters to batch",
                        value=True,
                        help="Use the same filters (Competition, Date, etc.) for all players",
                        key="batch_apply_filters"
                    )
                    
                    # Generate button
                    col_gen, col_term = st.sidebar.columns(2)
                    with col_gen:
                        generate_batch = st.button("🚀 Generate Batch Plots", type="primary", key="batch_generate_btn", use_container_width=True)
                    with col_term:
                        clear_batch = st.button("🛑 Clear Job", key="batch_clear_btn", use_container_width=True)
                    
                    # Handle clear batch button
                    if clear_batch:
                        st.session_state['batch_job_cleared'] = True
                        st.sidebar.info("✓ Batch job cleared. You can start a new one.")
                        st.rerun()
                    
                    if generate_batch:
                        if batch_plot_types:
                            # Ensure date column is datetime format
             
