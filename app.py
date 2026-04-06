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
    st.title("⭐ PSL Live - Private Cricket App Login")
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

st.set_page_config(page_title="PSL Live Cricket Wagon Wheel App" ,page_icon="🏏" ,layout="wide")
st.title("🏏 PSL Live - Wagons Analysis Dashboard")


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
            value="PSL-26_1527565-Comm.csv"
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
        "data/S2026_PSL.xlsx",
        "data/S2026_IPL.xlsx",
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
                            if 'date' in df.columns and df['date'].dtype == 'object':
                                df['date'] = pd.to_datetime(df['date'])
                            
                            with st.spinner(f"Generating plots for {len(team_pids)} players..."):
                                all_batch_figures = {}
                                progress_bar = st.progress(0)
                                status_text = st.empty()
                                error_count = 0
                                success_count = 0
                                
                                for idx, pid in enumerate(team_pids):
                                    # Update progress
                                    progress = (idx + 1) / len(team_pids)
                                    progress_bar.progress(progress)
                                    
                                    # Get player name from Squad file
                                    player_row = squad_df[squad_df['Bt-ID'].astype(str) == str(pid)]
                                    if not player_row.empty and 'Player' in squad_df.columns:
                                        player_name = player_row['Player'].iloc[0]
                                        # Clean player name for filename (remove spaces, special chars)
                                        player_name = player_name.replace(" ", "_").replace("/", "_")
                                    else:
                                        player_name = f"Player_{pid}"
                                    
                                    # OLD LOGIC (commented out):
                                    # player_row = squad_df[squad_df['Bt-ID'] == str(pid)]
                                    # if not player_row.empty and 'Player' in squad_df.columns:
                                    #     player_name = player_row['Player'].iloc[0]
                                    # else:
                                    #     player_name = f"Player_{pid}"
                                    
                                    status_text.text(f"Generating: {player_name} ({idx+1}/{len(team_pids)})")
                                    
                                    # Set filters - get values from session state if apply_filters is checked
                                    if apply_filters_to_batch:
                                        # Get filter values from session state (these are set in main app)
                                        filter_comp = st.session_state.get('filter_competition', None)
                                        filter_comp_val = filter_comp
                                        
                                        filter_team_bat = st.session_state.get('filter_team_bat', None)
                                        filter_team_bat_val = filter_team_bat
                                        
                                        filter_team_bowl = st.session_state.get('filter_team_bowl', None)
                                        filter_team_bowl_val = filter_team_bowl
                                        
                                        filter_inns = st.session_state.get('filter_inns', None)
                                        filter_inns_val = filter_inns if filter_inns else None
                                        
                                        filter_match = st.session_state.get('filter_match', None)
                                        filter_match_val = filter_match if filter_match else None
                                        
                                        filter_bowler = st.session_state.get('filter_bowler', None)
                                        filter_bowler_val = filter_bowler
                                        
                                        filter_bowler_id = st.session_state.get('filter_bowler_id', None)
                                        filter_bowler_id_val = filter_bowler_id
                                        
                                        filter_bat_hand = st.session_state.get('filter_bat_hand', [])
                                        filter_bat_hand_val = filter_bat_hand if filter_bat_hand else None
                                        
                                        filter_mcode = st.session_state.get('filter_mcode', [])
                                        filter_mcode_val = filter_mcode if filter_mcode else None
                                        
                                        filter_ground = st.session_state.get('filter_ground', [])
                                        filter_ground_val = filter_ground if filter_ground else None
                                        
                                        filter_bowl_type = st.session_state.get('filter_bowl_type', [])
                                        filter_bowl_type_val = filter_bowl_type if filter_bowl_type else None
                                        
                                        filter_bowl_kind = st.session_state.get('filter_bowl_kind', [])
                                        filter_bowl_kind_val = filter_bowl_kind if filter_bowl_kind else None
                                        
                                        filter_bowl_arm = st.session_state.get('filter_bowl_arm', [])
                                        filter_bowl_arm_val = filter_bowl_arm if filter_bowl_arm else None
                                        
                                        filter_over_values = st.session_state.get('filter_over_values', [])
                                        filter_over_values_val = filter_over_values if filter_over_values else None
                                        
                                        filter_phase = st.session_state.get('filter_phase', [])
                                        filter_phase_val = filter_phase if filter_phase else None
                                        
                                        # Get date range from session state and convert to datetime
                                        date_range_state = st.session_state.get('date_range_filter', None)
                                        if date_range_state and len(date_range_state) == 2:
                                            # Convert date objects to datetime for plotting functions
                                            filter_date_from = pd.to_datetime(date_range_state[0])
                                            filter_date_to = pd.to_datetime(date_range_state[1])
                                        else:
                                            filter_date_from, filter_date_to = None, None
                                        
                                        batch_filters = {
                                            'competition': filter_comp_val,
                                            'date_from': filter_date_from,
                                            'date_to': filter_date_to,
                                            'inns': filter_inns_val,
                                            'mat_num': filter_match_val,
                                            'team_bat': filter_team_bat_val,
                                            'team_bowl': filter_team_bowl_val,
                                            'bowler_name': filter_bowler_val,
                                            'bowler_id': filter_bowler_id_val,
                                            'bat_hand': filter_bat_hand_val,
                                            'mcode': filter_mcode_val,
                                            'ground': filter_ground_val,
                                            'bowl_type': filter_bowl_type_val,
                                            'bowl_kind': filter_bowl_kind_val,
                                            'bowl_arm': filter_bowl_arm_val,
                                            'run_values': None,
                                            'over_values': filter_over_values_val,
                                            'phase': filter_phase_val,
                                            'title_components': title_components,
                                            'transparent': batch_transparent,
                                            'show_title': True,
                                            'show_summary': True,
                                            'show_legend': True,
                                            'runs_count': True,
                                            'show_fours_sixes': True,
                                            'show_control': True,
                                            'show_prod_shot': True,
                                            'show_bowler': True,
                                            'show_ground': True,
                                            'show_overs': True,
                                            'show_phase': True,
                                            'show_bowl_type': True,
                                            'show_bowl_kind': True,
                                            'show_bowl_arm': True 
                                        }
                                    else:
                                        batch_filters = {
                                            'competition': None,
                                            'date_from': None,
                                            'date_to': None,
                                            'inns': None,
                                            'mat_num': None,
                                            'team_bat': None,
                                            'team_bowl': None,
                                            'bowler_name': None,
                                            'bowler_id': None,
                                            'bat_hand': None,
                                            'mcode': None,
                                            'ground': None,
                                            'bowl_type': None,
                                            'bowl_kind': None,
                                            'bowl_arm': None,
                                            'run_values': None,
                                            'over_values': None,
                                            'phase': None,
                                            'title_components': title_components,
                                            'transparent': batch_transparent,
                                            'show_title': True,
                                            'show_summary': True,
                                            'show_legend': True,
                                            'runs_count': True,
                                            'show_fours_sixes': True,
                                            'show_control': True,
                                            'show_prod_shot': True,
                                            'show_bowler': True,
                                            'show_ground': True,
                                            'show_overs': True,
                                            'show_phase': True,
                                            'show_bowl_type': True,
                                            'show_bowl_kind': True,
                                            'show_bowl_arm': True,
                                        }
                                    
                                    # Generate selected plots
                                    try:
                                        if "Wagon Wheel R" in batch_plot_types:
                                            spike_filters = {k: v for k, v in batch_filters.items()}
                                            fig = spike_plot_custom(df=df, pid=pid, player_name=None, **spike_filters)
                                            if fig is not None:
                                                all_batch_figures[f"{player_name}_wagon_wheel.png"] = fig
                                                success_count += 1
                                        
                                        if "Wagon Wheel" in batch_plot_types:
                                            spike_filters = {k: v for k, v in batch_filters.items()}
                                            fig = spike_graph_plot_descriptive(df=df, pid=pid, player_name=None, **spike_filters)
                                            if fig is not None:
                                                all_batch_figures[f"{player_name}_wagon_wheel_desc.png"] = fig
                                                success_count += 1
                                        
                                        if "Wagon Zone R" in batch_plot_types:
                                            # Wagon plots don't have show_legend or show_ground parameters
                                            wagon_filters = {k: v for k, v in batch_filters.items() if k not in ['show_legend', 'show_ground']}
                                            fig = wagon_zone_plot(df=df, pid=pid, player_name=None, **wagon_filters)
                                            if fig is not None:
                                                all_batch_figures[f"{player_name}_wagon_zone_plot.png"] = fig
                                                success_count += 1
                                        
                                        if "Wagon Zone" in batch_plot_types:
                                            # Wagon plots don't have show_legend or show_ground parameters
                                            wagon_filters = {k: v for k, v in batch_filters.items() if k not in ['show_legend', 'show_ground']}
                                            fig = wagon_zone_plot_descriptive(df=df, pid=pid, player_name=None, **wagon_filters)
                                            if fig is not None:
                                                all_batch_figures[f"{player_name}_wagon_zone_desc.png"] = fig
                                                success_count += 1
                                        
                                        if "Dismissal Plot" in batch_plot_types:
                                            # Dismissal plots don't have run_values or show_legend parameters
                                            # dismissal_filters = {k: v for k, v in batch_filters.items()}
                                            dismissal_filters = {k: v for k, v in batch_filters.items() if k not in ['run_values', 'show_legend']}
                                            fig = dismissal_plot(df=df, pid=pid, player_name=None, **dismissal_filters)
                                            if fig is not None:
                                                all_batch_figures[f"{player_name}_dismissal_plot.png"] = fig
                                                success_count += 1
                                    
                                    except ZeroDivisionError:
                                        error_count += 1
                                        # Player has no data
                                    except Exception as e:
                                        error_count += 1
                                        st.sidebar.warning(f"⚠️ {player_name}: {str(e)[:100]}")
                                    
                                    # Add delay between players (2.5 seconds)
                                    if idx < len(team_pids) - 1:  # Don't delay after last player
                                        time.sleep(2.5)
                                
                                progress_bar.empty()
                                status_text.empty()
                                
                                # Create ZIP and download
                                if all_batch_figures:
                                    zip_buffer = create_zip_of_plots(all_batch_figures)
                                    
                                    st.sidebar.success(f"Generated {len(all_batch_figures)} plots!")
                                    if error_count > 0:
                                        st.sidebar.warning(f"⚠️ {error_count} players had no data")
                                    
                                    st.sidebar.download_button(
                                        label=f"📦 Download {selected_squad_team} Batch ZIP",
                                        data=zip_buffer.getvalue(),
                                        file_name=f"{selected_squad_team}_batch_plots.zip",
                                        mime="application/zip",
                                        key="batch_download_btn"
                                    )
                                else:
                                    st.sidebar.error("No plots were generated. Check if PIDs have data.")
                        else:
                            st.sidebar.warning("⚠️ Please select at least one plot type")
                else:
                    st.sidebar.error(" 'Bt-ID' column not found in squad file")
            else:
                st.sidebar.error(" 'Team' column not found in squad file")
        
        except Exception as e:
            st.sidebar.error(f" Error reading squad file: {str(e)}")


# ===== Main App Logic =====
if df is not None:
    # Convert date column to datetime if it exists and isn't already
    if 'date' in df.columns and df['date'].dtype == 'object':
        df['date'] = pd.to_datetime(df['date'])
    
    # ===== CASCADING FILTERS SECTION =====
    st.markdown("---")
    st.subheader("Value Filter Options")
    
    # Create 4 columns for filters
    filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)
    
    # Initialize working dataframe
    working_df = df.copy()
    
    # ===== COLUMN 1: Date, Competition, Match =====
    with filter_col1:
        
        # Date Range Filter (always shown)
        if 'date' in df.columns:
            # Ensure date column is datetime format
            if df['date'].dtype != 'datetime64[ns]':
                df['date'] = pd.to_datetime(df['date'], errors='coerce')
                working_df['date'] = pd.to_datetime(working_df['date'], errors='coerce')
            
            # Get valid date range (exclude NaT values)
            valid_dates = df['date'].dropna()
            if not valid_dates.empty:
                min_date = valid_dates.min().date()
                max_date = valid_dates.max().date()
                
                date_range = st.date_input(
                    "Date Range",
                    value=(min_date, max_date),
                    min_value=min_date,
                    max_value=max_date
                )
                if len(date_range) == 2:
                    date_from, date_to = date_range
                    working_df = working_df[
                        (working_df['date'].dt.date >= date_from) & 
                        (working_df['date'].dt.date <= date_to)
                    ]
                else:
                    date_from, date_to = None, None
            else:
                date_from, date_to = None, None
        else:
            date_from, date_to = None, None
        
        # Competition Filter (from working_df)
        competitions = sorted(working_df['competition'].dropna().unique())
        competition_options = ["All"] + list(competitions)
        selected_competition = st.selectbox("Competition", competition_options, index=0)
        
        if selected_competition != "All":
            working_df = working_df[working_df['competition'] == selected_competition]
            selected_competition_value = selected_competition
        else:
            selected_competition_value = None
        
        # Match Number Filter (from working_df)
        mat_nums = sorted(working_df['p_match'].dropna().unique())
        mat_num_options = ["All"] + [str(int(num)) for num in mat_nums]
        selected_mat_str = st.selectbox("Match Number", mat_num_options, index=0)
        
        if selected_mat_str != "All":
            selected_mat_num = int(selected_mat_str)
            working_df = working_df[working_df['p_match'] == selected_mat_num]
        else:
            selected_mat_num = None
        
        # Match Code Filter (from working_df)
        # if 'mcode' in working_df.columns:
        #     mcode_options = sorted(working_df['mcode'].dropna().unique())
        #     mcode_display = ["All"] + list(mcode_options)
        #     selected_mcode_str = st.selectbox("Match Code", mcode_display, index=0)
            
        #     if selected_mcode_str != "All":
        #         selected_mcode = selected_mcode_str
        #     else:
        #         selected_mcode = None
        # else:
        #     selected_mcode = None

        if 'mcode' in working_df.columns:
            mcode_options = sorted(working_df['mcode'].dropna().unique())
            stored_mcode = st.session_state.get('filter_mcode', []) if isinstance(st.session_state.get('filter_mcode', []), list) else []
            selected_mcode = st.multiselect("Match Code", mcode_options, default=stored_mcode)
            # Filtering logic (if you want to filter working_df here)
            if selected_mcode:
                working_df = working_df[working_df['mcode'].isin(selected_mcode)]
            # Save immediately for persistence
            st.session_state['filter_mcode'] = selected_mcode
        else:
            selected_mcode = None
        
        # Title Components Filter (Global - applies to all plots)
        title_components = st.multiselect(
            "Title Components",
            options=['title', 'filters', 'show_venue'],
            default=['title'],
            help="'title' = Player vs Team | 'filters' = Competition, Match#, Innings | 'show_venue' = Venue info in title. Applies to all plots."
        )
        st.session_state.title_components = title_components
        
    
    # ===== COLUMN 2: Batting Team, Batter, Player ID =====
    with filter_col2:
        
        # Batting Team Filter (from working_df)
        batting_teams = sorted(working_df['team_bat'].dropna().unique())
        team_bat_options = ["All"] + list(batting_teams)
        stored_team = st.session_state.get('filter_team_bat', []) if isinstance(st.session_state.get('filter_team_bat', []), list) and st.session_state.get('filter_team_bat') != "All" else []
        selected_team = st.multiselect("Batting Team", team_bat_options, default=stored_team)
        
        # if selected_team != "All":
        #     working_df = working_df[working_df['team_bat'] == selected_team]
        if selected_team and len(selected_team) > 0:
            working_df = working_df[working_df['team_bat'].isin(selected_team)]
            selected_team_value = selected_team
        else:
            selected_team_value = None
        # Save immediately for persistence
        st.session_state['filter_team_bat'] = selected_team
        
        # Player Filter (from working_df, only from selected batting team)
        player_list = sorted(working_df['bat'].dropna().unique())
        player_options = ["All"] + list(player_list)
        selected_player = st.selectbox("Batter", player_options, index=0)
        
        if selected_player != "All":
            selected_player_value = selected_player
        else:
            selected_player_value = None
        
        # PID Filter (dropdown with unique p_bat values)
        pid_list = sorted(working_df['p_bat'].dropna().unique())
        pid_options = ["All"] + [str(int(p)) for p in pid_list]
        selected_pid_str = st.selectbox("Batter PID", pid_options, index=0)
        
        if selected_pid_str != "All":
            selected_pid = int(selected_pid_str)
        else:
            selected_pid = None
        
        # Batter Hand Filter (from working_df)
        if 'bat_hand' in working_df.columns:
            bat_hand_options = sorted(working_df['bat_hand'].dropna().unique())
            stored_bat_hands = st.session_state.get('filter_bat_hand', []) if isinstance(st.session_state.get('filter_bat_hand', []), list) else []
            selected_bat_hands = st.multiselect(
                "Batter Hand(s)",
                options=list(bat_hand_options),
                default=stored_bat_hands,
                help="Leave empty to include all"
            )
            bat_hand = selected_bat_hands if selected_bat_hands else None
            # Save immediately for persistence
            st.session_state['filter_bat_hand'] = selected_bat_hands
        else:
            bat_hand = None
    
    # ===== COLUMN 3: Bowling Team, Bowler, Bowler PID =====
    with filter_col3:
        
        # Bowling Team Filter (from working_df, excluding batting team)
        bowling_teams = sorted(working_df['team_bowl'].dropna().unique())
        # Exclude selected batting team from bowling options
        if selected_team and len(selected_team) > 0:
            bowling_teams = [t for t in bowling_teams if t not in selected_team]
        team_bowl_options = ["All"] + list(bowling_teams)
        stored_team_bowl = st.session_state.get('filter_team_bowl', []) if isinstance(st.session_state.get('filter_team_bowl', []), list) and st.session_state.get('filter_team_bowl') != "All" else []
        selected_team_bowl = st.multiselect("Bowling Team", team_bowl_options, default=stored_team_bowl)
        
        if selected_team_bowl and len(selected_team_bowl) > 0:
            working_df = working_df[working_df['team_bowl'].isin(selected_team_bowl)]
            selected_team_bowl_value = selected_team_bowl
        else:
            selected_team_bowl_value = None
        # Save immediately for persistence
        st.session_state['filter_team_bowl'] = selected_team_bowl
        
        # Bowler Filter (from working_df, only from bowling team)
        bowler_list = sorted(working_df['bowl'].dropna().unique())
        bowler_options = ["All"] + list(bowler_list)
        selected_bowler = st.selectbox("Bowler", bowler_options, index=0)
        
        if selected_bowler != "All":
            bowler_name = selected_bowler
        else:
            bowler_name = None
        
        # Bowler PID Filter (dropdown with unique p_bowl values)
        bowl_pid_list = sorted(working_df['p_bowl'].dropna().unique())
        bowl_pid_options = ["All"] + [str(int(p)) for p in bowl_pid_list]
        selected_bowl_pid_str = st.selectbox("Bowler PID", bowl_pid_options, index=0)
        
        if selected_bowl_pid_str != "All":
            bowler_id = int(selected_bowl_pid_str)
        else:
            bowler_id = None
        
        # Bowler Type Filter (from working_df)
        if 'bowl_type' in working_df.columns:
            bowl_type_options = sorted(working_df['bowl_type'].dropna().unique())
            # bowl_type_display = ["All"] + list(bowl_type_options)
            # selected_bowl_type_str = st.selectbox("Bowler Type", bowl_type_display, index=0)
            
            # if selected_bowl_type_str != "All":
            #     bowl_type = selected_bowl_type_str
            # else:
            #     bowl_type = None
            # updated multiselect
            stored_bowl_types = st.session_state.get('filter_bowl_type', []) if isinstance(st.session_state.get('filter_bowl_type', []), list) else []
            selected_bowl_types = st.multiselect(
                "Bowler Kind(s)",
                options=list(bowl_type_options),  # No "All" needed
                default=stored_bowl_types,  # Empty = All (no filter)
                help="Leave empty to include all types"
            )
            bowl_type = selected_bowl_types if selected_bowl_types else None
            # Save immediately for persistence
            st.session_state['filter_bowl_type'] = selected_bowl_types

        else:
            bowl_type = None
        
        # Bowler Kind Filter (from working_df)
        if 'bowl_kind' in working_df.columns:
            bowl_kind_options = sorted(working_df['bowl_kind'].dropna().unique())
            # bowl_kind_display = ["All"] + list(bowl_kind_options)
            # selected_bowl_kind_str = st.selectbox("Bowler Pace", bowl_kind_display, index=0)
            
            # if selected_bowl_kind_str != "All":
            #     bowl_kind = selected_bowl_kind_str
            # else:
            #     bowl_kind = None

            stored_bowl_kinds = st.session_state.get('filter_bowl_kind', []) if isinstance(st.session_state.get('filter_bowl_kind', []), list) else []
            selected_bowl_kinds = st.multiselect(
                "Bowler Type(s)",
                options=list(bowl_kind_options),
                default=stored_bowl_kinds,
                help="Leave empty to include all"
            )
            bowl_kind = selected_bowl_kinds if selected_bowl_kinds else None
            # Save immediately for persistence
            st.session_state['filter_bowl_kind'] = selected_bowl_kinds

        else:
            bowl_kind = None
        
        # Bowler Arm Filter (from working_df)
        if 'bowl_arm' in working_df.columns:
            bowl_arm_options = sorted(working_df['bowl_arm'].dropna().unique())
            # bowl_arm_display = ["All"] + list(bowl_arm_options)
            # selected_bowl_arm_str = st.selectbox("Bowler Arm", bowl_arm_display, index=0)
            
            # if selected_bowl_arm_str != "All":
            #     bowl_arm = selected_bowl_arm_str
            # else:
            #     bowl_arm = None

            stored_bowl_arms = st.session_state.get('filter_bowl_arm', []) if isinstance(st.session_state.get('filter_bowl_arm', []), list) else []
            selected_bowl_arms = st.multiselect(
                "Bowler Arm(s)",
                options=list(bowl_arm_options),
                default=stored_bowl_arms,
                help="Leave empty to include all"
            )
            bowl_arm = selected_bowl_arms if selected_bowl_arms else None
            # Save immediately for persistence
            st.session_state['filter_bowl_arm'] = selected_bowl_arms

        else:
            bowl_arm = None
    
    # ===== COLUMN 4: Innings, Overs, Phases =====
    with filter_col4:
        
        # Innings Filter (from working_df)
        # innings_options = sorted(working_df['inns'].dropna().unique())
        # innings_display = ["All"] + [str(int(i)) for i in innings_options]
        # selected_inns_str = st.selectbox("Innings", innings_display, index=0)
        
        # if selected_inns_str != "All":
        #     selected_inns = int(selected_inns_str)
        #     working_df = working_df[working_df['inns'] == selected_inns]
        # else:
        #     selected_inns = None

        innings_options = sorted(working_df['inns'].dropna().unique())
        stored_inns = st.session_state.get('filter_inns', []) if isinstance(st.session_state.get('filter_inns', []), list) else []
        selected_inns = st.multiselect("Innings", [int(i) for i in innings_options], default=stored_inns)
        if selected_inns:
            working_df = working_df[working_df['inns'].isin(selected_inns)]
        else:
            selected_inns = None
        # Save immediately for persistence
        st.session_state['filter_inns'] = selected_inns
        
        # Overs Filter (multiselect)
        if 'over' in working_df.columns:
            over_options = sorted(working_df['over'].dropna().unique())
            stored_overs = st.session_state.get('filter_over_values', []) if isinstance(st.session_state.get('filter_over_values', []), list) else []
            selected_overs = st.multiselect(
                "Overs",
                options=[int(o) for o in over_options],
                default=stored_overs,
                help="Select specific overs (leave empty for all)"
            )
            over_values = selected_overs if selected_overs else None
            # Save immediately for persistence
            st.session_state['filter_over_values'] = selected_overs
        else:
            over_values = None
        
        # Phase Filter (dropdown)
        # phase_options = ["All", "Powerplay (1-6)", "Middle (7-15)", "Death (16-20)"]
        # selected_phase_str = st.selectbox("Phase", phase_options, index=0)
        
        # phase_map = {
        #     "Powerplay (1-6)": 1,
        #     "Middle (7-15)": 2,
        #     "Death (16-20)": 3
        # }
        # phase = phase_map.get(selected_phase_str, None)

        phase_options = ["Powerplay (1-6)", "Middle (7-15)", "Slog (16-20)"]
        
        # Reverse map to convert stored numeric phases back to display names
        phase_reverse_map = {1: "Powerplay (1-6)", 2: "Middle (7-15)", 3: "Slog (16-20)"}
        stored_phase = st.session_state.get('filter_phase_display', [])
        
        selected_phase_str = st.multiselect("Phase", phase_options, default=stored_phase)
        phase_map = {
            "Powerplay (1-6)": 1,
            "Middle (7-15)": 2,
            "Slog (16-20)": 3
        }
        phase = [phase_map[p] for p in selected_phase_str] if selected_phase_str else None
        
        # Store both display names and numeric values
        st.session_state['filter_phase_display'] = selected_phase_str


        # Ground Filter (dropdown)
        # if 'ground' in working_df.columns:
        #     ground_options = sorted(working_df['ground'].dropna().unique())
        #     ground_display = ["All"] + list(ground_options)
        #     # selected_ground_str = st.selectbox("Ground", ground_display, index=0)
        #     selected_ground_str = st.multiselect("Ground", ground_display, default=[])
            
        #     if selected_ground_str != ["All"] and len(selected_ground_str) > 0:
        #         working_df = working_df[working_df['ground'].isin(selected_ground_str)]
        #         selected_ground = selected_ground_str
        #     else:
        #         selected_ground = None
        # else:
        #     selected_ground = None

        #updated ground filters
        if 'ground' in working_df.columns:
            ground_options = sorted(working_df['ground'].dropna().unique())
            stored_ground = st.session_state.get('filter_ground', []) if isinstance(st.session_state.get('filter_ground', []), list) else []
            selected_ground_str = st.multiselect("Venue", ground_options, default=stored_ground)
            if selected_ground_str:
                working_df = working_df[working_df['ground'].isin(selected_ground_str)]
                selected_ground = selected_ground_str
            else:
                selected_ground = None
            # Save immediately for persistence
            st.session_state['filter_ground'] = selected_ground_str
        else:
            selected_ground = None
    
    # ===== UPDATE FILTER SESSION STATE AT END OF FILTER SECTION =====
    # Update with actual filter values so batch section reads latest values
    st.session_state['filter_competition'] = selected_competition_value
    st.session_state['filter_team_bat'] = selected_team_value
    st.session_state['filter_team_bowl'] = selected_team_bowl_value
    st.session_state['filter_inns'] = selected_inns
    st.session_state['filter_match'] = selected_mat_num
    st.session_state['filter_bowler'] = bowler_name
    st.session_state['filter_bowler_id'] = bowler_id
    st.session_state['filter_bat_hand'] = bat_hand
    st.session_state['filter_mcode'] = selected_mcode
    st.session_state['filter_ground'] = selected_ground
    st.session_state['filter_bowl_type'] = bowl_type
    st.session_state['filter_bowl_kind'] = bowl_kind
    st.session_state['filter_bowl_arm'] = bowl_arm
    st.session_state['filter_over_values'] = over_values
    st.session_state['filter_phase'] = phase
    st.session_state['date_range_filter'] = (date_from, date_to) if 'date_from' in locals() else (None, None)
    
    # ===== DATA VALIDATION ====
    st.markdown("---")
    
    # Check if we have data after all filters
    if working_df.empty:
        st.error("⚠️ No data available for the selected filters. Please adjust your filter selections.")
        # st.info("💡 Try selecting 'All' for some filters or choosing different combinations.")
        st.stop()
    else:
        pass
        # st.success(f"Found {len(working_df):,} balls matching your filters")

    # ===== GENERATE ALL PLOTS SECTION =====
    st.markdown("**🚀 Quick Actions:**")
    col_btn1, col_btn2, col_blank = st.columns([2, 2, 4])
    
    with col_btn1:
        generate_all = st.button(
            "🎬 Generate All Plots", 
            key="generate_all_plots_button",
            help="Generates all available plots with current filters and creates a ZIP file"
        )
    
    # Generate all plots if button clicked
    if generate_all:
        # Create batter name for filename (sanitize for file naming)
        batter_name_for_file = selected_player_value.replace(" ", "_").replace("/", "_") if selected_player_value else "AllBatters"
        
        with col_btn2:
            st.info("⏳ Generating all plots... This may take a few minutes.")
        
        progress_placeholder = st.empty()
        status_placeholder = st.empty()
        
        all_generated_figures = {}
        all_plot_types = [
            "Wagon Wheel", "Wagon Wheel (Trans)",
            "━━ Wagon Wheel - vs All Types", "━━ Wagon Wheel - vs Pace", "━━ Wagon Wheel - vs Spin",
            "━━ Wagon Wheel - All Phases", "━━ Wagon Wheel - Powerplay", "━━ Wagon Wheel - Middle", "━━ Wagon Wheel - Slog",
            "━━ Wagon Wheel - All Kinds", "━━ Wagon Wheel - RAP", "━━ Wagon Wheel - RAFS", "━━ Wagon Wheel - RAWS",
            "━━ Wagon Wheel - LAP", "━━ Wagon Wheel - LAFS", "━━ Wagon Wheel - LAWS",
            "━━ Wagon Wheel - All Arm", "━━ Wagon Wheel - Right Arm", "━━ Wagon Wheel - Left Arm",
            "Wagon Zone", "Wagon Zone (Trans)",
            "━━ Wagon Zone - vs All Types", "━━ Wagon Zone - vs Pace", "━━ Wagon Zone - vs Spin",
            "━━ Wagon Zone - All Phases", "━━ Wagon Zone - Powerplay", "━━ Wagon Zone - Middle", "━━ Wagon Zone - Slog",
            "━━ Wagon Zone - All Kinds", "━━ Wagon Zone - RAP", "━━ Wagon Zone - RAFS", "━━ Wagon Zone - RAWS",
            "━━ Wagon Zone - LAP", "━━ Wagon Zone - LAFS", "━━ Wagon Zone - LAWS",
            "━━ Wagon Zone - All Arm", "━━ Wagon Zone - Right Arm", "━━ Wagon Zone - Left Arm",
            "Dismissal Plot", "Dismissal Plot (Trans)",
            "━━ Dis Plot - vs All Types", "━━ Dis Plot - vs Pace", "━━ Dis Plot - vs Spin",
            "━━ Dis Plot - All Phases", "━━ Dis Plot - Powerplay", "━━ Dis Plot - Middle", "━━ Dis Plot - Slog",
            "━━ Dis Plot - All Kinds", "━━ Dis Plot - RAP", "━━ Dis Plot - RAFS", "━━ Dis Plot - RAWS",
            "━━ Dis Plot - LAP", "━━ Dis Plot - LAFS", "━━ Dis Plot - LAWS",
            "━━ Dis Plot - All Arm", "━━ Dis Plot - Right Arm", "━━ Dis Plot - Left Arm"
        ]
        
        # Define run values for all plots
        all_run_values = [0, 1, 2, 3, 4, 5, 6]
        
        # Build mapping of plot types to their generation logic
        plot_generation_map = {
            # ===== WAGON WHEEL PLOTS =====
            "Wagon Wheel": ("spike_desc", None),
            "Wagon Wheel (Trans)": ("spike_desc", "trans"),
            "━━ Wagon Wheel - vs All Types": ("spike_desc_bowl_type", None, "all_types"),
            "━━ Wagon Wheel - vs Pace": ("spike_desc_bowl_type", None, "pace"),
            "━━ Wagon Wheel - vs Spin": ("spike_desc_bowl_type", None, "spin"),
            "━━ Wagon Wheel - All Phases": ("spike_desc_phase", None, None),
            "━━ Wagon Wheel - Powerplay": ("spike_desc_phase", None, "powerplay"),
            "━━ Wagon Wheel - Middle": ("spike_desc_phase", None, "middle"),
            "━━ Wagon Wheel - Slog": ("spike_desc_phase", None, "slog"),
            "━━ Wagon Wheel - All Kinds": ("spike_desc_bowl_kind", None, None),
            # Fixed - variant strings now match the "in" substring checks
            "━━ Wagon Wheel - RAP":  ("spike_desc_bat_arm_bowl_kind", None, "rap"),
            "━━ Wagon Wheel - RAFS": ("spike_desc_bat_arm_bowl_kind", None, "rafs"),
            "━━ Wagon Wheel - RAWS": ("spike_desc_bat_arm_bowl_kind", None, "raws"),
            "━━ Wagon Wheel - LAP":  ("spike_desc_bat_arm_bowl_kind", None, "lap"),
            "━━ Wagon Wheel - LAFS": ("spike_desc_bat_arm_bowl_kind", None, "lafs"),
            "━━ Wagon Wheel - LAWS": ("spike_desc_bat_arm_bowl_kind", None, "laws"),
            "━━ Wagon Wheel - All Arm": ("spike_desc_bowl_arm", None, None),
            "━━ Wagon Wheel - Right Arm": ("spike_desc_bowl_arm", None, "right"),
            "━━ Wagon Wheel - Left Arm": ("spike_desc_bowl_arm", None, "left"),
            # # ===== WAGON ZONE PLOTS =====
            "Wagon Zone": ("wagon_zone", None),
            "Wagon Zone (Trans)": ("wagon_zone", "trans"),
            "━━ Wagon Zone - vs All Types": ("wagon_zone_bowl_type", None, "all_types"),
            "━━ Wagon Zone - vs Pace": ("wagon_zone_bowl_type", None, "pace"),
            "━━ Wagon Zone - vs Spin": ("wagon_zone_bowl_type", None, "spin"),
            "━━ Wagon Zone - All Phases": ("wagon_zone_phase", None, None),
            "━━ Wagon Zone - Powerplay": ("wagon_zone_phase", None, "powerplay"),
            "━━ Wagon Zone - Middle": ("wagon_zone_phase", None, "middle"),
            "━━ Wagon Zone - Slog": ("wagon_zone_phase", None, "slog"),
            "━━ Wagon Zone - All Kinds": ("wagon_zone_bowl_kind", None, None),
            # Wagon Zone - Fixed
            "━━ Wagon Zone - RAP":  ("wagon_zone_bat_arm_bowl_kind", None, "rap"),
            "━━ Wagon Zone - RAFS": ("wagon_zone_bat_arm_bowl_kind", None, "rafs"),
            "━━ Wagon Zone - RAWS": ("wagon_zone_bat_arm_bowl_kind", None, "raws"),
            "━━ Wagon Zone - LAP":  ("wagon_zone_bat_arm_bowl_kind", None, "lap"),
            "━━ Wagon Zone - LAFS": ("wagon_zone_bat_arm_bowl_kind", None, "lafs"),
            "━━ Wagon Zone - LAWS": ("wagon_zone_bat_arm_bowl_kind", None, "laws"),
            "━━ Wagon Zone - All Arm": ("wagon_zone_bowl_arm", None, None),
            "━━ Wagon Zone - Right Arm": ("wagon_zone_bowl_arm", None, "right"),
            "━━ Wagon Zone - Left Arm": ("wagon_zone_bowl_arm", None, "left"),
            # ===== DISMISSAL PLOTS =====
            "Dismissal Plot": ("dismissal", None),
            "Dismissal Plot (Trans)": ("dismissal", "trans"),
            "━━ Dis Plot - vs All Types": ("dismissal_bowl_type", None, "all_types"),
            "━━ Dis Plot - vs Pace": ("dismissal_bowl_type", None, "pace"),
            "━━ Dis Plot - vs Spin": ("dismissal_bowl_type", None, "spin"),
            "━━ Dis Plot - All Phases": ("dismissal_phase", None, None),
            "━━ Dis Plot - Powerplay": ("dismissal_phase", None, "powerplay"),
            "━━ Dis Plot - Middle": ("dismissal_phase", None, "middle"),
            "━━ Dis Plot - Slog": ("dismissal_phase", None, "slog"),
            "━━ Dis Plot - All Kinds": ("dismissal_bowl_kind", None, None),
            # Dismissal - Fixed
            "━━ Dis Plot - RAP":  ("dismissal_bat_arm_bowl_kind", None, "rap"),
            "━━ Dis Plot - RAFS": ("dismissal_bat_arm_bowl_kind", None, "rafs"),
            "━━ Dis Plot - RAWS": ("dismissal_bat_arm_bowl_kind", None, "raws"),
            "━━ Dis Plot - LAP":  ("dismissal_bat_arm_bowl_kind", None, "lap"),
            "━━ Dis Plot - LAFS": ("dismissal_bat_arm_bowl_kind", None, "lafs"),
            "━━ Dis Plot - LAWS": ("dismissal_bat_arm_bowl_kind", None, "laws"),
            "━━ Dis Plot - All Arm": ("dismissal_bowl_arm", None, None),
            "━━ Dis Plot - Right Arm": ("dismissal_bowl_arm", None, "right"),
            "━━ Dis Plot - Left Arm": ("dismissal_bowl_arm", None, "left"),
        }
        
        # Generate each plot
        for idx, plot_name in enumerate(all_plot_types):
            try:
                status_placeholder.write(f"⏳ Generating: **{plot_name}** ({idx+1}/{len(all_plot_types)})")
                progress_placeholder.progress((idx + 1) / len(all_plot_types))
                
                plot_info = plot_generation_map.get(plot_name)
                if not plot_info:
                    status_placeholder.write(f"⚠️ Skipped: {plot_name} (not configured)")
                    time.sleep(1)
                    continue
                
                plot_type = plot_info[0]
                transparent = plot_info[1] == "trans"
                variant = plot_info[2] if len(plot_info) > 2 else None
                
                # ===== SPIKE PLOTS =====
                if plot_type == "spike_desc":
                    fig = spike_graph_plot_descriptive(
                        df=df, player_name=selected_player_value, pid=selected_pid, inns=selected_inns,
                        mat_num=selected_mat_num, team_bat=selected_team_value, team_bowl=selected_team_bowl_value,
                        run_values=all_run_values, bowler_name=bowler_name, bowler_id=bowler_id,
                        competition=selected_competition_value, transparent=transparent, over_values=over_values,
                        phase=phase, ground=selected_ground, mcode=selected_mcode, date_from=date_from, date_to=date_to,
                        title_components=title_components, bat_hand=bat_hand, bowl_type=bowl_type,
                        bowl_kind=bowl_kind, bowl_arm=bowl_arm
                    )
                
                # ===== SPIKE WITH BOWL TYPE FILTER =====
                elif plot_type == "spike_desc_bowl_type":
                    filter_bowl_kind = ["pace bowler", "Pace"] if variant == "pace" else (["spin bowler", "Spin"] if variant == "spin" else None)
                    fig = spike_graph_plot_descriptive(
                        df=df, player_name=selected_player_value, pid=selected_pid, inns=selected_inns,
                        mat_num=selected_mat_num, team_bat=selected_team_value, team_bowl=selected_team_bowl_value,
                        run_values=all_run_values, bowler_name=bowler_name, bowler_id=bowler_id,
                        competition=selected_competition_value, transparent=transparent, over_values=over_values,
                        phase=phase, ground=selected_ground, mcode=selected_mcode, date_from=date_from, date_to=date_to,
                        title_components=title_components, bat_hand=bat_hand, bowl_type=None,
                        bowl_kind=filter_bowl_kind, bowl_arm=None
                    )
                
                # ===== SPIKE WITH PHASE FILTER =====
                elif plot_type == "spike_desc_phase":
                    phase_filter = None
                    if variant == "powerplay":
                        phase_filter = [1]
                    elif variant == "middle":
                        phase_filter = [2]
                    elif variant == "slog":
                        phase_filter = [3]
                    fig = spike_graph_plot_descriptive(
                        df=df, player_name=selected_player_value, pid=selected_pid, inns=selected_inns,
                        mat_num=selected_mat_num, team_bat=selected_team_value, team_bowl=selected_team_bowl_value,
                        run_values=all_run_values, bowler_name=bowler_name, bowler_id=bowler_id,
                        competition=selected_competition_value, transparent=transparent, over_values=over_values,
                        phase=phase_filter, ground=selected_ground, mcode=selected_mcode, date_from=date_from, date_to=date_to,
                        title_components=title_components, bat_hand=bat_hand, bowl_type=bowl_type,
                        bowl_kind=bowl_kind, bowl_arm=bowl_arm
                    )
                
                # ===== SPIKE WITH BOWL KIND FILTER =====
                elif plot_type == "spike_desc_bowl_kind":
                    fig = spike_graph_plot_descriptive(
                        df=df, player_name=selected_player_value, pid=selected_pid, inns=selected_inns,
                        mat_num=selected_mat_num, team_bat=selected_team_value, team_bowl=selected_team_bowl_value,
                        run_values=all_run_values, bowler_name=bowler_name, bowler_id=bowler_id,
                        competition=selected_competition_value, transparent=transparent, over_values=over_values,
                        phase=phase, ground=selected_ground, mcode=selected_mcode, date_from=date_from, date_to=date_to,
                        title_components=title_components, bat_hand=bat_hand, bowl_type=bowl_type,
                        bowl_kind=bowl_kind, bowl_arm=bowl_arm
                    )
                
                # ===== SPIKE WITH Bowl ARM & BOWL KIND FILTER =====
                elif plot_type == "spike_desc_bat_arm_bowl_kind":
                    # bat_arm_filter = ["Right Arm"] if "right" in variant else ["Left Arm"]
                    bowl_type_filter = ["Right Arm Pace"] if "rap" in variant else (["Right Arm Finger Spin"] if "rafs" in variant else (["Right Arm Wrist Spin"] if "raws" in variant else (["Left Arm Pace"] if "lap" in variant else (["Left Arm Finger Spin"] if "lafs" in variant else (["Left Arm Wrist Spin"] if "laws" in variant else None)))))
                    fig = spike_graph_plot_descriptive(
                        df=df, player_name=selected_player_value, pid=selected_pid, inns=selected_inns,
                        mat_num=selected_mat_num, team_bat=selected_team_value, team_bowl=selected_team_bowl_value,
                        run_values=all_run_values, bowler_name=bowler_name, bowler_id=bowler_id,
                        competition=selected_competition_value, transparent=transparent, over_values=over_values,
                        phase=phase, ground=selected_ground, mcode=selected_mcode, date_from=date_from, date_to=date_to,
                        title_components=title_components, bat_hand=bat_hand, bowl_type=bowl_type_filter,
                        bowl_kind=None, bowl_arm=None
                    )
                
                # ===== SPIKE WITH BOWL ARM FILTER =====
                elif plot_type == "spike_desc_bowl_arm":
                    filter_bowl_arm = ["Right Arm"] if variant == "right" else (["Left Arm"] if variant == "left" else None)
                    fig = spike_graph_plot_descriptive(
                        df=df, player_name=selected_player_value, pid=selected_pid, inns=selected_inns,
                        mat_num=selected_mat_num, team_bat=selected_team_value, team_bowl=selected_team_bowl_value,
                        run_values=all_run_values, bowler_name=bowler_name, bowler_id=bowler_id,
                        competition=selected_competition_value, transparent=transparent, over_values=over_values,
                        phase=phase, ground=selected_ground, mcode=selected_mcode, date_from=date_from, date_to=date_to,
                        title_components=title_components, bat_hand=bat_hand, bowl_type=None,
                        bowl_kind=None, bowl_arm=filter_bowl_arm
                    )
                
                # ===== WAGON ZONE PLOTS =====
                elif plot_type == "wagon_zone":
                    fig = wagon_zone_plot_descriptive(
                        df=df, player_name=selected_player_value, pid=selected_pid, inns=selected_inns,
                        mat_num=selected_mat_num, team_bat=selected_team_value, team_bowl=selected_team_bowl_value,
                        bowler_name=bowler_name, bowler_id=bowler_id, competition=selected_competition_value,
                        transparent=transparent, over_values=over_values, phase=phase, ground=selected_ground,
                        mcode=selected_mcode, date_from=date_from, date_to=date_to, title_components=title_components,
                        bat_hand=bat_hand, bowl_type=None, bowl_kind=None, bowl_arm=None
                    )
                
                # ===== WAGON ZONE WITH BOWL TYPE FILTER =====
                elif plot_type == "wagon_zone_bowl_type":
                    filter_bowl_kind = ["pace bowler", "Pace"] if variant == "pace" else (["spin bowler", "Spin"] if variant == "spin" else None)
                    fig = wagon_zone_plot_descriptive(
                        df=df, player_name=selected_player_value, pid=selected_pid, inns=selected_inns,
                        mat_num=selected_mat_num, team_bat=selected_team_value, team_bowl=selected_team_bowl_value,
                        bowler_name=bowler_name, bowler_id=bowler_id, competition=selected_competition_value,
                        transparent=transparent, over_values=over_values, phase=phase, ground=selected_ground,
                        mcode=selected_mcode, date_from=date_from, date_to=date_to, title_components=title_components,
                        bat_hand=bat_hand, bowl_type=None, bowl_kind=filter_bowl_kind, bowl_arm=None
                    )
                
                # ===== WAGON ZONE WITH PHASE FILTER =====
                elif plot_type == "wagon_zone_phase":
                    phase_filter = None
                    if variant == "powerplay":
                        phase_filter = [1]
                    elif variant == "middle":
                        phase_filter = [2]
                    elif variant == "slog":
                        phase_filter = [3]
                    fig = wagon_zone_plot_descriptive(
                        df=df, player_name=selected_player_value, pid=selected_pid, inns=selected_inns,
                        mat_num=selected_mat_num, team_bat=selected_team_value, team_bowl=selected_team_bowl_value,
                        bowler_name=bowler_name, bowler_id=bowler_id, competition=selected_competition_value,
                        transparent=transparent, over_values=over_values, phase=phase_filter, ground=selected_ground,
                        mcode=selected_mcode, date_from=date_from, date_to=date_to, title_components=title_components,
                        bat_hand=bat_hand, bowl_type=None, bowl_kind=None, bowl_arm=None
                    )
                
                # ===== WAGON ZONE WITH BOWL KIND FILTER =====
                elif plot_type == "wagon_zone_bowl_kind":
                    fig = wagon_zone_plot_descriptive(
                        df=df, player_name=selected_player_value, pid=selected_pid, inns=selected_inns,
                        mat_num=selected_mat_num, team_bat=selected_team_value, team_bowl=selected_team_bowl_value,
                        bowler_name=bowler_name, bowler_id=bowler_id, competition=selected_competition_value,
                        transparent=transparent, over_values=over_values, phase=phase, ground=selected_ground,
                        mcode=selected_mcode, date_from=date_from, date_to=date_to, title_components=title_components,
                        bat_hand=bat_hand, bowl_type=None, bowl_kind=None, bowl_arm=None
                    )
                
                # ===== WAGON ZONE WITH BAT ARM & BOWL KIND FILTER =====
                elif plot_type == "wagon_zone_bat_arm_bowl_kind":
                    # bat_arm_filter = ["Right Arm"] if "right" in variant else ["Left Arm"]
                    bowl_type_filter = ["Right Arm Pace"] if "rap" in variant else (["Right Arm Finger Spin"] if "rafs" in variant else (["Right Arm Wrist Spin"] if "raws" in variant else (["Left Arm Pace"] if "lap" in variant else (["Left Arm Finger Spin"] if "lafs" in variant else (["Left Arm Wrist Spin"] if "laws" in variant else None)))))
                    fig = wagon_zone_plot_descriptive(
                        df=df, player_name=selected_player_value, pid=selected_pid, inns=selected_inns,
                        mat_num=selected_mat_num, team_bat=selected_team_value, team_bowl=selected_team_bowl_value,
                        bowler_name=bowler_name, bowler_id=bowler_id, competition=selected_competition_value,
                        transparent=transparent, over_values=over_values, phase=phase, ground=selected_ground,
                        mcode=selected_mcode, date_from=date_from, date_to=date_to, title_components=title_components,
                        bat_hand=bat_hand, bowl_type=bowl_type_filter, bowl_kind=None, bowl_arm=None
                    )
                
                # ===== WAGON ZONE WITH BOWL ARM FILTER =====
                elif plot_type == "wagon_zone_bowl_arm":
                    filter_bowl_arm = ["Right Arm"] if variant == "right" else (["Left Arm"] if variant == "left" else None)
                    fig = wagon_zone_plot_descriptive(
                        df=df, player_name=selected_player_value, pid=selected_pid, inns=selected_inns,
                        mat_num=selected_mat_num, team_bat=selected_team_value, team_bowl=selected_team_bowl_value,
                        bowler_name=bowler_name, bowler_id=bowler_id, competition=selected_competition_value,
                        transparent=transparent, over_values=over_values, phase=phase, ground=selected_ground,
                        mcode=selected_mcode, date_from=date_from, date_to=date_to, title_components=title_components,
                        bat_hand=bat_hand, bowl_type=None, bowl_kind=None, bowl_arm=filter_bowl_arm
                    )
                
                # ===== DISMISSAL PLOTS =====
                elif plot_type == "dismissal":
                    fig = dismissal_plot(
                        df=df, player_name=selected_player_value, pid=selected_pid, inns=selected_inns,
                        mat_num=selected_mat_num, team_bat=selected_team_value, team_bowl=selected_team_bowl_value,
                        bowler_name=bowler_name, bowler_id=bowler_id, competition=selected_competition_value,
                        transparent=transparent, over_values=over_values, phase=phase, ground=selected_ground,
                        mcode=selected_mcode, date_from=date_from, date_to=date_to, title_components=title_components,
                        bat_hand=bat_hand, bowl_type=None, bowl_kind=None, bowl_arm=None
                    )
                
                # ===== DISMISSAL WITH BOWL TYPE FILTER =====
                elif plot_type == "dismissal_bowl_type":
                    filter_bowl_kind = ["pace bowler", "Pace"] if variant == "pace" else (["spin bowler", "Spin"] if variant == "spin" else None)
                    fig = dismissal_plot(
                        df=df, player_name=selected_player_value, pid=selected_pid, inns=selected_inns,
                        mat_num=selected_mat_num, team_bat=selected_team_value, team_bowl=selected_team_bowl_value,
                        bowler_name=bowler_name, bowler_id=bowler_id, competition=selected_competition_value,
                        transparent=transparent, over_values=over_values, phase=phase, ground=selected_ground,
                        mcode=selected_mcode, date_from=date_from, date_to=date_to, title_components=title_components,
                        bat_hand=bat_hand, bowl_type=None, bowl_kind=filter_bowl_kind, bowl_arm=None
                    )
                
                # ===== DISMISSAL WITH PHASE FILTER =====
                elif plot_type == "dismissal_phase":
                    phase_filter = None
                    if variant == "powerplay":
                        phase_filter = [1]
                    elif variant == "middle":
                        phase_filter = [2]
                    elif variant == "slog":
                        phase_filter = [3]
                    fig = dismissal_plot(
                        df=df, player_name=selected_player_value, pid=selected_pid, inns=selected_inns,
                        mat_num=selected_mat_num, team_bat=selected_team_value, team_bowl=selected_team_bowl_value,
                        bowler_name=bowler_name, bowler_id=bowler_id, competition=selected_competition_value,
                        transparent=transparent, over_values=over_values, phase=phase_filter, ground=selected_ground,
                        mcode=selected_mcode, date_from=date_from, date_to=date_to, title_components=title_components,
                        bat_hand=bat_hand, bowl_type=None, bowl_kind=None, bowl_arm=None
                    )
                
                # ===== DISMISSAL WITH BOWL KIND FILTER =====
                elif plot_type == "dismissal_bowl_kind":
                    fig = dismissal_plot(
                        df=df, player_name=selected_player_value, pid=selected_pid, inns=selected_inns,
                        mat_num=selected_mat_num, team_bat=selected_team_value, team_bowl=selected_team_bowl_value,
                        bowler_name=bowler_name, bowler_id=bowler_id, competition=selected_competition_value,
                        transparent=transparent, over_values=over_values, phase=phase, ground=selected_ground,
                        mcode=selected_mcode, date_from=date_from, date_to=date_to, title_components=title_components,
                        bat_hand=bat_hand, bowl_type=None, bowl_kind=None, bowl_arm=None
                    )
                
                # ===== DISMISSAL WITH BAT ARM & BOWL KIND FILTER =====
                elif plot_type == "dismissal_bat_arm_bowl_kind":
                    # bat_arm_filter = ["Right Arm"] if "right" in variant else ["Left Arm"]
                    bowl_type_filter = ["Right Arm Pace"] if "rap" in variant else (["Right Arm Finger Spin"] if "rafs" in variant else (["Right Arm Wrist Spin"] if "raws" in variant else (["Left Arm Pace"] if "lap" in variant else (["Left Arm Finger Spin"] if "lafs" in variant else (["Left Arm Wrist Spin"] if "laws" in variant else None)))))
                    fig = dismissal_plot(
                        df=df, player_name=selected_player_value, pid=selected_pid, inns=selected_inns,
                        mat_num=selected_mat_num, team_bat=selected_team_value, team_bowl=selected_team_bowl_value,
                        bowler_name=bowler_name, bowler_id=bowler_id, competition=selected_competition_value,
                        transparent=transparent, over_values=over_values, phase=phase, ground=selected_ground,
                        mcode=selected_mcode, date_from=date_from, date_to=date_to, title_components=title_components,
                        bat_hand=bat_hand, bowl_type=bowl_type_filter, bowl_kind=None, bowl_arm=None
                    )
                
                # ===== DISMISSAL WITH BOWL ARM FILTER =====
                elif plot_type == "dismissal_bowl_arm":
                    filter_bowl_arm = ["Right Arm"] if variant == "right" else (["Left Arm"] if variant == "left" else None)
                    fig = dismissal_plot(
                        df=df, player_name=selected_player_value, pid=selected_pid, inns=selected_inns,
                        mat_num=selected_mat_num, team_bat=selected_team_value, team_bowl=selected_team_bowl_value,
                        bowler_name=bowler_name, bowler_id=bowler_id, competition=selected_competition_value,
                        transparent=transparent, over_values=over_values, phase=phase, ground=selected_ground,
                        mcode=selected_mcode, date_from=date_from, date_to=date_to, title_components=title_components,
                        bat_hand=bat_hand, bowl_type=None, bowl_kind=None, bowl_arm=filter_bowl_arm
                    )
                
                else:
                    fig = None
                
                # Store figure if generated with batter name in filename
                if fig is not None:
                    filename_with_batter = f"{batter_name_for_file}_{plot_name}"
                    all_generated_figures[filename_with_batter] = fig
                
                time.sleep(3)  # 3-second delay between plots
                
            except Exception as e:
                status_placeholder.write(f"❌ Error generating {plot_name}: {str(e)}")
                time.sleep(1)
        
        # Create ZIP file with all generated plots
        if all_generated_figures:
            status_placeholder.write(f"✅ Generated {len(all_generated_figures)}/{len(all_plot_types)} plots! Creating ZIP file...")
            zip_buffer = create_zip_of_plots(all_generated_figures)
            
            st.success(f"🎉 Successfully generated {len(all_generated_figures)} plots!")
            st.download_button(
                label=f"📥 Download {batter_name_for_file}_plots.zip",
                data=zip_buffer,
                # file_name="Multiple_plots.zip",
                file_name=f"{batter_name_for_file}_plots.zip",
                mime="application/zip",
                key="download_all_plots"
            )
        else:
            st.error("❌ No plots were generated. Please check your filters and try again.")

    st.markdown("**Select Plot Types to Display:**")
    plot_types = st.multiselect(
        "Choose plot(s):",
        [
            # "Wagon Wheel (White Background)",
            # "Wagon Wheel (Transparent Background)",
            "Wagon Wheel",
            "Wagon Wheel (Trans)",
            "━━ Wagon Wheel - vs All Types",
            "━━ Wagon Wheel - vs Pace",
            "━━ Wagon Wheel - vs Spin",
            "━━ Wagon Wheel - All Phases",
            "━━ Wagon Wheel - Powerplay",
            "━━ Wagon Wheel - Middle",
            "━━ Wagon Wheel - Slog",
            "━━ Wagon Wheel - All Kinds",
            "━━ Wagon Wheel - RAP",
            "━━ Wagon Wheel - RAFS",
            "━━ Wagon Wheel - RAWS",
            "━━ Wagon Wheel - LAP",
            "━━ Wagon Wheel - LAFS",
            "━━ Wagon Wheel - LAWS",
            "━━ Wagon Wheel - All Arm",
            "━━ Wagon Wheel - Right Arm",
            "━━ Wagon Wheel - Left Arm",
            # "Wagon Zone Plot (White Background)",
            # "Wagon Zone Plot (Transparent Background)",
            "Wagon Zone",
            "Wagon Zone (Trans)",
            "━━ Wagon Zone - vs All Types",
            "━━ Wagon Zone - vs Pace",
            "━━ Wagon Zone - vs Spin",
            "━━ Wagon Zone - All Phases",
            "━━ Wagon Zone - Powerplay",
            "━━ Wagon Zone - Middle",
            "━━ Wagon Zone - Slog",
            "━━ Wagon Zone - All Kinds",
            "━━ Wagon Zone - RAP",
            "━━ Wagon Zone - RAFS",
            "━━ Wagon Zone - RAWS",
            "━━ Wagon Zone - LAP",
            "━━ Wagon Zone - LAFS",
            "━━ Wagon Zone - LAWS",
            "━━ Wagon Zone - All Arm",
            "━━ Wagon Zone - Right Arm",
            "━━ Wagon Zone - Left Arm",
            "Dismissal Plot",
            "Dismissal Plot (Trans)",
            "━━ Dis Plot - vs All Types",
            "━━ Dis Plot - vs Pace",
            "━━ Dis Plot - vs Spin",
            "━━ Dis Plot - All Phases",
            "━━ Dis Plot - Powerplay",
            "━━ Dis Plot - Middle",
            "━━ Dis Plot - Slog",
            "━━ Dis Plot - All Kinds",
            "━━ Dis Plot - RAP",
            "━━ Dis Plot - RAFS",
            "━━ Dis Plot - RAWS",
            "━━ Dis Plot - LAP",
            "━━ Dis Plot - LAFS",
            "━━ Dis Plot - LAWS",
            "━━ Dis Plot - All Arm",
            "━━ Dis Plot - Right Arm",
            "━━ Dis Plot - Left Arm"
        ]
    )

    fig_spike, fig_wagon, fig_spike_trans, fig_wagon_trans, fig_spike_desc, fig_wagon_desc, fig_spike_desc_trans, fig_wagon_desc_trans, fig_dismissal, fig_dismissal_trans, fig_spike_desc_pace, fig_spike_desc_spin, fig_whl_phs_all, fig_whl_phs_pp, fig_whl_phs_mid, fig_whl_phs_slog, fig_whl_all_kind, fig_whl_all_type, fig_whl_rap, fig_whl_rafs, fig_whl_raws, fig_whl_lap, fig_whl_lafs, fig_whl_laws, fig_whl_all_arm, fig_whl_right_arm, fig_whl_left_arm, fig_wzn_all_type, fig_wzn_pace, fig_wzn_spin, fig_wzn_all_phase, fig_wzn_pp, fig_wzn_mid, fig_wzn_slog, fig_wzn_all_kind, fig_wzn_rap, fig_wzn_rafs, fig_wzn_raws, fig_wzn_lap, fig_wzn_lafs, fig_wzn_laws, fig_wzn_all_arm, fig_wzn_right_arm, fig_wzn_left_arm, fig_dis_all_type, fig_dis_pace, fig_dis_spin, fig_dis_all_phase, fig_dis_pp, fig_dis_mid, fig_dis_slog, fig_dis_all_kind, fig_dis_rap, fig_dis_rafs, fig_dis_raws, fig_dis_lap, fig_dis_lafs, fig_dis_laws, fig_dis_all_arm, fig_dis_right_arm, fig_dis_left_arm = None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None

    # Ensure variables persist in session state
    for var_name in ['fig_whl_phs_all', 'fig_whl_phs_pp', 'fig_whl_phs_mid', 'fig_whl_phs_slog', 'fig_whl_all_kind', 'fig_whl_all_type', 'fig_whl_rap', 'fig_whl_rafs', 'fig_whl_raws', 'fig_whl_lap', 'fig_whl_lafs', 'fig_whl_laws', 'fig_whl_all_arm', 'fig_whl_right_arm', 'fig_whl_left_arm']:
        if var_name not in st.session_state:
            st.session_state[var_name] = locals()[var_name]

    if plot_types:
        if "Wagon Wheel (White Background)" in plot_types:
            st.markdown("<h2 style='text-align: center;'>Wagon Wheel (White Background)</h2>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([2, 2, 2])
            
            with col1:
                st.markdown("## Customize Plot Info")
                show_title = st.checkbox("Show Plot Title", value=True)
                show_legend = st.checkbox("Show Legend", value=True)
                show_summary = st.checkbox("Show Runs Summary", value=True)
                
                show_shots_breakdown = st.checkbox("Show Shots Breakdown", value=True, key="spike_shots_breakdown")
                if show_shots_breakdown:
                    shots_breakdown_options = st.multiselect(
                        "Shots to Display",
                        options=['0s', '1s', '2s', '3s', '4s', '6s'],
                        default=['0s', '1s', '2s', '4s', '6s'],
                        key="spike_shots_options",
                        help="Select which run types to display in breakdown"
                    )
                else:
                    shots_breakdown_options = []
                
                runs_count = st.checkbox("Show Runs Count", value=True)
                show_fours_sixes = st.checkbox("Show 4s and 6s", value=True)
                show_bowler = st.checkbox("Show Bowler", value=True)
                show_control = st.checkbox("Show Control %", value=True)
                show_prod_shot = st.checkbox("Show Productive Shot", value=True)
                show_overs = st.checkbox("Show Overs", value=True)
                show_phase = st.checkbox("Show Phase", value=True)
                show_venue = st.checkbox("Show Venue", value=True)
                show_ground = st.checkbox("Show Ground Image", value=True)

            with col3:
                st.markdown("## Run Filter (Wagon Wheel)")

                if "run_init_spike" not in st.session_state:
                    st.session_state["run_all_spike"] = True
                    for i in range(7):
                        st.session_state[f'run_{i}_spike'] = True
                    st.session_state["run_init_spike"] = True

                def sync_all_to_individual_spike():
                    all_selected = st.session_state["run_all_spike"]
                    for i in range(7):
                        st.session_state[f'run_{i}_spike'] = all_selected

                def sync_individual_to_all_spike():
                    all_selected = all(st.session_state[f'run_{i}_spike'] for i in range(7))
                    st.session_state["run_all_spike"] = all_selected

                st.checkbox("All", key="run_all_spike", on_change=sync_all_to_individual_spike)

                for i in range(7):
                    st.checkbox(str(i), key=f'run_{i}_spike', on_change=sync_individual_to_all_spike)

                individual_selected_spike = [i for i in range(7) if st.session_state.get(f'run_{i}_spike', False)]

                if st.session_state["run_all_spike"]:
                    filtered_runs_spike = None
                elif individual_selected_spike:
                    filtered_runs_spike = individual_selected_spike
                else:
                    filtered_runs_spike = []
                    
            if filtered_runs_spike == []:
                st.warning("Please select at least one run value to display the plot.")
            else:
                fig_spike = spike_plot_custom(
                    df=df,
                    player_name=selected_player_value,
                    pid=selected_pid,
                    inns=selected_inns,
                    mat_num=selected_mat_num,
                    team_bat=selected_team_value,
                    team_bowl=selected_team_bowl_value,
                    run_values=filtered_runs_spike,
                    bowler_name=bowler_name,
                    bowler_id=bowler_id,
                    competition=selected_competition_value,
                    transparent=False,
                    over_values=over_values,
                    phase=phase,
                    ground=selected_ground,
                    mcode=selected_mcode,
                    date_from=date_from,
                    date_to=date_to,
                    title_components=title_components if show_title else [],
                    bat_hand=bat_hand,
                    bowl_type=bowl_type,
                    bowl_kind=bowl_kind,
                    bowl_arm=bowl_arm,
                    show_title=show_title,
                    show_summary=show_summary,
                    show_shots_breakdown=show_shots_breakdown,
                    shots_breakdown_options=shots_breakdown_options,
                    show_legend=show_legend,
                    runs_count=runs_count,
                    show_fours_sixes=show_fours_sixes,
                    show_control=show_control,
                    show_prod_shot=show_prod_shot,
                    show_bowler=show_bowler,
                    show_ground=show_ground,
                    show_venue=show_venue,
                    show_overs=show_overs,
                    show_phase=show_phase,
                )
                with col2:
                    st.pyplot(fig_spike)
            
            with col3:
                if fig_spike:
                    buf = BytesIO()
                    fig_spike.savefig(buf, format="png", transparent=False, dpi=300, bbox_inches='tight')
                    buf.seek(0)
                    st.download_button(
                        label="📅 Download Plot as PNG",
                        data=buf.getvalue(),
                        file_name=f"{selected_player}_spikeplot.png",
                        mime="image/png",
                        key="spike_download"
                    )

        if "Wagon Wheel (Transparent Background)" in plot_types:
            st.markdown("<h2 style='text-align: center;'>Wagon Wheel (Transparent Background)</h2>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([2, 2, 2])
            
            with col1:
                st.markdown("## Customize Plot Info")
                show_title_trans = st.checkbox("Show Plot Title", value=True, key="spike_trans_title")
                show_legend_trans = st.checkbox("Show Legend", value=True, key="spike_trans_legend")
                show_summary_trans = st.checkbox("Show Runs Summary", value=True, key="spike_trans_summary")
                
                show_shots_breakdown_trans = st.checkbox("Show Shots Breakdown", value=True, key="spike_trans_shots_breakdown")
                if show_shots_breakdown_trans:
                    shots_breakdown_options_trans = st.multiselect(
                        "Shots to Display",
                        options=['0s', '1s', '2s', '3s', '4s', '6s'],
                        default=['0s', '1s', '2s', '4s', '6s'],
                        key="spike_trans_shots_options",
                        help="Select which run types to display in breakdown"
                    )
                else:
                    shots_breakdown_options_trans = []
                
                runs_count_trans = st.checkbox("Show Runs Count", value=True, key="spike_trans_runs")
                show_fours_sixes_trans = st.checkbox("Show 4s and 6s", value=True, key="spike_trans_fs")
                show_bowler_trans = st.checkbox("Show Bowler", value=True, key="spike_trans_bowler")
                show_control_trans = st.checkbox("Show Control %", value=True, key="spike_trans_control")
                show_prod_shot_trans = st.checkbox("Show Productive Shot", value=True, key="spike_trans_prod")
                show_overs_trans = st.checkbox("Show Overs", value=True, key="spike_trans_overs")
                show_phase_trans = st.checkbox("Show Phase", value=True, key="spike_trans_phase")
                show_venue_trans = st.checkbox("Show Venue", value=True, key="spike_trans_venue")
                show_ground_trans = st.checkbox("Show Ground Image", value=True, key="spike_trans_ground")

            with col3:
                st.markdown("## Run Filter (Wagon Wheel)")

                if "run_init_spike_trans" not in st.session_state:
                    st.session_state["run_all_spike_trans"] = True
                    for i in range(7):
                        st.session_state[f'run_{i}_spike_trans'] = True
                    st.session_state["run_init_spike_trans"] = True

                def sync_all_to_individual_spike_trans():
                    all_selected = st.session_state["run_all_spike_trans"]
                    for i in range(7):
                        st.session_state[f'run_{i}_spike_trans'] = all_selected

                def sync_individual_to_all_spike_trans():
                    all_selected = all(st.session_state[f'run_{i}_spike_trans'] for i in range(7))
                    st.session_state["run_all_spike_trans"] = all_selected

                st.checkbox("All", key="run_all_spike_trans", on_change=sync_all_to_individual_spike_trans)

                for i in range(7):
                    st.checkbox(str(i), key=f'run_{i}_spike_trans', on_change=sync_individual_to_all_spike_trans)

                individual_selected_spike_trans = [i for i in range(7) if st.session_state.get(f'run_{i}_spike_trans', False)]

                if st.session_state["run_all_spike_trans"]:
                    filtered_runs_spike_trans = None
                elif individual_selected_spike_trans:
                    filtered_runs_spike_trans = individual_selected_spike_trans
                else:
                    filtered_runs_spike_trans = []
                    
            if filtered_runs_spike_trans == []:
                st.warning("Please select at least one run value to display the plot.")
            else:
                fig_spike_trans = spike_plot_custom(
                    df=df,
                    player_name=selected_player_value,
                    pid=selected_pid,
                    inns=selected_inns,
                    mat_num=selected_mat_num,
                    team_bat=selected_team_value,
                    team_bowl=selected_team_bowl_value,
                    run_values=filtered_runs_spike_trans,
                    bowler_name=bowler_name,
                    ground=selected_ground,
                    bowler_id=bowler_id,
                    competition=selected_competition_value,
                    transparent=True,
                    over_values=over_values,
                    phase=phase,
                    mcode=selected_mcode,
                    date_from=date_from,
                    date_to=date_to,
                    title_components=title_components if show_title_trans else [],
                    bat_hand=bat_hand,
                    bowl_type=bowl_type,
                    bowl_kind=bowl_kind,
                    bowl_arm=bowl_arm,
                    show_title=show_title_trans,
                    show_summary=show_summary_trans,
                    show_shots_breakdown=show_shots_breakdown_trans,
                    shots_breakdown_options=shots_breakdown_options_trans,
                    show_legend=show_legend_trans,
                    runs_count=runs_count_trans,
                    show_fours_sixes=show_fours_sixes_trans,
                    show_control=show_control_trans,
                    show_prod_shot=show_prod_shot_trans,
                    show_bowler=show_bowler_trans,
                    show_ground=show_ground_trans,
                    show_venue=show_venue_trans,
                    show_overs=show_overs_trans,
                    show_phase=show_phase_trans
                )
                with col2:
                    st.pyplot(fig_spike_trans)
            
            with col3:
                if fig_spike_trans:
                    buf = BytesIO()
                    fig_spike_trans.savefig(buf, format="png", transparent=True, dpi=300, bbox_inches='tight')
                    buf.seek(0)
                    st.download_button(
                        label="📅 Download Plot as PNG",
                        data=buf.getvalue(),
                        file_name=f"{selected_player}_wagon_wheel_transparent.png",
                        mime="image/png",
                        key="spike_trans_download"
                    )

        if "Wagon Wheel" in plot_types:
            st.markdown("<h2 style='text-align: center;'>Wagon Wheel</h2>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([2, 2, 2])
            
            with col1:
                st.markdown("## Customize Plot Info")
                show_title_desc = st.checkbox("Show Plot Title", value=True, key="spike_desc_title")
                show_legend_desc = st.checkbox("Show Legend", value=True, key="spike_desc_legend")
                show_summary_desc = st.checkbox("Show Runs Summary", value=True, key="spike_desc_summary")
                
                show_shots_breakdown_desc = st.checkbox("Show Shots Breakdown", value=True, key="spike_desc_shots_breakdown")
                if show_shots_breakdown_desc:
                    shots_breakdown_options_desc = st.multiselect(
                        "Shots to Display",
                        options=['0s', '1s', '2s', '3s', '4s', '6s'],
                        default=['0s', '1s', '2s', '4s', '6s'],
                        key="spike_desc_shots_options",
                        help="Select which run types to display in breakdown"
                    )
                else:
                    shots_breakdown_options_desc = []
                
                runs_count_desc = st.checkbox("Show Runs Count", value=True, key="spike_desc_runs")
                show_fours_sixes_desc = st.checkbox("Show 4s and 6s", value=True, key="spike_desc_fs")
                show_bowler_desc = st.checkbox("Show Bowler", value=True, key="spike_desc_bowler")
                show_control_desc = st.checkbox("Show Control %", value=True, key="spike_desc_control")
                show_prod_shot_desc = st.checkbox("Show Productive Shot", value=True, key="spike_desc_prod")
                show_overs_desc = st.checkbox("Show Overs", value=True, key="spike_desc_overs")
                show_phase_desc = st.checkbox("Show Phase", value=True, key="spike_desc_phase")
                show_ground_desc = st.checkbox("Show Ground Image", value=True, key="spike_desc_ground")
                show_bowl_type_desc = st.checkbox("Show Bowl Type", value=True, key="spike_desc_bowl_type")
                show_bowl_kind_desc = st.checkbox("Show Bowl Pace", value=True, key="spike_desc_bowl_kind")
                show_bowl_arm_desc = st.checkbox("Show Bowl Arm", value=True, key="spike_desc_bowl_arm")
                show_venue_desc = st.checkbox("Show Venue", value=True, key="spike_desc_venue")

            with col3:
                st.markdown("## Run Filter (Wagon Wheel)")

                if "run_init_spike_desc" not in st.session_state:
                    st.session_state.run_init_spike_desc = True
                    for i in range(7):
                        st.session_state[f'run_{i}_spike_desc'] = True
                    st.session_state["run_all_spike_desc"] = True

                def sync_all_to_individual_spike_desc():
                    for i in range(7):
                        st.session_state[f'run_{i}_spike_desc'] = st.session_state["run_all_spike_desc"]

                def sync_individual_to_all_spike_desc():
                    if all(st.session_state.get(f'run_{i}_spike_desc', False) for i in range(7)):
                        st.session_state["run_all_spike_desc"] = True

                st.checkbox("All", key="run_all_spike_desc", on_change=sync_all_to_individual_spike_desc)

                for i in range(7):
                    st.checkbox(str(i), key=f'run_{i}_spike_desc', on_change=sync_individual_to_all_spike_desc)

                individual_selected_spike_desc = [i for i in range(7) if st.session_state.get(f'run_{i}_spike_desc', False)]

                if st.session_state["run_all_spike_desc"]:
                    filtered_runs_spike_desc = None
                elif individual_selected_spike_desc:
                    filtered_runs_spike_desc = individual_selected_spike_desc
                else:
                    filtered_runs_spike_desc = []
                    
            if filtered_runs_spike_desc == []:
                st.warning("Please select at least one run value to display the plot.")
            else:
                fig_spike_desc = spike_graph_plot_descriptive(
                    df=df,
                    player_name=selected_player_value,
                    pid=selected_pid,
                    inns=selected_inns,
                    mat_num=selected_mat_num,
                    team_bat=selected_team_value,
                    team_bowl=selected_team_bowl_value,
                    run_values=filtered_runs_spike_desc,
                    bowler_name=bowler_name,
                    bowler_id=bowler_id,
                    competition=selected_competition_value,
                    transparent=False,
                    over_values=over_values,
                    phase=phase,
                    ground=selected_ground,
                    mcode=selected_mcode,
                    date_from=date_from,
                    date_to=date_to,
                    title_components=title_components if show_title_desc else [],
                    bat_hand=bat_hand,
                    bowl_type=bowl_type,
                    bowl_kind=bowl_kind,
                    bowl_arm=bowl_arm,
                    show_title=show_title_desc,
                    show_summary=show_summary_desc,
                    show_shots_breakdown=show_shots_breakdown_desc,
                    shots_breakdown_options=shots_breakdown_options_desc,
                    show_legend=show_legend_desc,
                    runs_count=runs_count_desc,
                    show_fours_sixes=show_fours_sixes_desc,
                    show_control=show_control_desc,
                    show_prod_shot=show_prod_shot_desc,
                    show_bowler=show_bowler_desc,
                    show_ground=show_ground_desc,
                    show_venue=show_venue_desc,
                    show_overs=show_overs_desc,
                    show_phase=show_phase_desc,
                    show_bowl_type=show_bowl_type_desc,
                    show_bowl_kind=show_bowl_kind_desc,
                    show_bowl_arm=show_bowl_arm_desc
                )
                
                if fig_spike_desc is None:
                    st.warning("⚠️ No data available for selected filters. Please adjust your filter selections.")
                else:
                    with col2:
                        st.pyplot(fig_spike_desc)
            
            with col3:
                if fig_spike_desc:
                    buf = BytesIO()
                    fig_spike_desc.savefig(buf, format="png", transparent=False, dpi=300, bbox_inches='tight')
                    buf.seek(0)
                    st.download_button(
                        label="📅 Download Plot as PNG",
                        data=buf.getvalue(),
                        file_name=f"{selected_player}_wagon_wheel_descriptive.png",
                        mime="image/png",
                        key="spike_desc_download"
                    )

        if "━━ Wagon Wheel - vs All Types" in plot_types:
            st.markdown("<h2 style='text-align: center;'>Wagon Wheel - All Bowler Types</h2>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([2, 2, 2])
            
            with col1:
                st.markdown("## Customize Plot Info")
                show_title_all_kind = st.checkbox("Show Plot Title", value=True, key="whl_all_kind_title")
                show_legend_all_kind = st.checkbox("Show Legend", value=True, key="whl_all_kind_legend")
                show_summary_all_kind = st.checkbox("Show Runs Summary", value=True, key="whl_all_kind_summary")
                
                show_shots_breakdown_all_kind = st.checkbox("Show Shots Breakdown", value=True, key="whl_all_kind_shots_breakdown")
                if show_shots_breakdown_all_kind:
                    shots_breakdown_options_all_kind = st.multiselect(
                        "Shots to Display",
                        options=['0s', '1s', '2s', '3s', '4s', '6s'],
                        default=['0s', '1s', '2s', '4s', '6s'],
                        key="whl_all_kind_shots_options",
                        help="Select which run types to display in breakdown"
                    )
                else:
                    shots_breakdown_options_all_kind = []
                
                runs_count_all_kind = st.checkbox("Show Runs Count", value=True, key="whl_all_kind_runs")
                show_fours_sixes_all_kind = st.checkbox("Show 4s and 6s", value=True, key="whl_all_kind_fs")
                show_bowler_all_kind = st.checkbox("Show Bowler", value=True, key="whl_all_kind_bowler")
                show_control_all_kind = st.checkbox("Show Control %", value=True, key="whl_all_kind_control")
                show_prod_shot_all_kind = st.checkbox("Show Productive Shot", value=True, key="whl_all_kind_prod")
                show_overs_all_kind = st.checkbox("Show Overs", value=True, key="whl_all_kind_overs")
                show_phase_all_kind = st.checkbox("Show Phase", value=True, key="whl_all_kind_phase")
                show_ground_all_kind = st.checkbox("Show Ground Image", value=True, key="whl_all_kind_ground")
                show_bowl_type_all_kind = st.checkbox("Show Bowl Type", value=True, key="whl_all_kind_bowl_type")
                show_bowl_kind_all_kind = st.checkbox("Show Bowl Pace", value=True, key="whl_all_kind_bowl_kind")
                show_bowl_arm_all_kind = st.checkbox("Show Bowl Arm", value=True, key="whl_all_kind_bowl_arm")
                show_venue_all_kind = st.checkbox("Show Venue", value=True, key="whl_all_kind_venue")

            with col3:
                st.markdown("## Run Filter (Wagon Wheel)")

                if "run_init_whl_all_kind" not in st.session_state:
                    st.session_state["run_all_whl_all_kind"] = True
                    for i in range(7):
                        st.session_state[f'run_{i}_whl_all_kind'] = True
                    st.session_state["run_init_whl_all_kind"] = True

                def sync_all_to_individual_whl_all_kind():
                    all_selected = st.session_state["run_all_whl_all_kind"]
                    for i in range(7):
                        st.session_state[f'run_{i}_whl_all_kind'] = all_selected

                def sync_individual_to_all_whl_all_kind():
                    all_selected = all(st.session_state[f'run_{i}_whl_all_kind'] for i in range(7))
                    st.session_state["run_all_whl_all_kind"] = all_selected

                st.checkbox("All", key="run_all_whl_all_kind", on_change=sync_all_to_individual_whl_all_kind)

                for i in range(7):
                    st.checkbox(str(i), key=f'run_{i}_whl_all_kind', on_change=sync_individual_to_all_whl_all_kind)

                individual_selected_whl_all_kind = [i for i in range(7) if st.session_state.get(f'run_{i}_whl_all_kind', False)]

                if st.session_state["run_all_whl_all_kind"]:
                    filtered_runs_whl_all_kind = None
                elif individual_selected_whl_all_kind:
                    filtered_runs_whl_all_kind = individual_selected_whl_all_kind
                else:
                    filtered_runs_whl_all_kind = []
                    
            if filtered_runs_whl_all_kind == []:
                st.warning("Please select at least one run value to display the plot.")
            else:
                fig_whl_all_kind = spike_graph_plot_descriptive(
                    df=df,
                    player_name=selected_player_value,
                    pid=selected_pid,
                    inns=selected_inns,
                    mat_num=selected_mat_num,
                    team_bat=selected_team_value,
                    team_bowl=selected_team_bowl_value,
                    run_values=filtered_runs_whl_all_kind,
                    bowler_name=bowler_name,
                    bowler_id=bowler_id,
                    competition=selected_competition_value,
                    transparent=False,
                    over_values=over_values,
                    phase=phase,
                    ground=selected_ground,
                    mcode=selected_mcode,
                    date_from=date_from,
                    date_to=date_to,
                    title_components=title_components if show_title_all_kind else [],
                    bat_hand=bat_hand,
                    bowl_type=bowl_type,
                    bowl_kind=None,  # HARDCODED: All types (no filter)
                    bowl_arm=bowl_arm,
                    show_title=show_title_all_kind,
                    show_summary=show_summary_all_kind,
                    show_shots_breakdown=show_shots_breakdown_all_kind,
                    shots_breakdown_options=shots_breakdown_options_all_kind,
                    show_legend=show_legend_all_kind,
                    runs_count=runs_count_all_kind,
                    show_fours_sixes=show_fours_sixes_all_kind,
                    show_control=show_control_all_kind,
                    show_prod_shot=show_prod_shot_all_kind,
                    show_bowler=show_bowler_all_kind,
                    show_ground=show_ground_all_kind,
                    show_venue=show_venue_all_kind,
                    show_overs=show_overs_all_kind,
                    show_phase=show_phase_all_kind,
                    show_bowl_type=show_bowl_type_all_kind,
                    show_bowl_kind=show_bowl_kind_all_kind,
                    show_bowl_arm=show_bowl_arm_all_kind
                )
                with col2:
                    st.pyplot(fig_whl_all_kind)
            
            with col3:
                if fig_whl_all_kind:
                    buf = BytesIO()
                    fig_whl_all_kind.savefig(buf, format="png", transparent=False, dpi=300, bbox_inches='tight')
                    buf.seek(0)
                    st.download_button(
                        label="📅 Download Plot as PNG",
                        data=buf.getvalue(),
                        file_name=f"{selected_player}_whl_all_kind.png",
                        mime="image/png",
                        key="whl_all_kind_download"
                    )


        if "━━ Wagon Wheel - vs Pace" in plot_types:
            st.markdown("<h2 style='text-align: center;'>Wagon Wheel vs Pace Bowlers</h2>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([2, 2, 2])
            
            with col1:
                st.markdown("## Customize Plot Info")
                show_title_pace = st.checkbox("Show Plot Title", value=True, key="spike_desc_pace_title")
                show_legend_pace = st.checkbox("Show Legend", value=True, key="spike_desc_pace_legend")
                show_summary_pace = st.checkbox("Show Runs Summary", value=True, key="spike_desc_pace_summary")
                
                show_shots_breakdown_pace = st.checkbox("Show Shots Breakdown", value=True, key="spike_desc_pace_shots_breakdown")
                if show_shots_breakdown_pace:
                    shots_breakdown_options_pace = st.multiselect(
                        "Shots to Display",
                        options=['0s', '1s', '2s', '3s', '4s', '6s'],
                        default=['0s', '1s', '2s', '4s', '6s'],
                        key="spike_desc_pace_shots_options",
                        help="Select which run types to display in breakdown"
                    )
                else:
                    shots_breakdown_options_pace = []
                
                runs_count_pace = st.checkbox("Show Runs Count", value=True, key="spike_desc_pace_runs")
                show_fours_sixes_pace = st.checkbox("Show 4s and 6s", value=True, key="spike_desc_pace_fs")
                show_bowler_pace = st.checkbox("Show Bowler", value=True, key="spike_desc_pace_bowler")
                show_control_pace = st.checkbox("Show Control %", value=True, key="spike_desc_pace_control")
                show_prod_shot_pace = st.checkbox("Show Productive Shot", value=True, key="spike_desc_pace_prod")
                show_overs_pace = st.checkbox("Show Overs", value=True, key="spike_desc_pace_overs")
                show_phase_pace = st.checkbox("Show Phase", value=True, key="spike_desc_pace_phase")
                show_ground_pace = st.checkbox("Show Ground Image", value=True, key="spike_desc_pace_ground")
                show_bowl_type_pace = st.checkbox("Show Bowl Type", value=True, key="spike_desc_pace_bowl_type")
                show_bowl_kind_pace = st.checkbox("Show Bowl Pace", value=True, key="spike_desc_pace_bowl_kind")
                show_bowl_arm_pace = st.checkbox("Show Bowl Arm", value=True, key="spike_desc_pace_bowl_arm")
                show_venue_pace = st.checkbox("Show Venue", value=True, key="spike_desc_pace_venue")

            with col3:
                st.markdown("## Run Filter (Wagon Wheel)")

                if "run_init_spike_desc_pace" not in st.session_state:
                    st.session_state["run_all_spike_desc_pace"] = True
                    for i in range(7):
                        st.session_state[f'run_{i}_spike_desc_pace'] = True
                    st.session_state["run_init_spike_desc_pace"] = True

                def sync_all_to_individual_spike_desc_pace():
                    all_selected = st.session_state["run_all_spike_desc_pace"]
                    for i in range(7):
                        st.session_state[f'run_{i}_spike_desc_pace'] = all_selected

                def sync_individual_to_all_spike_desc_pace():
                    all_selected = all(st.session_state[f'run_{i}_spike_desc_pace'] for i in range(7))
                    st.session_state["run_all_spike_desc_pace"] = all_selected

                st.checkbox("All", key="run_all_spike_desc_pace", on_change=sync_all_to_individual_spike_desc_pace)

                for i in range(7):
                    st.checkbox(str(i), key=f'run_{i}_spike_desc_pace', on_change=sync_individual_to_all_spike_desc_pace)

                individual_selected_spike_desc_pace = [i for i in range(7) if st.session_state.get(f'run_{i}_spike_desc_pace', False)]

                if st.session_state["run_all_spike_desc_pace"]:
                    filtered_runs_spike_desc_pace = None
                elif individual_selected_spike_desc_pace:
                    filtered_runs_spike_desc_pace = individual_selected_spike_desc_pace
                else:
                    filtered_runs_spike_desc_pace = []
                    
            if filtered_runs_spike_desc_pace == []:
                st.warning("Please select at least one run value to display the plot.")
            else:
                fig_spike_desc_pace = spike_graph_plot_descriptive(
                    df=df,
                    player_name=selected_player_value,
                    pid=selected_pid,
                    inns=selected_inns,
                    mat_num=selected_mat_num,
                    team_bat=selected_team_value,
                    team_bowl=selected_team_bowl_value,
                    run_values=filtered_runs_spike_desc_pace,
                    bowler_name=bowler_name,
                    bowler_id=bowler_id,
                    competition=selected_competition_value,
                    transparent=False,
                    over_values=over_values,
                    phase=phase,
                    ground=selected_ground,
                    mcode=selected_mcode,
                    date_from=date_from,
                    date_to=date_to,
                    title_components=title_components if show_title_pace else [],
                    bat_hand=bat_hand,
                    bowl_type=bowl_type,
                    bowl_kind=["pace bowler", "Pace"],  # HARDCODED: vs Pace
                    bowl_arm=bowl_arm,
                    show_title=show_title_pace,
                    show_summary=show_summary_pace,
                    show_shots_breakdown=show_shots_breakdown_pace,
                    shots_breakdown_options=shots_breakdown_options_pace,
                    show_legend=show_legend_pace,
                    runs_count=runs_count_pace,
                    show_fours_sixes=show_fours_sixes_pace,
                    show_control=show_control_pace,
                    show_prod_shot=show_prod_shot_pace,
                    show_bowler=show_bowler_pace,
                    show_ground=show_ground_pace,
                    show_venue=show_venue_pace,
                    show_overs=show_overs_pace,
                    show_phase=show_phase_pace,
                    show_bowl_type=show_bowl_type_pace,
                    show_bowl_kind=show_bowl_kind_pace,
                    show_bowl_arm=show_bowl_arm_pace
                )
                with col2:
                    st.pyplot(fig_spike_desc_pace)
            
            with col3:
                if fig_spike_desc_pace:
                    buf = BytesIO()
                    fig_spike_desc_pace.savefig(buf, format="png", transparent=False, dpi=300, bbox_inches='tight')
                    buf.seek(0)
                    st.download_button(
                        label="📅 Download Plot as PNG",
                        data=buf.getvalue(),
                        file_name=f"{selected_player}_wagon_wheel_descriptive_vs_pace.png",
                        mime="image/png",
                        key="spike_desc_pace_download"
                    )

        if "━━ Wagon Wheel - vs Spin" in plot_types:
            st.markdown("<h2 style='text-align: center;'>Wagon Wheel vs Spin Bowlers</h2>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([2, 2, 2])
            
            with col1:
                st.markdown("## Customize Plot Info")
                show_title_spin = st.checkbox("Show Plot Title", value=True, key="spike_desc_spin_title")
                show_legend_spin = st.checkbox("Show Legend", value=True, key="spike_desc_spin_legend")
                show_summary_spin = st.checkbox("Show Runs Summary", value=True, key="spike_desc_spin_summary")
                
                show_shots_breakdown_spin = st.checkbox("Show Shots Breakdown", value=True, key="spike_desc_spin_shots_breakdown")
                if show_shots_breakdown_spin:
                    shots_breakdown_options_spin = st.multiselect(
                        "Shots to Display",
                        options=['0s', '1s', '2s', '3s', '4s', '6s'],
                        default=['0s', '1s', '2s', '4s', '6s'],
                        key="spike_desc_spin_shots_options",
                        help="Select which run types to display in breakdown"
                    )
                else:
                    shots_breakdown_options_spin = []
                
                runs_count_spin = st.checkbox("Show Runs Count", value=True, key="spike_desc_spin_runs")
                show_fours_sixes_spin = st.checkbox("Show 4s and 6s", value=True, key="spike_desc_spin_fs")
                show_bowler_spin = st.checkbox("Show Bowler", value=True, key="spike_desc_spin_bowler")
                show_control_spin = st.checkbox("Show Control %", value=True, key="spike_desc_spin_control")
                show_prod_shot_spin = st.checkbox("Show Productive Shot", value=True, key="spike_desc_spin_prod")
                show_overs_spin = st.checkbox("Show Overs", value=True, key="spike_desc_spin_overs")
                show_phase_spin = st.checkbox("Show Phase", value=True, key="spike_desc_spin_phase")
                show_ground_spin = st.checkbox("Show Ground Image", value=True, key="spike_desc_spin_ground")
                show_bowl_type_spin = st.checkbox("Show Bowl Type", value=True, key="spike_desc_spin_bowl_type")
                show_bowl_kind_spin = st.checkbox("Show Bowl Pace", value=True, key="spike_desc_spin_bowl_kind")
                show_bowl_arm_spin = st.checkbox("Show Bowl Arm", value=True, key="spike_desc_spin_bowl_arm")
                show_venue_spin = st.checkbox("Show Venue", value=True, key="spike_desc_spin_venue")

            with col3:
                st.markdown("## Run Filter (Wagon Wheel)")

                if "run_init_spike_desc_spin" not in st.session_state:
                    st.session_state["run_all_spike_desc_spin"] = True
                    for i in range(7):
                        st.session_state[f'run_{i}_spike_desc_spin'] = True
                    st.session_state["run_init_spike_desc_spin"] = True

                def sync_all_to_individual_spike_desc_spin():
                    all_selected = st.session_state["run_all_spike_desc_spin"]
                    for i in range(7):
                        st.session_state[f'run_{i}_spike_desc_spin'] = all_selected

                def sync_individual_to_all_spike_desc_spin():
                    all_selected = all(st.session_state[f'run_{i}_spike_desc_spin'] for i in range(7))
                    st.session_state["run_all_spike_desc_spin"] = all_selected

                st.checkbox("All", key="run_all_spike_desc_spin", on_change=sync_all_to_individual_spike_desc_spin)

                for i in range(7):
                    st.checkbox(str(i), key=f'run_{i}_spike_desc_spin', on_change=sync_individual_to_all_spike_desc_spin)

                individual_selected_spike_desc_spin = [i for i in range(7) if st.session_state.get(f'run_{i}_spike_desc_spin', False)]

                if st.session_state["run_all_spike_desc_spin"]:
                    filtered_runs_spike_desc_spin = None
                elif individual_selected_spike_desc_spin:
                    filtered_runs_spike_desc_spin = individual_selected_spike_desc_spin
                else:
                    filtered_runs_spike_desc_spin = []
                    
            if filtered_runs_spike_desc_spin == []:
                st.warning("Please select at least one run value to display the plot.")
            else:
                fig_spike_desc_spin = spike_graph_plot_descriptive(
                    df=df,
                    player_name=selected_player_value,
                    pid=selected_pid,
                    inns=selected_inns,
                    mat_num=selected_mat_num,
                    team_bat=selected_team_value,
                    team_bowl=selected_team_bowl_value,
                    run_values=filtered_runs_spike_desc_spin,
                    bowler_name=bowler_name,
                    bowler_id=bowler_id,
                    competition=selected_competition_value,
                    transparent=False,
                    over_values=over_values,
                    phase=phase,
                    ground=selected_ground,
                    mcode=selected_mcode,
                    date_from=date_from,
                    date_to=date_to,
                    title_components=title_components if show_title_spin else [],
                    bat_hand=bat_hand,
                    bowl_type=bowl_type,
                    bowl_kind=["spin bowler", "Spin"],  # HARDCODED: vs Spin
                    bowl_arm=bowl_arm,
                    show_title=show_title_spin,
                    show_summary=show_summary_spin,
                    show_shots_breakdown=show_shots_breakdown_spin,
                    shots_breakdown_options=shots_breakdown_options_spin,
                    show_legend=show_legend_spin,
                    runs_count=runs_count_spin,
                    show_fours_sixes=show_fours_sixes_spin,
                    show_control=show_control_spin,
                    show_prod_shot=show_prod_shot_spin,
                    show_bowler=show_bowler_spin,
                    show_ground=show_ground_spin,
                    show_venue=show_venue_spin,
                    show_overs=show_overs_spin,
                    show_phase=show_phase_spin,
                    show_bowl_type=show_bowl_type_spin,
                    show_bowl_kind=show_bowl_kind_spin,
                    show_bowl_arm=show_bowl_arm_spin
                )
                with col2:
                    st.pyplot(fig_spike_desc_spin)
            
            with col3:
                if fig_spike_desc_spin:
                    buf = BytesIO()
                    fig_spike_desc_spin.savefig(buf, format="png", transparent=False, dpi=300, bbox_inches='tight')
                    buf.seek(0)
                    st.download_button(
                        label="📅 Download Plot as PNG",
                        data=buf.getvalue(),
                        file_name=f"{selected_player}_wagon_wheel_descriptive_vs_spin.png",
                        mime="image/png",
                        key="spike_desc_spin_download"
                    )

        if "Wagon Wheel (Trans)" in plot_types:
            st.markdown("<h2 style='text-align: center;'>Wagon Wheel (Trans)</h2>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([2, 2, 2])
            
            with col1:
                st.markdown("## Customize Plot Info")
                show_title_desc_trans = st.checkbox("Show Plot Title", value=True, key="spike_desc_trans_title")
                show_legend_desc_trans = st.checkbox("Show Legend", value=True, key="spike_desc_trans_legend")
                show_summary_desc_trans = st.checkbox("Show Runs Summary", value=True, key="spike_desc_trans_summary")
                
                show_shots_breakdown_desc_trans = st.checkbox("Show Shots Breakdown", value=True, key="spike_desc_trans_shots_breakdown")
                if show_shots_breakdown_desc_trans:
                    shots_breakdown_options_desc_trans = st.multiselect(
                        "Shots to Display",
                        options=['0s', '1s', '2s', '3s', '4s', '6s'],
                        default=['0s', '1s', '2s', '4s', '6s'],
                        key="spike_desc_trans_shots_options",
                        help="Select which run types to display in breakdown"
                    )
                else:
                    shots_breakdown_options_desc_trans = []
                
                runs_count_desc_trans = st.checkbox("Show Runs Count", value=True, key="spike_desc_trans_runs")
                show_fours_sixes_desc_trans = st.checkbox("Show 4s and 6s", value=True, key="spike_desc_trans_fs")
                show_bowler_desc_trans = st.checkbox("Show Bowler", value=True, key="spike_desc_trans_bowler")
                show_control_desc_trans = st.checkbox("Show Control %", value=True, key="spike_desc_trans_control")
                show_prod_shot_desc_trans = st.checkbox("Show Productive Shot", value=True, key="spike_desc_trans_prod")
                show_overs_desc_trans = st.checkbox("Show Overs", value=True, key="spike_desc_trans_overs")
                show_phase_desc_trans = st.checkbox("Show Phase", value=True, key="spike_desc_trans_phase")
                show_ground_desc_trans = st.checkbox("Show Ground Image", value=True, key="spike_desc_trans_ground")
                show_bowl_type_desc_trans = st.checkbox("Show Bowl Type", value=True, key="spike_desc_trans_bowl_type")
                show_bowl_kind_desc_trans = st.checkbox("Show Bowl Pace", value=True, key="spike_desc_trans_bowl_kind")
                show_bowl_arm_desc_trans = st.checkbox("Show Bowl Arm", value=True, key="spike_desc_trans_bowl_arm")
                show_venue_desc_trans = st.checkbox("Show Venue", value=True, key="spike_desc_trans_venue")

            with col3:
                st.markdown("## Run Filter (Wagon Wheel)")

                if "run_init_spike_desc_trans" not in st.session_state:
                    st.session_state.run_init_spike_desc_trans = True
                    for i in range(7):
                        st.session_state[f'run_{i}_spike_desc_trans'] = True
                    st.session_state["run_all_spike_desc_trans"] = True

                def sync_all_to_individual_spike_desc_trans():
                    for i in range(7):
                        st.session_state[f'run_{i}_spike_desc_trans'] = st.session_state["run_all_spike_desc_trans"]

                def sync_individual_to_all_spike_desc_trans():
                    if all(st.session_state.get(f'run_{i}_spike_desc_trans', False) for i in range(7)):
                        st.session_state["run_all_spike_desc_trans"] = True

                st.checkbox("All", key="run_all_spike_desc_trans", on_change=sync_all_to_individual_spike_desc_trans)

                for i in range(7):
                    st.checkbox(str(i), key=f'run_{i}_spike_desc_trans', on_change=sync_individual_to_all_spike_desc_trans)

                individual_selected_spike_desc_trans = [i for i in range(7) if st.session_state.get(f'run_{i}_spike_desc_trans', False)]

                if st.session_state["run_all_spike_desc_trans"]:
                    filtered_runs_spike_desc_trans = None
                elif individual_selected_spike_desc_trans:
                    filtered_runs_spike_desc_trans = individual_selected_spike_desc_trans
                else:
                    filtered_runs_spike_desc_trans = []
                    
            if filtered_runs_spike_desc_trans == []:
                st.warning("Please select at least one run value to display the plot.")
            else:
                fig_spike_desc_trans = spike_graph_plot_descriptive(
                    df=df,
                    player_name=selected_player_value,
                    pid=selected_pid,
                    inns=selected_inns,
                    mat_num=selected_mat_num,
                    team_bat=selected_team_value,
                    team_bowl=selected_team_bowl_value,
                    run_values=filtered_runs_spike_desc_trans,
                    bowler_name=bowler_name,
                    bowler_id=bowler_id,
                    competition=selected_competition_value,
                    transparent=True,
                    over_values=over_values,
                    phase=phase,
                    ground=selected_ground,
                    mcode=selected_mcode,
                    date_from=date_from,
                    date_to=date_to,
                    title_components=title_components if show_title_desc_trans else [],
                    bat_hand=bat_hand,
                    bowl_type=bowl_type,
                    bowl_kind=bowl_kind,
                    bowl_arm=bowl_arm,
                    show_title=show_title_desc_trans,
                    show_summary=show_summary_desc_trans,
                    show_shots_breakdown=show_shots_breakdown_desc_trans,
                    shots_breakdown_options=shots_breakdown_options_desc_trans,
                    show_legend=show_legend_desc_trans,
                    runs_count=runs_count_desc_trans,
                    show_fours_sixes=show_fours_sixes_desc_trans,
                    show_control=show_control_desc_trans,
                    show_prod_shot=show_prod_shot_desc_trans,
                    show_bowler=show_bowler_desc_trans,
                    show_ground=show_ground_desc_trans,
                    show_venue=show_venue_desc_trans,
                    show_overs=show_overs_desc_trans,
                    show_phase=show_phase_desc_trans,
                    show_bowl_type=show_bowl_type_desc_trans,
                    show_bowl_kind=show_bowl_kind_desc_trans,
                    show_bowl_arm=show_bowl_arm_desc_trans
                )
                with col2:
                    st.pyplot(fig_spike_desc_trans)
            
            with col3:
                if fig_spike_desc_trans:
                    buf = BytesIO()
                    fig_spike_desc_trans.savefig(buf, format="png", transparent=True, dpi=300, bbox_inches='tight')
                    buf.seek(0)
                    st.download_button(
                        label="📅 Download Plot as PNG",
                        data=buf.getvalue(),
                        file_name=f"{selected_player}_wagon_wheel_descriptive_transparent.png",
                        mime="image/png",
                        key="spike_desc_trans_download"
                    )

        if "━━ Wagon Wheel - All Phases" in plot_types:
            st.markdown("<h2 style='text-align: center;'>Wagon Wheel - All Phases</h2>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([2, 2, 2])
            
            with col1:
                st.markdown("## Customize Plot Info")
                show_title_phs_all = st.checkbox("Show Plot Title", value=True, key="whl_phs_all_title")
                show_legend_phs_all = st.checkbox("Show Legend", value=True, key="whl_phs_all_legend")
                show_summary_phs_all = st.checkbox("Show Runs Summary", value=True, key="whl_phs_all_summary")
                
                show_shots_breakdown_phs_all = st.checkbox("Show Shots Breakdown", value=True, key="whl_phs_all_shots_breakdown")
                if show_shots_breakdown_phs_all:
                    shots_breakdown_options_phs_all = st.multiselect(
                        "Shots to Display",
                        options=['0s', '1s', '2s', '3s', '4s', '6s'],
                        default=['0s', '1s', '2s', '4s', '6s'],
                        key="whl_phs_all_shots_options",
                        help="Select which run types to display in breakdown"
                    )
                else:
                    shots_breakdown_options_phs_all = []
                
                runs_count_phs_all = st.checkbox("Show Runs Count", value=True, key="whl_phs_all_runs")
                show_fours_sixes_phs_all = st.checkbox("Show 4s and 6s", value=True, key="whl_phs_all_fs")
                show_bowler_phs_all = st.checkbox("Show Bowler", value=True, key="whl_phs_all_bowler")
                show_control_phs_all = st.checkbox("Show Control %", value=True, key="whl_phs_all_control")
                show_prod_shot_phs_all = st.checkbox("Show Productive Shot", value=True, key="whl_phs_all_prod")
                show_overs_phs_all = st.checkbox("Show Overs", value=True, key="whl_phs_all_overs")
                show_phase_phs_all = st.checkbox("Show Phase", value=True, key="whl_phs_all_phase")
                show_ground_phs_all = st.checkbox("Show Ground Image", value=True, key="whl_phs_all_ground")
                show_bowl_type_phs_all = st.checkbox("Show Bowl Type", value=True, key="whl_phs_all_bowl_type")
                show_bowl_kind_phs_all = st.checkbox("Show Bowl Pace", value=True, key="whl_phs_all_bowl_kind")
                show_bowl_arm_phs_all = st.checkbox("Show Bowl Arm", value=True, key="whl_phs_all_bowl_arm")
                show_venue_phs_all = st.checkbox("Show Venue", value=True, key="whl_phs_all_venue")

            with col3:
                st.markdown("## Run Filter (Wagon Wheel)")

                if "run_init_whl_phs_all" not in st.session_state:
                    st.session_state["run_all_whl_phs_all"] = True
                    for i in range(7):
                        st.session_state[f'run_{i}_whl_phs_all'] = True
                    st.session_state["run_init_whl_phs_all"] = True

                def sync_all_to_individual_whl_phs_all():
                    all_selected = st.session_state["run_all_whl_phs_all"]
                    for i in range(7):
                        st.session_state[f'run_{i}_whl_phs_all'] = all_selected

                def sync_individual_to_all_whl_phs_all():
                    all_selected = all(st.session_state[f'run_{i}_whl_phs_all'] for i in range(7))
                    st.session_state["run_all_whl_phs_all"] = all_selected

                st.checkbox("All", key="run_all_whl_phs_all", on_change=sync_all_to_individual_whl_phs_all)

                for i in range(7):
                    st.checkbox(str(i), key=f'run_{i}_whl_phs_all', on_change=sync_individual_to_all_whl_phs_all)

                individual_selected_whl_phs_all = [i for i in range(7) if st.session_state.get(f'run_{i}_whl_phs_all', False)]

                if st.session_state["run_all_whl_phs_all"]:
                    filtered_runs_whl_phs_all = None
                elif individual_selected_whl_phs_all:
                    filtered_runs_whl_phs_all = individual_selected_whl_phs_all
                else:
                    filtered_runs_whl_phs_all = []
                    
            if filtered_runs_whl_phs_all == []:
                st.warning("Please select at least one run value to display the plot.")
            else:
                fig_whl_phs_all = spike_graph_plot_descriptive(
                    df=df,
                    player_name=selected_player_value,
                    pid=selected_pid,
                    inns=selected_inns,
                    mat_num=selected_mat_num,
                    team_bat=selected_team_value,
                    team_bowl=selected_team_bowl_value,
                    run_values=filtered_runs_whl_phs_all,
                    bowler_name=bowler_name,
                    bowler_id=bowler_id,
                    competition=selected_competition_value,
                    transparent=False,
                    over_values=over_values,
                    phase=None,  # HARDCODED: All phases
                    ground=selected_ground,
                    mcode=selected_mcode,
                    date_from=date_from,
                    date_to=date_to,
                    title_components=title_components if show_title_phs_all else [],
                    bat_hand=bat_hand,
                    bowl_type=bowl_type,
                    bowl_kind=bowl_kind,
                    bowl_arm=bowl_arm,
                    show_title=show_title_phs_all,
                    show_summary=show_summary_phs_all,
                    show_shots_breakdown=show_shots_breakdown_phs_all,
                    shots_breakdown_options=shots_breakdown_options_phs_all,
                    show_legend=show_legend_phs_all,
                    runs_count=runs_count_phs_all,
                    show_fours_sixes=show_fours_sixes_phs_all,
                    show_control=show_control_phs_all,
                    show_prod_shot=show_prod_shot_phs_all,
                    show_bowler=show_bowler_phs_all,
                    show_ground=show_ground_phs_all,
                    show_venue=show_venue_phs_all,
                    show_overs=show_overs_phs_all,
                    show_phase=show_phase_phs_all,
                    show_bowl_type=show_bowl_type_phs_all,
                    show_bowl_kind=show_bowl_kind_phs_all,
                    show_bowl_arm=show_bowl_arm_phs_all
                )
                with col2:
                    st.pyplot(fig_whl_phs_all)
            
            with col3:
                if fig_whl_phs_all:
                    buf = BytesIO()
                    fig_whl_phs_all.savefig(buf, format="png", transparent=False, dpi=300, bbox_inches='tight')
                    buf.seek(0)
                    st.download_button(
                        label="📅 Download Plot as PNG",
                        data=buf.getvalue(),
                        file_name=f"{selected_player}_whl_phase_all.png",
                        mime="image/png",
                        key="whl_phs_all_download"
                    )

        if "━━ Wagon Wheel - Powerplay" in plot_types:
            st.markdown("<h2 style='text-align: center;'>Wagon Wheel - Powerplay (1-6)</h2>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([2, 2, 2])
            
            with col1:
                st.markdown("## Customize Plot Info")
                show_title_phs_pp = st.checkbox("Show Plot Title", value=True, key="whl_phs_pp_title")
                show_legend_phs_pp = st.checkbox("Show Legend", value=True, key="whl_phs_pp_legend")
                show_summary_phs_pp = st.checkbox("Show Runs Summary", value=True, key="whl_phs_pp_summary")
                
                show_shots_breakdown_phs_pp = st.checkbox("Show Shots Breakdown", value=True, key="whl_phs_pp_shots_breakdown")
                if show_shots_breakdown_phs_pp:
                    shots_breakdown_options_phs_pp = st.multiselect(
                        "Shots to Display",
                        options=['0s', '1s', '2s', '3s', '4s', '6s'],
                        default=['0s', '1s', '2s', '4s', '6s'],
                        key="whl_phs_pp_shots_options",
                        help="Select which run types to display in breakdown"
                    )
                else:
                    shots_breakdown_options_phs_pp = []
                
                runs_count_phs_pp = st.checkbox("Show Runs Count", value=True, key="whl_phs_pp_runs")
                show_fours_sixes_phs_pp = st.checkbox("Show 4s and 6s", value=True, key="whl_phs_pp_fs")
                show_bowler_phs_pp = st.checkbox("Show Bowler", value=True, key="whl_phs_pp_bowler")
                show_control_phs_pp = st.checkbox("Show Control %", value=True, key="whl_phs_pp_control")
                show_prod_shot_phs_pp = st.checkbox("Show Productive Shot", value=True, key="whl_phs_pp_prod")
                show_overs_phs_pp = st.checkbox("Show Overs", value=True, key="whl_phs_pp_overs")
                show_phase_phs_pp = st.checkbox("Show Phase", value=True, key="whl_phs_pp_phase")
                show_ground_phs_pp = st.checkbox("Show Ground Image", value=True, key="whl_phs_pp_ground")
                show_bowl_type_phs_pp = st.checkbox("Show Bowl Type", value=True, key="whl_phs_pp_bowl_type")
                show_bowl_kind_phs_pp = st.checkbox("Show Bowl Pace", value=True, key="whl_phs_pp_bowl_kind")
                show_bowl_arm_phs_pp = st.checkbox("Show Bowl Arm", value=True, key="whl_phs_pp_bowl_arm")
                show_venue_phs_pp = st.checkbox("Show Venue", value=True, key="whl_phs_pp_venue")

            with col3:
                st.markdown("## Run Filter (Wagon Wheel)")

                if "run_init_whl_phs_pp" not in st.session_state:
                    st.session_state["run_all_whl_phs_pp"] = True
                    for i in range(7):
                        st.session_state[f'run_{i}_whl_phs_pp'] = True
                    st.session_state["run_init_whl_phs_pp"] = True

                def sync_all_to_individual_whl_phs_pp():
                    all_selected = st.session_state["run_all_whl_phs_pp"]
                    for i in range(7):
                        st.session_state[f'run_{i}_whl_phs_pp'] = all_selected

                def sync_individual_to_all_whl_phs_pp():
                    all_selected = all(st.session_state[f'run_{i}_whl_phs_pp'] for i in range(7))
                    st.session_state["run_all_whl_phs_pp"] = all_selected

                st.checkbox("All", key="run_all_whl_phs_pp", on_change=sync_all_to_individual_whl_phs_pp)

                for i in range(7):
                    st.checkbox(str(i), key=f'run_{i}_whl_phs_pp', on_change=sync_individual_to_all_whl_phs_pp)

                individual_selected_whl_phs_pp = [i for i in range(7) if st.session_state.get(f'run_{i}_whl_phs_pp', False)]

                if st.session_state["run_all_whl_phs_pp"]:
                    filtered_runs_whl_phs_pp = None
                elif individual_selected_whl_phs_pp:
                    filtered_runs_whl_phs_pp = individual_selected_whl_phs_pp
                else:
                    filtered_runs_whl_phs_pp = []
                    
            if filtered_runs_whl_phs_pp == []:
                st.warning("Please select at least one run value to display the plot.")
            else:
                fig_whl_phs_pp = spike_graph_plot_descriptive(
                    df=df,
                    player_name=selected_player_value,
                    pid=selected_pid,
                    inns=selected_inns,
                    mat_num=selected_mat_num,
                    team_bat=selected_team_value,
                    team_bowl=selected_team_bowl_value,
                    run_values=filtered_runs_whl_phs_pp,
                    bowler_name=bowler_name,
                    bowler_id=bowler_id,
                    competition=selected_competition_value,
                    transparent=False,
                    over_values=over_values,
                    phase=[1],  # HARDCODED: Powerplay (1-6)
                    ground=selected_ground,
                    mcode=selected_mcode,
                    date_from=date_from,
                    date_to=date_to,
                    title_components=title_components if show_title_phs_pp else [],
                    bat_hand=bat_hand,
                    bowl_type=bowl_type,
                    bowl_kind=bowl_kind,
                    bowl_arm=bowl_arm,
                    show_title=show_title_phs_pp,
                    show_summary=show_summary_phs_pp,
                    show_shots_breakdown=show_shots_breakdown_phs_pp,
                    shots_breakdown_options=shots_breakdown_options_phs_pp,
                    show_legend=show_legend_phs_pp,
                    runs_count=runs_count_phs_pp,
                    show_fours_sixes=show_fours_sixes_phs_pp,
                    show_control=show_control_phs_pp,
                    show_prod_shot=show_prod_shot_phs_pp,
                    show_bowler=show_bowler_phs_pp,
                    show_ground=show_ground_phs_pp,
                    show_venue=show_venue_phs_pp,
                    show_overs=show_overs_phs_pp,
                    show_phase=show_phase_phs_pp,
                    show_bowl_type=show_bowl_type_phs_pp,
                    show_bowl_kind=show_bowl_kind_phs_pp,
                    show_bowl_arm=show_bowl_arm_phs_pp
                )
                with col2:
                    st.pyplot(fig_whl_phs_pp)
            
            with col3:
                if fig_whl_phs_pp:
                    buf = BytesIO()
                    fig_whl_phs_pp.savefig(buf, format="png", transparent=False, dpi=300, bbox_inches='tight')
                    buf.seek(0)
                    st.download_button(
                        label="📅 Download Plot as PNG",
                        data=buf.getvalue(),
                        file_name=f"{selected_player}_whl_phase_pp.png",
                        mime="image/png",
                        key="whl_phs_pp_download"
                    )

        if "━━ Wagon Wheel - Middle" in plot_types:
            st.markdown("<h2 style='text-align: center;'>Wagon Wheel - Middle (7-15)</h2>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([2, 2, 2])
            
            with col1:
                st.markdown("## Customize Plot Info")
                show_title_phs_mid = st.checkbox("Show Plot Title", value=True, key="whl_phs_mid_title")
                show_legend_phs_mid = st.checkbox("Show Legend", value=True, key="whl_phs_mid_legend")
                show_summary_phs_mid = st.checkbox("Show Runs Summary", value=True, key="whl_phs_mid_summary")
                
                show_shots_breakdown_phs_mid = st.checkbox("Show Shots Breakdown", value=True, key="whl_phs_mid_shots_breakdown")
                if show_shots_breakdown_phs_mid:
                    shots_breakdown_options_phs_mid = st.multiselect(
                        "Shots to Display",
                        options=['0s', '1s', '2s', '3s', '4s', '6s'],
                        default=['0s', '1s', '2s', '4s', '6s'],
                        key="whl_phs_mid_shots_options",
                        help="Select which run types to display in breakdown"
                    )
                else:
                    shots_breakdown_options_phs_mid = []
                
                runs_count_phs_mid = st.checkbox("Show Runs Count", value=True, key="whl_phs_mid_runs")
                show_fours_sixes_phs_mid = st.checkbox("Show 4s and 6s", value=True, key="whl_phs_mid_fs")
                show_bowler_phs_mid = st.checkbox("Show Bowler", value=True, key="whl_phs_mid_bowler")
                show_control_phs_mid = st.checkbox("Show Control %", value=True, key="whl_phs_mid_control")
                show_prod_shot_phs_mid = st.checkbox("Show Productive Shot", value=True, key="whl_phs_mid_prod")
                show_overs_phs_mid = st.checkbox("Show Overs", value=True, key="whl_phs_mid_overs")
                show_phase_phs_mid = st.checkbox("Show Phase", value=True, key="whl_phs_mid_phase")
                show_ground_phs_mid = st.checkbox("Show Ground Image", value=True, key="whl_phs_mid_ground")
                show_bowl_type_phs_mid = st.checkbox("Show Bowl Type", value=True, key="whl_phs_mid_bowl_type")
                show_bowl_kind_phs_mid = st.checkbox("Show Bowl Pace", value=True, key="whl_phs_mid_bowl_kind")
                show_bowl_arm_phs_mid = st.checkbox("Show Bowl Arm", value=True, key="whl_phs_mid_bowl_arm")
                show_venue_phs_mid = st.checkbox("Show Venue", value=True, key="whl_phs_mid_venue")

            with col3:
                st.markdown("## Run Filter (Wagon Wheel)")

                if "run_init_whl_phs_mid" not in st.session_state:
                    st.session_state["run_all_whl_phs_mid"] = True
                    for i in range(7):
                        st.session_state[f'run_{i}_whl_phs_mid'] = True
                    st.session_state["run_init_whl_phs_mid"] = True

                def sync_all_to_individual_whl_phs_mid():
                    all_selected = st.session_state["run_all_whl_phs_mid"]
                    for i in range(7):
                        st.session_state[f'run_{i}_whl_phs_mid'] = all_selected

                def sync_individual_to_all_whl_phs_mid():
                    all_selected = all(st.session_state[f'run_{i}_whl_phs_mid'] for i in range(7))
                    st.session_state["run_all_whl_phs_mid"] = all_selected

                st.checkbox("All", key="run_all_whl_phs_mid", on_change=sync_all_to_individual_whl_phs_mid)

                for i in range(7):
                    st.checkbox(str(i), key=f'run_{i}_whl_phs_mid', on_change=sync_individual_to_all_whl_phs_mid)

                individual_selected_whl_phs_mid = [i for i in range(7) if st.session_state.get(f'run_{i}_whl_phs_mid', False)]

                if st.session_state["run_all_whl_phs_mid"]:
                    filtered_runs_whl_phs_mid = None
                elif individual_selected_whl_phs_mid:
                    filtered_runs_whl_phs_mid = individual_selected_whl_phs_mid
                else:
                    filtered_runs_whl_phs_mid = []
                    
            if filtered_runs_whl_phs_mid == []:
                st.warning("Please select at least one run value to display the plot.")
            else:
                fig_whl_phs_mid = spike_graph_plot_descriptive(
                    df=df,
                    player_name=selected_player_value,
                    pid=selected_pid,
                    inns=selected_inns,
                    mat_num=selected_mat_num,
                    team_bat=selected_team_value,
                    team_bowl=selected_team_bowl_value,
                    run_values=filtered_runs_whl_phs_mid,
                    bowler_name=bowler_name,
                    bowler_id=bowler_id,
                    competition=selected_competition_value,
                    transparent=False,
                    over_values=over_values,
                    phase=[2],  # HARDCODED: Middle (7-15)
                    ground=selected_ground,
                    mcode=selected_mcode,
                    date_from=date_from,
                    date_to=date_to,
                    title_components=title_components if show_title_phs_mid else [],
                    bat_hand=bat_hand,
                    bowl_type=bowl_type,
                    bowl_kind=bowl_kind,
                    bowl_arm=bowl_arm,
                    show_title=show_title_phs_mid,
                    show_summary=show_summary_phs_mid,
                    show_shots_breakdown=show_shots_breakdown_phs_mid,
                    shots_breakdown_options=shots_breakdown_options_phs_mid,
                    show_legend=show_legend_phs_mid,
                    runs_count=runs_count_phs_mid,
                    show_fours_sixes=show_fours_sixes_phs_mid,
                    show_control=show_control_phs_mid,
                    show_prod_shot=show_prod_shot_phs_mid,
                    show_bowler=show_bowler_phs_mid,
                    show_ground=show_ground_phs_mid,
                    show_venue=show_venue_phs_mid,
                    show_overs=show_overs_phs_mid,
                    show_phase=show_phase_phs_mid,
                    show_bowl_type=show_bowl_type_phs_mid,
                    show_bowl_kind=show_bowl_kind_phs_mid,
                    show_bowl_arm=show_bowl_arm_phs_mid
                )
                with col2:
                    st.pyplot(fig_whl_phs_mid)
            
            with col3:
                if fig_whl_phs_mid:
                    buf = BytesIO()
                    fig_whl_phs_mid.savefig(buf, format="png", transparent=False, dpi=300, bbox_inches='tight')
                    buf.seek(0)
                    st.download_button(
                        label="📅 Download Plot as PNG",
                        data=buf.getvalue(),
                        file_name=f"{selected_player}_whl_phase_mid.png",
                        mime="image/png",
                        key="whl_phs_mid_download"
                    )

        if "━━ Wagon Wheel - Slog" in plot_types:
            st.markdown("<h2 style='text-align: center;'>Wagon Wheel - Slog (16-20)</h2>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([2, 2, 2])
            
            with col1:
                st.markdown("## Customize Plot Info")
                show_title_phs_slog = st.checkbox("Show Plot Title", value=True, key="whl_phs_slog_title")
                show_legend_phs_slog = st.checkbox("Show Legend", value=True, key="whl_phs_slog_legend")
                show_summary_phs_slog = st.checkbox("Show Runs Summary", value=True, key="whl_phs_slog_summary")
                
                show_shots_breakdown_phs_slog = st.checkbox("Show Shots Breakdown", value=True, key="whl_phs_slog_shots_breakdown")
                if show_shots_breakdown_phs_slog:
                    shots_breakdown_options_phs_slog = st.multiselect(
                        "Shots to Display",
                        options=['0s', '1s', '2s', '3s', '4s', '6s'],
                        default=['0s', '1s', '2s', '4s', '6s'],
                        key="whl_phs_slog_shots_options",
                        help="Select which run types to display in breakdown"
                    )
                else:
                    shots_breakdown_options_phs_slog = []
                
                runs_count_phs_slog = st.checkbox("Show Runs Count", value=True, key="whl_phs_slog_runs")
                show_fours_sixes_phs_slog = st.checkbox("Show 4s and 6s", value=True, key="whl_phs_slog_fs")
                show_bowler_phs_slog = st.checkbox("Show Bowler", value=True, key="whl_phs_slog_bowler")
                show_control_phs_slog = st.checkbox("Show Control %", value=True, key="whl_phs_slog_control")
                show_prod_shot_phs_slog = st.checkbox("Show Productive Shot", value=True, key="whl_phs_slog_prod")
                show_overs_phs_slog = st.checkbox("Show Overs", value=True, key="whl_phs_slog_overs")
                show_phase_phs_slog = st.checkbox("Show Phase", value=True, key="whl_phs_slog_phase")
                show_ground_phs_slog = st.checkbox("Show Ground Image", value=True, key="whl_phs_slog_ground")
                show_bowl_type_phs_slog = st.checkbox("Show Bowl Type", value=True, key="whl_phs_slog_bowl_type")
                show_bowl_kind_phs_slog = st.checkbox("Show Bowl Pace", value=True, key="whl_phs_slog_bowl_kind")
                show_bowl_arm_phs_slog = st.checkbox("Show Bowl Arm", value=True, key="whl_phs_slog_bowl_arm")
                show_venue_phs_slog = st.checkbox("Show Venue", value=True, key="whl_phs_slog_venue")

            with col3:
                st.markdown("## Run Filter (Wagon Wheel)")

                if "run_init_whl_phs_slog" not in st.session_state:
                    st.session_state["run_all_whl_phs_slog"] = True
                    for i in range(7):
                        st.session_state[f'run_{i}_whl_phs_slog'] = True
                    st.session_state["run_init_whl_phs_slog"] = True

                def sync_all_to_individual_whl_phs_slog():
                    all_selected = st.session_state["run_all_whl_phs_slog"]
                    for i in range(7):
                        st.session_state[f'run_{i}_whl_phs_slog'] = all_selected

                def sync_individual_to_all_whl_phs_slog():
                    all_selected = all(st.session_state[f'run_{i}_whl_phs_slog'] for i in range(7))
                    st.session_state["run_all_whl_phs_slog"] = all_selected

                st.checkbox("All", key="run_all_whl_phs_slog", on_change=sync_all_to_individual_whl_phs_slog)

                for i in range(7):
                    st.checkbox(str(i), key=f'run_{i}_whl_phs_slog', on_change=sync_individual_to_all_whl_phs_slog)

                individual_selected_whl_phs_slog = [i for i in range(7) if st.session_state.get(f'run_{i}_whl_phs_slog', False)]

                if st.session_state["run_all_whl_phs_slog"]:
                    filtered_runs_whl_phs_slog = None
                elif individual_selected_whl_phs_slog:
                    filtered_runs_whl_phs_slog = individual_selected_whl_phs_slog
                else:
                    filtered_runs_whl_phs_slog = []
                    
            if filtered_runs_whl_phs_slog == []:
                st.warning("Please select at least one run value to display the plot.")
            else:
                fig_whl_phs_slog = spike_graph_plot_descriptive(
                    df=df,
                    player_name=selected_player_value,
                    pid=selected_pid,
                    inns=selected_inns,
                    mat_num=selected_mat_num,
                    team_bat=selected_team_value,
                    team_bowl=selected_team_bowl_value,
                    run_values=filtered_runs_whl_phs_slog,
                    bowler_name=bowler_name,
                    bowler_id=bowler_id,
                    competition=selected_competition_value,
                    transparent=False,
                    over_values=over_values,
                    phase=[3],  # HARDCODED: Slog (16-20)
                    ground=selected_ground,
                    mcode=selected_mcode,
                    date_from=date_from,
                    date_to=date_to,
                    title_components=title_components if show_title_phs_slog else [],
                    bat_hand=bat_hand,
                    bowl_type=bowl_type,
                    bowl_kind=bowl_kind,
                    bowl_arm=bowl_arm,
                    show_title=show_title_phs_slog,
                    show_summary=show_summary_phs_slog,
                    show_shots_breakdown=show_shots_breakdown_phs_slog,
                    shots_breakdown_options=shots_breakdown_options_phs_slog,
                    show_legend=show_legend_phs_slog,
                    runs_count=runs_count_phs_slog,
                    show_fours_sixes=show_fours_sixes_phs_slog,
                    show_control=show_control_phs_slog,
                    show_prod_shot=show_prod_shot_phs_slog,
                    show_bowler=show_bowler_phs_slog,
                    show_ground=show_ground_phs_slog,
                    show_venue=show_venue_phs_slog,
                    show_overs=show_overs_phs_slog,
                    show_phase=show_phase_phs_slog,
                    show_bowl_type=show_bowl_type_phs_slog,
                    show_bowl_kind=show_bowl_kind_phs_slog,
                    show_bowl_arm=show_bowl_arm_phs_slog
                )
                with col2:
                    st.pyplot(fig_whl_phs_slog)
            
            with col3:
                if fig_whl_phs_slog:
                    buf = BytesIO()
                    fig_whl_phs_slog.savefig(buf, format="png", transparent=False, dpi=300, bbox_inches='tight')
                    buf.seek(0)
                    st.download_button(
                        label="📅 Download Plot as PNG",
                        data=buf.getvalue(),
                        file_name=f"{selected_player}_whl_phase_slog.png",
                        mime="image/png",
                        key="whl_phs_slog_download"
                    )

        if "━━ Wagon Wheel - All Kinds" in plot_types:
            st.markdown("<h2 style='text-align: center;'>Wagon Wheel - All Bowler Kinds</h2>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([2, 2, 2])
            
            with col1:
                st.markdown("## Customize Plot Info")
                show_title_whl_all_type = st.checkbox("Show Plot Title", value=True, key="whl_all_type_title")
                show_legend_whl_all_type = st.checkbox("Show Legend", value=True, key="whl_all_type_legend")
                show_summary_whl_all_type = st.checkbox("Show Runs Summary", value=True, key="whl_all_type_summary")
                
                show_shots_breakdown_whl_all_type = st.checkbox("Show Shots Breakdown", value=True, key="whl_all_type_shots_breakdown")
                if show_shots_breakdown_whl_all_type:
                    shots_breakdown_options_whl_all_type = st.multiselect(
                        "Shots to Display",
                        options=['0s', '1s', '2s', '3s', '4s', '6s'],
                        default=['0s', '1s', '2s', '4s', '6s'],
                        key="whl_all_type_shots_options",
                        help="Select which run types to display in breakdown"
                    )
                else:
                    shots_breakdown_options_whl_all_type = []
                
                runs_count_whl_all_type = st.checkbox("Show Runs Count", value=True, key="whl_all_type_runs")
                show_fours_sixes_whl_all_type = st.checkbox("Show 4s and 6s", value=True, key="whl_all_type_fs")
                show_bowler_whl_all_type = st.checkbox("Show Bowler", value=True, key="whl_all_type_bowler")
                show_control_whl_all_type = st.checkbox("Show Control %", value=True, key="whl_all_type_control")
                show_prod_shot_whl_all_type = st.checkbox("Show Productive Shot", value=True, key="whl_all_type_prod")
                show_overs_whl_all_type = st.checkbox("Show Overs", value=True, key="whl_all_type_overs")
                show_phase_whl_all_type = st.checkbox("Show Phase", value=True, key="whl_all_type_phase")
                show_ground_whl_all_type = st.checkbox("Show Ground Image", value=True, key="whl_all_type_ground")
                show_bowl_type_whl_all_type = st.checkbox("Show Bowl Type", value=True, key="whl_all_type_bowl_type")
                show_bowl_kind_whl_all_type = st.checkbox("Show Bowl Pace", value=True, key="whl_all_type_bowl_kind")
                show_bowl_arm_whl_all_type = st.checkbox("Show Bowl Arm", value=True, key="whl_all_type_bowl_arm")
                show_venue_whl_all_type = st.checkbox("Show Venue", value=True, key="whl_all_type_venue")

            with col3:
                st.markdown("## Run Filter (Wagon Wheel)")

                if "run_init_whl_all_type" not in st.session_state:
                    st.session_state["run_all_whl_all_type"] = True
                    for i in range(7):
                        st.session_state[f'run_{i}_whl_all_type'] = True
                    st.session_state["run_init_whl_all_type"] = True

                def sync_all_to_individual_whl_all_type():
                    all_selected = st.session_state["run_all_whl_all_type"]
                    for i in range(7):
                        st.session_state[f'run_{i}_whl_all_type'] = all_selected

                def sync_individual_to_all_whl_all_type():
                    all_selected = all(st.session_state[f'run_{i}_whl_all_type'] for i in range(7))
                    st.session_state["run_all_whl_all_type"] = all_selected

                st.checkbox("All", key="run_all_whl_all_type", on_change=sync_all_to_individual_whl_all_type)

                for i in range(7):
                    st.checkbox(str(i), key=f'run_{i}_whl_all_type', on_change=sync_individual_to_all_whl_all_type)

                individual_selected_whl_all_type = [i for i in range(7) if st.session_state.get(f'run_{i}_whl_all_type', False)]

                if st.session_state["run_all_whl_all_type"]:
                    filtered_runs_whl_all_type = None
                elif individual_selected_whl_all_type:
                    filtered_runs_whl_all_type = individual_selected_whl_all_type
                else:
                    filtered_runs_whl_all_type = []
                    
            if filtered_runs_whl_all_type == []:
                st.warning("Please select at least one run value to display the plot.")
            else:
                fig_whl_all_type = spike_graph_plot_descriptive(
                    df=df,
                    player_name=selected_player_value,
                    pid=selected_pid,
                    inns=selected_inns,
                    mat_num=selected_mat_num,
                    team_bat=selected_team_value,
                    team_bowl=selected_team_bowl_value,
                    run_values=filtered_runs_whl_all_type,
                    bowler_name=bowler_name,
                    bowler_id=bowler_id,
                    competition=selected_competition_value,
                    transparent=False,
                    over_values=over_values,
                    phase=phase,
                    ground=selected_ground,
                    mcode=selected_mcode,
                    date_from=date_from,
                    date_to=date_to,
                    title_components=title_components if show_title_whl_all_type else [],
                    bat_hand=bat_hand,
                    bowl_type=None,
                    bowl_kind=bowl_kind,
                    bowl_arm=bowl_arm,
                    show_title=show_title_whl_all_type,
                    show_summary=show_summary_whl_all_type,
                    show_shots_breakdown=show_shots_breakdown_whl_all_type,
                    shots_breakdown_options=shots_breakdown_options_whl_all_type,
                    show_legend=show_legend_whl_all_type,
                    runs_count=runs_count_whl_all_type,
                    show_fours_sixes=show_fours_sixes_whl_all_type,
                    show_control=show_control_whl_all_type,
                    show_prod_shot=show_prod_shot_whl_all_type,
                    show_bowler=show_bowler_whl_all_type,
                    show_ground=show_ground_whl_all_type,
                    show_venue=show_venue_whl_all_type,
                    show_overs=show_overs_whl_all_type,
                    show_phase=show_phase_whl_all_type,
                    show_bowl_type=show_bowl_type_whl_all_type,
                    show_bowl_kind=show_bowl_kind_whl_all_type,
                    show_bowl_arm=show_bowl_arm_whl_all_type
                )
                with col2:
                    st.pyplot(fig_whl_all_type)
            
            with col3:
                if fig_whl_all_type:
                    buf = BytesIO()
                    fig_whl_all_type.savefig(buf, format="png", transparent=False, dpi=300, bbox_inches='tight')
                    buf.seek(0)
                    st.download_button(
                        label="📅 Download Plot as PNG",
                        data=buf.getvalue(),
                        file_name=f"{selected_player}_whl_all_type.png",
                        mime="image/png",
                        key="whl_all_type_download"
                    )

        if "━━ Wagon Wheel - RAP" in plot_types:
            st.markdown("<h2 style='text-align: center;'>Wagon Wheel - RAP</h2>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([2, 2, 2])
            
            with col1:
                st.markdown("## Customize Plot Info")
                show_title_whl_rap = st.checkbox("Show Plot Title", value=True, key="whl_rap_title")
                show_legend_whl_rap = st.checkbox("Show Legend", value=True, key="whl_rap_legend")
                show_summary_whl_rap = st.checkbox("Show Runs Summary", value=True, key="whl_rap_summary")
                
                show_shots_breakdown_whl_rap = st.checkbox("Show Shots Breakdown", value=True, key="whl_rap_shots_breakdown")
                if show_shots_breakdown_whl_rap:
                    shots_breakdown_options_whl_rap = st.multiselect(
                        "Shots to Display",
                        options=['0s', '1s', '2s', '3s', '4s', '6s'],
                        default=['0s', '1s', '2s', '4s', '6s'],
                        key="whl_rap_shots_options",
                        help="Select which run types to display in breakdown"
                    )
                else:
                    shots_breakdown_options_whl_rap = []
                
                runs_count_whl_rap = st.checkbox("Show Runs Count", value=True, key="whl_rap_runs")
                show_fours_sixes_whl_rap = st.checkbox("Show 4s and 6s", value=True, key="whl_rap_fs")
                show_bowler_whl_rap = st.checkbox("Show Bowler", value=True, key="whl_rap_bowler")
                show_control_whl_rap = st.checkbox("Show Control %", value=True, key="whl_rap_control")
                show_prod_shot_whl_rap = st.checkbox("Show Productive Shot", value=True, key="whl_rap_prod")
                show_overs_whl_rap = st.checkbox("Show Overs", value=True, key="whl_rap_overs")
                show_phase_whl_rap = st.checkbox("Show Phase", value=True, key="whl_rap_phase")
                show_ground_whl_rap = st.checkbox("Show Ground Image", value=True, key="whl_rap_ground")
                show_bowl_type_whl_rap = st.checkbox("Show Bowl Type", value=True, key="whl_rap_bowl_type")
                show_bowl_kind_whl_rap = st.checkbox("Show Bowl Pace", value=True, key="whl_rap_bowl_kind")
                show_bowl_arm_whl_rap = st.checkbox("Show Bowl Arm", value=True, key="whl_rap_bowl_arm")
                show_venue_whl_rap = st.checkbox("Show Venue", value=True, key="whl_rap_venue")

            with col3:
                st.markdown("## Run Filter (Wagon Wheel)")

                if "run_init_whl_rap" not in st.session_state:
                    st.session_state["run_all_whl_rap"] = True
                    for i in range(7):
                        st.session_state[f'run_{i}_whl_rap'] = True
                    st.session_state["run_init_whl_rap"] = True

                def sync_all_to_individual_whl_rap():
                    all_selected = st.session_state["run_all_whl_rap"]
                    for i in range(7):
                        st.session_state[f'run_{i}_whl_rap'] = all_selected

                def sync_individual_to_all_whl_rap():
                    all_selected = all(st.session_state[f'run_{i}_whl_rap'] for i in range(7))
                    st.session_state["run_all_whl_rap"] = all_selected

                st.checkbox("All", key="run_all_whl_rap", on_change=sync_all_to_individual_whl_rap)

                for i in range(7):
                    st.checkbox(str(i), key=f'run_{i}_whl_rap', on_change=sync_individual_to_all_whl_rap)

                individual_selected_whl_rap = [i for i in range(7) if st.session_state.get(f'run_{i}_whl_rap', False)]

                if st.session_state["run_all_whl_rap"]:
                    filtered_runs_whl_rap = None
                elif individual_selected_whl_rap:
                    filtered_runs_whl_rap = individual_selected_whl_rap
                else:
                    filtered_runs_whl_rap = []
                    
            if filtered_runs_whl_rap == []:
                st.warning("Please select at least one run value to display the plot.")
            else:
                fig_whl_rap = spike_graph_plot_descriptive(
                    df=df,
                    player_name=selected_player_value,
                    pid=selected_pid,
                    inns=selected_inns,
                    mat_num=selected_mat_num,
                    team_bat=selected_team_value,
                    team_bowl=selected_team_bowl_value,
                    run_values=filtered_runs_whl_rap,
                    bowler_name=bowler_name,
                    bowler_id=bowler_id,
                    competition=selected_competition_value,
                    transparent=False,
                    over_values=over_values,
                    phase=phase,
                    ground=selected_ground,
                    mcode=selected_mcode,
                    date_from=date_from,
                    date_to=date_to,
                    title_components=title_components if show_title_whl_rap else [],
                    bat_hand=bat_hand,
                    bowl_type=["Right Arm Pace"],
                    bowl_kind=bowl_kind,
                    bowl_arm=bowl_arm,
                    show_title=show_title_whl_rap,
                    show_summary=show_summary_whl_rap,
                    show_shots_breakdown=show_shots_breakdown_whl_rap,
                    shots_breakdown_options=shots_breakdown_options_whl_rap,
                    show_legend=show_legend_whl_rap,
                    runs_count=runs_count_whl_rap,
                    show_fours_sixes=show_fours_sixes_whl_rap,
                    show_control=show_control_whl_rap,
                    show_prod_shot=show_prod_shot_whl_rap,
                    show_bowler=show_bowler_whl_rap,
                    show_ground=show_ground_whl_rap,
                    show_venue=show_venue_whl_rap,
                    show_overs=show_overs_whl_rap,
                    show_phase=show_phase_whl_rap,
                    show_bowl_type=show_bowl_type_whl_rap,
                    show_bowl_kind=show_bowl_kind_whl_rap,
                    show_bowl_arm=show_bowl_arm_whl_rap
                )
                with col2:
                    st.pyplot(fig_whl_rap)
            
            with col3:
                if fig_whl_rap:
                    buf = BytesIO()
                    fig_whl_rap.savefig(buf, format="png", transparent=False, dpi=300, bbox_inches='tight')
                    buf.seek(0)
                    st.download_button(
                        label="📅 Download Plot as PNG",
                        data=buf.getvalue(),
                        file_name=f"{selected_player}_whl_rap.png",
                        mime="image/png",
                        key="whl_rap_download"
                    )

        if "━━ Wagon Wheel - RAFS" in plot_types:
            st.markdown("<h2 style='text-align: center;'>Wagon Wheel - RAFS</h2>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([2, 2, 2])
            
            with col1:
                st.markdown("## Customize Plot Info")
                show_title_whl_rafs = st.checkbox("Show Plot Title", value=True, key="whl_rafs_title")
                show_legend_whl_rafs = st.checkbox("Show Legend", value=True, key="whl_rafs_legend")
                show_summary_whl_rafs = st.checkbox("Show Runs Summary", value=True, key="whl_rafs_summary")
                
                show_shots_breakdown_whl_rafs = st.checkbox("Show Shots Breakdown", value=True, key="whl_rafs_shots_breakdown")
                if show_shots_breakdown_whl_rafs:
                    shots_breakdown_options_whl_rafs = st.multiselect(
                        "Shots to Display",
                        options=['0s', '1s', '2s', '3s', '4s', '6s'],
                        default=['0s', '1s', '2s', '4s', '6s'],
                        key="whl_rafs_shots_options",
                        help="Select which run types to display in breakdown"
                    )
                else:
                    shots_breakdown_options_whl_rafs = []
                
                runs_count_whl_rafs = st.checkbox("Show Runs Count", value=True, key="whl_rafs_runs")
                show_fours_sixes_whl_rafs = st.checkbox("Show 4s and 6s", value=True, key="whl_rafs_fs")
                show_bowler_whl_rafs = st.checkbox("Show Bowler", value=True, key="whl_rafs_bowler")
                show_control_whl_rafs = st.checkbox("Show Control %", value=True, key="whl_rafs_control")
                show_prod_shot_whl_rafs = st.checkbox("Show Productive Shot", value=True, key="whl_rafs_prod")
                show_overs_whl_rafs = st.checkbox("Show Overs", value=True, key="whl_rafs_overs")
                show_phase_whl_rafs = st.checkbox("Show Phase", value=True, key="whl_rafs_phase")
                show_ground_whl_rafs = st.checkbox("Show Ground Image", value=True, key="whl_rafs_ground")
                show_bowl_type_whl_rafs = st.checkbox("Show Bowl Type", value=True, key="whl_rafs_bowl_type")
                show_bowl_kind_whl_rafs = st.checkbox("Show Bowl Pace", value=True, key="whl_rafs_bowl_kind")
                show_bowl_arm_whl_rafs = st.checkbox("Show Bowl Arm", value=True, key="whl_rafs_bowl_arm")
                show_venue_whl_rafs = st.checkbox("Show Venue", value=True, key="whl_rafs_venue")

            with col3:
                st.markdown("## Run Filter (Wagon Wheel)")

                if "run_init_whl_rafs" not in st.session_state:
                    st.session_state["run_all_whl_rafs"] = True
                    for i in range(7):
                        st.session_state[f'run_{i}_whl_rafs'] = True
                    st.session_state["run_init_whl_rafs"] = True

                def sync_all_to_individual_whl_rafs():
                    all_selected = st.session_state["run_all_whl_rafs"]
                    for i in range(7):
                        st.session_state[f'run_{i}_whl_rafs'] = all_selected

                def sync_individual_to_all_whl_rafs():
                    all_selected = all(st.session_state[f'run_{i}_whl_rafs'] for i in range(7))
                    st.session_state["run_all_whl_rafs"] = all_selected

                st.checkbox("All", key="run_all_whl_rafs", on_change=sync_all_to_individual_whl_rafs)

                for i in range(7):
                    st.checkbox(str(i), key=f'run_{i}_whl_rafs', on_change=sync_individual_to_all_whl_rafs)

                individual_selected_whl_rafs = [i for i in range(7) if st.session_state.get(f'run_{i}_whl_rafs', False)]

                if st.session_state["run_all_whl_rafs"]:
                    filtered_runs_whl_rafs = None
                elif individual_selected_whl_rafs:
                    filtered_runs_whl_rafs = individual_selected_whl_rafs
                else:
                    filtered_runs_whl_rafs = []
                    
            if filtered_runs_whl_rafs == []:
                st.warning("Please select at least one run value to display the plot.")
            else:
                fig_whl_rafs = spike_graph_plot_descriptive(
                    df=df,
                    player_name=selected_player_value,
                    pid=selected_pid,
                    inns=selected_inns,
                    mat_num=selected_mat_num,
                    team_bat=selected_team_value,
                    team_bowl=selected_team_bowl_value,
                    run_values=filtered_runs_whl_rafs,
                    bowler_name=bowler_name,
                    bowler_id=bowler_id,
                    competition=selected_competition_value,
                    transparent=False,
                    over_values=over_values,
                    phase=phase,
                    ground=selected_ground,
                    mcode=selected_mcode,
                    date_from=date_from,
                    date_to=date_to,
                    title_components=title_components if show_title_whl_rafs else [],
                    bat_hand=bat_hand,
                    bowl_type=["Right Arm Finger Spin"],
                    bowl_kind=bowl_kind,
                    bowl_arm=bowl_arm,
                    show_title=show_title_whl_rafs,
                    show_summary=show_summary_whl_rafs,
                    show_shots_breakdown=show_shots_breakdown_whl_rafs,
                    shots_breakdown_options=shots_breakdown_options_whl_rafs,
                    show_legend=show_legend_whl_rafs,
                    runs_count=runs_count_whl_rafs,
                    show_fours_sixes=show_fours_sixes_whl_rafs,
                    show_control=show_control_whl_rafs,
                    show_prod_shot=show_prod_shot_whl_rafs,
                    show_bowler=show_bowler_whl_rafs,
                    show_ground=show_ground_whl_rafs,
                    show_venue=show_venue_whl_rafs,
                    show_overs=show_overs_whl_rafs,
                    show_phase=show_phase_whl_rafs,
                    show_bowl_type=show_bowl_type_whl_rafs,
                    show_bowl_kind=show_bowl_kind_whl_rafs,
                    show_bowl_arm=show_bowl_arm_whl_rafs
                )
                with col2:
                    st.pyplot(fig_whl_rafs)
            
            with col3:
                if fig_whl_rafs:
                    buf = BytesIO()
                    fig_whl_rafs.savefig(buf, format="png", transparent=False, dpi=300, bbox_inches='tight')
                    buf.seek(0)
                    st.download_button(
                        label="📅 Download Plot as PNG",
                        data=buf.getvalue(),
                        file_name=f"{selected_player}_whl_rafs.png",
                        mime="image/png",
                        key="whl_rafs_download"
                    )

        if "━━ Wagon Wheel - RAWS" in plot_types:
            st.markdown("<h2 style='text-align: center;'>Wagon Wheel - RAWS</h2>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([2, 2, 2])
            
            with col1:
                st.markdown("## Customize Plot Info")
                show_title_whl_raws = st.checkbox("Show Plot Title", value=True, key="whl_raws_title")
                show_legend_whl_raws = st.checkbox("Show Legend", value=True, key="whl_raws_legend")
                show_summary_whl_raws = st.checkbox("Show Runs Summary", value=True, key="whl_raws_summary")
                
                show_shots_breakdown_whl_raws = st.checkbox("Show Shots Breakdown", value=True, key="whl_raws_shots_breakdown")
                if show_shots_breakdown_whl_raws:
                    shots_breakdown_options_whl_raws = st.multiselect(
                        "Shots to Display",
                        options=['0s', '1s', '2s', '3s', '4s', '6s'],
                        default=['0s', '1s', '2s', '4s', '6s'],
                        key="whl_raws_shots_options",
                        help="Select which run types to display in breakdown"
                    )
                else:
                    shots_breakdown_options_whl_raws = []
                
                runs_count_whl_raws = st.checkbox("Show Runs Count", value=True, key="whl_raws_runs")
                show_fours_sixes_whl_raws = st.checkbox("Show 4s and 6s", value=True, key="whl_raws_fs")
                show_bowler_whl_raws = st.checkbox("Show Bowler", value=True, key="whl_raws_bowler")
                show_control_whl_raws = st.checkbox("Show Control %", value=True, key="whl_raws_control")
                show_prod_shot_whl_raws = st.checkbox("Show Productive Shot", value=True, key="whl_raws_prod")
                show_overs_whl_raws = st.checkbox("Show Overs", value=True, key="whl_raws_overs")
                show_phase_whl_raws = st.checkbox("Show Phase", value=True, key="whl_raws_phase")
                show_ground_whl_raws = st.checkbox("Show Ground Image", value=True, key="whl_raws_ground")
                show_bowl_type_whl_raws = st.checkbox("Show Bowl Type", value=True, key="whl_raws_bowl_type")
                show_bowl_kind_whl_raws = st.checkbox("Show Bowl Pace", value=True, key="whl_raws_bowl_kind")
                show_bowl_arm_whl_raws = st.checkbox("Show Bowl Arm", value=True, key="whl_raws_bowl_arm")
                show_venue_whl_raws = st.checkbox("Show Venue", value=True, key="whl_raws_venue")

            with col3:
                st.markdown("## Run Filter (Wagon Wheel)")

                if "run_init_whl_raws" not in st.session_state:
                    st.session_state["run_all_whl_raws"] = True
                    for i in range(7):
                        st.session_state[f'run_{i}_whl_raws'] = True
                    st.session_state["run_init_whl_raws"] = True

                def sync_all_to_individual_whl_raws():
                    all_selected = st.session_state["run_all_whl_raws"]
                    for i in range(7):
                        st.session_state[f'run_{i}_whl_raws'] = all_selected

                def sync_individual_to_all_whl_raws():
                    all_selected = all(st.session_state[f'run_{i}_whl_raws'] for i in range(7))
                    st.session_state["run_all_whl_raws"] = all_selected

                st.checkbox("All", key="run_all_whl_raws", on_change=sync_all_to_individual_whl_raws)

                for i in range(7):
                    st.checkbox(str(i), key=f'run_{i}_whl_raws', on_change=sync_individual_to_all_whl_raws)

                individual_selected_whl_raws = [i for i in range(7) if st.session_state.get(f'run_{i}_whl_raws', False)]

                if st.session_state["run_all_whl_raws"]:
                    filtered_runs_whl_raws = None
                elif individual_selected_whl_raws:
                    filtered_runs_whl_raws = individual_selected_whl_raws
                else:
                    filtered_runs_whl_raws = []
                    
            if filtered_runs_whl_raws == []:
                st.warning("Please select at least one run value to display the plot.")
            else:
                fig_whl_raws = spike_graph_plot_descriptive(
                    df=df,
                    player_name=selected_player_value,
                    pid=selected_pid,
                    inns=selected_inns,
                    mat_num=selected_mat_num,
                    team_bat=selected_team_value,
                    team_bowl=selected_team_bowl_value,
                    run_values=filtered_runs_whl_raws,
                    bowler_name=bowler_name,
                    bowler_id=bowler_id,
                    competition=selected_competition_value,
                    transparent=False,
                    over_values=over_values,
                    phase=phase,
                    ground=selected_ground,
                    mcode=selected_mcode,
                    date_from=date_from,
                    date_to=date_to,
                    title_components=title_components if show_title_whl_raws else [],
                    bat_hand=bat_hand,
                    bowl_type=["Right Arm Wrist Spin"],
                    bowl_kind=bowl_kind,
                    bowl_arm=bowl_arm,
                    show_title=show_title_whl_raws,
                    show_summary=show_summary_whl_raws,
                    show_shots_breakdown=show_shots_breakdown_whl_raws,
                    shots_breakdown_options=shots_breakdown_options_whl_raws,
                    show_legend=show_legend_whl_raws,
                    runs_count=runs_count_whl_raws,
                    show_fours_sixes=show_fours_sixes_whl_raws,
                    show_control=show_control_whl_raws,
                    show_prod_shot=show_prod_shot_whl_raws,
                    show_bowler=show_bowler_whl_raws,
                    show_ground=show_ground_whl_raws,
                    show_venue=show_venue_whl_raws,
                    show_overs=show_overs_whl_raws,
                    show_phase=show_phase_whl_raws,
                    show_bowl_type=show_bowl_type_whl_raws,
                    show_bowl_kind=show_bowl_kind_whl_raws,
                    show_bowl_arm=show_bowl_arm_whl_raws
                )
                with col2:
                    st.pyplot(fig_whl_raws)
            
            with col3:
                if fig_whl_raws:
                    buf = BytesIO()
                    fig_whl_raws.savefig(buf, format="png", transparent=False, dpi=300, bbox_inches='tight')
                    buf.seek(0)
                    st.download_button(
                        label="📅 Download Plot as PNG",
                        data=buf.getvalue(),
                        file_name=f"{selected_player}_whl_raws.png",
                        mime="image/png",
                        key="whl_raws_download"
                    )

        if "━━ Wagon Wheel - LAP" in plot_types:
            st.markdown("<h2 style='text-align: center;'>Wagon Wheel - LAP</h2>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([2, 2, 2])
            
            with col1:
                st.markdown("## Customize Plot Info")
                show_title_whl_lap = st.checkbox("Show Plot Title", value=True, key="whl_lap_title")
                show_legend_whl_lap = st.checkbox("Show Legend", value=True, key="whl_lap_legend")
                show_summary_whl_lap = st.checkbox("Show Runs Summary", value=True, key="whl_lap_summary")
                
                show_shots_breakdown_whl_lap = st.checkbox("Show Shots Breakdown", value=True, key="whl_lap_shots_breakdown")
                if show_shots_breakdown_whl_lap:
                    shots_breakdown_options_whl_lap = st.multiselect(
                        "Shots to Display",
                        options=['0s', '1s', '2s', '3s', '4s', '6s'],
                        default=['0s', '1s', '2s', '4s', '6s'],
                        key="whl_lap_shots_options",
                        help="Select which run types to display in breakdown"
                    )
                else:
                    shots_breakdown_options_whl_lap = []
                
                runs_count_whl_lap = st.checkbox("Show Runs Count", value=True, key="whl_lap_runs")
                show_fours_sixes_whl_lap = st.checkbox("Show 4s and 6s", value=True, key="whl_lap_fs")
                show_bowler_whl_lap = st.checkbox("Show Bowler", value=True, key="whl_lap_bowler")
                show_control_whl_lap = st.checkbox("Show Control %", value=True, key="whl_lap_control")
                show_prod_shot_whl_lap = st.checkbox("Show Productive Shot", value=True, key="whl_lap_prod")
                show_overs_whl_lap = st.checkbox("Show Overs", value=True, key="whl_lap_overs")
                show_phase_whl_lap = st.checkbox("Show Phase", value=True, key="whl_lap_phase")
                show_ground_whl_lap = st.checkbox("Show Ground Image", value=True, key="whl_lap_ground")
                show_bowl_type_whl_lap = st.checkbox("Show Bowl Type", value=True, key="whl_lap_bowl_type")
                show_bowl_kind_whl_lap = st.checkbox("Show Bowl Pace", value=True, key="whl_lap_bowl_kind")
                show_bowl_arm_whl_lap = st.checkbox("Show Bowl Arm", value=True, key="whl_lap_bowl_arm")
                show_venue_whl_lap = st.checkbox("Show Venue", value=True, key="whl_lap_venue")

            with col3:
                st.markdown("## Run Filter (Wagon Wheel)")

                if "run_init_whl_lap" not in st.session_state:
                    st.session_state["run_all_whl_lap"] = True
                    for i in range(7):
                        st.session_state[f'run_{i}_whl_lap'] = True
                    st.session_state["run_init_whl_lap"] = True

                def sync_all_to_individual_whl_lap():
                    all_selected = st.session_state["run_all_whl_lap"]
                    for i in range(7):
                        st.session_state[f'run_{i}_whl_lap'] = all_selected

                def sync_individual_to_all_whl_lap():
                    all_selected = all(st.session_state[f'run_{i}_whl_lap'] for i in range(7))
                    st.session_state["run_all_whl_lap"] = all_selected

                st.checkbox("All", key="run_all_whl_lap", on_change=sync_all_to_individual_whl_lap)

                for i in range(7):
                    st.checkbox(str(i), key=f'run_{i}_whl_lap', on_change=sync_individual_to_all_whl_lap)

                individual_selected_whl_lap = [i for i in range(7) if st.session_state.get(f'run_{i}_whl_lap', False)]

                if st.session_state["run_all_whl_lap"]:
                    filtered_runs_whl_lap = None
                elif individual_selected_whl_lap:
                    filtered_runs_whl_lap = individual_selected_whl_lap
                else:
                    filtered_runs_whl_lap = []
                    
            if filtered_runs_whl_lap == []:
                st.warning("Please select at least one run value to display the plot.")
            else:
                fig_whl_lap = spike_graph_plot_descriptive(
                    df=df,
                    player_name=selected_player_value,
                    pid=selected_pid,
                    inns=selected_inns,
                    mat_num=selected_mat_num,
                    team_bat=selected_team_value,
                    team_bowl=selected_team_bowl_value,
                    run_values=filtered_runs_whl_lap,
                    bowler_name=bowler_name,
                    bowler_id=bowler_id,
                    competition=selected_competition_value,
                    transparent=False,
                    over_values=over_values,
                    phase=phase,
                    ground=selected_ground,
                    mcode=selected_mcode,
                    date_from=date_from,
                    date_to=date_to,
                    title_components=title_components if show_title_whl_lap else [],
                    bat_hand=bat_hand,
                    bowl_type=["Left Arm Pace"],
                    bowl_kind=bowl_kind,
                    bowl_arm=bowl_arm,
                    show_title=show_title_whl_lap,
                    show_summary=show_summary_whl_lap,
                    show_shots_breakdown=show_shots_breakdown_whl_lap,
                    shots_breakdown_options=shots_breakdown_options_whl_lap,
                    show_legend=show_legend_whl_lap,
                    runs_count=runs_count_whl_lap,
                    show_fours_sixes=show_fours_sixes_whl_lap,
                    show_control=show_control_whl_lap,
                    show_prod_shot=show_prod_shot_whl_lap,
                    show_bowler=show_bowler_whl_lap,
                    show_ground=show_ground_whl_lap,
                    show_venue=show_venue_whl_lap,
                    show_overs=show_overs_whl_lap,
                    show_phase=show_phase_whl_lap,
                    show_bowl_type=show_bowl_type_whl_lap,
                    show_bowl_kind=show_bowl_kind_whl_lap,
                    show_bowl_arm=show_bowl_arm_whl_lap
                )
                with col2:
                    st.pyplot(fig_whl_lap)
            
            with col3:
                if fig_whl_lap:
                    buf = BytesIO()
                    fig_whl_lap.savefig(buf, format="png", transparent=False, dpi=300, bbox_inches='tight')
                    buf.seek(0)
                    st.download_button(
                        label="📅 Download Plot as PNG",
                        data=buf.getvalue(),
                        file_name=f"{selected_player}_whl_lap.png",
                        mime="image/png",
                        key="whl_lap_download"
                    )

        if "━━ Wagon Wheel - LAFS" in plot_types:
            st.markdown("<h2 style='text-align: center;'>Wagon Wheel - LAFS</h2>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([2, 2, 2])
            
            with col1:
                st.markdown("## Customize Plot Info")
                show_title_whl_lafs = st.checkbox("Show Plot Title", value=True, key="whl_lafs_title")
                show_legend_whl_lafs = st.checkbox("Show Legend", value=True, key="whl_lafs_legend")
                show_summary_whl_lafs = st.checkbox("Show Runs Summary", value=True, key="whl_lafs_summary")
                
                show_shots_breakdown_whl_lafs = st.checkbox("Show Shots Breakdown", value=True, key="whl_lafs_shots_breakdown")
                if show_shots_breakdown_whl_lafs:
                    shots_breakdown_options_whl_lafs = st.multiselect(
                        "Shots to Display",
                        options=['0s', '1s', '2s', '3s', '4s', '6s'],
                        default=['0s', '1s', '2s', '4s', '6s'],
                        key="whl_lafs_shots_options",
                        help="Select which run types to display in breakdown"
                    )
                else:
                    shots_breakdown_options_whl_lafs = []
                
                runs_count_whl_lafs = st.checkbox("Show Runs Count", value=True, key="whl_lafs_runs")
                show_fours_sixes_whl_lafs = st.checkbox("Show 4s and 6s", value=True, key="whl_lafs_fs")
                show_bowler_whl_lafs = st.checkbox("Show Bowler", value=True, key="whl_lafs_bowler")
                show_control_whl_lafs = st.checkbox("Show Control %", value=True, key="whl_lafs_control")
                show_prod_shot_whl_lafs = st.checkbox("Show Productive Shot", value=True, key="whl_lafs_prod")
                show_overs_whl_lafs = st.checkbox("Show Overs", value=True, key="whl_lafs_overs")
                show_phase_whl_lafs = st.checkbox("Show Phase", value=True, key="whl_lafs_phase")
                show_ground_whl_lafs = st.checkbox("Show Ground Image", value=True, key="whl_lafs_ground")
                show_bowl_type_whl_lafs = st.checkbox("Show Bowl Type", value=True, key="whl_lafs_bowl_type")
                show_bowl_kind_whl_lafs = st.checkbox("Show Bowl Pace", value=True, key="whl_lafs_bowl_kind")
                show_bowl_arm_whl_lafs = st.checkbox("Show Bowl Arm", value=True, key="whl_lafs_bowl_arm")
                show_venue_whl_lafs = st.checkbox("Show Venue", value=True, key="whl_lafs_venue")

            with col3:
                st.markdown("## Run Filter (Wagon Wheel)")

                if "run_init_whl_lafs" not in st.session_state:
                    st.session_state["run_all_whl_lafs"] = True
                    for i in range(7):
                        st.session_state[f'run_{i}_whl_lafs'] = True
                    st.session_state["run_init_whl_lafs"] = True

                def sync_all_to_individual_whl_lafs():
                    all_selected = st.session_state["run_all_whl_lafs"]
                    for i in range(7):
                        st.session_state[f'run_{i}_whl_lafs'] = all_selected

                def sync_individual_to_all_whl_lafs():
                    all_selected = all(st.session_state[f'run_{i}_whl_lafs'] for i in range(7))
                    st.session_state["run_all_whl_lafs"] = all_selected

                st.checkbox("All", key="run_all_whl_lafs", on_change=sync_all_to_individual_whl_lafs)

                for i in range(7):
                    st.checkbox(str(i), key=f'run_{i}_whl_lafs', on_change=sync_individual_to_all_whl_lafs)

                individual_selected_whl_lafs = [i for i in range(7) if st.session_state.get(f'run_{i}_whl_lafs', False)]

                if st.session_state["run_all_whl_lafs"]:
                    filtered_runs_whl_lafs = None
                elif individual_selected_whl_lafs:
                    filtered_runs_whl_lafs = individual_selected_whl_lafs
                else:
                    filtered_runs_whl_lafs = []
                    
            if filtered_runs_whl_lafs == []:
                st.warning("Please select at least one run value to display the plot.")
            else:
                fig_whl_lafs = spike_graph_plot_descriptive(
                    df=df,
                    player_name=selected_player_value,
                    pid=selected_pid,
                    inns=selected_inns,
                    mat_num=selected_mat_num,
                    team_bat=selected_team_value,
                    team_bowl=selected_team_bowl_value,
                    run_values=filtered_runs_whl_lafs,
                    bowler_name=bowler_name,
                    bowler_id=bowler_id,
                    competition=selected_competition_value,
                    transparent=False,
                    over_values=over_values,
                    phase=phase,
                    ground=selected_ground,
                    mcode=selected_mcode,
                    date_from=date_from,
                    date_to=date_to,
                    title_components=title_components if show_title_whl_lafs else [],
                    bat_hand=bat_hand,
                    bowl_type=["Left Arm Figner Spin"],
                    bowl_kind=bowl_kind,
                    bowl_arm=bowl_arm,
                    show_title=show_title_whl_lafs,
                    show_summary=show_summary_whl_lafs,
                    show_shots_breakdown=show_shots_breakdown_whl_lafs,
                    shots_breakdown_options=shots_breakdown_options_whl_lafs,
                    show_legend=show_legend_whl_lafs,
                    runs_count=runs_count_whl_lafs,
                    show_fours_sixes=show_fours_sixes_whl_lafs,
                    show_control=show_control_whl_lafs,
                    show_prod_shot=show_prod_shot_whl_lafs,
                    show_bowler=show_bowler_whl_lafs,
                    show_ground=show_ground_whl_lafs,
                    show_venue=show_venue_whl_lafs,
                    show_overs=show_overs_whl_lafs,
                    show_phase=show_phase_whl_lafs,
                    show_bowl_type=show_bowl_type_whl_lafs,
                    show_bowl_kind=show_bowl_kind_whl_lafs,
                    show_bowl_arm=show_bowl_arm_whl_lafs
                )
                with col2:
                    st.pyplot(fig_whl_lafs)
            
            with col3:
                if fig_whl_lafs:
                    buf = BytesIO()
                    fig_whl_lafs.savefig(buf, format="png", transparent=False, dpi=300, bbox_inches='tight')
                    buf.seek(0)
                    st.download_button(
                        label="📅 Download Plot as PNG",
                        data=buf.getvalue(),
                        file_name=f"{selected_player}_whl_lafs.png",
                        mime="image/png",
                        key="whl_lafs_download"
                    )

        if "━━ Wagon Wheel - LAWS" in plot_types:
            st.markdown("<h2 style='text-align: center;'>Wagon Wheel - LAWS</h2>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([2, 2, 2])
            
            with col1:
                st.markdown("## Customize Plot Info")
                show_title_whl_laws = st.checkbox("Show Plot Title", value=True, key="whl_laws_title")
                show_legend_whl_laws = st.checkbox("Show Legend", value=True, key="whl_laws_legend")
                show_summary_whl_laws = st.checkbox("Show Runs Summary", value=True, key="whl_laws_summary")
                
                show_shots_breakdown_whl_laws = st.checkbox("Show Shots Breakdown", value=True, key="whl_laws_shots_breakdown")
                if show_shots_breakdown_whl_laws:
                    shots_breakdown_options_whl_laws = st.multiselect(
                        "Shots to Display",
                        options=['0s', '1s', '2s', '3s', '4s', '6s'],
                        default=['0s', '1s', '2s', '4s', '6s'],
                        key="whl_laws_shots_options",
                        help="Select which run types to display in breakdown"
                    )
                else:
                    shots_breakdown_options_whl_laws = []
                
                runs_count_whl_laws = st.checkbox("Show Runs Count", value=True, key="whl_laws_runs")
                show_fours_sixes_whl_laws = st.checkbox("Show 4s and 6s", value=True, key="whl_laws_fs")
                show_bowler_whl_laws = st.checkbox("Show Bowler", value=True, key="whl_laws_bowler")
                show_control_whl_laws = st.checkbox("Show Control %", value=True, key="whl_laws_control")
                show_prod_shot_whl_laws = st.checkbox("Show Productive Shot", value=True, key="whl_laws_prod")
                show_overs_whl_laws = st.checkbox("Show Overs", value=True, key="whl_laws_overs")
                show_phase_whl_laws = st.checkbox("Show Phase", value=True, key="whl_laws_phase")
                show_ground_whl_laws = st.checkbox("Show Ground Image", value=True, key="whl_laws_ground")
                show_bowl_type_whl_laws = st.checkbox("Show Bowl Type", value=True, key="whl_laws_bowl_type")
                show_bowl_kind_whl_laws = st.checkbox("Show Bowl Pace", value=True, key="whl_laws_bowl_kind")
                show_bowl_arm_whl_laws = st.checkbox("Show Bowl Arm", value=True, key="whl_laws_bowl_arm")
                show_venue_whl_laws = st.checkbox("Show Venue", value=True, key="whl_laws_venue")

            with col3:
                st.markdown("## Run Filter (Wagon Wheel)")

                if "run_init_whl_laws" not in st.session_state:
                    st.session_state["run_all_whl_laws"] = True
                    for i in range(7):
                        st.session_state[f'run_{i}_whl_laws'] = True
                    st.session_state["run_init_whl_laws"] = True

                def sync_all_to_individual_whl_laws():
                    all_selected = st.session_state["run_all_whl_laws"]
                    for i in range(7):
                        st.session_state[f'run_{i}_whl_laws'] = all_selected

                def sync_individual_to_all_whl_laws():
                    all_selected = all(st.session_state[f'run_{i}_whl_laws'] for i in range(7))
                    st.session_state["run_all_whl_laws"] = all_selected

                st.checkbox("All", key="run_all_whl_laws", on_change=sync_all_to_individual_whl_laws)

                for i in range(7):
                    st.checkbox(str(i), key=f'run_{i}_whl_laws', on_change=sync_individual_to_all_whl_laws)

                individual_selected_whl_laws = [i for i in range(7) if st.session_state.get(f'run_{i}_whl_laws', False)]

                if st.session_state["run_all_whl_laws"]:
                    filtered_runs_whl_laws = None
                elif individual_selected_whl_laws:
                    filtered_runs_whl_laws = individual_selected_whl_laws
                else:
                    filtered_runs_whl_laws = []
                    
            if filtered_runs_whl_laws == []:
                st.warning("Please select at least one run value to display the plot.")
            else:
                fig_whl_laws = spike_graph_plot_descriptive(
                    df=df,
                    player_name=selected_player_value,
                    pid=selected_pid,
                    inns=selected_inns,
                    mat_num=selected_mat_num,
                    team_bat=selected_team_value,
                    team_bowl=selected_team_bowl_value,
                    run_values=filtered_runs_whl_laws,
                    bowler_name=bowler_name,
                    bowler_id=bowler_id,
                    competition=selected_competition_value,
                    transparent=False,
                    over_values=over_values,
                    phase=phase,
                    ground=selected_ground,
                    mcode=selected_mcode,
                    date_from=date_from,
                    date_to=date_to,
                    title_components=title_components if show_title_whl_laws else [],
                    bat_hand=bat_hand,
                    bowl_type=["Left Arm Wrist Spin"],
                    bowl_kind=bowl_kind,
                    bowl_arm=bowl_arm,
                    show_title=show_title_whl_laws,
                    show_summary=show_summary_whl_laws,
                    show_shots_breakdown=show_shots_breakdown_whl_laws,
                    shots_breakdown_options=shots_breakdown_options_whl_laws,
                    show_legend=show_legend_whl_laws,
                    runs_count=runs_count_whl_laws,
                    show_fours_sixes=show_fours_sixes_whl_laws,
                    show_control=show_control_whl_laws,
                    show_prod_shot=show_prod_shot_whl_laws,
                    show_bowler=show_bowler_whl_laws,
                    show_ground=show_ground_whl_laws,
                    show_venue=show_venue_whl_laws,
                    show_overs=show_overs_whl_laws,
                    show_phase=show_phase_whl_laws,
                    show_bowl_type=show_bowl_type_whl_laws,
                    show_bowl_kind=show_bowl_kind_whl_laws,
                    show_bowl_arm=show_bowl_arm_whl_laws
                )
                with col2:
                    st.pyplot(fig_whl_laws)
            
            with col3:
                if fig_whl_laws:
                    buf = BytesIO()
                    fig_whl_laws.savefig(buf, format="png", transparent=False, dpi=300, bbox_inches='tight')
                    buf.seek(0)
                    st.download_button(
                        label="📅 Download Plot as PNG",
                        data=buf.getvalue(),
                        file_name=f"{selected_player}_whl_laws.png",
                        mime="image/png",
                        key="whl_laws_download"
                    )

        if "━━ Wagon Wheel - All Arm" in plot_types:
            st.markdown("<h2 style='text-align: center;'>Wagon Wheel - All Arm</h2>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([2, 2, 2])
            
            with col1:
                st.markdown("## Customize Plot Info")
                show_title_whl_all_arm = st.checkbox("Show Plot Title", value=True, key="whl_all_arm_title")
                show_legend_whl_all_arm = st.checkbox("Show Legend", value=True, key="whl_all_arm_legend")
                show_summary_whl_all_arm = st.checkbox("Show Runs Summary", value=True, key="whl_all_arm_summary")
                
                show_shots_breakdown_whl_all_arm = st.checkbox("Show Shots Breakdown", value=True, key="whl_all_arm_shots_breakdown")
                if show_shots_breakdown_whl_all_arm:
                    shots_breakdown_options_whl_all_arm = st.multiselect(
                        "Shots to Display",
                        options=['0s', '1s', '2s', '3s', '4s', '6s'],
                        default=['0s', '1s', '2s', '4s', '6s'],
                        key="whl_all_arm_shots_options",
                        help="Select which run types to display in breakdown"
                    )
                else:
                    shots_breakdown_options_whl_all_arm = []
                
                runs_count_whl_all_arm = st.checkbox("Show Runs Count", value=True, key="whl_all_arm_runs")
                show_fours_sixes_whl_all_arm = st.checkbox("Show 4s and 6s", value=True, key="whl_all_arm_fs")
                show_bowler_whl_all_arm = st.checkbox("Show Bowler", value=True, key="whl_all_arm_bowler")
                show_control_whl_all_arm = st.checkbox("Show Control %", value=True, key="whl_all_arm_control")
                show_prod_shot_whl_all_arm = st.checkbox("Show Productive Shot", value=True, key="whl_all_arm_prod")
                show_overs_whl_all_arm = st.checkbox("Show Overs", value=True, key="whl_all_arm_overs")
                show_phase_whl_all_arm = st.checkbox("Show Phase", value=True, key="whl_all_arm_phase")
                show_ground_whl_all_arm = st.checkbox("Show Ground Image", value=True, key="whl_all_arm_ground")
                show_bowl_type_whl_all_arm = st.checkbox("Show Bowl Type", value=True, key="whl_all_arm_bowl_type")
                show_bowl_kind_whl_all_arm = st.checkbox("Show Bowl Pace", value=True, key="whl_all_arm_bowl_kind")
                show_bowl_arm_whl_all_arm = st.checkbox("Show Bowl Arm", value=True, key="whl_all_arm_bowl_arm")
                show_venue_whl_all_arm = st.checkbox("Show Venue", value=True, key="whl_all_arm_venue")

            with col3:
                st.markdown("## Run Filter (Wagon Wheel)")

                if "run_init_whl_all_arm" not in st.session_state:
                    st.session_state["run_all_whl_all_arm"] = True
                    for i in range(7):
                        st.session_state[f'run_{i}_whl_all_arm'] = True
                    st.session_state["run_init_whl_all_arm"] = True

                def sync_all_to_individual_whl_all_arm():
                    all_selected = st.session_state["run_all_whl_all_arm"]
                    for i in range(7):
                        st.session_state[f'run_{i}_whl_all_arm'] = all_selected

                def sync_individual_to_all_whl_all_arm():
                    all_selected = all(st.session_state[f'run_{i}_whl_all_arm'] for i in range(7))
                    st.session_state["run_all_whl_all_arm"] = all_selected

                st.checkbox("All", key="run_all_whl_all_arm", on_change=sync_all_to_individual_whl_all_arm)

                for i in range(7):
                    st.checkbox(str(i), key=f'run_{i}_whl_all_arm', on_change=sync_individual_to_all_whl_all_arm)

                individual_selected_whl_all_arm = [i for i in range(7) if st.session_state.get(f'run_{i}_whl_all_arm', False)]

                if st.session_state["run_all_whl_all_arm"]:
                    filtered_runs_whl_all_arm = None
                elif individual_selected_whl_all_arm:
                    filtered_runs_whl_all_arm = individual_selected_whl_all_arm
                else:
                    filtered_runs_whl_all_arm = []
                    
            if filtered_runs_whl_all_arm == []:
                st.warning("Please select at least one run value to display the plot.")
            else:
                fig_whl_all_arm = spike_graph_plot_descriptive(
                    df=df,
                    player_name=selected_player_value,
                    pid=selected_pid,
                    inns=selected_inns,
                    mat_num=selected_mat_num,
                    team_bat=selected_team_value,
                    team_bowl=selected_team_bowl_value,
                    run_values=filtered_runs_whl_all_arm,
                    bowler_name=bowler_name,
                    bowler_id=bowler_id,
                    competition=selected_competition_value,
                    transparent=False,
                    over_values=over_values,
                    phase=phase,
                    ground=selected_ground,
                    mcode=selected_mcode,
                    date_from=date_from,
                    date_to=date_to,
                    title_components=title_components if show_title_whl_all_arm else [],
                    bat_hand=bat_hand,
                    bowl_type=bowl_type,
                    bowl_kind=bowl_kind,
                    bowl_arm=None,
                    show_title=show_title_whl_all_arm,
                    show_summary=show_summary_whl_all_arm,
                    show_shots_breakdown=show_shots_breakdown_whl_all_arm,
                    shots_breakdown_options=shots_breakdown_options_whl_all_arm,
                    show_legend=show_legend_whl_all_arm,
                    runs_count=runs_count_whl_all_arm,
                    show_fours_sixes=show_fours_sixes_whl_all_arm,
                    show_control=show_control_whl_all_arm,
                    show_prod_shot=show_prod_shot_whl_all_arm,
                    show_bowler=show_bowler_whl_all_arm,
                    show_ground=show_ground_whl_all_arm,
                    show_venue=show_venue_whl_all_arm,
                    show_overs=show_overs_whl_all_arm,
                    show_phase=show_phase_whl_all_arm,
                    show_bowl_type=show_bowl_type_whl_all_arm,
                    show_bowl_kind=show_bowl_kind_whl_all_arm,
                    show_bowl_arm=show_bowl_arm_whl_all_arm
                )
                with col2:
                    st.pyplot(fig_whl_all_arm)
            
            with col3:
                if fig_whl_all_arm:
                    buf = BytesIO()
                    fig_whl_all_arm.savefig(buf, format="png", transparent=False, dpi=300, bbox_inches='tight')
                    buf.seek(0)
                    st.download_button(
                        label="📅 Download Plot as PNG",
                        data=buf.getvalue(),
                        file_name=f"{selected_player}_whl_all_arm.png",
                        mime="image/png",
                        key="whl_all_arm_download"
                    )

        if "━━ Wagon Wheel - Right Arm" in plot_types:
            st.markdown("<h2 style='text-align: center;'>Wagon Wheel - Right Arm</h2>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([2, 2, 2])
            
            with col1:
                st.markdown("## Customize Plot Info")
                show_title_whl_right_arm = st.checkbox("Show Plot Title", value=True, key="whl_right_arm_title")
                show_legend_whl_right_arm = st.checkbox("Show Legend", value=True, key="whl_right_arm_legend")
                show_summary_whl_right_arm = st.checkbox("Show Runs Summary", value=True, key="whl_right_arm_summary")
                
                show_shots_breakdown_whl_right_arm = st.checkbox("Show Shots Breakdown", value=True, key="whl_right_arm_shots_breakdown")
                if show_shots_breakdown_whl_right_arm:
                    shots_breakdown_options_whl_right_arm = st.multiselect(
                        "Shots to Display",
                        options=['0s', '1s', '2s', '3s', '4s', '6s'],
                        default=['0s', '1s', '2s', '4s', '6s'],
                        key="whl_right_arm_shots_options",
                        help="Select which run types to display in breakdown"
                    )
                else:
                    shots_breakdown_options_whl_right_arm = []
                
                runs_count_whl_right_arm = st.checkbox("Show Runs Count", value=True, key="whl_right_arm_runs")
                show_fours_sixes_whl_right_arm = st.checkbox("Show 4s and 6s", value=True, key="whl_right_arm_fs")
                show_bowler_whl_right_arm = st.checkbox("Show Bowler", value=True, key="whl_right_arm_bowler")
                show_control_whl_right_arm = st.checkbox("Show Control %", value=True, key="whl_right_arm_control")
                show_prod_shot_whl_right_arm = st.checkbox("Show Productive Shot", value=True, key="whl_right_arm_prod")
                show_overs_whl_right_arm = st.checkbox("Show Overs", value=True, key="whl_right_arm_overs")
                show_phase_whl_right_arm = st.checkbox("Show Phase", value=True, key="whl_right_arm_phase")
                show_ground_whl_right_arm = st.checkbox("Show Ground Image", value=True, key="whl_right_arm_ground")
                show_bowl_type_whl_right_arm = st.checkbox("Show Bowl Type", value=True, key="whl_right_arm_bowl_type")
                show_bowl_kind_whl_right_arm = st.checkbox("Show Bowl Pace", value=True, key="whl_right_arm_bowl_kind")
                show_bowl_arm_whl_right_arm = st.checkbox("Show Bowl Arm", value=True, key="whl_right_arm_bowl_arm")
                show_venue_whl_right_arm = st.checkbox("Show Venue", value=True, key="whl_right_arm_venue")

            with col3:
                st.markdown("## Run Filter (Wagon Wheel)")

                if "run_init_whl_right_arm" not in st.session_state:
                    st.session_state["run_all_whl_right_arm"] = True
                    for i in range(7):
                        st.session_state[f'run_{i}_whl_right_arm'] = True
                    st.session_state["run_init_whl_right_arm"] = True

                def sync_all_to_individual_whl_right_arm():
                    all_selected = st.session_state["run_all_whl_right_arm"]
                    for i in range(7):
                        st.session_state[f'run_{i}_whl_right_arm'] = all_selected

                def sync_individual_to_all_whl_right_arm():
                    all_selected = all(st.session_state[f'run_{i}_whl_right_arm'] for i in range(7))
                    st.session_state["run_all_whl_right_arm"] = all_selected

                st.checkbox("All", key="run_all_whl_right_arm", on_change=sync_all_to_individual_whl_right_arm)

                for i in range(7):
                    st.checkbox(str(i), key=f'run_{i}_whl_right_arm', on_change=sync_individual_to_all_whl_right_arm)

                individual_selected_whl_right_arm = [i for i in range(7) if st.session_state.get(f'run_{i}_whl_right_arm', False)]

                if st.session_state["run_all_whl_right_arm"]:
                    filtered_runs_whl_right_arm = None
                elif individual_selected_whl_right_arm:
                    filtered_runs_whl_right_arm = individual_selected_whl_right_arm
                else:
                    filtered_runs_whl_right_arm = []
                    
            if filtered_runs_whl_right_arm == []:
                st.warning("Please select at least one run value to display the plot.")
            else:
                fig_whl_right_arm = spike_graph_plot_descriptive(
                    df=df,
                    player_name=selected_player_value,
                    pid=selected_pid,
                    inns=selected_inns,
                    mat_num=selected_mat_num,
                    team_bat=selected_team_value,
                    team_bowl=selected_team_bowl_value,
                    run_values=filtered_runs_whl_right_arm,
                    bowler_name=bowler_name,
                    bowler_id=bowler_id,
                    competition=selected_competition_value,
                    transparent=False,
                    over_values=over_values,
                    phase=phase,
                    ground=selected_ground,
                    mcode=selected_mcode,
                    date_from=date_from,
                    date_to=date_to,
                    title_components=title_components if show_title_whl_right_arm else [],
                    bat_hand=bat_hand,
                    bowl_type=bowl_type,
                    bowl_kind=bowl_kind,
                    bowl_arm=["Right Arm"],
                    show_title=show_title_whl_right_arm,
                    show_summary=show_summary_whl_right_arm,
                    show_shots_breakdown=show_shots_breakdown_whl_right_arm,
                    shots_breakdown_options=shots_breakdown_options_whl_right_arm,
                    show_legend=show_legend_whl_right_arm,
                    runs_count=runs_count_whl_right_arm,
                    show_fours_sixes=show_fours_sixes_whl_right_arm,
                    show_control=show_control_whl_right_arm,
                    show_prod_shot=show_prod_shot_whl_right_arm,
                    show_bowler=show_bowler_whl_right_arm,
                    show_ground=show_ground_whl_right_arm,
                    show_venue=show_venue_whl_right_arm,
                    show_overs=show_overs_whl_right_arm,
                    show_phase=show_phase_whl_right_arm,
                    show_bowl_type=show_bowl_type_whl_right_arm,
                    show_bowl_kind=show_bowl_kind_whl_right_arm,
                    show_bowl_arm=show_bowl_arm_whl_right_arm
                )
                with col2:
                    st.pyplot(fig_whl_right_arm)
            
            with col3:
                if fig_whl_right_arm:
                    buf = BytesIO()
                    fig_whl_right_arm.savefig(buf, format="png", transparent=False, dpi=300, bbox_inches='tight')
                    buf.seek(0)
                    st.download_button(
                        label="📅 Download Plot as PNG",
                        data=buf.getvalue(),
                        file_name=f"{selected_player}_whl_right_arm.png",
                        mime="image/png",
                        key="whl_right_arm_download"
                    )

        if "━━ Wagon Wheel - Left Arm" in plot_types:
            st.markdown("<h2 style='text-align: center;'>Wagon Wheel - Left Arm</h2>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([2, 2, 2])
            
            with col1:
                st.markdown("## Customize Plot Info")
                show_title_whl_left_arm = st.checkbox("Show Plot Title", value=True, key="whl_left_arm_title")
                show_legend_whl_left_arm = st.checkbox("Show Legend", value=True, key="whl_left_arm_legend")
                show_summary_whl_left_arm = st.checkbox("Show Runs Summary", value=True, key="whl_left_arm_summary")
                
                show_shots_breakdown_whl_left_arm = st.checkbox("Show Shots Breakdown", value=True, key="whl_left_arm_shots_breakdown")
                if show_shots_breakdown_whl_left_arm:
                    shots_breakdown_options_whl_left_arm = st.multiselect(
                        "Shots to Display",
                        options=['0s', '1s', '2s', '3s', '4s', '6s'],
                        default=['0s', '1s', '2s', '4s', '6s'],
                        key="whl_left_arm_shots_options",
                        help="Select which run types to display in breakdown"
                    )
                else:
                    shots_breakdown_options_whl_left_arm = []
                
                runs_count_whl_left_arm = st.checkbox("Show Runs Count", value=True, key="whl_left_arm_runs")
                show_fours_sixes_whl_left_arm = st.checkbox("Show 4s and 6s", value=True, key="whl_left_arm_fs")
                show_bowler_whl_left_arm = st.checkbox("Show Bowler", value=True, key="whl_left_arm_bowler")
                show_control_whl_left_arm = st.checkbox("Show Control %", value=True, key="whl_left_arm_control")
                show_prod_shot_whl_left_arm = st.checkbox("Show Productive Shot", value=True, key="whl_left_arm_prod")
                show_overs_whl_left_arm = st.checkbox("Show Overs", value=True, key="whl_left_arm_overs")
                show_phase_whl_left_arm = st.checkbox("Show Phase", value=True, key="whl_left_arm_phase")
                show_ground_whl_left_arm = st.checkbox("Show Ground Image", value=True, key="whl_left_arm_ground")
                show_bowl_type_whl_left_arm = st.checkbox("Show Bowl Type", value=True, key="whl_left_arm_bowl_type")
                show_bowl_kind_whl_left_arm = st.checkbox("Show Bowl Pace", value=True, key="whl_left_arm_bowl_kind")
                show_bowl_arm_whl_left_arm = st.checkbox("Show Bowl Arm", value=True, key="whl_left_arm_bowl_arm")
                show_venue_whl_left_arm = st.checkbox("Show Venue", value=True, key="whl_left_arm_venue")

            with col3:
                st.markdown("## Run Filter (Wagon Wheel)")

                if "run_init_whl_left_arm" not in st.session_state:
                    st.session_state["run_all_whl_left_arm"] = True
                    for i in range(7):
                        st.session_state[f'run_{i}_whl_left_arm'] = True
                    st.session_state["run_init_whl_left_arm"] = True

                def sync_all_to_individual_whl_left_arm():
                    all_selected = st.session_state["run_all_whl_left_arm"]
                    for i in range(7):
                        st.session_state[f'run_{i}_whl_left_arm'] = all_selected

                def sync_individual_to_all_whl_left_arm():
                    all_selected = all(st.session_state[f'run_{i}_whl_left_arm'] for i in range(7))
                    st.session_state["run_all_whl_left_arm"] = all_selected

                st.checkbox("All", key="run_all_whl_left_arm", on_change=sync_all_to_individual_whl_left_arm)

                for i in range(7):
                    st.checkbox(str(i), key=f'run_{i}_whl_left_arm', on_change=sync_individual_to_all_whl_left_arm)

                individual_selected_whl_left_arm = [i for i in range(7) if st.session_state.get(f'run_{i}_whl_left_arm', False)]

                if st.session_state["run_all_whl_left_arm"]:
                    filtered_runs_whl_left_arm = None
                elif individual_selected_whl_left_arm:
                    filtered_runs_whl_left_arm = individual_selected_whl_left_arm
                else:
                    filtered_runs_whl_left_arm = []
                    
            if filtered_runs_whl_left_arm == []:
                st.warning("Please select at least one run value to display the plot.")
            else:
                fig_whl_left_arm = spike_graph_plot_descriptive(
                    df=df,
                    player_name=selected_player_value,
                    pid=selected_pid,
                    inns=selected_inns,
                    mat_num=selected_mat_num,
                    team_bat=selected_team_value,
                    team_bowl=selected_team_bowl_value,
                    run_values=filtered_runs_whl_left_arm,
                    bowler_name=bowler_name,
                    bowler_id=bowler_id,
                    competition=selected_competition_value,
                    transparent=False,
                    over_values=over_values,
                    phase=phase,
                    ground=selected_ground,
                    mcode=selected_mcode,
                    date_from=date_from,
                    date_to=date_to,
                    title_components=title_components if show_title_whl_left_arm else [],
                    bat_hand=bat_hand,
                    bowl_type=bowl_type,
                    bowl_kind=bowl_kind,
                    bowl_arm=["Left Arm"],
                    show_title=show_title_whl_left_arm,
                    show_summary=show_summary_whl_left_arm,
                    show_shots_breakdown=show_shots_breakdown_whl_left_arm,
                    shots_breakdown_options=shots_breakdown_options_whl_left_arm,
                    show_legend=show_legend_whl_left_arm,
                    runs_count=runs_count_whl_left_arm,
                    show_fours_sixes=show_fours_sixes_whl_left_arm,
                    show_control=show_control_whl_left_arm,
                    show_prod_shot=show_prod_shot_whl_left_arm,
                    show_bowler=show_bowler_whl_left_arm,
                    show_ground=show_ground_whl_left_arm,
                    show_venue=show_venue_whl_left_arm,
                    show_overs=show_overs_whl_left_arm,
                    show_phase=show_phase_whl_left_arm,
                    show_bowl_type=show_bowl_type_whl_left_arm,
                    show_bowl_kind=show_bowl_kind_whl_left_arm,
                    show_bowl_arm=show_bowl_arm_whl_left_arm
                )
                with col2:
                    st.pyplot(fig_whl_left_arm)
            
            with col3:
                if fig_whl_left_arm:
                    buf = BytesIO()
                    fig_whl_left_arm.savefig(buf, format="png", transparent=False, dpi=300, bbox_inches='tight')
                    buf.seek(0)
                    st.download_button(
                        label="📅 Download Plot as PNG",
                        data=buf.getvalue(),
                        file_name=f"{selected_player}_whl_left_arm.png",
                        mime="image/png",
                        key="whl_left_arm_download"
                    )

        if "Wagon Zone Plot (White Background)" in plot_types:
            st.markdown("<h2 style='text-align: center;'>Wagon Zone Plot (White Background)</h2>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([2, 2, 2])
            
            with col1:
                st.markdown("## Customize Plot Info")    
                show_title_wagon = st.checkbox("Show Plot Title (Wagon)", value=True, key="wagon_title")
                show_summary_wagon = st.checkbox("Show Runs Summary (Wagon)", value=True, key="wagon_summary")
                
                show_shots_breakdown_wagon = st.checkbox("Show Shots Breakdown", value=True, key="wagon_shots_breakdown")
                if show_shots_breakdown_wagon:
                    shots_breakdown_options_wagon = st.multiselect(
                        "Shots to Display",
                        options=['0s', '1s', '2s', '3s', '4s', '6s'],
                        default=['0s', '1s', '2s', '4s', '6s'],
                        key="wagon_shots_options",
                        help="Select which run types to display in breakdown"
                    )
                else:
                    shots_breakdown_options_wagon = []
                
                runs_count_wagon = st.checkbox("Show Total Runs (Wagon)", value=True, key="wagon_total")
                show_fours_sixes_wagon = st.checkbox("Show 4s and 6s (Wagon)", value=True, key="wagon_fs")
                show_bowler_wagon = st.checkbox("Show Bowler (Wagon)", value=True, key="wagon_bowler")
                show_control_wagon = st.checkbox("Show Control % (Wagon)", value=True, key="wagon_ctrl")
                show_prod_shot_wagon = st.checkbox("Show Productive Shot (Wagon)", value=True, key="wagon_prod")
                show_overs_wagon = st.checkbox("Show Overs (Wagon)", value=True, key="wagon_overs")
                show_phase_wagon = st.checkbox("Show Phase (Wagon)", value=True, key="wagon_phase")
            with col3:
                st.markdown("## Run Filter (Wagon Plot)")

                if "run_init_wagon" not in st.session_state:
                    st.session_state["run_all_wagon"] = True
                    for i in range(7):
                        st.session_state[f'run_{i}_wagon'] = True
                    st.session_state["run_init_wagon"] = True

                def sync_all_to_individual_wagon():
                    all_selected = st.session_state["run_all_wagon"]
                    for i in range(7):
                        st.session_state[f'run_{i}_wagon'] = all_selected

                def sync_individual_to_all_wagon():
                    all_selected = all(st.session_state[f'run_{i}_wagon'] for i in range(7))
                    st.session_state["run_all_wagon"] = all_selected

                st.checkbox("All", key="run_all_wagon", on_change=sync_all_to_individual_wagon)

                for i in range(7):
                    st.checkbox(str(i), key=f'run_{i}_wagon', on_change=sync_individual_to_all_wagon)

                individual_selected_wagon = [i for i in range(7) if st.session_state.get(f'run_{i}_wagon', False)]

                if st.session_state["run_all_wagon"]:
                    filtered_runs_wagon = None
                elif individual_selected_wagon:
                    filtered_runs_wagon = individual_selected_wagon
                else:
                    filtered_runs_wagon = []

            if filtered_runs_wagon == []:
                st.warning("Please select at least one run value to display the plot.")
            else:
                with col2:
                    fig_wagon = wagon_zone_plot(
                        df=df,
                        player_name=selected_player_value,
                        pid=selected_pid,
                        inns=selected_inns,
                        mat_num=selected_mat_num,
                        team_bat=selected_team_value,
                        team_bowl=selected_team_bowl_value,
                        bowler_name=bowler_name,
                        bowler_id=bowler_id,
                        run_values=filtered_runs_wagon,
                        competition=selected_competition_value,
                        transparent=False,
                        ground=selected_ground,
                        mcode=selected_mcode,
                        over_values=over_values,
                        phase=phase,
                        date_from=date_from,
                        date_to=date_to,
                        title_components=title_components if show_title_wagon else [],
                        bat_hand=bat_hand,
                        bowl_type=bowl_type,
                        bowl_kind=bowl_kind,
                        bowl_arm=bowl_arm,
                        show_title=show_title_wagon,
                        show_summary=show_summary_wagon,
                        show_shots_breakdown=show_shots_breakdown_wagon,
                        shots_breakdown_options=shots_breakdown_options_wagon,
                        runs_count=runs_count_wagon,
                        show_fours_sixes=show_fours_sixes_wagon,
                        show_control=show_control_wagon,
                        show_prod_shot=show_prod_shot_wagon,
                        show_bowler=show_bowler_wagon,
                        show_overs=show_overs_wagon,
                        show_phase=show_phase_wagon
                    )
                    st.pyplot(fig_wagon)
            
            with col3:
                if fig_wagon:
                    buf = BytesIO()
                    fig_wagon.savefig(buf, format="png", transparent=False, dpi=300, bbox_inches='tight')
                    buf.seek(0)
                    st.download_button(
                        label="📅 Download Plot as PNG",
                        data=buf.getvalue(),
                        file_name=f"{selected_player}_wagon_plot.png",
                        mime="image/png",
                        key="wagon_download"
                    )

        if "Wagon Zone Plot (Transparent Background)" in plot_types:
            st.markdown("<h2 style='text-align: center;'>Wagon Zone Plot (Transparent Background)</h2>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([2, 2, 2])
            
            with col1:
                st.markdown("## Customize Plot Info")    
                show_title_wagon_trans = st.checkbox("Show Plot Title (Wagon)", value=True, key="wagon_trans_title")
                show_summary_wagon_trans = st.checkbox("Show Runs Summary (Wagon)", value=True, key="wagon_trans_summary")
                
                show_shots_breakdown_wagon_trans = st.checkbox("Show Shots Breakdown", value=True, key="wagon_trans_shots_breakdown")
                if show_shots_breakdown_wagon_trans:
                    shots_breakdown_options_wagon_trans = st.multiselect(
                        "Shots to Display",
                        options=['0s', '1s', '2s', '3s', '4s', '6s'],
                        default=['0s', '1s', '2s', '4s', '6s'],
                        key="wagon_trans_shots_options",
                        help="Select which run types to display in breakdown"
                    )
                else:
                    shots_breakdown_options_wagon_trans = []
                
                runs_count_wagon_trans = st.checkbox("Show Total Runs (Wagon)", value=True, key="wagon_trans_total")
                show_fours_sixes_wagon_trans = st.checkbox("Show 4s and 6s (Wagon)", value=True, key="wagon_trans_fs")
                show_bowler_wagon_trans = st.checkbox("Show Bowler (Wagon)", value=True, key="wagon_trans_bowler")
                show_control_wagon_trans = st.checkbox("Show Control % (Wagon)", value=True, key="wagon_trans_ctrl")
                show_overs_wagon_trans = st.checkbox("Show Overs (Wagon)", value=True, key="wagon_trans_overs")
                show_phase_wagon_trans = st.checkbox("Show Phase (Wagon)", value=True, key="wagon_trans_phase")
                show_prod_shot_wagon_trans = st.checkbox("Show Productive Shot (Wagon)", value=True, key="wagon_trans_prod")
            
            with col3:
                st.markdown("## Run Filter (Wagon Plot)")

                if "run_init_wagon_trans" not in st.session_state:
                    st.session_state["run_all_wagon_trans"] = True
                    for i in range(7):
                        st.session_state[f'run_{i}_wagon_trans'] = True
                    st.session_state["run_init_wagon_trans"] = True

                def sync_all_to_individual_wagon_trans():
                    all_selected = st.session_state["run_all_wagon_trans"]
                    for i in range(7):
                        st.session_state[f'run_{i}_wagon_trans'] = all_selected

                def sync_individual_to_all_wagon_trans():
                    all_selected = all(st.session_state[f'run_{i}_wagon_trans'] for i in range(7))
                    st.session_state["run_all_wagon_trans"] = all_selected

                st.checkbox("All", key="run_all_wagon_trans", on_change=sync_all_to_individual_wagon_trans)

                for i in range(7):
                    st.checkbox(str(i), key=f'run_{i}_wagon_trans', on_change=sync_individual_to_all_wagon_trans)

                individual_selected_wagon_trans = [i for i in range(7) if st.session_state.get(f'run_{i}_wagon_trans', False)]

                if st.session_state["run_all_wagon_trans"]:
                    filtered_runs_wagon_trans = None
                elif individual_selected_wagon_trans:
                    filtered_runs_wagon_trans = individual_selected_wagon_trans
                else:
                    filtered_runs_wagon_trans = []

            if filtered_runs_wagon_trans == []:
                st.warning("Please select at least one run value to display the plot.")
            else:
                with col2:
                    fig_wagon_trans = wagon_zone_plot(
                        df=df,
                        player_name=selected_player_value,
                        pid=selected_pid,
                        inns=selected_inns,
                        mat_num=selected_mat_num,
                        team_bat=selected_team_value,
                        team_bowl=selected_team_bowl_value,
                        bowler_name=bowler_name,
                        bowler_id=bowler_id,
                        run_values=filtered_runs_wagon_trans,
                        competition=selected_competition_value,
                        transparent=True,
                        ground=selected_ground,
                        mcode=selected_mcode,
                        over_values=over_values,
                        phase=phase,
                        date_from=date_from,
                        date_to=date_to,
                        title_components=title_components if show_title_wagon_trans else [],
                        bat_hand=bat_hand,
                        bowl_type=bowl_type,
                        bowl_kind=bowl_kind,
                        bowl_arm=bowl_arm,
                        show_title=show_title_wagon_trans,
                        show_summary=show_summary_wagon_trans,
                        show_shots_breakdown=show_shots_breakdown_wagon_trans,
                        shots_breakdown_options=shots_breakdown_options_wagon_trans,
                        runs_count=runs_count_wagon_trans,
                        show_fours_sixes=show_fours_sixes_wagon_trans,
                        show_control=show_control_wagon_trans,
                        show_prod_shot=show_prod_shot_wagon_trans,
                        show_bowler=show_bowler_wagon_trans,
                        show_overs=show_overs_wagon_trans,
                        show_phase=show_phase_wagon_trans
                    )
                    st.pyplot(fig_wagon_trans)
            
            with col3:
                if fig_wagon_trans:
                    buf = BytesIO()
                    fig_wagon_trans.savefig(buf, format="png", transparent=True, dpi=300, bbox_inches='tight')
                    buf.seek(0)
                    st.download_button(
                        label="📅 Download Plot as PNG",
                        data=buf.getvalue(),
                        file_name=f"{selected_player}_wagon_plot_transparent.png",
                        mime="image/png",
                        key="wagon_trans_download"
                    )

        if "Wagon Zone" in plot_types:
            st.markdown("<h2 style='text-align: center;'>Wagon Zone</h2>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([2, 2, 2])
            
            with col1:
                st.markdown("## Customize Plot Info")
                show_title_wagon_desc = st.checkbox("Show Plot Title (Wagon Desc)", value=True, key="wagon_desc_title")
                show_summary_wagon_desc = st.checkbox("Show Runs Summary (Wagon Desc)", value=True, key="wagon_desc_summary")
                
                show_shots_breakdown_wagon_desc = st.checkbox("Show Shots Breakdown", value=True, key="wagon_desc_shots_breakdown")
                if show_shots_breakdown_wagon_desc:
                    shots_breakdown_options_wagon_desc = st.multiselect(
                        "Shots to Display",
                        options=['0s', '1s', '2s', '3s', '4s', '6s'],
                        default=['0s', '1s', '2s', '4s', '6s'],
                        key="wagon_desc_shots_options",
                        help="Select which run types to display in breakdown"
                    )
                else:
                    shots_breakdown_options_wagon_desc = []
                
                runs_count_wagon_desc = st.checkbox("Show Runs Count (Wagon Desc)", value=True, key="wagon_desc_runs")
                show_fours_sixes_wagon_desc = st.checkbox("Show 4s and 6s (Wagon Desc)", value=True, key="wagon_desc_fs")
                show_bowler_wagon_desc = st.checkbox("Show Bowler (Wagon Desc)", value=True, key="wagon_desc_bowler")
                show_control_wagon_desc = st.checkbox("Show Control % (Wagon Desc)", value=True, key="wagon_desc_control")
                show_overs_wagon_desc = st.checkbox("Show Overs (Wagon Desc)", value=True, key="wagon_desc_overs")
                show_phase_wagon_desc = st.checkbox("Show Phase (Wagon Desc)", value=True, key="wagon_desc_phase")
                show_prod_shot_wagon_desc = st.checkbox("Show Productive Shot (Wagon Desc)", value=True, key="wagon_desc_prod")
                show_bowl_type_wagon_desc = st.checkbox("Show Bowl Type (Wagon Desc)", value=True, key="wagon_desc_bowl_type")
                show_bowl_kind_wagon_desc = st.checkbox("Show Bowl Pace (Wagon Desc)", value=True, key="wagon_desc_bowl_kind")
                show_bowl_arm_wagon_desc = st.checkbox("Show Bowl Arm (Wagon Desc)", value=True, key="wagon_desc_bowl_arm")
                show_venue_wagon_desc = st.checkbox("Show Venue (Wagon Desc)", value=True, key="wagon_desc_venue")
            
            with col3:
                st.markdown("## Run Filter (Wagon Zone)")

                if "run_init_wagon_desc" not in st.session_state:
                    st.session_state.run_init_wagon_desc = True
                    for i in range(7):
                        st.session_state[f'run_{i}_wagon_desc'] = True
                    st.session_state["run_all_wagon_desc"] = True

                def sync_all_to_individual_wagon_desc():
                    for i in range(7):
                        st.session_state[f'run_{i}_wagon_desc'] = st.session_state["run_all_wagon_desc"]

                def sync_individual_to_all_wagon_desc():
                    if all(st.session_state.get(f'run_{i}_wagon_desc', False) for i in range(7)):
                        st.session_state["run_all_wagon_desc"] = True

                st.checkbox("All", key="run_all_wagon_desc", on_change=sync_all_to_individual_wagon_desc)

                for i in range(7):
                    st.checkbox(str(i), key=f'run_{i}_wagon_desc', on_change=sync_individual_to_all_wagon_desc)

                individual_selected_wagon_desc = [i for i in range(7) if st.session_state.get(f'run_{i}_wagon_desc', False)]

                if st.session_state["run_all_wagon_desc"]:
                    filtered_runs_wagon_desc = None
                elif individual_selected_wagon_desc:
                    filtered_runs_wagon_desc = individual_selected_wagon_desc
                else:
                    filtered_runs_wagon_desc = []

            if filtered_runs_wagon_desc == []:
                st.warning("Please select at least one run value to display the plot.")
            else:
                fig_wagon_desc = wagon_zone_plot_descriptive(
                    df=df,
                    player_name=selected_player_value,
                    pid=selected_pid,
                    inns=selected_inns,
                    mat_num=selected_mat_num,
                    team_bat=selected_team_value,
                    team_bowl=selected_team_bowl_value,
                    run_values=filtered_runs_wagon_desc,
                    bowler_name=bowler_name,
                    bowler_id=bowler_id,
                    competition=selected_competition_value,
                    transparent=False,
                    ground=selected_ground,
                    mcode=selected_mcode,
                    over_values=over_values,
                    phase=phase,
                    date_from=date_from,
                    date_to=date_to,
                    title_components=title_components if show_title_wagon_desc else [],
                    bat_hand=bat_hand,
                    bowl_type=bowl_type,
                    bowl_kind=bowl_kind,
                    bowl_arm=bowl_arm,
                    show_title=show_title_wagon_desc,
                    show_summary=show_summary_wagon_desc,
                    show_shots_breakdown=show_shots_breakdown_wagon_desc,
                    shots_breakdown_options=shots_breakdown_options_wagon_desc,
                    runs_count=runs_count_wagon_desc,
                    show_fours_sixes=show_fours_sixes_wagon_desc,
                    show_control=show_control_wagon_desc,
                    show_prod_shot=show_prod_shot_wagon_desc,
                    show_bowler=show_bowler_wagon_desc,
                    show_overs=show_overs_wagon_desc,
                    show_phase=show_phase_wagon_desc,
                    show_bowl_type=show_bowl_type_wagon_desc,
                    show_bowl_kind=show_bowl_kind_wagon_desc,
                    show_bowl_arm=show_bowl_arm_wagon_desc,
                    show_venue=show_venue_wagon_desc
                )
                with col2:
                    st.pyplot(fig_wagon_desc)
            
            with col3:
                if fig_wagon_desc:
                    buf = BytesIO()
                    fig_wagon_desc.savefig(buf, format="png", transparent=False, dpi=300, bbox_inches='tight')
                    buf.seek(0)
                    st.download_button(
                        label="📅 Download Plot as PNG",
                        data=buf.getvalue(),
                        file_name=f"{selected_player}_wagon_zone_descriptive.png",
                        mime="image/png",
                        key="wagon_desc_download"
                    )

        if "Wagon Zone (Trans)" in plot_types:
            st.markdown("<h2 style='text-align: center;'>Wagon Zone (Trans)</h2>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([2, 2, 2])
            
            with col1:
                st.markdown("## Customize Plot Info")
                show_title_wagon_desc_trans = st.checkbox("Show Plot Title (Wagon Desc)", value=True, key="wagon_desc_trans_title")
                show_summary_wagon_desc_trans = st.checkbox("Show Runs Summary (Wagon Desc)", value=True, key="wagon_desc_trans_summary")
                
                show_shots_breakdown_wagon_desc_trans = st.checkbox("Show Shots Breakdown", value=True, key="wagon_desc_trans_shots_breakdown")
                if show_shots_breakdown_wagon_desc_trans:
                    shots_breakdown_options_wagon_desc_trans = st.multiselect(
                        "Shots to Display",
                        options=['0s', '1s', '2s', '3s', '4s', '6s'],
                        default=['0s', '1s', '2s', '4s', '6s'],
                        key="wagon_desc_trans_shots_options",
                        help="Select which run types to display in breakdown"
                    )
                else:
                    shots_breakdown_options_wagon_desc_trans = []
                
                runs_count_wagon_desc_trans = st.checkbox("Show Runs Count (Wagon Desc)", value=True, key="wagon_desc_trans_runs")
                show_fours_sixes_wagon_desc_trans = st.checkbox("Show 4s and 6s (Wagon Desc)", value=True, key="wagon_desc_trans_fs")
                show_bowler_wagon_desc_trans = st.checkbox("Show Bowler (Wagon Desc)", value=True, key="wagon_desc_trans_bowler")
                show_control_wagon_desc_trans = st.checkbox("Show Control % (Wagon Desc)", value=True, key="wagon_desc_trans_control")
                show_overs_wagon_desc_trans = st.checkbox("Show Overs (Wagon Desc)", value=True, key="wagon_desc_trans_overs")
                show_phase_wagon_desc_trans = st.checkbox("Show Phase (Wagon Desc)", value=True, key="wagon_desc_trans_phase")
                show_prod_shot_wagon_desc_trans = st.checkbox("Show Productive Shot (Wagon Desc)", value=True, key="wagon_desc_trans_prod")
                show_bowl_type_wagon_desc_trans = st.checkbox("Show Bowl Type (Wagon Desc)", value=True, key="wagon_desc_trans_bowl_type")
                show_bowl_kind_wagon_desc_trans = st.checkbox("Show Bowl Pace (Wagon Desc)", value=True, key="wagon_desc_trans_bowl_kind")
                show_bowl_arm_wagon_desc_trans = st.checkbox("Show Bowl Arm (Wagon Desc)", value=True, key="wagon_desc_trans_bowl_arm")
                show_venue_wagon_desc_trans = st.checkbox("Show Venue (Wagon Desc)", value=True, key="wagon_desc_trans_venue")
            
            with col3:
                st.markdown("## Run Filter (Wagon Zone)")

                if "run_init_wagon_desc_trans" not in st.session_state:
                    st.session_state.run_init_wagon_desc_trans = True
                    for i in range(7):
                        st.session_state[f'run_{i}_wagon_desc_trans'] = True
                    st.session_state["run_all_wagon_desc_trans"] = True

                def sync_all_to_individual_wagon_desc_trans():
                    for i in range(7):
                        st.session_state[f'run_{i}_wagon_desc_trans'] = st.session_state["run_all_wagon_desc_trans"]

                def sync_individual_to_all_wagon_desc_trans():
                    if all(st.session_state.get(f'run_{i}_wagon_desc_trans', False) for i in range(7)):
                        st.session_state["run_all_wagon_desc_trans"] = True

                st.checkbox("All", key="run_all_wagon_desc_trans", on_change=sync_all_to_individual_wagon_desc_trans)

                for i in range(7):
                    st.checkbox(str(i), key=f'run_{i}_wagon_desc_trans', on_change=sync_individual_to_all_wagon_desc_trans)

                individual_selected_wagon_desc_trans = [i for i in range(7) if st.session_state.get(f'run_{i}_wagon_desc_trans', False)]

                if st.session_state["run_all_wagon_desc_trans"]:
                    filtered_runs_wagon_desc_trans = None
                elif individual_selected_wagon_desc_trans:
                    filtered_runs_wagon_desc_trans = individual_selected_wagon_desc_trans
                else:
                    filtered_runs_wagon_desc_trans = []

            if filtered_runs_wagon_desc_trans == []:
                st.warning("Please select at least one run value to display the plot.")
            else:
                fig_wagon_desc_trans = wagon_zone_plot_descriptive(
                    df=df,
                    player_name=selected_player_value,
                    pid=selected_pid,
                    inns=selected_inns,
                    mat_num=selected_mat_num,
                    team_bat=selected_team_value,
                    team_bowl=selected_team_bowl_value,
                    run_values=filtered_runs_wagon_desc_trans,
                    bowler_name=bowler_name,
                    bowler_id=bowler_id,
                    competition=selected_competition_value,
                    transparent=True,
                    ground=selected_ground,
                    mcode=selected_mcode,
                    over_values=over_values,
                    phase=phase,
                    date_from=date_from,
                    date_to=date_to,
                    title_components=title_components if show_title_wagon_desc_trans else [],
                    bat_hand=bat_hand,
                    bowl_type=bowl_type,
                    bowl_kind=bowl_kind,
                    bowl_arm=bowl_arm,
                    show_title=show_title_wagon_desc_trans,
                    show_summary=show_summary_wagon_desc_trans,
                    show_shots_breakdown=show_shots_breakdown_wagon_desc_trans,
                    shots_breakdown_options=shots_breakdown_options_wagon_desc_trans,
                    runs_count=runs_count_wagon_desc_trans,
                    show_fours_sixes=show_fours_sixes_wagon_desc_trans,
                    show_control=show_control_wagon_desc_trans,
                    show_prod_shot=show_prod_shot_wagon_desc_trans,
                    show_bowler=show_bowler_wagon_desc_trans,
                    show_overs=show_overs_wagon_desc_trans,
                    show_phase=show_phase_wagon_desc_trans,
                    show_bowl_type=show_bowl_type_wagon_desc_trans,
                    show_bowl_kind=show_bowl_kind_wagon_desc_trans,
                    show_bowl_arm=show_bowl_arm_wagon_desc_trans,
                    show_venue=show_venue_wagon_desc_trans
                )
                with col2:
                    st.pyplot(fig_wagon_desc_trans)
            
            with col3:
                if fig_wagon_desc_trans:
                    buf = BytesIO()
                    fig_wagon_desc_trans.savefig(buf, format="png", transparent=True, dpi=300, bbox_inches='tight')
                    buf.seek(0)
                    st.download_button(
                        label="📅 Download Plot as PNG",
                        data=buf.getvalue(),
                        file_name=f"{selected_player}_wagon_zone_descriptive_transparent.png",
                        mime="image/png",
                        key="wagon_desc_trans_download"
                    )

        if "━━ Wagon Zone - vs All Types" in plot_types:
            st.markdown("<h2 style='text-align: center;'>Wagon Zone - All Bowler Types</h2>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([2, 2, 2])
            
            with col1:
                st.markdown("## Customize Plot Info")
                show_title_wzn_all_type = st.checkbox("Show Plot Title", value=True, key="wzn_all_type_title")
                show_summary_wzn_all_type = st.checkbox("Show Runs Summary", value=True, key="wzn_all_type_summary")
                runs_count_wzn_all_type = st.checkbox("Show Runs Count", value=True, key="wzn_all_type_runs")
                show_fours_sixes_wzn_all_type = st.checkbox("Show 4s and 6s", value=True, key="wzn_all_type_fs")
                show_bowler_wzn_all_type = st.checkbox("Show Bowler", value=True, key="wzn_all_type_bowler")
                show_control_wzn_all_type = st.checkbox("Show Control %", value=True, key="wzn_all_type_control")
                show_prod_shot_wzn_all_type = st.checkbox("Show Productive Shot", value=True, key="wzn_all_type_prod")
                show_overs_wzn_all_type = st.checkbox("Show Overs", value=True, key="wzn_all_type_overs")
                show_phase_wzn_all_type = st.checkbox("Show Phase", value=True, key="wzn_all_type_phase")
                show_bowl_type_wzn_all_type = st.checkbox("Show Bowl Type", value=True, key="wzn_all_type_bowl_type")
                show_venue_wzn_all_type = st.checkbox("Show Venue", value=True, key="wzn_all_type_venue")

            with col3:
                st.markdown("## Run Filter (Wagon Zone)")
                if "run_init_wzn_all_type" not in st.session_state:
                    st.session_state["run_all_wzn_all_type"] = True
                    for i in range(7):
                        st.session_state[f'run_{i}_wzn_all_type'] = True
                    st.session_state["run_init_wzn_all_type"] = True

                def sync_all_to_individual_wzn_all_type():
                    all_selected = st.session_state["run_all_wzn_all_type"]
                    for i in range(7):
                        st.session_state[f'run_{i}_wzn_all_type'] = all_selected

                def sync_individual_to_all_wzn_all_type():
                    all_selected = all(st.session_state[f'run_{i}_wzn_all_type'] for i in range(7))
                    st.session_state["run_all_wzn_all_type"] = all_selected

                st.checkbox("All", key="run_all_wzn_all_type", on_change=sync_all_to_individual_wzn_all_type)
                for i in range(7):
                    st.checkbox(str(i), key=f'run_{i}_wzn_all_type', on_change=sync_individual_to_all_wzn_all_type)

                individual_selected_wzn_all_type = [i for i in range(7) if st.session_state.get(f'run_{i}_wzn_all_type', False)]
                if st.session_state["run_all_wzn_all_type"]:
                    filtered_runs_wzn_all_type = None
                elif individual_selected_wzn_all_type:
                    filtered_runs_wzn_all_type = individual_selected_wzn_all_type
                else:
                    filtered_runs_wzn_all_type = []
                    
            if filtered_runs_wzn_all_type == []:
                st.warning("Please select at least one run value to display the plot.")
            else:
                fig_wzn_all_type = wagon_zone_plot_descriptive(
                    df=df,
                    player_name=selected_player_value,
                    pid=selected_pid,
                    inns=selected_inns,
                    mat_num=selected_mat_num,
                    team_bat=selected_team_value,
                    team_bowl=selected_team_bowl_value,
                    run_values=filtered_runs_wzn_all_type,
                    bowler_name=bowler_name,
                    bowler_id=bowler_id,
                    competition=selected_competition_value,
                    transparent=False,
                    over_values=over_values,
                    phase=phase,
                    ground=selected_ground,
                    mcode=selected_mcode,
                    date_from=date_from,
                    date_to=date_to,
                    title_components=title_components if show_title_wzn_all_type else [],
                    bat_hand=bat_hand,
                    bowl_type=bowl_type,
                    bowl_kind=None,
                    bowl_arm=bowl_arm,
                    show_title=show_title_wzn_all_type,
                    show_summary=show_summary_wzn_all_type,
                    runs_count=runs_count_wzn_all_type,
                    show_fours_sixes=show_fours_sixes_wzn_all_type,
                    show_control=show_control_wzn_all_type,
                    show_prod_shot=show_prod_shot_wzn_all_type,
                    show_bowler=show_bowler_wzn_all_type,
                    show_venue=show_venue_wzn_all_type,
                    show_overs=show_overs_wzn_all_type,
                    show_phase=show_phase_wzn_all_type,
                    show_bowl_type=show_bowl_type_wzn_all_type
                )
                with col2:
                    st.pyplot(fig_wzn_all_type)
            
            with col3:
                if fig_wzn_all_type:
                    buf = BytesIO()
                    fig_wzn_all_type.savefig(buf, format="png", transparent=False, dpi=300, bbox_inches='tight')
                    buf.seek(0)
                    st.download_button(
                        label="📅 Download Plot as PNG",
                        data=buf.getvalue(),
                        file_name=f"{selected_player}_wzn_all_type.png",
                        mime="image/png",
                        key="wzn_all_type_download"
                    )

        if "━━ Wagon Zone - vs Pace" in plot_types:
            st.markdown("<h2 style='text-align: center;'>Wagon Zone vs Pace Bowlers</h2>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([2, 2, 2])
            
            with col1:
                st.markdown("## Customize Plot Info")
                show_title_wzn_pace = st.checkbox("Show Plot Title", value=True, key="wzn_pace_title")
                show_summary_wzn_pace = st.checkbox("Show Runs Summary", value=True, key="wzn_pace_summary")
                runs_count_wzn_pace = st.checkbox("Show Runs Count", value=True, key="wzn_pace_runs")
                show_fours_sixes_wzn_pace = st.checkbox("Show 4s and 6s", value=True, key="wzn_pace_fs")
                show_bowler_wzn_pace = st.checkbox("Show Bowler", value=True, key="wzn_pace_bowler")
                show_control_wzn_pace = st.checkbox("Show Control %", value=True, key="wzn_pace_control")
                show_prod_shot_wzn_pace = st.checkbox("Show Productive Shot", value=True, key="wzn_pace_prod")
                show_overs_wzn_pace = st.checkbox("Show Overs", value=True, key="wzn_pace_overs")
                show_phase_wzn_pace = st.checkbox("Show Phase", value=True, key="wzn_pace_phase")
                show_bowl_type_wzn_pace = st.checkbox("Show Bowl Type", value=True, key="wzn_pace_bowl_type")
                show_venue_wzn_pace = st.checkbox("Show Venue", value=True, key="wzn_pace_venue")

            with col3:
                st.markdown("## Run Filter (Wagon Zone)")
                if "run_init_wzn_pace" not in st.session_state:
                    st.session_state["run_all_wzn_pace"] = True
                    for i in range(7):
                        st.session_state[f'run_{i}_wzn_pace'] = True
                    st.session_state["run_init_wzn_pace"] = True

                def sync_all_to_individual_wzn_pace():
                    all_selected = st.session_state["run_all_wzn_pace"]
                    for i in range(7):
                        st.session_state[f'run_{i}_wzn_pace'] = all_selected

                def sync_individual_to_all_wzn_pace():
                    all_selected = all(st.session_state[f'run_{i}_wzn_pace'] for i in range(7))
                    st.session_state["run_all_wzn_pace"] = all_selected

                st.checkbox("All", key="run_all_wzn_pace", on_change=sync_all_to_individual_wzn_pace)
                for i in range(7):
                    st.checkbox(str(i), key=f'run_{i}_wzn_pace', on_change=sync_individual_to_all_wzn_pace)

                individual_selected_wzn_pace = [i for i in range(7) if st.session_state.get(f'run_{i}_wzn_pace', False)]
                if st.session_state["run_all_wzn_pace"]:
                    filtered_runs_wzn_pace = None
                elif individual_selected_wzn_pace:
                    filtered_runs_wzn_pace = individual_selected_wzn_pace
                else:
                    filtered_runs_wzn_pace = []
                    
            if filtered_runs_wzn_pace == []:
                st.warning("Please select at least one run value to display the plot.")
            else:
                fig_wzn_pace = wagon_zone_plot_descriptive(
                    df=df,
                    player_name=selected_player_value,
                    pid=selected_pid,
                    inns=selected_inns,
                    mat_num=selected_mat_num,
                    team_bat=selected_team_value,
                    team_bowl=selected_team_bowl_value,
                    run_values=filtered_runs_wzn_pace,
                    bowler_name=bowler_name,
                    bowler_id=bowler_id,
                    competition=selected_competition_value,
                    transparent=False,
                    over_values=over_values,
                    phase=phase,
                    ground=selected_ground,
                    mcode=selected_mcode,
                    date_from=date_from,
                    date_to=date_to,
                    title_components=title_components if show_title_wzn_pace else [],
                    bat_hand=bat_hand,
                    bowl_type=bowl_type,
                    bowl_kind=["pace bowler", "Pace"],
                    bowl_arm=bowl_arm,
                    show_title=show_title_wzn_pace,
                    show_summary=show_summary_wzn_pace,
                    runs_count=runs_count_wzn_pace,
                    show_fours_sixes=show_fours_sixes_wzn_pace,
                    show_control=show_control_wzn_pace,
                    show_prod_shot=show_prod_shot_wzn_pace,
                    show_bowler=show_bowler_wzn_pace,
                    show_venue=show_venue_wzn_pace,
                    show_overs=show_overs_wzn_pace,
                    show_phase=show_phase_wzn_pace,
                    show_bowl_type=show_bowl_type_wzn_pace
                )
                with col2:
                    st.pyplot(fig_wzn_pace)
            
            with col3:
                if fig_wzn_pace:
                    buf = BytesIO()
                    fig_wzn_pace.savefig(buf, format="png", transparent=False, dpi=300, bbox_inches='tight')
                    buf.seek(0)
                    st.download_button(
                        label="📅 Download Plot as PNG",
                        data=buf.getvalue(),
                        file_name=f"{selected_player}_wzn_pace.png",
                        mime="image/png",
                        key="wzn_pace_download"
                    )

        if "━━ Wagon Zone - vs Spin" in plot_types:
            st.markdown("<h2 style='text-align: center;'>Wagon Zone vs Spin Bowlers</h2>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([2, 2, 2])
            
            with col1:
                st.markdown("## Customize Plot Info")
                show_title_wzn_spin = st.checkbox("Show Plot Title", value=True, key="wzn_spin_title")
                show_summary_wzn_spin = st.checkbox("Show Runs Summary", value=True, key="wzn_spin_summary")
                runs_count_wzn_spin = st.checkbox("Show Runs Count", value=True, key="wzn_spin_runs")
                show_fours_sixes_wzn_spin = st.checkbox("Show 4s and 6s", value=True, key="wzn_spin_fs")
                show_bowler_wzn_spin = st.checkbox("Show Bowler", value=True, key="wzn_spin_bowler")
                show_control_wzn_spin = st.checkbox("Show Control %", value=True, key="wzn_spin_control")
                show_prod_shot_wzn_spin = st.checkbox("Show Productive Shot", value=True, key="wzn_spin_prod")
                show_overs_wzn_spin = st.checkbox("Show Overs", value=True, key="wzn_spin_overs")
                show_phase_wzn_spin = st.checkbox("Show Phase", value=True, key="wzn_spin_phase")
                show_bowl_type_wzn_spin = st.checkbox("Show Bowl Type", value=True, key="wzn_spin_bowl_type")
                show_venue_wzn_spin = st.checkbox("Show Venue", value=True, key="wzn_spin_venue")

            with col3:
                st.markdown("## Run Filter (Wagon Zone)")
                if "run_init_wzn_spin" not in st.session_state:
                    st.session_state["run_all_wzn_spin"] = True
                    for i in range(7):
                        st.session_state[f'run_{i}_wzn_spin'] = True
                    st.session_state["run_init_wzn_spin"] = True

                def sync_all_to_individual_wzn_spin():
                    all_selected = st.session_state["run_all_wzn_spin"]
                    for i in range(7):
                        st.session_state[f'run_{i}_wzn_spin'] = all_selected

                def sync_individual_to_all_wzn_spin():
                    all_selected = all(st.session_state[f'run_{i}_wzn_spin'] for i in range(7))
                    st.session_state["run_all_wzn_spin"] = all_selected

                st.checkbox("All", key="run_all_wzn_spin", on_change=sync_all_to_individual_wzn_spin)
                for i in range(7):
                    st.checkbox(str(i), key=f'run_{i}_wzn_spin', on_change=sync_individual_to_all_wzn_spin)

                individual_selected_wzn_spin = [i for i in range(7) if st.session_state.get(f'run_{i}_wzn_spin', False)]
                if st.session_state["run_all_wzn_spin"]:
                    filtered_runs_wzn_spin = None
                elif individual_selected_wzn_spin:
                    filtered_runs_wzn_spin = individual_selected_wzn_spin
                else:
                    filtered_runs_wzn_spin = []
                    
            if filtered_runs_wzn_spin == []:
                st.warning("Please select at least one run value to display the plot.")
            else:
                fig_wzn_spin = wagon_zone_plot_descriptive(
                    df=df,
                    player_name=selected_player_value,
                    pid=selected_pid,
                    inns=selected_inns,
                    mat_num=selected_mat_num,
                    team_bat=selected_team_value,
                    team_bowl=selected_team_bowl_value,
                    run_values=filtered_runs_wzn_spin,
                    bowler_name=bowler_name,
                    bowler_id=bowler_id,
                    competition=selected_competition_value,
                    transparent=False,
                    over_values=over_values,
                    phase=phase,
                    ground=selected_ground,
                    mcode=selected_mcode,
                    date_from=date_from,
                    date_to=date_to,
                    title_components=title_components if show_title_wzn_spin else [],
                    bat_hand=bat_hand,
                    bowl_type=bowl_type,
                    bowl_kind=["spin bowler", "Spin"],
                    bowl_arm=bowl_arm,
                    show_title=show_title_wzn_spin,
                    show_summary=show_summary_wzn_spin,
                    runs_count=runs_count_wzn_spin,
                    show_fours_sixes=show_fours_sixes_wzn_spin,
                    show_control=show_control_wzn_spin,
                    show_prod_shot=show_prod_shot_wzn_spin,
                    show_bowler=show_bowler_wzn_spin,
                    show_venue=show_venue_wzn_spin,
                    show_overs=show_overs_wzn_spin,
                    show_phase=show_phase_wzn_spin,
                    show_bowl_type=show_bowl_type_wzn_spin
                )
                with col2:
                    st.pyplot(fig_wzn_spin)
            
            with col3:
                if fig_wzn_spin:
                    buf = BytesIO()
                    fig_wzn_spin.savefig(buf, format="png", transparent=False, dpi=300, bbox_inches='tight')
                    buf.seek(0)
                    st.download_button(
                        label="📅 Download Plot as PNG",
                        data=buf.getvalue(),
                        file_name=f"{selected_player}_wzn_spin.png",
                        mime="image/png",
                        key="wzn_spin_download"
                    )

        if "━━ Wagon Zone - All Phases" in plot_types:
            st.markdown("<h2 style='text-align: center;'>Wagon Zone - All Phases</h2>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([2, 2, 2])
            
            with col1:
                st.markdown("## Customize Plot Info")
                show_title_wzn_phs_all = st.checkbox("Show Plot Title", value=True, key="wzn_phs_all_title")
                show_summary_wzn_phs_all = st.checkbox("Show Runs Summary", value=True, key="wzn_phs_all_summary")
                runs_count_wzn_phs_all = st.checkbox("Show Runs Count", value=True, key="wzn_phs_all_runs")
                show_fours_sixes_wzn_phs_all = st.checkbox("Show 4s and 6s", value=True, key="wzn_phs_all_fs")
                show_bowler_wzn_phs_all = st.checkbox("Show Bowler", value=True, key="wzn_phs_all_bowler")
                show_control_wzn_phs_all = st.checkbox("Show Control %", value=True, key="wzn_phs_all_control")
                show_prod_shot_wzn_phs_all = st.checkbox("Show Productive Shot", value=True, key="wzn_phs_all_prod")
                show_overs_wzn_phs_all = st.checkbox("Show Overs", value=True, key="wzn_phs_all_overs")
                show_phase_wzn_phs_all = st.checkbox("Show Phase", value=True, key="wzn_phs_all_phase")
                show_venue_wzn_phs_all = st.checkbox("Show Venue", value=True, key="wzn_phs_all_venue")

            with col3:
                st.markdown("## Run Filter (Wagon Zone)")
                if "run_init_wzn_phs_all" not in st.session_state:
                    st.session_state["run_all_wzn_phs_all"] = True
                    for i in range(7):
                        st.session_state[f'run_{i}_wzn_phs_all'] = True
                    st.session_state["run_init_wzn_phs_all"] = True

                def sync_all_to_individual_wzn_phs_all():
                    all_selected = st.session_state["run_all_wzn_phs_all"]
                    for i in range(7):
                        st.session_state[f'run_{i}_wzn_phs_all'] = all_selected

                def sync_individual_to_all_wzn_phs_all():
                    all_selected = all(st.session_state[f'run_{i}_wzn_phs_all'] for i in range(7))
                    st.session_state["run_all_wzn_phs_all"] = all_selected

                st.checkbox("All", key="run_all_wzn_phs_all", on_change=sync_all_to_individual_wzn_phs_all)
                for i in range(7):
                    st.checkbox(str(i), key=f'run_{i}_wzn_phs_all', on_change=sync_individual_to_all_wzn_phs_all)

                individual_selected_wzn_phs_all = [i for i in range(7) if st.session_state.get(f'run_{i}_wzn_phs_all', False)]
                if st.session_state["run_all_wzn_phs_all"]:
                    filtered_runs_wzn_phs_all = None
                elif individual_selected_wzn_phs_all:
                    filtered_runs_wzn_phs_all = individual_selected_wzn_phs_all
                else:
                    filtered_runs_wzn_phs_all = []
                    
            if filtered_runs_wzn_phs_all == []:
                st.warning("Please select at least one run value to display the plot.")
            else:
                fig_wzn_all_phase = wagon_zone_plot_descriptive(
                    df=df,
                    player_name=selected_player_value,
                    pid=selected_pid,
                    inns=selected_inns,
                    mat_num=selected_mat_num,
                    team_bat=selected_team_value,
                    team_bowl=selected_team_bowl_value,
                    run_values=filtered_runs_wzn_phs_all,
                    bowler_name=bowler_name,
                    bowler_id=bowler_id,
                    competition=selected_competition_value,
                    transparent=False,
                    over_values=over_values,
                    phase=None,
                    ground=selected_ground,
                    mcode=selected_mcode,
                    date_from=date_from,
                    date_to=date_to,
                    title_components=title_components if show_title_wzn_phs_all else [],
                    bat_hand=bat_hand,
                    bowl_type=bowl_type,
                    bowl_kind=bowl_kind,
                    bowl_arm=bowl_arm,
                    show_title=show_title_wzn_phs_all,
                    show_summary=show_summary_wzn_phs_all,
                    runs_count=runs_count_wzn_phs_all,
                    show_fours_sixes=show_fours_sixes_wzn_phs_all,
                    show_control=show_control_wzn_phs_all,
                    show_prod_shot=show_prod_shot_wzn_phs_all,
                    show_bowler=show_bowler_wzn_phs_all,
                    show_venue=show_venue_wzn_phs_all,
                    show_overs=show_overs_wzn_phs_all,
                    show_phase=show_phase_wzn_phs_all
                )
                with col2:
                    st.pyplot(fig_wzn_all_phase)
            
            with col3:
                if fig_wzn_all_phase:
                    buf = BytesIO()
                    fig_wzn_all_phase.savefig(buf, format="png", transparent=False, dpi=300, bbox_inches='tight')
                    buf.seek(0)
                    st.download_button(
                        label="📅 Download Plot as PNG",
                        data=buf.getvalue(),
                        file_name=f"{selected_player}_wzn_all_phase.png",
                        mime="image/png",
                        key="wzn_all_phase_download"
                    )

        if "━━ Wagon Zone - Powerplay" in plot_types:
            st.markdown("<h2 style='text-align: center;'>Wagon Zone - Powerplay</h2>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([2, 2, 2])
            
            with col1:
                st.markdown("## Customize Plot Info")
                show_title_wzn_pp = st.checkbox("Show Plot Title", value=True, key="wzn_pp_title")
                show_summary_wzn_pp = st.checkbox("Show Runs Summary", value=True, key="wzn_pp_summary")
                runs_count_wzn_pp = st.checkbox("Show Runs Count", value=True, key="wzn_pp_runs")
                show_fours_sixes_wzn_pp = st.checkbox("Show 4s and 6s", value=True, key="wzn_pp_fs")
                show_bowler_wzn_pp = st.checkbox("Show Bowler", value=True, key="wzn_pp_bowler")
                show_control_wzn_pp = st.checkbox("Show Control %", value=True, key="wzn_pp_control")
                show_prod_shot_wzn_pp = st.checkbox("Show Productive Shot", value=True, key="wzn_pp_prod")
                show_overs_wzn_pp = st.checkbox("Show Overs", value=True, key="wzn_pp_overs")
                show_phase_wzn_pp = st.checkbox("Show Phase", value=True, key="wzn_pp_phase")
                show_venue_wzn_pp = st.checkbox("Show Venue", value=True, key="wzn_pp_venue")

            with col3:
                st.markdown("## Run Filter (Wagon Zone)")
                if "run_init_wzn_pp" not in st.session_state:
                    st.session_state["run_all_wzn_pp"] = True
                    for i in range(7):
                        st.session_state[f'run_{i}_wzn_pp'] = True
                    st.session_state["run_init_wzn_pp"] = True

                def sync_all_to_individual_wzn_pp():
                    all_selected = st.session_state["run_all_wzn_pp"]
                    for i in range(7):
                        st.session_state[f'run_{i}_wzn_pp'] = all_selected

                def sync_individual_to_all_wzn_pp():
                    all_selected = all(st.session_state[f'run_{i}_wzn_pp'] for i in range(7))
                    st.session_state["run_all_wzn_pp"] = all_selected

                st.checkbox("All", key="run_all_wzn_pp", on_change=sync_all_to_individual_wzn_pp)
                for i in range(7):
                    st.checkbox(str(i), key=f'run_{i}_wzn_pp', on_change=sync_individual_to_all_wzn_pp)

                individual_selected_wzn_pp = [i for i in range(7) if st.session_state.get(f'run_{i}_wzn_pp', False)]
                if st.session_state["run_all_wzn_pp"]:
                    filtered_runs_wzn_pp = None
                elif individual_selected_wzn_pp:
                    filtered_runs_wzn_pp = individual_selected_wzn_pp
                else:
                    filtered_runs_wzn_pp = []
                    
            if filtered_runs_wzn_pp == []:
                st.warning("Please select at least one run value to display the plot.")
            else:
                fig_wzn_pp = wagon_zone_plot_descriptive(
                    df=df,
                    player_name=selected_player_value,
                    pid=selected_pid,
                    inns=selected_inns,
                    mat_num=selected_mat_num,
                    team_bat=selected_team_value,
                    team_bowl=selected_team_bowl_value,
                    run_values=filtered_runs_wzn_pp,
                    bowler_name=bowler_name,
                    bowler_id=bowler_id,
                    competition=selected_competition_value,
                    transparent=False,
                    over_values=over_values,
                    phase=[1],
                    ground=selected_ground,
                    mcode=selected_mcode,
                    date_from=date_from,
                    date_to=date_to,
                    title_components=title_components if show_title_wzn_pp else [],
                    bat_hand=bat_hand,
                    bowl_type=bowl_type,
                    bowl_kind=bowl_kind,
                    bowl_arm=bowl_arm,
                    show_title=show_title_wzn_pp,
                    show_summary=show_summary_wzn_pp,
                    runs_count=runs_count_wzn_pp,
                    show_fours_sixes=show_fours_sixes_wzn_pp,
                    show_control=show_control_wzn_pp,
                    show_prod_shot=show_prod_shot_wzn_pp,
                    show_bowler=show_bowler_wzn_pp,
                    show_venue=show_venue_wzn_pp,
                    show_overs=show_overs_wzn_pp,
                    show_phase=show_phase_wzn_pp
                )
                with col2:
                    st.pyplot(fig_wzn_pp)
            
            with col3:
                if fig_wzn_pp:
                    buf = BytesIO()
                    fig_wzn_pp.savefig(buf, format="png", transparent=False, dpi=300, bbox_inches='tight')
                    buf.seek(0)
                    st.download_button(
                        label="📅 Download Plot as PNG",
                        data=buf.getvalue(),
                        file_name=f"{selected_player}_wzn_pp.png",
                        mime="image/png",
                        key="wzn_pp_download"
                    )

        if "━━ Wagon Zone - Middle" in plot_types:
            st.markdown("<h2 style='text-align: center;'>Wagon Zone - Middle</h2>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([2, 2, 2])
            
            with col1:
                st.markdown("## Customize Plot Info")
                show_title_wzn_mid = st.checkbox("Show Plot Title", value=True, key="wzn_mid_title")
                show_summary_wzn_mid = st.checkbox("Show Runs Summary", value=True, key="wzn_mid_summary")
                runs_count_wzn_mid = st.checkbox("Show Runs Count", value=True, key="wzn_mid_runs")
                show_fours_sixes_wzn_mid = st.checkbox("Show 4s and 6s", value=True, key="wzn_mid_fs")
                show_bowler_wzn_mid = st.checkbox("Show Bowler", value=True, key="wzn_mid_bowler")
                show_control_wzn_mid = st.checkbox("Show Control %", value=True, key="wzn_mid_control")
                show_prod_shot_wzn_mid = st.checkbox("Show Productive Shot", value=True, key="wzn_mid_prod")
                show_overs_wzn_mid = st.checkbox("Show Overs", value=True, key="wzn_mid_overs")
                show_phase_wzn_mid = st.checkbox("Show Phase", value=True, key="wzn_mid_phase")
                show_venue_wzn_mid = st.checkbox("Show Venue", value=True, key="wzn_mid_venue")

            with col3:
                st.markdown("## Run Filter (Wagon Zone)")
                if "run_init_wzn_mid" not in st.session_state:
                    st.session_state["run_all_wzn_mid"] = True
                    for i in range(7):
                        st.session_state[f'run_{i}_wzn_mid'] = True
                    st.session_state["run_init_wzn_mid"] = True

                def sync_all_to_individual_wzn_mid():
                    all_selected = st.session_state["run_all_wzn_mid"]
                    for i in range(7):
                        st.session_state[f'run_{i}_wzn_mid'] = all_selected

                def sync_individual_to_all_wzn_mid():
                    all_selected = all(st.session_state[f'run_{i}_wzn_mid'] for i in range(7))
                    st.session_state["run_all_wzn_mid"] = all_selected

                st.checkbox("All", key="run_all_wzn_mid", on_change=sync_all_to_individual_wzn_mid)
                for i in range(7):
                    st.checkbox(str(i), key=f'run_{i}_wzn_mid', on_change=sync_individual_to_all_wzn_mid)

                individual_selected_wzn_mid = [i for i in range(7) if st.session_state.get(f'run_{i}_wzn_mid', False)]
                if st.session_state["run_all_wzn_mid"]:
                    filtered_runs_wzn_mid = None
                elif individual_selected_wzn_mid:
                    filtered_runs_wzn_mid = individual_selected_wzn_mid
                else:
                    filtered_runs_wzn_mid = []
                    
            if filtered_runs_wzn_mid == []:
                st.warning("Please select at least one run value to display the plot.")
            else:
                fig_wzn_mid = wagon_zone_plot_descriptive(
                    df=df,
                    player_name=selected_player_value,
                    pid=selected_pid,
                    inns=selected_inns,
                    mat_num=selected_mat_num,
                    team_bat=selected_team_value,
                    team_bowl=selected_team_bowl_value,
                    run_values=filtered_runs_wzn_mid,
                    bowler_name=bowler_name,
                    bowler_id=bowler_id,
                    competition=selected_competition_value,
                    transparent=False,
                    over_values=over_values,
                    phase=[2],
                    ground=selected_ground,
                    mcode=selected_mcode,
                    date_from=date_from,
                    date_to=date_to,
                    title_components=title_components if show_title_wzn_mid else [],
                    bat_hand=bat_hand,
                    bowl_type=bowl_type,
                    bowl_kind=bowl_kind,
                    bowl_arm=bowl_arm,
                    show_title=show_title_wzn_mid,
                    show_summary=show_summary_wzn_mid,
                    runs_count=runs_count_wzn_mid,
                    show_fours_sixes=show_fours_sixes_wzn_mid,
                    show_control=show_control_wzn_mid,
                    show_prod_shot=show_prod_shot_wzn_mid,
                    show_bowler=show_bowler_wzn_mid,
                    show_venue=show_venue_wzn_mid,
                    show_overs=show_overs_wzn_mid,
                    show_phase=show_phase_wzn_mid
                )
                with col2:
                    st.pyplot(fig_wzn_mid)
            
            with col3:
                if fig_wzn_mid:
                    buf = BytesIO()
                    fig_wzn_mid.savefig(buf, format="png", transparent=False, dpi=300, bbox_inches='tight')
                    buf.seek(0)
                    st.download_button(
                        label="📅 Download Plot as PNG",
                        data=buf.getvalue(),
                        file_name=f"{selected_player}_wzn_mid.png",
                        mime="image/png",
                        key="wzn_mid_download"
                    )

        if "━━ Wagon Zone - Slog" in plot_types:
            st.markdown("<h2 style='text-align: center;'>Wagon Zone - Slog</h2>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([2, 2, 2])
            
            with col1:
                st.markdown("## Customize Plot Info")
                show_title_wzn_slog = st.checkbox("Show Plot Title", value=True, key="wzn_slog_title")
                show_summary_wzn_slog = st.checkbox("Show Runs Summary", value=True, key="wzn_slog_summary")
                runs_count_wzn_slog = st.checkbox("Show Runs Count", value=True, key="wzn_slog_runs")
                show_fours_sixes_wzn_slog = st.checkbox("Show 4s and 6s", value=True, key="wzn_slog_fs")
                show_bowler_wzn_slog = st.checkbox("Show Bowler", value=True, key="wzn_slog_bowler")
                show_control_wzn_slog = st.checkbox("Show Control %", value=True, key="wzn_slog_control")
                show_prod_shot_wzn_slog = st.checkbox("Show Productive Shot", value=True, key="wzn_slog_prod")
                show_overs_wzn_slog = st.checkbox("Show Overs", value=True, key="wzn_slog_overs")
                show_phase_wzn_slog = st.checkbox("Show Phase", value=True, key="wzn_slog_phase")
                show_venue_wzn_slog = st.checkbox("Show Venue", value=True, key="wzn_slog_venue")

            with col3:
                st.markdown("## Run Filter (Wagon Zone)")
                if "run_init_wzn_slog" not in st.session_state:
                    st.session_state["run_all_wzn_slog"] = True
                    for i in range(7):
                        st.session_state[f'run_{i}_wzn_slog'] = True
                    st.session_state["run_init_wzn_slog"] = True

                def sync_all_to_individual_wzn_slog():
                    all_selected = st.session_state["run_all_wzn_slog"]
                    for i in range(7):
                        st.session_state[f'run_{i}_wzn_slog'] = all_selected

                def sync_individual_to_all_wzn_slog():
                    all_selected = all(st.session_state[f'run_{i}_wzn_slog'] for i in range(7))
                    st.session_state["run_all_wzn_slog"] = all_selected

                st.checkbox("All", key="run_all_wzn_slog", on_change=sync_all_to_individual_wzn_slog)
                for i in range(7):
                    st.checkbox(str(i), key=f'run_{i}_wzn_slog', on_change=sync_individual_to_all_wzn_slog)

                individual_selected_wzn_slog = [i for i in range(7) if st.session_state.get(f'run_{i}_wzn_slog', False)]
                if st.session_state["run_all_wzn_slog"]:
                    filtered_runs_wzn_slog = None
                elif individual_selected_wzn_slog:
                    filtered_runs_wzn_slog = individual_selected_wzn_slog
                else:
                    filtered_runs_wzn_slog = []
                    
            if filtered_runs_wzn_slog == []:
                st.warning("Please select at least one run value to display the plot.")
            else:
                fig_wzn_slog = wagon_zone_plot_descriptive(
                    df=df,
                    player_name=selected_player_value,
                    pid=selected_pid,
                    inns=selected_inns,
                    mat_num=selected_mat_num,
                    team_bat=selected_team_value,
                    team_bowl=selected_team_bowl_value,
                    run_values=filtered_runs_wzn_slog,
                    bowler_name=bowler_name,
                    bowler_id=bowler_id,
                    competition=selected_competition_value,
                    transparent=False,
                    over_values=over_values,
                    phase=[3],
                    ground=selected_ground,
                    mcode=selected_mcode,
                    date_from=date_from,
                    date_to=date_to,
                    title_components=title_components if show_title_wzn_slog else [],
                    bat_hand=bat_hand,
                    bowl_type=bowl_type,
                    bowl_kind=bowl_kind,
                    bowl_arm=bowl_arm,
                    show_title=show_title_wzn_slog,
                    show_summary=show_summary_wzn_slog,
                    runs_count=runs_count_wzn_slog,
                    show_fours_sixes=show_fours_sixes_wzn_slog,
                    show_control=show_control_wzn_slog,
                    show_prod_shot=show_prod_shot_wzn_slog,
                    show_bowler=show_bowler_wzn_slog,
                    show_venue=show_venue_wzn_slog,
                    show_overs=show_overs_wzn_slog,
                    show_phase=show_phase_wzn_slog
                )
                with col2:
                    st.pyplot(fig_wzn_slog)
            
            with col3:
                if fig_wzn_slog:
                    buf = BytesIO()
                    fig_wzn_slog.savefig(buf, format="png", transparent=False, dpi=300, bbox_inches='tight')
                    buf.seek(0)
                    st.download_button(
                        label="📅 Download Plot as PNG",
                        data=buf.getvalue(),
                        file_name=f"{selected_player}_wzn_slog.png",
                        mime="image/png",
                        key="wzn_slog_download"
                    )

        if "━━ Wagon Zone - All Kinds" in plot_types:
            st.markdown("<h2 style='text-align: center;'>Wagon Zone - All Bowler Kinds</h2>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([2, 2, 2])
            
            with col1:
                st.markdown("## Customize Plot Info")
                show_title_wzn_all_kind = st.checkbox("Show Plot Title", value=True, key="wzn_all_kind_title")
                show_summary_wzn_all_kind = st.checkbox("Show Runs Summary", value=True, key="wzn_all_kind_summary")
                
                show_shots_breakdown_wzn_all_kind = st.checkbox("Show Shots Breakdown", value=True, key="wzn_all_kind_shots_breakdown")
                if show_shots_breakdown_wzn_all_kind:
                    shots_breakdown_options_wzn_all_kind = st.multiselect(
                        "Shots to Display",
                        options=['0s', '1s', '2s', '3s', '4s', '6s'],
                        default=['0s', '1s', '2s', '4s', '6s'],
                        key="wzn_all_kind_shots_options",
                        help="Select which run types to display in breakdown"
                    )
                else:
                    shots_breakdown_options_wzn_all_kind = []
                
                runs_count_wzn_all_kind = st.checkbox("Show Runs Count", value=True, key="wzn_all_kind_runs")
                show_fours_sixes_wzn_all_kind = st.checkbox("Show 4s and 6s", value=True, key="wzn_all_kind_fs")
                show_bowler_wzn_all_kind = st.checkbox("Show Bowler", value=True, key="wzn_all_kind_bowler")
                show_control_wzn_all_kind = st.checkbox("Show Control %", value=True, key="wzn_all_kind_control")
                show_prod_shot_wzn_all_kind = st.checkbox("Show Productive Shot", value=True, key="wzn_all_kind_prod")
                show_overs_wzn_all_kind = st.checkbox("Show Overs", value=True, key="wzn_all_kind_overs")
                show_phase_wzn_all_kind = st.checkbox("Show Phase", value=True, key="wzn_all_kind_phase")
                show_bowl_type_wzn_all_kind = st.checkbox("Show Bowl Type", value=True, key="wzn_all_kind_bowl_type")
                show_bowl_kind_wzn_all_kind = st.checkbox("Show Bowl Pace", value=True, key="wzn_all_kind_bowl_kind")
                show_bowl_arm_wzn_all_kind = st.checkbox("Show Bowl Arm", value=True, key="wzn_all_kind_bowl_arm")
                show_venue_wzn_all_kind = st.checkbox("Show Venue", value=True, key="wzn_all_kind_venue")

            with col3:
                st.markdown("## Run Filter (Wagon Zone)")
                if "run_init_wzn_all_kind" not in st.session_state:
                    st.session_state["run_all_wzn_all_kind"] = True
                    for i in range(7):
                        st.session_state[f'run_{i}_wzn_all_kind'] = True
                    st.session_state["run_init_wzn_all_kind"] = True

                def sync_all_to_individual_wzn_all_kind():
                    all_selected = st.session_state["run_all_wzn_all_kind"]
                    for i in range(7):
                        st.session_state[f'run_{i}_wzn_all_kind'] = all_selected

                def sync_individual_to_all_wzn_all_kind():
                    all_selected = all(st.session_state[f'run_{i}_wzn_all_kind'] for i in range(7))
                    st.session_state["run_all_wzn_all_kind"] = all_selected

                st.checkbox("All", key="run_all_wzn_all_kind", on_change=sync_all_to_individual_wzn_all_kind)
                for i in range(7):
                    st.checkbox(str(i), key=f'run_{i}_wzn_all_kind', on_change=sync_individual_to_all_wzn_all_kind)

                individual_selected_wzn_all_kind = [i for i in range(7) if st.session_state.get(f'run_{i}_wzn_all_kind', False)]
                if st.session_state["run_all_wzn_all_kind"]:
                    filtered_runs_wzn_all_kind = None
                elif individual_selected_wzn_all_kind:
                    filtered_runs_wzn_all_kind = individual_selected_wzn_all_kind
                else:
                    filtered_runs_wzn_all_kind = []
                    
            if filtered_runs_wzn_all_kind == []:
                st.warning("Please select at least one run value to display the plot.")
            else:
                fig_wzn_all_kind = wagon_zone_plot_descriptive(
                    df=df,
                    player_name=selected_player_value,
                    pid=selected_pid,
                    inns=selected_inns,
                    mat_num=selected_mat_num,
                    team_bat=selected_team_value,
                    team_bowl=selected_team_bowl_value,
                    run_values=filtered_runs_wzn_all_kind,
                    bowler_name=bowler_name,
                    bowler_id=bowler_id,
                    competition=selected_competition_value,
                    transparent=False,
                    over_values=over_values,
                    phase=phase,
                    ground=selected_ground,
                    mcode=selected_mcode,
                    date_from=date_from,
                    date_to=date_to,
                    title_components=title_components if show_title_wzn_all_kind else [],
                    bat_hand=bat_hand,
                    bowl_type=bowl_type,
                    bowl_kind=None,
                    bowl_arm=bowl_arm,
                    show_title=show_title_wzn_all_kind,
                    show_summary=show_summary_wzn_all_kind,
                    show_shots_breakdown=show_shots_breakdown_wzn_all_kind,
                    shots_breakdown_options=shots_breakdown_options_wzn_all_kind,
                    runs_count=runs_count_wzn_all_kind,
                    show_fours_sixes=show_fours_sixes_wzn_all_kind,
                    show_control=show_control_wzn_all_kind,
                    show_prod_shot=show_prod_shot_wzn_all_kind,
                    show_bowler=show_bowler_wzn_all_kind,
                    show_venue=show_venue_wzn_all_kind,
                    show_overs=show_overs_wzn_all_kind,
                    show_phase=show_phase_wzn_all_kind,
                    show_bowl_type=show_bowl_type_wzn_all_kind,
                    show_bowl_kind=show_bowl_kind_wzn_all_kind,
                    show_bowl_arm=show_bowl_arm_wzn_all_kind
                )
                with col2:
                    st.pyplot(fig_wzn_all_kind)
            
            with col3:
                if fig_wzn_all_kind:
                    buf = BytesIO()
                    fig_wzn_all_kind.savefig(buf, format="png", transparent=False, dpi=300, bbox_inches='tight')
                    buf.seek(0)
                    st.download_button(
                        label="📅 Download Plot as PNG",
                        data=buf.getvalue(),
                        file_name=f"{selected_player}_wzn_all_kind.png",
                        mime="image/png",
                        key="wzn_all_kind_download"
                    )

        if "━━ Wagon Zone - RAP" in plot_types:
            st.markdown("<h2 style='text-align: center;'>Wagon Zone - Right Arm Pace</h2>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([2, 2, 2])
            
            with col1:
                st.markdown("## Customize Plot Info")
                show_title_wzn_rap = st.checkbox("Show Plot Title", value=True, key="wzn_rap_title")
                show_summary_wzn_rap = st.checkbox("Show Runs Summary", value=True, key="wzn_rap_summary")
                
                show_shots_breakdown_wzn_rap = st.checkbox("Show Shots Breakdown", value=True, key="wzn_rap_shots_breakdown")
                if show_shots_breakdown_wzn_rap:
                    shots_breakdown_options_wzn_rap = st.multiselect(
                        "Shots to Display",
                        options=['0s', '1s', '2s', '3s', '4s', '6s'],
                        default=['0s', '1s', '2s', '4s', '6s'],
                        key="wzn_rap_shots_options",
                        help="Select which run types to display in breakdown"
                    )
                else:
                    shots_breakdown_options_wzn_rap = []
                
                runs_count_wzn_rap = st.checkbox("Show Runs Count", value=True, key="wzn_rap_runs")
                show_fours_sixes_wzn_rap = st.checkbox("Show 4s and 6s", value=True, key="wzn_rap_fs")
                show_bowler_wzn_rap = st.checkbox("Show Bowler", value=True, key="wzn_rap_bowler")
                show_control_wzn_rap = st.checkbox("Show Control %", value=True, key="wzn_rap_control")
                show_prod_shot_wzn_rap = st.checkbox("Show Productive Shot", value=True, key="wzn_rap_prod")
                show_overs_wzn_rap = st.checkbox("Show Overs", value=True, key="wzn_rap_overs")
                show_phase_wzn_rap = st.checkbox("Show Phase", value=True, key="wzn_rap_phase")
                show_bowl_type_wzn_rap = st.checkbox("Show Bowl Type", value=True, key="wzn_rap_bowl_type")
                show_bowl_arm_wzn_rap = st.checkbox("Show Bowl Arm", value=True, key="wzn_rap_bowl_arm")
                show_venue_wzn_rap = st.checkbox("Show Venue", value=True, key="wzn_rap_venue")

            with col3:
                st.markdown("## Run Filter (Wagon Zone)")
                if "run_init_wzn_rap" not in st.session_state:
                    st.session_state["run_all_wzn_rap"] = True
                    for i in range(7):
                        st.session_state[f'run_{i}_wzn_rap'] = True
                    st.session_state["run_init_wzn_rap"] = True

                def sync_all_to_individual_wzn_rap():
                    all_selected = st.session_state["run_all_wzn_rap"]
                    for i in range(7):
                        st.session_state[f'run_{i}_wzn_rap'] = all_selected

                def sync_individual_to_all_wzn_rap():
                    all_selected = all(st.session_state[f'run_{i}_wzn_rap'] for i in range(7))
                    st.session_state["run_all_wzn_rap"] = all_selected

                st.checkbox("All", key="run_all_wzn_rap", on_change=sync_all_to_individual_wzn_rap)
                for i in range(7):
                    st.checkbox(str(i), key=f'run_{i}_wzn_rap', on_change=sync_individual_to_all_wzn_rap)

                individual_selected_wzn_rap = [i for i in range(7) if st.session_state.get(f'run_{i}_wzn_rap', False)]
                if st.session_state["run_all_wzn_rap"]:
                    filtered_runs_wzn_rap = None
                elif individual_selected_wzn_rap:
                    filtered_runs_wzn_rap = individual_selected_wzn_rap
                else:
                    filtered_runs_wzn_rap = []
                    
            if filtered_runs_wzn_rap == []:
                st.warning("Please select at least one run value to display the plot.")
            else:
                fig_wzn_rap = wagon_zone_plot_descriptive(
                    df=df,
                    player_name=selected_player_value,
                    pid=selected_pid,
                    inns=selected_inns,
                    mat_num=selected_mat_num,
                    team_bat=selected_team_value,
                    team_bowl=selected_team_bowl_value,
                    run_values=filtered_runs_wzn_rap,
                    bowler_name=bowler_name,
                    bowler_id=bowler_id,
                    competition=selected_competition_value,
                    transparent=False,
                    over_values=over_values,
                    phase=phase,
                    ground=selected_ground,
                    mcode=selected_mcode,
                    date_from=date_from,
                    date_to=date_to,
                    title_components=title_components if show_title_wzn_rap else [],
                    bat_hand=bat_hand,
                    bowl_type=["Right Arm Pace"],
                    bowl_kind=bowl_kind,
                    bowl_arm=bowl_arm,
                    show_title=show_title_wzn_rap,
                    show_summary=show_summary_wzn_rap,
                    show_shots_breakdown=show_shots_breakdown_wzn_rap,
                    shots_breakdown_options=shots_breakdown_options_wzn_rap,
                    runs_count=runs_count_wzn_rap,
                    show_fours_sixes=show_fours_sixes_wzn_rap,
                    show_control=show_control_wzn_rap,
                    show_prod_shot=show_prod_shot_wzn_rap,
                    show_bowler=show_bowler_wzn_rap,
                    show_venue=show_venue_wzn_rap,
                    show_overs=show_overs_wzn_rap,
                    show_phase=show_phase_wzn_rap,
                    show_bowl_type=show_bowl_type_wzn_rap,
                    show_bowl_arm=show_bowl_arm_wzn_rap
                )
                with col2:
                    st.pyplot(fig_wzn_rap)
            
            with col3:
                if fig_wzn_rap:
                    buf = BytesIO()
                    fig_wzn_rap.savefig(buf, format="png", transparent=False, dpi=300, bbox_inches='tight')
                    buf.seek(0)
                    st.download_button(
                        label="📅 Download Plot as PNG",
                        data=buf.getvalue(),
                        file_name=f"{selected_player}_wzn_rap.png",
                        mime="image/png",
                        key="wzn_rap_download"
                    )

        if "━━ Wagon Zone - RAFS" in plot_types:
            st.markdown("<h2 style='text-align: center;'>Wagon Zone - Right Arm Finger Spin</h2>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([2, 2, 2])
            
            with col1:
                st.markdown("## Customize Plot Info")
                show_title_wzn_rafs = st.checkbox("Show Plot Title", value=True, key="wzn_rafs_title")
                show_summary_wzn_rafs = st.checkbox("Show Runs Summary", value=True, key="wzn_rafs_summary")
                
                show_shots_breakdown_wzn_rafs = st.checkbox("Show Shots Breakdown", value=True, key="wzn_rafs_shots_breakdown")
                if show_shots_breakdown_wzn_rafs:
                    shots_breakdown_options_wzn_rafs = st.multiselect(
                        "Shots to Display",
                        options=['0s', '1s', '2s', '3s', '4s', '6s'],
                        default=['0s', '1s', '2s', '4s', '6s'],
                        key="wzn_rafs_shots_options",
                        help="Select which run types to display in breakdown"
                    )
                else:
                    shots_breakdown_options_wzn_rafs = []
                
                runs_count_wzn_rafs = st.checkbox("Show Runs Count", value=True, key="wzn_rafs_runs")
                show_fours_sixes_wzn_rafs = st.checkbox("Show 4s and 6s", value=True, key="wzn_rafs_fs")
                show_bowler_wzn_rafs = st.checkbox("Show Bowler", value=True, key="wzn_rafs_bowler")
                show_control_wzn_rafs = st.checkbox("Show Control %", value=True, key="wzn_rafs_control")
                show_prod_shot_wzn_rafs = st.checkbox("Show Productive Shot", value=True, key="wzn_rafs_prod")
                show_overs_wzn_rafs = st.checkbox("Show Overs", value=True, key="wzn_rafs_overs")
                show_phase_wzn_rafs = st.checkbox("Show Phase", value=True, key="wzn_rafs_phase")
                show_bowl_type_wzn_rafs = st.checkbox("Show Bowl Type", value=True, key="wzn_rafs_bowl_type")
                show_bowl_arm_wzn_rafs = st.checkbox("Show Bowl Arm", value=True, key="wzn_rafs_bowl_arm")
                show_venue_wzn_rafs = st.checkbox("Show Venue", value=True, key="wzn_rafs_venue")

            with col3:
                st.markdown("## Run Filter (Wagon Zone)")
                if "run_init_wzn_rafs" not in st.session_state:
                    st.session_state["run_all_wzn_rafs"] = True
                    for i in range(7):
                        st.session_state[f'run_{i}_wzn_rafs'] = True
                    st.session_state["run_init_wzn_rafs"] = True

                def sync_all_to_individual_wzn_rafs():
                    all_selected = st.session_state["run_all_wzn_rafs"]
                    for i in range(7):
                        st.session_state[f'run_{i}_wzn_rafs'] = all_selected

                def sync_individual_to_all_wzn_rafs():
                    all_selected = all(st.session_state[f'run_{i}_wzn_rafs'] for i in range(7))
                    st.session_state["run_all_wzn_rafs"] = all_selected

                st.checkbox("All", key="run_all_wzn_rafs", on_change=sync_all_to_individual_wzn_rafs)
                for i in range(7):
                    st.checkbox(str(i), key=f'run_{i}_wzn_rafs', on_change=sync_individual_to_all_wzn_rafs)

                individual_selected_wzn_rafs = [i for i in range(7) if st.session_state.get(f'run_{i}_wzn_rafs', False)]
                if st.session_state["run_all_wzn_rafs"]:
                    filtered_runs_wzn_rafs = None
                elif individual_selected_wzn_rafs:
                    filtered_runs_wzn_rafs = individual_selected_wzn_rafs
                else:
                    filtered_runs_wzn_rafs = []
                    
            if filtered_runs_wzn_rafs == []:
                st.warning("Please select at least one run value to display the plot.")
            else:
                fig_wzn_rafs = wagon_zone_plot_descriptive(
                    df=df,
                    player_name=selected_player_value,
                    pid=selected_pid,
                    inns=selected_inns,
                    mat_num=selected_mat_num,
                    team_bat=selected_team_value,
                    team_bowl=selected_team_bowl_value,
                    run_values=filtered_runs_wzn_rafs,
                    bowler_name=bowler_name,
                    bowler_id=bowler_id,
                    competition=selected_competition_value,
                    transparent=False,
                    over_values=over_values,
                    phase=phase,
                    ground=selected_ground,
                    mcode=selected_mcode,
                    date_from=date_from,
                    date_to=date_to,
                    title_components=title_components if show_title_wzn_rafs else [],
                    bat_hand=bat_hand,
                    bowl_type=["Right Arm Finger Spin"],
                    bowl_kind=bowl_kind,
                    bowl_arm=bowl_arm,
                    show_title=show_title_wzn_rafs,
                    show_summary=show_summary_wzn_rafs,
                    show_shots_breakdown=show_shots_breakdown_wzn_rafs,
                    shots_breakdown_options=shots_breakdown_options_wzn_rafs,
                    runs_count=runs_count_wzn_rafs,
                    show_fours_sixes=show_fours_sixes_wzn_rafs,
                    show_control=show_control_wzn_rafs,
                    show_prod_shot=show_prod_shot_wzn_rafs,
                    show_bowler=show_bowler_wzn_rafs,
                    show_venue=show_venue_wzn_rafs,
                    show_overs=show_overs_wzn_rafs,
                    show_phase=show_phase_wzn_rafs,
                    show_bowl_type=show_bowl_type_wzn_rafs,
                    show_bowl_arm=show_bowl_arm_wzn_rafs
                )
                with col2:
                    st.pyplot(fig_wzn_rafs)
            
            with col3:
                if fig_wzn_rafs:
                    buf = BytesIO()
                    fig_wzn_rafs.savefig(buf, format="png", transparent=False, dpi=300, bbox_inches='tight')
                    buf.seek(0)
                    st.download_button(
                        label="📅 Download Plot as PNG",
                        data=buf.getvalue(),
                        file_name=f"{selected_player}_wzn_rafs.png",
                        mime="image/png",
                        key="wzn_rafs_download"
                    )

        if "━━ Wagon Zone - RAWS" in plot_types:
            st.markdown("<h2 style='text-align: center;'>Wagon Zone - Right Arm Wrist Spin</h2>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([2, 2, 2])
            
            with col1:
                st.markdown("## Customize Plot Info")
                show_title_wzn_raws = st.checkbox("Show Plot Title", value=True, key="wzn_raws_title")
                show_summary_wzn_raws = st.checkbox("Show Runs Summary", value=True, key="wzn_raws_summary")
                
                show_shots_breakdown_wzn_raws = st.checkbox("Show Shots Breakdown", value=True, key="wzn_raws_shots_breakdown")
                if show_shots_breakdown_wzn_raws:
                    shots_breakdown_options_wzn_raws = st.multiselect(
                        "Shots to Display",
                        options=['0s', '1s', '2s', '3s', '4s', '6s'],
                        default=['0s', '1s', '2s', '4s', '6s'],
                        key="wzn_raws_shots_options",
                        help="Select which run types to display in breakdown"
                    )
                else:
                    shots_breakdown_options_wzn_raws = []
                
                runs_count_wzn_raws = st.checkbox("Show Runs Count", value=True, key="wzn_raws_runs")
                show_fours_sixes_wzn_raws = st.checkbox("Show 4s and 6s", value=True, key="wzn_raws_fs")
                show_bowler_wzn_raws = st.checkbox("Show Bowler", value=True, key="wzn_raws_bowler")
                show_control_wzn_raws = st.checkbox("Show Control %", value=True, key="wzn_raws_control")
                show_prod_shot_wzn_raws = st.checkbox("Show Productive Shot", value=True, key="wzn_raws_prod")
                show_overs_wzn_raws = st.checkbox("Show Overs", value=True, key="wzn_raws_overs")
                show_phase_wzn_raws = st.checkbox("Show Phase", value=True, key="wzn_raws_phase")
                show_bowl_type_wzn_raws = st.checkbox("Show Bowl Type", value=True, key="wzn_raws_bowl_type")
                show_bowl_arm_wzn_raws = st.checkbox("Show Bowl Arm", value=True, key="wzn_raws_bowl_arm")
                show_venue_wzn_raws = st.checkbox("Show Venue", value=True, key="wzn_raws_venue")

            with col3:
                st.markdown("## Run Filter (Wagon Zone)")
                if "run_init_wzn_raws" not in st.session_state:
                    st.session_state["run_all_wzn_raws"] = True
                    for i in range(7):
                        st.session_state[f'run_{i}_wzn_raws'] = True
                    st.session_state["run_init_wzn_raws"] = True

                def sync_all_to_individual_wzn_raws():
                    all_selected = st.session_state["run_all_wzn_raws"]
                    for i in range(7):
                        st.session_state[f'run_{i}_wzn_raws'] = all_selected

                def sync_individual_to_all_wzn_raws():
                    all_selected = all(st.session_state[f'run_{i}_wzn_raws'] for i in range(7))
                    st.session_state["run_all_wzn_raws"] = all_selected

                st.checkbox("All", key="run_all_wzn_raws", on_change=sync_all_to_individual_wzn_raws)
                for i in range(7):
                    st.checkbox(str(i), key=f'run_{i}_wzn_raws', on_change=sync_individual_to_all_wzn_raws)

                individual_selected_wzn_raws = [i for i in range(7) if st.session_state.get(f'run_{i}_wzn_raws', False)]
                if st.session_state["run_all_wzn_raws"]:
                    filtered_runs_wzn_raws = None
                elif individual_selected_wzn_raws:
                    filtered_runs_wzn_raws = individual_selected_wzn_raws
                else:
                    filtered_runs_wzn_raws = []
                    
            if filtered_runs_wzn_raws == []:
                st.warning("Please select at least one run value to display the plot.")
            else:
                fig_wzn_raws = wagon_zone_plot_descriptive(
                    df=df,
                    player_name=selected_player_value,
                    pid=selected_pid,
                    inns=selected_inns,
                    mat_num=selected_mat_num,
                    team_bat=selected_team_value,
                    team_bowl=selected_team_bowl_value,
                    run_values=filtered_runs_wzn_raws,
                    bowler_name=bowler_name,
                    bowler_id=bowler_id,
                    competition=selected_competition_value,
                    transparent=False,
                    over_values=over_values,
                    phase=phase,
                    ground=selected_ground,
                    mcode=selected_mcode,
                    date_from=date_from,
                    date_to=date_to,
                    title_components=title_components if show_title_wzn_raws else [],
                    bat_hand=bat_hand,
                    bowl_type=["Right Arm Wrist Spin"],
                    bowl_kind=bowl_kind,
                    bowl_arm=bowl_arm,
                    show_title=show_title_wzn_raws,
                    show_summary=show_summary_wzn_raws,
                    show_shots_breakdown=show_shots_breakdown_wzn_raws,
                    shots_breakdown_options=shots_breakdown_options_wzn_raws,
                    runs_count=runs_count_wzn_raws,
                    show_fours_sixes=show_fours_sixes_wzn_raws,
                    show_control=show_control_wzn_raws,
                    show_prod_shot=show_prod_shot_wzn_raws,
                    show_bowler=show_bowler_wzn_raws,
                    show_venue=show_venue_wzn_raws,
                    show_overs=show_overs_wzn_raws,
                    show_phase=show_phase_wzn_raws,
                    show_bowl_type=show_bowl_type_wzn_raws,
                    show_bowl_arm=show_bowl_arm_wzn_raws
                )
                with col2:
                    st.pyplot(fig_wzn_raws)
            
            with col3:
                if fig_wzn_raws:
                    buf = BytesIO()
                    fig_wzn_raws.savefig(buf, format="png", transparent=False, dpi=300, bbox_inches='tight')
                    buf.seek(0)
                    st.download_button(
                        label="📅 Download Plot as PNG",
                        data=buf.getvalue(),
                        file_name=f"{selected_player}_wzn_raws.png",
                        mime="image/png",
                        key="wzn_raws_download"
                    )

        if "━━ Wagon Zone - LAP" in plot_types:
            st.markdown("<h2 style='text-align: center;'>Wagon Zone - Left Arm Pace</h2>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([2, 2, 2])
            
            with col1:
                st.markdown("## Customize Plot Info")
                show_title_wzn_lap = st.checkbox("Show Plot Title", value=True, key="wzn_lap_title")
                show_summary_wzn_lap = st.checkbox("Show Runs Summary", value=True, key="wzn_lap_summary")
                runs_count_wzn_lap = st.checkbox("Show Runs Count", value=True, key="wzn_lap_runs")
                show_fours_sixes_wzn_lap = st.checkbox("Show 4s and 6s", value=True, key="wzn_lap_fs")
                show_bowler_wzn_lap = st.checkbox("Show Bowler", value=True, key="wzn_lap_bowler")
                show_control_wzn_lap = st.checkbox("Show Control %", value=True, key="wzn_lap_control")
                show_prod_shot_wzn_lap = st.checkbox("Show Productive Shot", value=True, key="wzn_lap_prod")
                show_overs_wzn_lap = st.checkbox("Show Overs", value=True, key="wzn_lap_overs")
                show_phase_wzn_lap = st.checkbox("Show Phase", value=True, key="wzn_lap_phase")
                show_bowl_type_wzn_lap = st.checkbox("Show Bowl Type", value=True, key="wzn_lap_bowl_type")
                show_venue_wzn_lap = st.checkbox("Show Venue", value=True, key="wzn_lap_venue")

            with col3:
                st.markdown("## Run Filter (Wagon Zone)")
                if "run_init_wzn_lap" not in st.session_state:
                    st.session_state["run_all_wzn_lap"] = True
                    for i in range(7):
                        st.session_state[f'run_{i}_wzn_lap'] = True
                    st.session_state["run_init_wzn_lap"] = True

                def sync_all_to_individual_wzn_lap():
                    all_selected = st.session_state["run_all_wzn_lap"]
                    for i in range(7):
                        st.session_state[f'run_{i}_wzn_lap'] = all_selected

                def sync_individual_to_all_wzn_lap():
                    all_selected = all(st.session_state[f'run_{i}_wzn_lap'] for i in range(7))
                    st.session_state["run_all_wzn_lap"] = all_selected

                st.checkbox("All", key="run_all_wzn_lap", on_change=sync_all_to_individual_wzn_lap)
                for i in range(7):
                    st.checkbox(str(i), key=f'run_{i}_wzn_lap', on_change=sync_individual_to_all_wzn_lap)

                individual_selected_wzn_lap = [i for i in range(7) if st.session_state.get(f'run_{i}_wzn_lap', False)]
                if st.session_state["run_all_wzn_lap"]:
                    filtered_runs_wzn_lap = None
                elif individual_selected_wzn_lap:
                    filtered_runs_wzn_lap = individual_selected_wzn_lap
                else:
                    filtered_runs_wzn_lap = []
                    
            if filtered_runs_wzn_lap == []:
                st.warning("Please select at least one run value to display the plot.")
            else:
                fig_wzn_lap = wagon_zone_plot_descriptive(
                    df=df,
                    player_name=selected_player_value,
                    pid=selected_pid,
                    inns=selected_inns,
                    mat_num=selected_mat_num,
                    team_bat=selected_team_value,
                    team_bowl=selected_team_bowl_value,
                    run_values=filtered_runs_wzn_lap,
                    bowler_name=bowler_name,
                    bowler_id=bowler_id,
                    competition=selected_competition_value,
                    transparent=False,
                    over_values=over_values,
                    phase=phase,
                    ground=selected_ground,
                    mcode=selected_mcode,
                    date_from=date_from,
                    date_to=date_to,
                    title_components=title_components if show_title_wzn_lap else [],
                    bat_hand=bat_hand,
                    bowl_type=["Left Arm Pace"],
                    bowl_kind=bowl_kind,
                    bowl_arm=bowl_arm,
                    show_title=show_title_wzn_lap,
                    show_summary=show_summary_wzn_lap,
                    runs_count=runs_count_wzn_lap,
                    show_fours_sixes=show_fours_sixes_wzn_lap,
                    show_control=show_control_wzn_lap,
                    show_prod_shot=show_prod_shot_wzn_lap,
                    show_bowler=show_bowler_wzn_lap,
                    show_venue=show_venue_wzn_lap,
                    show_overs=show_overs_wzn_lap,
                    show_phase=show_phase_wzn_lap,
                    show_bowl_type=show_bowl_type_wzn_lap
                )
                with col2:
                    st.pyplot(fig_wzn_lap)
            
            with col3:
                if fig_wzn_lap:
                    buf = BytesIO()
                    fig_wzn_lap.savefig(buf, format="png", transparent=False, dpi=300, bbox_inches='tight')
                    buf.seek(0)
                    st.download_button(
                        label="📅 Download Plot as PNG",
                        data=buf.getvalue(),
                        file_name=f"{selected_player}_wzn_lap.png",
                        mime="image/png",
                        key="wzn_lap_download"
                    )

        if "━━ Wagon Zone - LAFS" in plot_types:
            st.markdown("<h2 style='text-align: center;'>Wagon Zone - Left Arm Finger Spin</h2>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([2, 2, 2])
            
            with col1:
                st.markdown("## Customize Plot Info")
                show_title_wzn_lafs = st.checkbox("Show Plot Title", value=True, key="wzn_lafs_title")
                show_summary_wzn_lafs = st.checkbox("Show Runs Summary", value=True, key="wzn_lafs_summary")
                runs_count_wzn_lafs = st.checkbox("Show Runs Count", value=True, key="wzn_lafs_runs")
                show_fours_sixes_wzn_lafs = st.checkbox("Show 4s and 6s", value=True, key="wzn_lafs_fs")
                show_bowler_wzn_lafs = st.checkbox("Show Bowler", value=True, key="wzn_lafs_bowler")
                show_control_wzn_lafs = st.checkbox("Show Control %", value=True, key="wzn_lafs_control")
                show_prod_shot_wzn_lafs = st.checkbox("Show Productive Shot", value=True, key="wzn_lafs_prod")
                show_overs_wzn_lafs = st.checkbox("Show Overs", value=True, key="wzn_lafs_overs")
                show_phase_wzn_lafs = st.checkbox("Show Phase", value=True, key="wzn_lafs_phase")
                show_bowl_type_wzn_lafs = st.checkbox("Show Bowl Type", value=True, key="wzn_lafs_bowl_type")
                show_venue_wzn_lafs = st.checkbox("Show Venue", value=True, key="wzn_lafs_venue")

            with col3:
                st.markdown("## Run Filter (Wagon Zone)")
                if "run_init_wzn_lafs" not in st.session_state:
                    st.session_state["run_all_wzn_lafs"] = True
                    for i in range(7):
                        st.session_state[f'run_{i}_wzn_lafs'] = True
                    st.session_state["run_init_wzn_lafs"] = True

                def sync_all_to_individual_wzn_lafs():
                    all_selected = st.session_state["run_all_wzn_lafs"]
                    for i in range(7):
                        st.session_state[f'run_{i}_wzn_lafs'] = all_selected

                def sync_individual_to_all_wzn_lafs():
                    all_selected = all(st.session_state[f'run_{i}_wzn_lafs'] for i in range(7))
                    st.session_state["run_all_wzn_lafs"] = all_selected

                st.checkbox("All", key="run_all_wzn_lafs", on_change=sync_all_to_individual_wzn_lafs)
                for i in range(7):
                    st.checkbox(str(i), key=f'run_{i}_wzn_lafs', on_change=sync_individual_to_all_wzn_lafs)

                individual_selected_wzn_lafs = [i for i in range(7) if st.session_state.get(f'run_{i}_wzn_lafs', False)]
                if st.session_state["run_all_wzn_lafs"]:
                    filtered_runs_wzn_lafs = None
                elif individual_selected_wzn_lafs:
                    filtered_runs_wzn_lafs = individual_selected_wzn_lafs
                else:
                    filtered_runs_wzn_lafs = []
                    
            if filtered_runs_wzn_lafs == []:
                st.warning("Please select at least one run value to display the plot.")
            else:
                fig_wzn_lafs = wagon_zone_plot_descriptive(
                    df=df,
                    player_name=selected_player_value,
                    pid=selected_pid,
                    inns=selected_inns,
                    mat_num=selected_mat_num,
                    team_bat=selected_team_value,
                    team_bowl=selected_team_bowl_value,
                    run_values=filtered_runs_wzn_lafs,
                    bowler_name=bowler_name,
                    bowler_id=bowler_id,
                    competition=selected_competition_value,
                    transparent=False,
                    over_values=over_values,
                    phase=phase,
                    ground=selected_ground,
                    mcode=selected_mcode,
                    date_from=date_from,
                    date_to=date_to,
                    title_components=title_components if show_title_wzn_lafs else [],
                    bat_hand=bat_hand,
                    bowl_type=["Left Arm Figner Spin"],
                    bowl_kind=bowl_kind,
                    bowl_arm=bowl_arm,
                    show_title=show_title_wzn_lafs,
                    show_summary=show_summary_wzn_lafs,
                    runs_count=runs_count_wzn_lafs,
                    show_fours_sixes=show_fours_sixes_wzn_lafs,
                    show_control=show_control_wzn_lafs,
                    show_prod_shot=show_prod_shot_wzn_lafs,
                    show_bowler=show_bowler_wzn_lafs,
                    show_venue=show_venue_wzn_lafs,
                    show_overs=show_overs_wzn_lafs,
                    show_phase=show_phase_wzn_lafs,
                    show_bowl_type=show_bowl_type_wzn_lafs
                )
                with col2:
                    st.pyplot(fig_wzn_lafs)
            
            with col3:
                if fig_wzn_lafs:
                    buf = BytesIO()
                    fig_wzn_lafs.savefig(buf, format="png", transparent=False, dpi=300, bbox_inches='tight')
                    buf.seek(0)
                    st.download_button(
                        label="📅 Download Plot as PNG",
                        data=buf.getvalue(),
                        file_name=f"{selected_player}_wzn_lafs.png",
                        mime="image/png",
                        key="wzn_lafs_download"
                    )

        if "━━ Wagon Zone - LAWS" in plot_types:
            st.markdown("<h2 style='text-align: center;'>Wagon Zone - Left Arm Wrist Spin</h2>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([2, 2, 2])
            
            with col1:
                st.markdown("## Customize Plot Info")
                show_title_wzn_laws = st.checkbox("Show Plot Title", value=True, key="wzn_laws_title")
                show_summary_wzn_laws = st.checkbox("Show Runs Summary", value=True, key="wzn_laws_summary")
                runs_count_wzn_laws = st.checkbox("Show Runs Count", value=True, key="wzn_laws_runs")
                show_fours_sixes_wzn_laws = st.checkbox("Show 4s and 6s", value=True, key="wzn_laws_fs")
                show_bowler_wzn_laws = st.checkbox("Show Bowler", value=True, key="wzn_laws_bowler")
                show_control_wzn_laws = st.checkbox("Show Control %", value=True, key="wzn_laws_control")
                show_prod_shot_wzn_laws = st.checkbox("Show Productive Shot", value=True, key="wzn_laws_prod")
                show_overs_wzn_laws = st.checkbox("Show Overs", value=True, key="wzn_laws_overs")
                show_phase_wzn_laws = st.checkbox("Show Phase", value=True, key="wzn_laws_phase")
                show_bowl_type_wzn_laws = st.checkbox("Show Bowl Type", value=True, key="wzn_laws_bowl_type")
                show_venue_wzn_laws = st.checkbox("Show Venue", value=True, key="wzn_laws_venue")

            with col3:
                st.markdown("## Run Filter (Wagon Zone)")
                if "run_init_wzn_laws" not in st.session_state:
                    st.session_state["run_all_wzn_laws"] = True
                    for i in range(7):
                        st.session_state[f'run_{i}_wzn_laws'] = True
                    st.session_state["run_init_wzn_laws"] = True

                def sync_all_to_individual_wzn_laws():
                    all_selected = st.session_state["run_all_wzn_laws"]
                    for i in range(7):
                        st.session_state[f'run_{i}_wzn_laws'] = all_selected

                def sync_individual_to_all_wzn_laws():
                    all_selected = all(st.session_state[f'run_{i}_wzn_laws'] for i in range(7))
                    st.session_state["run_all_wzn_laws"] = all_selected

                st.checkbox("All", key="run_all_wzn_laws", on_change=sync_all_to_individual_wzn_laws)
                for i in range(7):
                    st.checkbox(str(i), key=f'run_{i}_wzn_laws', on_change=sync_individual_to_all_wzn_laws)

                individual_selected_wzn_laws = [i for i in range(7) if st.session_state.get(f'run_{i}_wzn_laws', False)]
                if st.session_state["run_all_wzn_laws"]:
                    filtered_runs_wzn_laws = None
                elif individual_selected_wzn_laws:
                    filtered_runs_wzn_laws = individual_selected_wzn_laws
                else:
                    filtered_runs_wzn_laws = []
                    
            if filtered_runs_wzn_laws == []:
                st.warning("Please select at least one run value to display the plot.")
            else:
                fig_wzn_laws = wagon_zone_plot_descriptive(
                    df=df,
                    player_name=selected_player_value,
                    pid=selected_pid,
                    inns=selected_inns,
                    mat_num=selected_mat_num,
                    team_bat=selected_team_value,
                    team_bowl=selected_team_bowl_value,
                    run_values=filtered_runs_wzn_laws,
                    bowler_name=bowler_name,
                    bowler_id=bowler_id,
                    competition=selected_competition_value,
                    transparent=False,
                    over_values=over_values,
                    phase=phase,
                    ground=selected_ground,
                    mcode=selected_mcode,
                    date_from=date_from,
                    date_to=date_to,
                    title_components=title_components if show_title_wzn_laws else [],
                    bat_hand=bat_hand,
                    bowl_type=["Left Arm Wrist Spin"],
                    bowl_kind=bowl_kind,
                    bowl_arm=bowl_arm,
                    show_title=show_title_wzn_laws,
                    show_summary=show_summary_wzn_laws,
                    runs_count=runs_count_wzn_laws,
                    show_fours_sixes=show_fours_sixes_wzn_laws,
                    show_control=show_control_wzn_laws,
                    show_prod_shot=show_prod_shot_wzn_laws,
                    show_bowler=show_bowler_wzn_laws,
                    show_venue=show_venue_wzn_laws,
                    show_overs=show_overs_wzn_laws,
                    show_phase=show_phase_wzn_laws,
                    show_bowl_type=show_bowl_type_wzn_laws
                )
                with col2:
                    st.pyplot(fig_wzn_laws)
            
            with col3:
                if fig_wzn_laws:
                    buf = BytesIO()
                    fig_wzn_laws.savefig(buf, format="png", transparent=False, dpi=300, bbox_inches='tight')
                    buf.seek(0)
                    st.download_button(
                        label="📅 Download Plot as PNG",
                        data=buf.getvalue(),
                        file_name=f"{selected_player}_wzn_laws.png",
                        mime="image/png",
                        key="wzn_laws_download"
                    )

        if "━━ Wagon Zone - All Arm" in plot_types:
            st.markdown("<h2 style='text-align: center;'>Wagon Zone - All Bowler Arm</h2>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([2, 2, 2])
            
            with col1:
                st.markdown("## Customize Plot Info")
                show_title_wzn_all_arm = st.checkbox("Show Plot Title", value=True, key="wzn_all_arm_title")
                show_summary_wzn_all_arm = st.checkbox("Show Runs Summary", value=True, key="wzn_all_arm_summary")
                runs_count_wzn_all_arm = st.checkbox("Show Runs Count", value=True, key="wzn_all_arm_runs")
                show_fours_sixes_wzn_all_arm = st.checkbox("Show 4s and 6s", value=True, key="wzn_all_arm_fs")
                show_bowler_wzn_all_arm = st.checkbox("Show Bowler", value=True, key="wzn_all_arm_bowler")
                show_control_wzn_all_arm = st.checkbox("Show Control %", value=True, key="wzn_all_arm_control")
                show_prod_shot_wzn_all_arm = st.checkbox("Show Productive Shot", value=True, key="wzn_all_arm_prod")
                show_overs_wzn_all_arm = st.checkbox("Show Overs", value=True, key="wzn_all_arm_overs")
                show_phase_wzn_all_arm = st.checkbox("Show Phase", value=True, key="wzn_all_arm_phase")
                show_venue_wzn_all_arm = st.checkbox("Show Venue", value=True, key="wzn_all_arm_venue")

            with col3:
                st.markdown("## Run Filter (Wagon Zone)")
                if "run_init_wzn_all_arm" not in st.session_state:
                    st.session_state["run_all_wzn_all_arm"] = True
                    for i in range(7):
                        st.session_state[f'run_{i}_wzn_all_arm'] = True
                    st.session_state["run_init_wzn_all_arm"] = True

                def sync_all_to_individual_wzn_all_arm():
                    all_selected = st.session_state["run_all_wzn_all_arm"]
                    for i in range(7):
                        st.session_state[f'run_{i}_wzn_all_arm'] = all_selected

                def sync_individual_to_all_wzn_all_arm():
                    all_selected = all(st.session_state[f'run_{i}_wzn_all_arm'] for i in range(7))
                    st.session_state["run_all_wzn_all_arm"] = all_selected

                st.checkbox("All", key="run_all_wzn_all_arm", on_change=sync_all_to_individual_wzn_all_arm)
                for i in range(7):
                    st.checkbox(str(i), key=f'run_{i}_wzn_all_arm', on_change=sync_individual_to_all_wzn_all_arm)

                individual_selected_wzn_all_arm = [i for i in range(7) if st.session_state.get(f'run_{i}_wzn_all_arm', False)]
                if st.session_state["run_all_wzn_all_arm"]:
                    filtered_runs_wzn_all_arm = None
                elif individual_selected_wzn_all_arm:
                    filtered_runs_wzn_all_arm = individual_selected_wzn_all_arm
                else:
                    filtered_runs_wzn_all_arm = []
                    
            if filtered_runs_wzn_all_arm == []:
                st.warning("Please select at least one run value to display the plot.")
            else:
                fig_wzn_all_arm = wagon_zone_plot_descriptive(
                    df=df,
                    player_name=selected_player_value,
                    pid=selected_pid,
                    inns=selected_inns,
                    mat_num=selected_mat_num,
                    team_bat=selected_team_value,
                    team_bowl=selected_team_bowl_value,
                    run_values=filtered_runs_wzn_all_arm,
                    bowler_name=bowler_name,
                    bowler_id=bowler_id,
                    competition=selected_competition_value,
                    transparent=False,
                    over_values=over_values,
                    phase=phase,
                    ground=selected_ground,
                    mcode=selected_mcode,
                    date_from=date_from,
                    date_to=date_to,
                    title_components=title_components if show_title_wzn_all_arm else [],
                    bat_hand=bat_hand,
                    bowl_type=bowl_type,
                    bowl_kind=bowl_kind,
                    bowl_arm=None,
                    show_title=show_title_wzn_all_arm,
                    show_summary=show_summary_wzn_all_arm,
                    runs_count=runs_count_wzn_all_arm,
                    show_fours_sixes=show_fours_sixes_wzn_all_arm,
                    show_control=show_control_wzn_all_arm,
                    show_prod_shot=show_prod_shot_wzn_all_arm,
                    show_bowler=show_bowler_wzn_all_arm,
                    show_venue=show_venue_wzn_all_arm,
                    show_overs=show_overs_wzn_all_arm,
                    show_phase=show_phase_wzn_all_arm
                )
                with col2:
                    st.pyplot(fig_wzn_all_arm)
            
            with col3:
                if fig_wzn_all_arm:
                    buf = BytesIO()
                    fig_wzn_all_arm.savefig(buf, format="png", transparent=False, dpi=300, bbox_inches='tight')
                    buf.seek(0)
                    st.download_button(
                        label="📅 Download Plot as PNG",
                        data=buf.getvalue(),
                        file_name=f"{selected_player}_wzn_all_arm.png",
                        mime="image/png",
                        key="wzn_all_arm_download"
                    )

        if "━━ Wagon Zone - Right Arm" in plot_types:
            st.markdown("<h2 style='text-align: center;'>Wagon Zone - Right Arm</h2>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([2, 2, 2])
            
            with col1:
                st.markdown("## Customize Plot Info")
                show_title_wzn_right_arm = st.checkbox("Show Plot Title", value=True, key="wzn_right_arm_title")
                show_summary_wzn_right_arm = st.checkbox("Show Runs Summary", value=True, key="wzn_right_arm_summary")
                runs_count_wzn_right_arm = st.checkbox("Show Runs Count", value=True, key="wzn_right_arm_runs")
                show_fours_sixes_wzn_right_arm = st.checkbox("Show 4s and 6s", value=True, key="wzn_right_arm_fs")
                show_bowler_wzn_right_arm = st.checkbox("Show Bowler", value=True, key="wzn_right_arm_bowler")
                show_control_wzn_right_arm = st.checkbox("Show Control %", value=True, key="wzn_right_arm_control")
                show_prod_shot_wzn_right_arm = st.checkbox("Show Productive Shot", value=True, key="wzn_right_arm_prod")
                show_overs_wzn_right_arm = st.checkbox("Show Overs", value=True, key="wzn_right_arm_overs")
                show_phase_wzn_right_arm = st.checkbox("Show Phase", value=True, key="wzn_right_arm_phase")
                show_venue_wzn_right_arm = st.checkbox("Show Venue", value=True, key="wzn_right_arm_venue")

            with col3:
                st.markdown("## Run Filter (Wagon Zone)")
                if "run_init_wzn_right_arm" not in st.session_state:
                    st.session_state["run_all_wzn_right_arm"] = True
                    for i in range(7):
                        st.session_state[f'run_{i}_wzn_right_arm'] = True
                    st.session_state["run_init_wzn_right_arm"] = True

                def sync_all_to_individual_wzn_right_arm():
                    all_selected = st.session_state["run_all_wzn_right_arm"]
                    for i in range(7):
                        st.session_state[f'run_{i}_wzn_right_arm'] = all_selected

                def sync_individual_to_all_wzn_right_arm():
                    all_selected = all(st.session_state[f'run_{i}_wzn_right_arm'] for i in range(7))
                    st.session_state["run_all_wzn_right_arm"] = all_selected

                st.checkbox("All", key="run_all_wzn_right_arm", on_change=sync_all_to_individual_wzn_right_arm)
                for i in range(7):
                    st.checkbox(str(i), key=f'run_{i}_wzn_right_arm', on_change=sync_individual_to_all_wzn_right_arm)

                individual_selected_wzn_right_arm = [i for i in range(7) if st.session_state.get(f'run_{i}_wzn_right_arm', False)]
                if st.session_state["run_all_wzn_right_arm"]:
                    filtered_runs_wzn_right_arm = None
                elif individual_selected_wzn_right_arm:
                    filtered_runs_wzn_right_arm = individual_selected_wzn_right_arm
                else:
                    filtered_runs_wzn_right_arm = []
                    
            if filtered_runs_wzn_right_arm == []:
                st.warning("Please select at least one run value to display the plot.")
            else:
                fig_wzn_right_arm = wagon_zone_plot_descriptive(
                    df=df,
                    player_name=selected_player_value,
                    pid=selected_pid,
                    inns=selected_inns,
                    mat_num=selected_mat_num,
                    team_bat=selected_team_value,
                    team_bowl=selected_team_bowl_value,
                    run_values=filtered_runs_wzn_right_arm,
                    bowler_name=bowler_name,
                    bowler_id=bowler_id,
                    competition=selected_competition_value,
                    transparent=False,
                    over_values=over_values,
                    phase=phase,
                    ground=selected_ground,
                    mcode=selected_mcode,
                    date_from=date_from,
                    date_to=date_to,
                    title_components=title_components if show_title_wzn_right_arm else [],
                    bat_hand=bat_hand,
                    bowl_type=bowl_type,
                    bowl_kind=bowl_kind,
                    bowl_arm=["Right Arm"],
                    show_title=show_title_wzn_right_arm,
                    show_summary=show_summary_wzn_right_arm,
                    runs_count=runs_count_wzn_right_arm,
                    show_fours_sixes=show_fours_sixes_wzn_right_arm,
                    show_control=show_control_wzn_right_arm,
                    show_prod_shot=show_prod_shot_wzn_right_arm,
                    show_bowler=show_bowler_wzn_right_arm,
                    show_venue=show_venue_wzn_right_arm,
                    show_overs=show_overs_wzn_right_arm,
                    show_phase=show_phase_wzn_right_arm
                )
                with col2:
                    st.pyplot(fig_wzn_right_arm)
            
            with col3:
                if fig_wzn_right_arm:
                    buf = BytesIO()
                    fig_wzn_right_arm.savefig(buf, format="png", transparent=False, dpi=300, bbox_inches='tight')
                    buf.seek(0)
                    st.download_button(
                        label="📅 Download Plot as PNG",
                        data=buf.getvalue(),
                        file_name=f"{selected_player}_wzn_right_arm.png",
                        mime="image/png",
                        key="wzn_right_arm_download"
                    )

        if "━━ Wagon Zone - Left Arm" in plot_types:
            st.markdown("<h2 style='text-align: center;'>Wagon Zone - Left Arm</h2>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([2, 2, 2])
            
            with col1:
                st.markdown("## Customize Plot Info")
                show_title_wzn_left_arm = st.checkbox("Show Plot Title", value=True, key="wzn_left_arm_title")
                show_summary_wzn_left_arm = st.checkbox("Show Runs Summary", value=True, key="wzn_left_arm_summary")
                runs_count_wzn_left_arm = st.checkbox("Show Runs Count", value=True, key="wzn_left_arm_runs")
                show_fours_sixes_wzn_left_arm = st.checkbox("Show 4s and 6s", value=True, key="wzn_left_arm_fs")
                show_bowler_wzn_left_arm = st.checkbox("Show Bowler", value=True, key="wzn_left_arm_bowler")
                show_control_wzn_left_arm = st.checkbox("Show Control %", value=True, key="wzn_left_arm_control")
                show_prod_shot_wzn_left_arm = st.checkbox("Show Productive Shot", value=True, key="wzn_left_arm_prod")
                show_overs_wzn_left_arm = st.checkbox("Show Overs", value=True, key="wzn_left_arm_overs")
                show_phase_wzn_left_arm = st.checkbox("Show Phase", value=True, key="wzn_left_arm_phase")
                show_venue_wzn_left_arm = st.checkbox("Show Venue", value=True, key="wzn_left_arm_venue")

            with col3:
                st.markdown("## Run Filter (Wagon Zone)")
                if "run_init_wzn_left_arm" not in st.session_state:
                    st.session_state["run_all_wzn_left_arm"] = True
                    for i in range(7):
                        st.session_state[f'run_{i}_wzn_left_arm'] = True
                    st.session_state["run_init_wzn_left_arm"] = True

                def sync_all_to_individual_wzn_left_arm():
                    all_selected = st.session_state["run_all_wzn_left_arm"]
                    for i in range(7):
                        st.session_state[f'run_{i}_wzn_left_arm'] = all_selected

                def sync_individual_to_all_wzn_left_arm():
                    all_selected = all(st.session_state[f'run_{i}_wzn_left_arm'] for i in range(7))
                    st.session_state["run_all_wzn_left_arm"] = all_selected

                st.checkbox("All", key="run_all_wzn_left_arm", on_change=sync_all_to_individual_wzn_left_arm)
                for i in range(7):
                    st.checkbox(str(i), key=f'run_{i}_wzn_left_arm', on_change=sync_individual_to_all_wzn_left_arm)

                individual_selected_wzn_left_arm = [i for i in range(7) if st.session_state.get(f'run_{i}_wzn_left_arm', False)]
                if st.session_state["run_all_wzn_left_arm"]:
                    filtered_runs_wzn_left_arm = None
                elif individual_selected_wzn_left_arm:
                    filtered_runs_wzn_left_arm = individual_selected_wzn_left_arm
                else:
                    filtered_runs_wzn_left_arm = []
                    
            if filtered_runs_wzn_left_arm == []:
                st.warning("Please select at least one run value to display the plot.")
            else:
                fig_wzn_left_arm = wagon_zone_plot_descriptive(
                    df=df,
                    player_name=selected_player_value,
                    pid=selected_pid,
                    inns=selected_inns,
                    mat_num=selected_mat_num,
                    team_bat=selected_team_value,
                    team_bowl=selected_team_bowl_value,
                    run_values=filtered_runs_wzn_left_arm,
                    bowler_name=bowler_name,
                    bowler_id=bowler_id,
                    competition=selected_competition_value,
                    transparent=False,
                    over_values=over_values,
                    phase=phase,
                    ground=selected_ground,
                    mcode=selected_mcode,
                    date_from=date_from,
                    date_to=date_to,
                    title_components=title_components if show_title_wzn_left_arm else [],
                    bat_hand=bat_hand,
                    bowl_type=bowl_type,
                    bowl_kind=bowl_kind,
                    bowl_arm=["Left Arm"],
                    show_title=show_title_wzn_left_arm,
                    show_summary=show_summary_wzn_left_arm,
                    runs_count=runs_count_wzn_left_arm,
                    show_fours_sixes=show_fours_sixes_wzn_left_arm,
                    show_control=show_control_wzn_left_arm,
                    show_prod_shot=show_prod_shot_wzn_left_arm,
                    show_bowler=show_bowler_wzn_left_arm,
                    show_venue=show_venue_wzn_left_arm,
                    show_overs=show_overs_wzn_left_arm,
                    show_phase=show_phase_wzn_left_arm
                )
                with col2:
                    st.pyplot(fig_wzn_left_arm)
            
            with col3:
                if fig_wzn_left_arm:
                    buf = BytesIO()
                    fig_wzn_left_arm.savefig(buf, format="png", transparent=False, dpi=300, bbox_inches='tight')
                    buf.seek(0)
                    st.download_button(
                        label="📅 Download Plot as PNG",
                        data=buf.getvalue(),
                        file_name=f"{selected_player}_wzn_left_arm.png",
                        mime="image/png",
                        key="wzn_left_arm_download"
                    )

        if "Dismissal Plot" in plot_types:
            st.markdown("<h2 style='text-align: center;'>Dismissal Plot</h2>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([2, 2, 2])
            
            with col1:
                show_title_dismissal = st.checkbox("Show Title", value=True, key="title_dismissal")
                show_summary_dismissal = st.checkbox("Show Summary", value=True, key="summary_dismissal")
                
                # Shots Breakdown checkbox and multiselect
                show_shots_breakdown_dismissal = st.checkbox("Show Shots Breakdown", value=True, key="shots_breakdown_dismissal")
                
                if show_shots_breakdown_dismissal:
                    shots_breakdown_options_dismissal = st.multiselect(
                        "Select Runs to Show",
                        options=['0s', '1s', '2s', '3s', '4s', '6s'],
                        default=['0s', '1s', '2s', '4s', '6s'],
                        key="shots_options_dismissal"
                    )
                else:
                    shots_breakdown_options_dismissal = []

            with col3:
                show_bowler_dismissal = st.checkbox("Show Bowler", value=True, key="bowler_dismissal")
                show_ground_dismissal = st.checkbox("Show Ground", value=True, key="ground_dismissal")
                show_control_dismissal = st.checkbox("Show Control %", value=True, key="control_dismissal")
                show_prod_shot_dismissal = st.checkbox("Show Most Loose Shot", value=True, key="prod_shot_dismissal")
                show_overs_dismissal = st.checkbox("Show Overs", value=True, key="overs_dismissal")
                show_phase_dismissal = st.checkbox("Show Phase", value=True, key="phase_dismissal")
                show_venue_dismissal = st.checkbox("Show Venue", value=True, key="venue_dismissal")
                # # Auto-enable show_venue if 'show_venue' is selected in title_components
                # show_venue_default = 'show_venue' in title_components
                # show_venue_dismissal = st.checkbox("Show Venue", value=show_venue_default, key="venue_dismissal")
                show_bowl_type_dismissal = st.checkbox("Show Bowl Type", value=True, key="bowl_type_dismissal")
                show_bowl_kind_dismissal = st.checkbox("Show Bowl Pace", value=True, key="bowl_kind_dismissal")
                show_bowl_arm_dismissal = st.checkbox("Show Bowl Arm", value=True, key="bowl_arm_dismissal")

            try:
                fig_dismissal = dismissal_plot(
                    df, 
                    player_name=selected_player_value, 
                    pid=selected_pid,
                    mat_num=selected_mat_num,
                    inns=selected_inns,
                    team_bat=selected_team_value,
                    team_bowl=selected_team_bowl_value,
                    bowler_name=bowler_name,
                    bowler_id=bowler_id,
                    competition=selected_competition_value,
                    date_from=date_from,
                    date_to=date_to,
                    transparent=False,
                    over_values=over_values,
                    phase=phase,
                    ground=selected_ground,
                    mcode=selected_mcode,
                    title_components=title_components,
                    shots_breakdown_options=shots_breakdown_options_dismissal,
                    bat_hand=bat_hand,
                    bowl_type=bowl_type,
                    bowl_kind=bowl_kind,
                    bowl_arm=bowl_arm,
                    show_title=show_title_dismissal,
                    show_summary=show_summary_dismissal,
                    show_shots_breakdown=show_shots_breakdown_dismissal,
                    show_fours_sixes=False,
                    show_control=show_control_dismissal,
                    show_prod_shot=show_prod_shot_dismissal,
                    runs_count=False,
                    show_bowler=show_bowler_dismissal,
                    show_ground=show_ground_dismissal,
                    show_venue=show_venue_dismissal,
                    show_overs=show_overs_dismissal,
                    show_phase=show_phase_dismissal,
                    show_bowl_type=show_bowl_type_dismissal,
                    show_bowl_kind=show_bowl_kind_dismissal,
                    show_bowl_arm=show_bowl_arm_dismissal
                )
            except Exception as e:
                st.error(f"Error generating dismissal plot: {str(e)}")
                fig_dismissal = None
            
            with col2:
                if fig_dismissal:
                    st.pyplot(fig_dismissal)
            
            with col3:
                if fig_dismissal:
                    buf = BytesIO()
                    fig_dismissal.savefig(buf, format='png', dpi=300, bbox_inches='tight')
                    buf.seek(0)
                    st.download_button(
                        label="📅 Download Plot as PNG",
                        data=buf.getvalue(),
                        file_name=f"{selected_player}_dismissal_plot.png",
                        mime="image/png",
                        key="dismissal_download"
                    )

        if "Dismissal Plot (Trans)" in plot_types:
            st.markdown("<h2 style='text-align: center;'>Dismissal Plot (Transparent Background)</h2>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([2, 2, 2])
            
            with col1:
                show_title_dismissal_trans = st.checkbox("Show Title", value=True, key="title_dismissal_trans")
                show_summary_dismissal_trans = st.checkbox("Show Summary", value=True, key="summary_dismissal_trans")
                
                # Shots Breakdown checkbox and multiselect
                show_shots_breakdown_dismissal_trans = st.checkbox("Show Shots Breakdown", value=True, key="shots_breakdown_dismissal_trans")
                
                if show_shots_breakdown_dismissal_trans:
                    shots_breakdown_options_dismissal_trans = st.multiselect(
                        "Select Runs to Show",
                        options=['0s', '1s', '2s', '3s', '4s', '6s'],
                        default=['0s', '1s', '2s', '4s', '6s'],
                        key="shots_options_dismissal_trans"
                    )
                else:
                    shots_breakdown_options_dismissal_trans = []

            with col3:
                show_bowler_dismissal_trans = st.checkbox("Show Bowler", value=True, key="bowler_dismissal_trans")
                show_ground_dismissal_trans = st.checkbox("Show Ground", value=False, key="ground_dismissal_trans")
                show_control_dismissal_trans = st.checkbox("Show Control %", value=True, key="control_dismissal_trans")
                show_prod_shot_dismissal_trans = st.checkbox("Show Most Loose Shot", value=True, key="prod_shot_dismissal_trans")
                show_overs_dismissal_trans = st.checkbox("Show Overs", value=True, key="overs_dismissal_trans")
                show_phase_dismissal_trans = st.checkbox("Show Phase", value=True, key="phase_dismissal_trans")
                show_venue_dismissal_trans = st.checkbox("Show Venue", value=True, key="venue_dismissal_trans")
                show_bowl_type_dismissal_trans = st.checkbox("Show Bowl Type", value=True, key="bowl_type_dismissal_trans")
                show_bowl_kind_dismissal_trans = st.checkbox("Show Bowl Pace", value=True, key="bowl_kind_dismissal_trans")
                show_bowl_arm_dismissal_trans = st.checkbox("Show Bowl Arm", value=True, key="bowl_arm_dismissal_trans")

            try:
                fig_dismissal_trans = dismissal_plot(
                    df, 
                    player_name=selected_player_value, 
                    pid=selected_pid,
                    mat_num=selected_mat_num,
                    inns=selected_inns,
                    team_bat=selected_team_value,
                    team_bowl=selected_team_bowl_value,
                    bowler_name=bowler_name,
                    bowler_id=bowler_id,
                    competition=selected_competition_value,
                    date_from=date_from,
                    date_to=date_to,
                    transparent=True,
                    over_values=over_values,
                    phase=phase,
                    ground=selected_ground,
                    mcode=selected_mcode,
                    title_components=title_components,
                    shots_breakdown_options=shots_breakdown_options_dismissal_trans,
                    bat_hand=bat_hand,
                    bowl_type=bowl_type,
                    bowl_kind=bowl_kind,
                    bowl_arm=bowl_arm,
                    show_title=show_title_dismissal_trans,
                    show_summary=show_summary_dismissal_trans,
                    show_shots_breakdown=show_shots_breakdown_dismissal_trans,
                    show_fours_sixes=False,
                    show_control=show_control_dismissal_trans,
                    show_prod_shot=show_prod_shot_dismissal_trans,
                    runs_count=False,
                    show_bowler=show_bowler_dismissal_trans,
                    show_ground=show_ground_dismissal_trans,
                    show_venue=show_venue_dismissal_trans,
                    show_overs=show_overs_dismissal_trans,
                    show_phase=show_phase_dismissal_trans,
                    show_bowl_type=show_bowl_type_dismissal_trans,
                    show_bowl_kind=show_bowl_kind_dismissal_trans,
                    show_bowl_arm=show_bowl_arm_dismissal_trans
                )
            except Exception as e:
                st.error(f"Error generating dismissal plot (transparent): {str(e)}")
                fig_dismissal_trans = None
            
            with col2:
                if fig_dismissal_trans:
                    st.pyplot(fig_dismissal_trans)
            
            with col3:
                if fig_dismissal_trans:
                    buf = BytesIO()
                    fig_dismissal_trans.savefig(buf, format='png', transparent=True, dpi=300, bbox_inches='tight')
                    buf.seek(0)
                    st.download_button(
                        label="📅 Download Plot as PNG",
                        data=buf.getvalue(),
                        file_name=f"{selected_player}_dismissal_plot_transparent.png",
                        mime="image/png",
                        key="dismissal_trans_download"
                    )

        # ===== 17 DISMISSAL PLOT VARIANTS =====
        if "━━ Dis Plot - vs All Types" in plot_types:
            st.markdown("<h2 style='text-align: center;'>Dismissal Plot - All Bowler Types</h2>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([2, 2, 2])
            
            with col1:
                st.markdown("## Customize Plot Info")
                show_title_dis_all_type = st.checkbox("Show Plot Title", value=True, key="dis_all_type_title")
                show_summary_dis_all_type = st.checkbox("Show Runs Summary", value=True, key="dis_all_type_summary")
                runs_count_dis_all_type = st.checkbox("Show Runs Count", value=True, key="dis_all_type_runs")
                show_fours_sixes_dis_all_type = st.checkbox("Show 4s and 6s", value=True, key="dis_all_type_fs")
                show_bowler_dis_all_type = st.checkbox("Show Bowler", value=True, key="dis_all_type_bowler")
                show_control_dis_all_type = st.checkbox("Show Control %", value=True, key="dis_all_type_control")
                show_prod_shot_dis_all_type = st.checkbox("Show Productive Shot", value=True, key="dis_all_type_prod")
                show_overs_dis_all_type = st.checkbox("Show Overs", value=True, key="dis_all_type_overs")
                show_phase_dis_all_type = st.checkbox("Show Phase", value=True, key="dis_all_type_phase")
                show_bowl_type_dis_all_type = st.checkbox("Show Bowl Type", value=True, key="dis_all_type_bowl_type")
                
            try:
                fig_dis_all_type = dismissal_plot(
                    df=df,
                    player_name=selected_player_value,
                    pid=selected_pid,
                    inns=selected_inns,
                    mat_num=selected_mat_num,
                    team_bat=selected_team_value,
                    team_bowl=selected_team_bowl_value,
                    bowler_name=bowler_name,
                    bowler_id=bowler_id,
                    competition=selected_competition_value,
                    transparent=False,
                    over_values=over_values,
                    phase=phase,
                    ground=selected_ground,
                    mcode=selected_mcode,
                    date_from=date_from,
                    date_to=date_to,
                    title_components=title_components if show_title_dis_all_type else [],
                    bat_hand=bat_hand,
                    bowl_type=bowl_type,
                    bowl_kind=None,
                    bowl_arm=bowl_arm,
                    show_title=show_title_dis_all_type,
                    show_summary=show_summary_dis_all_type,
                    runs_count=runs_count_dis_all_type,
                    show_fours_sixes=show_fours_sixes_dis_all_type,
                    show_control=show_control_dis_all_type,
                    show_prod_shot=show_prod_shot_dis_all_type,
                    show_bowler=show_bowler_dis_all_type,
                    show_overs=show_overs_dis_all_type,
                    show_phase=show_phase_dis_all_type,
                    show_bowl_type=show_bowl_type_dis_all_type
                )
                with col2:
                    st.pyplot(fig_dis_all_type)
            except Exception as e:
                st.error(f"Error generating dismissal plot: {str(e)}")
                fig_dis_all_type = None
            
            with col3:
                if fig_dis_all_type:
                    buf = BytesIO()
                    fig_dis_all_type.savefig(buf, format="png", transparent=False, dpi=300, bbox_inches='tight')
                    buf.seek(0)
                    st.download_button(
                        label="📅 Download Plot as PNG",
                        data=buf.getvalue(),
                        file_name=f"{selected_player}_dis_all_type.png",
                        mime="image/png",
                        key="dis_all_type_download"
                    )

        if "━━ Dis Plot - vs Pace" in plot_types:
            st.markdown("<h2 style='text-align: center;'>Dismissal Plot - vs Pace Bowlers</h2>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([2, 2, 2])
            
            with col1:
                st.markdown("## Customize Plot Info")
                show_title_dis_pace = st.checkbox("Show Plot Title", value=True, key="dis_pace_title")
                show_summary_dis_pace = st.checkbox("Show Runs Summary", value=True, key="dis_pace_summary")
                show_shots_breakdown_dis_pace = st.checkbox("Show Shots Breakdown", value=True, key="dis_pace_shots_breakdown")
                if show_shots_breakdown_dis_pace:
                    shots_breakdown_options_dis_pace = st.multiselect(
                        "Shots to Display",
                        options=['0s', '1s', '2s', '3s', '4s', '6s'],
                        default=['0s', '1s', '2s', '4s', '6s'],
                        key="dis_pace_shots_options"
                    )
                else:
                    shots_breakdown_options_dis_pace = []
                runs_count_dis_pace = st.checkbox("Show Runs Count", value=True, key="dis_pace_runs")
                show_fours_sixes_dis_pace = st.checkbox("Show 4s and 6s", value=True, key="dis_pace_fs")
                show_bowler_dis_pace = st.checkbox("Show Bowler", value=True, key="dis_pace_bowler")
                show_control_dis_pace = st.checkbox("Show Control %", value=True, key="dis_pace_control")
                show_prod_shot_dis_pace = st.checkbox("Show Productive Shot", value=True, key="dis_pace_prod")
                show_overs_dis_pace = st.checkbox("Show Overs", value=True, key="dis_pace_overs")
                show_phase_dis_pace = st.checkbox("Show Phase", value=True, key="dis_pace_phase")
                show_bowl_type_dis_pace = st.checkbox("Show Bowl Type", value=True, key="dis_pace_bowl_type")
                show_ground_dis_pace = st.checkbox("Show Ground", value=True, key="dis_pace_ground")
                show_venue_dis_pace = st.checkbox("Show Venue", value=True, key="dis_pace_venue")
                show_bowl_kind_dis_pace = st.checkbox("Show Bowl Pace", value=True, key="dis_pace_bowl_kind")
                show_bowl_arm_dis_pace = st.checkbox("Show Bowl Arm", value=True, key="dis_pace_bowl_arm")
                
            try:
                fig_dis_pace = dismissal_plot(
                    df=df,
                    player_name=selected_player_value,
                    pid=selected_pid,
                    inns=selected_inns,
                    mat_num=selected_mat_num,
                    team_bat=selected_team_value,
                    team_bowl=selected_team_bowl_value,
                    bowler_name=bowler_name,
                    bowler_id=bowler_id,
                    competition=selected_competition_value,
                    transparent=False,
                    over_values=over_values,
                    phase=phase,
                    ground=selected_ground,
                    mcode=selected_mcode,
                    date_from=date_from,
                    date_to=date_to,
                    title_components=title_components if show_title_dis_pace else [],
                    bat_hand=bat_hand,
                    bowl_type=bowl_type,
                    bowl_kind=["pace bowler", "Pace"],
                    bowl_arm=bowl_arm,
                    show_title=show_title_dis_pace,
                    show_summary=show_summary_dis_pace,
                    show_shots_breakdown=show_shots_breakdown_dis_pace,
                    shots_breakdown_options=shots_breakdown_options_dis_pace,
                    runs_count=runs_count_dis_pace,
                    show_fours_sixes=show_fours_sixes_dis_pace,
                    show_control=show_control_dis_pace,
                    show_prod_shot=show_prod_shot_dis_pace,
                    show_bowler=show_bowler_dis_pace,
                    show_ground=show_ground_dis_pace,
                    show_venue=show_venue_dis_pace,
                    show_overs=show_overs_dis_pace,
                    show_phase=show_phase_dis_pace,
                    show_bowl_type=show_bowl_type_dis_pace,
                    show_bowl_kind=show_bowl_kind_dis_pace,
                    show_bowl_arm=show_bowl_arm_dis_pace
                )
                with col2:
                    st.pyplot(fig_dis_pace)
            except Exception as e:
                st.error(f"Error generating dismissal plot: {str(e)}")
                fig_dis_pace = None
            
            with col3:
                if fig_dis_pace:
                    buf = BytesIO()
                    fig_dis_pace.savefig(buf, format="png", transparent=False, dpi=300, bbox_inches='tight')
                    buf.seek(0)
                    st.download_button(
                        label="📅 Download Plot as PNG",
                        data=buf.getvalue(),
                        file_name=f"{selected_player}_dis_pace.png",
                        mime="image/png",
                        key="dis_pace_download"
                    )

        if "━━ Dis Plot - vs Spin" in plot_types:
            st.markdown("<h2 style='text-align: center;'>Dismissal Plot - vs Spin Bowlers</h2>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([2, 2, 2])
            
            with col1:
                st.markdown("## Customize Plot Info")
                show_title_dis_spin = st.checkbox("Show Plot Title", value=True, key="dis_spin_title")
                show_summary_dis_spin = st.checkbox("Show Runs Summary", value=True, key="dis_spin_summary")
                show_shots_breakdown_dis_spin = st.checkbox("Show Shots Breakdown", value=True, key="dis_spin_shots_breakdown")
                if show_shots_breakdown_dis_spin:
                    shots_breakdown_options_dis_spin = st.multiselect(
                        "Shots to Display",
                        options=['0s', '1s', '2s', '3s', '4s', '6s'],
                        default=['0s', '1s', '2s', '4s', '6s'],
                        key="dis_spin_shots_options"
                    )
                else:
                    shots_breakdown_options_dis_spin = []
                runs_count_dis_spin = st.checkbox("Show Runs Count", value=True, key="dis_spin_runs")
                show_fours_sixes_dis_spin = st.checkbox("Show 4s and 6s", value=True, key="dis_spin_fs")
                show_bowler_dis_spin = st.checkbox("Show Bowler", value=True, key="dis_spin_bowler")
                show_control_dis_spin = st.checkbox("Show Control %", value=True, key="dis_spin_control")
                show_prod_shot_dis_spin = st.checkbox("Show Productive Shot", value=True, key="dis_spin_prod")
                show_overs_dis_spin = st.checkbox("Show Overs", value=True, key="dis_spin_overs")
                show_phase_dis_spin = st.checkbox("Show Phase", value=True, key="dis_spin_phase")
                show_bowl_type_dis_spin = st.checkbox("Show Bowl Type", value=True, key="dis_spin_bowl_type")
                show_ground_dis_spin = st.checkbox("Show Ground", value=True, key="dis_spin_ground")
                show_venue_dis_spin = st.checkbox("Show Venue", value=True, key="dis_spin_venue")
                show_bowl_kind_dis_spin = st.checkbox("Show Bowl Pace", value=True, key="dis_spin_bowl_kind")
                show_bowl_arm_dis_spin = st.checkbox("Show Bowl Arm", value=True, key="dis_spin_bowl_arm")
                
            try:
                fig_dis_spin = dismissal_plot(
                    df=df,
                    player_name=selected_player_value,
                    pid=selected_pid,
                    inns=selected_inns,
                    mat_num=selected_mat_num,
                    team_bat=selected_team_value,
                    team_bowl=selected_team_bowl_value,
                    bowler_name=bowler_name,
                    bowler_id=bowler_id,
                    competition=selected_competition_value,
                    transparent=False,
                    over_values=over_values,
                    phase=phase,
                    ground=selected_ground,
                    mcode=selected_mcode,
                    date_from=date_from,
                    date_to=date_to,
                    title_components=title_components if show_title_dis_spin else [],
                    bat_hand=bat_hand,
                    bowl_type=bowl_type,
                    bowl_kind=["spin bowler", "Spin"],
                    bowl_arm=bowl_arm,
                    show_title=show_title_dis_spin,
                    show_summary=show_summary_dis_spin,
                    show_shots_breakdown=show_shots_breakdown_dis_spin,
                    shots_breakdown_options=shots_breakdown_options_dis_spin,
                    runs_count=runs_count_dis_spin,
                    show_fours_sixes=show_fours_sixes_dis_spin,
                    show_control=show_control_dis_spin,
                    show_prod_shot=show_prod_shot_dis_spin,
                    show_bowler=show_bowler_dis_spin,
                    show_ground=show_ground_dis_spin,
                    show_venue=show_venue_dis_spin,
                    show_overs=show_overs_dis_spin,
                    show_phase=show_phase_dis_spin,
                    show_bowl_type=show_bowl_type_dis_spin,
                    show_bowl_kind=show_bowl_kind_dis_spin,
                    show_bowl_arm=show_bowl_arm_dis_spin
                )
                with col2:
                    st.pyplot(fig_dis_spin)
            except Exception as e:
                st.error(f"Error generating dismissal plot: {str(e)}")
                fig_dis_spin = None
            
            with col3:
                if fig_dis_spin:
                    buf = BytesIO()
                    fig_dis_spin.savefig(buf, format="png", transparent=False, dpi=300, bbox_inches='tight')
                    buf.seek(0)
                    st.download_button(
                        label="📅 Download Plot as PNG",
                        data=buf.getvalue(),
                        file_name=f"{selected_player}_dis_spin.png",
                        mime="image/png",
                        key="dis_spin_download"
                    )

        if "━━ Dis Plot - All Phases" in plot_types:
            st.markdown("<h2 style='text-align: center;'>Dismissal Plot - All Phases</h2>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([2, 2, 2])
            
            with col1:
                st.markdown("## Customize Plot Info")
                show_title_dis_all_phase = st.checkbox("Show Plot Title", value=True, key="dis_all_phase_title")
                show_summary_dis_all_phase = st.checkbox("Show Runs Summary", value=True, key="dis_all_phase_summary")
                show_shots_breakdown_dis_all_phase = st.checkbox("Show Shots Breakdown", value=True, key="dis_all_phase_shots_breakdown")
                if show_shots_breakdown_dis_all_phase:
                    shots_breakdown_options_dis_all_phase = st.multiselect(
                        "Shots to Display",
                        options=['0s', '1s', '2s', '3s', '4s', '6s'],
                        default=['0s', '1s', '2s', '4s', '6s'],
                        key="dis_all_phase_shots_options"
                    )
                else:
                    shots_breakdown_options_dis_all_phase = []
                runs_count_dis_all_phase = st.checkbox("Show Runs Count", value=True, key="dis_all_phase_runs")
                show_fours_sixes_dis_all_phase = st.checkbox("Show 4s and 6s", value=True, key="dis_all_phase_fs")
                show_bowler_dis_all_phase = st.checkbox("Show Bowler", value=True, key="dis_all_phase_bowler")
                show_control_dis_all_phase = st.checkbox("Show Control %", value=True, key="dis_all_phase_control")
                show_prod_shot_dis_all_phase = st.checkbox("Show Productive Shot", value=True, key="dis_all_phase_prod")
                show_overs_dis_all_phase = st.checkbox("Show Overs", value=True, key="dis_all_phase_overs")
                show_phase_dis_all_phase = st.checkbox("Show Phase", value=True, key="dis_all_phase_phase")
                show_bowl_type_dis_all_phase = st.checkbox("Show Bowl Type", value=True, key="dis_all_phase_bowl_type")
                show_ground_dis_all_phase = st.checkbox("Show Ground", value=True, key="dis_all_phase_ground")
                show_venue_dis_all_phase = st.checkbox("Show Venue", value=True, key="dis_all_phase_venue")
                show_bowl_kind_dis_all_phase = st.checkbox("Show Bowl Pace", value=True, key="dis_all_phase_bowl_kind")
                show_bowl_arm_dis_all_phase = st.checkbox("Show Bowl Arm", value=True, key="dis_all_phase_bowl_arm")
                
            try:
                fig_dis_all_phase = dismissal_plot(
                    df=df,
                    player_name=selected_player_value,
                    pid=selected_pid,
                    inns=selected_inns,
                    mat_num=selected_mat_num,
                    team_bat=selected_team_value,
                    team_bowl=selected_team_bowl_value,
                    bowler_name=bowler_name,
                    bowler_id=bowler_id,
                    competition=selected_competition_value,
                    transparent=False,
                    over_values=over_values,
                    phase=None,
                    ground=selected_ground,
                    mcode=selected_mcode,
                    date_from=date_from,
                    date_to=date_to,
                    title_components=title_components if show_title_dis_all_phase else [],
                    bat_hand=bat_hand,
                    bowl_type=bowl_type,
                    bowl_kind=bowl_kind,
                    bowl_arm=bowl_arm,
                    show_title=show_title_dis_all_phase,
                    show_summary=show_summary_dis_all_phase,
                    show_shots_breakdown=show_shots_breakdown_dis_all_phase,
                    shots_breakdown_options=shots_breakdown_options_dis_all_phase,
                    runs_count=runs_count_dis_all_phase,
                    show_fours_sixes=show_fours_sixes_dis_all_phase,
                    show_control=show_control_dis_all_phase,
                    show_prod_shot=show_prod_shot_dis_all_phase,
                    show_bowler=show_bowler_dis_all_phase,
                    show_ground=show_ground_dis_all_phase,
                    show_venue=show_venue_dis_all_phase,
                    show_overs=show_overs_dis_all_phase,
                    show_phase=show_phase_dis_all_phase,
                    show_bowl_type=show_bowl_type_dis_all_phase,
                    show_bowl_kind=show_bowl_kind_dis_all_phase,
                    show_bowl_arm=show_bowl_arm_dis_all_phase
                )
                with col2:
                    st.pyplot(fig_dis_all_phase)
            except Exception as e:
                st.error(f"Error generating dismissal plot: {str(e)}")
                fig_dis_all_phase = None
            
            with col3:
                if fig_dis_all_phase:
                    buf = BytesIO()
                    fig_dis_all_phase.savefig(buf, format="png", transparent=False, dpi=300, bbox_inches='tight')
                    buf.seek(0)
                    st.download_button(
                        label="📅 Download Plot as PNG",
                        data=buf.getvalue(),
                        file_name=f"{selected_player}_dis_all_phase.png",
                        mime="image/png",
                        key="dis_all_phase_download"
                    )

        if "━━ Dis Plot - Powerplay" in plot_types:
            st.markdown("<h2 style='text-align: center;'>Dismissal Plot - Powerplay Phase</h2>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([2, 2, 2])
            
            with col1:
                st.markdown("## Customize Plot Info")
                show_title_dis_pp = st.checkbox("Show Plot Title", value=True, key="dis_pp_title")
                show_summary_dis_pp = st.checkbox("Show Runs Summary", value=True, key="dis_pp_summary")
                show_shots_breakdown_dis_pp = st.checkbox("Show Shots Breakdown", value=True, key="dis_pp_shots_breakdown")
                if show_shots_breakdown_dis_pp:
                    shots_breakdown_options_dis_pp = st.multiselect(
                        "Shots to Display",
                        options=['0s', '1s', '2s', '3s', '4s', '6s'],
                        default=['0s', '1s', '2s', '4s', '6s'],
                        key="dis_pp_shots_options"
                    )
                else:
                    shots_breakdown_options_dis_pp = []
                runs_count_dis_pp = st.checkbox("Show Runs Count", value=True, key="dis_pp_runs")
                show_fours_sixes_dis_pp = st.checkbox("Show 4s and 6s", value=True, key="dis_pp_fs")
                show_bowler_dis_pp = st.checkbox("Show Bowler", value=True, key="dis_pp_bowler")
                show_control_dis_pp = st.checkbox("Show Control %", value=True, key="dis_pp_control")
                show_prod_shot_dis_pp = st.checkbox("Show Productive Shot", value=True, key="dis_pp_prod")
                show_overs_dis_pp = st.checkbox("Show Overs", value=True, key="dis_pp_overs")
                show_phase_dis_pp = st.checkbox("Show Phase", value=True, key="dis_pp_phase")
                show_bowl_type_dis_pp = st.checkbox("Show Bowl Type", value=True, key="dis_pp_bowl_type")
                show_ground_dis_pp = st.checkbox("Show Ground", value=True, key="dis_pp_ground")
                show_venue_dis_pp = st.checkbox("Show Venue", value=True, key="dis_pp_venue")
                show_bowl_kind_dis_pp = st.checkbox("Show Bowl Pace", value=True, key="dis_pp_bowl_kind")
                show_bowl_arm_dis_pp = st.checkbox("Show Bowl Arm", value=True, key="dis_pp_bowl_arm")
                
            try:
                fig_dis_pp = dismissal_plot(
                    df=df,
                    player_name=selected_player_value,
                    pid=selected_pid,
                    inns=selected_inns,
                    mat_num=selected_mat_num,
                    team_bat=selected_team_value,
                    team_bowl=selected_team_bowl_value,
                    bowler_name=bowler_name,
                    bowler_id=bowler_id,
                    competition=selected_competition_value,
                    transparent=False,
                    over_values=over_values,
                    phase=[1],
                    ground=selected_ground,
                    mcode=selected_mcode,
                    date_from=date_from,
                    date_to=date_to,
                    title_components=title_components if show_title_dis_pp else [],
                    bat_hand=bat_hand,
                    bowl_type=bowl_type,
                    bowl_kind=bowl_kind,
                    bowl_arm=bowl_arm,
                    show_title=show_title_dis_pp,
                    show_summary=show_summary_dis_pp,
                    show_shots_breakdown=show_shots_breakdown_dis_pp,
                    shots_breakdown_options=shots_breakdown_options_dis_pp,
                    runs_count=runs_count_dis_pp,
                    show_fours_sixes=show_fours_sixes_dis_pp,
                    show_control=show_control_dis_pp,
                    show_prod_shot=show_prod_shot_dis_pp,
                    show_bowler=show_bowler_dis_pp,
                    show_ground=show_ground_dis_pp,
                    show_venue=show_venue_dis_pp,
                    show_overs=show_overs_dis_pp,
                    show_phase=show_phase_dis_pp,
                    show_bowl_type=show_bowl_type_dis_pp,
                    show_bowl_kind=show_bowl_kind_dis_pp,
                    show_bowl_arm=show_bowl_arm_dis_pp
                )
                with col2:
                    st.pyplot(fig_dis_pp)
            except Exception as e:
                st.error(f"Error generating dismissal plot: {str(e)}")
                fig_dis_pp = None
            
            with col3:
                if fig_dis_pp:
                    buf = BytesIO()
                    fig_dis_pp.savefig(buf, format="png", transparent=False, dpi=300, bbox_inches='tight')
                    buf.seek(0)
                    st.download_button(
                        label="📅 Download Plot as PNG",
                        data=buf.getvalue(),
                        file_name=f"{selected_player}_dis_pp.png",
                        mime="image/png",
                        key="dis_pp_download"
                    )

        if "━━ Dis Plot - Middle" in plot_types:
            st.markdown("<h2 style='text-align: center;'>Dismissal Plot - Middle Phase</h2>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([2, 2, 2])
            
            with col1:
                st.markdown("## Customize Plot Info")
                show_title_dis_mid = st.checkbox("Show Plot Title", value=True, key="dis_mid_title")
                show_summary_dis_mid = st.checkbox("Show Runs Summary", value=True, key="dis_mid_summary")
                show_shots_breakdown_dis_mid = st.checkbox("Show Shots Breakdown", value=True, key="dis_mid_shots_breakdown")
                if show_shots_breakdown_dis_mid:
                    shots_breakdown_options_dis_mid = st.multiselect(
                        "Shots to Display",
                        options=['0s', '1s', '2s', '3s', '4s', '6s'],
                        default=['0s', '1s', '2s', '4s', '6s'],
                        key="dis_mid_shots_options"
                    )
                else:
                    shots_breakdown_options_dis_mid = []
                runs_count_dis_mid = st.checkbox("Show Runs Count", value=True, key="dis_mid_runs")
                show_fours_sixes_dis_mid = st.checkbox("Show 4s and 6s", value=True, key="dis_mid_fs")
                show_bowler_dis_mid = st.checkbox("Show Bowler", value=True, key="dis_mid_bowler")
                show_control_dis_mid = st.checkbox("Show Control %", value=True, key="dis_mid_control")
                show_prod_shot_dis_mid = st.checkbox("Show Productive Shot", value=True, key="dis_mid_prod")
                show_overs_dis_mid = st.checkbox("Show Overs", value=True, key="dis_mid_overs")
                show_phase_dis_mid = st.checkbox("Show Phase", value=True, key="dis_mid_phase")
                show_bowl_type_dis_mid = st.checkbox("Show Bowl Type", value=True, key="dis_mid_bowl_type")
                show_ground_dis_mid = st.checkbox("Show Ground", value=True, key="dis_mid_ground")
                show_venue_dis_mid = st.checkbox("Show Venue", value=True, key="dis_mid_venue")
                show_bowl_kind_dis_mid = st.checkbox("Show Bowl Pace", value=True, key="dis_mid_bowl_kind")
                show_bowl_arm_dis_mid = st.checkbox("Show Bowl Arm", value=True, key="dis_mid_bowl_arm")
                
            try:
                fig_dis_mid = dismissal_plot(
                    df=df,
                    player_name=selected_player_value,
                    pid=selected_pid,
                    inns=selected_inns,
                    mat_num=selected_mat_num,
                    team_bat=selected_team_value,
                    team_bowl=selected_team_bowl_value,
                    bowler_name=bowler_name,
                    bowler_id=bowler_id,
                    competition=selected_competition_value,
                    transparent=False,
                    over_values=over_values,
                    phase=[2],
                    ground=selected_ground,
                    mcode=selected_mcode,
                    date_from=date_from,
                    date_to=date_to,
                    title_components=title_components if show_title_dis_mid else [],
                    bat_hand=bat_hand,
                    bowl_type=bowl_type,
                    bowl_kind=bowl_kind,
                    bowl_arm=bowl_arm,
                    show_title=show_title_dis_mid,
                    show_summary=show_summary_dis_mid,
                    show_shots_breakdown=show_shots_breakdown_dis_mid,
                    shots_breakdown_options=shots_breakdown_options_dis_mid,
                    runs_count=runs_count_dis_mid,
                    show_fours_sixes=show_fours_sixes_dis_mid,
                    show_control=show_control_dis_mid,
                    show_prod_shot=show_prod_shot_dis_mid,
                    show_bowler=show_bowler_dis_mid,
                    show_ground=show_ground_dis_mid,
                    show_venue=show_venue_dis_mid,
                    show_overs=show_overs_dis_mid,
                    show_phase=show_phase_dis_mid,
                    show_bowl_type=show_bowl_type_dis_mid,
                    show_bowl_kind=show_bowl_kind_dis_mid,
                    show_bowl_arm=show_bowl_arm_dis_mid
                )
                with col2:
                    st.pyplot(fig_dis_mid)
            except Exception as e:
                st.error(f"Error generating dismissal plot: {str(e)}")
                fig_dis_mid = None
            
            with col3:
                if fig_dis_mid:
                    buf = BytesIO()
                    fig_dis_mid.savefig(buf, format="png", transparent=False, dpi=300, bbox_inches='tight')
                    buf.seek(0)
                    st.download_button(
                        label="📅 Download Plot as PNG",
                        data=buf.getvalue(),
                        file_name=f"{selected_player}_dis_mid.png",
                        mime="image/png",
                        key="dis_mid_download"
                    )

        if "━━ Dis Plot - Slog" in plot_types:
            st.markdown("<h2 style='text-align: center;'>Dismissal Plot - Slog Phase</h2>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([2, 2, 2])
            
            with col1:
                st.markdown("## Customize Plot Info")
                show_title_dis_slog = st.checkbox("Show Plot Title", value=True, key="dis_slog_title")
                show_summary_dis_slog = st.checkbox("Show Runs Summary", value=True, key="dis_slog_summary")
                show_shots_breakdown_dis_slog = st.checkbox("Show Shots Breakdown", value=True, key="dis_slog_shots_breakdown")
                if show_shots_breakdown_dis_slog:
                    shots_breakdown_options_dis_slog = st.multiselect(
                        "Shots to Display",
                        options=['0s', '1s', '2s', '3s', '4s', '6s'],
                        default=['0s', '1s', '2s', '4s', '6s'],
                        key="dis_slog_shots_options"
                    )
                else:
                    shots_breakdown_options_dis_slog = []
                runs_count_dis_slog = st.checkbox("Show Runs Count", value=True, key="dis_slog_runs")
                show_fours_sixes_dis_slog = st.checkbox("Show 4s and 6s", value=True, key="dis_slog_fs")
                show_bowler_dis_slog = st.checkbox("Show Bowler", value=True, key="dis_slog_bowler")
                show_control_dis_slog = st.checkbox("Show Control %", value=True, key="dis_slog_control")
                show_prod_shot_dis_slog = st.checkbox("Show Productive Shot", value=True, key="dis_slog_prod")
                show_overs_dis_slog = st.checkbox("Show Overs", value=True, key="dis_slog_overs")
                show_phase_dis_slog = st.checkbox("Show Phase", value=True, key="dis_slog_phase")
                show_bowl_type_dis_slog = st.checkbox("Show Bowl Type", value=True, key="dis_slog_bowl_type")
                show_ground_dis_slog = st.checkbox("Show Ground", value=True, key="dis_slog_ground")
                show_venue_dis_slog = st.checkbox("Show Venue", value=True, key="dis_slog_venue")
                show_bowl_kind_dis_slog = st.checkbox("Show Bowl Pace", value=True, key="dis_slog_bowl_kind")
                show_bowl_arm_dis_slog = st.checkbox("Show Bowl Arm", value=True, key="dis_slog_bowl_arm")
                
            try:
                fig_dis_slog = dismissal_plot(
                    df=df,
                    player_name=selected_player_value,
                    pid=selected_pid,
                    inns=selected_inns,
                    mat_num=selected_mat_num,
                    team_bat=selected_team_value,
                    team_bowl=selected_team_bowl_value,
                    bowler_name=bowler_name,
                    bowler_id=bowler_id,
                    competition=selected_competition_value,
                    transparent=False,
                    over_values=over_values,
                    phase=[3],
                    ground=selected_ground,
                    mcode=selected_mcode,
                    date_from=date_from,
                    date_to=date_to,
                    title_components=title_components if show_title_dis_slog else [],
                    bat_hand=bat_hand,
                    bowl_type=bowl_type,
                    bowl_kind=bowl_kind,
                    bowl_arm=bowl_arm,
                    show_title=show_title_dis_slog,
                    show_summary=show_summary_dis_slog,
                    show_shots_breakdown=show_shots_breakdown_dis_slog,
                    shots_breakdown_options=shots_breakdown_options_dis_slog,
                    runs_count=runs_count_dis_slog,
                    show_fours_sixes=show_fours_sixes_dis_slog,
                    show_control=show_control_dis_slog,
                    show_prod_shot=show_prod_shot_dis_slog,
                    show_bowler=show_bowler_dis_slog,
                    show_ground=show_ground_dis_slog,
                    show_venue=show_venue_dis_slog,
                    show_overs=show_overs_dis_slog,
                    show_phase=show_phase_dis_slog,
                    show_bowl_type=show_bowl_type_dis_slog,
                    show_bowl_kind=show_bowl_kind_dis_slog,
                    show_bowl_arm=show_bowl_arm_dis_slog
                )
                with col2:
                    st.pyplot(fig_dis_slog)
            except Exception as e:
                st.error(f"Error generating dismissal plot: {str(e)}")
                fig_dis_slog = None
            
            with col3:
                if fig_dis_slog:
                    buf = BytesIO()
                    fig_dis_slog.savefig(buf, format="png", transparent=False, dpi=300, bbox_inches='tight')
                    buf.seek(0)
                    st.download_button(
                        label="📅 Download Plot as PNG",
                        data=buf.getvalue(),
                        file_name=f"{selected_player}_dis_slog.png",
                        mime="image/png",
                        key="dis_slog_download"
                    )

        if "━━ Dis Plot - All Kinds" in plot_types:
            st.markdown("<h2 style='text-align: center;'>Dismissal Plot - All Bowling Kinds</h2>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([2, 2, 2])
            
            with col1:
                st.markdown("## Customize Plot Info")
                show_title_dis_all_kind = st.checkbox("Show Plot Title", value=True, key="dis_all_kind_title")
                show_summary_dis_all_kind = st.checkbox("Show Runs Summary", value=True, key="dis_all_kind_summary")
                show_shots_breakdown_dis_all_kind = st.checkbox("Show Shots Breakdown", value=True, key="dis_all_kind_shots_breakdown")
                if show_shots_breakdown_dis_all_kind:
                    shots_breakdown_options_dis_all_kind = st.multiselect(
                        "Shots to Display",
                        options=['0s', '1s', '2s', '3s', '4s', '6s'],
                        default=['0s', '1s', '2s', '4s', '6s'],
                        key="dis_all_kind_shots_options"
                    )
                else:
                    shots_breakdown_options_dis_all_kind = []
                runs_count_dis_all_kind = st.checkbox("Show Runs Count", value=True, key="dis_all_kind_runs")
                show_fours_sixes_dis_all_kind = st.checkbox("Show 4s and 6s", value=True, key="dis_all_kind_fs")
                show_bowler_dis_all_kind = st.checkbox("Show Bowler", value=True, key="dis_all_kind_bowler")
                show_control_dis_all_kind = st.checkbox("Show Control %", value=True, key="dis_all_kind_control")
                show_prod_shot_dis_all_kind = st.checkbox("Show Productive Shot", value=True, key="dis_all_kind_prod")
                show_overs_dis_all_kind = st.checkbox("Show Overs", value=True, key="dis_all_kind_overs")
                show_phase_dis_all_kind = st.checkbox("Show Phase", value=True, key="dis_all_kind_phase")
                show_bowl_type_dis_all_kind = st.checkbox("Show Bowl Type", value=True, key="dis_all_kind_bowl_type")
                show_ground_dis_all_kind = st.checkbox("Show Ground", value=True, key="dis_all_kind_ground")
                show_venue_dis_all_kind = st.checkbox("Show Venue", value=True, key="dis_all_kind_venue")
                show_bowl_kind_dis_all_kind = st.checkbox("Show Bowl Pace", value=True, key="dis_all_kind_bowl_kind")
                show_bowl_arm_dis_all_kind = st.checkbox("Show Bowl Arm", value=True, key="dis_all_kind_bowl_arm")
                
            try:
                fig_dis_all_kind = dismissal_plot(
                    df=df,
                    player_name=selected_player_value,
                    pid=selected_pid,
                    inns=selected_inns,
                    mat_num=selected_mat_num,
                    team_bat=selected_team_value,
                    team_bowl=selected_team_bowl_value,
                    bowler_name=bowler_name,
                    bowler_id=bowler_id,
                    competition=selected_competition_value,
                    transparent=False,
                    over_values=over_values,
                    phase=phase,
                    ground=selected_ground,
                    mcode=selected_mcode,
                    date_from=date_from,
                    date_to=date_to,
                    title_components=title_components if show_title_dis_all_kind else [],
                    bat_hand=bat_hand,
                    bowl_type=bowl_type,
                    bowl_kind=None,
                    bowl_arm=bowl_arm,
                    show_title=show_title_dis_all_kind,
                    show_summary=show_summary_dis_all_kind,
                    show_shots_breakdown=show_shots_breakdown_dis_all_kind,
                    shots_breakdown_options=shots_breakdown_options_dis_all_kind,
                    runs_count=runs_count_dis_all_kind,
                    show_fours_sixes=show_fours_sixes_dis_all_kind,
                    show_control=show_control_dis_all_kind,
                    show_prod_shot=show_prod_shot_dis_all_kind,
                    show_bowler=show_bowler_dis_all_kind,
                    show_ground=show_ground_dis_all_kind,
                    show_venue=show_venue_dis_all_kind,
                    show_overs=show_overs_dis_all_kind,
                    show_phase=show_phase_dis_all_kind,
                    show_bowl_type=show_bowl_type_dis_all_kind,
                    show_bowl_kind=show_bowl_kind_dis_all_kind,
                    show_bowl_arm=show_bowl_arm_dis_all_kind
                )
                with col2:
                    st.pyplot(fig_dis_all_kind)
            except Exception as e:
                st.error(f"Error generating dismissal plot: {str(e)}")
                fig_dis_all_kind = None
            
            with col3:
                if fig_dis_all_kind:
                    buf = BytesIO()
                    fig_dis_all_kind.savefig(buf, format="png", transparent=False, dpi=300, bbox_inches='tight')
                    buf.seek(0)
                    st.download_button(
                        label="📅 Download Plot as PNG",
                        data=buf.getvalue(),
                        file_name=f"{selected_player}_dis_all_kind.png",
                        mime="image/png",
                        key="dis_all_kind_download"
                    )

        if "━━ Dis Plot - RAP" in plot_types:
            st.markdown("<h2 style='text-align: center;'>Dismissal Plot - Right Arm Pace</h2>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([2, 2, 2])
            
            with col1:
                st.markdown("## Customize Plot Info")
                show_title_dis_rap = st.checkbox("Show Plot Title", value=True, key="dis_rap_title")
                show_summary_dis_rap = st.checkbox("Show Runs Summary", value=True, key="dis_rap_summary")
                show_shots_breakdown_dis_rap = st.checkbox("Show Shots Breakdown", value=True, key="dis_rap_shots_breakdown")
                if show_shots_breakdown_dis_rap:
                    shots_breakdown_options_dis_rap = st.multiselect(
                        "Shots to Display",
                        options=['0s', '1s', '2s', '3s', '4s', '6s'],
                        default=['0s', '1s', '2s', '4s', '6s'],
                        key="dis_rap_shots_options"
                    )
                else:
                    shots_breakdown_options_dis_rap = []
                runs_count_dis_rap = st.checkbox("Show Runs Count", value=True, key="dis_rap_runs")
                show_fours_sixes_dis_rap = st.checkbox("Show 4s and 6s", value=True, key="dis_rap_fs")
                show_bowler_dis_rap = st.checkbox("Show Bowler", value=True, key="dis_rap_bowler")
                show_control_dis_rap = st.checkbox("Show Control %", value=True, key="dis_rap_control")
                show_prod_shot_dis_rap = st.checkbox("Show Productive Shot", value=True, key="dis_rap_prod")
                show_overs_dis_rap = st.checkbox("Show Overs", value=True, key="dis_rap_overs")
                show_phase_dis_rap = st.checkbox("Show Phase", value=True, key="dis_rap_phase")
                show_bowl_type_dis_rap = st.checkbox("Show Bowl Type", value=True, key="dis_rap_bowl_type")
                show_ground_dis_rap = st.checkbox("Show Ground", value=True, key="dis_rap_ground")
                show_venue_dis_rap = st.checkbox("Show Venue", value=True, key="dis_rap_venue")
                show_bowl_kind_dis_rap = st.checkbox("Show Bowl Pace", value=True, key="dis_rap_bowl_kind")
                show_bowl_arm_dis_rap = st.checkbox("Show Bowl Arm", value=True, key="dis_rap_bowl_arm")
                
            try:
                fig_dis_rap = dismissal_plot(
                    df=df,
                    player_name=selected_player_value,
                    pid=selected_pid,
                    inns=selected_inns,
                    mat_num=selected_mat_num,
                    team_bat=selected_team_value,
                    team_bowl=selected_team_bowl_value,
                    bowler_name=bowler_name,
                    bowler_id=bowler_id,
                    competition=selected_competition_value,
                    transparent=False,
                    over_values=over_values,
                    phase=phase,
                    ground=selected_ground,
                    mcode=selected_mcode,
                    date_from=date_from,
                    date_to=date_to,
                    title_components=title_components if show_title_dis_rap else [],
                    bat_hand=bat_hand,
                    bowl_type=["Right Arm Pace"],
                    bowl_kind=bowl_kind,
                    bowl_arm=bowl_arm,
                    show_title=show_title_dis_rap,
                    show_summary=show_summary_dis_rap,
                    show_shots_breakdown=show_shots_breakdown_dis_rap,
                    shots_breakdown_options=shots_breakdown_options_dis_rap,
                    runs_count=runs_count_dis_rap,
                    show_fours_sixes=show_fours_sixes_dis_rap,
                    show_control=show_control_dis_rap,
                    show_prod_shot=show_prod_shot_dis_rap,
                    show_bowler=show_bowler_dis_rap,
                    show_ground=show_ground_dis_rap,
                    show_venue=show_venue_dis_rap,
                    show_overs=show_overs_dis_rap,
                    show_phase=show_phase_dis_rap,
                    show_bowl_type=show_bowl_type_dis_rap,
                    show_bowl_kind=show_bowl_kind_dis_rap,
                    show_bowl_arm=show_bowl_arm_dis_rap
                )
                with col2:
                    st.pyplot(fig_dis_rap)
            except Exception as e:
                st.error(f"Error generating dismissal plot: {str(e)}")
                fig_dis_rap = None
            
            with col3:
                if fig_dis_rap:
                    buf = BytesIO()
                    fig_dis_rap.savefig(buf, format="png", transparent=False, dpi=300, bbox_inches='tight')
                    buf.seek(0)
                    st.download_button(
                        label="📅 Download Plot as PNG",
                        data=buf.getvalue(),
                        file_name=f"{selected_player}_dis_rap.png",
                        mime="image/png",
                        key="dis_rap_download"
                    )

        if "━━ Dis Plot - RAFS" in plot_types:
            st.markdown("<h2 style='text-align: center;'>Dismissal Plot - Right Arm Fast Spin</h2>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([2, 2, 2])
            
            with col1:
                st.markdown("## Customize Plot Info")
                show_title_dis_rafs = st.checkbox("Show Plot Title", value=True, key="dis_rafs_title")
                show_summary_dis_rafs = st.checkbox("Show Runs Summary", value=True, key="dis_rafs_summary")
                show_shots_breakdown_dis_rafs = st.checkbox("Show Shots Breakdown", value=True, key="dis_rafs_shots_breakdown")
                if show_shots_breakdown_dis_rafs:
                    shots_breakdown_options_dis_rafs = st.multiselect(
                        "Shots to Display",
                        options=['0s', '1s', '2s', '3s', '4s', '6s'],
                        default=['0s', '1s', '2s', '4s', '6s'],
                        key="dis_rafs_shots_options"
                    )
                else:
                    shots_breakdown_options_dis_rafs = []
                runs_count_dis_rafs = st.checkbox("Show Runs Count", value=True, key="dis_rafs_runs")
                show_fours_sixes_dis_rafs = st.checkbox("Show 4s and 6s", value=True, key="dis_rafs_fs")
                show_bowler_dis_rafs = st.checkbox("Show Bowler", value=True, key="dis_rafs_bowler")
                show_control_dis_rafs = st.checkbox("Show Control %", value=True, key="dis_rafs_control")
                show_prod_shot_dis_rafs = st.checkbox("Show Productive Shot", value=True, key="dis_rafs_prod")
                show_overs_dis_rafs = st.checkbox("Show Overs", value=True, key="dis_rafs_overs")
                show_phase_dis_rafs = st.checkbox("Show Phase", value=True, key="dis_rafs_phase")
                show_bowl_type_dis_rafs = st.checkbox("Show Bowl Type", value=True, key="dis_rafs_bowl_type")
                show_ground_dis_rafs = st.checkbox("Show Ground", value=True, key="dis_rafs_ground")
                show_venue_dis_rafs = st.checkbox("Show Venue", value=True, key="dis_rafs_venue")
                show_bowl_kind_dis_rafs = st.checkbox("Show Bowl Pace", value=True, key="dis_rafs_bowl_kind")
                show_bowl_arm_dis_rafs = st.checkbox("Show Bowl Arm", value=True, key="dis_rafs_bowl_arm")
                
            try:
                fig_dis_rafs = dismissal_plot(
                    df=df,
                    player_name=selected_player_value,
                    pid=selected_pid,
                    inns=selected_inns,
                    mat_num=selected_mat_num,
                    team_bat=selected_team_value,
                    team_bowl=selected_team_bowl_value,
                    bowler_name=bowler_name,
                    bowler_id=bowler_id,
                    competition=selected_competition_value,
                    transparent=False,
                    over_values=over_values,
                    phase=phase,
                    ground=selected_ground,
                    mcode=selected_mcode,
                    date_from=date_from,
                    date_to=date_to,
                    title_components=title_components if show_title_dis_rafs else [],
                    bat_hand=bat_hand,
                    bowl_type=["Right Arm Fast Spin"],
                    bowl_kind=bowl_kind,
                    bowl_arm=bowl_arm,
                    show_title=show_title_dis_rafs,
                    show_summary=show_summary_dis_rafs,
                    show_shots_breakdown=show_shots_breakdown_dis_rafs,
                    shots_breakdown_options=shots_breakdown_options_dis_rafs,
                    runs_count=runs_count_dis_rafs,
                    show_fours_sixes=show_fours_sixes_dis_rafs,
                    show_control=show_control_dis_rafs,
                    show_prod_shot=show_prod_shot_dis_rafs,
                    show_bowler=show_bowler_dis_rafs,
                    show_ground=show_ground_dis_rafs,
                    show_venue=show_venue_dis_rafs,
                    show_overs=show_overs_dis_rafs,
                    show_phase=show_phase_dis_rafs,
                    show_bowl_type=show_bowl_type_dis_rafs,
                    show_bowl_kind=show_bowl_kind_dis_rafs,
                    show_bowl_arm=show_bowl_arm_dis_rafs
                )
                with col2:
                    st.pyplot(fig_dis_rafs)
            except Exception as e:
                st.error(f"Error generating dismissal plot: {str(e)}")
                fig_dis_rafs = None
            
            with col3:
                if fig_dis_rafs:
                    buf = BytesIO()
                    fig_dis_rafs.savefig(buf, format="png", transparent=False, dpi=300, bbox_inches='tight')
                    buf.seek(0)
                    st.download_button(
                        label="📅 Download Plot as PNG",
                        data=buf.getvalue(),
                        file_name=f"{selected_player}_dis_rafs.png",
                        mime="image/png",
                        key="dis_rafs_download"
                    )

        if "━━ Dis Plot - RAWS" in plot_types:
            st.markdown("<h2 style='text-align: center;'>Dismissal Plot - Right Arm Wrist Spin</h2>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([2, 2, 2])
            
            with col1:
                st.markdown("## Customize Plot Info")
                show_title_dis_raws = st.checkbox("Show Plot Title", value=True, key="dis_raws_title")
                show_summary_dis_raws = st.checkbox("Show Runs Summary", value=True, key="dis_raws_summary")
                show_shots_breakdown_dis_raws = st.checkbox("Show Shots Breakdown", value=True, key="dis_raws_shots_breakdown")
                if show_shots_breakdown_dis_raws:
                    shots_breakdown_options_dis_raws = st.multiselect(
                        "Shots to Display",
                        options=['0s', '1s', '2s', '3s', '4s', '6s'],
                        default=['0s', '1s', '2s', '4s', '6s'],
                        key="dis_raws_shots_options"
                    )
                else:
                    shots_breakdown_options_dis_raws = []
                runs_count_dis_raws = st.checkbox("Show Runs Count", value=True, key="dis_raws_runs")
                show_fours_sixes_dis_raws = st.checkbox("Show 4s and 6s", value=True, key="dis_raws_fs")
                show_bowler_dis_raws = st.checkbox("Show Bowler", value=True, key="dis_raws_bowler")
                show_control_dis_raws = st.checkbox("Show Control %", value=True, key="dis_raws_control")
                show_prod_shot_dis_raws = st.checkbox("Show Productive Shot", value=True, key="dis_raws_prod")
                show_overs_dis_raws = st.checkbox("Show Overs", value=True, key="dis_raws_overs")
                show_phase_dis_raws = st.checkbox("Show Phase", value=True, key="dis_raws_phase")
                show_bowl_type_dis_raws = st.checkbox("Show Bowl Type", value=True, key="dis_raws_bowl_type")
                show_ground_dis_raws = st.checkbox("Show Ground", value=True, key="dis_raws_ground")
                show_venue_dis_raws = st.checkbox("Show Venue", value=True, key="dis_raws_venue")
                show_bowl_kind_dis_raws = st.checkbox("Show Bowl Pace", value=True, key="dis_raws_bowl_kind")
                show_bowl_arm_dis_raws = st.checkbox("Show Bowl Arm", value=True, key="dis_raws_bowl_arm")
                
            try:
                fig_dis_raws = dismissal_plot(
                    df=df,
                    player_name=selected_player_value,
                    pid=selected_pid,
                    inns=selected_inns,
                    mat_num=selected_mat_num,
                    team_bat=selected_team_value,
                    team_bowl=selected_team_bowl_value,
                    bowler_name=bowler_name,
                    bowler_id=bowler_id,
                    competition=selected_competition_value,
                    transparent=False,
                    over_values=over_values,
                    phase=phase,
                    ground=selected_ground,
                    mcode=selected_mcode,
                    date_from=date_from,
                    date_to=date_to,
                    title_components=title_components if show_title_dis_raws else [],
                    bat_hand=bat_hand,
                    bowl_type=["Right Arm Wrist Spin"],
                    bowl_kind=bowl_kind,
                    bowl_arm=bowl_arm,
                    show_title=show_title_dis_raws,
                    show_summary=show_summary_dis_raws,
                    show_shots_breakdown=show_shots_breakdown_dis_raws,
                    shots_breakdown_options=shots_breakdown_options_dis_raws,
                    runs_count=runs_count_dis_raws,
                    show_fours_sixes=show_fours_sixes_dis_raws,
                    show_control=show_control_dis_raws,
                    show_prod_shot=show_prod_shot_dis_raws,
                    show_bowler=show_bowler_dis_raws,
                    show_ground=show_ground_dis_raws,
                    show_venue=show_venue_dis_raws,
                    show_overs=show_overs_dis_raws,
                    show_phase=show_phase_dis_raws,
                    show_bowl_type=show_bowl_type_dis_raws,
                    show_bowl_kind=show_bowl_kind_dis_raws,
                    show_bowl_arm=show_bowl_arm_dis_raws
                )
                with col2:
                    st.pyplot(fig_dis_raws)
            except Exception as e:
                st.error(f"Error generating dismissal plot: {str(e)}")
                fig_dis_raws = None
            
            with col3:
                if fig_dis_raws:
                    buf = BytesIO()
                    fig_dis_raws.savefig(buf, format="png", transparent=False, dpi=300, bbox_inches='tight')
                    buf.seek(0)
                    st.download_button(
                        label="📅 Download Plot as PNG",
                        data=buf.getvalue(),
                        file_name=f"{selected_player}_dis_raws.png",
                        mime="image/png",
                        key="dis_raws_download"
                    )

        if "━━ Dis Plot - LAP" in plot_types:
            st.markdown("<h2 style='text-align: center;'>Dismissal Plot - Left Arm Pace</h2>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([2, 2, 2])
            
            with col1:
                st.markdown("## Customize Plot Info")
                show_title_dis_lap = st.checkbox("Show Plot Title", value=True, key="dis_lap_title")
                show_summary_dis_lap = st.checkbox("Show Runs Summary", value=True, key="dis_lap_summary")
                show_shots_breakdown_dis_lap = st.checkbox("Show Shots Breakdown", value=True, key="dis_lap_shots_breakdown")
                if show_shots_breakdown_dis_lap:
                    shots_breakdown_options_dis_lap = st.multiselect(
                        "Shots to Display",
                        options=['0s', '1s', '2s', '3s', '4s', '6s'],
                        default=['0s', '1s', '2s', '4s', '6s'],
                        key="dis_lap_shots_options"
                    )
                else:
                    shots_breakdown_options_dis_lap = []
                runs_count_dis_lap = st.checkbox("Show Runs Count", value=True, key="dis_lap_runs")
                show_fours_sixes_dis_lap = st.checkbox("Show 4s and 6s", value=True, key="dis_lap_fs")
                show_bowler_dis_lap = st.checkbox("Show Bowler", value=True, key="dis_lap_bowler")
                show_control_dis_lap = st.checkbox("Show Control %", value=True, key="dis_lap_control")
                show_prod_shot_dis_lap = st.checkbox("Show Productive Shot", value=True, key="dis_lap_prod")
                show_overs_dis_lap = st.checkbox("Show Overs", value=True, key="dis_lap_overs")
                show_phase_dis_lap = st.checkbox("Show Phase", value=True, key="dis_lap_phase")
                show_bowl_type_dis_lap = st.checkbox("Show Bowl Type", value=True, key="dis_lap_bowl_type")
                show_ground_dis_lap = st.checkbox("Show Ground", value=True, key="dis_lap_ground")
                show_venue_dis_lap = st.checkbox("Show Venue", value=True, key="dis_lap_venue")
                show_bowl_kind_dis_lap = st.checkbox("Show Bowl Pace", value=True, key="dis_lap_bowl_kind")
                show_bowl_arm_dis_lap = st.checkbox("Show Bowl Arm", value=True, key="dis_lap_bowl_arm")
                
            try:
                fig_dis_lap = dismissal_plot(
                    df=df,
                    player_name=selected_player_value,
                    pid=selected_pid,
                    inns=selected_inns,
                    mat_num=selected_mat_num,
                    team_bat=selected_team_value,
                    team_bowl=selected_team_bowl_value,
                    bowler_name=bowler_name,
                    bowler_id=bowler_id,
                    competition=selected_competition_value,
                    transparent=False,
                    over_values=over_values,
                    phase=phase,
                    ground=selected_ground,
                    mcode=selected_mcode,
                    date_from=date_from,
                    date_to=date_to,
                    title_components=title_components if show_title_dis_lap else [],
                    bat_hand=bat_hand,
                    bowl_type=["Left Arm Pace"],
                    bowl_kind=bowl_kind,
                    bowl_arm=bowl_arm,
                    show_title=show_title_dis_lap,
                    show_summary=show_summary_dis_lap,
                    show_shots_breakdown=show_shots_breakdown_dis_lap,
                    shots_breakdown_options=shots_breakdown_options_dis_lap,
                    runs_count=runs_count_dis_lap,
                    show_fours_sixes=show_fours_sixes_dis_lap,
                    show_control=show_control_dis_lap,
                    show_prod_shot=show_prod_shot_dis_lap,
                    show_bowler=show_bowler_dis_lap,
                    show_ground=show_ground_dis_lap,
                    show_venue=show_venue_dis_lap,
                    show_overs=show_overs_dis_lap,
                    show_phase=show_phase_dis_lap,
                    show_bowl_type=show_bowl_type_dis_lap,
                    show_bowl_kind=show_bowl_kind_dis_lap,
                    show_bowl_arm=show_bowl_arm_dis_lap
                )
                with col2:
                    st.pyplot(fig_dis_lap)
            except Exception as e:
                st.error(f"Error generating dismissal plot: {str(e)}")
                fig_dis_lap = None
            
            with col3:
                if fig_dis_lap:
                    buf = BytesIO()
                    fig_dis_lap.savefig(buf, format="png", transparent=False, dpi=300, bbox_inches='tight')
                    buf.seek(0)
                    st.download_button(
                        label="📅 Download Plot as PNG",
                        data=buf.getvalue(),
                        file_name=f"{selected_player}_dis_lap.png",
                        mime="image/png",
                        key="dis_lap_download"
                    )

        if "━━ Dis Plot - LAFS" in plot_types:
            st.markdown("<h2 style='text-align: center;'>Dismissal Plot - Left Arm Fast Spin</h2>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([2, 2, 2])
            
            with col1:
                st.markdown("## Customize Plot Info")
                show_title_dis_lafs = st.checkbox("Show Plot Title", value=True, key="dis_lafs_title")
                show_summary_dis_lafs = st.checkbox("Show Runs Summary", value=True, key="dis_lafs_summary")
                show_shots_breakdown_dis_lafs = st.checkbox("Show Shots Breakdown", value=True, key="dis_lafs_shots_breakdown")
                if show_shots_breakdown_dis_lafs:
                    shots_breakdown_options_dis_lafs = st.multiselect(
                        "Shots to Display",
                        options=['0s', '1s', '2s', '3s', '4s', '6s'],
                        default=['0s', '1s', '2s', '4s', '6s'],
                        key="dis_lafs_shots_options"
                    )
                else:
                    shots_breakdown_options_dis_lafs = []
                runs_count_dis_lafs = st.checkbox("Show Runs Count", value=True, key="dis_lafs_runs")
                show_fours_sixes_dis_lafs = st.checkbox("Show 4s and 6s", value=True, key="dis_lafs_fs")
                show_bowler_dis_lafs = st.checkbox("Show Bowler", value=True, key="dis_lafs_bowler")
                show_control_dis_lafs = st.checkbox("Show Control %", value=True, key="dis_lafs_control")
                show_prod_shot_dis_lafs = st.checkbox("Show Productive Shot", value=True, key="dis_lafs_prod")
                show_overs_dis_lafs = st.checkbox("Show Overs", value=True, key="dis_lafs_overs")
                show_phase_dis_lafs = st.checkbox("Show Phase", value=True, key="dis_lafs_phase")
                show_bowl_type_dis_lafs = st.checkbox("Show Bowl Type", value=True, key="dis_lafs_bowl_type")
                show_ground_dis_lafs = st.checkbox("Show Ground", value=True, key="dis_lafs_ground")
                show_venue_dis_lafs = st.checkbox("Show Venue", value=True, key="dis_lafs_venue")
                show_bowl_kind_dis_lafs = st.checkbox("Show Bowl Pace", value=True, key="dis_lafs_bowl_kind")
                show_bowl_arm_dis_lafs = st.checkbox("Show Bowl Arm", value=True, key="dis_lafs_bowl_arm")
                
            try:
                fig_dis_lafs = dismissal_plot(
                    df=df,
                    player_name=selected_player_value,
                    pid=selected_pid,
                    inns=selected_inns,
                    mat_num=selected_mat_num,
                    team_bat=selected_team_value,
                    team_bowl=selected_team_bowl_value,
                    bowler_name=bowler_name,
                    bowler_id=bowler_id,
                    competition=selected_competition_value,
                    transparent=False,
                    over_values=over_values,
                    phase=phase,
                    ground=selected_ground,
                    mcode=selected_mcode,
                    date_from=date_from,
                    date_to=date_to,
                    title_components=title_components if show_title_dis_lafs else [],
                    bat_hand=bat_hand,
                    bowl_type=["Left Arm Fast Spin"],
                    bowl_kind=bowl_kind,
                    bowl_arm=bowl_arm,
                    show_title=show_title_dis_lafs,
                    show_summary=show_summary_dis_lafs,
                    show_shots_breakdown=show_shots_breakdown_dis_lafs,
                    shots_breakdown_options=shots_breakdown_options_dis_lafs,
                    runs_count=runs_count_dis_lafs,
                    show_fours_sixes=show_fours_sixes_dis_lafs,
                    show_control=show_control_dis_lafs,
                    show_prod_shot=show_prod_shot_dis_lafs,
                    show_bowler=show_bowler_dis_lafs,
                    show_ground=show_ground_dis_lafs,
                    show_venue=show_venue_dis_lafs,
                    show_overs=show_overs_dis_lafs,
                    show_phase=show_phase_dis_lafs,
                    show_bowl_type=show_bowl_type_dis_lafs,
                    show_bowl_kind=show_bowl_kind_dis_lafs,
                    show_bowl_arm=show_bowl_arm_dis_lafs
                )
                with col2:
                    st.pyplot(fig_dis_lafs)
            except Exception as e:
                st.error(f"Error generating dismissal plot: {str(e)}")
                fig_dis_lafs = None
            
            with col3:
                if fig_dis_lafs:
                    buf = BytesIO()
                    fig_dis_lafs.savefig(buf, format="png", transparent=False, dpi=300, bbox_inches='tight')
                    buf.seek(0)
                    st.download_button(
                        label="📅 Download Plot as PNG",
                        data=buf.getvalue(),
                        file_name=f"{selected_player}_dis_lafs.png",
                        mime="image/png",
                        key="dis_lafs_download"
                    )

        if "━━ Dis Plot - LAWS" in plot_types:
            st.markdown("<h2 style='text-align: center;'>Dismissal Plot - Left Arm Wrist Spin</h2>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([2, 2, 2])
            
            with col1:
                st.markdown("## Customize Plot Info")
                show_title_dis_laws = st.checkbox("Show Plot Title", value=True, key="dis_laws_title")
                show_summary_dis_laws = st.checkbox("Show Runs Summary", value=True, key="dis_laws_summary")
                show_shots_breakdown_dis_laws = st.checkbox("Show Shots Breakdown", value=True, key="dis_laws_shots_breakdown")
                if show_shots_breakdown_dis_laws:
                    shots_breakdown_options_dis_laws = st.multiselect(
                        "Shots to Display",
                        options=['0s', '1s', '2s', '3s', '4s', '6s'],
                        default=['0s', '1s', '2s', '4s', '6s'],
                        key="dis_laws_shots_options"
                    )
                else:
                    shots_breakdown_options_dis_laws = []
                runs_count_dis_laws = st.checkbox("Show Runs Count", value=True, key="dis_laws_runs")
                show_fours_sixes_dis_laws = st.checkbox("Show 4s and 6s", value=True, key="dis_laws_fs")
                show_bowler_dis_laws = st.checkbox("Show Bowler", value=True, key="dis_laws_bowler")
                show_control_dis_laws = st.checkbox("Show Control %", value=True, key="dis_laws_control")
                show_prod_shot_dis_laws = st.checkbox("Show Productive Shot", value=True, key="dis_laws_prod")
                show_overs_dis_laws = st.checkbox("Show Overs", value=True, key="dis_laws_overs")
                show_phase_dis_laws = st.checkbox("Show Phase", value=True, key="dis_laws_phase")
                show_bowl_type_dis_laws = st.checkbox("Show Bowl Type", value=True, key="dis_laws_bowl_type")
                show_ground_dis_laws = st.checkbox("Show Ground", value=True, key="dis_laws_ground")
                show_venue_dis_laws = st.checkbox("Show Venue", value=True, key="dis_laws_venue")
                show_bowl_kind_dis_laws = st.checkbox("Show Bowl Pace", value=True, key="dis_laws_bowl_kind")
                show_bowl_arm_dis_laws = st.checkbox("Show Bowl Arm", value=True, key="dis_laws_bowl_arm")
                
            try:
                fig_dis_laws = dismissal_plot(
                    df=df,
                    player_name=selected_player_value,
                    pid=selected_pid,
                    inns=selected_inns,
                    mat_num=selected_mat_num,
                    team_bat=selected_team_value,
                    team_bowl=selected_team_bowl_value,
                    bowler_name=bowler_name,
                    bowler_id=bowler_id,
                    competition=selected_competition_value,
                    transparent=False,
                    over_values=over_values,
                    phase=phase,
                    ground=selected_ground,
                    mcode=selected_mcode,
                    date_from=date_from,
                    date_to=date_to,
                    title_components=title_components if show_title_dis_laws else [],
                    bat_hand=bat_hand,
                    bowl_type=["Left Arm Wrist Spin"],
                    bowl_kind=bowl_kind,
                    bowl_arm=bowl_arm,
                    show_title=show_title_dis_laws,
                    show_summary=show_summary_dis_laws,
                    show_shots_breakdown=show_shots_breakdown_dis_laws,
                    shots_breakdown_options=shots_breakdown_options_dis_laws,
                    runs_count=runs_count_dis_laws,
                    show_fours_sixes=show_fours_sixes_dis_laws,
                    show_control=show_control_dis_laws,
                    show_prod_shot=show_prod_shot_dis_laws,
                    show_bowler=show_bowler_dis_laws,
                    show_ground=show_ground_dis_laws,
                    show_venue=show_venue_dis_laws,
                    show_overs=show_overs_dis_laws,
                    show_phase=show_phase_dis_laws,
                    show_bowl_type=show_bowl_type_dis_laws,
                    show_bowl_kind=show_bowl_kind_dis_laws,
                    show_bowl_arm=show_bowl_arm_dis_laws
                )
                with col2:
                    st.pyplot(fig_dis_laws)
            except Exception as e:
                st.error(f"Error generating dismissal plot: {str(e)}")
                fig_dis_laws = None
            
            with col3:
                if fig_dis_laws:
                    buf = BytesIO()
                    fig_dis_laws.savefig(buf, format="png", transparent=False, dpi=300, bbox_inches='tight')
                    buf.seek(0)
                    st.download_button(
                        label="📅 Download Plot as PNG",
                        data=buf.getvalue(),
                        file_name=f"{selected_player}_dis_laws.png",
                        mime="image/png",
                        key="dis_laws_download"
                    )

        if "━━ Dis Plot - All Arm" in plot_types:
            st.markdown("<h2 style='text-align: center;'>Dismissal Plot - All Bowling Arms</h2>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([2, 2, 2])
            
            with col1:
                st.markdown("## Customize Plot Info")
                show_title_dis_all_arm = st.checkbox("Show Plot Title", value=True, key="dis_all_arm_title")
                show_summary_dis_all_arm = st.checkbox("Show Runs Summary", value=True, key="dis_all_arm_summary")
                show_shots_breakdown_dis_all_arm = st.checkbox("Show Shots Breakdown", value=True, key="dis_all_arm_shots_breakdown")
                if show_shots_breakdown_dis_all_arm:
                    shots_breakdown_options_dis_all_arm = st.multiselect(
                        "Shots to Display",
                        options=['0s', '1s', '2s', '3s', '4s', '6s'],
                        default=['0s', '1s', '2s', '4s', '6s'],
                        key="dis_all_arm_shots_options"
                    )
                else:
                    shots_breakdown_options_dis_all_arm = []
                runs_count_dis_all_arm = st.checkbox("Show Runs Count", value=True, key="dis_all_arm_runs")
                show_fours_sixes_dis_all_arm = st.checkbox("Show 4s and 6s", value=True, key="dis_all_arm_fs")
                show_bowler_dis_all_arm = st.checkbox("Show Bowler", value=True, key="dis_all_arm_bowler")
                show_control_dis_all_arm = st.checkbox("Show Control %", value=True, key="dis_all_arm_control")
                show_prod_shot_dis_all_arm = st.checkbox("Show Productive Shot", value=True, key="dis_all_arm_prod")
                show_overs_dis_all_arm = st.checkbox("Show Overs", value=True, key="dis_all_arm_overs")
                show_phase_dis_all_arm = st.checkbox("Show Phase", value=True, key="dis_all_arm_phase")
                show_bowl_type_dis_all_arm = st.checkbox("Show Bowl Type", value=True, key="dis_all_arm_bowl_type")
                show_ground_dis_all_arm = st.checkbox("Show Ground", value=True, key="dis_all_arm_ground")
                show_venue_dis_all_arm = st.checkbox("Show Venue", value=True, key="dis_all_arm_venue")
                show_bowl_kind_dis_all_arm = st.checkbox("Show Bowl Pace", value=True, key="dis_all_arm_bowl_kind")
                show_bowl_arm_dis_all_arm = st.checkbox("Show Bowl Arm", value=True, key="dis_all_arm_bowl_arm")
                
            try:
                fig_dis_all_arm = dismissal_plot(
                    df=df,
                    player_name=selected_player_value,
                    pid=selected_pid,
                    inns=selected_inns,
                    mat_num=selected_mat_num,
                    team_bat=selected_team_value,
                    team_bowl=selected_team_bowl_value,
                    bowler_name=bowler_name,
                    bowler_id=bowler_id,
                    competition=selected_competition_value,
                    transparent=False,
                    over_values=over_values,
                    phase=phase,
                    ground=selected_ground,
                    mcode=selected_mcode,
                    date_from=date_from,
                    date_to=date_to,
                    title_components=title_components if show_title_dis_all_arm else [],
                    bat_hand=bat_hand,
                    bowl_type=bowl_type,
                    bowl_kind=bowl_kind,
                    bowl_arm=None,
                    show_title=show_title_dis_all_arm,
                    show_summary=show_summary_dis_all_arm,
                    show_shots_breakdown=show_shots_breakdown_dis_all_arm,
                    shots_breakdown_options=shots_breakdown_options_dis_all_arm,
                    runs_count=runs_count_dis_all_arm,
                    show_fours_sixes=show_fours_sixes_dis_all_arm,
                    show_control=show_control_dis_all_arm,
                    show_prod_shot=show_prod_shot_dis_all_arm,
                    show_bowler=show_bowler_dis_all_arm,
                    show_ground=show_ground_dis_all_arm,
                    show_venue=show_venue_dis_all_arm,
                    show_overs=show_overs_dis_all_arm,
                    show_phase=show_phase_dis_all_arm,
                    show_bowl_type=show_bowl_type_dis_all_arm,
                    show_bowl_kind=show_bowl_kind_dis_all_arm,
                    show_bowl_arm=show_bowl_arm_dis_all_arm
                )
                with col2:
                    st.pyplot(fig_dis_all_arm)
            except Exception as e:
                st.error(f"Error generating dismissal plot: {str(e)}")
                fig_dis_all_arm = None
            
            with col3:
                if fig_dis_all_arm:
                    buf = BytesIO()
                    fig_dis_all_arm.savefig(buf, format="png", transparent=False, dpi=300, bbox_inches='tight')
                    buf.seek(0)
                    st.download_button(
                        label="📅 Download Plot as PNG",
                        data=buf.getvalue(),
                        file_name=f"{selected_player}_dis_all_arm.png",
                        mime="image/png",
                        key="dis_all_arm_download"
                    )

        if "━━ Dis Plot - Right Arm" in plot_types:
            st.markdown("<h2 style='text-align: center;'>Dismissal Plot - Right Arm</h2>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([2, 2, 2])
            
            with col1:
                st.markdown("## Customize Plot Info")
                show_title_dis_right_arm = st.checkbox("Show Plot Title", value=True, key="dis_right_arm_title")
                show_summary_dis_right_arm = st.checkbox("Show Runs Summary", value=True, key="dis_right_arm_summary")
                show_shots_breakdown_dis_right_arm = st.checkbox("Show Shots Breakdown", value=True, key="dis_right_arm_shots_breakdown")
                if show_shots_breakdown_dis_right_arm:
                    shots_breakdown_options_dis_right_arm = st.multiselect(
                        "Shots to Display",
                        options=['0s', '1s', '2s', '3s', '4s', '6s'],
                        default=['0s', '1s', '2s', '4s', '6s'],
                        key="dis_right_arm_shots_options"
                    )
                else:
                    shots_breakdown_options_dis_right_arm = []
                runs_count_dis_right_arm = st.checkbox("Show Runs Count", value=True, key="dis_right_arm_runs")
                show_fours_sixes_dis_right_arm = st.checkbox("Show 4s and 6s", value=True, key="dis_right_arm_fs")
                show_bowler_dis_right_arm = st.checkbox("Show Bowler", value=True, key="dis_right_arm_bowler")
                show_control_dis_right_arm = st.checkbox("Show Control %", value=True, key="dis_right_arm_control")
                show_prod_shot_dis_right_arm = st.checkbox("Show Productive Shot", value=True, key="dis_right_arm_prod")
                show_overs_dis_right_arm = st.checkbox("Show Overs", value=True, key="dis_right_arm_overs")
                show_phase_dis_right_arm = st.checkbox("Show Phase", value=True, key="dis_right_arm_phase")
                show_bowl_type_dis_right_arm = st.checkbox("Show Bowl Type", value=True, key="dis_right_arm_bowl_type")
                show_ground_dis_right_arm = st.checkbox("Show Ground", value=True, key="dis_right_arm_ground")
                show_venue_dis_right_arm = st.checkbox("Show Venue", value=True, key="dis_right_arm_venue")
                show_bowl_kind_dis_right_arm = st.checkbox("Show Bowl Pace", value=True, key="dis_right_arm_bowl_kind")
                show_bowl_arm_dis_right_arm = st.checkbox("Show Bowl Arm", value=True, key="dis_right_arm_bowl_arm")
                
            try:
                fig_dis_right_arm = dismissal_plot(
                    df=df,
                    player_name=selected_player_value,
                    pid=selected_pid,
                    inns=selected_inns,
                    mat_num=selected_mat_num,
                    team_bat=selected_team_value,
                    team_bowl=selected_team_bowl_value,
                    bowler_name=bowler_name,
                    bowler_id=bowler_id,
                    competition=selected_competition_value,
                    transparent=False,
                    over_values=over_values,
                    phase=phase,
                    ground=selected_ground,
                    mcode=selected_mcode,
                    date_from=date_from,
                    date_to=date_to,
                    title_components=title_components if show_title_dis_right_arm else [],
                    bat_hand=bat_hand,
                    bowl_type=bowl_type,
                    bowl_kind=bowl_kind,
                    bowl_arm=["Right Arm"],
                    show_title=show_title_dis_right_arm,
                    show_summary=show_summary_dis_right_arm,
                    show_shots_breakdown=show_shots_breakdown_dis_right_arm,
                    shots_breakdown_options=shots_breakdown_options_dis_right_arm,
                    runs_count=runs_count_dis_right_arm,
                    show_fours_sixes=show_fours_sixes_dis_right_arm,
                    show_control=show_control_dis_right_arm,
                    show_prod_shot=show_prod_shot_dis_right_arm,
                    show_bowler=show_bowler_dis_right_arm,
                    show_ground=show_ground_dis_right_arm,
                    show_venue=show_venue_dis_right_arm,
                    show_overs=show_overs_dis_right_arm,
                    show_phase=show_phase_dis_right_arm,
                    show_bowl_type=show_bowl_type_dis_right_arm,
                    show_bowl_kind=show_bowl_kind_dis_right_arm,
                    show_bowl_arm=show_bowl_arm_dis_right_arm
                )
                with col2:
                    st.pyplot(fig_dis_right_arm)
            except Exception as e:
                st.error(f"Error generating dismissal plot: {str(e)}")
                fig_dis_right_arm = None
            
            with col3:
                if fig_dis_right_arm:
                    buf = BytesIO()
                    fig_dis_right_arm.savefig(buf, format="png", transparent=False, dpi=300, bbox_inches='tight')
                    buf.seek(0)
                    st.download_button(
                        label="📅 Download Plot as PNG",
                        data=buf.getvalue(),
                        file_name=f"{selected_player}_dis_right_arm.png",
                        mime="image/png",
                        key="dis_right_arm_download"
                    )

        if "━━ Dis Plot - Left Arm" in plot_types:
            st.markdown("<h2 style='text-align: center;'>Dismissal Plot - Left Arm</h2>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([2, 2, 2])
            
            with col1:
                st.markdown("## Customize Plot Info")
                show_title_dis_left_arm = st.checkbox("Show Plot Title", value=True, key="dis_left_arm_title")
                show_summary_dis_left_arm = st.checkbox("Show Runs Summary", value=True, key="dis_left_arm_summary")
                show_shots_breakdown_dis_left_arm = st.checkbox("Show Shots Breakdown", value=True, key="dis_left_arm_shots_breakdown")
                if show_shots_breakdown_dis_left_arm:
                    shots_breakdown_options_dis_left_arm = st.multiselect(
                        "Shots to Display",
                        options=['0s', '1s', '2s', '3s', '4s', '6s'],
                        default=['0s', '1s', '2s', '4s', '6s'],
                        key="dis_left_arm_shots_options"
                    )
                else:
                    shots_breakdown_options_dis_left_arm = []
                runs_count_dis_left_arm = st.checkbox("Show Runs Count", value=True, key="dis_left_arm_runs")
                show_fours_sixes_dis_left_arm = st.checkbox("Show 4s and 6s", value=True, key="dis_left_arm_fs")
                show_bowler_dis_left_arm = st.checkbox("Show Bowler", value=True, key="dis_left_arm_bowler")
                show_control_dis_left_arm = st.checkbox("Show Control %", value=True, key="dis_left_arm_control")
                show_prod_shot_dis_left_arm = st.checkbox("Show Productive Shot", value=True, key="dis_left_arm_prod")
                show_overs_dis_left_arm = st.checkbox("Show Overs", value=True, key="dis_left_arm_overs")
                show_phase_dis_left_arm = st.checkbox("Show Phase", value=True, key="dis_left_arm_phase")
                show_bowl_type_dis_left_arm = st.checkbox("Show Bowl Type", value=True, key="dis_left_arm_bowl_type")
                show_ground_dis_left_arm = st.checkbox("Show Ground", value=True, key="dis_left_arm_ground")
                show_venue_dis_left_arm = st.checkbox("Show Venue", value=True, key="dis_left_arm_venue")
                show_bowl_kind_dis_left_arm = st.checkbox("Show Bowl Pace", value=True, key="dis_left_arm_bowl_kind")
                show_bowl_arm_dis_left_arm = st.checkbox("Show Bowl Arm", value=True, key="dis_left_arm_bowl_arm")
                
            try:
                fig_dis_left_arm = dismissal_plot(
                    df=df,
                    player_name=selected_player_value,
                    pid=selected_pid,
                    inns=selected_inns,
                    mat_num=selected_mat_num,
                    team_bat=selected_team_value,
                    team_bowl=selected_team_bowl_value,
                    bowler_name=bowler_name,
                    bowler_id=bowler_id,
                    competition=selected_competition_value,
                    transparent=False,
                    over_values=over_values,
                    phase=phase,
                    ground=selected_ground,
                    mcode=selected_mcode,
                    date_from=date_from,
                    date_to=date_to,
                    title_components=title_components if show_title_dis_left_arm else [],
                    bat_hand=bat_hand,
                    bowl_type=bowl_type,
                    bowl_kind=bowl_kind,
                    bowl_arm=["Left Arm"],
                    show_title=show_title_dis_left_arm,
                    show_summary=show_summary_dis_left_arm,
                    show_shots_breakdown=show_shots_breakdown_dis_left_arm,
                    shots_breakdown_options=shots_breakdown_options_dis_left_arm,
                    runs_count=runs_count_dis_left_arm,
                    show_fours_sixes=show_fours_sixes_dis_left_arm,
                    show_control=show_control_dis_left_arm,
                    show_prod_shot=show_prod_shot_dis_left_arm,
                    show_bowler=show_bowler_dis_left_arm,
                    show_ground=show_ground_dis_left_arm,
                    show_venue=show_venue_dis_left_arm,
                    show_overs=show_overs_dis_left_arm,
                    show_phase=show_phase_dis_left_arm,
                    show_bowl_type=show_bowl_type_dis_left_arm,
                    show_bowl_kind=show_bowl_kind_dis_left_arm,
                    show_bowl_arm=show_bowl_arm_dis_left_arm
                )
                with col2:
                    st.pyplot(fig_dis_left_arm)
            except Exception as e:
                st.error(f"Error generating dismissal plot: {str(e)}")
                fig_dis_left_arm = None
            
            with col3:
                if fig_dis_left_arm:
                    buf = BytesIO()
                    fig_dis_left_arm.savefig(buf, format="png", transparent=False, dpi=300, bbox_inches='tight')
                    buf.seek(0)
                    st.download_button(
                        label="📅 Download Plot as PNG",
                        data=buf.getvalue(),
                        file_name=f"{selected_player}_dis_left_arm.png",
                        mime="image/png",
                        key="dis_left_arm_download"
                    )

        # ZIP Download Section
        # After all 8 plot sections
    # ===== DOWNLOAD ALL PLOTS AS ZIP =====""
    if plot_types:
        st.markdown("---")
        st.markdown("### 📦 Download All Generated Plots")
        
        # Collect all generated figures
        all_figures = {}
        
        if fig_spike is not None:
            all_figures[f"{selected_player}_wagon_wheel"] = fig_spike
            
        if fig_spike_trans is not None:
            all_figures[f"{selected_player}_wagon_wheel_trans"] = fig_spike_trans
            
        if fig_spike_desc is not None:
            all_figures[f"{selected_player}_wagon_wheel"] = fig_spike_desc
        
        if fig_spike_desc_pace is not None:
            all_figures[f"{selected_player}_wagon_wheel_vs_pace"] = fig_spike_desc_pace
        
        if fig_spike_desc_spin is not None:
            all_figures[f"{selected_player}_wagon_wheel_vs_spin"] = fig_spike_desc_spin
            
        if fig_wagon is not None:
            all_figures[f"{selected_player}_wagon_plot"] = fig_wagon
            
        if fig_wagon_trans is not None:
            all_figures[f"{selected_player}_wagon_zone_transparent"] = fig_wagon_trans
            
        if fig_wagon_desc is not None:
            all_figures[f"{selected_player}_wagon_zone_descriptive"] = fig_wagon_desc
            
        if fig_spike_desc_trans is not None:
            all_figures[f"{selected_player}_wagon_wheel_descriptive_transparent"] = fig_spike_desc_trans
            
        if fig_wagon_desc_trans is not None:
            all_figures[f"{selected_player}_wagon_zone_descriptive_transparent"] = fig_wagon_desc_trans
        
        if fig_dismissal is not None:
            all_figures[f"{selected_player}_dismissal_plot"] = fig_dismissal
            
        if fig_dismissal_trans is not None:
            all_figures[f"{selected_player}_dismissal_plot_transparent"] = fig_dismissal_trans
        
        if fig_whl_phs_all is not None:
            all_figures[f"{selected_player}_whl_phase_all"] = fig_whl_phs_all
        
        if fig_whl_phs_pp is not None:
            all_figures[f"{selected_player}_whl_phase_powerplay"] = fig_whl_phs_pp
        
        if fig_whl_phs_mid is not None:
            all_figures[f"{selected_player}_whl_phase_middle"] = fig_whl_phs_mid
        
        if fig_whl_phs_slog is not None:
            all_figures[f"{selected_player}_whl_phase_slog"] = fig_whl_phs_slog
        
        if fig_whl_all_kind is not None:
            all_figures[f"{selected_player}_whl_all_kind"] = fig_whl_all_kind
        
        if fig_whl_all_type is not None:
            all_figures[f"{selected_player}_whl_all_type"] = fig_whl_all_type
        
        if fig_whl_rap is not None:
            all_figures[f"{selected_player}_whl_rap"] = fig_whl_rap
        
        if fig_whl_rafs is not None:
            all_figures[f"{selected_player}_whl_rafs"] = fig_whl_rafs
        
        if fig_whl_raws is not None:
            all_figures[f"{selected_player}_whl_raws"] = fig_whl_raws
        
        if fig_whl_lap is not None:
            all_figures[f"{selected_player}_whl_lap"] = fig_whl_lap
        
        if fig_whl_lafs is not None:
            all_figures[f"{selected_player}_whl_lafs"] = fig_whl_lafs
        
        if fig_whl_laws is not None:
            all_figures[f"{selected_player}_whl_laws"] = fig_whl_laws
        
        if fig_whl_all_arm is not None:
            all_figures[f"{selected_player}_whl_all_arm"] = fig_whl_all_arm
        
        if fig_whl_right_arm is not None:
            all_figures[f"{selected_player}_whl_right_arm"] = fig_whl_right_arm
        
        if fig_whl_left_arm is not None:
            all_figures[f"{selected_player}_whl_left_arm"] = fig_whl_left_arm
        
        if fig_wzn_all_type is not None:
            all_figures[f"{selected_player}_wzn_all_type"] = fig_wzn_all_type
        
        if fig_wzn_pace is not None:
            all_figures[f"{selected_player}_wzn_pace"] = fig_wzn_pace
        
        if fig_wzn_spin is not None:
            all_figures[f"{selected_player}_wzn_spin"] = fig_wzn_spin
        
        if fig_wzn_all_phase is not None:
            all_figures[f"{selected_player}_wzn_all_phase"] = fig_wzn_all_phase
        
        if fig_wzn_pp is not None:
            all_figures[f"{selected_player}_wzn_pp"] = fig_wzn_pp
        
        if fig_wzn_mid is not None:
            all_figures[f"{selected_player}_wzn_mid"] = fig_wzn_mid
        
        if fig_wzn_slog is not None:
            all_figures[f"{selected_player}_wzn_slog"] = fig_wzn_slog
        
        if fig_wzn_all_kind is not None:
            all_figures[f"{selected_player}_wzn_all_kind"] = fig_wzn_all_kind
        
        if fig_wzn_rap is not None:
            all_figures[f"{selected_player}_wzn_rap"] = fig_wzn_rap
        
        if fig_wzn_rafs is not None:
            all_figures[f"{selected_player}_wzn_rafs"] = fig_wzn_rafs
        
        if fig_wzn_raws is not None:
            all_figures[f"{selected_player}_wzn_raws"] = fig_wzn_raws
        
        if fig_wzn_lap is not None:
            all_figures[f"{selected_player}_wzn_lap"] = fig_wzn_lap
        
        if fig_wzn_lafs is not None:
            all_figures[f"{selected_player}_wzn_lafs"] = fig_wzn_lafs
        
        if fig_wzn_laws is not None:
            all_figures[f"{selected_player}_wzn_laws"] = fig_wzn_laws
        
        if fig_wzn_all_arm is not None:
            all_figures[f"{selected_player}_wzn_all_arm"] = fig_wzn_all_arm
        
        if fig_wzn_right_arm is not None:
            all_figures[f"{selected_player}_wzn_right_arm"] = fig_wzn_right_arm
        
        if fig_wzn_left_arm is not None:
            all_figures[f"{selected_player}_wzn_left_arm"] = fig_wzn_left_arm
        
        if fig_dis_all_type is not None:
            all_figures[f"{selected_player}_dis_all_type"] = fig_dis_all_type
        
        if fig_dis_pace is not None:
            all_figures[f"{selected_player}_dis_pace"] = fig_dis_pace
        
        if fig_dis_spin is not None:
            all_figures[f"{selected_player}_dis_spin"] = fig_dis_spin
        
        if fig_dis_all_phase is not None:
            all_figures[f"{selected_player}_dis_all_phase"] = fig_dis_all_phase
        
        if fig_dis_pp is not None:
            all_figures[f"{selected_player}_dis_pp"] = fig_dis_pp
        
        if fig_dis_mid is not None:
            all_figures[f"{selected_player}_dis_mid"] = fig_dis_mid
        
        if fig_dis_slog is not None:
            all_figures[f"{selected_player}_dis_slog"] = fig_dis_slog
        
        if fig_dis_all_kind is not None:
            all_figures[f"{selected_player}_dis_all_kind"] = fig_dis_all_kind
        
        if fig_dis_rap is not None:
            all_figures[f"{selected_player}_dis_rap"] = fig_dis_rap
        
        if fig_dis_rafs is not None:
            all_figures[f"{selected_player}_dis_rafs"] = fig_dis_rafs
        
        if fig_dis_raws is not None:
            all_figures[f"{selected_player}_dis_raws"] = fig_dis_raws
        
        if fig_dis_lap is not None:
            all_figures[f"{selected_player}_dis_lap"] = fig_dis_lap
        
        if fig_dis_lafs is not None:
            all_figures[f"{selected_player}_dis_lafs"] = fig_dis_lafs
        
        if fig_dis_laws is not None:
            all_figures[f"{selected_player}_dis_laws"] = fig_dis_laws
        
        if fig_dis_all_arm is not None:
            all_figures[f"{selected_player}_dis_all_arm"] = fig_dis_all_arm
        
        if fig_dis_right_arm is not None:
            all_figures[f"{selected_player}_dis_right_arm"] = fig_dis_right_arm
        
        if fig_dis_left_arm is not None:
            all_figures[f"{selected_player}_dis_left_arm"] = fig_dis_left_arm
        
        if all_figures:
            player_text = selected_player if selected_player != "All" else "AllPlayers"
            zip_filename = f"{player_text}_Cricket_Plots.zip"
            
            zip_buffer = create_zip_of_plots(all_figures)
            
            st.download_button(
                label=f"📦 Download All Plots as ZIP ({len(all_figures)} plots)",
                data=zip_buffer.getvalue(),
                file_name=zip_filename,
                mime="application/zip",
                key="download_all_zip",
                use_container_width=True
            )
            
            st.info(f"Ready to download {len(all_figures)} plot(s)")

else:
    st.info("Please select a dataset source to begin.")
