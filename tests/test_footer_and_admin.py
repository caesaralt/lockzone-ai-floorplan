#!/usr/bin/env python3
"""
Test script to verify footer additions and admin page editor functionality
"""

import os
import sys
import re

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_footer_in_all_modules():
    """Test that footer is present in all module templates"""
    templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')

    # List of all modules that should have the footer
    modules = [
        'template_unified.html',
        'index.html',
        'crm.html',
        'kanban.html',
        'learning.html',
        'mapping.html',
        'board_builder.html',
        'cad_designer.html',
        'canvas.html',
        'simpro.html',
        'admin_page_editor.html'
    ]

    footer_pattern = r'© 2025 Integratd Living\. All rights reserved\.'

    results = []
    for module in modules:
        filepath = os.path.join(templates_dir, module)
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                if re.search(footer_pattern, content):
                    results.append((module, True, 'Footer found'))
                else:
                    results.append((module, False, 'Footer NOT found'))
        else:
            results.append((module, False, f'File not found: {filepath}'))

    return results

def test_admin_routes_in_app():
    """Test that admin routes are properly defined in app.py"""
    app_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'app.py')

    with open(app_path, 'r', encoding='utf-8') as f:
        content = f.read()

    tests = [
        ("Admin page editor route", r"@app\.route\('/admin/page-editor'\)"),
        ("GET page config route", r"@app\.route\('/api/admin/page-config', methods=\['GET'\]\)"),
        ("POST page config route", r"@app\.route\('/api/admin/page-config', methods=\['POST'\]\)"),
        ("load_page_config function", r"def load_page_config\(\):"),
        ("save_page_config function", r"def save_page_config\(config\):"),
        ("Uses DATA_FOLDER config", r"app\.config\['DATA_FOLDER'\]"),
    ]

    results = []
    for name, pattern in tests:
        if re.search(pattern, content):
            results.append((name, True, 'Found'))
        else:
            results.append((name, False, 'Not found'))

    return results

def test_admin_editor_template():
    """Test the admin page editor template has required elements"""
    template_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates', 'admin_page_editor.html')

    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()

    tests = [
        ("Logo icon picker", r'id="logo_icon"'),
        ("Logo text input", r'id="logo_text"'),
        ("Logo color picker", r'id="logo_color"'),
        ("Background color picker", r'id="background_color"'),
        ("Welcome title input", r'id="welcome_title"'),
        ("Welcome subtitle input", r'id="welcome_subtitle"'),
        ("Modules container", r'id="modules-container"'),
        ("Save config function", r'function saveConfig\(\)'),
        ("Add module function", r'function addModule\(\)'),
        ("Delete module function", r'function deleteModule\('),
        ("Move module function", r'function moveModule\('),
        ("Preview iframe", r'id="preview-frame"'),
        ("Reset to default button", r'onclick="resetToDefault\(\)"'),
        ("API endpoint call", r'/api/admin/page-config'),
    ]

    results = []
    for name, pattern in tests:
        if re.search(pattern, content):
            results.append((name, True, 'Found'))
        else:
            results.append((name, False, 'Not found'))

    return results

def test_template_uses_config():
    """Test that template_unified.html uses the config values"""
    template_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates', 'template_unified.html')

    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()

    tests = [
        ("Config logo icon", r'config\.logo_icon'),
        ("Config logo text", r'config\.logo_text'),
        ("Config logo color", r'config\.logo_color'),
        ("Config background color", r'config\.background_color'),
        ("Config welcome title", r'config\.welcome_title'),
        ("Config welcome subtitle", r'config\.welcome_subtitle'),
        ("Config modules loop", r'for module in config\.modules'),
        ("Admin link in nav", r'href="/admin/page-editor"'),
    ]

    results = []
    for name, pattern in tests:
        if re.search(pattern, content):
            results.append((name, True, 'Found'))
        else:
            results.append((name, False, 'Not found'))

    return results

def main():
    print("=" * 60)
    print("FOOTER AND ADMIN EDITOR TEST SUITE")
    print("=" * 60)
    print()

    total_passed = 0
    total_failed = 0

    # Test 1: Footer in all modules
    print("TEST 1: Footer in All Modules")
    print("-" * 40)
    results = test_footer_in_all_modules()
    for name, passed, message in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {name} - {message}")
        if passed:
            total_passed += 1
        else:
            total_failed += 1
    print()

    # Test 2: Admin routes in app.py
    print("TEST 2: Admin Routes in app.py")
    print("-" * 40)
    results = test_admin_routes_in_app()
    for name, passed, message in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {name}")
        if passed:
            total_passed += 1
        else:
            total_failed += 1
    print()

    # Test 3: Admin editor template
    print("TEST 3: Admin Editor Template Elements")
    print("-" * 40)
    results = test_admin_editor_template()
    for name, passed, message in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {name}")
        if passed:
            total_passed += 1
        else:
            total_failed += 1
    print()

    # Test 4: Template uses config
    print("TEST 4: Template Uses Config Values")
    print("-" * 40)
    results = test_template_uses_config()
    for name, passed, message in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {name}")
        if passed:
            total_passed += 1
        else:
            total_failed += 1
    print()

    # Summary
    total = total_passed + total_failed
    percentage = (total_passed / total * 100) if total > 0 else 0

    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Total tests: {total}")
    print(f"Passed: {total_passed}")
    print(f"Failed: {total_failed}")
    print(f"Success rate: {percentage:.1f}%")
    print("=" * 60)

    return 0 if total_failed == 0 else 1

if __name__ == '__main__':
    sys.exit(main())
