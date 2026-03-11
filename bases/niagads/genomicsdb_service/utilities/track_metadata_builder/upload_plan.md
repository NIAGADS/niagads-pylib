I'll analyze the current code and suggest an implementation approach for adding a JSON upload feature.

Read [](file:///home/allenem/projects/genomicsdb/niagads-pylib/bases/niagads/genomicsdb_service/utilities/track_metadata_builder/app.py#1-1), lines 1 to 100

Let me see more of the run method to understand the current form flow:

Read [](file:///home/allenem/projects/genomicsdb/niagads-pylib/bases/niagads/genomicsdb_service/utilities/track_metadata_builder/app.py#350-350), lines 350 to 450

Perfect! Now I have a good understanding of the code structure. Let me provide a comprehensive implementation plan:

## Implementation Plan: JSON Upload Feature

### **Overview**

Add the ability to upload a previously downloaded JSON file to pre-populate the form with saved values. This creates a "load/save" workflow for users.

---

### **Architecture & Components**

#### **1. New Private Method: `__load_json_upload()`**

**Location:** In `MetadataBuilderApp` class
**Purpose:** Handle JSON file upload and validation
**Logic:**

- Use `st.file_uploader()` to accept JSON files
- Parse the JSON and validate it matches the Pydantic model schema
- Return parsed data or error messages

**Key considerations:**

- Validate uploaded JSON can be instantiated with `self.__pydantic_model(**json_data)`
- Catch `ValidationError` to report what fields failed
- Handle malformed JSON gracefully

---

#### **2. New Private Method: `__deserialize_from_json()`**

**Location:** In `MetadataBuilderApp` class
**Purpose:** Convert JSON-serialized values back into form-compatible format
**Logic:**

- Reverse the serialization process (opposite of `model_dump(mode="json")`)
- Convert dates from ISO string → `date` object
- Convert `OntologyTerm` dicts → `OntologyTerm` objects
- Handle nested composite fields and repeatable lists
- Handle enum values (ensure string matches enum option)

**Key considerations:**

- This reverses what `__process_form_data()` does
- Use the same deserializers in `self.__deserializers` but apply them systematically
- For repeatable fields, reconstruct the session state properly with `_entry_id` keys

---

#### **3. New Private Method: `__populate_form_from_data()`**

**Location:** In `MetadataBuilderApp` class
**Purpose:** Store deserialized data into Streamlit session state for form rendering
**Logic:**

- For simple fields: store value directly in session state
- For repeatable fields: reconstruct the session list with proper `_entry_id` tracking
- For nested composite fields: recursively populate session state
- Trigger `st.rerun()` to re-render the form with populated values

**Key considerations:**

- Session state keys must match what `FormRenderer.render_field()` expects
- For repeatable fields, use the same `_list_{field_name}_entries` and `_list_{field_name}_counter` pattern
- Must handle the render cycle: populate session → form renders with defaults from session

---

#### **4. UI Integration in `run()` Method**

**Location:** Before the form (at the top of `run()`)
**Suggested placement:**

```
Title
"Enter track metadata below"
[Upload JSON Button / File Uploader]  ← NEW
---
[Existing Form]
```

**Implementation:**

- Add `st.file_uploader()` in a dedicated section above the form
- On file selection:
  - Call `__load_json_upload()` to parse and validate
  - Call `__deserialize_from_json()` to convert back to form format
  - Call `__populate_form_from_data()` to set session state
  - Call `st.rerun()` to re-render
- Show success message with loaded metadata summary
- Show error messages if validation fails

---

### **Data Flow Diagram**

```
User downloads JSON
        ↓
User selects file with st.file_uploader()
        ↓
__load_json_upload()
  ├─ Parse JSON
  ├─ Validate with Track model
  └─ Return parsed dict or errors
        ↓
__deserialize_from_json()
  ├─ Convert dates: "2026-03-11" → date(2026, 3, 11)
  ├─ Convert OntologyTerms: {"term": "X", "curie": "Y"} → OntologyTerm(...)
  ├─ Handle enums and lists
  └─ Return form-compatible dict
        ↓
__populate_form_from_data()
  ├─ Set session state for simple fields
  ├─ Reconstruct repeatable field session state with _entry_id
  ├─ Recursively populate nested composites
  └─ st.rerun()
        ↓
Form re-renders with populated values
```

---

### **Session State Considerations**

For repeatable fields, maintain the existing pattern:

- Key: `_list_{field_name}_entries` → list of dicts with `_entry_id`
- Key: `_list_{field_name}_counter` → tracks next available ID

When loading from JSON, you'll need to reconstruct these lists properly to ensure the UI's remove buttons work correctly.

---

### **Error Handling Strategy**

1. **Invalid JSON**: Show error and offer retry
2. **Validation errors**: Show Pydantic error messages with field paths
3. **Type mismatches**: Report which fields couldn't be deserialized
4. **Partial loads**: Allow loading even if some optional fields are missing

---

### **Suggested Implementation Order**

1. `__load_json_upload()` — Core parsing and validation
2. `__deserialize_from_json()` — Handle type conversions (most complex)
3. `__populate_form_from_data()` — Session state management
4. UI integration in `run()` — Add file uploader and call handlers

---

### **Testing Considerations**

- Download a JSON, immediately re-upload it → should match exactly
- Upload with missing optional fields → should load successfully
- Upload with invalid dates or enums → should show helpful errors
- Repeatable fields → verify add/remove buttons work after loading

---

Would you like me to proceed with implementing these methods? I'd recommend starting with `__load_json_upload()` and `__deserialize_from_json()` first to validate the approach, then integrate into the UI.
