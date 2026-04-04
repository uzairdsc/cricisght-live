# spike plot
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from io import BytesIO
import matplotlib.image as mpimg


#  dismissal plot
def dismissal_plot(
    df, player_name=None, pid=None, inns=None, mat_num = None, team_bat=None, team_bowl=None,
    bowler_name=None, competition=None, date_from=None, date_to=None,
    transparent=False, over_values=None, phase=None, bowler_id=None, ground=None, mcode=None,
    title_components=["title", "filters"], shots_breakdown_options=['0s', '1s', '2s', '3s', '4s', '6s'],
    bat_hand=None , bowl_type=None, bowl_kind=None, bowl_arm=None,
    show_title=True,  show_summary=True, show_shots_breakdown=True,
    show_fours_sixes=True, show_control=True, show_prod_shot=True, 
    show_bowl_type=True, show_bowl_kind=True, show_bowl_arm=True, show_venue=False,
    runs_count=True, show_bowler=True, show_ground=True, show_overs=True, show_phase=True
):
    # score_colors = {
    #     0:  "#706B6C",   
    #     1:  "#FF5733",   
    #     2:  '#1F51FF',   
    #     3:  '#D16FBC',   
    #     4:  '#0B9B67',
    #     5:  '#FFA500',   
    #     6:  '#7A41D8',   
    # }

    local_df = df.copy()

    # Filter by PID if provided (takes priority)
    if pid is not None:
        # local_df = local_df[local_df['p_bat'] == pid]
        local_df = local_df[local_df['p_bat'].astype(str) == str(pid)]

        # Auto-get player name from PID for display
        if not local_df.empty and player_name is None:
            player_name = local_df['bat'].iloc[0]
    # Otherwise filter by player name
    elif player_name is not None:
        local_df = local_df[local_df['bat'] == player_name]

    # if player_name is not None:
    #     local_df = df[
    #         (df['bat'] == player_name)
    #     ].copy()
    # else:
    #     local_df = df.copy()

    if mat_num is not None:
        local_df = local_df[local_df['p_match'] == mat_num]

    # if inns is not None:
    #     local_df = local_df[local_df['inns'] == inns]

    if inns is not None and len(inns) > 0:
        local_df = local_df[local_df['inns'].isin(inns)]

        
    # if team_bat is not None and team_bat != "All":
    #     local_df = local_df[local_df['team_bat'] == team_bat]

    # if team_bowl is not None and team_bowl != "All":
    #     local_df = local_df[local_df['team_bowl'] == team_bowl]

    if team_bat is not None and len(team_bat) > 0:
        local_df = local_df[local_df['team_bat'].isin(team_bat)]

    if team_bowl is not None and len(team_bowl) > 0:
        local_df = local_df[local_df['team_bowl'].isin(team_bowl)]

    # ADD THIS:
    if competition:
        local_df = local_df[local_df['competition'] == competition]
    
    # Filter by specific overs
    if over_values is not None:
        local_df = local_df[local_df['over'].isin(over_values)]

    # Phase filter (takes priority over over_values if both provided)
    # if phase is not None:
    #     if phase == 1 or phase == "Powerplay":
    #         local_df = local_df[local_df['over'].between(1, 6)]
    #     elif phase == 2 or phase == "Middle":
    #         local_df = local_df[local_df['over'].between(7, 15)]
    #     elif phase == 3 or phase == "Death":
    #         local_df = local_df[local_df['over'].between(16, 20)]

    if phase is not None and len(phase) > 0:
        mask = pd.Series([False] * len(local_df), index=local_df.index)
        if 1 in phase:
            mask |= local_df['over'].between(1, 6)
        if 2 in phase:
            mask |= local_df['over'].between(7, 15)
        if 3 in phase:
            mask |= local_df['over'].between(16, 20)
        local_df = local_df[mask]

    # Date range filter
    if date_from is not None:
        local_df = local_df[local_df['date'] >= pd.to_datetime(date_from)]

    if date_to is not None:
        local_df = local_df[local_df['date'] <= pd.to_datetime(date_to)]

    #ground filter
    # if ground is not None:
    #     local_df = local_df[local_df['ground'] == ground]

    if ground is not None and len(ground) > 0:
        local_df = local_df[local_df['ground'].isin(ground)]


    # if bat_hand is not None:
    #     local_df = local_df[local_df['bat_hand'] == bat_hand]
    if bat_hand is not None and len(bat_hand) > 0:
        local_df = local_df[local_df['bat_hand'].isin(bat_hand)]

    # if bowl_type is not None:
    #     local_df = local_df[local_df['bowl_type'] == bowl_type]

    # if bowl_kind is not None:
    #     local_df = local_df[local_df['bowl_kind'] == bowl_kind]
        
    # if bowl_arm is not None:
    #     local_df = local_df[local_df['bowl_arm'] == bowl_arm]

    # updated multiselect logic
    # 2. Update filtering logic
    if bowl_type is not None and len(bowl_type) > 0:
        local_df = local_df[local_df['bowl_type'].isin(bowl_type)]

    if bowl_kind is not None and len(bowl_kind) > 0:
        local_df = local_df[local_df['bowl_kind'].isin(bowl_kind)]

    if bowl_arm is not None and len(bowl_arm) > 0:
        local_df = local_df[local_df['bowl_arm'].isin(bowl_arm)]


    #match code like PAK v NED
    # if mcode is not None:
    #     local_df = local_df[local_df['mcode'] == mcode]
    if mcode is not None and len(mcode) > 0:
        local_df = local_df[local_df['mcode'].isin(mcode)]

    # === Total Innings Summary ===
    # innings_valid_balls = local_df[local_df['wides'] == 0]
    # innings_runs = innings_valid_balls['batsmanRuns'].sum()
    # innings_balls = innings_valid_balls.shape[0]


    if bowler_id is not None:
        local_df = local_df[local_df['p_bowl'] == bowler_id]

        if not local_df.empty and bowler_name is None:
            bowler_name = local_df['bowl'].iloc[0]
    # Otherwise filter by bowler name
    elif bowler_name is not None:
        local_df = local_df[local_df['bowl'] == bowler_name]

    if bowler_name:
        local_df = local_df[local_df['bowl'] == bowler_name]

    # innings_valid_balls = local_df[local_df['wide'] == 0]

    # if player_name is None:
    #     innings_runs = innings_valid_balls['score'].sum()
    # else:
    #     innings_runs = innings_valid_balls['batruns'].sum()

    # innings_balls = innings_valid_balls.shape[0]
    if player_name is None:
        innings_valid_balls = local_df.copy()  # include all for team
        innings_runs = innings_valid_balls['score'].sum() #score
    else:
        innings_valid_balls = local_df[local_df['wide'] == 0]
        innings_runs = innings_valid_balls['batruns'].sum() #batruns

    innings_balls = innings_valid_balls.shape[0]
    
    # innings_4s = innings_valid_balls['isFour'].sum()
    # innings_6s = innings_valid_balls['isSix'].sum()
    
    innings_4s = (innings_valid_balls['outcome'] == 'four').sum()
    innings_6s = (innings_valid_balls['outcome'] == 'six').sum()

    innings_0s = (innings_valid_balls['batruns'] == 0).sum()
    innings_1s = (innings_valid_balls['batruns'] == 1).sum()
    innings_2s = (innings_valid_balls['batruns'] == 2).sum()
    innings_3s = (innings_valid_balls['batruns'] == 3).sum()
    
    # Get unique batting teams
    batting_teams = local_df['team_bat'].dropna().unique()
    all_teams = pd.concat([local_df['team_bat'], local_df['team_bowl']]).dropna().unique()

    # # Calculate bowling team based on filtered team_bat
    # if len(batting_teams) == 0:
    #     team_bowl = "UNKNOWN"
    # else:
    #     bowling_teams = [team for team in all_teams if team not in batting_teams]
    #     if len(bowling_teams) == 1:
    #         team_bowl = bowling_teams[0]
    #     elif len(bowling_teams) > 1:
    #         team_bowl = "/".join(sorted(set(bowling_teams)))
    #     else:
    #         team_bowl = "ALL TEAMS"

    # Determine team names - Updated logic
    # (Commented out to preserve original team_bowl selection for title display)
    # if not local_df.empty:
    #     team_bats = local_df['team_bat'].unique() 
    #     if len(team_bats) == 1:
    #         team_bat = team_bats[0]
    #         # Filter by the same match to get correct opponent
    #         if mat_num is not None and mat_num != "All Matches":  # ✅ ADD THIS CHECK
    #             match_df = df[df['p_match'] == mat_num]
    #         else:
    #             match_df = local_df
    #         
    #         # Get opponent from the same match
    #         team_bowls_in_match = match_df['team_bowl'].unique()
    #         opponents = [t for t in team_bowls_in_match if t != team_bat]  # ✅ STORE AS LIST
    #         
    #         if len(opponents) == 1:  # ✅ CHECK LIST LENGTH
    #             team_bowl = opponents[0]
    #         elif len(opponents) > 1:  # ✅ MULTIPLE OPPONENTS
    #             team_bowl = "All Teams"
    #         else:
    #             team_bowl = "Opponents"
    #     else:
    #         team_bowl = "All Teams"
    # else:
    #     team_bowl = "All Teams"

    # --- Updated team_bowl logic: always use unique from filtered data ---
    unique_bowling_teams = local_df['team_bowl'].dropna().unique()
    if len(unique_bowling_teams) == 1:
        team_bowl = unique_bowling_teams[0]
    elif len(unique_bowling_teams) > 1:
        team_bowl = "All Teams"
    else:
        team_bowl = "Opponents"


    
    # This keeps a copy of the full innings shot data (unfiltered)
    all_shots_data = local_df[
        ~((local_df['wagonX'] == 0) & (local_df['wagonY'] == 0))
    ][['wagonX', 'wagonY', 'score', 'batruns', 'outcome', 'control', 'shot']].dropna()

    # ADD THESE TWO LINES to create isFour and isSix:
    all_shots_data['isFour'] = (all_shots_data['outcome'] == 'four').astype(int)
    all_shots_data['isSix'] = (all_shots_data['outcome'] == 'six').astype(int)

    # === DISMISSAL FILTER (NEW) ===
    # Filter for dismissals only (disPlot == 1)
    # print(f"DEBUG: local_df shape before dismissal filter: {local_df.shape}")
    # print(f"DEBUG: 'disPlot' column exists: {'disPlot' in local_df.columns}")
    
    if 'disPlot' in local_df.columns:
        dismissal_df = local_df[local_df['disPlot'] == 1].copy()
        # print(f"DEBUG: dismissal_df shape after filter: {dismissal_df.shape}")
    else:
        print("ERROR: 'disPlot' column not found in dataframe!")
        dismissal_df = pd.DataFrame()  # Empty dataframe
    
    # Calculate dismissals count
    dismissals_count = len(dismissal_df)
    # print(f"DEBUG: dismissals_count = {dismissals_count}")

    # # Apply run filter (COMMENTED OUT - Not used for dismissal plot)
    # if run_values is None:
    #     filtered_df = local_df.copy()
    # else:
    #     filtered_df = local_df[local_df['batruns'].isin(run_values)]
    
    # Use dismissal_df instead of filtered_df
    filtered_df = dismissal_df.copy()

    # Shots without wides (based on filtered data now)
    # balls_faced_df = filtered_df[
    #     (filtered_df['wides'] == 0)
    # ][['batsmanName', 'wagonX', 'wagonY', 'teamRuns', 'batsmanRuns']].dropna()
    balls_faced_df = filtered_df[filtered_df['wide'] == 0].dropna(subset=['wagonX', 'wagonY'])


    # Handle run_values = None to include all run types

    # Filter valid shot points
    player_data = filtered_df[
        ~((filtered_df['wagonX'] == 0) & (filtered_df['wagonY'] == 0))
    ][['wagonX', 'wagonY', 'score', 'batruns', 'outcome', 'control', 'shot']].dropna()

    # print(f"DEBUG: player_data shape after extraction: {player_data.shape}")
    # if not player_data.empty:
        # print(f"DEBUG: player_data sample:\n{player_data.head()}")
        # print(f"DEBUG: player_data batruns unique values: {player_data['batruns'].unique()}")

    # ADD THESE TWO LINES:
    player_data['isFour'] = (player_data['outcome'] == 'four').astype(int)
    player_data['isSix'] = (player_data['outcome'] == 'six').astype(int)
    
    # if player_data.empty:
    #     print(f"No data found for {player_name} in this match and innings {inns} for selected runs {run_values}")
    #     return
    # if player_data.empty:
    #     player_data_sorted = pd.DataFrame()  # Set to empty for drawing logic below
    # else:
    #     player_data_sorted = player_data.sort_values(by='batsmanRuns')
    #     player_data['color'] = player_data['batsmanRuns'].map(score_colors).fillna('black')
    # if player_name is None:
    #     innings_valid_balls = local_df.copy()  # include all for team
    #     innings_runs = innings_valid_balls['score'].sum()
    # else:
    #     innings_valid_balls = local_df[local_df['wide'] == 0]
    #     innings_runs = innings_valid_balls['batruns'].sum()

    # innings_balls = innings_valid_balls[innings_valid_balls['wide'] == 0].shape[0]  # consistent valid balls



    # Final unified stats calculation
    if player_name is None:
        # Team-level stats (exclude wides only)
        valid_balls = local_df[local_df['wide'] == 0]
        valid_shots = valid_balls[~((valid_balls['wagonX'] == 0) & (valid_balls['wagonY'] == 0))]
        # ADD THESE TWO LINES:

        #testing lines
        valid_shots = valid_shots.copy()

        valid_shots['isFour'] = (valid_shots['outcome'] == 'four').astype(int)
        valid_shots['isSix'] = (valid_shots['outcome'] == 'six').astype(int)

        total_score = valid_shots['score'].sum()
        total_4s = valid_shots['isFour'].sum()
        total_6s = valid_shots['isSix'].sum()
        
        balls_faced = valid_balls.shape[0]

    else:
        # Player-level stats (exclude wides + keep only player's shots)
        valid_balls = local_df[(local_df['wide'] == 0) & (~local_df['control'].isna())]
        valid_shots = player_data  # already filtered with shot data
        # ADD THESE TWO LINES:
        valid_shots['isFour'] = (valid_shots['outcome'] == 'four').astype(int)
        valid_shots['isSix'] = (valid_shots['outcome'] == 'six').astype(int)

        total_score = valid_shots['batruns'].sum()
        total_4s = valid_shots['isFour'].sum()
        total_6s = valid_shots['isSix'].sum()
        # balls_faced = balls_faced_df.shape[0]

        balls_faced_df = valid_balls
        balls_faced = balls_faced_df.shape[0]

    if len(valid_balls) == 0:
        control_pct = 0.0
    else:
        # Convert mixed-type control column to numeric FIRST
        control_numeric = pd.to_numeric(valid_balls['control'], errors='coerce')
        # Now count all 1.0 values (regardless of original type)
        controlled = (control_numeric == 1).sum()
        control_pct = round(controlled / len(valid_balls) * 100, 2)
        # controlled_balls = valid_balls[valid_balls['shotControl'] == 1]
        # control_pct = round(len(controlled_balls) / len(valid_balls) * 100, 2)


    # controlled_balls = valid_balls[valid_balls['control'] ==1]
    # control_pct = round(len(controlled_balls) / len(valid_balls) * 100, 2)
    # valid_balls = df[
    #     (df['batsmanName'] == player_name) &
    #     (df['inningNumber'] == inns) &
    #     (df['wides'] == 0)
    # ]

    # if bowler_name:
    #     valid_balls = valid_balls[valid_balls['bowlerName'] == bowler_name]

    # control_pct = round((valid_balls['shotControl'] == 1).sum() / valid_balls.shape[0] * 100, 2)

    # total_runs_count = player_data['batsmanRuns'].sum() if runs_count else None
    # Most productive shot calculation
    if 'shot' in all_shots_data.columns and not all_shots_data.empty:
    # if 'shotType' in player_data.columns and not player_data.empty:
        # shot_summary = all_shots_data.groupby('shotType').agg({
        #     'batsmanRuns': 'sum',
        #     'isFour': 'sum',
        #     'isSix': 'sum'
        # }).sort_values(by='batsmanRuns', ascending=False)
        run_col = 'score' if player_name is None else 'batruns'

        shot_summary = all_shots_data.groupby('shot').agg({
            run_col: 'sum',
            'isFour': 'sum',
            'isSix': 'sum'
        }).sort_values(by=run_col, ascending=False)

        if not shot_summary.empty:
            top_shot = shot_summary.iloc[0]
            top_shot_type = shot_summary.index[0]
            most_prod_shot_text = (
                # f"{top_shot_type}: {int(top_shot['batsmanRuns'])} runs,\n"
                # f"{top_shot_type}: {int(top_shot[run_col])} runs,\n"
                f"{top_shot_type}: {int(top_shot[run_col])} runs, "
                f"4s: {int(top_shot['isFour'])}, 6s: {int(top_shot['isSix'])}"
            )
        else:
            most_prod_shot_text = "No productive shot data"
    else:
        most_prod_shot_text = "No shot type data"

    # === MOST LOOSE SHOT CALCULATION (NEW) ===
    # Calculate the shot type that led to most dismissals
    most_loose_shot_text = "No dismissal data"
    if 'shot' in dismissal_df.columns and not dismissal_df.empty:
        dismissal_shot_counts = dismissal_df['shot'].value_counts()
        
        if not dismissal_shot_counts.empty:
            most_loose_shot_type = dismissal_shot_counts.index[0]
            most_loose_shot_count = dismissal_shot_counts.iloc[0]
            most_loose_shot_text = (
                f"{most_loose_shot_type}"
                f" | dismissals: {int(most_loose_shot_count)}"
            )

    # Color map
    # score_colors = {
    #     # 0: '#A9A9A9',
    #     0: '#FFFFFF',   # White (dot balls)
    #     1: '#00C853',
    #     2: '#2979FF',
    #     3: '#FF9100',
    #     5: '#C62828',  # Dark Red
    #     4: '#D50000',
    #     6: '#AA00FF'
    # }

    # player_data['color'] = player_data['batsmanRuns'].map(score_colors).fillna('black')
    # OLD: Color by runs scored on dismissal ball
    # if not player_data.empty:
    #     player_data['color'] = player_data['batruns'].map(score_colors).fillna('black')
    # else:
    #     player_data['color'] = pd.Series(dtype='str')
    
    # NEW: All dismissal dots in red color
    if not player_data.empty:
        player_data['color'] = '#FD3531'   # Red color for all dismissals
        # player_data['color'] = '#e30702'  # Red color for all dismissals
    else:
        player_data['color'] = pd.Series(dtype='str')

    # Plot setup
    # fig, ax = plt.subplots(figsize=(7, 7))
    # ax.set_facecolor("white")
    fig, ax = plt.subplots(figsize=(7, 7), facecolor='none' if transparent else 'white')
    ax.set_facecolor('none' if transparent else 'white')
    center_x, center_y = 180, 164

     # Add background image
    if not transparent and show_ground:
        # bg_img = mpimg.imread("ground_high_res.png")
        try:
            # Try from streamlitapp folder (when importing from streamlitapp/)
            bg_img = mpimg.imread("streamlitapp/Ground_Group_24.png")
        except FileNotFoundError:
            try:
                # Try relative path (when running inside streamlitapp/)
                bg_img = mpimg.imread("Ground_Group_24.png")
            except FileNotFoundError:
                # Skip if image not found - don't crash the plot
                print("Warning: Ground image not found, continuing without background")
                bg_img = None
        
        if bg_img is not None:
            ax.imshow(bg_img, extent=[0, 360, 20, 360], aspect='auto', zorder=0)

    # Sort shots so 0s are drawn first, 6s last (so 6s are on top)
    player_data_sorted = player_data.sort_values(by='batruns')

    # # Optional: define different line widths based on run value (COMMENTED OUT - Not used for dismissal plot)
    # run_widths = {
    #     0: 1.5,
    #     1: 2.0,
    #     2: 2.0,
    #     3: 2.0,
    #     4: 3.0,
    #     5: 2.0,
    #     6: 3.0
    # }

    # # Draw the lines in sorted order (COMMENTED OUT - Replaced with scatter plot for dismissals)
    # # for _, row in player_data_sorted.iterrows():
    # #     lw = run_widths.get(row['batsmanRuns'], 1.0)  # default width = 1.0 if not defined
    # #     ax.plot(
    # #         [center_x, row['wagonX']], [center_y, row['wagonY']],
    # #         color=row['color'], linewidth=lw, alpha=0.8, zorder=1
    # #     )
    # if not player_data_sorted.empty:
    #     for _, row in player_data_sorted.iterrows():
    #         lw = run_widths.get(row['batruns'], 1.0)
    #         ax.plot(
    #             [center_x, row['wagonX']], [center_y, row['wagonY']],
    #             color=row['color'], linewidth=lw, alpha=0.8, zorder=1
    #         )
    # else:
    #     ax.text(180, 515, "No shots for selected run(s)", ha='center', fontsize=12, color='red', fontweight='bold')
    
    # === NEW: Draw dismissals as scatter dots ===
    if not player_data_sorted.empty:
        # print(f"DEBUG: Drawing {len(player_data_sorted)} dismissal dots")
        # print(f"DEBUG: Color values: {player_data_sorted['color'].unique()}")
        ax.scatter(
            player_data_sorted['wagonX'], 
            player_data_sorted['wagonY'],
            c=player_data_sorted['color'],
            s=50,  # Dot size
            alpha=0.8,
            zorder=2,
            edgecolors='#e30702',
            # edgecolors='black',
            linewidth=1.2
        )
    else:
        # print("DEBUG: player_data_sorted is EMPTY - showing error message")
        ax.text(180, 390, "No dismissals for selected filter(s)", ha='center', fontsize=12, color='red', fontweight='bold')

    # plot the point (dot) at batter position which is at 180, 164, not rectangle only dot
    #batter position dot
    batter_dot = plt.Circle((center_x, center_y), radius=4, edgecolor='black', facecolor='green', linewidth=0.2, zorder=2)
    ax.add_artist(batter_dot)
    
    

    # Quadrants
    def get_quadrant(x, y):
        angle = np.arctan2(y - center_y, x - center_x)
        degree = (np.degrees(angle) + 360) % 360
        return int(degree // 45)

    # player_data['quadrant'] = player_data.apply(
    #     lambda row: get_quadrant(row['wagonX'], row['wagonY']), axis=1
    # )
    if not player_data.empty:
        player_data['quadrant'] = player_data.apply(
            lambda row: get_quadrant(row['wagonX'], row['wagonY']), axis=1
        )
    else:
        player_data['quadrant'] = pd.Series(dtype='int')  # Just to prevent downstream errors

    # Quadrant scores
    quadrant_totals = [0] * 8
    total_score = 0
    for q in range(8):
        q_score = player_data[player_data['quadrant'] == q]['batruns'].sum()
        quadrant_totals[q] = q_score
        total_score += q_score

    # Layout
    # ax.set_xlim(-20, 380)
    # ax.set_ylim(-20, 410)
    # ax.set_xticks([]), ax.set_yticks([])
    # ax.set_xticklabels([]), ax.set_yticklabels([])
    # ax.set_aspect('equal', adjustable='box')
    # ax.set_title(f"{player_name} Spike Graph Wheel Innings: {inns}", fontsize=12)

    # ax.text(180, 360, f"Total Runs: {total_score} ({balls_faced_df.shape[0]} balls)",
    #         fontsize=11, ha='center', fontweight='bold')
    # ax.text(180, 375, f"4s: {total_4s} | 6s: {total_6s}",
    #         fontsize=11, ha='center', color='darkgreen')
    # ax.text(180, 390, f"Control: {control_pct}%",
    #         fontsize=11, ha='center', color='purple')
    # ax.text(180, 405, f"Most Productive Shot: {most_prod_shot_text}",
    #         fontsize=11, ha='center', color='navy')
    # ax.set_xlim(-20, 470)
    # ax.set_ylim(-30, 370)
    ax.set_xlim(-20, 380)
    ax.set_ylim(-30, 640)
    ax.set_xticks([]), ax.set_yticks([])
    ax.set_xticklabels([]), ax.set_yticklabels([])
    ax.set_aspect('equal', adjustable='box')

    if mat_num is None:
        mat_num = "All Mats"
    if inns is None:
        inns = "All Inns"
    if player_name is None:
        player_name = "All Players"
    # ADD THIS:
    if competition is None:
        competition = "All Comps"
    # if team_bats is None:
    #     team_bowl = "All Teams"
    # ax.set_title(f"{player_name} Spike Graph Wheel Innings: {inns}", fontsize=12)
    # if show_title:
    #     ax.set_title(f"{player_name} vs {team_bowl} | {competition} - Mat \'{mat_num}\', Inns: \'{inns}\'".upper(), fontsize=12, fontweight='bold',fontfamily='DejaVu Sans')
        # ax.set_title(f"{player_name} - {team_bats} vs {team_bowl} | Test: {test_num}, Inns: {inns}".upper(), fontsize=12, fontweight='bold',fontfamily='Segoe UI')
    # updated filter with teams names in plot
    if show_title:
        # Determine title display
        if player_name and player_name != "All Players":
            title_name = player_name
        else:
            # For team view, show both teams
            if not local_df.empty:
                batting_teams_display = local_df['team_bat'].unique()
                if len(batting_teams_display) == 1:
                    title_name = batting_teams_display[0]
                else:
                    title_name = "All Players"
            else:
                title_name = "All Players"

        # --- Enhanced team_bowl display logic ---
        # If team_bowl is a list, join all selected teams
        title_fontsize = 12
        if isinstance(team_bowl, list):
            if len(team_bowl) == 0:
                title_opponent = "All Teams"
            elif len(team_bowl) == 1:
                title_opponent = team_bowl[0]
            else:
                title_opponent = ", ".join(team_bowl)
                if len(team_bowl) > 2:
                    title_fontsize = 9  # Reduce font size for many teams
        else:
            title_opponent = team_bowl if team_bowl is not None else "All Teams"

        title_parts = []
        if 'title' in title_components:
            title_parts.append(f"{title_name} vs {title_opponent}")
        if 'filters' in title_components:
            title_parts.append(f"{competition} - Mat '{mat_num}', Inns: '{inns}'")
        title_text = " | ".join(title_parts).upper()


    # if show_summary:
    #     ax.text(180, -20, f"Total Runs: {innings_runs} ({innings_balls} balls)",
    #             fontsize=11, ha='center', fontweight='bold', color='darkgreen')
    #     ax.text(180, -5, f"Total 4s: {innings_4s} | 6s: {innings_6s}",
    #             fontsize=11, ha='center', color='darkgreen')

    if show_summary:
        ax.text(180, 440, f"Total Runs: {innings_runs} ({innings_balls} balls) | Strike Rate: {round(innings_runs/innings_balls*100, 2) if innings_balls > 0 else 0}",
                fontsize=11, ha='center', fontweight='bold', color='darkgreen')
        # ax.text(180, 458, f"4s x {innings_4s} | 6s x {innings_6s}",
        # ax.text(180, 458, f"0s x {innings_0s} | 1s x {innings_1s} | 4s x {innings_4s} | 6s x {innings_6s}",
        #         fontsize=11, ha='center', color='darkgreen')

    if show_shots_breakdown:
    # Build breakdown text dynamically
        breakdown_parts = []
        if '0s' in shots_breakdown_options:
            breakdown_parts.append(f"0s x {innings_0s}")
        if '1s' in shots_breakdown_options:
            breakdown_parts.append(f"1s x {innings_1s}")
        if '2s' in shots_breakdown_options:
            breakdown_parts.append(f"2s x {innings_2s}")
        if '3s' in shots_breakdown_options:
            breakdown_parts.append(f"3s x {innings_3s}")
        if '4s' in shots_breakdown_options:
            breakdown_parts.append(f"4s x {innings_4s}")
        if '6s' in shots_breakdown_options:
            breakdown_parts.append(f"6s x {innings_6s}")
        
        if breakdown_parts:  # Only show if something selected
            breakdown_text = " | ".join(breakdown_parts)
            ax.text(180, 458, breakdown_text, fontsize=11, ha='center', color='darkgreen')
    
    
    # # COMMENTED OUT - Not relevant for dismissal plot
    # if runs_count:
    #     if player_name is None:
    #         ax.text(180, 375, f"{innings_runs} ({innings_balls} balls)",
    #                 fontsize=11, ha='center', fontweight='bold')
    #     else:
    #         ax.text(180, 375, f"{total_score} ({balls_faced} balls)",
    #                 fontsize=11, ha='center', fontweight='bold')

    # if runs_count:
    #     ax.text(430, 140, f"{total_score} ({balls_faced} balls)",
    #             fontsize=11, ha='center', fontweight='bold')
        
    # if show_fours_sixes:
    #     ax.text(430, 155, f"4s: {total_4s} | 6s: {total_6s}",
    #             fontsize=11, ha='center', color='darkgreen')
        
    # if show_bowler:
    #     if bowler_name is None:
    #         bowler_name = 'All Bowlers'
    #     if bowler_name:
    #         ax.text(430,175, f"vs {bowler_name}",
    #                 fontsize=11, ha='center', color='blue', fontweight='bold')

    # if show_control:
    #     ax.text(430, 80, f"Control: {control_pct}%",
    #             fontsize=12, ha='center', color='purple', fontweight='bold')

    # if show_prod_shot:
    #     ax.text(430, 250, f"Productive Shot:\n{most_prod_shot_text}",
    #             fontsize=11, ha='center', color='navy',fontweight='bold')

    # # update position for the plot (COMMENTED OUT - Not relevant for dismissal plot)
    # if runs_count:
    #     if not show_fours_sixes and not show_bowler:
    #          ax.text(180, 499, f"{total_score} ({balls_faced} balls)",
    #             fontsize=11, ha='center', fontweight='bold')
    #     else:
    #         ax.text(40, 499, f"{total_score} ({balls_faced} balls)",
    #                 fontsize=11, ha='center', fontweight='bold')

    #     # ax.text(40, 499, f"{total_score} ({balls_faced} balls)",
    #     #         fontsize=11, ha='center', fontweight='bold')
        
    # if show_fours_sixes:
    #     if not runs_count and not show_bowler:
    #         ax.text(180, 499, f" 4s: {total_4s} | 6s: {total_6s}",
    #             fontsize=11, ha='center', color='darkgreen')
    #     else:
    #         ax.text(180, 499, f" | 4s: {total_4s} | 6s: {total_6s}",
    #             fontsize=11, ha='center', color='darkgreen')

    #     # ax.text(180, 499, f" | 4s: {total_4s} | 6s: {total_6s}",
    #     #         fontsize=11, ha='center', color='darkgreen')
    
    # === NEW: Display Dismissals Count ===
    ax.text(180, 545, f"Dismissals: {dismissals_count}",
            fontsize=12, ha='center', fontweight='bold', color='red')
        
    if show_bowler:
        if bowler_name is None:
            bowler_name = 'All Bowlers'
        if bowler_name:
            if not runs_count and not show_fours_sixes:
                ax.text(180, 499, f"vs {bowler_name}",
                        fontsize=11, ha='center', color='blue', fontweight='bold')
            else:
                ax.text(180, 499, f"vs {bowler_name}",
                        fontsize=11, ha='center', color='blue', fontweight='bold')
            # ax.text(310, 499, f" | vs {bowler_name}",
            #         fontsize=11, ha='center', color='blue', fontweight='bold')

    if show_title:
        # Adjust position based on title length
        if len(title_components) == 1:
            title_x = 180
            title_y = 420
            ax.set_xlim(-60, 420)
        else:
            title_x = 180
            title_y = 420
        # Use dynamic font size
        ax.text(title_x, title_y, title_text, fontsize=title_fontsize, ha='center', 
                fontweight='bold', fontfamily='DejaVu Sans')

    if show_control:
        ax.text(180, 482, f"Control: {control_pct}%",
                fontsize=12, ha='center', color='purple', fontweight='bold')

    # # COMMENTED OUT - Replaced with Most Loose Shot
    # if show_prod_shot:
    #     ax.text(180, 520, f"Productive Shot: {most_prod_shot_text}",
    #             fontsize=11, ha='center', color='navy',fontweight='bold')
    
    # === NEW: Display Most Loose Shot ===
    if show_prod_shot:  # Using same flag for consistency
        ax.text(180, 520, f"Most Fatal Shot: {most_loose_shot_text}",
                fontsize=11, ha='center', color='crimson', fontweight='bold')

    ax.invert_yaxis()
    ax.set_axis_off()

    # # Legend (COMMENTED OUT - Not required for dismissal plot)
    # legend_elements = [
    #     mpatches.Patch(color=color, label=f'{score} \'s')
    #     for score, color in score_colors.items() if run_values is None or score in run_values
    # ]

    # # ax.legend(handles=legend_elements, loc='upper right', fontsize=8)
    
    # if show_legend:
    #     # ax.legend(handles=legend_elements, loc='upper right', fontsize=8)
    #     ax.legend(
    #         handles=legend_elements,
    #         loc='center',
    #         bbox_to_anchor=(180, 540),  # (x, y) in data coordinates
    #         bbox_transform=ax.transData,
    #         ncol=4,
    #         frameon=False,
    #         fontsize=8
    #     )


    if show_overs:
        # 1. Format Overs text
        if over_values is None:
            over_text = "All"
        elif len(over_values) <= 10:
            over_text = ", ".join(map(str, sorted(over_values)))
        else:
            over_text = f"{min(over_values)}-{max(over_values)} ({len(over_values)} overs)"

        if not show_phase:
            ax.text(180, 570, f"Overs: {over_text}", 
                fontsize=10, ha='center', color='darkslategrey', fontweight='bold')
        else:
            ax.text(100, 570, f"Overs: {over_text}", 
                fontsize=10, ha='center', color='darkslategrey', fontweight='bold')
        
        # 3. Display on plot (below productive shot at 430, 250)
        # ax.text(100, 570, f"Overs: {over_text}", 
        #         fontsize=10, ha='center', color='darkslategrey', fontweight='bold')

    if show_phase:
        # 2. Format Phase text
        phase_names = {
            1: "Powerplay (1-6)",
            2: "Middle (7-15)", 
            3: "Death (16-20)"
        }
        # phase_text = phase_names.get(phase, "All")

        if isinstance(phase, list):
            phase_text = ", ".join([phase_names.get(p, str(p)) for p in phase]) if phase else "All"
        else:
            phase_text = phase_names.get(phase, "All")


        if not show_overs:
            ax.text(180, 570, f"Phase: {phase_text}", 
                fontsize=10, ha='center', color='crimson', fontweight='bold')
        else:
            ax.text(260, 570, f"Phase: {phase_text}", 
                fontsize=10, ha='center', color='crimson', fontweight='bold')
        # ax.text(260, 570, f"Phase: {phase_text}", 
        #         fontsize=10, ha='center', color='crimson', fontweight='bold')
    
    if show_bowl_type:
        # Format bowl_type text
        # bowl_type_text = bowl_type if bowl_type is not None else "All"
        if bowl_type is None or len(bowl_type) == 0:
            bowl_type_text = "All"
        elif len(bowl_type) == 1:
            bowl_type_text = bowl_type[0]
        else:
            bowl_type_text = ", ".join(bowl_type)
        
        # Responsive positioning
        if not show_bowl_kind:
            ax.text(180, 590, f"     Type: {bowl_type_text}", 
                    fontsize=10, ha='center', color='darkviolet', fontweight='bold')
        else:
            ax.text(180, 590, f"Bowl Type: {bowl_type_text}", 
            # ax.text(70, 590, f"Bowl Type: {bowl_type_text}", 
                    fontsize=10, ha='center', color='darkviolet', fontweight='bold')

    if show_venue:
        if ground is None or len(ground) == 0:
            ground = "All Venues"
        elif len(ground) == 1:
            ground = ground[0]
        else:
            ground = ", ".join(ground)

        ax.text(180, 630, f"Venue: {ground}", 
                fontsize=10, ha='center', color='blue', fontweight='bold')


    if show_bowl_kind:
        # Format bowl_kind text
        # bowl_kind_text = bowl_kind if bowl_kind is not None else "All"

        if bowl_kind is None or len(bowl_kind) == 0:
            bowl_kind_text = "All"
        elif len(bowl_kind) == 1:
            bowl_kind_text = bowl_kind[0]
        else:
            bowl_kind_text = ", ".join(bowl_kind)
        
        # Responsive positioning
        if not show_bowl_arm:
            # ax.text(180, 590, f"Bowl Pace: {bowl_kind_text}", 
            ax.text(180, 610, f"Bowl Pace: {bowl_kind_text}", 
                    fontsize=10, ha='center', color='teal', fontweight='bold')
        else:
            ax.text(70, 610, f"Bowl Pace: {bowl_kind_text}", 
            # ax.text(290, 590, f"Bowl Pace: {bowl_kind_text}", 
                    fontsize=10, ha='center', color='teal', fontweight='bold')
            

    if show_bowl_arm:
        # Format bowl_arm text
        if bowl_arm is None or len(bowl_arm) == 0:
            bowl_arm_text = "All"
        elif len(bowl_arm) == 1:
            bowl_arm_text = bowl_arm[0]
        else:
            bowl_arm_text = ", ".join(bowl_arm)
        
        # Responsive positioning
        if not show_bowl_kind:
            ax.text(180, 610, f"Bowl Arm: {bowl_arm_text}", 
                fontsize=10, ha='center', color='saddlebrown', fontweight='bold')
        else: 
            ax.text(270, 610, f"Bowl Arm: {bowl_arm_text}", 
                fontsize=10, ha='center', color='saddlebrown', fontweight='bold')
        
    # plt.subplots_adjust(left=0.05, right=0.95, top=0.93, bottom=0.07)
    plt.subplots_adjust(left=0.05, right=0.95, top=0.93, bottom=0.02)
    plt.close(fig)
    return fig
    # plt.show()