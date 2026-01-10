# Development Workflow Guide: Adding New Modules

This guide explains the recommended workflow for adding new modules to the Spanish Helper project, including chat session management and documentation organization.

---

## Quick Answer: Should I Start a New Chat Session?

**✅ YES - Start a new chat session for each new module!**

This keeps chat histories clean, organized, and easy to reference later.

---

## Complete Workflow: Adding a New Module

### Phase 1: Preparation

1. **Plan the module**
   - What functionality will it provide?
   - What are the inputs/outputs?
   - How does it relate to existing modules?

2. **Create module file**
   - `new_module.py` (or appropriate name)
   - Add basic structure/boilerplate

3. **Start NEW chat session** in Cursor
   - This is important! Keep conversations focused
   - Mention which module you're working on: "I'm creating a vocabulary_extractor module..."

### Phase 2: Development

1. **Work on the module** in the focused chat session
   - Keep conversation focused on this module only
   - If you need to discuss integration with other modules, note it but keep focused

2. **Export chat history periodically**
   - After major features: Export as `notes/{module}_CHAT_HISTORY.md`
   - Or wait until module is complete
   - In Cursor: Right-click chat → "Export Chat"

### Phase 3: Documentation

1. **Export final chat history**
   ```
   notes/{module}_CHAT_HISTORY.md
   ```

2. **Generate SUMMARY and CONTEXT files**
   - Use chat history to create:
     - `notes/{module}_SUMMARY.md` - Comprehensive summary
     - `notes/{module}_CONTEXT.md` - Quick reference
   - Or ask AI to summarize the chat history

3. **Update project documentation**
   - Add module to `notes/README.md`
   - Update project `README.md` if needed
   - Update `requirements.txt` if new dependencies

---

## Example: Adding a Vocabulary Extractor Module

### Step-by-Step

1. **Start new chat session:**
   ```
   User: "I want to create a vocabulary_extractor.py module that 
         extracts Spanish vocabulary words from transcripts and 
         saves them to a vocabulary list file."
   ```

2. **Develop in focused session:**
   - Discuss requirements
   - Implement features
   - Test and iterate
   - Keep all conversation in this session

3. **When module is complete:**
   ```
   → Export chat: notes/vocabulary_extractor_CHAT_HISTORY.md
   → Generate summary: notes/vocabulary_extractor_SUMMARY.md
   → Create quick ref: notes/vocabulary_extractor_CONTEXT.md
   → Update notes/README.md to list new module
   ```

4. **Final structure:**
   ```
   notes/
   ├── transcribe_audio_CHAT_HISTORY.md
   ├── transcribe_audio_SUMMARY.md
   ├── transcribe_audio_CONTEXT.md
   ├── vocabulary_extractor_CHAT_HISTORY.md    ← New
   ├── vocabulary_extractor_SUMMARY.md          ← New
   └── vocabulary_extractor_CONTEXT.md          ← New
   ```

---

## Chat Session Guidelines

### When to Start a New Session

**✅ Start NEW session:**
- Creating a completely new module
- Major refactoring of existing module
- Different functionality/feature area
- Want clean history for documentation

**⚠️ Can continue same session:**
- Minor bug fixes in existing module
- Quick follow-up questions (same day)
- Small enhancements to current work
- Testing/debugging current module

**❌ Don't mix:**
- Different modules in same session
- Unrelated features
- Multiple development tracks

### Managing Multiple Sessions

If you're working on multiple modules:

**Option 1: Sequential development**
- Complete one module fully
- Export and document
- Start new session for next module

**Option 2: Parallel development**
- Start separate sessions for each module
- Keep conversations focused
- Export each independently when done

**Option 3: Branching**
- Main session for project-level discussions
- Separate sessions for each module
- Export all when complete

---

## Exporting Chat History

### How to Export in Cursor

1. **During development:**
   - Right-click on chat panel
   - Select "Export Chat" or "Save Chat"
   - Save as: `notes/{module}_CHAT_HISTORY.md`

2. **Format:**
   ```markdown
   # {Module Name} Development
   _Exported on {date} from Cursor {version}_
   
   ---
   
   {full chat history}
   ```

3. **When to export:**
   - After completing major features
   - At end of development session
   - When module reaches stable state
   - Before starting unrelated work

### Best Practices

- **Regular exports** - Don't wait until end (might lose history)
- **Clear naming** - Use consistent `{module}_CHAT_HISTORY.md` pattern
- **Include dates** - If multiple exports, add date: `{module}_CHAT_HISTORY_2026-01-09.md`
- **Version control** - Commit exported histories to git

---

## Documentation Generation

### From Chat History to Documentation

After exporting chat history:

1. **Generate SUMMARY:**
   ```
   → Read through chat history
   → Extract key features, decisions, architecture
   → Create comprehensive summary document
   → Include: overview, features, technical details, decisions
   ```

2. **Create CONTEXT:**
   ```
   → Extract quick reference info
   → Current state, setup, usage
   → Common tasks, troubleshooting
   → Keep concise and practical
   ```

3. **Update README:**
   ```
   → Add module to notes/README.md
   → List all three files (HISTORY, SUMMARY, CONTEXT)
   → Brief description of module purpose
   ```

### Using AI to Generate Docs

You can ask AI (in a new session or the same session) to:
- "Summarize the chat history in notes/{module}_CHAT_HISTORY.md"
- "Create a SUMMARY document for this module"
- "Generate a CONTEXT quick reference from this chat history"

---

## Project-Level vs Module-Level

### Project-Level Documentation
**Location:** Project root  
**Purpose:** Overview, setup, general info  
**Examples:**
- `README.md` - Project overview
- `SETUP_GUIDE.md` - Setup instructions
- `API_COMPARISON.md` - API comparisons
- `LICENSE` - Project license

**Chat sessions:** Use for project-wide discussions, architecture decisions

### Module-Level Documentation
**Location:** `notes/` directory  
**Purpose:** Module-specific details  
**Examples:**
- `{module}_CHAT_HISTORY.md` - Development history
- `{module}_SUMMARY.md` - Detailed summary
- `{module}_CONTEXT.md` - Quick reference

**Chat sessions:** Use separate sessions for each module

---

## Troubleshooting

### "I forgot to start a new session"
- **Solution:** Export current mixed session
- Filter relevant parts for each module
- Split into separate files manually
- Start new sessions going forward

### "I need to discuss multiple modules together"
- **Solution:** Use a separate integration session
- Create: `notes/cross_module_integration.md`
- Keep module-specific sessions separate
- Document integration decisions in project-level docs

### "My chat history is too long"
- **Solution:** Export periodically during development
- Break into milestones: `{module}_CHAT_HISTORY_v1.md`, `_v2.md`
- Or export after major features
- Keep final complete export for reference

---

## Checklist: Adding a New Module

- [ ] Plan module functionality and requirements
- [ ] Create module file (`{module}.py`)
- [ ] **Start NEW chat session in Cursor**
- [ ] Develop module in focused session
- [ ] Export chat history: `notes/{module}_CHAT_HISTORY.md`
- [ ] Generate summary: `notes/{module}_SUMMARY.md`
- [ ] Create quick reference: `notes/{module}_CONTEXT.md`
- [ ] Update `notes/README.md` with new module
- [ ] Update project `README.md` if needed
- [ ] Update `requirements.txt` if new dependencies
- [ ] Commit all documentation to git

---

**Last Updated:** 2026-01-09  
**Maintained By:** Project maintainers
