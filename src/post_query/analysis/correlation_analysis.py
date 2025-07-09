import pandas as pd
import numpy as np
import yaml
import os
from pathlib import Path
import statsmodels.api as sm
import statsmodels.formula.api as smf
from statsmodels.stats.outliers_influence import variance_inflation_factor

def load_data():
    """Load the main analysis dataset"""
    data_path = Path(__file__).parent.parent.parent / "data" / "main_analysis_dataset.feather"
    df = pd.read_feather(data_path)
    return df

def explore_data(df):
    """Explore the structure of the dataset"""
    print("Dataset shape:", df.shape)
    print("\nColumn names:")
    print(df.columns.tolist())
    print("\nFirst few rows:")
    print(df.head())
    print("\nData types:")
    print(df.dtypes)
    print("\nSummary statistics:")
    print(df.describe())

def prepare_analysis_data(df):
    """Prepare data for correlation analysis"""
    # Create a copy for analysis
    analysis_df = df.copy()
    
    # Create log market value (handling missing/zero values)
    analysis_df['log_mkvalt'] = np.log(analysis_df['mkvalt'].replace(0, np.nan))
    
    # Clean sector, country, and year variables
    analysis_df['sector'] = analysis_df['gsector'].astype('category')
    analysis_df['country'] = analysis_df['loc'].astype('category')
    analysis_df['year'] = analysis_df['fyear'].astype('category')
    
    return analysis_df

def calculate_summary_statistics(df):
    """Calculate basic summary statistics for the analysis"""
    stats = {}
    
    # Total number of transcripts
    stats['total_transcripts'] = len(df)
    
    # LLM tagging statistics
    stats['llm_tagged_collusive'] = int(df['llm_flag'].sum())
    stats['llm_tagged_collusive_pct'] = float(df['llm_flag'].mean() * 100)
    
    # Human tagging statistics
    stats['human_tagged_collusive'] = int(df['benchmark_human_flag'].sum())
    stats['human_tagged_collusive_pct'] = float(df['benchmark_human_flag'].mean() * 100)
    
    # Both LLM and human tagged as collusive
    both_tagged = (df['llm_flag'] == 1) & (df['benchmark_human_flag'] == 1)
    stats['both_tagged_collusive'] = int(both_tagged.sum())
    stats['both_tagged_collusive_pct'] = float(both_tagged.mean() * 100)
    
    return stats

def run_logistic_regression_market_value(df):
    """Run logistic regression with log market value as predictor"""
    # Filter to observations with non-missing market value
    reg_df = df.dropna(subset=['log_mkvalt'])
    
    if len(reg_df) == 0:
        return None
    
    # Run regression using statsmodels
    model = smf.logit('llm_flag ~ log_mkvalt', data=reg_df).fit(disp=0)
    
    results = {
        'n_obs': int(model.nobs),
        'coefficient': float(model.params['log_mkvalt']),
        'std_error': float(model.bse['log_mkvalt']),
        'p_value': float(model.pvalues['log_mkvalt']),
        'odds_ratio': float(np.exp(model.params['log_mkvalt'])),
        'confidence_interval': [float(x) for x in model.conf_int().loc['log_mkvalt'].tolist()],
        'pseudo_r2': float(model.prsquared),
        'log_likelihood': float(model.llf),
        'aic': float(model.aic),
        'bic': float(model.bic)
    }
    
    return results

def run_logistic_regression_sector(df):
    """Run logistic regression with sector as predictor"""
    # Filter to observations with non-missing sector
    reg_df = df.dropna(subset=['sector'])
    
    if len(reg_df) == 0:
        return None
    
    # Create dummy variables for sectors (excluding the first category as reference)
    sector_dummies = pd.get_dummies(reg_df['sector'], prefix='sector', drop_first=True)
    
    # Clean column names to make them valid for statsmodels
    sector_dummies.columns = [col.replace(' ', '_').replace('.', '_').replace('-', '_') for col in sector_dummies.columns]
    
    reg_df_with_dummies = pd.concat([reg_df[['llm_flag']], sector_dummies], axis=1)
    
    # Run regression using statsmodels
    formula = 'llm_flag ~ ' + ' + '.join(sector_dummies.columns)
    model = smf.logit(formula, data=reg_df_with_dummies).fit(disp=0)
    
    # Extract results for each sector
    results = {
        'n_obs': int(model.nobs),
        'pseudo_r2': float(model.prsquared),
        'log_likelihood': float(model.llf),
        'aic': float(model.aic),
        'bic': float(model.bic),
        'sector_effects': {}
    }
    
    # Add coefficient for each sector (relative to reference category)
    for param in model.params.index:
        if param != 'Intercept':
            results['sector_effects'][param] = {
                'coefficient': float(model.params[param]),
                'std_error': float(model.bse[param]),
                'p_value': float(model.pvalues[param]),
                'odds_ratio': float(np.exp(model.params[param])),
                'confidence_interval': [float(x) for x in model.conf_int().loc[param].tolist()]
            }
    
    return results

def run_logistic_regression_country(df):
    """Run logistic regression with country as predictor, using top 5 most common countries"""
    # Filter to observations with non-missing country
    reg_df = df.dropna(subset=['country'])
    
    if len(reg_df) == 0:
        return None
    
    # Keep only the 5 most common countries
    country_counts = reg_df['country'].value_counts()
    top_5_countries = country_counts.head(5).index
    reg_df = reg_df[reg_df['country'].isin(top_5_countries)]
    
    if len(reg_df) == 0 or len(top_5_countries) <= 1:
        return None
    
    # Reset the country variable to only include the top 5 countries (removes unused categories)
    reg_df['country'] = reg_df['country'].cat.remove_unused_categories()
    
    # Reorder categories so the most common country (USA) is first (will be reference category)
    most_common_country = top_5_countries[0]  # First country in the sorted list is most common
    other_countries = [c for c in reg_df['country'].cat.categories if c != most_common_country]
    new_category_order = [most_common_country] + sorted(other_countries)
    reg_df['country'] = reg_df['country'].cat.reorder_categories(new_category_order)
    
    # Create dummy variables for countries (excluding the first category as reference)
    country_dummies = pd.get_dummies(reg_df['country'], prefix='country', drop_first=True)
    
    # Clean column names to make them valid for statsmodels
    country_dummies.columns = [col.replace(' ', '_').replace('.', '_').replace('-', '_').replace('(', '').replace(')', '') for col in country_dummies.columns]
    
    reg_df_with_dummies = pd.concat([reg_df[['llm_flag']], country_dummies], axis=1)
    
    try:
        # Run regression using statsmodels
        formula = 'llm_flag ~ ' + ' + '.join(country_dummies.columns)
        model = smf.logit(formula, data=reg_df_with_dummies).fit(disp=0)
        
        # Extract results for each country
        results = {
            'n_obs': int(model.nobs),
            'pseudo_r2': float(model.prsquared),
            'log_likelihood': float(model.llf),
            'aic': float(model.aic),
            'bic': float(model.bic),
            'reference_country': most_common_country,  # Add reference country info
            'country_effects': {}
        }
        
        # Add coefficient for each country (relative to reference category)
        for param in model.params.index:
            if param != 'Intercept':
                results['country_effects'][param] = {
                    'coefficient': float(model.params[param]),
                    'std_error': float(model.bse[param]),
                    'p_value': float(model.pvalues[param]),
                    'odds_ratio': float(np.exp(model.params[param])),
                    'confidence_interval': [float(x) for x in model.conf_int().loc[param].tolist()]
                }
        
        return results
    
    except (np.linalg.LinAlgError, ValueError) as e:
        print(f"Could not fit country regression due to: {e}")
        return None

def run_logistic_regression_year(df):
    """Run logistic regression with individual years as predictor, starting from 2008"""
    # Filter to observations with non-missing year
    reg_df = df.dropna(subset=['year'])
    
    if len(reg_df) == 0:
        return None
    
    # Print distribution of transcripts and hits by individual year (all years)
    print("\n   Individual Year Distribution (All Years):")
    year_summary = reg_df.groupby('fyear').agg({
        'llm_flag': ['count', 'sum']
    }).round(1)
    year_summary.columns = ['transcripts', 'hits']
    year_summary['hit_rate'] = (year_summary['hits'] / year_summary['transcripts'] * 100).round(1)
    
    for year in sorted(reg_df['fyear'].unique()):
        row = year_summary.loc[year]
        print(f"     {int(year)}: {int(row['transcripts']):,} transcripts, {int(row['hits']):,} hits ({row['hit_rate']:.1f}%)")
    
    # Filter to years 2008 and later for regression
    reg_df_filtered = reg_df[reg_df['fyear'] >= 2008].copy()
    
    if len(reg_df_filtered) == 0:
        return None
    
    print(f"\n   Using years 2008+ for regression (N = {len(reg_df_filtered):,})")
    
    # Get unique years from 2008+ and sort them
    years = sorted(reg_df_filtered['fyear'].unique())
    
    # Use the earliest year (2008) as reference category
    reg_df_filtered['year'] = reg_df_filtered['fyear'].astype('category')
    reg_df_filtered['year'] = reg_df_filtered['year'].cat.reorder_categories(years)
    
    # Create dummy variables for years (excluding the first category as reference)
    year_dummies = pd.get_dummies(reg_df_filtered['year'], prefix='year', drop_first=True)
    
    # Clean column names to make them valid for statsmodels
    year_dummies.columns = [col.replace(' ', '_').replace('.', '_').replace('-', '_') for col in year_dummies.columns]
    
    reg_df_with_dummies = pd.concat([reg_df_filtered[['llm_flag']], year_dummies], axis=1)
    
    try:
        # Run regression using statsmodels
        formula = 'llm_flag ~ ' + ' + '.join(year_dummies.columns)
        model = smf.logit(formula, data=reg_df_with_dummies).fit(disp=0)
        
        # Extract results for each year
        results = {
            'n_obs': int(model.nobs),
            'pseudo_r2': float(model.prsquared),
            'log_likelihood': float(model.llf),
            'aic': float(model.aic),
            'bic': float(model.bic),
            'reference_year': years[0],  # Add reference year info (2008)
            'year_effects': {}
        }
        
        # Add coefficient for each year (relative to reference category)
        for param in model.params.index:
            if param != 'Intercept':
                results['year_effects'][param] = {
                    'coefficient': float(model.params[param]),
                    'std_error': float(model.bse[param]),
                    'p_value': float(model.pvalues[param]),
                    'odds_ratio': float(np.exp(model.params[param])),
                    'confidence_interval': [float(x) for x in model.conf_int().loc[param].tolist()]
                }
        
        return results
    
    except (np.linalg.LinAlgError, ValueError) as e:
        print(f"Could not fit year regression due to: {e}")
        return None

def save_results_to_yaml(results, output_path):
    """Save analysis results to YAML file"""
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        yaml.dump(results, f, default_flow_style=False, sort_keys=False)
    
    print(f"Results saved to: {output_path}")

def main():
    """Run the complete correlation analysis"""
    print("Loading data...")
    df = load_data()
    
    print("\nPreparing analysis data...")
    analysis_df = prepare_analysis_data(df)
    
    print("\nCalculating summary statistics...")
    summary_stats = calculate_summary_statistics(analysis_df)
    
    print("\nRunning logistic regression analyses...")
    
    # Market value regression
    print("  - Log market value regression...")
    market_value_results = run_logistic_regression_market_value(analysis_df)
    
    # Sector regression
    print("  - Sector regression...")
    sector_results = run_logistic_regression_sector(analysis_df)
    
    # Country regression
    print("  - Country regression...")
    country_results = run_logistic_regression_country(analysis_df)
    
    # Year regression
    print("  - Year regression...")
    year_results = run_logistic_regression_year(analysis_df)
    
    # Compile results for YAML (only summary stats)
    results = {
        'summary_statistics': summary_stats
    }
    
    # Save simplified results
    output_path = Path(__file__).parent.parent.parent / "output" / "yaml" / "correlation_analysis.yaml"
    save_results_to_yaml(results, output_path)
    
    # Print key findings
    print("\n" + "="*60)
    print("SUMMARY STATISTICS")
    print("="*60)
    print(f"Total transcripts analyzed: {summary_stats['total_transcripts']:,}")
    print(f"LLM tagged as collusive: {summary_stats['llm_tagged_collusive']:,} ({summary_stats['llm_tagged_collusive_pct']:.1f}%)")
    print(f"Human tagged as collusive: {summary_stats['human_tagged_collusive']:,} ({summary_stats['human_tagged_collusive_pct']:.1f}%)")
    print(f"Both tagged as collusive: {summary_stats['both_tagged_collusive']:,} ({summary_stats['both_tagged_collusive_pct']:.1f}%)")
    
    # Print logistic regression results
    print("\n" + "="*60)
    print("LOGISTIC REGRESSION RESULTS")
    print("="*60)
    
    if market_value_results:
        print(f"\n1. MARKET VALUE REGRESSION:")
        print(f"   N = {market_value_results['n_obs']:,}")
        print(f"   Coefficient: {market_value_results['coefficient']:.4f}")
        print(f"   Standard Error: {market_value_results['std_error']:.4f}")
        print(f"   P-value: {market_value_results['p_value']:.2e}")
        print(f"   Odds Ratio: {market_value_results['odds_ratio']:.4f}")
        print(f"   95% CI: [{market_value_results['confidence_interval'][0]:.4f}, {market_value_results['confidence_interval'][1]:.4f}]")
        print(f"   Pseudo R²: {market_value_results['pseudo_r2']:.4f}")
    
    if sector_results:
        print(f"\n2. SECTOR REGRESSION:")
        print(f"   N = {sector_results['n_obs']:,}")
        print(f"   Pseudo R²: {sector_results['pseudo_r2']:.4f}")
        print(f"   Sector Effects (relative to reference category):")
        for sector, effects in sector_results['sector_effects'].items():
            print(f"     {sector}: OR={effects['odds_ratio']:.4f}, p={effects['p_value']:.2e}")
    
    if country_results:
        print(f"\n3. COUNTRY REGRESSION (Top 5 Countries):")
        print(f"   N = {country_results['n_obs']:,}")
        print(f"   Reference Country: {country_results['reference_country']}")
        print(f"   Pseudo R²: {country_results['pseudo_r2']:.4f}")
        print(f"   Country Effects (relative to {country_results['reference_country']}):")
        for country, effects in country_results['country_effects'].items():
            print(f"     {country}: OR={effects['odds_ratio']:.4f}, p={effects['p_value']:.2e}")
    else:
        print(f"\n3. COUNTRY REGRESSION (Top 5 Countries):")
        print(f"   Could not be estimated due to multicollinearity issues")
    
    if year_results:
        print(f"\n4. YEAR REGRESSION (Individual Years, 2008+):")
        print(f"   N = {year_results['n_obs']:,}")
        print(f"   Reference Year: {year_results['reference_year']}")
        print(f"   Pseudo R²: {year_results['pseudo_r2']:.4f}")
        print(f"   Year Effects (relative to {year_results['reference_year']}):")
        for year, effects in year_results['year_effects'].items():
            print(f"     {year}: OR={effects['odds_ratio']:.4f}, p={effects['p_value']:.2e}")
    else:
        print(f"\n4. YEAR REGRESSION (Individual Years, 2008+):")
        print(f"   Could not be estimated (insufficient data)")
    
    print(f"\nSummary statistics saved to: {output_path}")

if __name__ == "__main__":
    main()