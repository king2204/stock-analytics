"""Generate reports and visualizations."""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from src.analyzer import PortfolioAnalyzer


class PortfolioReporter:
    """Generate reports and visualizations for portfolio analysis."""
    
    def __init__(self, analyzer: PortfolioAnalyzer):
        """
        Initialize reporter.
        
        Args:
            analyzer: PortfolioAnalyzer object
        """
        self.analyzer = analyzer
        sns.set_style("whitegrid")
    
    def print_summary_report(self):
        """Print portfolio summary report to console."""
        summary = self.analyzer.calculate_portfolio_summary()
        
        print("\n" + "="*60)
        print(f"PORTFOLIO SUMMARY: {summary['portfolio_name']}")
        print("="*60)
        print(f"As of: {summary['as_of_date']}")
        print(f"Number of Holdings: {summary['number_of_holdings']}")
        print("-"*60)
        print(f"Total Invested: ${summary['total_invested']:,.2f}")
        print(f"Current Value: ${summary['total_current_value']:,.2f}")
        print(f"Total Gain/Loss: ${summary['total_gain_loss_dollars']:,.2f}")
        print(f"Total Return: {summary['total_gain_loss_percent']:.2f}%")
        print("="*60 + "\n")
    
    def print_allocation_report(self):
        """Print asset allocation report."""
        allocation = self.analyzer.calculate_asset_allocation()
        
        print("\n" + "="*60)
        print("ASSET ALLOCATION")
        print("="*60)
        for _, row in allocation.iterrows():
            print(f"{row['symbol']}: {row['allocation_percent']:.2f}% (${row['current_value']:,.2f})")
        print("="*60 + "\n")
    
    def print_holding_details(self):
        """Print detailed holding information."""
        holdings = self.analyzer.calculate_current_value()
        
        print("\n" + "="*60)
        print("HOLDING DETAILS")
        print("="*60)
        for _, holding in holdings.iterrows():
            print(f"\n{holding['symbol']}")
            print(f"  Shares: {holding['shares']}")
            print(f"  Purchase Price: ${holding['purchase_price']:.2f}")
            print(f"  Current Price: ${holding['current_price']:.2f}")
            print(f"  Current Value: ${holding['current_value']:,.2f}")
            print(f"  Gain/Loss: ${holding['gain_loss_dollars']:,.2f} ({holding['gain_loss_percent']:.2f}%)")
        print("\n" + "="*60 + "\n")
    
    def print_top_performers(self, top_n: int = 5):
        """Print top performing holdings."""
        top = self.analyzer.get_best_performers(top_n)

        print("\n" + "="*60)
        print(f"TOP {top_n} PERFORMERS")
        print("="*60)
        for _, holding in top.iterrows():
            sign = "+" if holding['gain_loss_percent'] >= 0 else ""
            print(f"{holding['symbol']}: {sign}{holding['gain_loss_percent']:.2f}% (${holding['gain_loss_dollars']:,.2f})")
        print("="*60 + "\n")
    
    def plot_allocation_pie_chart(self, save_path: str = None):
        """
        Create and display allocation pie chart.
        
        Args:
            save_path: Optional path to save the figure
        """
        allocation = self.analyzer.calculate_asset_allocation()
        
        plt.figure(figsize=(10, 8))
        plt.pie(allocation['allocation_percent'], labels=allocation['symbol'], autopct='%1.1f%%')
        plt.title(f"{self.analyzer.portfolio.name} - Asset Allocation")
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.show()
    
    def plot_performance_bars(self, save_path: str = None):
        """
        Create and display performance bar chart.
        
        Args:
            save_path: Optional path to save the figure
        """
        holdings = self.analyzer.calculate_current_value()
        
        plt.figure(figsize=(12, 6))
        colors = ['green' if x > 0 else 'red' for x in holdings['gain_loss_percent']]
        plt.barh(holdings['symbol'], holdings['gain_loss_percent'], color=colors)
        plt.xlabel('Gain/Loss %')
        plt.title(f"{self.analyzer.portfolio.name} - Performance by Holding")
        plt.axvline(x=0, color='black', linestyle='-', linewidth=0.5)
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.show()
    
    def export_to_csv(self, filepath: str):
        """
        Export detailed holdings report to CSV.
        
        Args:
            filepath: Path to save CSV file
        """
        holdings = self.analyzer.calculate_current_value()
        holdings.to_csv(filepath, index=False)
        print(f"Report exported to {filepath}")
