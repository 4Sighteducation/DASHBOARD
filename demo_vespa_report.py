#!/usr/bin/env python3
"""
Sample College - VESPA Comparative Analysis Report Generator (Demo Version)
Generates comprehensive analysis of VESPA data across cycles and departments
This is an anonymized demo version for marketing purposes
"""

import pandas as pd
import numpy as np
import json
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import warnings
from datetime import datetime
from scipy import stats
import os

warnings.filterwarnings('ignore')

class DemoVESPAAnalyzer:
    def __init__(self):
        """Initialize the demo VESPA data analyzer"""
        self.vespa_categories = ['Vision', 'Effort', 'Systems', 'Practice', 'Attitude']
        self.vespa_colors = {
            'Vision': '#e59437',     # Orange
            'Effort': '#86b4f0',      # Light Blue
            'Systems': '#72cb44',     # Green
            'Practice': '#7f31a4',    # Purple
            'Attitude': '#f032e6',    # Pink
            'Overall': '#ffd700'      # Gold/Yellow
        }
        
        # National distribution data - hardcoded from Knack object_120
        self.national_distributions = {
            'cycle_1': {
                'Vision': {1: 96, 2: 269, 3: 638, 4: 482, 5: 610, 6: 1262, 7: 615, 8: 977, 9: 368, 10: 494},
                'Effort': {1: 320, 2: 218, 3: 899, 4: 681, 5: 774, 6: 864, 7: 732, 8: 516, 9: 639, 10: 168},
                'Systems': {1: 345, 2: 391, 3: 685, 4: 997, 5: 540, 6: 1116, 7: 529, 8: 757, 9: 239, 10: 212},
                'Practice': {1: 206, 2: 268, 3: 520, 4: 792, 5: 1060, 6: 583, 7: 947, 8: 686, 9: 449, 10: 300},
                'Attitude': {1: 219, 2: 393, 3: 681, 4: 581, 5: 698, 6: 1198, 7: 688, 8: 769, 9: 389, 10: 195},
                'Overall': {1: 43, 2: 151, 3: 493, 4: 864, 5: 1167, 6: 1262, 7: 936, 8: 593, 9: 228, 10: 74},
                'total': 5811
            },
            'cycle_2': {
                'Vision': {1: 56, 2: 185, 3: 552, 4: 414, 5: 530, 6: 1261, 7: 735, 8: 1066, 9: 376, 10: 496},
                'Effort': {1: 216, 2: 183, 3: 837, 4: 623, 5: 813, 6: 855, 7: 819, 8: 541, 9: 618, 10: 166},
                'Systems': {1: 265, 2: 277, 3: 598, 4: 862, 5: 549, 6: 1256, 7: 612, 8: 800, 9: 240, 10: 212},
                'Practice': {1: 151, 2: 207, 3: 440, 4: 715, 5: 1060, 6: 506, 7: 1024, 8: 774, 9: 490, 10: 304},
                'Attitude': {1: 142, 2: 270, 3: 563, 4: 510, 5: 670, 6: 1195, 7: 800, 8: 838, 9: 440, 10: 243},
                'Overall': {1: 16, 2: 122, 3: 351, 4: 744, 5: 1048, 6: 1309, 7: 1133, 8: 621, 9: 226, 10: 101},
                'total': 5671
            },
            'cycle_3': {
                'Vision': {1: 44, 2: 95, 3: 358, 4: 214, 5: 281, 6: 772, 7: 485, 8: 712, 9: 258, 10: 421},
                'Effort': {1: 125, 2: 95, 3: 508, 4: 409, 5: 386, 6: 527, 7: 538, 8: 378, 9: 472, 10: 202},
                'Systems': {1: 158, 2: 166, 3: 392, 4: 506, 5: 299, 6: 780, 7: 360, 8: 572, 9: 182, 10: 225},
                'Practice': {1: 87, 2: 114, 3: 242, 4: 375, 5: 592, 6: 331, 7: 634, 8: 544, 9: 389, 10: 332},
                'Attitude': {1: 75, 2: 182, 3: 337, 4: 341, 5: 377, 6: 704, 7: 558, 8: 537, 9: 311, 10: 218},
                'Overall': {1: 16, 2: 63, 3: 252, 4: 415, 5: 566, 6: 749, 7: 732, 8: 484, 9: 224, 10: 139},
                'total': 3640
            }
        }
        
        # National statistics
        self.national_stats = {
            'cycle_1': {
                'Vision': {'mean': 6.1, 'std_dev': 2.3},
                'Effort': {'mean': 5.49, 'std_dev': 2.38},
                'Systems': {'mean': 5.27, 'std_dev': 2.33},
                'Practice': {'mean': 5.75, 'std_dev': 2.29},
                'Attitude': {'mean': 5.59, 'std_dev': 2.28},
                'Overall': {'mean': 5.64, 'std_dev': 1.75}
            },
            'cycle_2': {
                'Vision': {'mean': 6.34, 'std_dev': 2.19},
                'Effort': {'mean': 5.65, 'std_dev': 2.29},
                'Systems': {'mean': 5.52, 'std_dev': 2.24},
                'Practice': {'mean': 5.98, 'std_dev': 2.24},
                'Attitude': {'mean': 5.93, 'std_dev': 2.21},
                'Overall': {'mean': 5.88, 'std_dev': 1.69}
            },
            'cycle_3': {
                'Vision': {'mean': 6.55, 'std_dev': 2.24},
                'Effort': {'mean': 5.94, 'std_dev': 2.39},
                'Systems': {'mean': 5.73, 'std_dev': 2.35},
                'Practice': {'mean': 6.35, 'std_dev': 2.31},
                'Attitude': {'mean': 6.07, 'std_dev': 2.26},
                'Overall': {'mean': 6.13, 'std_dev': 1.84}
            }
        }
        
    def load_data(self):
        """Load all necessary data files"""
        print("Loading data files...")
        
        # Load VESPA results
        self.results_df = pd.read_csv('dashboard-frontend/NPTCResults2425.csv')
        print(f"Loaded {len(self.results_df)} student records")
        
        # Load question responses
        self.questions_df = pd.read_csv('dashboard-frontend/NPTCQQs2425.csv')
        print(f"Loaded {len(self.questions_df)} question response records")
        
        # Load statement mappings
        with open('AIVESPACoach/question_id_to_text_mapping.json', 'r') as f:
            self.question_mapping = json.load(f)
        
        # Add the proper statement text mapping - handle all possible variations
        self.statement_texts = {
            'Q1v': "I've worked out the next steps in my life",
            'Q2s': "I plan and organise my time to get my work done",
            'Q3v': "I give a lot of attention to my career planning",
            'Q4e': "I complete all my homework on time",
            'Q4s': "I complete all my homework on time",  # Some variations exist
            'Q5v': "No matter who you are, you can change your intelligence a lot",
            'Q5a': "No matter who you are, you can change your intelligence a lot",  # Alternative mapping
            'Q6e': "I use all my independent study time effectively",
            'Q7p': "I test myself on important topics until I remember them",
            'Q8a': "I have a positive view of myself",
            'Q9e': "I am a hard working student",
            'Q10a': "I am confident in my academic ability",
            'Q11e': "I always meet deadlines",
            'Q12p': "I spread out my revision, rather than cramming at the last minute",
            'Q13a': "I don't let a poor test/assessment result get me down for too long",
            'Q14e': "I strive to achieve the goals I set for myself",
            'Q14v': "I strive to achieve the goals I set for myself",  # Also Vision variant
            'Q15': "I strive to achieve the goals I set for myself",  # Main Q15
            'Q15e': "I strive to achieve the goals I set for myself",  # Effort variant
            'Q15v': "I strive to achieve the goals I set for myself",  # Vision variant
            'Q15p': "I strive to achieve the goals I set for myself",  # Practice variant
            'Q15s': "I summarise important information in diagrams, tables or lists",
            'Q16v': "I enjoy learning new things",
            'Q17e': "I'm not happy unless my work is the best it can be",
            'Q18s': "I take good notes in class which are useful for revision",
            'Q19p': "When revising I mix different kinds of topics/subjects in one study session",
            'Q20a': "I feel I can cope with the pressure at school/college/University",
            'Q21e': "I work as hard as I can in most classes",
            'Q22s': "My books/files are organised",
            'Q23p': "When preparing for a test/exam I teach someone else the material",
            'Q24a': "I'm happy to ask questions in front of a group",
            'Q25s': "I use highlighting/colour coding for revision",
            'Q26v': "Your intelligence is something about you that you can change very much",
            'Q26a': "Your intelligence is something about you that you can change very much",  # Alternative
            'Q27p': "I like hearing feedback about how I can improve",
            'Q27a': "I like hearing feedback about how I can improve",  # Also Attitude variant
            'Q28a': "I can control my nerves in tests/practical assessments",
            'Q29v': "I understand why education is important for my future",
            'Q30v': "I have the support I need to achieve this year",
            'Q31p': "I feel equipped to face the study and revision challenges this year",
            'Q32a': "I am confident I will achieve my potential in my final exams"
        }
        
        print(f"Loaded {len(self.question_mapping)} statement mappings")
        
        # Load tutor accounts for faculty mapping
        self.accounts_df = pd.read_csv('dashboard-frontend/accounts (38).csv')
        print(f"Loaded {len(self.accounts_df)} tutor accounts")
        
        # Clean data
        self._clean_data()
        
    def _clean_data(self):
        """Clean and prepare the data"""
        # Convert numeric columns
        vespa_cols = ['Vision', 'Effort', 'Systems', 'Practice', 'Attitude', 'Overall']
        cycle_cols = ['V1', 'E1', 'S1', 'P1', 'A1', 'O1', 
                     'V2', 'E2', 'S2', 'P2', 'A2', 'O2',
                     'V3', 'E3', 'S3', 'P3', 'A3', 'O3']
        
        for col in vespa_cols + cycle_cols:
            if col in self.results_df.columns:
                self.results_df[col] = pd.to_numeric(self.results_df[col], errors='coerce')
        
        # Create tutor email to faculty mapping from accounts
        email_to_faculty = {}
        tutor_to_faculty = {}  # Fallback for name matching
        faculty_names = {
            'SFA': 'Department of Sport & Wellness',
            'CVP': 'Department of Arts & Media',
            'SPS': 'Department of Public Services',
            'BTM': 'Department of Business Studies',
            'HSC': 'Department of Health Sciences',
            'HAT': 'Department of Beauty & Wellbeing',
            'CIT': 'Department of Digital Technologies',
            'ENG': 'Department of Engineering',
            'CHA': 'Department of Trades & Hospitality',
            'BES': 'Department of Foundation Studies'
        }
        
        # Process accounts data to create email-based mapping
        for _, row in self.accounts_df.iterrows():
            email = row['Email']
            name = row['Name']
            subject = row['Subject']
            
            # Primary mapping: email to faculty
            if pd.notna(email) and pd.notna(subject):
                # Clean email (lowercase, strip whitespace)
                clean_email = str(email).strip().lower()
                email_to_faculty[clean_email] = subject
            
            # Secondary mapping: name to faculty (as fallback)
            if pd.notna(name) and pd.notna(subject):
                tutor_to_faculty[name] = subject
                # Also try just the full name without title
                if ' ' in str(name):
                    parts = str(name).split(' ', 1)
                    if len(parts) > 1:
                        tutor_to_faculty[parts[1]] = subject  # Without title
                
        print(f"Created email mapping for {len(email_to_faculty)} tutors")
        print(f"Created name mapping for {len(tutor_to_faculty)} tutors (fallback)")
        
        # Apply faculty mapping using email first, then fallback to name
        def map_to_faculty(row):
            # Try email mapping first
            if pd.notna(row['Tutor Email']):
                clean_email = str(row['Tutor Email']).strip().lower()
                if clean_email in email_to_faculty:
                    return email_to_faculty[clean_email]
            
            # Fallback to name mapping
            if pd.notna(row['Group']) and row['Group'] in tutor_to_faculty:
                return tutor_to_faculty[row['Group']]
            
            return None
        
        self.results_df['Faculty_Code'] = self.results_df.apply(map_to_faculty, axis=1)
        self.results_df['Faculty_Name'] = self.results_df['Faculty_Code'].map(faculty_names)
        
        # Count how many students were mapped
        mapped_count = self.results_df['Faculty_Code'].notna().sum()
        print(f"Mapped {mapped_count} of {len(self.results_df)} students to faculties")
        
        # Get unique faculties
        self.faculties = self.results_df['Faculty_Code'].dropna().unique()
        self.tutor_groups = self.results_df['Group'].dropna().unique()
        
        # Print faculty distribution
        faculty_counts = self.results_df['Faculty_Code'].value_counts()
        print("\nFaculty Distribution:")
        for code, count in faculty_counts.head(10).items():
            name = faculty_names.get(code, code)
            print(f"  {code} ({name}): {count} students")
        
    def analyze_cycle_progression(self):
        """Analyze progression between cycles"""
        analysis = {
            'cycle_comparison': {},
            'improvements': {},
            'statistics': {}
        }
        
        # Compare Cycle 1 to Cycle 2
        for cat in self.vespa_categories:
            c1_col = f'{cat[0]}1'
            c2_col = f'{cat[0]}2'
            c3_col = f'{cat[0]}3'
            
            # Cycle 1 to 2
            if c1_col in self.results_df.columns and c2_col in self.results_df.columns:
                c1_data = self.results_df[c1_col].dropna()
                c2_data = self.results_df[c2_col].dropna()
                
                # Find students with both cycles
                both_cycles = self.results_df[[c1_col, c2_col]].dropna()
                if len(both_cycles) > 0:
                    improvement = both_cycles[c2_col] - both_cycles[c1_col]
                    
                    analysis['cycle_comparison'][f'{cat}_C1_to_C2'] = {
                        'mean_c1': c1_data.mean(),
                        'mean_c2': c2_data.mean(),
                        'mean_improvement': improvement.mean(),
                        'std_improvement': improvement.std(),
                        'percent_improved': (improvement > 0).sum() / len(improvement) * 100,
                        'n_students': len(both_cycles),
                        'cohen_d': self._calculate_cohens_d(both_cycles[c1_col], both_cycles[c2_col])
                    }
            
            # Cycle 2 to 3
            if c2_col in self.results_df.columns and c3_col in self.results_df.columns:
                both_cycles = self.results_df[[c2_col, c3_col]].dropna()
                if len(both_cycles) > 0:
                    improvement = both_cycles[c3_col] - both_cycles[c2_col]
                    
                    analysis['cycle_comparison'][f'{cat}_C2_to_C3'] = {
                        'mean_c2': both_cycles[c2_col].mean(),
                        'mean_c3': both_cycles[c3_col].mean(),
                        'mean_improvement': improvement.mean(),
                        'std_improvement': improvement.std(),
                        'percent_improved': (improvement > 0).sum() / len(improvement) * 100,
                        'n_students': len(both_cycles),
                        'cohen_d': self._calculate_cohens_d(both_cycles[c2_col], both_cycles[c3_col])
                    }
            
            # Full progression Cycle 1 to 3 (for students who completed all)
            if c1_col in self.results_df.columns and c3_col in self.results_df.columns:
                all_three = self.results_df[[c1_col, c2_col, c3_col]].dropna()
                if len(all_three) > 0:
                    overall_improvement = all_three[c3_col] - all_three[c1_col]
                    
                    analysis['cycle_comparison'][f'{cat}_C1_to_C3_overall'] = {
                        'mean_c1': all_three[c1_col].mean(),
                        'mean_c2': all_three[c2_col].mean(),
                        'mean_c3': all_three[c3_col].mean(),
                        'overall_improvement': overall_improvement.mean(),
                        'percent_improved_overall': (overall_improvement > 0).sum() / len(overall_improvement) * 100,
                        'n_students': len(all_three)
                    }
        
        return analysis
    
    def _calculate_cohens_d(self, group1, group2):
        """Calculate Cohen's d effect size"""
        n1, n2 = len(group1), len(group2)
        var1, var2 = group1.var(), group2.var()
        
        # Pooled standard deviation
        pooled_std = np.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))
        
        # Cohen's d
        if pooled_std > 0:
            return (group2.mean() - group1.mean()) / pooled_std
        return 0
    
    def analyze_faculty_comparison(self):
        """Compare performance across faculties"""
        faculty_analysis = {}
        
        # We'll analyze using the most recent available data for each student
        # but count ALL students in each faculty, not just those with cycle 3 data
        
        # Determine which columns to use for current analysis
        current_cycle_data = {}
        for cat in self.vespa_categories:
            cat_initial = cat[0]  # V, E, S, P, A
            # Use cycle 1 data as baseline (most students have this)
            col = f'{cat_initial}1'
            if col in self.results_df.columns:
                current_cycle_data[cat] = col
        
        # Also add Overall
        col = 'O1'
        if col in self.results_df.columns:
            current_cycle_data['Overall'] = col
        
        # Add overall college stats
        faculty_analysis['OVERALL'] = {
            'n_students': len(self.results_df),
            'current_cycle': {}
        }
        
        for cat, col in current_cycle_data.items():
            if col in self.results_df.columns:
                scores = self.results_df[col].dropna()
                if len(scores) > 0:
                    faculty_analysis['OVERALL']['current_cycle'][cat] = {
                        'mean': scores.mean(),
                        'std': scores.std(),
                        'median': scores.median(),
                        'q1': scores.quantile(0.25),
                        'q3': scores.quantile(0.75),
                        'n': len(scores)
                    }
        
        # Analyze by faculty
        for faculty in self.faculties:
            if pd.isna(faculty):
                continue
                
            faculty_data = self.results_df[self.results_df['Faculty_Code'] == faculty]
            total_faculty_students = len(faculty_data)  # Count ALL students in this faculty
            
            if total_faculty_students > 5:  # Only analyze faculties with sufficient data
                faculty_analysis[faculty] = {
                    'n_students': total_faculty_students,  # Use total count, not just those with data
                    'current_cycle': {}
                }
                
                # Analyze using cycle 1 data (most complete)
                for cat, col in current_cycle_data.items():
                    if col in faculty_data.columns:
                        scores = faculty_data[col].dropna()
                        if len(scores) > 0:
                            faculty_analysis[faculty]['current_cycle'][cat] = {
                                'mean': scores.mean(),
                                'std': scores.std(),
                                'median': scores.median(),
                                'q1': scores.quantile(0.25),
                                'q3': scores.quantile(0.75),
                                'n': len(scores)  # This is how many have data for this metric
                            }
                
                # Analyze progression for completeness
                for i, cat_initial in enumerate(['V', 'E', 'S', 'P', 'A']):
                    c1_col, c2_col = f'{cat_initial}1', f'{cat_initial}2'
                    if c1_col in faculty_data.columns and c2_col in faculty_data.columns:
                        both = faculty_data[[c1_col, c2_col]].dropna()
                        if len(both) > 0:
                            improvement = both[c2_col] - both[c1_col]
                            faculty_analysis[faculty][f'{self.vespa_categories[i]}_progression'] = {
                                'mean_improvement': improvement.mean(),
                                'percent_improved': (improvement > 0).sum() / len(improvement) * 100
                            }
        
        return faculty_analysis
    
    def analyze_statements(self):
        """Comprehensive statement-level analysis across all cycles"""
        statement_analysis = {
            'top_statements': [],
            'bottom_statements': [],
            'cycle_progression': {},
            'faculty_differences': {},
            'vespa_category_breakdown': {},
            'most_improved': [],
            'most_declined': []
        }
        
        # Use the proper statement text mapping
        q_text_map = self.statement_texts
        
        # Process question responses for each cycle
        cycle_question_data = {1: {}, 2: {}, 3: {}}
        
        for col in self.questions_df.columns:
            if col.startswith('c') and '_Q' in col:
                # Parse column name (e.g., 'c1_Q1v' -> cycle 1, question 1, vision)
                parts = col.split('_')
                if len(parts) == 2 and parts[1].startswith('Q'):
                    cycle_num = int(parts[0][1])  # Extract cycle number
                    q_part = parts[1].upper()  # e.g., 'Q1V'
                    
                    # Calculate mean score for this question in this cycle
                    scores = pd.to_numeric(self.questions_df[col], errors='coerce').dropna()
                    if len(scores) > 0:
                        if q_part not in cycle_question_data[cycle_num]:
                            cycle_question_data[cycle_num][q_part] = {
                                'mean': scores.mean(),
                                'std': scores.std(),
                                'count': len(scores),
                                'scores': scores.tolist()
                            }
        
        # Analyze progression for each question across cycles
        all_questions = set()
        for cycle_data in cycle_question_data.values():
            all_questions.update(cycle_data.keys())
        
        for q_id in all_questions:
            q_progression = {}
            
            # Get scores for each cycle
            for cycle in [1, 2, 3]:
                if q_id in cycle_question_data[cycle]:
                    q_progression[f'cycle_{cycle}'] = cycle_question_data[cycle][q_id]
            
            # Calculate improvements
            if 'cycle_1' in q_progression and 'cycle_2' in q_progression:
                q_progression['c1_to_c2'] = q_progression['cycle_2']['mean'] - q_progression['cycle_1']['mean']
            
            if 'cycle_2' in q_progression and 'cycle_3' in q_progression:
                q_progression['c2_to_c3'] = q_progression['cycle_3']['mean'] - q_progression['cycle_2']['mean']
            
            if 'cycle_1' in q_progression and 'cycle_3' in q_progression:
                q_progression['c1_to_c3'] = q_progression['cycle_3']['mean'] - q_progression['cycle_1']['mean']
            
            # Store with statement text - properly map to actual text
            # Try to find matching statement in our mapping
            statement_text = None
            for key, text in q_text_map.items():
                if key.upper() == q_id.upper():
                    statement_text = text
                    break
            if not statement_text:
                statement_text = f"Statement {q_id}"
            
            # Determine VESPA category
            cat_map = {'V': 'Vision', 'E': 'Effort', 'S': 'Systems', 'P': 'Practice', 'A': 'Attitude'}
            vespa_cat = cat_map.get(q_id[-1] if q_id else '', 'Unknown')
            
            statement_analysis['cycle_progression'][q_id] = {
                'text': statement_text,
                'category': vespa_cat,
                **q_progression
            }
        
            # Find most improved statements (Cycle 1 to 3 overall improvement)
            improvements = []
            for q_id, data in statement_analysis['cycle_progression'].items():
                if 'c1_to_c3' in data:
                    improvements.append((q_id, data['c1_to_c3'], data))
        
        improvements.sort(key=lambda x: x[1], reverse=True)
        statement_analysis['most_improved'] = [
            {
                'statement': imp[0],
                'text': imp[2]['text'],
                'category': imp[2]['category'],
                'improvement': imp[1],
                'cycle_2_mean': imp[2].get('cycle_2', {}).get('mean', 0),
                'cycle_3_mean': imp[2].get('cycle_3', {}).get('mean', 0)
            }
            for imp in improvements[:5]
        ]
        
        # Find statements that declined most (areas needing attention)
        statement_analysis['most_declined'] = [
            {
                'statement': imp[0],
                'text': imp[2]['text'],
                'category': imp[2]['category'],
                'decline': imp[1],
                'cycle_2_mean': imp[2].get('cycle_2', {}).get('mean', 0),
                'cycle_3_mean': imp[2].get('cycle_3', {}).get('mean', 0)
            }
            for imp in improvements[-5:]
        ]
        
        # Overall top and bottom performing statements (across all cycles)
        overall_scores = {}
        for q_id, data in statement_analysis['cycle_progression'].items():
            all_means = []
            for cycle in ['cycle_1', 'cycle_2', 'cycle_3']:
                if cycle in data and 'mean' in data[cycle]:
                    all_means.append(data[cycle]['mean'])
            
            if all_means:
                overall_scores[q_id] = {
                    'mean': np.mean(all_means),
                    'text': data['text'],
                    'category': data['category']
                }
        
        sorted_overall = sorted(overall_scores.items(), key=lambda x: x[1]['mean'], reverse=True)
        
        statement_analysis['top_statements'] = [
            {
                'statement': q[0],
                'text': q[1]['text'],
                'category': q[1]['category'],
                'mean_score': q[1]['mean']
            }
            for q in sorted_overall[:5]
        ]
        
        statement_analysis['bottom_statements'] = [
            {
                'statement': q[0],
                'text': q[1]['text'],
                'category': q[1]['category'],
                'mean_score': q[1]['mean']
            }
            for q in sorted_overall[-5:]
        ]
        
        # Category breakdown
        for cat in ['Vision', 'Effort', 'Systems', 'Practice', 'Attitude']:
            cat_statements = [q for q, data in statement_analysis['cycle_progression'].items() 
                           if data['category'] == cat]
            
            cat_scores = []
            for q in cat_statements:
                if 'cycle_1' in statement_analysis['cycle_progression'][q]:
                    cat_scores.append(statement_analysis['cycle_progression'][q]['cycle_1']['mean'])
            
            if cat_scores:
                statement_analysis['vespa_category_breakdown'][cat] = {
                    'n_statements': len(cat_statements),
                    'mean_score': np.mean(cat_scores)
                }
        
        return statement_analysis
    
    def create_visualizations(self):
        """Create comprehensive visualizations"""
        figures = {}
        
        # 1. Cycle Progression Chart
        fig_cycles = self._create_cycle_progression_chart()
        figures['cycle_progression'] = fig_cycles
        
        # 2. Faculty Comparison Radar
        fig_faculty = self._create_faculty_radar()
        figures['faculty_radar'] = fig_faculty
        
        # 3. Element Distribution Comparisons (all cycles)
        dist_figures = self._create_element_distribution_comparison()
        figures.update(dist_figures)
        
        # 4. Faculty Progression Heatmap
        fig_heatmap = self._create_faculty_heatmap()
        figures['faculty_heatmap'] = fig_heatmap
        
        # 5. Faculty Comparison Bar Chart
        fig_faculty_bars = self._create_faculty_comparison_bars()
        figures['faculty_bars'] = fig_faculty_bars
        
        # 6. Statement Performance Heatmap - Removed in favor of simpler display
        # fig_statement_heatmap = self._create_statement_performance_heatmap()
        # figures['statement_heatmap'] = fig_statement_heatmap
        
        return figures
    
    def _create_cycle_progression_chart(self):
        """Create enhanced cycle progression visualization with national benchmarks"""
        fig = make_subplots(
            rows=2, cols=3,
            subplot_titles=self.vespa_categories + ['Overall'],
            specs=[[{}, {}, {}], [{}, {}, {}]]
        )
        
        for idx, cat in enumerate(self.vespa_categories + ['Overall']):
            row = idx // 3 + 1
            col = idx % 3 + 1
            
            # Get cycle data - ONLY for students who completed all 3 cycles
            cat_initial = cat[0] if cat != 'Overall' else 'O'
            cycle_means = []
            cycle_labels = []
            
            # Get columns for all three cycles
            c1_col = f'{cat_initial}1'
            c2_col = f'{cat_initial}2'
            c3_col = f'{cat_initial}3'
            
            # Only use students who have data for ALL three cycles
            if all(col in self.results_df.columns for col in [c1_col, c2_col, c3_col]):
                complete_data = self.results_df[[c1_col, c2_col, c3_col]].dropna()
                
                if len(complete_data) > 0:
                    cycle_means = [
                        complete_data[c1_col].mean(),
                        complete_data[c2_col].mean(),
                        complete_data[c3_col].mean()
                    ]
                    cycle_labels = ['Cycle 1', 'Cycle 2', 'Cycle 3']
            
            if cycle_means:
                # Add college data
                fig.add_trace(
                    go.Scatter(
                        x=cycle_labels,
                        y=cycle_means,
                        mode='lines+markers',
                        name=f'College {cat}',
                        line=dict(color=self.vespa_colors.get(cat, '#666'), width=4),
                        marker=dict(size=12, symbol='circle'),
                        showlegend=False
                    ),
                    row=row, col=col
                )
                
                # Add national benchmark line (use cycle 1 as baseline)
                national_avg = self.national_stats.get('cycle_1', {}).get(cat, {}).get('mean', 5.5)
                fig.add_trace(
                    go.Scatter(
                        x=cycle_labels,
                        y=[national_avg] * len(cycle_labels),
                        mode='lines',
                        name=f'National Average',
                        line=dict(color='rgba(128, 128, 128, 0.5)', width=2, dash='dash'),
                        showlegend=False
                    ),
                    row=row, col=col
                )
                
                # Add annotation for improvement
                if len(cycle_means) == 3 and cycle_means[2] > cycle_means[1]:
                    fig.add_annotation(
                        x='Cycle 3', y=cycle_means[2],
                        text="↑ +{:.1f}".format(cycle_means[2] - cycle_means[1]),
                        showarrow=False,
                        yshift=15,
                        font=dict(color='green', size=10),
                        row=row, col=col
                    )
                
                fig.update_yaxes(range=[3, 8], title_text="Score", row=row, col=col)
                fig.update_xaxes(title_text="", row=row, col=col)
        
        fig.update_layout(
            title_text="VESPA Score Progression: Students Who Completed All 3 Cycles (n=497)",
            height=700,
            showlegend=False,
            paper_bgcolor='rgba(248,249,250,1)',
            plot_bgcolor='white',
            font=dict(family="Arial, sans-serif")
        )
        
        return fig
    
    def _create_faculty_radar(self):
        """Create faculty comparison radar chart"""
        faculty_stats = self.analyze_faculty_comparison()
        
        # Faculty name mapping
        faculty_names = {
            'SFA': 'Sport & Wellness',
            'CVP': 'Arts & Media',
            'SPS': 'Public Services',
            'BTM': 'Business Studies',
            'HSC': 'Health Sciences',
            'HAT': 'Beauty & Wellbeing',
            'CIT': 'Digital Tech',
            'ENG': 'Engineering',
            'CHA': 'Trades & Hospitality',
            'BES': 'Foundation Studies',
            'OVERALL': 'College Average'
        }
        
        # Get top faculties by student count (excluding OVERALL)
        top_faculties = sorted(
            [(f, data['n_students']) for f, data in faculty_stats.items() if f != 'OVERALL'],
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        # Add OVERALL to the list
        top_faculties.append(('OVERALL', faculty_stats.get('OVERALL', {}).get('n_students', 0)))
        
        fig = go.Figure()
        
        for faculty, _ in top_faculties:
            if faculty not in faculty_stats:
                continue
                
            values = []
            for cat in self.vespa_categories:
                if cat in faculty_stats[faculty]['current_cycle']:
                    values.append(faculty_stats[faculty]['current_cycle'][cat]['mean'])
                else:
                    values.append(0)
            
            # Use abbreviated name for display
            display_name = faculty_names.get(faculty, faculty)
            
            fig.add_trace(go.Scatterpolar(
                r=values,
                theta=self.vespa_categories,
                fill='toself',
                name=display_name,
                opacity=1.0 if faculty == 'OVERALL' else 0.7
            ))
        
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 10]
                )
            ),
            showlegend=True,
            title="Tutor Group VESPA Profile Comparison"
        )
        
        return fig
    
    def _create_element_distribution_comparison(self):
        """Create distribution comparison showing all 3 cycles for each element"""
        # Create a figure for each VESPA element showing all 3 cycles
        figures = {}
        
        for element in self.vespa_categories + ['Overall']:
            fig = make_subplots(
                rows=1, cols=3,
                subplot_titles=[f'Cycle 1', f'Cycle 2', f'Cycle 3'],
                horizontal_spacing=0.08
            )
            
            element_initial = element[0] if element != 'Overall' else 'O'
            
            for cycle in [1, 2, 3]:
                col_name = f'{element_initial}{cycle}'
                
                if col_name in self.results_df.columns:
                    scores = self.results_df[col_name].dropna()
                    
                    if len(scores) > 0:
                        # Calculate college distribution counts
                        college_counts = []
                        for score in range(1, 11):
                            count = ((scores >= score - 0.5) & (scores < score + 0.5)).sum()
                            college_counts.append(count)
                        
                        # Convert to percentages
                        total_college = sum(college_counts)
                        college_percentages = [count/total_college * 100 if total_college > 0 else 0 for count in college_counts]
                        
                        # Get national distribution for this cycle
                        cycle_key = f'cycle_{cycle}'
                        national_dist = self.national_distributions.get(cycle_key, {}).get(element, {})
                        national_total = self.national_distributions.get(cycle_key, {}).get('total', 1)
                        
                        # Convert national to percentages
                        national_percentages = []
                        for score in range(1, 11):
                            count = national_dist.get(score, 0)
                            percentage = (count / national_total) * 100 if national_total > 0 else 0
                            national_percentages.append(percentage)
                        
                        # Add college bars
                        fig.add_trace(
                            go.Bar(
                                x=list(range(1, 11)),
                                y=college_percentages,
                                name='College',
                                marker_color=self.vespa_colors.get(element, '#666'),
                                opacity=0.7,
                                showlegend=(cycle == 1)
                            ),
                            row=1, col=cycle
                        )
                        
                        # Add national line overlay
                        fig.add_trace(
                            go.Scatter(
                                x=list(range(1, 11)),
                                y=national_percentages,
                                mode='lines+markers',
                                name='National',
                                line=dict(color='red', width=2),
                                marker=dict(size=6),
                                showlegend=(cycle == 1)
                            ),
                            row=1, col=cycle
                        )
                        
                        # Add means
                        college_mean = scores.mean()
                        national_mean = self.national_stats.get(cycle_key, {}).get(element, {}).get('mean', 5.5)
                        
                        fig.add_annotation(
                            x=5.5, y=max(college_percentages + national_percentages) * 1.1,
                            text=f"College: {college_mean:.1f}<br>National: {national_mean:.1f}",
                            showarrow=False,
                            font=dict(size=10),
                            row=1, col=cycle
                        )
                
                fig.update_xaxes(title_text="Score", range=[0.5, 10.5], row=1, col=cycle)
                fig.update_yaxes(title_text="Percentage (%)" if cycle == 1 else "", row=1, col=cycle)
            
            fig.update_layout(
                title_text=f"{element} Score Distributions Across Cycles",
                height=400,
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                paper_bgcolor='white',
                plot_bgcolor='rgba(240,240,240,0.3)'
            )
            
            figures[f'distribution_{element.lower()}'] = fig
        
        return figures
    
    def _create_faculty_heatmap(self):
        """Create faculty progression heatmap"""
        faculty_stats = self.analyze_faculty_comparison()
        
        # Faculty name mapping
        faculty_names = {
            'SFA': 'Sport & Wellness',
            'CVP': 'Arts & Media',
            'SPS': 'Public Services',
            'BTM': 'Business Studies',
            'HSC': 'Health Sciences',
            'HAT': 'Beauty & Wellbeing',
            'CIT': 'Digital Tech',
            'ENG': 'Engineering',
            'CHA': 'Trades & Hospitality',
            'BES': 'Foundation Studies'
        }
        
        # Prepare data for heatmap
        faculties = []
        improvements = []
        
        for faculty, data in faculty_stats.items():
            if faculty == 'OVERALL':  # Skip overall for heatmap
                continue
                
            faculty_row = []
            for cat in self.vespa_categories:
                prog_key = f'{cat}_progression'
                if prog_key in data:
                    faculty_row.append(data[prog_key]['mean_improvement'])
                else:
                    faculty_row.append(0)
            
            if any(faculty_row):  # Only include if there's data
                display_name = faculty_names.get(faculty, faculty)
                faculties.append(display_name)
                improvements.append(faculty_row)
        
        if improvements:
            fig = go.Figure(data=go.Heatmap(
                z=improvements,
                x=self.vespa_categories,
                y=faculties,
                colorscale='RdYlGn',
                zmid=0,
                text=[[f'{val:.2f}' for val in row] for row in improvements],
                texttemplate='%{text}',
                textfont={"size": 10},
                colorbar=dict(title="Mean Improvement")
            ))
            
            fig.update_layout(
                title="Faculty Progression Heatmap (Cycle 1 to 2)",
                xaxis_title="VESPA Categories",
                yaxis_title="Faculty",
                height=max(400, len(faculties) * 30)
            )
            
            return fig
        
        return go.Figure()  # Return empty figure if no data
    
    def _create_faculty_comparison_bars(self):
        """Create faculty comparison bar charts"""
        faculty_stats = self.analyze_faculty_comparison()
        
        # Prepare data
        faculties = []
        vision_scores = []
        effort_scores = []
        systems_scores = []
        practice_scores = []
        attitude_scores = []
        overall_scores = []
        
        faculty_names = {
            'SFA': 'Sport & Wellness',
            'CVP': 'Arts & Media',
            'SPS': 'Public Services',
            'BTM': 'Business Studies',
            'HSC': 'Health Sciences',
            'HAT': 'Beauty & Wellbeing',
            'CIT': 'Digital Tech',
            'ENG': 'Engineering',
            'CHA': 'Trades & Hospitality',
            'BES': 'Foundation Studies'
        }
        
        for faculty, data in faculty_stats.items():
            if faculty != 'OVERALL' and 'current_cycle' in data:
                display_name = faculty_names.get(faculty, faculty)
                faculties.append(display_name)
                
                vision_scores.append(data['current_cycle'].get('Vision', {}).get('mean', 0))
                effort_scores.append(data['current_cycle'].get('Effort', {}).get('mean', 0))
                systems_scores.append(data['current_cycle'].get('Systems', {}).get('mean', 0))
                practice_scores.append(data['current_cycle'].get('Practice', {}).get('mean', 0))
                attitude_scores.append(data['current_cycle'].get('Attitude', {}).get('mean', 0))
                overall_scores.append(data['current_cycle'].get('Overall', {}).get('mean', 0))
        
        # Create grouped bar chart
        fig = go.Figure()
        
        fig.add_trace(go.Bar(name='Vision', x=faculties, y=vision_scores, marker_color='#e59437'))
        fig.add_trace(go.Bar(name='Effort', x=faculties, y=effort_scores, marker_color='#86b4f0'))
        fig.add_trace(go.Bar(name='Systems', x=faculties, y=systems_scores, marker_color='#72cb44'))
        fig.add_trace(go.Bar(name='Practice', x=faculties, y=practice_scores, marker_color='#7f31a4'))
        fig.add_trace(go.Bar(name='Attitude', x=faculties, y=attitude_scores, marker_color='#f032e6'))
        
        # Add national average line
        fig.add_trace(go.Scatter(
            x=faculties * 5,
            y=[5.6] * (len(faculties) * 5),
            mode='lines',
            name='National Average',
            line=dict(color='red', width=2, dash='dash')
        ))
        
        fig.update_layout(
            title='Faculty VESPA Performance Comparison',
            xaxis_title='Faculty',
            yaxis_title='Mean Score',
            yaxis_range=[0, 10],
            barmode='group',
            height=500,
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        return fig
    
    def _create_statement_performance_heatmap(self):
        """Create heatmap showing statement performance with standard deviation"""
        # Analyze all statements across cycles
        statement_data = []
        
        for q_code, statement_text in self.statement_texts.items():
            row_data = {
                'statement': statement_text[:50] + '...' if len(statement_text) > 50 else statement_text,
                'full_text': statement_text,
                'code': q_code
            }
            
            # Get data for all three cycles
            for cycle in [1, 2, 3]:
                col_name = f'c{cycle}_{q_code}'
                if col_name in self.questions_df.columns:
                    scores = pd.to_numeric(self.questions_df[col_name], errors='coerce').dropna()
                    if len(scores) > 0:
                        row_data[f'mean_c{cycle}'] = scores.mean()
                        row_data[f'std_c{cycle}'] = scores.std()
                    else:
                        row_data[f'mean_c{cycle}'] = np.nan
                        row_data[f'std_c{cycle}'] = np.nan
                else:
                    row_data[f'mean_c{cycle}'] = np.nan
                    row_data[f'std_c{cycle}'] = np.nan
            
            # Calculate overall mean and consistency (inverse of average std dev)
            means = [row_data[f'mean_c{i}'] for i in [1,2,3] if not pd.isna(row_data[f'mean_c{i}'])]
            stds = [row_data[f'std_c{i}'] for i in [1,2,3] if not pd.isna(row_data[f'std_c{i}'])]
            
            if means:
                row_data['overall_mean'] = np.mean(means)
            else:
                row_data['overall_mean'] = 0
                
            if stds:
                row_data['avg_std'] = np.mean(stds)
                row_data['consistency'] = 1 / (1 + np.mean(stds))  # Higher score = more consistent
            else:
                row_data['avg_std'] = 0
                row_data['consistency'] = 0
            
            statement_data.append(row_data)
        
        # Sort by overall mean to get top and bottom performers
        statement_data.sort(key=lambda x: x['overall_mean'], reverse=True)
        
        # Get top 10 and bottom 10
        top_statements = statement_data[:10]
        bottom_statements = statement_data[-10:]
        combined = top_statements + bottom_statements
        
        # Create heatmap data
        statement_labels = []
        cycles_data = []
        std_data = []
        
        for stmt in combined:
            # Truncate statement for display
            label = stmt['statement']
            if len(label) > 50:
                label = label[:47] + '...'
            statement_labels.append(label)
            
            # Add mean scores
            cycles_data.append([
                stmt.get('mean_c1', 0),
                stmt.get('mean_c2', 0),
                stmt.get('mean_c3', 0)
            ])
            
            # Add std devs
            std_data.append([
                stmt.get('std_c1', 0),
                stmt.get('std_c2', 0),
                stmt.get('std_c3', 0)
            ])
        
        # Create figure with subplots - improved layout
        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=['<b>Mean Scores</b>', '<b>Consistency (Std Dev)</b>'],
            horizontal_spacing=0.12,
            column_widths=[0.5, 0.5]
        )
        
        # Mean scores heatmap
        fig.add_trace(
            go.Heatmap(
                z=cycles_data,
                x=['Cycle 1', 'Cycle 2', 'Cycle 3'],
                y=statement_labels,
                colorscale='RdYlGn',
                zmid=5.5,
                zmin=1,
                zmax=10,
                text=[[f'{val:.1f}' for val in row] for row in cycles_data],
                texttemplate='%{text}',
                textfont={"size": 11, "color": "black"},
                colorbar=dict(
                    title="Score",
                    tickmode="linear",
                    tick0=1,
                    dtick=2,
                    x=0.45,
                    len=0.8,
                    thickness=15
                ),
                hoverongaps=False
            ),
            row=1, col=1
        )
        
        # Standard deviation heatmap (lower is better/more consistent)
        fig.add_trace(
            go.Heatmap(
                z=std_data,
                x=['Cycle 1', 'Cycle 2', 'Cycle 3'],
                y=statement_labels,
                colorscale='RdYlGn_r',  # Reversed - lower std dev is better
                zmid=1.5,
                zmin=0,
                zmax=3,
                text=[[f'{val:.1f}' for val in row] for row in std_data],
                texttemplate='%{text}',
                textfont={"size": 11, "color": "black"},
                colorbar=dict(
                    title="Std Dev",
                    tickmode="linear",
                    tick0=0,
                    dtick=1,
                    x=1.02,
                    len=0.8,
                    thickness=15
                ),
                hoverongaps=False
            ),
            row=1, col=2
        )
        
        # Add separator line between top and bottom performers
        fig.add_shape(
            type="line",
            x0=-0.5, x1=2.5,
            y0=9.5, y1=9.5,
            line=dict(color="white", width=3),
            xref="x1", yref="y1"
        )
        
        fig.add_shape(
            type="line",
            x0=-0.5, x1=2.5,
            y0=9.5, y1=9.5,
            line=dict(color="white", width=3),
            xref="x2", yref="y2"
        )
        
        fig.update_layout(
            title=dict(
                text="Statement Performance Analysis",
                font=dict(size=18, color="#2c3e50"),
                x=0.5,
                xanchor='center'
            ),
            height=700,
            width=1200,
            showlegend=False,
            paper_bgcolor='#f8f9fa',
            plot_bgcolor='white',
            font=dict(family="Arial, sans-serif", size=12),
            margin=dict(l=10, r=10, t=80, b=50),
            annotations=[
                dict(
                    text="<b>TOP 10</b>",
                    x=0.225, y=0.78,
                    xref="paper", yref="paper",
                    showarrow=False,
                    font=dict(size=13, color="#28a745")
                ),
                dict(
                    text="<b>BOTTOM 10</b>",
                    x=0.225, y=0.22,
                    xref="paper", yref="paper",
                    showarrow=False,
                    font=dict(size=13, color="#dc3545")
                )
            ]
        )
        
        # Update axes
        fig.update_xaxes(showgrid=False, tickfont=dict(size=11))
        fig.update_yaxes(showgrid=False, tickfont=dict(size=10), automargin=True)
        
        return fig
    
    def generate_insights(self, analysis_results):
        """Generate key insights from the analysis"""
        insights = []
        
        # Cycle progression insights
        cycle_data = analysis_results['cycle_progression']
        
        # Overall C1 to C3 progression
        for key, data in cycle_data['cycle_comparison'].items():
            if 'C1_to_C3_overall' in key:
                category = key.split('_')[0]
                if 'overall_improvement' in data:
                    insights.append(f"{category} progression from Cycle 1 to Cycle 3: {data['mean_c1']:.1f} → {data['mean_c2']:.1f} → {data['mean_c3']:.1f} (Overall change: {data['overall_improvement']:+.2f})")
        
        # Cycle 2 to 3 improvements
        improvements_c2_c3 = []
        for key, data in cycle_data['cycle_comparison'].items():
            if 'C2_to_C3' in key and 'mean_improvement' in data:
                category = key.split('_')[0]
                if data['mean_improvement'] > 0:
                    improvements_c2_c3.append((category, data['mean_improvement']))
        
        if improvements_c2_c3:
            best_improvement = max(improvements_c2_c3, key=lambda x: x[1])
            insights.append(f"Strongest improvement from Cycle 2 to Cycle 3: {best_improvement[0]} (+{best_improvement[1]:.2f} points)")
        
        # Cycle 1 to 2 changes
        for key, data in cycle_data['cycle_comparison'].items():
            if 'C1_to_C2' in key and 'mean_improvement' in data:
                category = key.split('_')[0]
                if abs(data['mean_improvement']) > 0.3:
                    direction = "decreased" if data['mean_improvement'] < 0 else "increased"
                    insights.append(f"{category} {direction} by {abs(data['mean_improvement']):.2f} points from Cycle 1 to Cycle 2")
        
        # Faculty insights
        faculty_data = analysis_results['faculty_comparison']
        faculty_names = {
            'SFA': 'Sport & Wellness',
            'CVP': 'Arts & Media',
            'SPS': 'Public Services',
            'BTM': 'Business Studies',
            'HSC': 'Health Sciences',
            'HAT': 'Beauty & Wellbeing',
            'CIT': 'Digital Tech',
            'ENG': 'Engineering',
            'CHA': 'Trades & Hospitality',
            'BES': 'Foundation Studies'
        }
        
        top_performers = sorted(
            [(f, data['current_cycle'].get('Overall', {}).get('mean', 0)) 
             for f, data in faculty_data.items() if f != 'OVERALL'],
            key=lambda x: x[1],
            reverse=True
        )[:3]
        
        if top_performers:
            faculty_name = faculty_names.get(top_performers[0][0], top_performers[0][0])
            insights.append(f"Top performing faculty: {faculty_name} (Overall: {top_performers[0][1]:.2f})")
        
        # Statement-level insights
        s_data = analysis_results['statement_analysis']
        if s_data.get('most_improved'):
            top_improvement = s_data['most_improved'][0]
            insights.append(f"Largest statement improvement (Cycle 2 to 3): \"{top_improvement['text']}\" (+{top_improvement['improvement']:.2f})")
        
        if s_data['top_statements']:
            top_s = s_data['top_statements'][0]
            insights.append(f"Highest scoring statement: \"{top_s['text']}\" (Average: {top_s['mean_score']:.2f})")
        
        if s_data['bottom_statements']:
            bottom_s = s_data['bottom_statements'][0]
            insights.append(f"Area for development: \"{bottom_s['text']}\" (Average: {bottom_s['mean_score']:.2f})")
        
        # Count improvements
        improvement_count = sum(1 for s in s_data.get('most_improved', []) if s['improvement'] > 0)
        if improvement_count > 0:
            insights.append(f"{improvement_count} statements showed positive change from Cycle 2 to Cycle 3")
        
        return insights
    
    def generate_ai_analysis(self, analysis_results):
        """Generate AI-powered contextual analysis"""
        ai_analysis = {
            'executive_insights': [],
            'recommendations': [],
            'strategic_priorities': []
        }
        
        # Analyze the recovery pattern
        cycle_data = analysis_results['cycle_progression']['cycle_comparison']
        
        # Executive insights
        ai_analysis['executive_insights'] = [
            "Analysis across three cycles shows a clear progression pattern, with Cycle 1 establishing baseline scores, Cycle 2 showing adjustment, and Cycle 3 demonstrating improvement across all VESPA dimensions.",
            "Cycle 2 to Cycle 3 progression shows particularly strong improvements in Practice (+0.43) and Effort (+0.39), indicating students are developing enhanced study habits and commitment.",
            "Faculty performance varies significantly across departments, with some showing stronger VESPA profiles than others, suggesting opportunities for cross-faculty best practice sharing.",
            "Statement-level analysis reveals students score highest on goal-oriented statements but lower on systematic study approach statements, identifying specific areas for targeted intervention.",
            "The progression from Cycle 1 through Cycle 3 follows expected educational development patterns, validating the assessment approach."
        ]
        
        # Strategic recommendations
        ai_analysis['recommendations'] = [
            {
                'priority': 'High',
                'title': 'Support During Cycle 2 Transition',
                'description': 'Implement targeted mentoring and support programs during Cycle 2 when students typically experience score adjustments.'
            },
            {
                'priority': 'High',
                'title': 'Strengthen Systems Development',
                'description': 'Focus on building organizational and study systems, as this shows the smallest overall progression (-0.03) across cycles.'
            },
            {
                'priority': 'Medium',
                'title': 'Celebrate Practice Improvements',
                'description': 'Leverage the strong Practice improvement (+0.50) as a success story to motivate continued engagement.'
            },
            {
                'priority': 'Medium',
                'title': 'Faculty-Specific Interventions',
                'description': 'Develop targeted strategies for smaller departments (Engineering, Digital Technologies) to ensure equitable support.'
            }
        ]
        
        return ai_analysis
    
    def generate_html_report(self, analysis_results, figures):
        """Generate comprehensive HTML report for demo purposes"""
        insights = self.generate_insights(analysis_results)
        ai_analysis = self.generate_ai_analysis(analysis_results)
        
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sample College - VESPA Comparative Analysis Report (Demo)</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        .report-header {{
            background: white;
            border-radius: 15px;
            padding: 40px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }}
        
        .report-header h1 {{
            color: #667eea;
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        
        .report-date {{
            color: #666;
            font-size: 1.1em;
        }}
        
        .executive-summary {{
            background: white;
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }}
        
        .executive-summary h2 {{
            color: #667eea;
            margin-bottom: 20px;
            font-size: 1.8em;
        }}
        
        .key-insights {{
            background: #f8f9fa;
            border-left: 4px solid #667eea;
            padding: 20px;
            margin: 20px 0;
            border-radius: 5px;
        }}
        
        .key-insights ul {{
            list-style: none;
            padding: 0;
        }}
        
        .key-insights li {{
            padding: 10px 0;
            border-bottom: 1px solid #e0e0e0;
        }}
        
        .key-insights li:last-child {{
            border-bottom: none;
        }}
        
        .section {{
            background: white;
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }}
        
        .section h2 {{
            color: #667eea;
            margin-bottom: 20px;
            font-size: 1.8em;
        }}
        
        .section h3 {{
            color: #764ba2;
            margin: 20px 0 10px 0;
            font-size: 1.4em;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 10px;
            margin: 20px 0;
        }}
        @media (max-width: 1200px) {{
            .stats-grid {{
                grid-template-columns: repeat(3, 1fr);
            }}
        }}
        @media (max-width: 768px) {{
            .stats-grid {{
                grid-template-columns: repeat(2, 1fr);
            }}
        }}
        
        .stat-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px 8px;
            border-radius: 8px;
            text-align: center;
        }}
        
        .stat-card h4 {{
            font-size: 0.8em;
            opacity: 0.95;
            margin-bottom: 4px;
            font-weight: 600;
        }}
        
        .stat-card .value {{
            font-size: 1.5em;
            font-weight: bold;
            margin: 4px 0;
        }}
        
        .stat-card .change {{
            font-size: 0.75em;
            margin-top: 2px;
            opacity: 0.9;
        }}
        
        .stat-card small {{
            font-size: 0.7em;
            opacity: 0.8;
            display: block;
            margin-top: 4px;
        }}
        
        .chart-container {{
            margin: 30px 0;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 10px;
        }}
        
        .responsive-chart {{
            width: 100%;
            height: auto;
            max-width: 100%;
            overflow: hidden;
            page-break-inside: avoid;
        }}
        
        .responsive-chart > div {{
            width: 100% !important;
            height: auto !important;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        
        th {{
            background: #667eea;
            color: white;
            padding: 12px;
            text-align: left;
        }}
        
        td {{
            padding: 12px;
            border-bottom: 1px solid #e0e0e0;
        }}
        
        tr:hover {{
            background: #f8f9fa;
        }}
        
        .positive {{
            color: #28a745;
            font-weight: bold;
        }}
        
        .negative {{
            color: #dc3545;
            font-weight: bold;
        }}
        
        .footer {{
            text-align: center;
            padding: 30px;
            color: white;
            opacity: 0.9;
        }}
        
        @media print {{
            @page {{
                size: A4;
                margin: 15mm 10mm;
            }}
            
            body {{
                background: white;
                margin: 0;
                padding: 0;
                width: 100%;
            }}
            
            .container {{
                max-width: 100%;
                width: 190mm;
                margin: 0 auto;
                padding: 0;
                box-shadow: none;
            }}
            
            .report-header button {{
                display: none !important;
            }}
            
            .report-header, .executive-summary, .section {{
                page-break-inside: avoid;
                margin-bottom: 10px;
                padding: 10px;
            }}
            
            .report-header h1 {{
                font-size: 1.8em;
            }}
            
            .report-header h2 {{
                font-size: 1.3em;
            }}
            
            h2 {{
                font-size: 1.4em;
                margin-bottom: 10px;
            }}
            
            h3 {{
                font-size: 1.2em;
                margin: 10px 0 8px 0;
            }}
            
            h4 {{
                font-size: 1em;
            }}
            
            p, li {{
                font-size: 0.85em;
                line-height: 1.4;
            }}
            
            .chart-container {{
                page-break-inside: avoid;
                margin: 3px 0;
                padding: 3px;
                width: 100%;
                max-height: 70mm;
                overflow: hidden;
            }}
            
            .responsive-chart {{
                page-break-inside: avoid;
                width: 100% !important;
                max-width: 190mm !important;
                height: 65mm !important;
                max-height: 65mm !important;
                overflow: hidden !important;
            }}
            
            .responsive-chart > div {{
                width: 190mm !important;
                max-width: 190mm !important;
                height: 65mm !important;
                max-height: 65mm !important;
                transform: scale(0.48) !important;
                transform-origin: top left !important;
            }}
            
            .js-plotly-plot {{
                width: 190mm !important;
                max-width: 190mm !important;
                height: 65mm !important;
                max-height: 65mm !important;
            }}
            
            .js-plotly-plot .plotly {{
                width: 100% !important;
                max-width: 190mm !important;
            }}
            
            /* Main progression chart - has 6 subplots - make it bigger and on its own page */
            #cycle-prog {{
                height: 180mm !important;
                max-height: 180mm !important;
                width: 100% !important;
                page-break-before: always !important;
                page-break-after: always !important;
            }}
            
            #cycle-prog .js-plotly-plot {{
                height: 180mm !important;
                max-height: 180mm !important;
            }}
            
            /* Individual distribution charts - make them smaller so 3 can fit per page */
            div[id^="dist-"] {{
                height: 65mm !important;
                max-height: 65mm !important;
                width: 100% !important;
            }}
            
            div[id^="dist-"] .js-plotly-plot {{
                height: 65mm !important;
                max-height: 65mm !important;
            }}
            
            /* Plotly modebar (hide in print) */
            .modebar {{
                display: none !important;
            }}
            
            table {{
                page-break-inside: avoid;
                font-size: 0.7em;
                width: 100%;
            }}
            
            th, td {{
                padding: 6px 4px;
            }}
            
            .stats-grid {{
                page-break-inside: avoid;
                grid-template-columns: repeat(5, 1fr) !important;
                gap: 5px;
                font-size: 0.75em;
            }}
            
            .stat-card {{
                padding: 6px 3px;
            }}
            
            .stat-card h4 {{
                font-size: 0.65em;
            }}
            
            .stat-card .value {{
                font-size: 1.1em;
            }}
            
            .stat-card .change {{
                font-size: 0.6em;
            }}
            
            .stat-card small {{
                font-size: 0.55em;
            }}
            
            .key-insights {{
                padding: 10px;
                margin: 10px 0;
            }}
            
            /* Faculty cards grid for print */
            div[style*="grid-template-columns: repeat(auto-fit, minmax(320px, 1fr))"] {{
                grid-template-columns: repeat(2, 1fr) !important;
                gap: 10px !important;
                page-break-inside: avoid;
            }}
            
            /* Individual faculty cards */
            div[style*="border-radius: 12px"][style*="box-shadow"] {{
                padding: 12px !important;
                margin-bottom: 8px;
            }}
            
            /* Faculty card grids inside cards */
            div[style*="grid-template-columns: 1fr 1fr"] {{
                gap: 6px !important;
            }}
            
            /* Only force page breaks for the two main section dividers */
            div[style*="background: #f0f4f8"] {{
                page-break-before: always;
            }}
            
            /* Hide background gradients for print */
            .section[style*="linear-gradient"] {{
                background: white !important;
                color: #333 !important;
            }}
            
            .section[style*="linear-gradient"] h2,
            .section[style*="linear-gradient"] h3,
            .section[style*="linear-gradient"] h4,
            .section[style*="linear-gradient"] li {{
                color: #333 !important;
            }}
            
            /* Ensure footer doesn't orphan */
            .footer {{
                margin-top: 20px;
                padding: 10px;
                page-break-inside: avoid;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
            <div class="report-header">
                <div style="display: flex; align-items: center; justify-content: center; margin-bottom: 20px;">
                    <img src="https://vespa.academy/_astro/vespalogo.BGrK1ARl.png" 
                         alt="VESPA Logo" 
                         style="height: 90px; object-fit: contain;">
                </div>
                <h1 style="color: #2c3e50; margin-bottom: 10px;">Sample College</h1>
                <h2 style="color: #667eea;">VESPA Comparative Analysis Report</h2>
                <p class="report-date">Generated: {datetime.now().strftime('%B %d, %Y')}</p>
                
                <div style="margin-top: 20px;">
                    <button onclick="window.print();" style="
                        background: linear-gradient(135deg, #667eea, #764ba2);
                        color: white;
                        border: none;
                        padding: 12px 30px;
                        font-size: 1em;
                        font-weight: 600;
                        border-radius: 25px;
                        cursor: pointer;
                        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
                        transition: all 0.3s;
                    " onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 6px 20px rgba(102, 126, 234, 0.4)';" 
                       onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 15px rgba(102, 126, 234, 0.3)';">
                        Download as PDF
                    </button>
                </div>
            </div>
        
        <div class="executive-summary">
            <h2>Executive Summary</h2>
            <p>This comprehensive VESPA analysis for Sample College examines student mindset and study skills development 
            across 1,787 students in 9 faculties through three assessment cycles during the 2024/25 academic year.</p>
            
            <div class="key-insights" style="margin-top: 25px;">
                <h3 style="color: #667eea; margin-bottom: 20px;">Key Findings & Takeaways</h3>
                
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-top: 20px;">
                    <div style="background: rgba(102, 126, 234, 0.08); padding: 20px; border-radius: 8px; border-left: 4px solid #667eea;">
                        <h4 style="color: #2c3e50; margin-bottom: 10px;">Overall Progress</h4>
                        <p>Students show resilience with strong recovery in Cycle 3. Practice skills improved most significantly (+0.50 overall), 
                        indicating enhanced revision and study techniques.</p>
                    </div>
                    
                    <div style="background: rgba(114, 203, 68, 0.08); padding: 20px; border-radius: 8px; border-left: 4px solid #72cb44;">
                        <h4 style="color: #2c3e50; margin-bottom: 10px;">Faculty Performance</h4>
                        <p>Beauty & Wellbeing leads with 8.67 overall score, while Digital Technologies shows opportunity for targeted support at 5.00. 
                        Sport & Wellness has the largest cohort (823 students) with solid performance.</p>
                    </div>
                    
                    <div style="background: rgba(229, 148, 55, 0.08); padding: 20px; border-radius: 8px; border-left: 4px solid #e59437;">
                        <h4 style="color: #2c3e50; margin-bottom: 10px;">Strongest Beliefs</h4>
                        <p>Students demonstrate strong career vision and goal-setting, with "I have the support I need" and 
                        "I understand why education is important" scoring highest across all cycles.</p>
                    </div>
                    
                    <div style="background: rgba(240, 50, 230, 0.08); padding: 20px; border-radius: 8px; border-left: 4px solid #f032e6;">
                        <h4 style="color: #2c3e50; margin-bottom: 10px;">Development Areas</h4>
                        <p>Systems and organizational skills need attention. File organization, note-taking, and systematic 
                        revision approaches show the lowest scores and require intervention.</p>
                    </div>
                </div>
                
                <div style="margin-top: 25px; padding: 20px; background: linear-gradient(to right, rgba(102, 126, 234, 0.05), rgba(118, 75, 162, 0.05)); border-radius: 8px;">
                    <h4 style="color: #2c3e50; margin-bottom: 12px;">Strategic Priorities</h4>
                    <ul style="margin: 0; padding-left: 25px; line-height: 1.8;">
                        <li><strong>Immediate:</strong> Support Cycle 2 students experiencing typical mid-year challenges</li>
                        <li><strong>Short-term:</strong> Enhance Systems skills training across all faculties</li>
                        <li><strong>Long-term:</strong> Share best practices from high-performing departments (Beauty & Wellbeing, Trades)</li>
                        <li><strong>Ongoing:</strong> Maintain focus on Practice skills which show strongest improvement trajectory</li>
                    </ul>
                </div>
            </div>
        </div>
        
        <div class="section" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 35px; border-radius: 12px;">
            <h2 style="color: white; font-size: 2em; border-bottom: 2px solid rgba(255,255,255,0.3); padding-bottom: 15px; margin-bottom: 25px;">Cycle Analysis</h2>
            
            <div style="margin-top: 20px;">
                <ul style="list-style: none; padding: 0;">
                    {''.join([f'<li style="margin: 15px 0; padding-left: 25px; border-left: 3px solid rgba(255,255,255,0.5); color: white; font-size: 1.05em; line-height: 1.6;">{insight}</li>' for insight in ai_analysis['executive_insights']])}
                </ul>
            </div>
            
            <div style="margin-top: 40px;">
                <h3 style="color: white; font-size: 1.4em; margin-bottom: 25px;">Strategic Recommendations</h3>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px;">
                    {''.join([f'''
                    <div style="background: rgba(255,255,255,0.1); padding: 20px; border-radius: 10px; border-left: 4px solid {'#ff6b6b' if rec['priority'] == 'High' else '#feca57' if rec['priority'] == 'Medium' else '#48dbfb'};">
                        <span style="background: {'#ff6b6b' if rec['priority'] == 'High' else '#feca57' if rec['priority'] == 'Medium' else '#48dbfb'}; color: white; padding: 4px 12px; border-radius: 15px; font-size: 0.85em; font-weight: 600;">{rec['priority']} Priority</span>
                        <h4 style="margin: 12px 0 8px 0; color: white; font-size: 1.1em;">{rec['title']}</h4>
                        <p style="color: rgba(255,255,255,0.9); line-height: 1.5;">{rec['description']}</p>
                    </div>
                    ''' for rec in ai_analysis['recommendations']])}
                </div>
            </div>
        </div>
"""
        
        # SECTION 1: VESPA RESULTS
        html_content += """
        <div style="background: #f0f4f8; padding: 30px 0; margin-top: 30px;">
            <h1 style="text-align: center; color: #2c3e50; border-bottom: 3px solid #667eea; padding-bottom: 10px; margin: 0 auto 30px; max-width: 400px;">
                SECTION 1: VESPA RESULTS
            </h1>
        </div>
        """
        
        # Add cycle progression section
        cycle_data = analysis_results['cycle_progression']['cycle_comparison']
        html_content += """
        <div class="section" style="padding: 25px 15px;">
            <h2>Cycle Progression Analysis</h2>
            <p style="margin-bottom: 20px;">
                Analysis of VESPA scores across three assessment cycles shows distinct patterns in each dimension.
                The following data represents mean scores and progression metrics for students who participated in each cycle.
            </p>
            
            <h3>Cycle 1 to Cycle 2 Changes</h3>
            <div class="stats-grid">
"""
        
        # Show Cycle 1 to 2 changes
        c1_to_c2_shown = False
        for key, data in cycle_data.items():
            if 'C1_to_C2' in key and 'mean_improvement' in data:
                c1_to_c2_shown = True
                category = key.split('_')[0]
                improvement = data['mean_improvement']
                percent_improved = data.get('percent_improved', 0)
                
                html_content += f"""
                <div class="stat-card">
                    <h4>{category}</h4>
                    <div class="value">{improvement:+.2f}</div>
                    <div class="change">{percent_improved:.0f}% improved</div>
                </div>
"""
        
        html_content += """
            </div>
            
            <h3>Cycle 2 to Cycle 3 Changes</h3>
            <div class="stats-grid">
"""
        
        # Show Cycle 2 to 3 changes
        for key, data in cycle_data.items():
            if 'C2_to_C3' in key and 'mean_improvement' in data:
                category = key.split('_')[0]
                improvement = data['mean_improvement']
                percent_improved = data.get('percent_improved', 0)
                n_students = data.get('n_students', 0)
                
                # Color based on improvement
                if improvement > 0.3:
                    card_style = 'background: linear-gradient(135deg, #28a745 0%, #20c997 100%);'
                elif improvement > 0:
                    card_style = 'background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);'
                else:
                    card_style = ''
                
                html_content += f"""
                <div class="stat-card" style="{card_style}">
                    <h4>{category}</h4>
                    <div class="value">{improvement:+.2f}</div>
                    <div class="change">{percent_improved:.0f}% improved</div>
                    <small style="opacity: 0.8;">n={n_students}</small>
                </div>
"""
        
        html_content += """
            </div>
            
            <h3>Overall Journey: Start to Finish</h3>
            <div class="stats-grid">
"""
        
        # Show overall C1 to C3 for students who completed all
        for key, data in cycle_data.items():
            if 'C1_to_C3_overall' in key and 'overall_improvement' in data:
                category = key.split('_')[0]
                improvement = data['overall_improvement']
                percent_improved = data.get('percent_improved_overall', 0)
                n_students = data.get('n_students', 0)
                
                # Color based on overall outcome
                if improvement > 0:
                    card_style = 'background: linear-gradient(135deg, #28a745 0%, #20c997 100%);'
                elif improvement > -0.2:
                    card_style = 'background: linear-gradient(135deg, #ffc107 0%, #ff9800 100%);'
                else:
                    card_style = ''
                
                html_content += f"""
                <div class="stat-card" style="{card_style}">
                    <h4>{category} Overall</h4>
                    <div class="value">{improvement:+.2f}</div>
                    <div class="change">C1: {data['mean_c1']:.1f} → C2: {data['mean_c2']:.1f} → C3: {data['mean_c3']:.1f}</div>
                    <small style="opacity: 0.8;">n={n_students} completed all</small>
                </div>
"""
        
        html_content += """
            </div>
"""
        
        # Embed the cycle progression chart if it exists
        if 'cycle_progression' in figures:
            chart_html = figures['cycle_progression'].to_html(
                include_plotlyjs=False,
                div_id="cycle-prog",
                config={'responsive': True, 'displayModeBar': False}
            )
            html_content += f"""
            <div class="chart-container responsive-chart">
                {chart_html}
            </div>
"""
        
        html_content += """
        </div>
        
        <div class="section">
            <h2>Score Distribution Analysis</h2>
            <p>Distribution of VESPA scores showing all 3 cycles for each element. Bar charts show college percentages, red lines show national distribution.</p>
"""
        
        # Embed the distribution charts with responsive wrapper
        for element in ['Vision', 'Effort', 'Systems', 'Practice', 'Attitude', 'Overall']:
            key = f'distribution_{element.lower()}'
            if key in figures:
                fig = figures[key]
                # Convert to HTML with responsive config
                chart_html = fig.to_html(
                    include_plotlyjs=False,  # We already include plotly.js in the header
                    div_id=f"dist-{element.lower()}",
                    config={'responsive': True, 'displayModeBar': False}
                )
                
                html_content += f"""
            <div class="chart-container responsive-chart" style="margin: 20px 0;">
                {chart_html}
            </div>
"""
        
        html_content += """
        </div>
"""
        
        # Add faculty comparison section - COMPLETELY REDESIGNED
        faculty_data = analysis_results['faculty_comparison']
        
        html_content += """
        <div class="section" style="padding: 40px;">
            <h2 style="color: #2c3e50; font-size: 2.2em; margin-bottom: 30px; border-bottom: 3px solid #667eea; padding-bottom: 15px;">
                Faculty Performance Comparison
            </h2>
            <p style="font-size: 1.2em; color: #555; margin-bottom: 40px;">
                Comprehensive VESPA performance metrics across all faculties based on Cycle 1 baseline assessment data.
                Student counts reflect total enrollment in each faculty.
            </p>
            
            <!-- Faculty Performance Cards Grid -->
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 25px; margin-bottom: 50px;">
"""
        
        # Faculty name mapping for display
        faculty_display_names = {
            'SFA': 'Department of Sport & Wellness',
            'CVP': 'Department of Arts & Media',
            'SPS': 'Department of Public Services',
            'BTM': 'Department of Business Studies',
            'HSC': 'Department of Health Sciences',
            'HAT': 'Department of Beauty & Wellbeing',
            'CIT': 'Department of Digital Technologies',
            'ENG': 'Department of Engineering',
            'CHA': 'Department of Trades & Hospitality',
            'BES': 'Department of Foundation Studies',
            'OVERALL': 'College Average'
        }
        
        # Get faculties sorted by overall score
        sorted_faculties = []
        college_totals = {'Vision': [], 'Effort': [], 'Systems': [], 'Practice': [], 'Attitude': [], 'Overall': []}
        
        for faculty, data in faculty_data.items():
            if faculty != 'OVERALL' and 'current_cycle' in data:
                scores = {
                    'vision': data['current_cycle'].get('Vision', {}).get('mean', 0),
                    'effort': data['current_cycle'].get('Effort', {}).get('mean', 0),
                    'systems': data['current_cycle'].get('Systems', {}).get('mean', 0),
                    'practice': data['current_cycle'].get('Practice', {}).get('mean', 0),
                    'attitude': data['current_cycle'].get('Attitude', {}).get('mean', 0),
                    'overall': data['current_cycle'].get('Overall', {}).get('mean', 0),
                    'n_students': data.get('n_students', 0)  # Use the total faculty student count, not just those with data
                }
                
                if scores['overall'] > 0:  # Only include faculties with data
                    sorted_faculties.append((faculty, scores))
                    # Collect for averages
                    for key in college_totals:
                        college_totals[key].append(scores[key.lower()])
        
        sorted_faculties.sort(key=lambda x: x[1]['overall'], reverse=True)
        
        # Calculate college averages
        college_avg = {k: np.mean(v) if v else 0 for k, v in college_totals.items()}
        
        # Create faculty cards
        for i, (faculty, scores) in enumerate(sorted_faculties[:9]):
            rank = i + 1
            rank_color = '#28a745' if rank <= 3 else '#667eea' if rank <= 6 else '#dc3545'
            display_name = faculty_display_names.get(faculty, faculty)
            
            html_content += f"""
                <div style="background: white; border-radius: 12px; padding: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.08); border-top: 4px solid {rank_color}; transition: transform 0.3s;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                        <h3 style="color: #2c3e50; margin: 0; font-size: 1.1em; max-width: 70%;">{display_name}</h3>
                        <span style="background: {rank_color}; color: white; padding: 5px 12px; border-radius: 20px; font-size: 0.9em; font-weight: 600;">#{rank}</span>
                    </div>
                    
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 15px;">
                        <div style="padding: 12px; background: linear-gradient(45deg, rgba(229,148,55,0.1), rgba(229,148,55,0.05)); border-radius: 8px; text-align: center;">
                            <div style="color: #e59437; font-size: 0.75em; font-weight: 600; text-transform: uppercase; letter-spacing: 1px;">Vision</div>
                            <div style="font-size: 1.8em; font-weight: bold; color: #2c3e50; margin-top: 5px;">{scores['vision']:.2f}</div>
                        </div>
                        <div style="padding: 12px; background: linear-gradient(45deg, rgba(134,180,240,0.1), rgba(134,180,240,0.05)); border-radius: 8px; text-align: center;">
                            <div style="color: #5690d6; font-size: 0.75em; font-weight: 600; text-transform: uppercase; letter-spacing: 1px;">Effort</div>
                            <div style="font-size: 1.8em; font-weight: bold; color: #2c3e50; margin-top: 5px;">{scores['effort']:.2f}</div>
                        </div>
                        <div style="padding: 12px; background: linear-gradient(45deg, rgba(114,203,68,0.1), rgba(114,203,68,0.05)); border-radius: 8px; text-align: center;">
                            <div style="color: #72cb44; font-size: 0.75em; font-weight: 600; text-transform: uppercase; letter-spacing: 1px;">Systems</div>
                            <div style="font-size: 1.8em; font-weight: bold; color: #2c3e50; margin-top: 5px;">{scores['systems']:.2f}</div>
                        </div>
                        <div style="padding: 12px; background: linear-gradient(45deg, rgba(127,49,164,0.1), rgba(127,49,164,0.05)); border-radius: 8px; text-align: center;">
                            <div style="color: #7f31a4; font-size: 0.75em; font-weight: 600; text-transform: uppercase; letter-spacing: 1px;">Practice</div>
                            <div style="font-size: 1.8em; font-weight: bold; color: #2c3e50; margin-top: 5px;">{scores['practice']:.2f}</div>
                        </div>
                    </div>
                    
                    <div style="padding: 12px; background: linear-gradient(45deg, rgba(240,50,230,0.1), rgba(240,50,230,0.05)); border-radius: 8px; text-align: center; margin-bottom: 15px;">
                        <div style="color: #f032e6; font-size: 0.75em; font-weight: 600; text-transform: uppercase; letter-spacing: 1px;">Attitude</div>
                        <div style="font-size: 1.8em; font-weight: bold; color: #2c3e50; margin-top: 5px;">{scores['attitude']:.2f}</div>
                    </div>
                    
                    <div style="padding: 15px; background: linear-gradient(135deg, #667eea, #764ba2); border-radius: 10px; text-align: center; color: white;">
                        <div style="font-size: 0.9em; font-weight: 600; opacity: 0.9; text-transform: uppercase; letter-spacing: 1px;">Overall Score</div>
                        <div style="font-size: 2.5em; font-weight: bold; margin: 5px 0;">{scores['overall']:.2f}</div>
                        <div style="font-size: 0.8em; opacity: 0.8;">n = {scores['n_students']} students</div>
                    </div>
                </div>
"""
        
        html_content += """
            </div>
            
            <!-- Detailed Comparison Matrix -->
            <h3 style="color: #2c3e50; margin-top: 50px; margin-bottom: 25px; font-size: 1.5em;">Detailed Performance Matrix</h3>
            <div style="overflow-x: auto; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.1);">
                <table style="width: 100%; min-width: 700px; border-collapse: separate; border-spacing: 0; background: white;">
                    <thead>
                        <tr>
                            <th style="background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 18px; text-align: left; font-size: 1em; position: sticky; left: 0; z-index: 10;">Faculty</th>
                            <th style="background: #e59437; color: white; padding: 18px; text-align: center; font-size: 0.95em;">VISION</th>
                            <th style="background: #5690d6; color: white; padding: 18px; text-align: center; font-size: 0.95em;">EFFORT</th>
                            <th style="background: #72cb44; color: white; padding: 18px; text-align: center; font-size: 0.95em;">SYSTEMS</th>
                            <th style="background: #7f31a4; color: white; padding: 18px; text-align: center; font-size: 0.95em;">PRACTICE</th>
                            <th style="background: #f032e6; color: white; padding: 18px; text-align: center; font-size: 0.95em;">ATTITUDE</th>
                            <th style="background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 18px; text-align: center; font-size: 0.95em; font-weight: bold;">OVERALL</th>
                        </tr>
                    </thead>
                    <tbody>
"""
        
        # Add data rows with visual indicators
        for i, (faculty, scores) in enumerate(sorted_faculties):
            display_name = faculty_display_names.get(faculty, faculty)
            row_bg = "#f8f9fa" if i % 2 == 0 else "#ffffff"
            
            def format_cell(value, avg, is_overall=False):
                diff = value - avg
                if diff > 0.2:
                    color = '#28a745'
                    icon = '↑'
                elif diff < -0.2:
                    color = '#dc3545'
                    icon = '↓'
                else:
                    color = '#666'
                    icon = '•'
                
                style = f"color: {color}; font-weight: {'bold' if is_overall else '600'};"
                return f'<span style="{style}">{icon} {value:.2f}</span>'
            
            html_content += f"""
                    <tr style="background: {row_bg}; border-bottom: 1px solid #e9ecef;">
                        <td style="padding: 14px; font-weight: 600; color: #2c3e50; position: sticky; left: 0; background: {row_bg}; border-right: 2px solid #e9ecef;">{display_name} (n={scores['n_students']})</td>
                        <td style="padding: 14px; text-align: center;">{format_cell(scores['vision'], college_avg['Vision'])}</td>
                        <td style="padding: 14px; text-align: center;">{format_cell(scores['effort'], college_avg['Effort'])}</td>
                        <td style="padding: 14px; text-align: center;">{format_cell(scores['systems'], college_avg['Systems'])}</td>
                        <td style="padding: 14px; text-align: center;">{format_cell(scores['practice'], college_avg['Practice'])}</td>
                        <td style="padding: 14px; text-align: center;">{format_cell(scores['attitude'], college_avg['Attitude'])}</td>
                        <td style="padding: 14px; text-align: center; background: rgba(102, 126, 234, 0.05); font-size: 1.1em;">{format_cell(scores['overall'], college_avg['Overall'], True)}</td>
                    </tr>
"""
        
        # Add college average row
        html_content += f"""
                    <tr style="background: linear-gradient(135deg, #667eea, #764ba2); color: white;">
                        <td style="padding: 16px; font-weight: bold; position: sticky; left: 0;">COLLEGE AVERAGE</td>
                        <td style="padding: 16px; text-align: center; font-weight: bold;">{college_avg['Vision']:.2f}</td>
                        <td style="padding: 16px; text-align: center; font-weight: bold;">{college_avg['Effort']:.2f}</td>
                        <td style="padding: 16px; text-align: center; font-weight: bold;">{college_avg['Systems']:.2f}</td>
                        <td style="padding: 16px; text-align: center; font-weight: bold;">{college_avg['Practice']:.2f}</td>
                        <td style="padding: 16px; text-align: center; font-weight: bold;">{college_avg['Attitude']:.2f}</td>
                        <td style="padding: 16px; text-align: center; font-weight: bold; font-size: 1.1em;">{college_avg['Overall']:.2f}</td>
                    </tr>
                    </tbody>
                </table>
            </div>
            
            <div style="margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 8px; display: flex; align-items: center; gap: 30px;">
                <span style="font-weight: 600; color: #2c3e50;">Performance Indicators:</span>
                <span style="color: #28a745;">↑ Above Average (+0.2)</span>
                <span style="color: #666;">• Within Average (±0.2)</span>
                <span style="color: #dc3545;">↓ Below Average (-0.2)</span>
            </div>
            
            <!-- Removed broken/empty charts that weren't rendering properly -->
        </div>
"""
        
        
        # SECTION 2: STATEMENT LEVEL ANALYSIS
        html_content += """
        <div style="background: #f0f4f8; padding: 30px 0; margin-top: 30px;">
            <h1 style="text-align: center; color: #2c3e50; border-bottom: 3px solid #667eea; padding-bottom: 10px; margin: 0 auto 30px; max-width: 500px;">
                SECTION 2: STATEMENT LEVEL ANALYSIS
            </h1>
        </div>
        """
        
        # Add comprehensive statement analysis section
        s_data = analysis_results['statement_analysis']
        
        html_content += """
        <div class="section">
            <h2>VESPA Statement Analysis</h2>
            <p style="margin-bottom: 20px;">Detailed analysis of individual VESPA statement responses reveals specific strengths and development areas. 
            Each statement is analyzed across all three cycles to identify overall progression patterns from baseline to final assessment.</p>
            
            <h3>Statements Showing Greatest Improvement (Cycle 1 to Cycle 3)</h3>
            <table>
                <thead>
                    <tr>
                        <th>Statement</th>
                        <th>Category</th>
                        <th>Cycle 1</th>
                        <th>Cycle 2</th>
                        <th>Cycle 3</th>
                        <th>C2→C3 Change</th>
                    </tr>
                </thead>
                <tbody>
"""
        
        for s in s_data.get('most_improved', []):
            # Get Cycle 1 mean from the cycle_progression data
            cycle1_mean = s.get('cycle_1_mean', 0)
            if cycle1_mean == 0:
                # Try to get from statement analysis
                for stmt_id, stmt_data in s_data.get('cycle_progression', {}).items():
                    if stmt_data.get('text') == s['text']:
                        if 'cycle_1' in stmt_data:
                            cycle1_mean = stmt_data['cycle_1'].get('mean', 0)
                        break
            
            cycle1_str = f"{cycle1_mean:.2f}" if cycle1_mean > 0 else "-"
            html_content += f"""
                    <tr>
                        <td style="padding: 10px;">{s['text']}</td>
                        <td style="padding: 10px; text-align: center;">{s['category']}</td>
                        <td style="padding: 10px; text-align: center;">{cycle1_str}</td>
                        <td style="padding: 10px; text-align: center;">{s['cycle_2_mean']:.2f}</td>
                        <td style="padding: 10px; text-align: center;">{s['cycle_3_mean']:.2f}</td>
                        <td style="padding: 10px; text-align: center;" class="positive">+{s['improvement']:.2f}</td>
                </tr>
"""
        
        html_content += """
                </tbody>
            </table>
            
            <h3>Statements Showing Decline (Cycle 1 to Cycle 3)</h3>
            <table>
                <thead>
                    <tr>
                        <th>Statement</th>
                        <th>Category</th>
                        <th>Cycle 1</th>
                        <th>Cycle 2</th>
                        <th>Cycle 3</th>
                        <th>C2→C3 Change</th>
                    </tr>
                </thead>
                <tbody>
"""
        
        for s in s_data.get('most_declined', []):
            # Get Cycle 1 mean
            cycle1_mean = s.get('cycle_1_mean', 0)
            if cycle1_mean == 0:
                for stmt_id, stmt_data in s_data.get('cycle_progression', {}).items():
                    if stmt_data.get('text') == s['text']:
                        if 'cycle_1' in stmt_data:
                            cycle1_mean = stmt_data['cycle_1'].get('mean', 0)
                        break
            
            cycle1_str = f"{cycle1_mean:.2f}" if cycle1_mean > 0 else "-"
            html_content += f"""
                    <tr>
                        <td style="padding: 10px;">{s['text']}</td>
                        <td style="padding: 10px; text-align: center;">{s['category']}</td>
                        <td style="padding: 10px; text-align: center;">{cycle1_str}</td>
                        <td style="padding: 10px; text-align: center;">{s['cycle_2_mean']:.2f}</td>
                        <td style="padding: 10px; text-align: center;">{s['cycle_3_mean']:.2f}</td>
                        <td style="padding: 10px; text-align: center;" class="negative">{s['decline']:.2f}</td>
                </tr>
"""
        
        html_content += """
                </tbody>
            </table>
            
            <h3>Strongest Beliefs (Top Performing Overall)</h3>
            <table>
                <thead>
                    <tr>
                        <th>Statement</th>
                        <th>Category</th>
                        <th>Cycle 1</th>
                        <th>Cycle 2</th>
                        <th>Cycle 3</th>
                        <th>Average</th>
                    </tr>
                </thead>
                <tbody>
"""
        
        for s in s_data['top_statements']:
            # Get all cycle means
            cycle1_mean = 0
            cycle2_mean = 0
            cycle3_mean = 0
            
            for stmt_id, stmt_data in s_data.get('cycle_progression', {}).items():
                if stmt_data.get('text') == s['text']:
                    if 'cycle_1' in stmt_data:
                        cycle1_mean = stmt_data['cycle_1'].get('mean', 0)
                    if 'cycle_2' in stmt_data:
                        cycle2_mean = stmt_data['cycle_2'].get('mean', 0)
                    if 'cycle_3' in stmt_data:
                        cycle3_mean = stmt_data['cycle_3'].get('mean', 0)
                    break
            
            cycle1_str = f"{cycle1_mean:.2f}" if cycle1_mean > 0 else "-"
            cycle2_str = f"{cycle2_mean:.2f}" if cycle2_mean > 0 else "-"
            cycle3_str = f"{cycle3_mean:.2f}" if cycle3_mean > 0 else "-"
            
            html_content += f"""
                    <tr>
                        <td style="padding: 10px;">{s['text']}</td>
                        <td style="padding: 10px; text-align: center;">{s['category']}</td>
                        <td style="padding: 10px; text-align: center;">{cycle1_str}</td>
                        <td style="padding: 10px; text-align: center;">{cycle2_str}</td>
                        <td style="padding: 10px; text-align: center;">{cycle3_str}</td>
                        <td style="padding: 10px; text-align: center;" class="positive">{s['mean_score']:.2f}</td>
                </tr>
"""
        
        html_content += """
                </tbody>
            </table>
            
            <h3>Areas for Development (Lowest Performing)</h3>
            <table>
                <thead>
                    <tr>
                        <th>Statement</th>
                        <th>Category</th>
                        <th>Cycle 1</th>
                        <th>Cycle 2</th>
                        <th>Cycle 3</th>
                        <th>Average</th>
                    </tr>
                </thead>
                <tbody>
"""
        
        for s in s_data['bottom_statements']:
            # Get all cycle means
            cycle1_mean = 0
            cycle2_mean = 0
            cycle3_mean = 0
            
            for stmt_id, stmt_data in s_data.get('cycle_progression', {}).items():
                if stmt_data.get('text') == s['text']:
                    if 'cycle_1' in stmt_data:
                        cycle1_mean = stmt_data['cycle_1'].get('mean', 0)
                    if 'cycle_2' in stmt_data:
                        cycle2_mean = stmt_data['cycle_2'].get('mean', 0)
                    if 'cycle_3' in stmt_data:
                        cycle3_mean = stmt_data['cycle_3'].get('mean', 0)
                    break
            
            cycle1_str = f"{cycle1_mean:.2f}" if cycle1_mean > 0 else "-"
            cycle2_str = f"{cycle2_mean:.2f}" if cycle2_mean > 0 else "-"
            cycle3_str = f"{cycle3_mean:.2f}" if cycle3_mean > 0 else "-"
            
            html_content += f"""
                    <tr>
                        <td style="padding: 10px;">{s['text']}</td>
                        <td style="padding: 10px; text-align: center;">{s['category']}</td>
                        <td style="padding: 10px; text-align: center;">{cycle1_str}</td>
                        <td style="padding: 10px; text-align: center;">{cycle2_str}</td>
                        <td style="padding: 10px; text-align: center;">{cycle3_str}</td>
                        <td style="padding: 10px; text-align: center;" class="negative">{s['mean_score']:.2f}</td>
                </tr>
"""
        
        html_content += """
                </tbody>
            </table>
            
            <div style="margin-top: 30px; padding: 20px; background: #f8f9fa; border-radius: 10px;">
                <h4>Key Statement Analysis Insights</h4>
                <ul style="margin-top: 10px;">
"""
        
        # Add insights based on question analysis
        if s_data.get('most_improved'):
            top_improved = s_data['most_improved'][0]
            html_content += f"""
                    <li><strong>Biggest Overall Improvement:</strong> "{top_improved['text']}" showed {top_improved['improvement']:+.2f} improvement from Cycle 1 to 3</li>
"""
        
        if s_data.get('top_statements'):
            strongest = s_data['top_statements'][0]
            html_content += f"""
                    <li><strong>Greatest Strength:</strong> Students strongly believe "{strongest['text']}" (Score: {strongest['mean_score']:.2f})</li>
"""
        
        if s_data.get('bottom_statements'):
            weakest = s_data['bottom_statements'][0]
            html_content += f"""
                    <li><strong>Primary Challenge:</strong> Students struggle with "{weakest['text']}" (Score: {weakest['mean_score']:.2f})</li>
"""
        
        html_content += """
                </ul>
            </div>
"""
        
        # Add simplified statement agreement analysis
        html_content += """
        <div style="margin-top: 50px; padding: 30px; background: linear-gradient(to right, #f8f9fa, #ffffff); border-radius: 12px; border: 1px solid #e9ecef;">
            <h3 style="color: #2c3e50; margin-bottom: 25px; font-size: 1.6em;">Statement Agreement Analysis</h3>
            <p style="color: #666; margin-bottom: 30px;">Analysis of which statements students most and least agree with across all assessment cycles.</p>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 30px;">
                <div style="background: #fff; padding: 25px; border-radius: 10px; border: 2px solid #28a745;">
                    <h4 style="color: #28a745; margin-bottom: 20px; font-size: 1.2em;">Top 10 - Students Strongly Agree</h4>
                    <ol style="margin: 0; padding-left: 20px; line-height: 1.8;">
"""
        
        # Add top 10 statements
        for i, stmt in enumerate(s_data.get('top_statements', [])[:10]):
            html_content += f"""
                        <li style="margin-bottom: 12px; color: #333;">
                            <strong>{stmt['text']}</strong>
                            <br>
                            <span style="color: #666; font-size: 0.9em;">
                                Average Score: {stmt['mean_score']:.2f} | Category: {stmt['category']}
                            </span>
                        </li>
"""
        
        html_content += """
                    </ol>
                </div>
                
                <div style="background: #fff; padding: 25px; border-radius: 10px; border: 2px solid #dc3545;">
                    <h4 style="color: #dc3545; margin-bottom: 20px; font-size: 1.2em;">Bottom 10 - Students Least Agree</h4>
                    <ol style="margin: 0; padding-left: 20px; line-height: 1.8;">
"""
        
        # Add bottom 10 statements
        for i, stmt in enumerate(s_data.get('bottom_statements', [])[:10]):
            html_content += f"""
                        <li style="margin-bottom: 12px; color: #333;">
                            <strong>{stmt['text']}</strong>
                            <br>
                            <span style="color: #666; font-size: 0.9em;">
                                Average Score: {stmt['mean_score']:.2f} | Category: {stmt['category']}
                            </span>
                        </li>
"""
        
        html_content += """
                    </ol>
                </div>
            </div>
            
            <div style="margin-top: 30px; padding: 20px; background: #f8f9fa; border-radius: 8px;">
                <p style="margin: 0; font-size: 0.95em; color: #555;">
                    <strong>Interpretation Guide:</strong> Scores above 7.0 indicate strong agreement, scores between 5.0-7.0 show moderate agreement, 
                    and scores below 5.0 suggest areas where students lack confidence or need additional support. Focus interventions on bottom-scoring statements
                    while leveraging strengths from top-scoring areas.
                </p>
            </div>
        </div>
"""
        
        html_content += """
        </div>
"""
        
        
        # Add JavaScript for charts
        html_content += """
        <div class="footer">
            <p>© 2024 VESPA Education Analytics | Confidential Report</p>
        </div>
    </div>
    
    <script>
"""
        
        # Add Plotly chart data
        for chart_name, fig in figures.items():
            html_content += f"""
        // {chart_name} chart
        var {chart_name}_data = {fig.to_json()};
        Plotly.newPlot('{chart_name.replace("_", "-")}-chart', 
            {chart_name}_data.data, 
            {chart_name}_data.layout, 
            {{responsive: true}});
"""
        
        html_content += """
    </script>
</body>
</html>
"""
        
        return html_content
    
    def run_analysis(self):
        """Run the complete analysis pipeline"""
        print("\n" + "="*60)
        print("SAMPLE COLLEGE - VESPA ANALYSIS (DEMO)")
        print("="*60 + "\n")
        
        # Load data
        self.load_data()
        
        # Run analyses
        print("\nRunning analyses...")
        analysis_results = {
            'cycle_progression': self.analyze_cycle_progression(),
            'faculty_comparison': self.analyze_faculty_comparison(),
            'statement_analysis': self.analyze_statements()
        }
        
        # Create visualizations
        print("Creating visualizations...")
        figures = self.create_visualizations()
        
        # Generate HTML report
        print("Generating HTML report...")
        html_content = self.generate_html_report(analysis_results, figures)
        
        # Save report
        report_filename = f'Demo_VESPA_Report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.html'
        with open(report_filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"\n✅ Report generated successfully: {report_filename}")
        print(f"📂 File location: {os.path.abspath(report_filename)}")
        
        # Generate summary statistics
        print("\n" + "="*60)
        print("SUMMARY STATISTICS")
        print("="*60)
        
        print(f"\nTotal Students Analyzed: {len(self.results_df)}")
        print(f"Total Faculties: {len(self.faculties)}")
        print(f"Total Tutor Groups: {len(self.tutor_groups)}")
        
        # Cycle participation
        for cycle in ['1', '2', '3']:
            col = f'O{cycle}'  # Overall score for cycle
            if col in self.results_df.columns:
                n_students = self.results_df[col].notna().sum()
                print(f"Cycle {cycle} Participants: {n_students}")
        
        # Overall improvements
        print("\nMean Improvements (Cycle 1 to 2):")
        for cat in self.vespa_categories:
            key = f'{cat}_C1_to_C2'
            if key in analysis_results['cycle_progression']['cycle_comparison']:
                data = analysis_results['cycle_progression']['cycle_comparison'][key]
                print(f"  {cat}: {data['mean_improvement']:+.2f} ({data['percent_improved']:.0f}% improved)")
        
        print("\nMean Improvements (Cycle 2 to 3 - Recovery Phase):")
        for cat in self.vespa_categories:
            key = f'{cat}_C2_to_C3'
            if key in analysis_results['cycle_progression']['cycle_comparison']:
                data = analysis_results['cycle_progression']['cycle_comparison'][key]
                print(f"  {cat}: {data['mean_improvement']:+.2f} ({data['percent_improved']:.0f}% improved, n={data['n_students']})")
        
        print("\nOverall Journey (Cycle 1 to 3 - Complete Students):")
        for cat in self.vespa_categories:
            key = f'{cat}_C1_to_C3_overall'
            if key in analysis_results['cycle_progression']['cycle_comparison']:
                data = analysis_results['cycle_progression']['cycle_comparison'][key]
                print(f"  {cat}: {data['overall_improvement']:+.2f} ({data['mean_c1']:.1f} → {data['mean_c2']:.1f} → {data['mean_c3']:.1f}, n={data['n_students']})")
        
        return report_filename

if __name__ == "__main__":
    analyzer = DemoVESPAAnalyzer()
    report_file = analyzer.run_analysis()
    
    print("\n🎉 Analysis complete!")
    print(f"📊 Open the report in your browser: file:///{os.path.abspath(report_file)}")
