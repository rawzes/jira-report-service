"""
HTML Styles module for Jira Report application.

This module contains the CSS styles used in the HTML report generation.
"""


def get_css() -> str:
    """
    Return CSS styles for the HTML report.
    
    Returns:
        String containing all CSS styles for the report
    """
    return """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f7fa;
            padding: 20px;
            color: #333;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
            padding: 40px;
        }
        h1 {
            color: #2c3e50;
            margin-bottom: 10px;
            font-size: 32px;
        }
        .subtitle {
            color: #7f8c8d;
            margin-bottom: 30px;
            font-size: 16px;
        }
        .share-link {
            background: #e8f4f8;
            border: 1px solid #3498db;
            border-radius: 6px;
            padding: 10px 15px;
            margin-bottom: 20px;
            font-size: 14px;
            word-break: break-all;
        }
        .share-link a {
            color: #3498db;
            text-decoration: none;
        }
        .share-link a:hover {
            text-decoration: underline;
        }
        h2 {
            color: #34495e;
            margin-top: 40px;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #3498db;
            font-size: 24px;
        }
        h3 {
            color: #555;
            margin-top: 20px;
            margin-bottom: 15px;
            font-size: 18px;
        }
        
        /* Tab Navigation */
        .tab-navigation {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin: 20px 0 30px 0;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 8px;
            border: 1px solid #e0e0e0;
            position: sticky;
            top: 0;
            z-index: 100;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }
        .tab-button {
            padding: 10px 18px;
            background: white;
            border: 1px solid #ddd;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            color: #555;
            transition: all 0.3s;
        }
        .tab-button:hover {
            background: #e8f4f8;
            border-color: #3498db;
            transform: translateY(-1px);
        }
        .tab-button.active {
            background: #3498db;
            color: white;
            border-color: #3498db;
            box-shadow: 0 2px 4px rgba(52, 152, 219, 0.3);
        }
        .tab-content {
            display: none;
            opacity: 0;
            transition: opacity 0.3s ease-in;
        }
        .tab-content.active {
            display: block;
            opacity: 1;
            animation: fadeIn 0.3s ease-in;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        /* Table Responsive Wrapper with improved styling */
        .table-responsive {
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
            margin-bottom: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            border: 1px solid #e0e0e0;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            min-width: 800px;
        }
        th {
            background: #3498db;
            color: white;
            padding: 14px 16px;
            text-align: left;
            font-weight: 600;
            font-size: 13px;
            white-space: nowrap;
            position: sticky;
            top: 0;
            z-index: 10;
        }
        td {
            padding: 12px 16px;
            border-bottom: 1px solid #ecf0f1;
            font-size: 13px;
            max-width: 250px;
            word-wrap: break-word;
            overflow-wrap: break-word;
        }
        tr:nth-child(even) {
            background: #f8f9fa;
        }
        tr:hover {
            background: #e8f4f8;
            transition: background 0.2s;
        }
        .total-row {
            font-weight: bold;
            background: #d0d0d0 !important;
        }
        a {
            color: #3498db;
            text-decoration: none;
            transition: color 0.2s;
        }
        a:hover {
            text-decoration: underline;
            color: #2980b9;
        }
        .metric-card {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 15px;
            border-left: 4px solid #3498db;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .metric-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }
        .metric-label {
            color: #7f8c8d;
            font-size: 14px;
            margin-bottom: 5px;
        }
        .metric-value {
            color: #2c3e50;
            font-size: 28px;
            font-weight: bold;
        }
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }
        .chart-container {
            width: 100%;
            max-width: 900px;
            height: 450px;
            margin: 20px 0;
            position: relative;
        }
        .chart-container canvas {
            width: 100% !important;
            height: 100% !important;
        }
        .no-data {
            color: #7f8c8d;
            font-style: italic;
            padding: 20px;
            text-align: center;
        }
        
        /* Responsive improvements */
        @media (max-width: 768px) {
            .container {
                padding: 20px;
            }
            h1 {
                font-size: 24px;
            }
            .tab-button {
                padding: 8px 12px;
                font-size: 12px;
            }
            .metrics-grid {
                grid-template-columns: 1fr;
            }
            table {
                min-width: 600px;
            }
        }
        
        /* Download button */
        .download-btn {
            background: #3498db;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            margin: 20px 0;
            transition: all 0.3s;
            display: inline-block;
        }
        .download-btn:hover {
            background: #2980b9;
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(52, 152, 219, 0.4);
        }
"""
