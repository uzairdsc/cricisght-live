# Live Wagon Plots

## Overview
Password-protected Streamlit dashboard for live cricket ball-by-ball analysis. It generates wagon wheels, wagon zones, and dismissal plots with filters for player, team, venue, phase, and date range. Batch plot generation is also supported.

## Data Sources
- CSV upload
- S3
- Local cache files
- Squad files for batch plot generation

## Usage
1. Open the app in Streamlit
2. Load a dataset from the sidebar
3. Select filters and plot types
4. Generate plots or batch outputs
5. Download individual figures or the batch ZIP file

## Requirements
- `streamlit`
- `pandas`
- `numpy`
- `matplotlib`
- `boto3`

