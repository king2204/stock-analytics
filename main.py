"""Main script to run portfolio analysis."""

from src.portfolio import Portfolio
from src.analyzer import PortfolioAnalyzer
from src.reporter import PortfolioReporter


def main():
    """Run portfolio analysis example."""
    
    # Create a sample portfolio
    portfolio = Portfolio("My Stock Portfolio")
    
    # Add some holdings (you can modify these)
    portfolio.add_holding("AAPL", 10, 150.00, "2023-01-15")
    portfolio.add_holding("MSFT", 5, 300.00, "2023-03-20")
    portfolio.add_holding("GOOGL", 3, 2800.00, "2023-06-10")
    portfolio.add_holding("AMZN", 2, 3200.00, "2023-08-05")
    
    print("Portfolio created with sample holdings.")
    print(f"Holdings: {portfolio.get_symbols()}")
    
    # Create analyzer
    analyzer = PortfolioAnalyzer(portfolio)
    
    # Create reporter
    reporter = PortfolioReporter(analyzer)
    
    # Print reports
    reporter.print_summary_report()
    reporter.print_allocation_report()
    reporter.print_holding_details()
    reporter.print_top_performers()
    
    # Optional: Generate visualizations (uncomment to use)
    # reporter.plot_allocation_pie_chart('allocation.png')
    # reporter.plot_performance_bars('performance.png')
    # reporter.export_to_csv('portfolio_report.csv')


if __name__ == "__main__":
    main()
