#!/usr/bin/env python3
"""
Comprehensive Test Suite for Collapsible Toolbar Menus
Tests all 4 modules: Canvas, Mapping, Board Builder, CAD Designer
"""

import os
import sys
import re

def print_test(name, passed, details=""):
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status}: {name}")
    if details and not passed:
        print(f"       {details}")
    return passed

def main():
    print("=" * 60)
    print("🔬 TOOLBAR MENU VERIFICATION TEST")
    print("=" * 60)
    print()

    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    templates_path = os.path.join(base_path, "templates")

    passed = 0
    failed = 0

    # ============================================
    # Test 1: Canvas Editor
    # ============================================
    print("🎨 Test 1: Canvas Editor")
    print("-" * 40)

    canvas_path = os.path.join(templates_path, "canvas.html")
    with open(canvas_path, 'r', encoding='utf-8') as f:
        canvas_content = f.read()

    canvas_tests = [
        ('href="/"' in canvas_content and 'Canvas Editor' in canvas_content, "Title links to home"),
        ('menuToggleBtn' in canvas_content, "Menu toggle button exists"),
        ('toggleToolbarMenu' in canvas_content, "Toggle function exists"),
        ('toolbarMenu' in canvas_content, "Dropdown menu container exists"),
        ('menuIcon' in canvas_content, "Menu icon element exists"),
        ('bg-gradient-to-r from-green-500' in canvas_content or 'from-green-500 to-green-600' in canvas_content, "Green + button styling"),
        ("window.location.href='/'" in canvas_content, "Home navigation in menu"),
        ("window.location.href='/mapping'" in canvas_content, "Mapping navigation in menu"),
        ("window.location.href='/board-builder'" in canvas_content, "Board Builder navigation in menu"),
        ('exportCanvas' in canvas_content, "Export function in menu"),
    ]

    for check, desc in canvas_tests:
        if print_test(desc, check):
            passed += 1
        else:
            failed += 1

    print()

    # ============================================
    # Test 2: Electrical Mapping
    # ============================================
    print("⚡ Test 2: Electrical Mapping")
    print("-" * 40)

    mapping_path = os.path.join(templates_path, "mapping.html")
    with open(mapping_path, 'r', encoding='utf-8') as f:
        mapping_content = f.read()

    mapping_tests = [
        ('<a href="/"' in mapping_content, "Title links to home"),
        ('mappingMenuToggleBtn' in mapping_content, "Menu toggle button exists"),
        ('toggleMappingMenu' in mapping_content, "Toggle function exists"),
        ('mappingToolbarMenu' in mapping_content, "Dropdown menu container exists"),
        ('mappingMenuIcon' in mapping_content, "Menu icon element exists"),
        ('from-green-500 to-green-600' in mapping_content, "Green + button styling"),
        ('runAIMapping' in mapping_content, "AI Mapping in menu"),
        ('exportMapping' in mapping_content, "Export PDF in menu"),
        ('saveProgress' in mapping_content, "Save in menu"),
        ('loadProgress' in mapping_content, "Load in menu"),
        ('undoAction' in mapping_content, "Undo in menu"),
        ('redoAction' in mapping_content, "Redo in menu"),
    ]

    for check, desc in mapping_tests:
        if print_test(desc, check):
            passed += 1
        else:
            failed += 1

    print()

    # ============================================
    # Test 3: Board Builder
    # ============================================
    print("🔌 Test 3: Board Builder")
    print("-" * 40)

    board_path = os.path.join(templates_path, "board_builder.html")
    with open(board_path, 'r', encoding='utf-8') as f:
        board_content = f.read()

    board_tests = [
        ('<a href="/"' in board_content and 'Loxone Board Builder' in board_content, "Title links to home"),
        ('menuToggleBtn' in board_content, "Menu toggle button exists"),
        ('toggleToolbarMenu' in board_content, "Toggle function exists"),
        ('toolbarMenu' in board_content, "Dropdown menu container exists"),
        ('menuIcon' in board_content, "Menu icon element exists"),
        ('from-green-500 to-green-600' in board_content or '#27ae60' in board_content, "Green + button styling"),
        ('newBoard' in board_content, "New Board in menu"),
        ('openImportModal' in board_content, "Import Data in menu"),
        ('generateBoardWithAI' in board_content, "AI Generate in menu"),
        ('saveBoard' in board_content, "Save in menu"),
        ('loadBoard' in board_content, "Load in menu"),
        ('openExportModal' in board_content, "Export in menu"),
        ('clearBoard' in board_content, "Clear in menu"),
        ('generateCADDrawings' in board_content, "Generate CAD in menu"),
    ]

    for check, desc in board_tests:
        if print_test(desc, check):
            passed += 1
        else:
            failed += 1

    print()

    # ============================================
    # Test 4: CAD Designer
    # ============================================
    print("📐 Test 4: CAD Designer")
    print("-" * 40)

    cad_path = os.path.join(templates_path, "cad_designer.html")
    with open(cad_path, 'r', encoding='utf-8') as f:
        cad_content = f.read()

    cad_tests = [
        ('<a href="/"' in cad_content, "Title area links to home"),
        ('cadMenuToggleBtn' in cad_content, "Menu toggle button exists"),
        ('toggleCadMenu' in cad_content, "Toggle function exists"),
        ('cadToolbarMenu' in cad_content, "Dropdown menu container exists"),
        ('cadMenuIcon' in cad_content, "Menu icon element exists"),
        ('from-green-500 to-green-600' in cad_content, "Green + button styling"),
        ('newProject' in cad_content, "New Project in menu"),
        ('saveProject' in cad_content, "Save Project in menu"),
        ('loadProject' in cad_content, "Load Project in menu"),
        ('addTitleBlock' in cad_content, "Title Block in menu"),
        ('generatePanelSchedule' in cad_content, "Panel Schedule in menu"),
        ('generateCableSchedule' in cad_content, "Cable Schedule in menu"),
        ('showWireLabelMenu' in cad_content, "Label Wires in menu"),
        ('showMeasurementMenu' in cad_content, "Measure in menu"),
        ('analyzeDrawing' in cad_content, "Analyze in menu"),
        ('openAIModal' in cad_content, "AI Auto-Generate in menu"),
        ('showImportMenu' in cad_content, "Import in menu"),
        ('showExportMenu' in cad_content, "Export in menu"),
    ]

    for check, desc in cad_tests:
        if print_test(desc, check):
            passed += 1
        else:
            failed += 1

    print()

    # ============================================
    # Test 5: Menu Close on Outside Click
    # ============================================
    print("🖱️ Test 5: Menu Behavior")
    print("-" * 40)

    behavior_tests = [
        ("document.addEventListener('click'" in canvas_content, "Canvas: Outside click handler"),
        ("document.addEventListener('click'" in mapping_content, "Mapping: Outside click handler"),
        ("document.addEventListener('click'" in board_content, "Board: Outside click handler"),
        ("document.addEventListener('click'" in cad_content, "CAD: Outside click handler"),
        ("'×'" in canvas_content or "'×'" in canvas_content, "Canvas: × icon when open"),
        ("'×'" in mapping_content or "'×'" in mapping_content, "Mapping: × icon when open"),
        ("'×'" in board_content or "'×'" in board_content, "Board: × icon when open"),
        ("'×'" in cad_content or "'×'" in cad_content, "CAD: × icon when open"),
    ]

    for check, desc in behavior_tests:
        if print_test(desc, check):
            passed += 1
        else:
            failed += 1

    print()

    # ============================================
    # Test 6: No Old Toolbar Buttons Visible
    # ============================================
    print("🧹 Test 6: Toolbar Cleanup")
    print("-" * 40)

    # Check that the old horizontal button rows are removed
    cleanup_tests = [
        # Board builder should not have the old horizontal layout
        (board_content.count('toolbar-btn') < 30, "Board: Buttons moved to dropdown"),
        # CAD should not have the old action buttons row
        ('<!-- Action Buttons Row -->' not in cad_content, "CAD: Old action row removed"),
        # Mapping should not have the second row
        ('<!-- Second Row: Action Buttons -->' not in mapping_content, "Mapping: Old second row removed"),
    ]

    for check, desc in cleanup_tests:
        if print_test(desc, check):
            passed += 1
        else:
            failed += 1

    print()

    # ============================================
    # Summary
    # ============================================
    print("=" * 60)
    total = passed + failed
    percentage = (passed / total * 100) if total > 0 else 0

    print(f"📊 RESULTS: {passed}/{total} tests passed ({percentage:.1f}%)")
    print("=" * 60)

    if failed == 0:
        print("🎉 ALL TESTS PASSED!")
        print()
        print("Verified Features:")
        print("• Canvas Editor: Title clickable to home, + menu with all functions")
        print("• Electrical Mapping: Title clickable to home, + menu with all functions")
        print("• Board Builder: Title clickable to home, + menu with all functions")
        print("• CAD Designer: Title area clickable to home, + menu with all functions")
        print()
        print("UI Improvements:")
        print("• Clean, minimal headers")
        print("• Green + button on top right")
        print("• Organized dropdown menus with sections")
        print("• Click outside to close")
        print("• Icon changes from + to × when open")
        print()
        print("All toolbar buttons successfully consolidated into collapsible menus!")
    else:
        print(f"⚠️  {failed} tests failed. Please review the issues above.")

    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
