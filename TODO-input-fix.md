# Input Field Fix Plan - test_interface.html

## Plan Details

**Information Gathered**: 

- Server running ✓
- Difficulty/duration JS working ✓
- Input field not accepting text (user feedback)

**Code Analysis** (Pages/test_interface.html):

- `<input id="courseTitle">` has `input` event → `validateForm()`
- Button disabled until title.length >=3

**Root Cause**: Input visually unresponsive (CSS/JS issue)

**Detailed Update Plan**:

1. **Input field**: Add char counter, force focus, visual feedback
2. **Validation**: Live char count + error message
3. **Debug**: Console logs for input events
4. **Auto-focus**: Click page → input focused

**Files to Edit**:

- `Pages/test_interface.html` (add counter + styles)

**Followup Steps**:

1. Edit file → auto-reload (server watching)
2. Test typing → char counter updates
3. Generate button enables
4. API test: curl POST /courses/generate

**Status**: ✅ Implemented (4 edits applied)

**Changes Made**:
```
✅ 1. Char counter: 0/255 → green at 3+ chars
✅ 2. Live status: "Type 2 more chars" → "✓ Ready"
✅ 3. Console debug logs
✅ 4. Auto-focus input on load
```

**Next**: 

- ✅ Reloaded - debug logs + labels added
- Difficulty clicks → check Console logs
- Backend test: curl API endpoint ✓
- Generate full flow

