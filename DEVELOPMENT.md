# Development Guide

Guide for contributors and developers extending the Portfolio Performance Dashboard.

## 🚀 Local Development Setup

### Prerequisites
- Python 3.9+
- Git
- Your favorite code editor (VS Code recommended)

### Setup

```bash
# Clone repository
git clone https://github.com/yourusername/portfolio-performance-dashboard.git
cd portfolio-performance-dashboard

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements_streamlit.txt
pip install -r requirements-dev.txt

# Run app
streamlit run streamlit_advanced.py --server.port 8502
```

## 📝 Code Style & Linting

### Format Code (Black)

```bash
# Format all Python files
black src/ streamlit_advanced.py

# Format single file
black streamlit_advanced.py
```

Configuration in `pyproject.toml`:
```toml
[tool.black]
line-length = 100
target-version = ['py39']
```

### Lint Code (Flake8)

```bash
flake8 src/ streamlit_advanced.py
```

Configuration in `.flake8`:
```
[flake8]
max-line-length = 100
exclude = .git,__pycache__,.venv
```

### Type Checking (mypy)

```bash
mypy src/ streamlit_advanced.py
```

### Pre-commit Hook (Automatic)

```bash
pip install pre-commit
pre-commit install
# Now linting runs automatically before each commit
```

---

## 🧪 Testing

### Run Tests

```bash
# All tests
pytest tests/ -v

# Specific test file
pytest tests/test_analyzer.py -v

# With coverage report
pytest tests/ --cov=src --cov-report=html
open htmlcov/index.html
```

### Test Structure

```
tests/
├── test_portfolio.py      # Portfolio class tests
├── test_analyzer.py       # Analyzer calculations
└── test_simulator.py      # Simulator algorithm
```

### Writing New Tests

```python
import pytest
from src.analyzer import PortfolioAnalyzer
from src.portfolio import Portfolio

def test_calculate_portfolio_summary():
    """Test portfolio summary calculation."""
    portfolio = Portfolio("Test")
    portfolio.add_holding("AAPL", 10, 100.0, "2023-01-01")

    analyzer = PortfolioAnalyzer(portfolio)
    # Note: This requires real network call
    # Use mocks for true unit tests

    summary = analyzer.calculate_portfolio_summary()
    assert summary is not None
    assert 'total_invested' in summary
```

### Test Coverage Goal

- Target: 80%+ code coverage
- Critical paths: 100% coverage
- Check coverage: `pytest --cov=src --cov-report=term-missing`

---

## 🏗️ Adding New Features

### Adding a New Metric

1. **Add calculation in `analyzer.py`**:

```python
class PortfolioAnalyzer:
    def calculate_new_metric(self, symbol: str) -> float:
        """Calculate new metric for a stock."""
        hist = StockDataFetcher.get_price_history(symbol, days=180)
        # Calculation logic here
        return metric_value
```

2. **Add test in `tests/test_analyzer.py`**:

```python
def test_calculate_new_metric():
    # Test the new metric
    pass
```

3. **Display in Streamlit**:

```python
# In streamlit_advanced.py
if show_metric:  # Add checkbox
    metric_value = analyzer.calculate_new_metric("AAPL")
    st.metric("New Metric", f"{metric_value:.2f}")
```

### Adding a New Chart

1. **Create chart rendering function**:

```python
def render_new_chart(analyzer: PortfolioAnalyzer):
    """Render new chart with Plotly."""
    data = analyzer.get_chart_data()

    fig = go.Figure(data=[
        go.Bar(x=data['x'], y=data['y'])
    ])
    fig.update_layout(
        title="New Chart",
        height=400,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    return fig
```

2. **Add to dashboard**:

```python
# In streamlit_advanced.py, tab_dashboard
show_new_chart = st.sidebar.checkbox("📊 New Chart", True)

if show_new_chart and is_real_time:
    st.subheader("New Chart")
    fig = render_new_chart(analyzer)
    st.plotly_chart(fig, use_container_width=True)
```

### Adding a New Simulator Feature

1. Add method to `DCASimulator` class
2. Add UI inputs in simulator tab
3. Call new method and render results

---

## 🐛 Debugging

### Enable Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# In streamlit app
st.write("Debug info:", analyzer.current_prices)
```

### Test Functions Locally

```python
# Outside Streamlit, test core logic
from src.simulator import DCASimulator

simulator = DCASimulator()
result = simulator.simulate_dca(
    symbols=["AAPL"],
    start_date="2024-01-01",
    end_date="2024-03-29",
    monthly_amount=500.0,
    allocation={"AAPL": 1.0}
)
print(result)
```

### Use Python Debugger (pdb)

```python
# Add breakpoint
import pdb
pdb.set_trace()

# In streamlit, use st.write for inspection
st.write("Debug:", variable_name)
```

---

## 📦 Dependency Management

### Add New Dependency

```bash
# Install
pip install new-library

# Add to requirements
pip freeze > requirements_streamlit.txt

# Or manually add:
echo "new-library>=1.0.0" >> requirements_streamlit.txt
```

### Update Dependencies

```bash
# Update all
pip install --upgrade -r requirements_streamlit.txt

# Update specific
pip install --upgrade streamlit

# Check for outdated
pip list --outdated
```

### Version Pinning

```
# requirements_streamlit.txt
# Pin exact versions for production
streamlit==1.28.0
plotly==5.18.0

# Or use >= for flexibility
streamlit>=1.28.0
plotly>=5.18.0
```

---

## 🔄 Git Workflow

### Branch Strategy

```
main (stable, deployed)
 ├── feature/new-feature (new features)
 ├── bugfix/issue-name (bug fixes)
 └── docs/update-readme (documentation)
```

### Commit Workflow

```bash
# 1. Create feature branch
git checkout -b feature/my-feature

# 2. Make changes
# Edit files...

# 3. Run tests
pytest tests/

# 4. Lint code
black src/
flake8 src/

# 5. Stage changes
git add src/ streamlit_advanced.py

# 6. Commit with message
git commit -m "feat: Add new feature description

- Detail 1
- Detail 2"

# 7. Push
git push origin feature/my-feature

# 8. Create Pull Request on GitHub
# 9. Request review
# 10. Address feedback
# 11. Merge to main
```

### Commit Message Format

```
<type>: <subject>

<description>

<footer>
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `refactor`: Code refactoring
- `test`: Adding tests
- `perf`: Performance improvement

Example:
```
feat: Add dividend yield calculation

- Calculate annual dividend yield per stock
- Display in risk metrics table
- Add unit tests

Closes #34
```

---

## 📚 Documentation Standards

### Docstrings (Google Style)

```python
def calculate_new_metric(self, symbol: str, days: int = 180) -> float:
    """Calculate annual growth rate for a stock.

    Args:
        symbol: Stock ticker (e.g., 'AAPL')
        days: Period for calculation in days

    Returns:
        Annual growth rate as percentage (e.g., 12.5 for 12.5%)

    Raises:
        ValueError: If symbol not found or days < 2

    Example:
        >>> analyzer = PortfolioAnalyzer(portfolio)
        >>> growth = analyzer.calculate_new_metric("AAPL", days=90)
        >>> print(growth)
        15.3
    """
```

### Type Hints

```python
def calculate_new_metric(
    symbol: str,
    days: int = 180
) -> float:
    pass

def get_holdings(
    analyzer: PortfolioAnalyzer
) -> pd.DataFrame:
    pass
```

---

## 🔍 Code Review Checklist

Before submitting PR, verify:

- [ ] Code follows style guide (Black formatted)
- [ ] All tests pass: `pytest tests/`
- [ ] No linting errors: `flake8 . `
- [ ] Type checking passes: `mypy src/`
- [ ] Coverage doesn't decrease
- [ ] Docstrings added for new functions
- [ ] Comments explain complex logic
- [ ] No hardcoded values (use constants)
- [ ] Error handling implemented
- [ ] Works locally: `streamlit run streamlit_advanced.py`
- [ ] README updated if needed
- [ ] Commit messages are clear

---

## 🚀 Release Process

### Creating a Release

1. **Bump version** in `src/__init__.py`:
```python
__version__ = "1.2.0"
```

2. **Update CHANGELOG.md**:
```markdown
## [1.2.0] - 2026-03-29

### Added
- DCA simulator feature
- Risk analytics

### Fixed
- Bug in correlation calculations

### Changed
- Updated dependencies
```

3. **Create commit**:
```bash
git tag -a v1.2.0 -m "Release v1.2.0"
git push origin v1.2.0
```

4. **Create GitHub Release**:
   - Go to GitHub → Releases → Draft new release
   - Select tag: v1.2.0
   - Title: "Portfolio Dashboard v1.2.0"
   - Description: Copy from CHANGELOG.md
   - Publish release

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/xyz`
3. Make changes
4. Run tests: `pytest tests/`
5. Commit: `git commit -am "feat: Add xyz"`
6. Push: `git push origin feature/xyz`
7. Create Pull Request
8. Wait for code review
9. Address feedback
10. Merge!

---

## 📞 Getting Help

- **Streamlit Docs**: https://docs.streamlit.io/
- **Plotly Docs**: https://plotly.com/python/
- **Pandas Docs**: https://pandas.pydata.org/docs/
- **yfinance Repo**: https://github.com/ranaroussi/yfinance

## Architecture Questions?

See [ARCHITECTURE.md](ARCHITECTURE.md) for:
- Module design
- Data flow diagrams
- Performance considerations
- Scaling strategies

---

**Happy coding! 🎉**
