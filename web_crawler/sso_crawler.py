#!/usr/bin/env python3
# -*- coding: utf-8 -*-


"""
Authenticated site crawler with Chrome profile (SSO), Playwright, and performance KPIs.
Outputs:
  - crawl_results.xlsx (Pages, BrokenLinks, Errors)
  - crawl_report.html  (tables + KPI chart)

Usage:pip install playwright pandas openpyxl matplotlib
  python -m playwright install chrome
  python sso_crawler.py --start-url "https://example.com" --user-data-dir "/path/to/profile" --headless false
"""

import argparse
import asyncio
from pathlib import Path
from urllib.parse import urlparse, urljoin

import pandas as pd

from playwright.async_api import async_playwright

import io
import base64
import matplotlib.pyplot as plt

//
# ----------------------- Utilities -----------------------

def default_port(scheme: str):
    return 443 if scheme == "https" else 80

def same_origin(u1: str, u2: str) -> bool:
    try:
        a, b = urlparse(u1), urlparse(u2)
        return (a.scheme, a.hostname, a.port or default_port(a.scheme)) == (
            b.scheme, b.hostname, b.port or default_port(b.scheme)
        )
    except Exception:
        return False

def normalize_link(base_url: str, href: str) -> str:
    try:
        # strip hash fragments
        return urljoin(base_url, (href or "").split("#")[0].strip())
    except Exception:
        return ""


# ----------------------- Page JS Snippets -----------------------

WEB_VITALS_BOOT_JS = """
() => {
  if (!window.__vitals__) {
    window.__vitals__ = { lcp: 0, cls: 0, inp: 0, longTasks: {count:0,total:0} };

    try {
      new PerformanceObserver((list) => {
        for (const e of list.getEntries()) {
          if (e.startTime > window.__vitals__.lcp) window.__vitals__.lcp = e.startTime;
        }
      }).observe({ type: 'largest-contentful-paint', buffered: true });
    } catch(e){}

    try {
      new PerformanceObserver((list) => {
        for (const e of list.getEntries()) {
          if (!e.hadRecentInput) window.__vitals__.cls += e.value;
        }
      }).observe({ type: 'layout-shift', buffered: true });
    } catch(e){}

    try {
      new PerformanceObserver((list) => {
        for (const e of list.getEntries()) {
          window.__vitals__.longTasks.count += 1;
          window.__vitals__.longTasks.total += (e.duration || 0);
        }
      }).observe({ type: 'longtask', buffered: true });
    } catch(e){}

    try {
      new PerformanceObserver((list) => {
        for (const e of list.getEntries()) {
          const d = (e.processingEnd || e.duration || 0);
          if (d > window.__vitals__.inp) window.__vitals__.inp = d;
        }
      }).observe({ type: 'event', buffered: true, durationThreshold: 16 });
    } catch(e){}
  }
}
"""

COLLECT_METRICS_JS = """
() => {
  const nav = performance.getEntriesByType('navigation')[0];
  const paints = performance.getEntriesByType('paint');
  const fcp = (paints.find(p => p.name === 'first-contentful-paint') || {}).startTime || 0;

  const resources = performance.getEntriesByType('resource');
  const resAgg = resources.reduce((acc, r) => {
    const t = (r.initiatorType || 'other').toLowerCase();
    acc.count += 1;
    acc.encoded += (r.encodedBodySize || 0);
    acc.transfer += (r.transferSize || 0);
    acc.types[t] = (acc.types[t] || 0) + (r.encodedBodySize || 0);
    return acc;
  }, {count:0, encoded:0, transfer:0, types:{}});

  const vit = (window.__vitals__ || {lcp:0,cls:0,inp:0,longTasks:{count:0,total:0}});

  return {
    timing: nav ? {
      ttfb_ms: (nav.responseStart || 0),
      dom_content_loaded_ms: (nav.domContentLoadedEventEnd || 0),
      response_end_ms: (nav.responseEnd || 0),
      load_event_ms: (nav.loadEventEnd || 0),
      type: nav.type || ""
    } : null,
    fcp_ms: fcp,
    lcp_ms: vit.lcp || 0,
    cls: vit.cls || 0,
    inp_ms: vit.inp || 0,
    longtask_count: (vit.longTasks && vit.longTasks.count) || 0,
    longtask_total_ms: (vit.longTasks && vit.longTasks.total) || 0,
    resources: resAgg
  };
}
"""

GET_LINKS_JS = """
() => {
  // Get all links with href attribute
  const links = Array.from(document.querySelectorAll('a[href]'))
    .map(a => a.getAttribute('href'))
    .filter(Boolean);
  
  // Also get links from elements that might navigate (buttons, divs with data-url, etc.)
  const otherLinks = Array.from(document.querySelectorAll('[data-url], [data-href], [data-link]'))
    .map(el => el.getAttribute('data-url') || el.getAttribute('data-href') || el.getAttribute('data-link'))
    .filter(Boolean);
  
  // Also try to find any onclick handlers that navigate
  const onclickLinks = Array.from(document.querySelectorAll('[onclick*="location"], [onclick*="href"]'))
    .map(el => {
      const onclick = el.getAttribute('onclick') || '';
      const match = onclick.match(/(?:location|href)\s*[=:]\s*["']([^"']+)["']/);
      return match ? match[1] : null;
    })
    .filter(Boolean);
  
  return [...new Set([...links, ...otherLinks, ...onclickLinks])];
}
"""

GET_TITLE_JS = "document.title || ''"

DEBUG_PAGE_CONTENT_JS = """
() => {
  const links = document.querySelectorAll('a');
  return {
    totalLinks: links.length,
    linksWithHref: Array.from(links).filter(a => a.href).length,
    linksWithoutHref: Array.from(links).filter(a => !a.href).length,
    sampleLinks: Array.from(links).slice(0, 5).map(a => ({
      text: a.textContent.trim().substring(0, 50),
      href: a.href || a.getAttribute('href') || 'NO HREF',
      className: a.className
    })),
    bodyTextPreview: document.body.textContent.substring(0, 200)
  };
}
"""


# ----------------------- HTML Report Generation -----------------------

def generate_advanced_html_report(pages_df, broken_df, errors_df, 
                                   total_pages, total_links, total_broken,
                                   avg_load, avg_lcp, avg_cls, chart_data, top_slowest):
    """Generate an advanced, interactive HTML report with charts and tooltips."""
    
    # Convert DataFrames to JSON for JavaScript
    pages_json = pages_df.to_json(orient='records') if not pages_df.empty else '[]'
    broken_json = broken_df.to_json(orient='records') if not broken_df.empty else '[]'
    errors_json = errors_df.to_json(orient='records') if not errors_df.empty else '[]'
    
    # Get top slowest URLs as JSON
    top_slowest_json = str(top_slowest).replace('"', '\\"')
    
    # Metric definitions
    metrics_defs = {
        'ttfb_ms': 'Time to First Byte - Time from request until first response byte',
        'fcp_ms': 'First Contentful Paint - When first content becomes visible',
        'lcp_ms': 'Largest Contentful Paint - When largest content element loads',
        'cls': 'Cumulative Layout Shift - Visual stability score (lower is better)',
        'inp_ms': 'Interaction to Next Paint - Input responsiveness latency',
        'dom_content_loaded_ms': 'DOM content loaded event time',
        'load_event_ms': 'Full page load event time',
        'req_count': 'Total number of HTTP requests',
        'bytes_encoded': 'Total bytes transferred (compressed)',
        'bytes_transfer': 'Total bytes transferred (actual)',
    }
    
    # Column tooltips for Pages table
    column_tooltips = {
        'url': 'The page URL',
        'title': 'The page title from document.title',
        'status': 'HTTP status code',
        'ttfb_ms': metrics_defs['ttfb_ms'],
        'fcp_ms': metrics_defs['fcp_ms'],
        'lcp_ms': metrics_defs['lcp_ms'],
        'cls': metrics_defs['cls'],
        'inp_ms': metrics_defs['inp_ms'],
        'dom_content_loaded_ms': metrics_defs['dom_content_loaded_ms'],
        'response_end_ms': 'HTTP response end time',
        'load_event_ms': metrics_defs['load_event_ms'],
        'req_count': metrics_defs['req_count'],
        'bytes_encoded': metrics_defs['bytes_encoded'],
        'bytes_transfer': metrics_defs['bytes_transfer'],
        'bytes_img': 'Bytes for image resources',
        'bytes_script': 'Bytes for JavaScript files',
        'bytes_css': 'Bytes for CSS files',
        'bytes_font': 'Bytes for font files',
        'console_errors': 'Number of console errors on page',
        'cache_control': 'Cache-Control header value',
        'content_encoding': 'Content encoding (gzip, etc)',
        'links_checked': 'Total links checked on this page',
        'links_broken': 'Number of broken links found',
    }
    
    # Chart data - multiple metrics for multiline chart
    chart_labels = []
    chart_ttfb = []
    chart_fcp = []
    chart_lcp = []
    chart_load = []
    
    if not chart_data.empty:
        chart_labels = [url[:50] + '...' if len(url) > 50 else url for url in chart_data['url'].tolist()]
        chart_ttfb = chart_data['ttfb_ms'].fillna(0).tolist()
        chart_fcp = chart_data['fcp_ms'].fillna(0).tolist()
        chart_lcp = chart_data['lcp_ms'].fillna(0).tolist()
        chart_load = chart_data['load_event_ms'].fillna(0).tolist()
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset='utf-8'>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Advanced Crawl Report</title>
    
    <!-- Bootstrap CSS for styling -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    
    <!-- DataTables CSS -->
    <link href="https://cdn.datatables.net/1.13.6/css/jquery.dataTables.min.css" rel="stylesheet">
    
    <!-- Chart.js CSS -->
    <link href="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.css" rel="stylesheet">
    
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 20px; background: linear-gradient(135deg, #E91E63 0%, #9C27B0 100%); min-height: 100vh; }}
        .header {{ background: linear-gradient(135deg, #E91E63 0%, #9C27B0 100%); color: white; padding: 30px; border-radius: 10px; margin-bottom: 30px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
        .header h1 {{ margin: 0; font-size: 2.5em; }}
        .header p {{ margin: 10px 0 0 0; opacity: 0.9; }}
        
        .kpi-card {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; }}
        .kpi-value {{ font-size: 2em; font-weight: bold; color: #E91E63; }}
        .kpi-label {{ color: #666; font-size: 0.9em; }}
        
        .tooltip-col {{ position: relative; }}
        .tooltip-col:hover {{ cursor: help; }}
        
        .slow-page {{ background-color: #ffebee !important; border-left: 4px solid #f44336 !important; }}
        
        .metric-box {{ background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 10px 0; border-left: 4px solid #E91E63; }}
        .metric-box h5 {{ margin: 0 0 8px 0; color: #333; }}
        .metric-box p {{ margin: 0; color: #666; font-size: 0.9em; }}
        
        .chart-container {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin: 20px 0; }}
        
        table {{ font-size: 0.9em; }}
        .dataTables_wrapper {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        
        .badge {{ padding: 5px 10px; border-radius: 5px; }}
        .badge-success {{ background: #28a745; color: white; }}
        .badge-danger {{ background: #dc3545; color: white; }}
        .badge-warning {{ background: #ffc107; color: #333; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 Advanced Crawl Report</h1>
        <p>Interactive performance analysis with real-time metrics</p>
    </div>
    
    <!-- KPI Summary -->
    <div class="row mb-4">
        <div class="col-md-3">
            <div class="kpi-card text-center">
                <div class="kpi-value">{total_pages}</div>
                <div class="kpi-label">Total Pages Crawled</div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="kpi-card text-center">
                <div class="kpi-value">{total_links}</div>
                <div class="kpi-label">Links Checked</div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="kpi-card text-center">
                <div class="kpi-value">{total_broken}</div>
                <div class="kpi-label">Broken Links</div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="kpi-card text-center">
                <div class="kpi-value">{('-' if avg_load is None else f'{avg_load}ms')}</div>
                <div class="kpi-label">Avg Load Time</div>
            </div>
        </div>
    </div>
    
    <!-- Metric Definitions -->
    <div class="metric-box">
        <h5>📊 Performance Metrics Guide</h5>
        <div class="row">
            <div class="col-md-6">
                <p><strong>TTFB (ms):</strong> {metrics_defs['ttfb_ms']}</p>
                <p><strong>FCP (ms):</strong> {metrics_defs['fcp_ms']}</p>
                <p><strong>LCP (ms):</strong> {metrics_defs['lcp_ms']}</p>
                <p><strong>CLS:</strong> {metrics_defs['cls']}</p>
                <p><strong>INP (ms):</strong> {metrics_defs['inp_ms']}</p>
            </div>
            <div class="col-md-6">
                <p><strong>Load Event:</strong> {metrics_defs['load_event_ms']}</p>
                <p><strong>DOM Loaded:</strong> {metrics_defs['dom_content_loaded_ms']}</p>
                <p><strong>Requests:</strong> {metrics_defs['req_count']}</p>
                <p><strong>Bytes:</strong> Total data transferred in bytes</p>
            </div>
        </div>
    </div>
    
    <!-- Performance Chart -->
    <div class="chart-container">
        <h3>📈 Performance Metrics Comparison</h3>
        <p class="text-muted">Comparing TTFB, FCP, LCP, and Load Event times across top 10 slowest pages</p>
        <canvas id="performanceChart"></canvas>
    </div>
    
    <!-- Pages Table -->
    <div class="dataTables_wrapper">
        <h3>📄 All Crawled Pages</h3>
        <table id="pagesTable" class="table table-striped table-hover">
            <thead class="thead-dark">
                <tr>
                    <th>URL</th>
                    <th>Title</th>
                    <th title="{column_tooltips['status']}">Status</th>
                    <th title="{column_tooltips['ttfb_ms']}">TTFB (ms)</th>
                    <th title="{column_tooltips['fcp_ms']}">FCP (ms)</th>
                    <th title="{column_tooltips['lcp_ms']}">LCP (ms)</th>
                    <th title="{column_tooltips['cls']}">CLS</th>
                    <th title="{column_tooltips['load_event_ms']}">Load (ms)</th>
                    <th title="{column_tooltips['links_broken']}">Broken</th>
                </tr>
            </thead>
            <tbody id="pagesTableBody">
            </tbody>
        </table>
    </div>
    
    <!-- Broken Links -->
    <div class="dataTables_wrapper mt-4">
        <h3>🔗 Broken Links</h3>
        <table id="brokenTable" class="table table-striped">
            <thead class="thead-dark">
                <tr>
                    <th>Source URL</th>
                    <th>Broken Link</th>
                    <th>Status</th>
                    <th>Error</th>
                </tr>
            </thead>
            <tbody id="brokenTableBody">
            </tbody>
        </table>
    </div>
    
    <!-- Errors -->
    <div class="dataTables_wrapper mt-4">
        <h3>⚠️ Errors</h3>
        <table id="errorsTable" class="table table-striped">
            <thead class="thead-dark">
                <tr>
                    <th>URL</th>
                    <th>Error Message</th>
                </tr>
            </thead>
            <tbody id="errorsTableBody">
            </tbody>
        </table>
    </div>
    
    <!-- Scripts -->
    <script src="https://code.jquery.com/jquery-3.7.0.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    
    <script>
        // Data
        const pagesData = {pages_json};
        const brokenData = {broken_json};
        const errorsData = {errors_json};
        const topSlowestUrls = {top_slowest_json};
        
        // Chart data
        const chartLabels = {chart_labels};
        const chartTtfb = {chart_ttfb};
        const chartFcp = {chart_fcp};
        const chartLcp = {chart_lcp};
        const chartLoad = {chart_load};
        
        // Initialize Multiline Chart
        const ctx = document.getElementById('performanceChart').getContext('2d');
        new Chart(ctx, {{
            type: 'line',
            data: {{
                labels: chartLabels,
                datasets: [
                    {{
                        label: 'TTFB (ms)',
                        data: chartTtfb,
                        borderColor: 'rgba(233, 30, 99, 1)',
                        backgroundColor: 'rgba(233, 30, 99, 0.1)',
                        tension: 0.4,
                        fill: false
                    }},
                    {{
                        label: 'FCP (ms)',
                        data: chartFcp,
                        borderColor: 'rgba(156, 39, 176, 1)',
                        backgroundColor: 'rgba(156, 39, 176, 0.1)',
                        tension: 0.4,
                        fill: false
                    }},
                    {{
                        label: 'LCP (ms)',
                        data: chartLcp,
                        borderColor: 'rgba(103, 58, 183, 1)',
                        backgroundColor: 'rgba(103, 58, 183, 0.1)',
                        tension: 0.4,
                        fill: false
                    }},
                    {{
                        label: 'Load Event (ms)',
                        data: chartLoad,
                        borderColor: 'rgba(63, 81, 181, 1)',
                        backgroundColor: 'rgba(63, 81, 181, 0.1)',
                        tension: 0.4,
                        fill: false
                    }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: true,
                plugins: {{
                    legend: {{ 
                        display: true,
                        position: 'top',
                        labels: {{
                            usePointStyle: true,
                            padding: 15
                        }}
                    }},
                    title: {{ 
                        display: true,
                        text: 'Performance Metrics Comparison (Top 10 Slowest Pages)',
                        font: {{ size: 16 }}
                    }},
                    tooltip: {{
                        mode: 'index',
                        intersect: false
                    }}
                }},
                scales: {{
                    y: {{ 
                        beginAtZero: true,
                        title: {{ display: true, text: 'Time (ms)' }}
                    }},
                    x: {{ 
                        title: {{ display: true, text: 'Pages' }},
                        ticks: {{ maxRotation: 45, minRotation: 45 }}
                    }}
                }},
                interaction: {{
                    mode: 'nearest',
                    axis: 'x',
                    intersect: false
                }}
            }}
        }});
        
        // Populate and initialize Pages Table
        const pagesRows = pagesData.map(page => {{
            const isSlow = topSlowestUrls.includes(page.url);
            const rowClass = isSlow ? 'slow-page' : '';
            return '<tr class="' + rowClass + '">' +
                '<td><a href="' + (page.url || '-') + '" target="_blank">' + (page.url || '-') + '</a></td>' +
                '<td>' + (page.title || '-') + '</td>' +
                '<td><span class="badge ' + (page.status >= 400 ? 'badge-danger' : 'badge-success') + '">' + (page.status || '-') + '</span></td>' +
                '<td>' + (page.ttfb_ms || '-') + '</td>' +
                '<td>' + (page.fcp_ms || '-') + '</td>' +
                '<td>' + (page.lcp_ms || '-') + '</td>' +
                '<td>' + (page.cls || '-') + '</td>' +
                '<td>' + (page.load_event_ms || '-') + '</td>' +
                '<td>' + (page.links_broken || 0) + '</td>' +
                '</tr>';
        }}).join('');
        
        $('#pagesTableBody').html(pagesRows);
        $('#pagesTable').DataTable({{
            order: [[7, 'desc']], // Sort by load_event_ms descending
            pageLength: 25,
            dom: 'Bfrtip',
            columnDefs: [{{
                targets: 1,
                render: function(data, type, row) {{
                    if (type === 'display' && data && data.length > 50) {{
                        return data.substring(0, 50) + '...';
                    }}
                    return data;
                }}
            }}]
        }});
        
        // Populate Broken Links Table
        const brokenRows = brokenData.map(link => 
            '<tr>' +
                '<td><a href="' + (link.source_url || '-') + '" target="_blank">' + (link.source_url || '-') + '</a></td>' +
                '<td><a href="' + (link.link_url || '-') + '" target="_blank">' + (link.link_url || '-') + '</a></td>' +
                '<td>' + (link.status || '-') + '</td>' +
                '<td>' + (link.error || '-') + '</td>' +
            '</tr>'
        ).join('');
        
        $('#brokenTableBody').html(brokenRows);
        $('#brokenTable').DataTable({{pageLength: 25}});
        
        // Populate Errors Table
        const errorsRows = errorsData.map(err =>
            '<tr>' +
                '<td><a href="' + (err.url || '-') + '" target="_blank">' + (err.url || '-') + '</a></td>' +
                '<td>' + (err.error || '-') + '</td>' +
            '</tr>'
        ).join('');
        
        $('#errorsTableBody').html(errorsRows);
        $('#errorsTable').DataTable({{pageLength: 25}});
        
        // Add tooltips to all column headers
        $(document).ready(function() {{
            const tooltipMap = {column_tooltips};
            $('#pagesTable thead th').each(function() {{
                const colName = $(this).text().trim();
                if (tooltipMap[colName]) {{
                    $(this).attr('title', tooltipMap[colName]);
                }}
            }});
        }});
    </script>
</body>
</html>"""
    
    return html


def generate_email_summary(pages_df, broken_df, errors_df, 
                           total_pages, total_links, total_broken,
                           avg_load, avg_lcp, avg_cls):
    """Generate a simple, email-friendly HTML summary."""
    
    # Get top 5 slowest pages
    slow_pages = []
    if not pages_df.empty and "load_event_ms" in pages_df.columns:
        slow_pages = pages_df.dropna(subset=["load_event_ms"]).sort_values(by="load_event_ms", ascending=False).head(5)
    
    slowest_list = ""
    if not slow_pages.empty:
        for idx, row in slow_pages.iterrows():
            slowest_list += f"""
            <tr style="background-color: #ffebee;">
                <td style="padding: 8px;">{row['url'][:80]}...</td>
                <td style="padding: 8px; text-align: right;">{int(row['load_event_ms'])} ms</td>
            </tr>"""
    
    # Get top 5 broken links
    broken_list = ""
    if not broken_df.empty:
        top_broken = broken_df.head(5)
        for idx, row in top_broken.iterrows():
            broken_list += f"""
            <tr>
                <td style="padding: 8px;">{row['link_url'][:60]}...</td>
                <td style="padding: 8px;">{row['status'] or 'Error'}</td>
            </tr>"""
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset='utf-8'>
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 20px; background-color: #f4f4f4;">
    <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1);">
        
        <!-- Header -->
        <div style="background: linear-gradient(135deg, #E91E63 0%, #9C27B0 100%); color: white; padding: 30px; margin: -20px -20px 20px -20px; border-radius: 10px 10px 0 0;">
            <h1 style="margin: 0; font-size: 24px;">🚀 Crawl Summary Report</h1>
        </div>
        
        <!-- Summary Stats -->
        <div style="margin: 20px 0;">
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 10px; background-color: #f9f9f9; border: 1px solid #ddd; width: 50%;"><strong>Total Pages Crawled:</strong></td>
                    <td style="padding: 10px; border: 1px solid #ddd; text-align: center; font-size: 18px; color: #E91E63; font-weight: bold;">{total_pages}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; background-color: #f9f9f9; border: 1px solid #ddd;"><strong>Links Checked:</strong></td>
                    <td style="padding: 10px; border: 1px solid #ddd; text-align: center;">{total_links}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; background-color: #f9f9f9; border: 1px solid #ddd;"><strong>Broken Links:</strong></td>
                    <td style="padding: 10px; border: 1px solid #ddd; text-align: center; color: {"#dc3545" if total_broken > 0 else "#28a745"}; font-weight: bold;">{total_broken}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; background-color: #f9f9f9; border: 1px solid #ddd;"><strong>Avg Load Time:</strong></td>
                    <td style="padding: 10px; border: 1px solid #ddd; text-align: center;">{'N/A' if avg_load is None else f'{avg_load} ms'}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; background-color: #f9f9f9; border: 1px solid #ddd;"><strong>Avg LCP:</strong></td>
                    <td style="padding: 10px; border: 1px solid #ddd; text-align: center;">{'N/A' if avg_lcp is None else f'{avg_lcp} ms'}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; background-color: #f9f9f9; border: 1px solid #ddd;"><strong>Avg CLS:</strong></td>
                    <td style="padding: 10px; border: 1px solid #ddd; text-align: center;">{'N/A' if avg_cls is None else f'{avg_cls}'}</td>
                </tr>
            </table>
        </div>
        
        <!-- Top 5 Slowest Pages -->
        {f'''
        <div style="margin: 30px 0;">
            <h3 style="color: #E91E63; border-bottom: 2px solid #E91E63; padding-bottom: 5px;">⏱️ Top 5 Slowest Pages</h3>
            <table style="width: 100%; border-collapse: collapse; margin-top: 10px;">
                <tr style="background-color: #f5f5f5;">
                    <th style="padding: 8px; text-align: left; border: 1px solid #ddd;">URL</th>
                    <th style="padding: 8px; text-align: right; border: 1px solid #ddd;">Load Time</th>
                </tr>
                {slowest_list}
            </table>
        </div>
        ''' if slowest_list else ''}
        
        <!-- Top 5 Broken Links -->
        {f'''
        <div style="margin: 30px 0;">
            <h3 style="color: #dc3545; border-bottom: 2px solid #dc3545; padding-bottom: 5px;">🔗 Recent Broken Links</h3>
            <table style="width: 100%; border-collapse: collapse; margin-top: 10px;">
                <tr style="background-color: #f5f5f5;">
                    <th style="padding: 8px; text-align: left; border: 1px solid #ddd;">Broken Link</th>
                    <th style="padding: 8px; text-align: center; border: 1px solid #ddd;">Status</th>
                </tr>
                {broken_list}
            </table>
        </div>
        ''' if broken_list else '<div style="margin: 30px 0;"><p>✅ No broken links found!</p></div>'}
        
        <!-- Footer -->
        <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; text-align: center; color: #666; font-size: 12px;">
            <p>This is an automated crawl summary. For detailed analysis, see the full report.</p>
        </div>
        
    </div>
</body>
</html>"""
    
    return html


# ----------------------- Core Functions -----------------------

async def build_request_context(pw, browser_context):
    """
    Create an APIRequestContext that shares cookies/storage with the browser context.
    """
    state = await browser_context.storage_state()
    return await pw.request.new_context(storage_state=state)

async def check_link(request_ctx, link_url: str, timeout_ms: int = 20000):
    """
    HEAD first; if not allowed/blocked, fallback to GET.
    Returns (status:int|None, error:str|None)
    """
    try:
        r = await request_ctx.fetch(link_url, method="HEAD", timeout=timeout_ms, max_redirects=10)
        if r is not None and r.status != 405:
            return r.status, None
    except Exception:
        pass

    try:
        r = await request_ctx.fetch(link_url, method="GET", timeout=timeout_ms, max_redirects=10)
        return (r.status if r else None), None
    except Exception as e:
        return None, str(e)

async def measure_navigation(page, url: str, timeout_ms: int = 60000):
    """
    Navigate and collect nav timing, web vitals, resource aggregates, headers, and title.
    """
    try:
        await page.add_init_script(WEB_VITALS_BOOT_JS)
    except Exception:
        pass

    resp = await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
    status = resp.status if resp else None

    # Wait for page to be fully interactive (JavaScript executed)
    # Wait for network to be idle (no requests for 500ms)
    try:
        await page.wait_for_load_state("networkidle", timeout=10000)
    except Exception:
        pass  # Timeout is okay, continue anyway
    
    # Additional wait to let dynamic content render
    await page.wait_for_timeout(2000)  # Wait 2 seconds for dynamic content

    metrics = await page.evaluate(COLLECT_METRICS_JS)
    title = await page.evaluate(GET_TITLE_JS)

    cache_control = ""
    content_encoding = ""
    try:
        if resp:
            h = await resp.all_headers()
            cache_control = h.get("cache-control", "")
            content_encoding = h.get("content-encoding", "")
    except Exception:
        pass

    timing = (metrics or {}).get("timing") or {}
    resources = (metrics or {}).get("resources") or {"count": 0, "encoded": 0, "transfer": 0, "types": {}}

    return {
        "status": status,
        "title": title,
        "ttfb_ms": timing.get("ttfb_ms"),
        "dom_content_loaded_ms": timing.get("dom_content_loaded_ms"),
        "response_end_ms": timing.get("response_end_ms"),
        "load_event_ms": timing.get("load_event_ms"),
        "fcp_ms": (metrics or {}).get("fcp_ms"),
        "lcp_ms": (metrics or {}).get("lcp_ms"),
        "cls": (metrics or {}).get("cls"),
        "inp_ms": (metrics or {}).get("inp_ms"),
        "longtask_count": (metrics or {}).get("longtask_count"),
        "longtask_total_ms": (metrics or {}).get("longtask_total_ms"),
        "req_count": resources.get("count", 0),
        "bytes_encoded": resources.get("encoded", 0),
        "bytes_transfer": resources.get("transfer", 0),
        "bytes_img": (resources.get("types", {}) or {}).get("img", 0),
        "bytes_script": (resources.get("types", {}) or {}).get("script", 0),
        "bytes_css": (resources.get("types", {}) or {}).get("css", 0),
        "bytes_font": (resources.get("types", {}) or {}).get("font", 0),
        "cache_control": cache_control,
        "content_encoding": content_encoding
    }

async def crawl(args):
    start_url = args.start_url
    user_data_dir = args.user_data_dir
    max_pages = args.max_pages
    headless = args.headless
    same_origin_only = args.same_origin_only

    print(f"🚀 Starting crawl of: {start_url}")
    print(f"📁 User data dir: {user_data_dir}")
    print(f"👁️  Headless mode: {headless}")
    print(f"📊 Max pages: {max_pages}")
    print("-" * 60)

    pages_rows = []
    broken_rows = []
    errors_rows = []

    visited = set()
    queue = [start_url]

    async with async_playwright() as p:
        print("🔧 Launching browser with Chrome profile...")
        print(f"   Profile: {user_data_dir}")
        
        # Use persistent context - this is the correct way to use Chrome profiles
        context = await p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            channel="chrome",
            headless=headless,
            args=[
                "--disable-dev-shm-usage",
                "--no-default-browser-check",
                "--no-first-run",
            ],
            ignore_default_args=["--disable-component-extensions-with-background-pages"],
        )
        print("✅ Browser with profile loaded successfully")

        # request context that shares cookies with the browser context
        print("🔧 Creating request context...")
        request_ctx = await build_request_context(p, context)
        print("✅ Request context created")

        # new tabs/pages (e.g., map views)
        new_pages_queue = []
        def on_new_page(page):
            new_pages_queue.append(page)
        context.on("page", on_new_page)

        # console error tracking (per current page)
        console_buffer = []
        def on_console(msg):
            try:
                if msg.type == "error":
                    loc = msg.location
                    console_buffer.append({
                        "text": msg.text,
                        "url": loc.get("url") if isinstance(loc, dict) else "",
                        "line": loc.get("lineNumber") if isinstance(loc, dict) else None
                    })
            except Exception:
                pass

        # Use the first page from persistent context (it comes with one)
        print("🔧 Getting default page from context...")
        page = context.pages[0] if context.pages else await context.new_page()
        page.on("console", on_console)
        print(f"✅ Using page: {len(context.pages)} page(s) available")

        print(f"\n🚀 Starting crawl loop. Queue has {len(queue)} URL(s).")
        i = 0
        while queue and i < max_pages:
            url = queue.pop(0)
            if url in visited:
                continue
            visited.add(url)
            
            print(f"\n[{i+1}/{max_pages}] Crawling: {url}")

            # reset console error buffer for this page
            console_buffer.clear()

            try:
                # Check if page is still valid
                if page.is_closed():
                    print(f"  ⚠️ Page was closed, stopping crawl")
                    break
                    
                # Navigate & measure
                print(f"  📍 Navigating to page...")
                metrics = await measure_navigation(page, url)
                print(f"  ✓ Page loaded")
                status = metrics["status"]
                title = metrics["title"]

                # Collect links
                raw_links = await page.evaluate(GET_LINKS_JS)
                print(f"  🔗 Found {len(raw_links)} raw links")
                
                # Debug info for first page
                if i == 0:
                    debug_info = await page.evaluate(DEBUG_PAGE_CONTENT_JS)
                    print(f"  🔍 Debug: Total <a> tags: {debug_info['totalLinks']}")
                    print(f"  🔍 Debug: Links with href: {debug_info['linksWithHref']}")
                    print(f"  🔍 Debug: Links without href: {debug_info['linksWithoutHref']}")
                    if debug_info['sampleLinks']:
                        print(f"  🔍 Debug: Sample links:")
                        for link in debug_info['sampleLinks'][:3]:
                            print(f"     - '{link['text'][:30]}' -> {link['href'][:80]}")
                abs_links = []
                for href in raw_links:
                    abs_url = normalize_link(url, href)
                    if not abs_url:
                        continue
                    if same_origin_only and not same_origin(url, abs_url):
                        continue
                    abs_links.append(abs_url)

                # Check links (broken detection) + enqueue new internal targets
                broken_count = 0
                checked_count = 0
                for link in sorted(set(abs_links)):
                    checked_count += 1
                    s, err = await check_link(request_ctx, link)
                    if s is None or s >= 400:
                        broken_count += 1
                        broken_rows.append({
                            "source_url": url,
                            "link_url": link,
                            "status": s,
                            "error": (err or "")
                        })
                    # enqueue crawl target
                    if link not in visited and link not in queue and (not same_origin_only or same_origin(url, link)):
                        queue.append(link)

                # Count console errors observed while loading this page
                console_err_count = len(console_buffer)
                # Optionally record last few in Errors sheet for reference
                tail = console_buffer[-3:] if console_buffer else []
                for e in tail:
                    errors_rows.append({"url": url, "error": f"console: {e.get('text','')}"})

                # record page row
                pages_rows.append({
                    "url": url,
                    "title": title,
                    "status": status,
                    "ttfb_ms": metrics["ttfb_ms"],
                    "fcp_ms": metrics["fcp_ms"],
                    "lcp_ms": metrics["lcp_ms"],
                    "cls": metrics["cls"],
                    "inp_ms": metrics["inp_ms"],
                    "dom_content_loaded_ms": metrics["dom_content_loaded_ms"],
                    "response_end_ms": metrics["response_end_ms"],
                    "load_event_ms": metrics["load_event_ms"],
                    "req_count": metrics["req_count"],
                    "bytes_encoded": metrics["bytes_encoded"],
                    "bytes_transfer": metrics["bytes_transfer"],
                    "bytes_img": metrics["bytes_img"],
                    "bytes_script": metrics["bytes_script"],
                    "bytes_css": metrics["bytes_css"],
                    "bytes_font": metrics["bytes_font"],
                    "console_errors": console_err_count,
                    "cache_control": metrics["cache_control"],
                    "content_encoding": metrics["content_encoding"],
                    "links_checked": checked_count,
                    "links_broken": broken_count,
                })

                i += 1
                print(f"  ✓ Found {len(set(abs_links))} unique links, {broken_count} broken")

                # Handle any pages opened in new tabs (enqueue their URL)
                while new_pages_queue:
                    np = new_pages_queue.pop(0)
                    try:
                        await np.wait_for_load_state("load", timeout=60000)
                        new_url = np.url
                        if new_url and new_url not in visited and (not same_origin_only or same_origin(url, new_url)):
                            queue.append(new_url)
                    except Exception:
                        pass
                    finally:
                        try:
                            await np.close()
                        except Exception:
                            pass

            except Exception as e:
                print(f"  ✗ Error crawling this page: {type(e).__name__}: {str(e)}")
                errors_rows.append({"url": url, "error": str(e)})

        print(f"\n⏹️  Crawl completed. Visited {len(visited)} pages.")
        print("🔧 Closing browser and cleaning up...")
        await context.close()
        await request_ctx.dispose()

    # ----------------------- Export: Excel -----------------------
    # Save outputs in the same directory as this script
    script_dir = Path(__file__).parent
    excel_path = script_dir / "crawl_results.xlsx"
    html_path = script_dir / "crawl_report.html"
    
    pages_df  = pd.DataFrame(pages_rows)
    broken_df = pd.DataFrame(broken_rows)
    errors_df = pd.DataFrame(errors_rows)

    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        pages_df.to_excel(writer,  sheet_name="Pages",       index=False)
        broken_df.to_excel(writer, sheet_name="BrokenLinks", index=False)
        errors_df.to_excel(writer, sheet_name="Errors",      index=False)

    # ----------------------- KPI Chart -----------------------
    img_b64 = ""
    if not pages_df.empty and "load_event_ms" in pages_df.columns:
        slow = pages_df.dropna(subset=["load_event_ms"]).sort_values(by="load_event_ms", ascending=False).head(10)[["url","load_event_ms"]]
        if not slow.empty:
            plt.figure(figsize=(10,5))
            plt.bar(range(len(slow)), slow["load_event_ms"])
            plt.xticks(range(len(slow)), [str(i+1) for i in range(len(slow))])
            plt.title("Top 10 Slowest Pages (by Load Event)")
            plt.ylabel("Load (ms)")
            buf = io.BytesIO()
            plt.tight_layout()
            plt.savefig(buf, format="png")
            buf.seek(0)
            img_b64 = base64.b64encode(buf.read()).decode("ascii")
            plt.close()

    # ----------------------- Export: HTML -----------------------
    total_pages  = len(pages_df)
    total_links  = int(pages_df["links_checked"].sum()) if not pages_df.empty else 0
    total_broken = int(pages_df["links_broken"].sum()) if not pages_df.empty else 0

    avg_load = int(pages_df["load_event_ms"].mean()) if ("load_event_ms" in pages_df and not pages_df["load_event_ms"].isna().all()) else None
    avg_lcp  = int(pages_df["lcp_ms"].mean()) if ("lcp_ms" in pages_df and not pages_df["lcp_ms"].isna().all()) else None
    avg_cls  = round(float(pages_df["cls"].mean()), 3) if ("cls" in pages_df and not pages_df["cls"].isna().all()) else None
    
    # Find top 10 slowest pages for highlighting
    top_slowest = []
    if not pages_df.empty and "load_event_ms" in pages_df.columns:
        slow_pages = pages_df.dropna(subset=["load_event_ms"]).sort_values(by="load_event_ms", ascending=False).head(10)
        top_slowest = slow_pages["url"].tolist()

    # Prepare data for charts
    chart_data = []
    if not pages_df.empty and "load_event_ms" in pages_df.columns:
        chart_data = pages_df.dropna(subset=["load_event_ms"]).sort_values(by="load_event_ms", ascending=False).head(10)

    # Generate HTML with advanced features
    html = generate_advanced_html_report(pages_df, broken_df, errors_df, 
                                           total_pages, total_links, total_broken, 
                                           avg_load, avg_lcp, avg_cls, 
                                           chart_data, top_slowest)

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    
    # Generate email summary
    script_dir = Path(__file__).parent
    email_html_path = script_dir / "crawl_email_summary.html"
    email_html = generate_email_summary(pages_df, broken_df, errors_df,
                                        total_pages, total_links, total_broken,
                                        avg_load, avg_lcp, avg_cls)
    
    with open(email_html_path, "w", encoding="utf-8") as f:
        f.write(email_html)


# ----------------------- CLI -----------------------

def parse_args():
    ap = argparse.ArgumentParser(description="SSO-aware site crawler using Playwright + Chrome profile.")
    ap.add_argument("--start-url", required=True, help="Seed URL to start crawling.")
    ap.add_argument("--user-data-dir", required=True, help="Path to Chrome user data dir (profile) to reuse SSO.")
    ap.add_argument("--max-pages", type=int, default=10, help="Max number of pages to visit.")
    ap.add_argument("--headless", type=lambda x: x.lower() == "true", default=True, help="Run headless (true/false).")
    ap.add_argument("--same-origin-only", type=lambda x: x.lower() == "true", default=True,
                    help="Restrict crawl and link checks to same origin (true/false).")
    return ap.parse_args()


if __name__ == "__main__":
    import traceback
    args = parse_args()
    try:
        asyncio.run(crawl(args))
        script_dir = Path(__file__).parent
        excel_path = script_dir / "crawl_results.xlsx"
        html_path = script_dir / "crawl_report.html"
        email_path = script_dir / "crawl_email_summary.html"
        print("\n✓ Crawl completed successfully!")
        print(f"✓ Results saved to: {excel_path}")
        print(f"✓ Full report saved to: {html_path}")
        print(f"✓ Email summary saved to: {email_path}")
    except KeyboardInterrupt:
        print("\n⚠ Crawl interrupted by user")
    except Exception as e:
        print(f"\n✗ Error occurred: {type(e).__name__}")
        print(f"  Message: {str(e)}")
        print("\nFull traceback:")
        traceback.print_exc()
