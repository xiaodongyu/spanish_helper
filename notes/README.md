# Notes Directory - Module Documentation

This directory contains module-specific documentation and development history for the Spanish Helper project.

## Organization Structure

Documentation is organized by module name to support multiple modules in the future:

```
notes/
├── README.md                        # This file - explains organization
├── {module_name}_SUMMARY.md         # Detailed module summary
├── {module_name}_CONTEXT.md         # Quick reference for module
└── {module_name}_CHAT_HISTORY.md    # Full chat history from development
```

## Current Modules

### transcribe_audio.py
The transcription module for Spanish Duolingo radio audio files.

**Documentation:**
- `transcribe_audio_SUMMARY.md` - Comprehensive module summary (features, architecture, decisions)
- `transcribe_audio_CONTEXT.md` - Quick reference (setup, usage, troubleshooting)
- `transcribe_audio_CHAT_HISTORY.md` - Full development chat history (41,831 lines)

## Adding a New Module

When adding a new module to the project:

### Step 1: Start a New Chat Session
**✅ Recommended:** Start a **new chat/agent session** for each module to keep histories separated.

**Benefits:**
- **Clean separation** - Each module's development history is isolated
- **Easier navigation** - Find relevant conversations quickly
- **Better organization** - Chat history aligns with module structure
- **Reduced confusion** - No mixing of different module discussions
- **Cleaner exports** - Export only module-specific conversations

**When to use separate sessions:**
- ✅ **New module development** - Always start fresh
- ✅ **Major refactoring of existing module** - Start new session for tracking
- ✅ **Different functionality** - Even if related, keep separate

**When you can use same session:**
- ⚠️ **Bug fixes** - Can continue in same session if minor
- ⚠️ **Quick follow-ups** - If within same development session
- ⚠️ **Related enhancements** - If closely related to current module

### Step 2: Create Module-Specific Documentation
1. **Create module-specific documentation:**
   ```
   notes/
   ├── {new_module}_SUMMARY.md       # Detailed summary
   ├── {new_module}_CONTEXT.md       # Quick reference
   └── {new_module}_CHAT_HISTORY.md  # Development history (exported)
   ```

2. **Naming convention:**
   - Use module filename (without `.py`) as prefix
   - Use descriptive suffixes: `_SUMMARY.md`, `_CONTEXT.md`, `_CHAT_HISTORY.md`
   - Examples:
     - `vocabulary_extractor_SUMMARY.md`
     - `quiz_generator_CONTEXT.md`
     - `word_frequency_CHAT_HISTORY.md`

### Step 3: Export Chat History
**Regularly export chat history** during or after module development:
- **How to export in Cursor:** Right-click chat panel → "Export Chat" → Save as `notes/{module}_CHAT_HISTORY.md`
- **When to export:** 
  - After completing major features
  - At end of development session
  - When module is "complete" or stable
- **Update SUMMARY/CONTEXT:** Use exported chat history to generate/update SUMMARY and CONTEXT files

### Step 4: Update Documentation
3. **Update this README** with the new module documentation

## File Naming Guidelines

- **`{module}_SUMMARY.md`** - Comprehensive documentation
  - Overview, features, architecture, decisions, history
  - For deep understanding of the module
  - Typically longer (10-20KB)

- **`{module}_CONTEXT.md`** - Quick reference
  - Current state, setup, common tasks, troubleshooting
  - For quick lookups during development
  - Typically shorter (5-10KB)

- **`{module}_CHAT_HISTORY.md`** - Development history (optional)
  - Full conversation/chat history from development
  - Raw development notes and decisions
  - Can be large (tens of thousands of lines)
  - Useful for understanding "why" behind decisions

## Project-Level Documentation

Module-agnostic documentation is kept in the project root:
- `README.md` - Project overview and main documentation
- `SETUP_GUIDE.md` - Setup instructions (may reference multiple modules)
- `API_COMPARISON.md` - API comparisons (may be used by multiple modules)
- `LICENSE` - Project license

## Chat Session Management Best Practices

### Recommended Workflow

1. **Starting a new module:**
   ```
   → Start NEW chat session in Cursor
   → Focus conversation on that module only
   → Export chat history when done: notes/{module}_CHAT_HISTORY.md
   → Create SUMMARY and CONTEXT from exported history
   ```

2. **During development:**
   - Keep chat focused on single module
   - If switching modules, start new session
   - Export periodically (after major milestones)

3. **After completion:**
   - Export final chat history
   - Generate SUMMARY and CONTEXT files
   - Update notes/README.md

### Exporting Chat History

**In Cursor:**
- Right-click on chat panel → "Export Chat" or "Save Chat"
- Save as: `notes/{module}_CHAT_HISTORY.md`
- Include date in file if you have multiple exports

**Format:**
```markdown
# {Module Name} Development Chat
_Exported on {date} from Cursor {version}_

---

{chat history content}
```

### Cross-Module Discussions

If you need to discuss **multiple modules together** (e.g., integration):
- Use a separate session: `notes/cross_module_discussions.md`
- Or add to project-level documentation: `README.md`, `ARCHITECTURE.md`
- Keep module-specific chats separate

## Benefits of This Structure

1. **Scalability** - Easy to add new modules without confusion
2. **Clarity** - Clear which module each document belongs to
3. **Organization** - Logical grouping by functionality
4. **Maintainability** - Easy to find and update module-specific docs
5. **Separation** - Module docs separate from project-level docs
6. **Clean history** - Each module has its own isolated development history

---

**Last Updated:** 2026-01-09  
**Maintained By:** Project maintainers
