# wagon zone plot
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from matplotlib import cm
from matplotlib.patches import Wedge
import pandas as pd

def wagon_zone_plot(
    df, player_name=None, pid=None, inns=None, mat_num=None, bowler_name=None, team_bat=None, 
    team_bowl=None, run_values=None, competition=None, transparent=False, ground=None,
    date_from=None, date_to=None, over_values=None, phase=None, bowler_id=None, mcode=None,
    title_components=['title', 'filters'], shots_breakdown_options=['0s', '1s', '2s', '3s', '4s', '6s'],  # NEW: Which runs to show
    bat_hand=None , bowl_type=None, bowl_kind=None, bowl_arm=None,
    show_bowl_type=True, show_bowl_kind=True, show_bowl_arm=True, show_venue=True,
    show_title=True, show_summary=True,show_fours_sixes=True, show_control=True, show_shots_breakdown=True,
    show_prod_shot=True,runs_count=True, show_bowler=True, show_overs=True, show_phase=True
):
    # ---- Apply Filters for Plotting ----
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


    if player_name:
        local_df = local_df[local_df['bat'] == player_name] # bat
    if mat_num:
        # local_df = local_df[local_df['TestNum'] == mat_num]
        local_df = local_df[local_df['p_match'] == mat_num] # p_match

    # if inns:
    #     local_df = local_df[local_df['inns'] == inns] # inns

    if inns is not None and len(inns) > 0:
        local_df = local_df[local_df['inns'].isin(inns)]

    # if bowler_id is not None:
    #     local_df = local_df[local_df['p_bowl'] == bowler_id]

    #     if not local_df.empty and bowler_name is None:
    #         bowler_name = local_df['bowl'].iloc[0]
    # # Otherwise filter by bowler name
    # elif bowler_name is not None:
    #     local_df = local_df[local_df['bowl'] == bowler_name]

    # if bowler_name:
    #     local_df = local_df[local_df['bowl'] == bowler_name] #bowl

    if run_values is not None:
        local_df = local_df[local_df['batruns'].isin(run_values)] #batruns

    # if team_bat is not None and team_bat != "All":
    #     local_df = local_df[local_df['team_bat'] == team_bat]

    # if team_bowl is not None and team_bowl != "All":
    #     local_df = local_df[local_df['team_bowl'] == team_bowl]

    if team_bat is not None and len(team_bat) > 0:
        local_df = local_df[local_df['team_bat'].isin(team_bat)]

    if team_bowl is not None and len(team_bowl) > 0:
        local_df = local_df[local_df['team_bowl'].isin(team_bowl)]

    #competition filter
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

    #match code like PAK v NED
    # if mcode is not None:
    #     local_df = local_df[local_df['mcode'] == mcode]

    if mcode is not None and len(mcode) > 0:
        local_df = local_df[local_df['mcode'].isin(mcode)]

    # Date range filter
    if date_from is not None:
        local_df = local_df[local_df['date'] >= pd.to_datetime(date_from)]

    if date_to is not None:
        local_df = local_df[local_df['date'] <= pd.to_datetime(date_to)]

    # if player_name is None:
    #     innings_valid_balls = local_df.copy()  # include all for team
    #     innings_runs = innings_valid_balls['score'].sum() #score
    # else:
    #     innings_valid_balls = local_df[local_df['wide'] == 0]
    #     innings_runs = innings_valid_balls['batruns'].sum() #batruns

    #ground filter
    # if ground is not None:
    #     local_df = local_df[local_df['ground'] == ground]

    if ground is not None and len(ground) > 0:
        local_df = local_df[local_df['ground'].isin(ground)]


    if bat_hand is not None and len(bat_hand) > 0:
        local_df = local_df[local_df['bat_hand'].isin(bat_hand)]

    # updated change of multiselect
    if bowl_type is not None and len(bowl_type) > 0:
        local_df = local_df[local_df['bowl_type'].isin(bowl_type)]

    if bowl_kind is not None and len(bowl_kind) > 0:
        local_df = local_df[local_df['bowl_kind'].isin(bowl_kind)]

    if bowl_arm is not None and len(bowl_arm) > 0:
        local_df = local_df[local_df['bowl_arm'].isin(bowl_arm)]


    if player_name is None:
        innings_valid_balls = local_df.copy()  # include all for team
        innings_runs = innings_valid_balls['score'].sum() #score
    else:
        innings_valid_balls = local_df[local_df['wide'] == 0]
        innings_runs = innings_valid_balls['batruns'].sum() #batruns

    innings_balls = innings_valid_balls.shape[0]

    if bowler_id is not None:
        local_df = local_df[local_df['p_bowl'] == bowler_id]

        if not local_df.empty and bowler_name is None:
            bowler_name = local_df['bowl'].iloc[0]
    # Otherwise filter by bowler name
    elif bowler_name is not None:
        local_df = local_df[local_df['bowl'] == bowler_name]

    if bowler_name:
        local_df = local_df[local_df['bowl'] == bowler_name] #bowl

    # innings_balls = innings_valid_balls[innings_valid_balls['wide'] == 0].shape[0]  # consistent valid balls

    # --- Core Filtering Logic (Team vs Player Mode) ---
    if player_name is None:
        valid_balls = local_df[local_df['wide'] == 0]
        valid_shots = valid_balls[~((valid_balls['wagonX'] == 0) & (valid_balls['wagonY'] == 0))]

        # ADD THESE TWO LINES:
        valid_shots['isFour'] = (valid_shots['outcome'] == 'four').astype(int)
        valid_shots['isSix'] = (valid_shots['outcome'] == 'six').astype(int)

        total_score = valid_shots['score'].sum() #score
        # total_4s = valid_shots['isFour'].sum()
        # total_6s = valid_shots['isSix'].sum()
        #logic update for generalization
        total_4s = (valid_shots['outcome'] == 'four').sum()
        total_6s = (valid_shots['outcome'] == 'six').sum()

        total_0s = (innings_valid_balls['batruns'] == 0).sum()
        total_1s = (innings_valid_balls['batruns'] == 1).sum()
        total_2s = (innings_valid_balls['batruns'] == 2).sum()
        total_3s = (innings_valid_balls['batruns'] == 3).sum()

        balls_faced = valid_balls.shape[0]

        # control_pct = round(
        #     (valid_balls[valid_balls['control'] == 1].shape[0]) / balls_faced * 100, 2 
        # )#shotControl to control

        # Control calculation like spike graph
        # controlled_balls = valid_balls[valid_balls['control'] == 1]
        # control_pct = round(len(controlled_balls) / len(valid_balls) * 100, 2) if len(valid_balls) > 0 else 0.0

        if len(valid_balls) == 0:
            control_pct = 0.0
        else:
            # Convert mixed-type control column to numeric FIRST
            control_numeric = pd.to_numeric(valid_balls['control'], errors='coerce')
            # Now count all 1.0 values (regardless of original type)
            controlled = (control_numeric == 1).sum()
            control_pct = round(controlled / len(valid_balls) * 100, 2)

        

        shot_summary = valid_shots.groupby('shot').agg({ #shot
            'score': 'sum', #score
            'isFour': 'sum', #we need to check the outcome column as four and six is there as strings
            'isSix': 'sum'
        }).sort_values(by='score', ascending=False) #score
    else:
        valid_balls = local_df[(local_df['wide'] == 0) & (~local_df['control'].isna())]
        valid_shots = local_df[
            ~((local_df['wagonX'] == 0) & (local_df['wagonY'] == 0))
        ].dropna(subset=['wagonX', 'wagonY'])

        # ✅ ADD: Filter valid_shots the same way - exclude wides AND control nulls
        # valid_shots = local_df[
        #     (local_df['wide'] == 0) & 
        #     ~((local_df['wagonX'] == 0) & (local_df['wagonY'] == 0)) &
        #     (~local_df['control'].isna())  # ← ADD THIS
        # ].dropna(subset=['wagonX', 'wagonY'])

        # ADD THESE TWO LINES:
        valid_shots['isFour'] = (valid_shots['outcome'] == 'four').astype(int)
        valid_shots['isSix'] = (valid_shots['outcome'] == 'six').astype(int)

        total_score = valid_shots['batruns'].sum() #batruns
        # total_4s = valid_shots['isFour'].sum()
        # total_6s = valid_shots['isSix'].sum()
        total_4s = (valid_shots['outcome'] == 'four').sum()
        total_6s = (valid_shots['outcome'] == 'six').sum()

        total_0s = (innings_valid_balls['batruns'] == 0).sum()
        total_1s = (innings_valid_balls['batruns'] == 1).sum()
        total_2s = (innings_valid_balls['batruns'] == 2).sum()
        total_3s = (innings_valid_balls['batruns'] == 3).sum()
        
        balls_faced = valid_balls.shape[0]

        # control_pct = round(
        #     (valid_balls[valid_balls['control'] == 1].shape[0]) / balls_faced * 100, 2 
        # ) #shotControl to control
        
        #  Control calculation like spike graph
        # controlled_balls = valid_balls[valid_balls['control'] == 1]
        # control_pct = round(len(controlled_balls) / len(valid_balls) * 100, 2) if len(valid_balls) > 0 else 0.0
        if len(valid_balls) == 0:
            control_pct = 0.0
        else:
            # Convert mixed-type control column to numeric FIRST
            control_numeric = pd.to_numeric(valid_balls['control'], errors='coerce')
            # Now count all 1.0 values (regardless of original type)
            controlled = (control_numeric == 1).sum()
            control_pct = round(controlled / len(valid_balls) * 100, 2)

        shot_summary = valid_shots.groupby('shot').agg({ #shot
            'batruns': 'sum', #batruns
            'isFour': 'sum',
            'isSix': 'sum'
        }).sort_values(by='batruns', ascending=False) #batruns

    # Most Productive Shot
    if not shot_summary.empty:
        top_shot = shot_summary.iloc[0]
        top_shot_type = shot_summary.index[0]
        runs_col = 'score' if player_name is None else 'batruns' #score or batruns
        most_prod_shot_text = (
            # f"{top_shot_type.upper()}: {int(top_shot[runs_col])} runs,\n"
            f"{top_shot_type.upper()}: {int(top_shot[runs_col])} runs, \n"
            f"4s: {int(top_shot['isFour'])}, 6s: {int(top_shot['isSix'])}"
        )
    else:
        most_prod_shot_text = "No productive shot data"

    # Prepare data for quadrant plotting
    score_col = 'batruns' if player_name else 'score' #batruns or score
    player_data = valid_shots[['wagonX', 'wagonY', score_col, 'isFour', 'isSix']].copy()

    center_x, center_y = 180, 164
    def get_quadrant(x, y):
        angle = np.arctan2(y - center_y, x - center_x)
        degree = (np.degrees(angle) + 360) % 360
        return int(degree // 45)

    # ✅ CHECK IF DATA IS EMPTY BEFORE ASSIGNING QUADRANT
    if not player_data.empty:
        player_data['quadrant'] = player_data.apply(lambda row: get_quadrant(row['wagonX'], row['wagonY']), axis=1)
        quadrant_totals = [player_data[player_data['quadrant'] == q][score_col].sum() for q in range(8)]
        total_score = sum(quadrant_totals)
    else:
        quadrant_totals = [0] * 8
        total_score = 0

    # Plot
    fig, ax = plt.subplots(figsize=(7, 7), facecolor='none' if transparent else 'white')
    ax.set_facecolor('none' if transparent else 'white')

    # Draw ground and pitch
    boundary = plt.Circle((center_x, center_y), 180, color='#8c8c8c', fill=False, linewidth=1.2)
    batter_dot = plt.Circle((center_x, center_y), radius=3, edgecolor='black', facecolor='green', zorder=2)
    ax.add_artist(boundary)
    ax.add_artist(batter_dot)

    for angle in range(0, 360, 45):
        rad = np.deg2rad(angle)
        x_end = center_x + 180 * np.cos(rad)
        y_end = center_y + 180 * np.sin(rad)
        ax.plot([center_x, x_end], [center_y, y_end], color='#8c8c8c', linewidth=1.3)

    # ✅ HIGHLIGHT TOP ZONES ONLY IF THEY HAVE RUNS > 0
    top_quadrants = [i for i in sorted(range(8), key=lambda i: quadrant_totals[i], reverse=True) if quadrant_totals[i] > 0][:2]
    rank_color = {top_quadrants[i]: 1.0 - i * 0.3 for i in range(len(top_quadrants))}
    # cmap = cm.get_cmap('Blues')
    cmap = plt.colormaps['Blues']

    for i in range(8):
        theta1, theta2 = i * 45, (i + 1) * 45
        if i in rank_color:
            ax.add_patch(Wedge(center=(center_x, center_y), r=180, theta1=theta1, theta2=theta2,
                               color=cmap(rank_color[i]), alpha=0.3, zorder=0))
        mid_angle = np.deg2rad(theta1 + 22.5)
        label_x = center_x + 100 * np.cos(mid_angle)
        label_y = center_y + 100 * np.sin(mid_angle)
        ax.text(label_x, label_y, f"{quadrant_totals[i]} runs", fontsize=10.5,
                color='black' if i in top_quadrants else '#000',
                ha='center', va='center',fontweight = 'bold')

    # ✅ ADD "NO SHOTS" MESSAGE IF DATA IS EMPTY
    if player_data.empty:
        ax.text(220, 410, "No shots for selected filter(s)", ha='center', fontsize=12, color='red', fontweight='bold')

    ax.set_xlim(-20, 470)
    ax.set_ylim(-50, 370)
    # ax.set_xlim(-20, 380)
    # ax.set_ylim(-50, 440)
    ax.invert_yaxis()
    ax.set_aspect('equal')
    ax.set_axis_off()

    # Determine team names
    # if not local_df.empty:
    #     team_bats = local_df['team_bat'].unique() 
    #     if len(team_bats) == 1:
    #         team_bat = team_bats[0]
    #         all_teams = df['team_bat'].unique().tolist() + df['team_bowl'].unique().tolist()
    #         team_bowl = [t for t in set(all_teams) if t != team_bat][0] if team_bat in all_teams else "Opponent"
    #     else:
    #         team_bowl = "All Teams"
    # else:
    #     team_bowl = "All Teams"
    
    # # Determine team names
    # if not local_df.empty:
    #     team_bats = local_df['team_bat'].unique() 
    #     if len(team_bats) == 1:
    #         team_bat = team_bats[0]
    #         # Filter by the same match to get correct opponent
    #         if mat_num is not None:
    #             match_df = df[df['p_match'] == mat_num]
    #         else:
    #             match_df = local_df
            
    #         # Get opponent from the same match
    #         team_bowls_in_match = match_df['team_bowl'].unique()
    #         team_bowl = [t for t in team_bowls_in_match if t != team_bat][0] if len(team_bowls_in_match) > 0 else "Opponents"
    #     else:
    #         team_bowl = "All Teams"
    # else:
    #     team_bowl = "All Teams"

    # if show_title:
    #     ax.set_title(
    #         f"{player_name} vs {team_bowl} | {competition} - Mat '{mat_num}', Inns: '{inns}'".upper(),
    #         fontsize=12, fontweight='bold', fontfamily='DejaVu Sans'
    #     )

    # # Metadata for title - DO THIS FIRST
    # if mat_num is None: mat_num = "All Mats"
    # if inns is None: inns = "All Inns"
    # if player_name is None: player_name = "All Players"
    # if competition is None: competition = "All Comps"
    
    # Determine team names ONLY if not provided as parameters
    if not local_df.empty:
        # Only detect team_bat if it wasn't provided as a filter
        if team_bat is None or team_bat == "All":
            team_bats = local_df['team_bat'].unique() 
            if len(team_bats) == 1:
                team_bat = team_bats[0]
            else:
                team_bat = "All Teams"
        
        # Only detect team_bowl if it wasn't provided as a filter
        if team_bowl is None or team_bowl == "All":
            if mat_num is not None and mat_num != "All Matches":
                match_df = df[df['p_match'] == mat_num]
            else:
                match_df = local_df
            
            team_bowls_in_match = match_df['team_bowl'].unique()
            opponents = [t for t in team_bowls_in_match if t != team_bat]
            
            if len(opponents) == 1:
                team_bowl = opponents[0]
            elif len(opponents) > 1:
                team_bowl = "All Teams"
            else:
                team_bowl = "Opponents"
    else:
        if team_bat is None: team_bat = "All Teams"
        if team_bowl is None: team_bowl = "All Teams"
    
    # Metadata for title - DO THIS FIRST
    if mat_num is None: mat_num = "All Mats"
    if inns is None: inns = "All Inns"
    if player_name is None: player_name = "All Players"
    if competition is None: competition = "All Comps"

    if show_title:
        # Determine title display (match spike graph logic)
        if player_name and player_name != "All Players":
            title_name = player_name
            title_opponent = team_bowl
        else:
            # For team view, show batting team from filtered data
            if not local_df.empty:
                batting_teams_display = local_df['team_bat'].unique()
                if len(batting_teams_display) == 1:
                    title_name = batting_teams_display[0]  # Show actual team name
                    title_opponent = team_bowl
                else:
                    title_name = "All Players"
                    title_opponent = team_bowl
            else:
                title_name = "All Players"
                title_opponent = "All Teams"
        
        # ax.set_title(
        #     f"{title_name} vs {title_opponent} | {competition} - Mat '{mat_num}', Inns: '{inns}'".upper(),
        #     fontsize=12, fontweight='bold', fontfamily='DejaVu Sans'
        # )

        title_part=[]

        if 'title' in title_components:
            title_part.append(f"{title_name} vs {title_opponent}")

        if 'filters' in title_components:
            title_part.append(f"{competition} - Mat '{mat_num}', Inns: '{inns}'")

        title_text = " | ".join(title_part).upper()

    if show_title:
        if len(title_components) == 1:
            # Shorter title - keep centered
            title_x = 180
            # title_y = 400  # Slightly lower for single line
        else:
            # Full title - original position
            title_x = 180
            # title_y = 408

        ax.text(title_x, -60, title_text, fontsize=12, fontweight='bold', fontfamily='DejaVu Sans', ha='center')

    # Text Summary
    if show_summary:
        ax.text(200, -40, f"Total Runs: {innings_runs} ({innings_balls} balls)| Strike Rate: {round(innings_runs/innings_balls*100, 2) if balls_faced > 0 else 0}",
                fontsize=11, ha='center', fontweight='bold', color='darkgreen')
        # ax.text(200, -25, f"0s x {total_0s} | 1s x {total_1s} | 2s x {total_2s} | 3s x {total_3s} | 4s x {total_4s} | 6s x {total_6s}",
        # ax.text(200, -25, f"4s x {total_4s} | 6s x {total_6s}",
        #         fontsize=11, ha='center', color='darkgreen')

    if show_shots_breakdown:
        # Build breakdown text dynamically
        breakdown_parts = []
        if '0s' in shots_breakdown_options:
            breakdown_parts.append(f"0s x {total_0s}")
        if '1s' in shots_breakdown_options:
            breakdown_parts.append(f"1s x {total_1s}")
        if '2s' in shots_breakdown_options:
            breakdown_parts.append(f"2s x {total_2s}")
        if '3s' in shots_breakdown_options:
            breakdown_parts.append(f"3s x {total_3s}")
        if '4s' in shots_breakdown_options:
            breakdown_parts.append(f"4s x {total_4s}")
        if '6s' in shots_breakdown_options:
            breakdown_parts.append(f"6s x {total_6s}")
        
        if breakdown_parts:  # Only show if something selected
            breakdown_text = " | ".join(breakdown_parts)
            ax.text(200, -25, breakdown_text, fontsize=11, ha='center', color='darkgreen')

    if runs_count:
        ax.text(430, 140, f"{total_score} ({balls_faced} balls)",
                fontsize=11, ha='center', fontweight='bold')

    if show_fours_sixes:
        ax.text(430, 155, f"4s: {int(player_data['isFour'].sum())} | 6s: {int(player_data['isSix'].sum())}",
                fontsize=11, ha='center', color='darkgreen')

    if show_bowler:
        if bowler_name is None:
            bowler_name = 'All Bowlers'
        ax.text(430, 170, f"vs {bowler_name}", fontsize=11, ha='center',
                color='blue', fontweight='bold')
        
    if show_control:
        ax.text(430, 80, f"Control: {control_pct}%", fontsize=12, ha='center',
                color='purple', fontweight='bold')

    if show_prod_shot:
        ax.text(430, 250, f"Productive Shot:\n{most_prod_shot_text}", fontsize=11,
                ha='center', color='navy', fontweight='bold')


    if show_overs:
        # 1. Format Overs text
        if over_values is None:
            over_text = "All"
        elif len(over_values) <= 10:
            over_text = ", ".join(map(str, sorted(over_values)))
        else:
            over_text = f"{min(over_values)}-{max(over_values)} ({len(over_values)} overs)"


        # 3. Display on plot (below productive shot at 430, 250)
        ax.text(430, 300, f"Overs: {over_text}", 
                fontsize=10, ha='center', color='darkslategrey', fontweight='bold')

    if show_phase:
        # 2. Format Phase text
        phase_names = {
            1: "Powerplay (1-6)",
            2: "Middle (7-15)", 
            3: "Slog (16-20)"
        }
        # phase_text = phase_names.get(phase, "All")

        if isinstance(phase, list):
            phase_text = ", ".join([phase_names.get(p, str(p)) for p in phase]) if phase else "All"
        else:
            phase_text = phase_names.get(phase, "All")

        ax.text(430, 320, f"Phase: {phase_text}", 
                fontsize=10, ha='center', color='crimson', fontweight='bold')
    
    # #  update the positions of the summary texts
    # if runs_count:
    #     ax.text(70, 400, f"{total_score} ({balls_faced} balls)",
    #             fontsize=11, ha='center', fontweight='bold')

    # if show_fours_sixes:
    #     ax.text(170, 400, f" - 4s: {int(player_data['isFour'].sum())} | 6s: {int(player_data['isSix'].sum())}",
    #             fontsize=11, ha='center', color='darkgreen')

    # if show_control:
    #     ax.text(180, 380, f"Control: {control_pct}%", fontsize=12, ha='center',
    #             color='purple', fontweight='bold')

    # if show_prod_shot:
    #     ax.text(180, 420, f"Productive Shot: {most_prod_shot_text}", fontsize=11,
    #             ha='center', color='navy', fontweight='bold')

    # if show_bowler:
    #     if bowler_name is None:
    #         bowler_name = 'All Bowlers'
    #     ax.text(270, 400, f" - vs {bowler_name}", fontsize=11, ha='center',
    #             color='blue', fontweight='bold')

    plt.subplots_adjust(left=0.05, right=0.95, top=0.93, bottom=0.07)
    # plt.subplots_adjust(left=0.05, right=0.95, top=0.93, bottom=0.02)
    plt.close(fig)
    return fig
    # plt.show()


def wagon_zone_plot_descriptive(
    df, player_name=None, pid=None, inns=None, mat_num=None, bowler_name=None, team_bat=None, 
    team_bowl=None, run_values=None, competition=None, transparent=False, ground=None,
    date_from=None, date_to=None, over_values=None, phase=None, bowler_id=None, mcode=None,
    title_components=['title', 'filters'], shots_breakdown_options=['0s', '1s', '2s', '3s', '4s', '6s'],  # NEW: Which runs to show
    bat_hand=None , bowl_type=None, bowl_kind=None, bowl_arm=None, show_shots_breakdown=True,
    show_title=True, show_summary=True,show_fours_sixes=True, show_control=True, 
    show_bowl_type=True, show_bowl_kind=True, show_bowl_arm=True, show_venue=True,
    show_prod_shot=True,runs_count=True, show_bowler=True, show_overs=True, show_phase=True
):
    # ---- Apply Filters for Plotting ----
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

    if player_name:
        local_df = local_df[local_df['bat'] == player_name] # bat
    if mat_num:
        # local_df = local_df[local_df['TestNum'] == mat_num]
        local_df = local_df[local_df['p_match'] == mat_num] # p_match

    # if inns:
    #     local_df = local_df[local_df['inns'] == inns] # inns

    if inns is not None and len(inns) > 0:
        local_df = local_df[local_df['inns'].isin(inns)]

    if run_values is not None:
        local_df = local_df[local_df['batruns'].isin(run_values)] #batruns

    # if team_bat is not None and team_bat != "All":
    #     local_df = local_df[local_df['team_bat'] == team_bat]

    # if team_bowl is not None and team_bowl != "All":
    #     local_df = local_df[local_df['team_bowl'] == team_bowl]

    if team_bat is not None and len(team_bat) > 0:
        local_df = local_df[local_df['team_bat'].isin(team_bat)]

    if team_bowl is not None and len(team_bowl) > 0:
        local_df = local_df[local_df['team_bowl'].isin(team_bowl)]


    #competition filter
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

    #match code like PAK v NED
    # if mcode is not None:
    #     local_df = local_df[local_df['mcode'] == mcode]

    if mcode is not None and len(mcode) > 0:
        local_df = local_df[local_df['mcode'].isin(mcode)]
        
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

    if bat_hand is not None and len(bat_hand) > 0:
        local_df = local_df[local_df['bat_hand'].isin(bat_hand)]

    # if bowl_type is not None:
    #     local_df = local_df[local_df['bowl_type'] == bowl_type]

    # if bowl_kind is not None:
    #     local_df = local_df[local_df['bowl_kind'] == bowl_kind]
        
    # if bowl_arm is not None:
    #     local_df = local_df[local_df['bowl_arm'] == bowl_arm]

    # updated change of multiselect
    if bowl_type is not None and len(bowl_type) > 0:
        local_df = local_df[local_df['bowl_type'].isin(bowl_type)]

    if bowl_kind is not None and len(bowl_kind) > 0:
        local_df = local_df[local_df['bowl_kind'].isin(bowl_kind)]

    if bowl_arm is not None and len(bowl_arm) > 0:
        local_df = local_df[local_df['bowl_arm'].isin(bowl_arm)]

        
    # === INNINGS STATS - Calculate BEFORE any bowler/bowl_type/bowl_kind/bowl_arm filter ===
    if player_name is None:
        innings_valid_balls = local_df.copy()
        innings_runs = innings_valid_balls['score'].sum()
    else:
        innings_valid_balls = local_df[local_df['wide'] == 0]
        innings_runs = innings_valid_balls['batruns'].sum()
        
    # actual complete innings balls
    innings_balls = innings_valid_balls.shape[0]

    # innings_balls = innings_valid_balls[
    #     ~((innings_valid_balls['wagonX'] == 0) & (innings_valid_balls['wagonY'] == 0))
    # ].dropna(subset=['wagonX', 'wagonY']).shape[0]

    # to check the filtered balls in summary
    # valid_shots = innings_valid_balls[~((innings_valid_balls['wagonX'] == 0) & (innings_valid_balls['wagonY'] == 0))]

    # innings_balls = valid_shots.shape[0]


    if bowler_id is not None:
        local_df = local_df[local_df['p_bowl'] == bowler_id]

        if not local_df.empty and bowler_name is None:
            bowler_name = local_df['bowl'].iloc[0]
    # Otherwise filter by bowler name
    elif bowler_name is not None:
        local_df = local_df[local_df['bowl'] == bowler_name]

    if bowler_name:
        local_df = local_df[local_df['bowl'] == bowler_name] #bowl

    # if player_name is None:
    #     innings_valid_balls = local_df.copy()  # include all for team
    #     innings_runs = innings_valid_balls['score'].sum() #score
    # else:
    #     innings_valid_balls = local_df[local_df['wide'] == 0]
    #     innings_runs = innings_valid_balls['batruns'].sum() #batruns

    # # innings_balls = innings_valid_balls[innings_valid_balls['wide'] == 0].shape[0]  # consistent valid balls
    # innings_balls = innings_valid_balls[
    #     ~((innings_valid_balls['wagonX'] == 0) & (innings_valid_balls['wagonY'] == 0))
    # ].dropna(subset=['wagonX', 'wagonY']).shape[0]

    # --- Core Filtering Logic (Team vs Player Mode) ---
    if player_name is None:
        valid_balls = local_df[local_df['wide'] == 0]
        valid_shots = valid_balls[~((valid_balls['wagonX'] == 0) & (valid_balls['wagonY'] == 0))]

        # ADD THESE TWO LINES:
        valid_shots['isFour'] = (valid_shots['outcome'] == 'four').astype(int)
        valid_shots['isSix'] = (valid_shots['outcome'] == 'six').astype(int)

        total_score = valid_shots['score'].sum() #score
        # total_4s = valid_shots['isFour'].sum()
        # total_6s = valid_shots['isSix'].sum()
        #logic update for generalization
        total_4s = (valid_shots['outcome'] == 'four').sum()
        total_6s = (valid_shots['outcome'] == 'six').sum()

        total_0s = (innings_valid_balls['batruns'] == 0).sum()
        total_1s = (innings_valid_balls['batruns'] == 1).sum()
        total_2s = (innings_valid_balls['batruns'] == 2).sum()
        total_3s = (innings_valid_balls['batruns'] == 3).sum()


        # balls_faced = valid_shots.shape[0]
        balls_faced = valid_balls.shape[0]

        # control_pct = round(
        #     (valid_balls[valid_balls['control'] == 1].shape[0]) / balls_faced * 100, 2 
        # )#shotControl to control

        # Control calculation like spike graph
        # controlled_balls = valid_balls[valid_balls['control'] == 1]
        # control_pct = round(len(controlled_balls) / len(valid_balls) * 100, 2) if len(valid_balls) > 0 else 0.0
        if len(valid_balls) == 0:
            control_pct = 0.0
        else:
            # Convert mixed-type control column to numeric FIRST
            control_numeric = pd.to_numeric(valid_balls['control'], errors='coerce')
            # Now count all 1.0 values (regardless of original type)
            controlled = (control_numeric == 1).sum()
            control_pct = round(controlled / len(valid_balls) * 100, 2)


        shot_summary = valid_shots.groupby('shot').agg({ #shot
            'score': 'sum', #score
            'isFour': 'sum', #we need to check the outcome column as four and six is there as strings
            'isSix': 'sum'
        }).sort_values(by='score', ascending=False) #score
    else:
        # valid_balls = local_df[local_df['wide'] == 0]
        valid_balls = local_df[(local_df['wide'] == 0) & (~local_df['control'].isna())]
        # valid_shots = local_df[
        #     ~((local_df['wagonX'] == 0) & (local_df['wagonY'] == 0))
        # ].dropna(subset=['wagonX', 'wagonY'])

        # ✅ ADD: Filter valid_shots the same way - exclude wides AND control nulls
        valid_shots = local_df[
            (local_df['wide'] == 0) & 
            ~((local_df['wagonX'] == 0) & (local_df['wagonY'] == 0)) &
            (~local_df['control'].isna())
        ].dropna(subset=['wagonX', 'wagonY'])

        # ADD THESE TWO LINES:
        valid_shots['isFour'] = (valid_shots['outcome'] == 'four').astype(int)
        valid_shots['isSix'] = (valid_shots['outcome'] == 'six').astype(int)

        total_score = valid_shots['batruns'].sum() #batruns
        # total_4s = valid_shots['isFour'].sum()
        # total_6s = valid_shots['isSix'].sum()
        total_4s = (valid_shots['outcome'] == 'four').sum()
        total_6s = (valid_shots['outcome'] == 'six').sum()
        
        total_0s = (innings_valid_balls['batruns'] == 0).sum()
        total_1s = (innings_valid_balls['batruns'] == 1).sum()
        total_2s = (innings_valid_balls['batruns'] == 2).sum()
        total_3s = (innings_valid_balls['batruns'] == 3).sum()

        # balls_faced = valid_shots.shape[0]
        # balls_faced = valid_balls.shape[0]

        # balls_faced_df = valid_balls.dropna(subset=['wagonX', 'wagonY'])
        # balls_faced_df = valid_shots
        balls_faced_df = valid_balls
        balls_faced = balls_faced_df.shape[0]  # ← Use the newly created balls_faced_df

        # control_pct = round(
        #     (valid_balls[valid_balls['control'] == 1].shape[0]) / balls_faced * 100, 2 
        # ) #shotControl to control
        
        #  Control calculation like spike graph
        # controlled_balls = valid_balls[valid_balls['control'] == 1]
        # control_pct = round(len(controlled_balls) / len(valid_balls) * 100, 2) if len(valid_balls) > 0 else 0.0
        if len(valid_balls) == 0:
            control_pct = 0.0
        else:
            # Convert mixed-type control column to numeric FIRST
            control_numeric = pd.to_numeric(valid_balls['control'], errors='coerce')
            # Now count all 1.0 values (regardless of original type)
            controlled = (control_numeric == 1).sum()
            control_pct = round(controlled / len(valid_balls) * 100, 2)

        shot_summary = valid_shots.groupby('shot').agg({ #shot
            'batruns': 'sum', #batruns
            'isFour': 'sum',
            'isSix': 'sum'
        }).sort_values(by='batruns', ascending=False) #batruns

    # Most Productive Shot
    if not shot_summary.empty:
        top_shot = shot_summary.iloc[0]
        top_shot_type = shot_summary.index[0]
        runs_col = 'score' if player_name is None else 'batruns' #score or batruns
        most_prod_shot_text = (
            # f"{top_shot_type.upper()}: {int(top_shot[runs_col])} runs,\n"
            f"{top_shot_type.upper()}: {int(top_shot[runs_col])} runs, "
            f"4s: {int(top_shot['isFour'])}, 6s: {int(top_shot['isSix'])}"
        )
    else:
        most_prod_shot_text = "No productive shot data"

    # Prepare data for quadrant plotting
    score_col = 'batruns' if player_name else 'score' #batruns or score
    player_data = valid_shots[['wagonX', 'wagonY', score_col, 'isFour', 'isSix']].copy()

    center_x, center_y = 180, 164
    def get_quadrant(x, y):
        angle = np.arctan2(y - center_y, x - center_x)
        degree = (np.degrees(angle) + 360) % 360
        return int(degree // 45)

    # player_data['quadrant'] = player_data.apply(lambda row: get_quadrant(row['wagonX'], row['wagonY']), axis=1)
    # # if not player_data.empty:
    # #     player_data['quadrant'] = player_data.apply(lambda row: get_quadrant(row['wagonX'], row['wagonY']), axis=1)
    # # else:
    # #     player_data['quadrant'] = pd.Series(dtype='int')
    # quadrant_totals = [player_data[player_data['quadrant'] == q][score_col].sum() for q in range(8)]
    # total_score = sum(quadrant_totals)

    # ✅ CHECK IF DATA IS EMPTY BEFORE ASSIGNING QUADRANT
    if not player_data.empty:
        player_data['quadrant'] = player_data.apply(lambda row: get_quadrant(row['wagonX'], row['wagonY']), axis=1)
        quadrant_totals = [player_data[player_data['quadrant'] == q][score_col].sum() for q in range(8)]
        total_score = sum(quadrant_totals)
    else:
        # Handle empty data case - initialize empty quadrant data
        quadrant_totals = [0] * 8
        total_score = 0

    # Plot
    fig, ax = plt.subplots(figsize=(7, 7), facecolor='none' if transparent else 'white')
    ax.set_facecolor('none' if transparent else 'white')

    # Draw ground and pitch
    boundary = plt.Circle((center_x, center_y), 180, color='#8c8c8c', fill=False, linewidth=1.2)
    batter_dot = plt.Circle((center_x, center_y), radius=3, edgecolor='black', facecolor='green', zorder=2)
    ax.add_artist(boundary)
    ax.add_artist(batter_dot)

    for angle in range(0, 360, 45):
        rad = np.deg2rad(angle)
        x_end = center_x + 180 * np.cos(rad)
        y_end = center_y + 180 * np.sin(rad)
        ax.plot([center_x, x_end], [center_y, y_end], color='#8c8c8c', linewidth=1.3)

    # ✅ HIGHLIGHT TOP ZONES ONLY IF THEY HAVE RUNS > 0
    top_quadrants = [i for i in sorted(range(8), key=lambda i: quadrant_totals[i], reverse=True) if quadrant_totals[i] > 0][:2]
    rank_color = {top_quadrants[i]: 1.0 - i * 0.3 for i in range(len(top_quadrants))}
    # cmap = cm.get_cmap('Blues')
    cmap = plt.colormaps['Blues']

    for i in range(8):
        theta1, theta2 = i * 45, (i + 1) * 45
        if i in rank_color:
            ax.add_patch(Wedge(center=(center_x, center_y), r=180, theta1=theta1, theta2=theta2,
                               color=cmap(rank_color[i]), alpha=0.3, zorder=0))
        mid_angle = np.deg2rad(theta1 + 22.5)
        label_x = center_x + 100 * np.cos(mid_angle)
        label_y = center_y + 100 * np.sin(mid_angle)
        ax.text(label_x, label_y, f"{quadrant_totals[i]} runs", fontsize=10.5,
                color='black' if i in top_quadrants else '#000',
                ha='center', va='center',fontweight = 'bold')

    # ✅ ADD "NO SHOTS" MESSAGE IF DATA IS EMPTY
    if player_data.empty:
        ax.text(180, 380, "No shots for selected filter(s)", ha='center', fontsize=13, color='red', fontweight='bold')

    # ax.set_xlim(-20, 470)
    # ax.set_ylim(-50, 370)
    ax.set_xlim(-20, 380)
    ax.set_ylim(-40, 600)
    ax.invert_yaxis()   
    ax.set_aspect('equal')
    ax.set_axis_off()

    # Determine team names
    # if not local_df.empty:
    #     team_bats = local_df['team_bat'].unique() 
    #     if len(team_bats) == 1:
    #         team_bat = team_bats[0]
    #         all_teams = df['team_bat'].unique().tolist() + df['team_bowl'].unique().tolist()
    #         team_bowl = [t for t in set(all_teams) if t != team_bat][0] if team_bat in all_teams else "Opponent"
    #     else:
    #         team_bowl = "All Teams"
    # else:
    #     team_bowl = "All Teams"
    
    # # Determine team names
    # if not local_df.empty:
    #     team_bats = local_df['team_bat'].unique() 
    #     if len(team_bats) == 1:
    #         team_bat = team_bats[0]
    #         # Filter by the same match to get correct opponent
    #         if mat_num is not None:
    #             match_df = df[df['p_match'] == mat_num]
    #         else:
    #             match_df = local_df
            
    #         # Get opponent from the same match
    #         team_bowls_in_match = match_df['team_bowl'].unique()
    #         team_bowl = [t for t in team_bowls_in_match if t != team_bat][0] if len(team_bowls_in_match) > 0 else "Opponents"
    #     else:
    #         team_bowl = "All Teams"
    # else:
    #     team_bowl = "All Teams"

    # if show_title:
    #     ax.set_title(
    #         f"{player_name} vs {team_bowl} | {competition} - Mat '{mat_num}', Inns: '{inns}'".upper(),
    #         fontsize=12, fontweight='bold', fontfamily='DejaVu Sans'
    #     )

    # # Metadata for title - DO THIS FIRST
    # if mat_num is None: mat_num = "All Mats"
    # if inns is None: inns = "All Inns"
    # if player_name is None: player_name = "All Players"
    # if competition is None: competition = "All Comps"
    
    # Determine team names ONLY if not provided as parameters
    if not local_df.empty:
        # Only detect team_bat if it wasn't provided as a filter
        if team_bat is None or team_bat == "All":
            team_bats = local_df['team_bat'].unique() 
            if len(team_bats) == 1:
                team_bat = team_bats[0]
            else:
                team_bat = "All Teams"
        
        # Only detect team_bowl if it wasn't provided as a filter
        if team_bowl is None or team_bowl == "All":
            if mat_num is not None and mat_num != "All Matches":
                match_df = df[df['p_match'] == mat_num]
            else:
                match_df = local_df
            
            team_bowls_in_match = match_df['team_bowl'].unique()
            opponents = [t for t in team_bowls_in_match if t != team_bat]
            
            if len(opponents) == 1:
                team_bowl = opponents[0]
            elif len(opponents) > 1:
                team_bowl = "All Teams"
            else:
                team_bowl = "Opponents"
    else:
        if team_bat is None: team_bat = "All Teams"
        if team_bowl is None: team_bowl = "All Teams"
    
    # Metadata for title - DO THIS FIRST
    if mat_num is None: mat_num = "All Mats"
    if inns is None: inns = "All Inns"
    if player_name is None: player_name = "All Players"
    if competition is None: competition = "All Comps"

    if show_title:
        # Determine title display (match spike graph logic)
        if player_name and player_name != "All Players":
            title_name = player_name
            title_opponent = team_bowl
        else:
            # For team view, show batting team from filtered data
            if not local_df.empty:
                batting_teams_display = local_df['team_bat'].unique()
                if len(batting_teams_display) == 1:
                    title_name = batting_teams_display[0]  # Show actual team name
                    title_opponent = team_bowl
                else:
                    title_name = "All Players"
                    title_opponent = team_bowl
            else:
                title_name = "All Players"
                title_opponent = "All Teams"
        
        # ax.set_title(
        #     f"{title_name} vs {title_opponent} | {competition} - Mat '{mat_num}', Inns: '{inns}'".upper(),
        #     fontsize=12, fontweight='bold', fontfamily='DejaVu Sans'
        # )
        # title_text = f"{title_name} vs {title_opponent} | {competition} - Mat '{mat_num}', Inns: '{inns}'".upper()

        title_parts = []

        if 'title' in title_components:
            title_parts.append(f"{title_name} vs {title_opponent}")
    
        if 'filters' in title_components:
            title_parts.append(f"{competition} - Mat '{mat_num}', Inns: '{inns}'")
        
        title_text = " | ".join(title_parts).upper()

    # Text Summary
    if show_summary:
        ax.text(180, 420, f"Total Runs: {innings_runs} ({innings_balls} balls) | Strike Rate: {round((innings_runs/innings_balls)*100, 2) if balls_faced > 0 else 0.0}",
                fontsize=11, ha='center', fontweight='bold', color='darkgreen')
        # # ax.text(180, 438, f"4s x {total_4s} | 6s x {total_6s}",
        # ax.text(180, 438, f"0s x {total_0s} | 1s x {total_1s} | 4s x {total_4s} | 6s x {total_6s}",
        #         fontsize=11, ha='center', color='darkgreen')

    if show_shots_breakdown:
        # Build breakdown text dynamically
        breakdown_parts = []
        if '0s' in shots_breakdown_options:
            breakdown_parts.append(f"0s x {total_0s}")
        if '1s' in shots_breakdown_options:
            breakdown_parts.append(f"1s x {total_1s}")
        if '2s' in shots_breakdown_options:
            breakdown_parts.append(f"2s x {total_2s}")
        if '3s' in shots_breakdown_options:
            breakdown_parts.append(f"3s x {total_3s}")
        if '4s' in shots_breakdown_options:
            breakdown_parts.append(f"4s x {total_4s}")
        if '6s' in shots_breakdown_options:
            breakdown_parts.append(f"6s x {total_6s}")
        
        if breakdown_parts:  # Only show if something selected
            breakdown_text = " | ".join(breakdown_parts)
            ax.text(180, 438, breakdown_text, fontsize=11, ha='center', color='darkgreen')

    # if runs_count:
    #     ax.text(430, 140, f"{total_score} ({balls_faced} balls)",
    #             fontsize=11, ha='center', fontweight='bold')

    # if show_fours_sixes:
    #     ax.text(430, 155, f"4s: {int(player_data['isFour'].sum())} | 6s: {int(player_data['isSix'].sum())}",
    #             fontsize=11, ha='center', color='darkgreen')

    # if show_control:
    #     ax.text(430, 80, f"Control: {control_pct}%", fontsize=12, ha='center',
    #             color='purple', fontweight='bold')

    # if show_prod_shot:
    #     ax.text(430, 250, f"Productive Shot:\n{most_prod_shot_text}", fontsize=11,
    #             ha='center', color='navy', fontweight='bold')

    # if show_bowler:
    #     if bowler_name is None:
    #         bowler_name = 'All Bowlers'
    #     ax.text(430, 170, f"vs {bowler_name}", fontsize=11, ha='center',
    #             color='blue', fontweight='bold')

    
    #  update the positions of the summary texts
    if runs_count:
        if not show_fours_sixes and not show_bowler:
            ax.text(180, 475, f"{total_score} ({balls_faced} balls)",
                fontsize=11, ha='center', fontweight='bold')
        else:
            ax.text(30, 475, f"{total_score} ({balls_faced} balls)",
                fontsize=11, ha='center', fontweight='bold')
        # ax.text(50, 475, f"{total_score} ({balls_faced} balls)",
        #         fontsize=11, ha='center', fontweight='bold')

    if show_fours_sixes:
        if not runs_count  and not show_bowler:
            ax.text(180, 475, f"4s: {int(player_data['isFour'].sum())} | 6s: {int(player_data['isSix'].sum())}",
                fontsize=11, ha='center', color='darkgreen')
        else:
            ax.text(180, 475, f" | 4s: {int(player_data['isFour'].sum())} | 6s: {int(player_data['isSix'].sum())}",
                fontsize=11, ha='center', color='darkgreen')
        # ax.text(180, 475, f" | 4s: {int(player_data['isFour'].sum())} | 6s: {int(player_data['isSix'].sum())}",
        #         fontsize=11, ha='center', color='darkgreen')
    
    if show_bowler:
        if bowler_name is None:
            bowler_name = 'All Bowlers'

        if not runs_count and not show_fours_sixes:
            ax.text(180, 475, f"vs {bowler_name}", fontsize=11, ha='center',
                color='blue', fontweight='bold')
        else:
            ax.text(360, 475, f" | vs {bowler_name}", fontsize=11, ha='center',
                color='blue', fontweight='bold')
        # ax.text(300, 475, f" | vs {bowler_name}", fontsize=11, ha='center',
        #         color='blue', fontweight='bold')

    if show_title:
        # ax.text(180, 400, title_text, fontsize=12, ha='center', 
        #     fontweight='bold', fontfamily='DejaVu Sans')
        # Adjust position based on title length
        if len(title_components) == 1:
            # Shorter title - keep centered
            title_x = 180
            title_y = 400  # Slightly lower for single line
            ax.set_xlim(-60, 420)
        else:
            # Full title - original position
            title_x = 180
            title_y = 400
        
        ax.text(title_x, title_y, title_text, fontsize=12, ha='center', 
                fontweight='bold', fontfamily='DejaVu Sans')
    
    if show_control:
        ax.text(180, 458, f"Control: {control_pct}%", fontsize=12, ha='center',
                color='purple', fontweight='bold')

    if show_prod_shot:
        ax.text(180, 495, f"Productive Shot: {most_prod_shot_text}", fontsize=11,
                ha='center', color='navy', fontweight='bold')

        
    if show_overs:
        # 1. Format Overs text
        if over_values is None:
            over_text = "All"
        elif len(over_values) <= 10:
            over_text = ", ".join(map(str, sorted(over_values)))
        else:
            over_text = f"{min(over_values)}-{max(over_values)} ({len(over_values)} overs)"

        if not show_phase:
            ax.text(180, 520, f"Overs: {over_text}", 
                fontsize=10, ha='center', color='darkslategrey', fontweight='bold')
        else:
            ax.text(100, 520, f"Overs: {over_text}", 
                fontsize=10, ha='center', color='darkslategrey', fontweight='bold')
        # 3. Display on plot (below productive shot at 430, 250)
        # ax.text(100, 520, f"Overs: {over_text}", 
        #         fontsize=10, ha='center', color='darkslategrey', fontweight='bold')
        
    if show_phase:
        # 2. Format Phase text
        phase_names = {
            1: "Powerplay (1-6)",
            2: "Middle (7-15)", 
            3: "Slog (16-20)"
        }
        # phase_text = phase_names.get(phase, "All")

        if isinstance(phase, list):
            phase_text = ", ".join([phase_names.get(p, str(p)) for p in phase]) if phase else "All"
        else:
            phase_text = phase_names.get(phase, "All")

        if not show_overs:
            ax.text(180, 520, f"Phase: {phase_text}", 
                fontsize=10, ha='center', color='crimson', fontweight='bold')
        else:
            ax.text(240, 520, f"Phase: {phase_text}", 
                fontsize=10, ha='center', color='crimson', fontweight='bold')

        # ax.text(220, 520, f"Phase: {phase_text}", 
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
            ax.text(180, 540, f"Bowl Type: {bowl_type_text}", 
                    fontsize=10, ha='center', color='darkviolet', fontweight='bold')
        else:
            # ax.text(70, 540, f"Bowl Type: {bowl_type_text}", 
            ax.text(180, 540, f"Bowl Type: {bowl_type_text}", 
                    fontsize=10, ha='center', color='darkviolet', fontweight='bold')

    if show_venue:
        if ground is None or len(ground) == 0:
            ground = "All Venues"
        elif len(ground) == 1:
            ground = ground[0]
        else:
            ground = ", ".join(ground)

        ax.text(180, 580, f"Venue: {ground}", 
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
            ax.text(180, 560, f"Bowl Pace: {bowl_kind_text.capitalize()}", 
            # ax.text(180, 540, f"Bowl Pace: {bowl_kind_text}", 
                    fontsize=10, ha='center', color='teal', fontweight='bold')
        else:
            # ax.text(290, 540, f"Bowl Pace: {bowl_kind_text}", 
            ax.text(70, 560, f"Bowl Pace: {bowl_kind_text.capitalize()}", 
                    fontsize=10, ha='center', color='teal', fontweight='bold')


    if show_bowl_arm:
        # Format bowl_arm text
        if bowl_arm is None or len(bowl_arm) == 0:
            bowl_arm_text = "All"
        elif len(bowl_arm) == 1:
            bowl_arm_text = bowl_arm[0]
        else:
            bowl_arm_text = ", ".join(bowl_arm)
        
        # responsive
        if not show_bowl_kind:
            ax.text(180, 560, f"Bowl Arm: {bowl_arm_text}", 
                    fontsize=10, ha='center', color='saddlebrown', fontweight='bold')
        else:
            ax.text(290, 560, f"Bowl Arm: {bowl_arm_text}", 
                    fontsize=10, ha='center', color='saddlebrown', fontweight='bold')
        
    

    # plt.subplots_adjust(left=0.05, right=0.95, top=0.93, bottom=0.07)
    plt.subplots_adjust(left=0.05, right=0.95, top=0.93, bottom=0.02)
    plt.close(fig)
    return fig
    # plt.show()
