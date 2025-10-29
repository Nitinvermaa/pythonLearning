# Test Command for Crawler with Enhanced HTML Report

## Quick Test (10 pages)

The default max pages is now set to **10** for testing. Run:

```bash
cd web_crawler
python sso_crawler.py --start-url "https://www.t-mobile.com/" --user-data-dir "C:\Users\nitin.verma\PythonProjects\pythonLearning\Profile_new" --headless false
```

## What's New in the HTML Report

### ✨ Features Added

1. **Interactive DataTables**
   - Sortable columns
   - Search functionality
   - Pagination (25 items per page)
   - Clickable URLs (open in new tab)

2. **Performance Chart**
   - Interactive Chart.js bar chart
   - Shows top 10 slowest pages
   - Hover for exact values
   - Responsive design

3. **Column Tooltips**
   - Hover over any column header to see metric definitions
   - TTFB, FCP, LCP, CLS, INP all explained

4. **Metric Definitions Section**
   - Comprehensive guide to all performance metrics
   - Explains what each metric means

5. **Visual Highlights**
   - Top 10 slowest pages highlighted in red/pink
   - Status badges (green for success, red for errors)
   - Gradient header design

6. **Modern UI**
   - Bootstrap 5 styling
   - Responsive layout
   - Card-based KPI display
   - Professional gradient header

### 🎯 Key Metrics Displayed

- **TTFB (ms)**: Time to First Byte
- **FCP (ms)**: First Contentful Paint
- **LCP (ms)**: Largest Contentful Paint
- **CLS**: Cumulative Layout Shift (visual stability)
- **Load Event (ms)**: Full page load time

### 📊 Charts & Visuals

- Bar chart of top 10 slowest pages
- Sortable tables
- Color-coded status indicators
- Row highlighting for slow pages

## Custom Page Limits

To test with different page limits:

```bash
# 5 pages
python sso_crawler.py --start-url "https://www.t-mobile.com/" --user-data-dir "C:\Users\nitin.verma\PythonProjects\pythonLearning\Profile_new" --headless false --max-pages 5

# 20 pages
python sso_crawler.py --start-url "https://www.t-mobile.com/" --user-data-dir "C:\Users\nitin.verma\PythonProjects\pythonLearning\Profile_new" --headless false --max-pages 20

# 100 pages (full crawl)
python sso_crawler.py --start-url "https://www.t-mobile.com/" --user-data-dir "C:\Users\nitin.verma\PythonProjects\pythonLearning\Profile_new" --headless false --max-pages 100
```

## Output Files

After running, you'll find:

1. **web_crawler/crawl_report.html** - The NEW enhanced interactive report
2. **web_crawler/crawl_results.xlsx** - Excel file with all data

Open `crawl_report.html` in your browser to see the interactive dashboard!

## What to Look For

1. ✅ **Metric Definitions**: Hover column headers for tooltips
2. ✅ **Chart**: Interactive chart at the top
3. ✅ **Highlighted Rows**: Red/pink rows are slowest pages
4. ✅ **Sortable Tables**: Click column headers to sort
5. ✅ **Search**: Type in search box to filter
6. ✅ **Clickable URLs**: Click any URL to open in new tab

