# coding: utf-8

# In[4]:

import csv
import sqlite3 as lite

from pandas import *


class PrepareForML(object):
    # Prepares the raw data scrapped from sport-reference.com and turns it into a 
    # form that can be digested by the scikit-learn classes

    def __init__(self, scoring_filename, nba_db_name, team_stats_csv_filename):
        self.scoring_filename = scoring_filename
        self.nba_db_name = nba_db_name
        self.team_stats_csv_filename = team_stats_csv_filename

    def __call__(self, features_filename):
        # Looping through the csv file 'nba_game_stats_year1_year2.csv" and creates a feature vector
        # for each game played. The results are stored in an array 'nba_features.npz' in the current directory

        self.process_raw_data(self.team_stats_csv_filename)

        con = lite.connect(self.nba_db_name)
        with con:
            cur = con.cursor()

            features = []
            results = []
            with open(self.scoring_filename, 'rb') as csvfile:
                games = csv.reader(csvfile)
                games.next()

                for game in games:
                    feature, result = self.process_game(game, cur)

                    if result is not None:
                        features.append(feature)
                        results.append(result)

        self.features = features
        # Save features and results to file
        features = np.vstack(features)
        results = np.array(results)
        # Storing the features and results into the 'features_filename' file for further predictive analysis
        np.savez(features_filename, X=features, y=results)

    @staticmethod
    def process_game(game, cursor):
        # The input frame is a list that contains the following elements:
        #  Season_Yr, Visitor_Team, V_PTS, Home_Team, Home_PTS
        # These elements refer to match. This function queries the SQL database
        #  'nba_db_name' created via the 'process_raw_data'
        # function and returns the differences and ratios between features of both Home and Visitor teams for each game.         
        # The result of the match is the target variable:
        # 1 if the Home_Team scored more than the Visitor_Team, 0 otherwise

        query = 'SELECT * FROM Team_Stats WHERE Team = ? AND Season_Yr = ?'

        try:
            # Slicing the game in the game_stats file
            year, t1, p1, t2, p2 = game
            # Converting numbers in integers
            year, p1, p2 = map(int, [year, p1, p2])
            # Execute the query on team1 and year
            cursor.execute(query, (t1, year))
            # create list of feature for that team
            feature1 = list(cursor.fetchone()[2::])
            # Execute the query on team2 and year
            cursor.execute(query, (t2, year))
            # create list of feature for that team
            feature2 = list(cursor.fetchone()[2::])
            # Create a list being the difference between home team and visitor team features
            feature = np.array(feature2) - np.array(feature1)
            # The implementation of these steps (and this function) will be within an iteration on the game_stats file

            # Calculate result of game 
            if (p2 - p1) > 0:
                result = 1
            else:
                result = 0

            return feature, result

        except ValueError:
            return None, None

        except TypeError:
            return None, None

    def process_raw_data(self, team_stats_csv_filename, what_to_do='sql'):
        # Processes the team_stats file containing team data. If what_to_do = csv,
        #  then a csv file is output. If set to 'sql',
        # then a sqlite table named 'Team_Stats' is created in the database titled 'nba_db_name'

        df = read_csv(team_stats_csv_filename)
        features = ['WP', 'MOV', 'SOS', 'SRS', 'ORtg', 'DRtg', 'Pace', 'FTr', '3PAr', 'TS_Perc', 'O_eFG_Perc',
                    'O_TOV_Perc', 'ORB_Perc', 'O_FT_per_FGA', 'D_eFG_Perc', 'D_TOV_Perc', 'DRB_Perc', 'D_FT_per_FGA']

        df_out = df[features]
        df_out.insert(0, 'Team', df['Team'])
        df_out.insert(1, 'Season_Yr', df['Season_Yr'])

        if what_to_do == 'sql':
            # Export to SQL table
            con = lite.connect(self.nba_db_name)
            with con:
                cur = con.cursor()
                df_out.to_sql('Team_Stats', con, if_exists='replace', index=False)
                # Add index to Team and Year columns
                cur.execute('CREATE INDEX tp_index ON Team_Stats(Team, Season_Yr);')
        elif what_to_do == 'csv':
            # Export to csv file
            output_name = team_stats_csv_filename.replace('.csv', '_processed.csv')
            df_out.to_csv(output_name, mode='w+')
