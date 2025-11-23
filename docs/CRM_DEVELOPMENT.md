# CRM Development Guide

## File Structure

### `templates/crm.html`

This is the main CRM dashboard file. **Important notes for developers:**

#### JavaScript Structure

**ONE UNIFIED SCRIPT BLOCK**: All JavaScript code is contained in a single `<script>` block (lines ~2299-6391).

⚠️ **CRITICAL**: Do NOT create additional `<script>` blocks in this file. This causes:
- "Function not defined" errors
- Variables not accessible across blocks
- Event listeners failing to attach
- Buttons and UI elements breaking

#### Code Organization Within the Script Block

The single script block is organized into sections:

1. **Global Variables** (top of script)
   - Arrays for data: `customers`, `projects`, `quotes`, `jobs`, etc.
   - Window-level storage: `window.allCustomers`, `window.allJobs`, etc.

2. **Initialization** (`DOMContentLoaded` listener)
   - `setupNavigation()` - Navigation menu handlers
   - `loadAllData()` - Initial data fetch
   - `checkForImportedData()` - Quote automation imports
   - `initDarkMode()` - Dark mode toggle initialization

3. **Data Loading Functions**
   - `loadCustomers()`, `loadProjects()`, `loadQuotes()`, etc.
   - Fetch data from API and render to DOM

4. **Modal Opening Functions**
   - `openModal(modalId)` - Generic modal opener
   - `openQuoteModal(status)` - Quote modal with status
   - `openPersonModal(type)` - Person modal with type
   - `openJobModal(status)` - Job modal with status
   - `openMaterialModal(type)` - Material modal
   - `openPaymentModal(direction)` - Payment modal
   - `openEventModal(date)` - Calendar event modal

5. **CRUD Operations**
   - Save, edit, delete functions for each entity type

6. **AI Chat Functions** (merged section)
   - `toggleAIChat()`, `sendAIMessage()`, etc.

7. **Dark Mode Functions** (merged section)
   - `initDarkMode()` - Theme toggle initialization

## Common Issues & Solutions

### Issue: Buttons Not Working

**Symptom**: Clicking "Add Customer", "Add Job", etc. does nothing

**Cause**: JavaScript error preventing code execution

**Debug Steps**:
1. Open browser console (F12)
2. Look for red error messages
3. Common errors:
   - "X is not defined" - Function missing or in wrong scope
   - "Cannot read property of null" - DOM element doesn't exist
   - "Unexpected token" - Syntax error in code

**Solution**: Ensure all modal opening functions (`openXModal`) exist and are properly defined

### Issue: Dark Mode Not Working

**Symptom**: Clicking sun/moon icon does nothing

**Cause**: `initDarkMode()` not being called or called before DOM ready

**Debug Steps**:
1. Check browser console for errors
2. Verify `initDarkMode()` is called in `DOMContentLoaded` listener
3. Check HTML elements exist: `id="themeToggle"`, `id="sunIcon"`, `id="moonIcon"`

**Solution**: Ensure `initDarkMode()` is in the main `DOMContentLoaded` listener at the top of the script block

### Issue: "Function Not Defined" Errors

**Symptom**: Console shows "Uncaught ReferenceError: functionName is not defined"

**Cause**: Function in different script block or not defined yet

**Solution**:
- Keep ALL functions in the ONE unified script block
- Ensure functions are defined before they're called
- Use `DOMContentLoaded` for initialization code

## Best Practices

### When Adding New Features

1. **Add functions inside the existing script block** - Never create a new `<script>` tag
2. **Define before use** - Ensure functions exist before they're called
3. **Use consistent naming**:
   - `openXModal(param)` for modal openers
   - `loadX()` for data loading
   - `saveX(event)` for save operations
   - `editX(id)` for edit operations
   - `deleteX(id)` for delete operations

4. **Initialize in DOMContentLoaded** - Add initialization calls to the main listener

### When Modifying Modals

- Modal HTML structure: `<div id="XModal" class="modal">`
- Modal content: `<div class="modal-content">`
- Open with: `openModal('XModal')` or custom `openXModal()`
- Close with: `closeModal('XModal')`
- Form submit: `onsubmit="saveX(event)"`

### Testing Checklist

Before committing changes:

- [ ] Check browser console for errors (F12)
- [ ] Test all affected buttons click properly
- [ ] Verify modals open and close
- [ ] Test form submissions save correctly
- [ ] Check dark mode toggle works
- [ ] Test on both desktop and mobile viewport

## File History

- **2025-11**: Merged two separate script blocks into one unified block to prevent cross-block reference errors
- Previous structure had functions split across two blocks, causing "not defined" errors

## Need Help?

If you encounter issues:
1. Check browser console first
2. Verify function exists in the unified script block
3. Ensure proper initialization in `DOMContentLoaded`
4. Review this guide for common patterns
