"""Lambda function for scheduled portfolio updates."""

import json
import time
from datetime import datetime
from src.portfolio import Portfolio
from src.analyzer import PortfolioAnalyzer

def lambda_handler(event, context):
    """
    Lambda handler triggered by CloudWatch Events every hour.
    Updates portfolio data and stores to DynamoDB.
    """

    try:
        # Create portfolio
        portfolio = Portfolio("AWS Portfolio")
        portfolio.add_holding("AAPL", 10, 150.00, "2023-01-15")
        portfolio.add_holding("MSFT", 5, 300.00, "2023-03-20")
        portfolio.add_holding("GOOGL", 3, 2800.00, "2023-06-10")
        portfolio.add_holding("AMZN", 2, 3200.00, "2023-08-05")

        # Analyze
        analyzer = PortfolioAnalyzer(portfolio)
        summary = analyzer.calculate_portfolio_summary()
        holdings = analyzer.calculate_current_value()

        # Prepare data for storage
        timestamp = int(time.time())
        data = {
            'timestamp': timestamp,
            'datetime': datetime.now().isoformat(),
            'summary': {
                'portfolio_name': summary['portfolio_name'],
                'total_invested': float(summary['total_invested']),
                'total_current_value': float(summary['total_current_value']),
                'total_gain_loss_dollars': float(summary['total_gain_loss_dollars']),
                'total_gain_loss_percent': float(summary['total_gain_loss_percent']),
                'number_of_holdings': summary['number_of_holdings'],
            },
            'holdings': json.loads(holdings.to_json(orient='table'))
        }

        print(f"Successfully updated portfolio at {datetime.now().isoformat()}")
        print(f"Total Value: ${summary['total_current_value']:,.2f}")

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Portfolio updated successfully',
                'data': data
            })
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
