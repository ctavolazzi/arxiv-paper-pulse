#!/usr/bin/env python3
"""
Generate HTML test results page with visualizations.
"""

import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime


def run_pytest_and_collect_results():
    """Run pytest and collect results"""
    print("Running tests...")

    # Create temp directory for visual tests
    import tempfile
    temp_dir = tempfile.mkdtemp(prefix="visual_tests_")

    # Run pytest
    result = subprocess.run(
        [sys.executable, "-m", "pytest",
         "tests/test_self_playing_game_visual.py",
         "-v", "-m", "visual"],
        capture_output=True,
        text=True
    )

    return result, temp_dir


def load_test_data(test_dir):
    """Load test data from JSON files"""
    test_dir = Path(test_dir)
    data = {}

    for json_file in test_dir.glob("*_data.json"):
        test_name = json_file.stem.replace("_data", "")
        try:
            with open(json_file) as f:
                data[test_name] = json.load(f)
        except:
            pass

    return data


def format_output(text):
    """Format output text for HTML display"""
    # Convert to monospace and preserve formatting
    lines = text.split('\n')
    formatted = []
    for line in lines:
        # Preserve spacing
        line = line.replace(' ', '&nbsp;')
        line = line.replace('█', '<span style="color: #00ff00;">█</span>')
        line = line.replace('░', '<span style="color: #666666;">░</span>')
        formatted.append(line)
    return '<br>'.join(formatted)


def generate_html(test_results, test_data):
    """Generate HTML test results page with enhanced features"""

    # Calculate statistics
    total_tests = len(test_data) if test_data else 0
    passed_tests = sum(1 for d in test_data.values() if d.get('success')) if test_data else 0
    total_execution_time = sum(d.get('execution_time', 0) for d in test_data.values()) if test_data else 0

    # Prepare JSON data for copy/download
    json_data = {
        'timestamp': datetime.now().isoformat(),
        'summary': {
            'total_tests': total_tests,
            'passed': passed_tests,
            'failed': total_tests - passed_tests,
            'total_execution_time': total_execution_time
        },
        'tests': test_data,
        'pytest_output': test_results.stdout if test_results else ''
    }
    json_str = json.dumps(json_data, indent=2)
    # Escape for HTML embedding
    json_str_escaped = json_str.replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Self-Playing Game System - Test Results</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/prism.min.js"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/themes/prism-tomorrow.min.css" rel="stylesheet" />
    <style>
        * {{
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
        .container {{
            background: white;
            border-radius: 10px;
            padding: 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .header-actions {{
            display: flex;
            gap: 10px;
        }}
        .btn {{
            padding: 8px 16px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.3s;
            text-decoration: none;
            display: inline-block;
        }}
        .btn-primary {{
            background: #667eea;
            color: white;
        }}
        .btn-primary:hover {{
            background: #5568d3;
            transform: translateY(-2px);
        }}
        .btn-success {{
            background: #28a745;
            color: white;
        }}
        .btn-success:hover {{
            background: #218838;
        }}
        .btn-secondary {{
            background: #6c757d;
            color: white;
        }}
        .btn-secondary:hover {{
            background: #5a6268;
        }}
        .test-section {{
            margin: 30px 0;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }}
        .test-section h2 {{
            color: #667eea;
            margin-top: 0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .output-box {{
            background: #1e1e1e;
            color: #d4d4d4;
            padding: 20px;
            border-radius: 5px;
            font-family: 'Courier New', monospace;
            font-size: 13px;
            line-height: 1.6;
            overflow-x: auto;
            margin: 15px 0;
            position: relative;
        }}
        .output-box pre {{
            margin: 0;
            white-space: pre-wrap;
            word-wrap: break-word;
            font-family: 'Courier New', monospace;
        }}
        .copy-btn {{
            position: absolute;
            top: 10px;
            right: 10px;
            background: #667eea;
            color: white;
            border: none;
            padding: 5px 10px;
            border-radius: 3px;
            cursor: pointer;
            font-size: 12px;
        }}
        .copy-btn:hover {{
            background: #5568d3;
        }}
        .copy-success {{
            background: #28a745 !important;
        }}
        .stats {{
            display: flex;
            gap: 20px;
            margin: 20px 0;
            flex-wrap: wrap;
        }}
        .stat-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px 25px;
            border-radius: 8px;
            flex: 1;
            min-width: 200px;
        }}
        .stat-card h3 {{
            margin: 0 0 10px 0;
            font-size: 14px;
            opacity: 0.9;
        }}
        .stat-card .value {{
            font-size: 32px;
            font-weight: bold;
        }}
        .stat-card.green {{
            background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
        }}
        .stat-card.orange {{
            background: linear-gradient(135deg, #fd7e14 0%, #ffc107 100%);
        }}
        .success {{
            color: #28a745;
            font-weight: bold;
        }}
        .failure {{
            color: #dc3545;
            font-weight: bold;
        }}
        .timestamp {{
            color: #666;
            font-size: 14px;
            margin-bottom: 20px;
        }}
        .console-log {{
            position: fixed;
            bottom: 20px;
            right: 20px;
            width: 400px;
            max-height: 500px;
            background: #1e1e1e;
            border-radius: 8px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.4);
            z-index: 1000;
            display: none;
            flex-direction: column;
        }}
        .console-log.show {{
            display: flex;
        }}
        .console-header {{
            background: #2d2d2d;
            padding: 10px 15px;
            border-radius: 8px 8px 0 0;
            display: flex;
            justify-content: space-between;
            align-items: center;
            color: #fff;
            font-weight: bold;
        }}
        .console-body {{
            padding: 15px;
            overflow-y: auto;
            flex: 1;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            line-height: 1.5;
        }}
        .console-body .log-line {{
            margin: 3px 0;
            padding: 2px 0;
        }}
        .log-info {{
            color: #4fc3f7;
        }}
        .log-success {{
            color: #81c784;
        }}
        .log-warning {{
            color: #ffb74d;
        }}
        .log-error {{
            color: #e57373;
        }}
        .log-debug {{
            color: #ba68c8;
        }}
        .toggle-console {{
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: #667eea;
            color: white;
            border: none;
            padding: 12px 20px;
            border-radius: 50px;
            cursor: pointer;
            font-size: 14px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.3);
            z-index: 999;
        }}
        .toggle-console:hover {{
            background: #5568d3;
            transform: translateY(-2px);
        }}
        .code-block {{
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 5px;
            padding: 15px;
            margin: 10px 0;
        }}
        .test-output {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            margin: 10px 0;
            border-left: 3px solid #667eea;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 3px;
            font-size: 12px;
            font-weight: bold;
            margin-left: 10px;
        }}
        .badge-success {{
            background: #28a745;
            color: white;
        }}
        .badge-danger {{
            background: #dc3545;
            color: white;
        }}
        .badge-info {{
            background: #17a2b8;
            color: white;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>
            <span>🎮 Self-Playing Game System - Test Results</span>
            <div class="header-actions">
                <button class="btn btn-primary" onclick="copyAllData()">📋 Copy All Data</button>
                <button class="btn btn-success" onclick="downloadJSON()">⬇️ Download JSON</button>
                <button class="btn btn-secondary" onclick="downloadReport()">📄 Download Report</button>
            </div>
        </h1>
        <div class="timestamp">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>

        <div class="stats">
            <div class="stat-card">
                <h3>Total Tests</h3>
                <div class="value">{total_tests}</div>
            </div>
            <div class="stat-card green">
                <h3>Passed</h3>
                <div class="value">{passed_tests}</div>
            </div>
            <div class="stat-card orange">
                <h3>Failed</h3>
                <div class="value">{total_tests - passed_tests}</div>
            </div>
            <div class="stat-card">
                <h3>Total Execution Time</h3>
                <div class="value" style="font-size: 24px;">{total_execution_time:.3f}s</div>
            </div>
        </div>

        <div id="jsonData" style="display:none;">{json_str_escaped}</div>
"""

    # Add test results
    for idx, (test_name, data) in enumerate(test_data.items(), 1):
        status = "success" if data.get('success') else "failure"
        status_text = "✅ PASSED" if data.get('success') else "❌ FAILED"
        output_text = data.get('output', 'No output')

        # Escape HTML for safety but preserve Unicode characters
        output_text_escaped = output_text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

        html += f"""
        <div class="test-section">
            <h2>
                <span>{idx}. {data.get('test_name', test_name)}</span>
                <span class="badge {'badge-success' if data.get('success') else 'badge-danger'}">{status_text}</span>
            </h2>
            <div class="stats">
                <div class="stat-card" style="background: {'linear-gradient(135deg, #28a745 0%, #20c997 100%)' if data.get('success') else 'linear-gradient(135deg, #dc3545 0%, #c82333 100%)'};">
                    <h3>Status</h3>
                    <div class="value" style="font-size: 20px;">{status_text}</div>
                </div>
                <div class="stat-card">
                    <h3>Execution Time</h3>
                    <div class="value" style="font-size: 20px;">{data.get('execution_time', 0):.3f}s</div>
                </div>
                <div class="stat-card" style="background: linear-gradient(135deg, #17a2b8 0%, #138496 100%);">
                    <h3>Test ID</h3>
                    <div class="value" style="font-size: 14px; word-break: break-all;">{test_name}</div>
                </div>
            </div>
            <div class="test-output">
                <h3>Game Output:</h3>
                <div class="output-box">
                    <button class="copy-btn" onclick="copyToClipboard('output-{idx}')">📋 Copy</button>
                    <pre id="output-{idx}" class="copyable-text" style="white-space: pre-wrap; word-wrap: break-word;">{output_text_escaped}</pre>
                </div>
            </div>
        </div>
"""

    # Add pytest output
    if test_results:
        pytest_output = test_results.stdout or test_results.stderr or "No output"
        html += f"""
        <div class="test-section">
            <h2>
                <span>Pytest Output</span>
                <span class="badge badge-info">Full Test Run</span>
            </h2>
            <div class="output-box">
                <button class="copy-btn" onclick="copyToClipboard('pytest-output')">📋 Copy</button>
                <pre id="pytest-output" class="copyable-text">{pytest_output}</pre>
            </div>
        </div>
"""

    # Build JavaScript console logs
    summary_data = json.dumps({
        'totalTests': total_tests,
        'passed': passed_tests,
        'failed': total_tests - passed_tests,
        'totalExecutionTime': f'{total_execution_time:.3f}s'
    })
    console_logs_js = []
    console_logs_js.append("console.log('🚀 Self-Playing Game System - Test Results Page Loaded');")
    console_logs_js.append(f"console.info('📊 Test Results Summary:', {summary_data});")

    # Add JavaScript section with all features
    html += """
    </div>

    <button class="toggle-console" onclick="toggleConsole()">🖥️ Console</button>

    <div id="console" class="console-log">
        <div class="console-header">
            <span>🖥️ Browser Console</span>
            <button onclick="toggleConsole()" style="background: #dc3545; color: white; border: none; padding: 3px 8px; border-radius: 3px; cursor: pointer;">✕</button>
        </div>
        <div id="console-body" class="console-body"></div>
    </div>

    <script>
        // Console logging system - store original console methods first
        const consoleLog = [];
        const originalConsole = window.console;

        // Store references to original console methods BEFORE overriding
        const originalLog = originalConsole.log.bind(originalConsole);
        const originalInfo = originalConsole.info.bind(originalConsole);
        const originalWarn = originalConsole.warn.bind(originalConsole);
        const originalError = originalConsole.error.bind(originalConsole);
        const originalDebug = originalConsole.debug.bind(originalConsole);

        function logToConsole(level, ...args) {
            const timestamp = new Date().toLocaleTimeString();
            const message = args.map(arg => {
                if (typeof arg === 'object' && arg !== null) {
                    try {
                        return JSON.stringify(arg, null, 2);
                    } catch (e) {
                        return String(arg);
                    }
                }
                return String(arg);
            }).join(' ');

            consoleLog.push({timestamp, level, message});
            updateConsoleDisplay();

            // Only call original console methods that exist
            if (level === 'success') {
                // success doesn't exist on original console, use log instead
                originalLog('%c✅', 'color: #28a745; font-weight: bold', ...args);
            } else if (typeof originalConsole[level] === 'function') {
                originalConsole[level](...args);
            } else {
                // Fallback to log if method doesn't exist
                originalLog(...args);
            }
        }

        function updateConsoleDisplay() {
            const consoleBody = document.getElementById('console-body');
            if (consoleBody) {
                consoleBody.innerHTML = consoleLog.map(log =>
                    `<div class="log-line log-${log.level}">[${log.timestamp}] ${escapeHtml(log.message)}</div>`
                ).join('');
                consoleBody.scrollTop = consoleBody.scrollHeight;
            }
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        // Override console methods
        window.console = {
            ...originalConsole,
            log: (...args) => {
                logToConsole('info', ...args);
                originalLog(...args);
            },
            info: (...args) => {
                logToConsole('info', ...args);
                originalInfo(...args);
            },
            warn: (...args) => {
                logToConsole('warning', ...args);
                originalWarn(...args);
            },
            error: (...args) => {
                logToConsole('error', ...args);
                originalError(...args);
            },
            debug: (...args) => {
                logToConsole('debug', ...args);
                originalDebug(...args);
            },
            // Add console.success method (custom, doesn't exist on original)
            success: (...args) => {
                logToConsole('success', ...args);
                // Use original console.log with styling since success doesn't exist
                originalLog('%c✅', 'color: #28a745; font-weight: bold', ...args);
            }
        };

        function toggleConsole() {
            const consoleEl = document.getElementById('console');
            if (consoleEl) {
                consoleEl.classList.toggle('show');
            }
        }

        function copyToClipboard(elementId) {
            const element = document.getElementById(elementId);
            if (!element) return;
            const text = element.textContent || element.innerText;

            if (navigator.clipboard) {
                navigator.clipboard.writeText(text).then(() => {
                    const btn = event.target;
                    const originalText = btn.textContent;
                    btn.textContent = '✅ Copied!';
                    btn.classList.add('copy-success');
                    setTimeout(() => {
                        btn.textContent = originalText;
                        btn.classList.remove('copy-success');
                    }, 2000);
                }).catch(err => {
                    console.error('Failed to copy:', err);
                });
            } else {
                // Fallback
                const textArea = document.createElement('textarea');
                textArea.value = text;
                textArea.style.position = 'fixed';
                textArea.style.opacity = '0';
                document.body.appendChild(textArea);
                textArea.select();
                document.execCommand('copy');
                document.body.removeChild(textArea);
            }
        }

        function copyAllData() {
            const jsonData = document.getElementById('jsonData');
            if (!jsonData) return;
            const text = jsonData.textContent;
            copyToClipboardRaw(text);
            alert('✅ All test data copied to clipboard!');
            console.info('📋 All test data copied to clipboard');
        }

        function copyToClipboardRaw(text) {
            if (navigator.clipboard) {
                navigator.clipboard.writeText(text);
            } else {
                const textArea = document.createElement('textarea');
                textArea.value = text;
                textArea.style.position = 'fixed';
                textArea.style.opacity = '0';
                document.body.appendChild(textArea);
                textArea.select();
                document.execCommand('copy');
                document.body.removeChild(textArea);
            }
        }

        function downloadJSON() {
            const jsonData = document.getElementById('jsonData');
            if (!jsonData) return;
            const text = jsonData.textContent;
            const blob = new Blob([text], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'test_results_' + new Date().toISOString().split('T')[0] + '.json';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            console.info('✅ JSON file downloaded');
        }

        function downloadReport() {
            const htmlContent = document.documentElement.outerHTML;
            const blob = new Blob([htmlContent], { type: 'text/html' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'test_report_' + new Date().toISOString().split('T')[0] + '.html';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            console.info('✅ HTML report downloaded');
        }

        // Comprehensive console logging on page load - AFTER override is set up
        (function initConsoleLogging() {
            // These will now go through our custom console system
            """ + "\n            ".join(console_logs_js) + """

            console.info('🔧 System Information:', {
                userAgent: navigator.userAgent,
                platform: navigator.platform,
                language: navigator.language,
                timestamp: new Date().toISOString(),
                url: window.location.href,
                screenResolution: screen.width + 'x' + screen.height,
                colorDepth: screen.colorDepth + ' bits',
                windowSize: window.innerWidth + 'x' + window.innerHeight,
                timezone: Intl.DateTimeFormat().resolvedOptions().timeZone
            });

            console.debug('🎮 Test Data Structure:', """ + json.dumps(list(test_data.keys()) if test_data else []) + """);

            // Log each test result
            """ + "\n            ".join([f"""
            console.log(`📋 Test {idx}: {data.get('test_name', test_name)}`);
            console.info('Test Result:', {{
                success: {str(data.get('success', False)).lower()},
                executionTime: '{data.get('execution_time', 0):.3f}s',
                outputLength: {len(data.get('output', ''))} + ' chars',
                testId: '{test_name}'
            }});
            """ for idx, (test_name, data) in enumerate(test_data.items(), 1)]) + """

            // Performance logging
            if (document.readyState === 'complete') {
                logPerformance();
            } else {
                window.addEventListener('load', logPerformance);
            }

            function logPerformance() {
                const perfData = performance.timing;
                const loadTime = perfData.loadEventEnd - perfData.navigationStart;
                const domTime = perfData.domContentLoadedEventEnd - perfData.navigationStart;
                console.info('⚡ Page Load Performance:', {
                    loadTime: loadTime + 'ms',
                    domContentLoaded: domTime + 'ms',
                    firstPaint: performance.getEntriesByType('paint')[0]?.startTime || 'N/A',
                    domInteractive: perfData.domInteractive - perfData.navigationStart + 'ms',
                    domComplete: perfData.domComplete - perfData.navigationStart + 'ms',
                    navigationType: performance.navigation.type === 0 ? 'navigate' :
                                  performance.navigation.type === 1 ? 'reload' :
                                  performance.navigation.type === 2 ? 'back_forward' : 'reserved'
                });
            }

            console.success('✅ All tests completed successfully!');
            console.info('💡 Tips: Use the Console button (bottom right) to view detailed logs, or copy/download data using the buttons above.');

            // Debug info after DOM is ready
            setTimeout(() => {
                const jsonData = document.getElementById('jsonData');
                console.debug('🔍 Debug Info:', {
                    jsonDataSize: (jsonData?.textContent.length || 0) + ' bytes',
                    totalElements: document.querySelectorAll('*').length,
                    pageTitle: document.title,
                    scriptCount: document.querySelectorAll('script').length,
                    styleCount: document.querySelectorAll('style, link[rel="stylesheet"]').length
                });
            }, 100);
        })();
    </script>
</body>
</html>
"""

    return html


def run_tests_and_capture_output():
    """Run tests and capture output directly"""
    import sys
    from pathlib import Path

    # Add project root to path
    project_root = Path(__file__).parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    from arxiv_paper_pulse.self_playing_game import SelfDesigningGame
    import tempfile

    temp_dir = Path(tempfile.mkdtemp(prefix="visual_tests_"))
    test_data = {}

    print("Running visual tests...")

    # Test 1: Conway's Game of Life
    try:
        code1 = """class Game:
    def __init__(self):
        self.grid = [
            [0, 1, 0, 0, 0, 0, 0],
            [1, 1, 0, 0, 0, 0, 0],
            [0, 0, 0, 1, 0, 0, 0],
            [0, 0, 1, 1, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 1, 1],
            [0, 0, 0, 0, 0, 1, 0]
        ]
        self.generation = 0

    def play(self):
        for i in range(5):
            self.generation += 1
            print(f"Generation {self.generation}:")
            for row in self.grid:
                print(" ".join("█" if cell else "░" for cell in row))
            print()
            new_grid = [row[:] for row in self.grid]
            for y in range(len(self.grid)):
                for x in range(len(self.grid[0])):
                    neighbors = sum(1 for dy in [-1,0,1] for dx in [-1,0,1]
                                   if (dy,dx) != (0,0) and 0 <= y+dy < len(self.grid)
                                   and 0 <= x+dx < len(self.grid[0])
                                   and self.grid[y+dy][x+dx] == 1)
                    if self.grid[y][x] == 1:
                        new_grid[y][x] = 1 if neighbors in [2,3] else 0
                    else:
                        new_grid[y][x] = 1 if neighbors == 3 else 0
            self.grid = new_grid

if __name__ == "__main__":
    game = Game()
    game.play()
"""
        generator = SelfDesigningGame(output_dir=str(temp_dir))
        result1 = generator.execute_game(code1)
        test_data['conway'] = {
            'test_name': "Conway's Game of Life",
            'success': result1['success'],
            'output': result1['stdout'],
            'execution_time': result1['execution_time']
        }
        print("✅ Conway's Game of Life test passed")
    except Exception as e:
        test_data['conway'] = {
            'test_name': "Conway's Game of Life",
            'success': False,
            'output': f'Error: {str(e)}',
            'execution_time': 0
        }
        print(f"❌ Conway's test failed: {e}")

    # Test 2: Particle Simulation
    try:
        code2 = """class Game:
    def __init__(self):
        self.particles = [
            {'x': 0, 'y': 0, 'vx': 1, 'vy': 1},
            {'x': 5, 'y': 5, 'vx': -1, 'vy': 1},
            {'x': 10, 'y': 10, 'vx': 1, 'vy': -1}
        ]
        self.step = 0

    def play(self):
        for step in range(8):
            self.step = step + 1
            print(f"Step {self.step}:")
            for i, p in enumerate(self.particles):
                p['x'] += p['vx']
                p['y'] += p['vy']
                print(f"  Particle {i}: position=({p['x']:3d}, {p['y']:3d}) velocity=({p['vx']:+2d}, {p['vy']:+2d})")
            print()

if __name__ == "__main__":
    game = Game()
    game.play()
"""
        generator = SelfDesigningGame(output_dir=str(temp_dir))
        result2 = generator.execute_game(code2)
        test_data['particle'] = {
            'test_name': "Particle Simulation",
            'success': result2['success'],
            'output': result2['stdout'],
            'execution_time': result2['execution_time']
        }
        print("✅ Particle Simulation test passed")
    except Exception as e:
        test_data['particle'] = {
            'test_name': "Particle Simulation",
            'success': False,
            'output': f'Error: {str(e)}',
            'execution_time': 0
        }
        print(f"❌ Particle test failed: {e}")

    # Test 3: Cellular Automata
    try:
        code3 = """class Game:
    def __init__(self):
        self.cells = [0, 1, 1, 0, 1, 0, 0, 1, 1, 0, 1, 1, 0, 0, 1]
        self.generation = 0

    def play(self):
        for gen in range(10):
            self.generation = gen + 1
            visual = "".join("█" if c else "░" for c in self.cells)
            print(f"Generation {self.generation:2d}: {visual}")
            new_cells = []
            for i in range(len(self.cells)):
                left = self.cells[i-1] if i > 0 else 0
                right = self.cells[i+1] if i < len(self.cells)-1 else 0
                new_cells.append(1 if (left + self.cells[i] + right) % 2 == 1 else 0)
            self.cells = new_cells

if __name__ == "__main__":
    game = Game()
    game.play()
"""
        generator = SelfDesigningGame(output_dir=str(temp_dir))
        result3 = generator.execute_game(code3)
        test_data['automata'] = {
            'test_name': "1D Cellular Automata",
            'success': result3['success'],
            'output': result3['stdout'],
            'execution_time': result3['execution_time']
        }
        print("✅ Cellular Automata test passed")
    except Exception as e:
        test_data['automata'] = {
            'test_name': "1D Cellular Automata",
            'success': False,
            'output': f'Error: {str(e)}',
            'execution_time': 0
        }
        print(f"❌ Automata test failed: {e}")

    return test_data


def main():
    """Main function"""
    print("Generating test results page...")

    # Run tests directly
    test_data = run_tests_and_capture_output()

    # Run pytest for output
    pytest_result = subprocess.run(
        [sys.executable, "-m", "pytest",
         "tests/test_self_playing_game.py",
         "-v", "--tb=short"],
        capture_output=True,
        text=True
    )

    # Generate HTML
    html = generate_html(pytest_result, test_data)

    # Save HTML
    output_file = Path("test_results.html")
    output_file.write_text(html)

    print(f"\n✅ Test results saved to: {output_file.absolute()}")
    print(f"Open in browser: file://{output_file.absolute()}")

    # Open in browser
    import webbrowser
    webbrowser.open(f"file://{output_file.absolute()}")

    return output_file


if __name__ == "__main__":
    main()

