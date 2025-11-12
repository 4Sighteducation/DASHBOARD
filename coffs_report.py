#!/usr/bin/env python3
"""
Coffs Harbour Senior College - 3 Cycle Analysis Report Generator
Generates comprehensive analysis of VESPA data across 3 cycles with interactive charts
Includes statement-level analysis and progression tracking
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

class CoffsAnalyzer:
    def __init__(self):
        """Initialize the Coffs Harbour data analyzer"""
        self.vespa_categories = ['Vision', 'Effort', 'Systems', 'Practice', 'Attitude']
        self.vespa_colors = {
            'Vision': '#e59437',     # Orange
            'Effort': '#86b4f0',      # Light Blue
            'Systems': '#72cb44',     # Green
            'Practice': '#7f31a4',    # Purple
            'Attitude': '#f032e6',    # Pink
            'Overall': '#ffd700'      # Gold/Yellow
        }
        
        # National distribution data from Knack object_120
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
        
        # Statement text mappings
        self.statement_texts = {
            'Q1V': "I've worked out the next steps in my life",
            'Q2S': "I plan and organise my time to get my work done",
            'Q3V': "I give a lot of attention to my career planning",
            'Q4S': "I complete all my homework on time",
            'Q5A': "No matter who you are, you can change your intelligence a lot",
            'Q6E': "I use all my independent study time effectively",
            'Q7P': "I test myself on important topics until I remember them",
            'Q8A': "I have a positive view of myself",
            'Q9E': "I am a hard working student",
            'Q10A': "I am confident in my academic ability",
            'Q11S': "I always meet deadlines",
            'Q12P': "I spread out my revision, rather than cramming at the last minute",
            'Q13A': "I don't let a poor test/assessment result get me down for too long",
            'Q14V': "I strive to achieve the goals I set for myself",
            'Q15P': "I summarise important information in diagrams, tables or lists",
            'Q16V': "I enjoy learning new things",
            'Q17E': "I'm not happy unless my work is the best it can be",
            'Q18S': "I take good notes in class which are useful for revision",
            'Q19P': "When revising I mix different kinds of topics/subjects in one study session",
            'Q20A': "I feel I can cope with the pressure at school/college/University",
            'Q21E': "I work as hard as I can in most classes",
            'Q22S': "My books/files are organised",
            'Q23P': "When preparing for a test/exam I teach someone else the material",
            'Q24A': "I'm happy to ask questions in front of a group",
            'Q25P': "I use highlighting/colour coding for revision",
            'Q26A': "Your intelligence is something about you that you can change very much",
            'Q27A': "I like hearing feedback about how I can improve",
            'Q28A': "I can control my nerves in tests/practical assessments",
            'Q29V': "I understand why education is important for my future"
        }
        
        # Insight definitions - from insights.js configuration
        self.insight_definitions = {
            'growth_mindset': {
                'title': 'Growth Mindset',
                'icon': '🌱',
                'description': 'Measures students\' belief that intelligence and abilities can be developed through effort and learning.',
                'questions': ['Q5A', 'Q26A']
            },
            'academic_momentum': {
                'title': 'Academic Momentum',
                'icon': '🚀',
                'description': 'Captures students\' intrinsic drive, engagement with learning, and commitment to excellence.',
                'questions': ['Q14V', 'Q16V', 'Q17E', 'Q9E']
            },
            'study_effectiveness': {
                'title': 'Study Effectiveness',
                'icon': '📚',
                'description': 'Measures adoption of evidence-based study techniques that improve learning and retention.',
                'questions': ['Q7P', 'Q12P', 'Q15P']
            },
            'organization_skills': {
                'title': 'Organization Skills',
                'icon': '📋',
                'description': 'Measures students\' ability to plan, organize, and manage their academic responsibilities.',
                'questions': ['Q2S', 'Q22S', 'Q11S']
            },
            'resilience_factor': {
                'title': 'Resilience',
                'icon': '🛡️',
                'description': 'Students\' ability to bounce back from setbacks and maintain a positive outlook.',
                'questions': ['Q13A', 'Q8A', 'Q27A']
            },
            'stress_management': {
                'title': 'Stress Management',
                'icon': '🧘',
                'description': 'Students\' ability to handle academic pressure and control exam nerves.',
                'questions': ['Q20A', 'Q28A']
            },
            'active_learning': {
                'title': 'Active Learning',
                'icon': '🎯',
                'description': 'Engagement with active learning techniques that deepen understanding and retention.',
                'questions': ['Q7P', 'Q23P', 'Q19P']
            },
            'time_management': {
                'title': 'Time Management',
                'icon': '⏰',
                'description': 'Students\' ability to effectively plan and use their time for academic work.',
                'questions': ['Q2S', 'Q4S', 'Q11S']
            },
            'academic_confidence': {
                'title': 'Academic Confidence',
                'icon': '🎓',
                'description': 'Students\' belief in their academic abilities and positive self-perception.',
                'questions': ['Q10A', 'Q8A']
            }
        }
        
    def load_data(self, csv_path):
        """Load the COFFS data file"""
        print(f"Loading data from {csv_path}...")
        
        # Load the data
        self.df = pd.read_csv(csv_path)
        print(f"Loaded {len(self.df)} student records")
        
        # Clean data
        self._clean_data()
        
    def _clean_data(self):
        """Clean and prepare the data"""
        # Convert VESPA score columns to numeric
        vespa_cols = []
        for cycle in [1, 2, 3]:
            for cat in ['V', 'E', 'S', 'P', 'A', 'O']:
                col = f'{cat}{cycle}'
                if col in self.df.columns:
                    vespa_cols.append(col)
                    self.df[col] = pd.to_numeric(self.df[col], errors='coerce')
        
        # Convert question columns to numeric
        question_cols = [col for col in self.df.columns if col.startswith('c') and '_Q' in col]
        for col in question_cols:
            self.df[col] = pd.to_numeric(self.df[col], errors='coerce')
        
        # Convert additional metrics to numeric
        for metric in ['sup', 'prep', 'conf']:
            for cycle in [1, 2, 3]:
                col = f'c{cycle}_{metric}'
                if col in self.df.columns:
                    self.df[col] = pd.to_numeric(self.df[col], errors='coerce')
        
        print(f"Data cleaning complete. Found {len(vespa_cols)} VESPA score columns and {len(question_cols)} question columns.")
        
    def calculate_distribution(self, series):
        """Calculate score distribution as percentages"""
        dist = {}
        total = len(series)
        if total == 0:
            return dist
        
        for score in range(1, 11):
            count = (series == score).sum()
            dist[score] = (count / total) * 100
        
        return dist
    
    def get_national_distribution_percentages(self, category, cycle):
        """Get national distribution percentages for a category and cycle"""
        cycle_key = f'cycle_{cycle}'
        if cycle_key in self.national_distributions:
            dist_data = self.national_distributions[cycle_key].get(category, {})
            total = self.national_distributions[cycle_key].get('total', 1)
            
            percentages = {}
            for score in range(1, 11):
                count = dist_data.get(score, 0)
                percentages[score] = (count / total) * 100
            
            return percentages
        return {}
    
    def create_cycle_progression_chart(self, analysis_results):
        """Create interactive Plotly chart showing progression across cycles"""
        progression = analysis_results['progression_analysis']
        cycle_means = progression.get('cycle_means', {})
        
        # Create subplots for each dimension
        fig = make_subplots(
            rows=2, cols=3,
            subplot_titles=('Vision', 'Effort', 'Systems', 'Practice', 'Attitude', 'Overall'),
            vertical_spacing=0.15,
            horizontal_spacing=0.1
        )
        
        positions = [
            (1, 1), (1, 2), (1, 3),
            (2, 1), (2, 2), (2, 3)
        ]
        
        for idx, cat in enumerate(self.vespa_categories + ['Overall']):
            row, col = positions[idx]
            color = self.vespa_colors[cat]
            
            # School data
            school_values = []
            for cycle_num in [1, 2, 3]:
                cycle_key = f'cycle_{cycle_num}'
                if cycle_key in cycle_means and cat in cycle_means[cycle_key]:
                    school_values.append(cycle_means[cycle_key][cat]['mean'])
                else:
                    school_values.append(None)
            
            # National averages
            national_values = []
            for cycle_num in [1, 2, 3]:
                cycle_key = f'cycle_{cycle_num}'
                if cycle_key in self.national_stats and cat in self.national_stats[cycle_key]:
                    national_values.append(self.national_stats[cycle_key][cat]['mean'])
                else:
                    national_values.append(None)
            
            # Add school trace
            fig.add_trace(
                go.Scatter(
                    x=['Cycle 1', 'Cycle 2', 'Cycle 3'],
                    y=school_values,
                    mode='lines+markers',
                    name=f'Coffs {cat}',
                    line=dict(color=color, width=4),
                    marker=dict(size=12, symbol='circle'),
                    showlegend=False
                ),
                row=row, col=col
            )
            
            # Add national average trace
            fig.add_trace(
                go.Scatter(
                    x=['Cycle 1', 'Cycle 2', 'Cycle 3'],
                    y=national_values,
                    mode='lines',
                    name='National Average',
                    line=dict(color='rgba(128, 128, 128, 0.5)', width=2, dash='dash'),
                    showlegend=False
                ),
                row=row, col=col
            )
            
            # Add improvement annotation for Cycle 3
            if school_values[2] is not None and school_values[1] is not None:
                improvement = school_values[2] - school_values[1]
                fig.add_annotation(
                    x='Cycle 3',
                    y=school_values[2],
                    text=f"↑ {improvement:+.1f}" if improvement > 0 else f"↓ {improvement:.1f}",
                    showarrow=False,
                    font=dict(size=10, color='green' if improvement > 0 else 'red'),
                    yshift=15,
                    row=row, col=col
                )
            
            # Update y-axis
            fig.update_yaxes(title_text="Score", range=[3, 10], row=row, col=col)
        
        fig.update_layout(
            title_text="VESPA Score Progression: Students Who Completed All 3 Cycles",
            height=700,
            showlegend=False,
            font=dict(family="Arial, sans-serif"),
            paper_bgcolor='rgba(248,249,250,1)',
            plot_bgcolor='white'
        )
        
        return fig.to_html(full_html=False, include_plotlyjs=False, div_id='cycle-prog')
    
    def create_distribution_chart(self, dimension, cycle_means):
        """Create distribution chart for a specific dimension across all 3 cycles"""
        fig = make_subplots(
            rows=1, cols=3,
            subplot_titles=('Cycle 1', 'Cycle 2', 'Cycle 3'),
            horizontal_spacing=0.08
        )
        
        color = self.vespa_colors[dimension]
        
        for cycle_num in [1, 2, 3]:
            col_name = f'{dimension[0]}{cycle_num}'
            if col_name in self.df.columns:
                scores = self.df[col_name].dropna()
                dist = self.calculate_distribution(scores)
                
                # Get national distribution
                nat_dist = self.get_national_distribution_percentages(dimension, cycle_num)
                
                # School distribution bars
                fig.add_trace(
                    go.Bar(
                        x=list(range(1, 11)),
                        y=[dist.get(i, 0) for i in range(1, 11)],
                        name='Coffs',
                        marker_color=color,
                        opacity=0.7,
                        showlegend=(cycle_num == 1)
                    ),
                    row=1, col=cycle_num
                )
                
                # National distribution line
                fig.add_trace(
                    go.Scatter(
                        x=list(range(1, 11)),
                        y=[nat_dist.get(i, 0) for i in range(1, 11)],
                        mode='lines+markers',
                        name='National',
                        line=dict(color='red', width=2),
                        marker=dict(size=6),
                        showlegend=(cycle_num == 1)
                    ),
                    row=1, col=cycle_num
                )
                
                # Add mean score annotation
                school_mean = scores.mean()
                nat_mean = self.national_stats[f'cycle_{cycle_num}'][dimension]['mean']
                
                fig.add_annotation(
                    x=5.5,
                    y=max([dist.get(i, 0) for i in range(1, 11)]) * 1.1,
                    text=f"Coffs: {school_mean:.1f}<br>National: {nat_mean:.1f}",
                    showarrow=False,
                    font=dict(size=10),
                    row=1, col=cycle_num
                )
            
            # Update axes
            fig.update_xaxes(title_text="Score", range=[0.5, 10.5], row=1, col=cycle_num)
            if cycle_num == 1:
                fig.update_yaxes(title_text="Percentage (%)", row=1, col=cycle_num)
            else:
                fig.update_yaxes(title_text="", row=1, col=cycle_num)
        
        fig.update_layout(
            title_text=f"{dimension} Score Distributions Across Cycles",
            height=400,
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            paper_bgcolor='white',
            plot_bgcolor='rgba(240,240,240,0.3)'
        )
        
        return fig.to_html(full_html=False, include_plotlyjs=False, div_id=f'dist-{dimension.lower()}')
    
    def analyze_cycle_progression(self):
        """Analyze progression across all three cycles"""
        analysis = {
            'cycle_means': {},
            'cycle_comparison': {},
            'improvements': {},
            'statistics': {}
        }
        
        # Calculate means for each cycle
        for cycle in [1, 2, 3]:
            analysis['cycle_means'][f'cycle_{cycle}'] = {}
            for cat in self.vespa_categories:
                col = f'{cat[0]}{cycle}'
                if col in self.df.columns:
                    scores = self.df[col].dropna()
                    if len(scores) > 0:
                        analysis['cycle_means'][f'cycle_{cycle}'][cat] = {
                            'mean': scores.mean(),
                            'std': scores.std(),
                            'median': scores.median(),
                            'n': len(scores),
                            'q1': scores.quantile(0.25),
                            'q3': scores.quantile(0.75)
                        }
            
            # Overall score
            col = f'O{cycle}'
            if col in self.df.columns:
                scores = self.df[col].dropna()
                if len(scores) > 0:
                    analysis['cycle_means'][f'cycle_{cycle}']['Overall'] = {
                        'mean': scores.mean(),
                        'std': scores.std(),
                        'median': scores.median(),
                        'n': len(scores),
                        'q1': scores.quantile(0.25),
                        'q3': scores.quantile(0.75)
                    }
        
        # Compare cycles
        for cat in self.vespa_categories + ['Overall']:
            cat_initial = cat[0] if cat != 'Overall' else 'O'
            
            # Cycle 1 to 2
            c1_col = f'{cat_initial}1'
            c2_col = f'{cat_initial}2'
            c3_col = f'{cat_initial}3'
            
            if c1_col in self.df.columns and c2_col in self.df.columns:
                both_cycles = self.df[[c1_col, c2_col]].dropna()
                if len(both_cycles) > 0:
                    improvement = both_cycles[c2_col] - both_cycles[c1_col]
                    
                    analysis['cycle_comparison'][f'{cat}_C1_to_C2'] = {
                        'mean_c1': both_cycles[c1_col].mean(),
                        'mean_c2': both_cycles[c2_col].mean(),
                        'mean_improvement': improvement.mean(),
                        'std_improvement': improvement.std(),
                        'percent_improved': (improvement > 0).sum() / len(improvement) * 100,
                        'n_students': len(both_cycles),
                        'cohen_d': self._calculate_cohens_d(both_cycles[c1_col], both_cycles[c2_col])
                    }
            
            # Cycle 2 to 3
            if c2_col in self.df.columns and c3_col in self.df.columns:
                both_cycles = self.df[[c2_col, c3_col]].dropna()
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
            
            # Overall progression Cycle 1 to 3
            if c1_col in self.df.columns and c3_col in self.df.columns:
                all_three = self.df[[c1_col, c2_col, c3_col]].dropna()
                if len(all_three) > 0:
                    overall_improvement = all_three[c3_col] - all_three[c1_col]
                    
                    analysis['cycle_comparison'][f'{cat}_C1_to_C3_overall'] = {
                        'mean_c1': all_three[c1_col].mean(),
                        'mean_c2': all_three[c2_col].mean(),
                        'mean_c3': all_three[c3_col].mean(),
                        'overall_improvement': overall_improvement.mean(),
                        'percent_improved_overall': (overall_improvement > 0).sum() / len(overall_improvement) * 100,
                        'n_students': len(all_three),
                        'cohen_d': self._calculate_cohens_d(all_three[c1_col], all_three[c3_col])
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
    
    def analyze_year_groups(self):
        """Analyze performance by year group"""
        if 'Year Gp' not in self.df.columns:
            return {}
        
        year_group_analysis = {}
        
        for year_group in self.df['Year Gp'].dropna().unique():
            year_data = self.df[self.df['Year Gp'] == year_group]
            
            if len(year_data) > 3:  # Only analyze groups with sufficient data
                year_group_analysis[year_group] = {
                    'n_students': len(year_data),
                    'cycles': {}
                }
                
                # Analyze each cycle for this year group
                for cycle in [1, 2, 3]:
                    cycle_data = {}
                    for cat in self.vespa_categories + ['Overall']:
                        cat_initial = cat[0] if cat != 'Overall' else 'O'
                        col = f'{cat_initial}{cycle}'
                        
                        if col in year_data.columns:
                            scores = year_data[col].dropna()
                            if len(scores) > 0:
                                cycle_data[cat] = {
                                    'mean': scores.mean(),
                                    'std': scores.std(),
                                    'n': len(scores)
                                }
                    
                    if cycle_data:
                        year_group_analysis[year_group]['cycles'][f'cycle_{cycle}'] = cycle_data
        
        return year_group_analysis
    
    def analyze_gender_differences(self):
        """Analyze performance differences by gender"""
        if 'Gender' not in self.df.columns:
            return {}
        
        gender_analysis = {}
        
        for gender in self.df['Gender'].dropna().unique():
            gender_data = self.df[self.df['Gender'] == gender]
            
            if len(gender_data) > 3:
                gender_analysis[gender] = {
                    'n_students': len(gender_data),
                    'cycles': {}
                }
                
                for cycle in [1, 2, 3]:
                    cycle_data = {}
                    for cat in self.vespa_categories + ['Overall']:
                        cat_initial = cat[0] if cat != 'Overall' else 'O'
                        col = f'{cat_initial}{cycle}'
                        
                        if col in gender_data.columns:
                            scores = gender_data[col].dropna()
                            if len(scores) > 0:
                                cycle_data[cat] = {
                                    'mean': scores.mean(),
                                    'std': scores.std(),
                                    'n': len(scores)
                                }
                    
                    if cycle_data:
                        gender_analysis[gender]['cycles'][f'cycle_{cycle}'] = cycle_data
        
        return gender_analysis
    
    def analyze_statements(self):
        """Comprehensive statement-level analysis across all cycles WITH VARIANCE"""
        statement_analysis = {
            'top_statements': [],
            'bottom_statements': [],
            'cycle_progression': {},
            'most_improved': [],
            'most_declined': []
        }
        
        # Process question responses for each cycle
        cycle_question_data = {1: {}, 2: {}, 3: {}}
        
        for col in self.df.columns:
            if col.startswith('c') and '_Q' in col:
                # Parse column name (e.g., 'c1_Q1v' -> cycle 1, question 1, vision)
                parts = col.split('_')
                if len(parts) == 2 and parts[1].startswith('Q'):
                    cycle_num = int(parts[0][1])  # Extract cycle number
                    q_part = parts[1].upper()  # e.g., 'Q1V'
                    
                    # Calculate mean score AND VARIANCE for this question in this cycle
                    scores = pd.to_numeric(self.df[col], errors='coerce').dropna()
                    if len(scores) > 0:
                        if q_part not in cycle_question_data[cycle_num]:
                            cycle_question_data[cycle_num][q_part] = {
                                'mean': scores.mean(),
                                'std': scores.std(),
                                'variance': scores.var(),  # ADD VARIANCE
                                'count': len(scores),
                                'scores': scores.tolist(),
                                'median': scores.median(),
                                'min': scores.min(),
                                'max': scores.max()
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
            
            # Get statement text
            statement_text = self.statement_texts.get(q_id, f"Statement {q_id}")
            
            # Determine VESPA category
            cat_map = {'V': 'Vision', 'E': 'Effort', 'S': 'Systems', 'P': 'Practice', 'A': 'Attitude'}
            vespa_cat = cat_map.get(q_id[-1] if q_id else '', 'Unknown')
            
            statement_analysis['cycle_progression'][q_id] = {
                'text': statement_text,
                'category': vespa_cat,
                **q_progression
            }
        
        # Find top and bottom performing statements (across all cycles)
        statement_means = []
        for q_id, data in statement_analysis['cycle_progression'].items():
            cycle_means = []
            cycle_stds = []
            for cycle in [1, 2, 3]:
                if f'cycle_{cycle}' in data:
                    cycle_means.append(data[f'cycle_{cycle}']['mean'])
                    cycle_stds.append(data[f'cycle_{cycle}']['std'])
            
            if cycle_means:
                avg_mean = np.mean(cycle_means)
                avg_std = np.mean(cycle_stds) if cycle_stds else 0
                statement_means.append((q_id, avg_mean, avg_std, data))
        
        statement_means.sort(key=lambda x: x[1], reverse=True)
        
        # Top statements - include variance data
        for q_id, avg_mean, avg_std, data in statement_means[:5]:
            statement_analysis['top_statements'].append({
                'statement': q_id,
                'text': data['text'],
                'category': data['category'],
                'mean_score': avg_mean,
                'std_dev': avg_std,
                'variance': avg_std ** 2
            })
        
        # Bottom statements - include variance data
        for q_id, avg_mean, avg_std, data in statement_means[-5:]:
            statement_analysis['bottom_statements'].append({
                'statement': q_id,
                'text': data['text'],
                'category': data['category'],
                'mean_score': avg_mean,
                'std_dev': avg_std,
                'variance': avg_std ** 2
            })
        
        # Find most improved statements (Cycle 2 to 3 - since not all have C1)
        improvements = []
        for q_id, data in statement_analysis['cycle_progression'].items():
            if 'c2_to_c3' in data and 'cycle_2' in data and 'cycle_3' in data:
                improvements.append((q_id, data['c2_to_c3'], data))
        
        improvements.sort(key=lambda x: x[1], reverse=True)
        
        # Most improved - include variance
        for q_id, improvement, data in improvements[:5]:
            if improvement > 0:
                c2_std = data['cycle_2'].get('std', 0)
                c3_std = data['cycle_3'].get('std', 0)
                statement_analysis['most_improved'].append({
                    'statement': q_id,
                    'text': data['text'],
                    'category': data['category'],
                    'improvement': improvement,
                    'cycle_2_mean': data['cycle_2']['mean'],
                    'cycle_3_mean': data['cycle_3']['mean'],
                    'cycle_2_std': c2_std,
                    'cycle_3_std': c3_std,
                    'avg_variance': ((c2_std ** 2) + (c3_std ** 2)) / 2
                })
        
        # Most declined - include variance
        for q_id, improvement, data in improvements[-5:]:
            if improvement < 0:  # Only include actual declines
                c2_std = data['cycle_2'].get('std', 0)
                c3_std = data['cycle_3'].get('std', 0)
                statement_analysis['most_declined'].append({
                    'statement': q_id,
                    'text': data['text'],
                    'category': data['category'],
                    'decline': improvement,
                    'cycle_2_mean': data['cycle_2']['mean'],
                    'cycle_3_mean': data['cycle_3']['mean'],
                    'cycle_2_std': c2_std,
                    'cycle_3_std': c3_std,
                    'avg_variance': ((c2_std ** 2) + (c3_std ** 2)) / 2
                })
        
        return statement_analysis
    
    def analyze_additional_metrics(self):
        """Analyze support, preparedness, and confidence metrics"""
        metrics_analysis = {}
        
        for metric_name, metric_code in [('Support', 'sup'), ('Preparedness', 'prep'), ('Confidence', 'conf')]:
            metrics_analysis[metric_name] = {}
            
            for cycle in [1, 2, 3]:
                col = f'c{cycle}_{metric_code}'
                if col in self.df.columns:
                    scores = self.df[col].dropna()
                    if len(scores) > 0:
                        metrics_analysis[metric_name][f'cycle_{cycle}'] = {
                            'mean': scores.mean(),
                            'std': scores.std(),
                            'n': len(scores)
                        }
        
        return metrics_analysis
    
    def analyze_insights_by_cycle(self):
        """Analyze insight scores for each cycle using defined insight categories"""
        insight_analysis = {}
        
        for cycle in [1, 2, 3]:
            insight_analysis[f'cycle_{cycle}'] = {}
            
            for insight_key, insight_def in self.insight_definitions.items():
                question_scores = []
                question_details = []
                
                for q_id in insight_def['questions']:
                    # Find the column for this question in this cycle
                    col = f'c{cycle}_{q_id.replace("A", "a").replace("V", "v").replace("E", "e").replace("S", "s").replace("P", "p")}'
                    
                    if col in self.df.columns:
                        scores = self.df[col].dropna()
                        if len(scores) > 0:
                            question_scores.append(scores.mean())
                            question_details.append({
                                'question_id': q_id,
                                'mean': scores.mean(),
                                'std': scores.std(),
                                'variance': scores.var(),
                                'n': len(scores)
                            })
                
                if question_scores:
                    insight_analysis[f'cycle_{cycle}'][insight_key] = {
                        'title': insight_def['title'],
                        'icon': insight_def['icon'],
                        'description': insight_def['description'],
                        'mean_score': np.mean(question_scores),
                        'question_details': question_details,
                        'n_questions': len(question_scores)
                    }
        
        return insight_analysis
    
    def generate_html_report(self, analysis_results, output_file='coffs_report.html'):
        """Generate a comprehensive HTML report with interactive charts"""
        
        report_date = datetime.now().strftime("%B %d, %Y")
        school_name = "Coffs Harbour Senior College"
        
        # Create cycle progression chart
        cycle_prog_chart = self.create_cycle_progression_chart(analysis_results)
        
        # Create distribution charts
        dist_charts = {}
        for dim in self.vespa_categories + ['Overall']:
            dist_charts[dim] = self.create_distribution_chart(dim, analysis_results['progression_analysis']['cycle_means'])
        
        # Start HTML
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{school_name} - VESPA 3 Cycle Analysis Report</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        {self._get_css_styles()}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="report-header">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px;">
                <img src="https://tse1.mm.bing.net/th/id/OIP.nkwhBIhBwNKWVejzrRlb1wHaBr?cb=ucfimg2ucfimg=1&rs=1&pid=ImgDetMain&o=7&rm=3" 
                     alt="Coffs Harbour Logo" 
                     style="height: 80px; object-fit: contain;">
                <img src="https://vespa.academy/_astro/vespalogo.BGrK1ARl.png" 
                     alt="VESPA Logo" 
                     style="height: 70px; object-fit: contain;">
            </div>
            <h1 style="color: #2c3e50; margin-bottom: 10px;">{school_name}</h1>
            <h2 style="color: #667eea;">VESPA 3 Cycle Analysis Report</h2>
            <p class="report-date">Generated: {report_date}</p>
            
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
"""
        
        # Executive Summary
        html_content += self._generate_executive_summary(analysis_results)
        
        # Strategic Recommendations
        html_content += self._generate_strategic_section(analysis_results)
        
        # Section 1: VESPA Results
        html_content += """
        <div style="background: #f0f4f8; padding: 30px 0; margin-top: 30px;">
            <h1 style="text-align: center; color: #2c3e50; border-bottom: 3px solid #667eea; padding-bottom: 10px; margin: 0 auto 30px; max-width: 400px;">
                SECTION 1: VESPA RESULTS
            </h1>
        </div>
"""
        
        # Cycle Progression Section with charts
        html_content += self._generate_cycle_progression_section(analysis_results, cycle_prog_chart)
        
        # Distribution Analysis
        html_content += self._generate_distribution_section(dist_charts)
        
        # Section 2: Statement Analysis
        html_content += """
        <div style="background: #f0f4f8; padding: 30px 0; margin-top: 30px;">
            <h1 style="text-align: center; color: #2c3e50; border-bottom: 3px solid #667eea; padding-bottom: 10px; margin: 0 auto 30px; max-width: 500px;">
                SECTION 2: STATEMENT LEVEL ANALYSIS
            </h1>
        </div>
"""
        
        # Statement Level Analysis
        html_content += self._generate_statement_analysis_section(analysis_results)
        
        # Insight Analysis - separate section for each cycle
        if 'insight_analysis' in analysis_results:
            html_content += """
        <div style="background: #f0f4f8; padding: 30px 0; margin-top: 30px;">
            <h1 style="text-align: center; color: #2c3e50; border-bottom: 3px solid #667eea; padding-bottom: 10px; margin: 0 auto 30px; max-width: 600px;">
                SECTION 3: INSIGHT CATEGORY ANALYSIS
            </h1>
        </div>
"""
            html_content += self._generate_insights_section(analysis_results)
        
        # Year Group Analysis (if available)
        if 'year_group_analysis' in analysis_results and analysis_results['year_group_analysis']:
            html_content += self._generate_year_group_section(analysis_results)
        
        # Gender Analysis (if available)
        if 'gender_analysis' in analysis_results and analysis_results['gender_analysis']:
            html_content += self._generate_gender_section(analysis_results)
        
        # Additional Metrics
        if 'metrics_analysis' in analysis_results and analysis_results['metrics_analysis']:
            html_content += self._generate_metrics_section(analysis_results)
        
        # Footer
        html_content += """
        <div class="footer">
            <p>© 2024 VESPA Education Analytics | Confidential Report</p>
        </div>
    </div>
</body>
</html>
"""
        
        # Write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"Report generated: {output_file}")
    
    def _get_css_styles(self):
        """Return CSS styles for the report"""
        return """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .report-header {
            background: white;
            border-radius: 15px;
            padding: 40px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }
        
        .report-header h1 {
            color: #2c3e50;
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .report-header h2 {
            color: #667eea;
            font-size: 1.8em;
        }
        
        .report-date {
            color: #666;
            font-size: 1.1em;
        }
        
        .executive-summary {
            background: white;
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }
        
        .executive-summary h2 {
            color: #667eea;
            margin-bottom: 20px;
            font-size: 1.8em;
        }
        
        .key-insights {
            background: #f8f9fa;
            border-left: 4px solid #667eea;
            padding: 20px;
            margin: 20px 0;
            border-radius: 5px;
        }
        
        .section {
            background: white;
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }
        
        .section h2 {
            color: #667eea;
            margin-bottom: 20px;
            font-size: 1.8em;
        }
        
        .section h3 {
            color: #764ba2;
            margin: 20px 0 10px 0;
            font-size: 1.4em;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 10px;
            margin: 20px 0;
        }
        
        @media (max-width: 1200px) {
            .stats-grid {
                grid-template-columns: repeat(3, 1fr);
            }
        }
        
        @media (max-width: 768px) {
            .stats-grid {
                grid-template-columns: repeat(2, 1fr);
            }
        }
        
        .stat-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px 8px;
            border-radius: 8px;
            text-align: center;
        }
        
        .stat-card h4 {
            font-size: 0.8em;
            opacity: 0.95;
            margin-bottom: 4px;
            font-weight: 600;
        }
        
        .stat-card .value {
            font-size: 1.5em;
            font-weight: bold;
            margin: 4px 0;
        }
        
        .stat-card .change {
            font-size: 0.75em;
            margin-top: 2px;
            opacity: 0.9;
        }
        
        .stat-card small {
            font-size: 0.7em;
            opacity: 0.8;
            display: block;
            margin-top: 4px;
        }
        
        .chart-container {
            margin: 30px 0;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 10px;
        }
        
        .responsive-chart {
            width: 100%;
            height: auto;
            max-width: 100%;
            overflow: hidden;
            page-break-inside: avoid;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        
        th {
            background: #667eea;
            color: white;
            padding: 12px;
            text-align: left;
        }
        
        td {
            padding: 12px;
            border-bottom: 1px solid #e0e0e0;
        }
        
        tr:hover {
            background: #f8f9fa;
        }
        
        .positive {
            color: #28a745;
            font-weight: bold;
        }
        
        .negative {
            color: #dc3545;
            font-weight: bold;
        }
        
        .neutral {
            color: #6c757d;
            font-weight: bold;
        }
        
        .footer {
            text-align: center;
            padding: 30px;
            color: white;
            opacity: 0.9;
        }
        
        .grid-container {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }
        
        .card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        @media print {
            body {
                background: white;
            }
            .container {
                max-width: 100%;
                padding: 15px;
            }
            .report-header button {
                display: none !important;
            }
            .chart-container {
                page-break-inside: avoid;
            }
        }
        """
    
    def _generate_executive_summary(self, analysis_results):
        """Generate executive summary section"""
        progression = analysis_results['progression_analysis']
        cycle_means = progression.get('cycle_means', {})
        cycle_comparison = progression.get('cycle_comparison', {})
        statements = analysis_results['statement_analysis']
        
        # Get overall statistics
        total_students = len(self.df)
        c1_students = cycle_means.get('cycle_1', {}).get('Overall', {}).get('n', 0)
        c2_students = cycle_means.get('cycle_2', {}).get('Overall', {}).get('n', 0)
        c3_students = cycle_means.get('cycle_3', {}).get('Overall', {}).get('n', 0)
        
        html = f"""
        <div class="executive-summary">
            <h2>Executive Summary</h2>
            <p>This comprehensive VESPA analysis for Coffs Harbour Senior College examines student mindset and study skills development 
            across {total_students} students through three assessment cycles during the 2024/25 academic year.</p>
            
            <div class="key-insights" style="margin-top: 25px;">
                <h3 style="color: #667eea; margin-bottom: 20px;">Key Findings & Takeaways</h3>
                
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-top: 20px;">
"""
        
        # Calculate key insights
        overall_c1_to_c3 = cycle_comparison.get('Overall_C1_to_C3_overall', {})
        if overall_c1_to_c3:
            improvement = overall_c1_to_c3.get('overall_improvement', 0)
            percent_improved = overall_c1_to_c3.get('percent_improved_overall', 0)
            n_completed = overall_c1_to_c3.get('n_students', 0)
            
            html += f"""
                    <div style="background: rgba(102, 126, 234, 0.08); padding: 20px; border-radius: 8px; border-left: 4px solid #667eea;">
                        <h4 style="color: #2c3e50; margin-bottom: 10px;">Overall Progress</h4>
                        <p>{n_completed} students completed all 3 cycles, showing an average improvement of {improvement:+.2f} points. 
                        {percent_improved:.1f}% of students improved their overall VESPA score from Cycle 1 to Cycle 3.</p>
                    </div>
"""
        
        # Find strongest improvement area
        best_improvement = None
        best_value = -999
        for cat in self.vespa_categories:
            key = f'{cat}_C1_to_C3_overall'
            if key in cycle_comparison:
                imp = cycle_comparison[key].get('overall_improvement', 0)
                if imp > best_value:
                    best_value = imp
                    best_improvement = cat
        
        if best_improvement:
            html += f"""
                    <div style="background: rgba(114, 203, 68, 0.08); padding: 20px; border-radius: 8px; border-left: 4px solid #72cb44;">
                        <h4 style="color: #2c3e50; margin-bottom: 10px;">Strongest Growth Area</h4>
                        <p>{best_improvement} showed the most significant improvement across the three cycles ({best_value:+.2f} points), 
                        indicating effective development in this key area.</p>
                    </div>
"""
        
        # Top statement
        if statements.get('top_statements'):
            top_stmt = statements['top_statements'][0]
            html += f"""
                    <div style="background: rgba(229, 148, 55, 0.08); padding: 20px; border-radius: 8px; border-left: 4px solid #e59437;">
                        <h4 style="color: #2c3e50; margin-bottom: 10px;">Strongest Belief</h4>
                        <p>Students demonstrate strong agreement with "{top_stmt['text']}" (Score: {top_stmt['mean_score']:.2f}), 
                        showing solid foundation in {top_stmt['category']}.</p>
                    </div>
"""
        
        # Bottom statement
        if statements.get('bottom_statements'):
            bottom_stmt = statements['bottom_statements'][0]
            html += f"""
                    <div style="background: rgba(240, 50, 230, 0.08); padding: 20px; border-radius: 8px; border-left: 4px solid #f032e6;">
                        <h4 style="color: #2c3e50; margin-bottom: 10px;">Development Area</h4>
                        <p>Students need support with "{bottom_stmt['text']}" (Score: {bottom_stmt['mean_score']:.2f}), 
                        representing a priority area for targeted intervention.</p>
                    </div>
"""
        
        html += """
                </div>
            </div>
        </div>
"""
        
        return html
    
    def _generate_strategic_section(self, analysis_results):
        """Generate strategic recommendations section"""
        progression = analysis_results['progression_analysis']
        statements = analysis_results['statement_analysis']
        cycle_comparison = progression.get('cycle_comparison', {})
        
        html = """
        <div class="section" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 35px; border-radius: 12px;">
            <h2 style="color: white; font-size: 2em; border-bottom: 2px solid rgba(255,255,255,0.3); padding-bottom: 15px; margin-bottom: 25px;">Cycle Analysis</h2>
            
            <div style="margin-top: 20px;">
                <ul style="list-style: none; padding: 0;">
"""
        
        # Generate insights based on data
        insights = []
        
        # Overall progression insight
        overall_prog = cycle_comparison.get('Overall_C1_to_C3_overall', {})
        if overall_prog:
            mean_c1 = overall_prog.get('mean_c1', 0)
            mean_c2 = overall_prog.get('mean_c2', 0)
            mean_c3 = overall_prog.get('mean_c3', 0)
            insights.append(f"Analysis across three cycles shows overall progression from {mean_c1:.1f} (Cycle 1) through {mean_c2:.1f} (Cycle 2) to {mean_c3:.1f} (Cycle 3), demonstrating the effectiveness of the VESPA intervention program.")
        
        # C2 to C3 improvements
        c2_to_c3_improvements = []
        for cat in self.vespa_categories:
            key = f'{cat}_C2_to_C3'
            if key in cycle_comparison:
                imp = cycle_comparison[key].get('mean_improvement', 0)
                if imp > 0.1:
                    c2_to_c3_improvements.append((cat, imp))
        
        if c2_to_c3_improvements:
            c2_to_c3_improvements.sort(key=lambda x: x[1], reverse=True)
            top_cats = ', '.join([f"{cat} ({imp:+.2f})" for cat, imp in c2_to_c3_improvements[:2]])
            insights.append(f"Cycle 2 to Cycle 3 progression shows particularly strong improvements in {top_cats}, indicating students are developing enhanced mindsets and study approaches.")
        
        # Statement insights
        if statements.get('most_improved'):
            insights.append(f"Statement-level analysis reveals students show greatest improvement in areas like \"{statements['most_improved'][0]['text']}\", demonstrating targeted growth in specific competencies.")
        
        if statements.get('bottom_statements'):
            insights.append(f"Students score lowest on systematic study approach statements, particularly \"{statements['bottom_statements'][0]['text']}\", identifying specific areas for targeted intervention.")
        
        # Add insights to HTML
        for insight in insights:
            html += f"""
                    <li style="margin: 15px 0; padding-left: 25px; border-left: 3px solid rgba(255,255,255,0.5); color: white; font-size: 1.05em; line-height: 1.6;">{insight}</li>
"""
        
        html += """
                </ul>
            </div>
            
            <div style="margin-top: 40px;">
                <h3 style="color: white; font-size: 1.4em; margin-bottom: 25px;">Strategic Recommendations</h3>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px;">
"""
        
        # Generate recommendations
        recommendations = []
        
        # Check for areas with minimal growth
        for cat in self.vespa_categories:
            key = f'{cat}_C1_to_C3_overall'
            if key in cycle_comparison:
                imp = cycle_comparison[key].get('overall_improvement', 0)
                if imp < 0.2:
                    recommendations.append({
                        'priority': 'High Priority',
                        'title': f'Support {cat} Development',
                        'description': f'Focus on building {cat.lower()} skills, as this area shows minimal overall progression ({imp:+.2f} points) across cycles.',
                        'color': '#ff6b6b'
                    })
        
        # Celebrate successes
        if c2_to_c3_improvements:
            top_cat, top_imp = c2_to_c3_improvements[0]
            recommendations.append({
                'priority': 'Medium Priority',
                'title': f'Leverage {top_cat} Success',
                'description': f'Build on the strong {top_cat} improvement ({top_imp:+.2f}) as a model for other dimensions.',
                'color': '#feca57'
            })
        
        # Statement-based recommendations
        if statements.get('bottom_statements'):
            bottom = statements['bottom_statements'][0]
            recommendations.append({
                'priority': 'High Priority',
                'title': 'Address Core Study Skills',
                'description': f'Implement targeted interventions for "{bottom['text']}" which shows the lowest performance.',
                'color': '#ff6b6b'
            })
        
        # Add recommendations to HTML
        for rec in recommendations[:4]:  # Show top 4 recommendations
            html += f"""
                    <div style="background: rgba(255,255,255,0.1); padding: 20px; border-radius: 10px; border-left: 4px solid {rec['color']};">
                        <span style="background: {rec['color']}; color: white; padding: 4px 12px; border-radius: 15px; font-size: 0.85em; font-weight: 600;">{rec['priority']}</span>
                        <h4 style="margin: 12px 0 8px 0; color: white; font-size: 1.1em;">{rec['title']}</h4>
                        <p style="color: rgba(255,255,255,0.9); line-height: 1.5;">{rec['description']}</p>
                    </div>
"""
        
        html += """
                </div>
            </div>
        </div>
"""
        
        return html
    
    def _generate_cycle_progression_section(self, analysis_results, cycle_chart):
        """Generate detailed cycle progression analysis with charts"""
        progression = analysis_results['progression_analysis']
        cycle_comparison = progression.get('cycle_comparison', {})
        
        html = """
        <div class="section" style="padding: 25px 15px;">
            <h2>Cycle Progression Analysis</h2>
            <p style="margin-bottom: 20px;">
                Analysis of VESPA scores across three assessment cycles shows distinct patterns in each dimension.
                The following data represents mean scores and progression metrics for students who participated in each cycle.
            </p>
            
            <h3>Cycle 1 to Cycle 2 Changes</h3>
            <div class="stats-grid">
"""
        
        # C1 to C2 changes
        for cat in self.vespa_categories:
            key = f'{cat}_C1_to_C2'
            if key in cycle_comparison:
                data = cycle_comparison[key]
                improvement = data['mean_improvement']
                percent = data['percent_improved']
                
                html += f"""
                <div class="stat-card">
                    <h4>{cat}</h4>
                    <div class="value">{improvement:+.2f}</div>
                    <div class="change">{percent:.0f}% improved</div>
                </div>
"""
        
        html += """
            </div>
            
            <h3>Cycle 2 to Cycle 3 Changes</h3>
            <div class="stats-grid">
"""
        
        # C2 to C3 changes
        for cat in self.vespa_categories:
            key = f'{cat}_C2_to_C3'
            if key in cycle_comparison:
                data = cycle_comparison[key]
                improvement = data['mean_improvement']
                percent = data['percent_improved']
                n_students = data['n_students']
                
                bg_gradient = 'linear-gradient(135deg, #28a745 0%, #20c997 100%)' if improvement > 0 else 'linear-gradient(135deg, #ffc107 0%, #ff9800 100%)'
                
                html += f"""
                <div class="stat-card" style="background: {bg_gradient};">
                    <h4>{cat}</h4>
                    <div class="value">{improvement:+.2f}</div>
                    <div class="change">{percent:.0f}% improved</div>
                    <small style="opacity: 0.8;">n={n_students}</small>
                </div>
"""
        
        html += """
            </div>
            
            <h3>Overall Journey: Start to Finish</h3>
            <div class="stats-grid">
"""
        
        # Overall C1 to C3
        for cat in self.vespa_categories:
            key = f'{cat}_C1_to_C3_overall'
            if key in cycle_comparison:
                data = cycle_comparison[key]
                improvement = data['overall_improvement']
                c1 = data['mean_c1']
                c2 = data['mean_c2']
                c3 = data['mean_c3']
                n_students = data['n_students']
                
                bg_gradient = 'linear-gradient(135deg, #28a745 0%, #20c997 100%)' if improvement > 0.1 else 'linear-gradient(135deg, #ffc107 0%, #ff9800 100%)'
                
                html += f"""
                <div class="stat-card" style="background: {bg_gradient};">
                    <h4>{cat} Overall</h4>
                    <div class="value">{improvement:+.2f}</div>
                    <div class="change">C1: {c1:.1f} → C2: {c2:.1f} → C3: {c3:.1f}</div>
                    <small style="opacity: 0.8;">n={n_students} completed all</small>
                </div>
"""
        
        html += f"""
            </div>

            <div class="chart-container responsive-chart">
                {cycle_chart}
            </div>

        </div>
"""
        
        return html
    
    def _generate_distribution_section(self, dist_charts):
        """Generate score distribution section with charts and educational commentary"""
        html = """
        <div class="section">
            <h2>Score Distribution Analysis</h2>
            
            <div class="key-insights" style="margin-bottom: 30px;">
                <h4 style="color: #2c3e50; margin-bottom: 15px;">📊 Understanding Distribution Charts</h4>
                <p style="margin-bottom: 10px;"><strong>What These Charts Show:</strong></p>
                <ul style="margin: 10px 0; padding-left: 25px; line-height: 1.8;">
                    <li><strong>Blue Bars:</strong> Coffs Harbour's distribution - shows what percentage of students scored at each level (1-10)</li>
                    <li><strong>Red Line:</strong> National distribution - how Coffs compares to schools across the country</li>
                    <li><strong>Three Panels:</strong> Each panel represents one assessment cycle, showing progression over time</li>
                </ul>
                
                <p style="margin-top: 15px;"><strong>Why Distribution Matters:</strong></p>
                <ul style="margin: 10px 0; padding-left: 25px; line-height: 1.8;">
                    <li><strong>Shape Analysis:</strong> A bell curve (peak in middle) indicates consistent performance; peaks at high scores show excellence; peaks at low scores indicate needs</li>
                    <li><strong>Spread Analysis:</strong> Wide distribution (flat) shows diverse student needs; narrow distribution (peaked) shows uniform performance</li>
                    <li><strong>Comparison:</strong> When your bars are higher than the red line at high scores (7-10), you're outperforming nationally</li>
                    <li><strong>Trend Spotting:</strong> Watch how the distribution shifts across cycles - movement toward higher scores indicates improvement</li>
                </ul>
                
                <div style="margin-top: 15px; padding: 15px; background: rgba(102, 126, 234, 0.1); border-radius: 5px;">
                    <p style="margin: 0; color: #2c3e50;"><strong>💡 Key Insight:</strong> Distribution charts reveal more than average scores alone - they show whether improvements benefit all students (shift right) or just some (increased spread).</p>
                </div>
            </div>
            
            <p style="margin-bottom: 20px;"><strong>Score distributions for each VESPA dimension across all three cycles:</strong></p>
"""
        
        for dim in self.vespa_categories + ['Overall']:
            html += f"""
            <div class="chart-container responsive-chart" style="margin: 20px 0;">
                {dist_charts[dim]}
            </div>
"""
        
        html += """
        </div>
"""
        
        return html
    
    def _generate_statement_analysis_section(self, analysis_results):
        """Generate statement-level analysis section"""
        s_data = analysis_results['statement_analysis']
        
        html = """
        <div class="section">
            <h2>VESPA Statement Analysis</h2>
            <p style="margin-bottom: 20px;">Detailed analysis of individual VESPA statement responses reveals specific strengths and development areas. 
            Each statement is analyzed across all three cycles to identify overall progression patterns from baseline to final assessment.</p>
"""
        
        # Add variance explanation
        html += """
            <div class="key-insights" style="margin-bottom: 30px;">
                <h4 style="color: #2c3e50; margin-bottom: 15px;">📈 Understanding Statement Scores & Variance</h4>
                <p style="margin-bottom: 10px;"><strong>What the Scores Mean:</strong></p>
                <ul style="margin: 10px 0; padding-left: 25px; line-height: 1.8;">
                    <li><strong>Scores 4.0-5.0:</strong> Strong agreement - students consistently demonstrate this belief/behavior</li>
                    <li><strong>Scores 3.0-3.9:</strong> Moderate agreement - room for improvement but a solid foundation</li>
                    <li><strong>Scores 2.0-2.9:</strong> Low agreement - priority area for intervention and support</li>
                    <li><strong>Scores below 2.0:</strong> Very low agreement - urgent attention needed</li>
                </ul>
                
                <p style="margin-top: 15px;"><strong>Understanding Variance (σ²) & Standard Deviation (σ):</strong></p>
                <ul style="margin: 10px 0; padding-left: 25px; line-height: 1.8;">
                    <li><strong>Low Variance (σ² < 0.5):</strong> Students have <em>consistent views</em> - the score represents a genuine cohort-wide belief</li>
                    <li><strong>Moderate Variance (σ² 0.5-1.0):</strong> Some diversity in views - typical variation within a group</li>
                    <li><strong>High Variance (σ² > 1.0):</strong> Students have <em>divergent views</em> - indicates the score may hide significant subgroup differences</li>
                </ul>
                
                <div style="margin-top: 15px; padding: 15px; background: rgba(102, 126, 234, 0.1); border-radius: 5px;">
                    <p style="margin: 0; color: #2c3e50;"><strong>💡 Why This Matters:</strong> A score of 3.5 with low variance (0.3) means most students agree at that level - actionable. The same 3.5 with high variance (1.5) means some students score 1-2 while others score 4-5 - requires differentiated interventions.</p>
                </div>
            </div>
"""
        
        # Most improved statements WITH VARIANCE
        if s_data.get('most_improved'):
            html += """
            <h3>Statements Showing Greatest Improvement (Cycle 2 to Cycle 3)</h3>
            <table>
                <thead>
                    <tr>
                        <th>Statement</th>
                        <th>Category</th>
                        <th>Cycle 2</th>
                        <th>Cycle 3</th>
                        <th>Change</th>
                        <th>Variance (σ²)</th>
                        <th>Agreement Level</th>
                    </tr>
                </thead>
                <tbody>
"""
            
            for s in s_data['most_improved']:
                variance = s.get('avg_variance', 0)
                variance_level = 'Low (Consistent)' if variance < 0.5 else 'Moderate' if variance < 1.0 else 'High (Diverse)'
                variance_color = '#28a745' if variance < 0.5 else '#ffc107' if variance < 1.0 else '#dc3545'
                
                html += f"""
                    <tr>
                        <td style="padding: 10px;">{s['text']}</td>
                        <td style="padding: 10px; text-align: center;">{s['category']}</td>
                        <td style="padding: 10px; text-align: center;">{s['cycle_2_mean']:.2f} (σ={s.get('cycle_2_std', 0):.2f})</td>
                        <td style="padding: 10px; text-align: center;">{s['cycle_3_mean']:.2f} (σ={s.get('cycle_3_std', 0):.2f})</td>
                        <td style="padding: 10px; text-align: center;" class="positive">+{s['improvement']:.2f}</td>
                        <td style="padding: 10px; text-align: center;">{variance:.2f}</td>
                        <td style="padding: 10px; text-align: center; color: {variance_color}; font-weight: 600;">{variance_level}</td>
                    </tr>
"""
            
            html += """
                </tbody>
            </table>
"""
        
        # Declined statements WITH VARIANCE
        if s_data.get('most_declined'):
            html += """
            <h3>Statements Showing Decline (Cycle 2 to Cycle 3)</h3>
            <table>
                <thead>
                    <tr>
                        <th>Statement</th>
                        <th>Category</th>
                        <th>Cycle 2</th>
                        <th>Cycle 3</th>
                        <th>Change</th>
                        <th>Variance (σ²)</th>
                        <th>Agreement Level</th>
                    </tr>
                </thead>
                <tbody>
"""
            
            for s in s_data['most_declined']:
                variance = s.get('avg_variance', 0)
                variance_level = 'Low (Consistent)' if variance < 0.5 else 'Moderate' if variance < 1.0 else 'High (Diverse)'
                variance_color = '#28a745' if variance < 0.5 else '#ffc107' if variance < 1.0 else '#dc3545'
                
                html += f"""
                    <tr>
                        <td style="padding: 10px;">{s['text']}</td>
                        <td style="padding: 10px; text-align: center;">{s['category']}</td>
                        <td style="padding: 10px; text-align: center;">{s['cycle_2_mean']:.2f} (σ={s.get('cycle_2_std', 0):.2f})</td>
                        <td style="padding: 10px; text-align: center;">{s['cycle_3_mean']:.2f} (σ={s.get('cycle_3_std', 0):.2f})</td>
                        <td style="padding: 10px; text-align: center;" class="negative">{s['decline']:.2f}</td>
                        <td style="padding: 10px; text-align: center;">{variance:.2f}</td>
                        <td style="padding: 10px; text-align: center; color: {variance_color}; font-weight: 600;">{variance_level}</td>
                    </tr>
"""
            
            html += """
                </tbody>
            </table>
"""
        
        # Top statements WITH VARIANCE
        html += """
            <h3>Strongest Beliefs (Top Performing Overall)</h3>
            <table>
                <thead>
                    <tr>
                        <th>Statement</th>
                        <th>Category</th>
                        <th>Average Score</th>
                        <th>Std Dev (σ)</th>
                        <th>Variance (σ²)</th>
                        <th>Confidence</th>
                    </tr>
                </thead>
                <tbody>
"""
        
        for s in s_data.get('top_statements', []):
            std_dev = s.get('std_dev', 0)
            variance = s.get('variance', 0)
            
            # Interpret variance for confidence level
            if variance < 0.5:
                confidence = 'High - Consistent belief across cohort'
                conf_color = '#28a745'
            elif variance < 1.0:
                confidence = 'Moderate - Some variation expected'
                conf_color = '#ffc107'
            else:
                confidence = 'Low - Divergent views, subgroup differences'
                conf_color = '#dc3545'
            
            html += f"""
                    <tr>
                        <td style="padding: 10px;">{s['text']}</td>
                        <td style="padding: 10px; text-align: center;">{s['category']}</td>
                        <td style="padding: 10px; text-align: center; font-weight: bold;" class="positive">{s['mean_score']:.2f}</td>
                        <td style="padding: 10px; text-align: center;">{std_dev:.2f}</td>
                        <td style="padding: 10px; text-align: center;">{variance:.2f}</td>
                        <td style="padding: 10px; text-align: center; color: {conf_color}; font-size: 0.9em;">{confidence}</td>
                    </tr>
"""
        
        html += """
                </tbody>
            </table>
            
            <h3>Areas for Development (Lowest Performing)</h3>
            <table>
                <thead>
                    <tr>
                        <th>Statement</th>
                        <th>Category</th>
                        <th>Average Score</th>
                        <th>Std Dev (σ)</th>
                        <th>Variance (σ²)</th>
                        <th>Confidence</th>
                    </tr>
                </thead>
                <tbody>
"""
        
        for s in s_data.get('bottom_statements', []):
            std_dev = s.get('std_dev', 0)
            variance = s.get('variance', 0)
            
            # Interpret variance for confidence level
            if variance < 0.5:
                confidence = 'High - Consistent belief across cohort'
                conf_color = '#28a745'
            elif variance < 1.0:
                confidence = 'Moderate - Some variation expected'
                conf_color = '#ffc107'
            else:
                confidence = 'Low - Divergent views, subgroup differences'
                conf_color = '#dc3545'
            
            html += f"""
                    <tr>
                        <td style="padding: 10px;">{s['text']}</td>
                        <td style="padding: 10px; text-align: center;">{s['category']}</td>
                        <td style="padding: 10px; text-align: center; font-weight: bold;" class="negative">{s['mean_score']:.2f}</td>
                        <td style="padding: 10px; text-align: center;">{std_dev:.2f}</td>
                        <td style="padding: 10px; text-align: center;">{variance:.2f}</td>
                        <td style="padding: 10px; text-align: center; color: {conf_color}; font-size: 0.9em;">{confidence}</td>
                    </tr>
"""
        
        html += """
                </tbody>
            </table>
"""
        
        # Agreement Analysis
        html += self._generate_statement_agreement_section(s_data)
        
        html += """
        </div>
"""
        
        return html
    
    def _generate_statement_agreement_section(self, s_data):
        """Generate statement agreement analysis"""
        html = """
        <div style="margin-top: 50px; padding: 30px; background: linear-gradient(to right, #f8f9fa, #ffffff); border-radius: 12px; border: 1px solid #e9ecef;">
            <h3 style="color: #2c3e50; margin-bottom: 25px; font-size: 1.6em;">Statement Agreement Analysis</h3>
            <p style="color: #666; margin-bottom: 30px;">Analysis of which statements students most and least agree with across all assessment cycles.</p>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 30px;">
                <div style="background: #fff; padding: 25px; border-radius: 10px; border: 2px solid #28a745;">
                    <h4 style="color: #28a745; margin-bottom: 20px; font-size: 1.2em;">Top 5 - Students Strongly Agree</h4>
                    <ol style="margin: 0; padding-left: 20px; line-height: 1.8;">
"""
        
        for s in s_data.get('top_statements', [])[:5]:
            html += f"""
                        <li style="margin-bottom: 12px; color: #333;">
                            <strong>{s['text']}</strong>
                            <br>
                            <span style="color: #666; font-size: 0.9em;">
                                Average Score: {s['mean_score']:.2f} | Category: {s['category']}
                            </span>
                        </li>
"""
        
        html += """
                    </ol>
                </div>
                
                <div style="background: #fff; padding: 25px; border-radius: 10px; border: 2px solid #dc3545;">
                    <h4 style="color: #dc3545; margin-bottom: 20px; font-size: 1.2em;">Bottom 5 - Students Least Agree</h4>
                    <ol style="margin: 0; padding-left: 20px; line-height: 1.8;">
"""
        
        for s in s_data.get('bottom_statements', [])[:5]:
            html += f"""
                        <li style="margin-bottom: 12px; color: #333;">
                            <strong>{s['text']}</strong>
                            <br>
                            <span style="color: #666; font-size: 0.9em;">
                                Average Score: {s['mean_score']:.2f} | Category: {s['category']}
                            </span>
                        </li>
"""
        
        html += """
                    </ol>
                </div>
            </div>
            
            <div style="margin-top: 30px; padding: 20px; background: #f8f9fa; border-radius: 8px;">
                <p style="margin: 0; font-size: 0.95em; color: #555;">
                    <strong>Interpretation Guide:</strong> Scores above 4.0 indicate strong agreement, scores between 3.0-4.0 show moderate agreement, 
                    and scores below 3.0 suggest areas where students lack confidence or need additional support.
                </p>
            </div>
        </div>
"""
        
        return html
    
    def _generate_insights_section(self, analysis_results):
        """Generate insight category analysis for each cycle"""
        insight_data = analysis_results.get('insight_analysis', {})
        
        html = """
        <div class="section">
            <h2>Insight Category Analysis Across Cycles</h2>
            
            <div class="key-insights" style="margin-bottom: 30px;">
                <h4 style="color: #2c3e50; margin-bottom: 15px;">🎯 Understanding Insight Categories</h4>
                <p style="margin-bottom: 10px;">VESPA insights group related statements to provide a comprehensive view of student mindsets and behaviors in key areas. Each insight is calculated from multiple related statements.</p>
                
                <p style="margin-top: 15px;"><strong>Why Insights Matter:</strong></p>
                <ul style="margin: 10px 0; padding-left: 25px; line-height: 1.8;">
                    <li><strong>Holistic View:</strong> Single statements can be affected by wording; insights combine multiple questions for reliability</li>
                    <li><strong>Actionable Targets:</strong> Each insight represents a specific area where interventions can be designed</li>
                    <li><strong>Progress Tracking:</strong> Monitoring insights across cycles shows whether interventions are working</li>
                    <li><strong>Resource Allocation:</strong> Low-scoring insights help prioritize where to focus support resources</li>
                </ul>
            </div>
"""
        
        # Generate a section for each cycle
        for cycle_num in [1, 2, 3]:
            cycle_key = f'cycle_{cycle_num}'
            if cycle_key in insight_data:
                html += f"""
            <h3 style="margin-top: 40px; color: #667eea;">Cycle {cycle_num} - Insight Breakdown</h3>
            <div style="margin-top: 20px;">
                <table>
                    <thead>
                        <tr>
                            <th>Insight Category</th>
                            <th>Score</th>
                            <th>Questions</th>
                            <th>Individual Q Scores & Variance</th>
                            <th>Interpretation</th>
                        </tr>
                    </thead>
                    <tbody>
"""
                
                # Sort insights by score for this cycle
                insights_sorted = sorted(
                    insight_data[cycle_key].items(),
                    key=lambda x: x[1]['mean_score'],
                    reverse=True
                )
                
                for insight_key, insight_info in insights_sorted:
                    score = insight_info['mean_score']
                    
                    # Determine interpretation
                    if score >= 4.0:
                        interpretation = 'Excellent - Strong foundation'
                        int_color = '#28a745'
                    elif score >= 3.0:
                        interpretation = 'Good - Solid but improvable'
                        int_color = '#3b82f6'
                    elif score >= 2.0:
                        interpretation = 'Average - Needs attention'
                        int_color = '#ffc107'
                    else:
                        interpretation = 'Priority - Urgent intervention needed'
                        int_color = '#dc3545'
                    
                    # Build question details string
                    q_details_html = '<div style="font-size: 0.85em;">'
                    for q in insight_info['question_details']:
                        variance = q['variance']
                        var_indicator = '✓' if variance < 0.5 else '~' if variance < 1.0 else '!'
                        var_color = '#28a745' if variance < 0.5 else '#ffc107' if variance < 1.0 else '#dc3545'
                        
                        q_details_html += f'<div style="margin: 3px 0;"><span style="color: {var_color}; font-weight: bold;">{var_indicator}</span> {q["question_id"]}: {q["mean"]:.2f} (σ²={variance:.2f})</div>'
                    q_details_html += '</div>'
                    
                    html += f"""
                    <tr>
                        <td style="padding: 12px;">
                            <div style="font-weight: 600; margin-bottom: 5px;">{insight_info['icon']} {insight_info['title']}</div>
                            <div style="font-size: 0.9em; color: #666; font-style: italic;">{insight_info['description']}</div>
                        </td>
                        <td style="padding: 12px; text-align: center; font-size: 1.3em; font-weight: bold;">{score:.2f}</td>
                        <td style="padding: 12px; text-align: center;">{insight_info['n_questions']} questions</td>
                        <td style="padding: 12px;">{q_details_html}</td>
                        <td style="padding: 12px; color: {int_color}; font-weight: 600; font-size: 0.9em;">{interpretation}</td>
                    </tr>
"""
                
                html += """
                    </tbody>
                </table>
            </div>
"""
        
        # Add summary comparison across cycles
        html += """
            <h3 style="margin-top: 50px; color: #667eea;">Insight Progression Summary</h3>
            <p style="margin-bottom: 20px;">How each insight category has changed across the three cycles:</p>
            <table>
                <thead>
                    <tr>
                        <th>Insight Category</th>
                        <th>Cycle 1</th>
                        <th>Cycle 2</th>
                        <th>Cycle 3</th>
                        <th>Overall Change</th>
                    </tr>
                </thead>
                <tbody>
"""
        
        # Collect all insight keys
        all_insights = set()
        for cycle_key in insight_data.keys():
            all_insights.update(insight_data[cycle_key].keys())
        
        for insight_key in sorted(all_insights):
            # Get scores for each cycle
            c1_score = insight_data.get('cycle_1', {}).get(insight_key, {}).get('mean_score', 0)
            c2_score = insight_data.get('cycle_2', {}).get(insight_key, {}).get('mean_score', 0)
            c3_score = insight_data.get('cycle_3', {}).get(insight_key, {}).get('mean_score', 0)
            
            if c1_score > 0 and c3_score > 0:
                change = c3_score - c1_score
                change_class = 'positive' if change > 0.1 else 'negative' if change < -0.1 else 'neutral'
                
                # Get title
                title = self.insight_definitions[insight_key]['title']
                icon = self.insight_definitions[insight_key]['icon']
                
                c1_str = f"{c1_score:.2f}" if c1_score > 0 else '-'
                c2_str = f"{c2_score:.2f}" if c2_score > 0 else '-'
                c3_str = f"{c3_score:.2f}" if c3_score > 0 else '-'
                
                html += f"""
                    <tr>
                        <td style="padding: 12px; font-weight: 600;">{icon} {title}</td>
                        <td style="padding: 12px; text-align: center;">{c1_str}</td>
                        <td style="padding: 12px; text-align: center;">{c2_str}</td>
                        <td style="padding: 12px; text-align: center;">{c3_str}</td>
                        <td style="padding: 12px; text-align: center;" class="{change_class}">{change:+.2f}</td>
                    </tr>
"""
        
        html += """
                </tbody>
            </table>
            
            <div style="margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 8px;">
                <p style="margin: 0; font-size: 0.95em; color: #555;">
                    <strong>Legend:</strong> 
                    ✓ = Low variance (consistent agreement), 
                    ~ = Moderate variance (typical variation), 
                    ! = High variance (divergent views - investigate subgroups)
                </p>
            </div>
        </div>
"""
        
        return html
    
    def _generate_year_group_section(self, analysis_results):
        """Generate year group analysis section"""
        year_data = analysis_results['year_group_analysis']
        
        html = """
        <div class="section">
            <h2>Year Group Analysis</h2>
            <p>Performance breakdown by year group across the three cycles.</p>
            
            <table>
                <thead>
                    <tr>
                        <th>Year Group</th>
                        <th>Students</th>
                        <th>Cycle 1 Overall</th>
                        <th>Cycle 2 Overall</th>
                        <th>Cycle 3 Overall</th>
                    </tr>
                </thead>
                <tbody>
"""
        
        for year_group, data in sorted(year_data.items()):
            c1_overall = data['cycles'].get('cycle_1', {}).get('Overall', {}).get('mean', 0)
            c2_overall = data['cycles'].get('cycle_2', {}).get('Overall', {}).get('mean', 0)
            c3_overall = data['cycles'].get('cycle_3', {}).get('Overall', {}).get('mean', 0)
            
            c1_str = f"{c1_overall:.2f}" if c1_overall > 0 else '-'
            c2_str = f"{c2_overall:.2f}" if c2_overall > 0 else '-'
            c3_str = f"{c3_overall:.2f}" if c3_overall > 0 else '-'
            
            html += f"""
                    <tr>
                        <td style="font-weight: 600;">Year {year_group}</td>
                        <td>{data['n_students']}</td>
                        <td>{c1_str}</td>
                        <td>{c2_str}</td>
                        <td>{c3_str}</td>
                    </tr>
"""
        
        html += """
                </tbody>
            </table>
        </div>
"""
        
        return html
    
    def _generate_gender_section(self, analysis_results):
        """Generate gender analysis section"""
        gender_data = analysis_results['gender_analysis']
        
        html = """
        <div class="section">
            <h2>Gender Analysis</h2>
            <p>Performance comparison by gender across the three cycles.</p>
            
            <table>
                <thead>
                    <tr>
                        <th>Gender</th>
                        <th>Students</th>
                        <th>Cycle 1 Overall</th>
                        <th>Cycle 2 Overall</th>
                        <th>Cycle 3 Overall</th>
                    </tr>
                </thead>
                <tbody>
"""
        
        for gender, data in sorted(gender_data.items()):
            c1_overall = data['cycles'].get('cycle_1', {}).get('Overall', {}).get('mean', 0)
            c2_overall = data['cycles'].get('cycle_2', {}).get('Overall', {}).get('mean', 0)
            c3_overall = data['cycles'].get('cycle_3', {}).get('Overall', {}).get('mean', 0)
            
            c1_str = f"{c1_overall:.2f}" if c1_overall > 0 else '-'
            c2_str = f"{c2_overall:.2f}" if c2_overall > 0 else '-'
            c3_str = f"{c3_overall:.2f}" if c3_overall > 0 else '-'
            
            html += f"""
                    <tr>
                        <td style="font-weight: 600;">{gender}</td>
                        <td>{data['n_students']}</td>
                        <td>{c1_str}</td>
                        <td>{c2_str}</td>
                        <td>{c3_str}</td>
                    </tr>
"""
        
        html += """
                </tbody>
            </table>
        </div>
"""
        
        return html
    
    def _generate_metrics_section(self, analysis_results):
        """Generate additional metrics section"""
        metrics_data = analysis_results['metrics_analysis']
        
        html = """
        <div class="section">
            <h2>Student Support, Preparedness & Confidence</h2>
            <p>Analysis of three key metrics tracked across the assessment cycles.</p>
            
            <div class="grid-container">
"""
        
        for metric_name, cycles in metrics_data.items():
            html += f"""
                <div class="card">
                    <h3 style="color: #667eea; margin-bottom: 15px;">{metric_name}</h3>
"""
            
            for cycle_num in [1, 2, 3]:
                cycle_key = f'cycle_{cycle_num}'
                if cycle_key in cycles:
                    cycle_data = cycles[cycle_key]
                    html += f"""
                    <div style="padding: 10px; margin: 5px 0; background: #f8f9fa; border-radius: 5px;">
                        <div style="font-size: 0.9em; color: #666;">Cycle {cycle_num}</div>
                        <div style="font-size: 1.5em; font-weight: bold; color: #2c3e50;">{cycle_data['mean']:.2f}</div>
                        <div style="font-size: 0.8em; color: #999;">n = {cycle_data['n']}</div>
                    </div>
"""
            
            html += """
                </div>
"""
        
        html += """
            </div>
        </div>
"""
        
        return html


def main():
    """Main execution function"""
    print("=" * 60)
    print("Coffs Harbour Senior College - 3 Cycle VESPA Analysis")
    print("=" * 60)
    
    # Initialize analyzer
    analyzer = CoffsAnalyzer()
    
    # Load data
    csv_path = 'DASHBOARD-Vue/COFFSQQS2425.csv'
    analyzer.load_data(csv_path)
    
    # Run all analyses
    print("\nRunning analyses...")
    
    analysis_results = {
        'progression_analysis': analyzer.analyze_cycle_progression(),
        'year_group_analysis': analyzer.analyze_year_groups(),
        'gender_analysis': analyzer.analyze_gender_differences(),
        'statement_analysis': analyzer.analyze_statements(),
        'metrics_analysis': analyzer.analyze_additional_metrics(),
        'insight_analysis': analyzer.analyze_insights_by_cycle()
    }
    
    print("Analysis complete!")
    
    # Generate report
    print("\nGenerating HTML report...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f'Coffs_Harbour_3Cycle_Report_{timestamp}.html'
    analyzer.generate_html_report(analysis_results, output_file)
    
    print("\n" + "=" * 60)
    print(f"Report generated successfully: {output_file}")
    print("=" * 60)


if __name__ == "__main__":
    main()
