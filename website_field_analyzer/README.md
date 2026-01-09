# Website Field Analyzer

A **pure, read-only analyzer** that captures what a website expects from a human user without any interaction. This tool follows a strict 14-step pipeline to produce structured JSON output describing forms, fields, and page types.

## 🎯 Purpose

This is **Step-1** of a larger web automation system. It analyzes web pages to understand their structure **without**:
- Filling forms
- Clicking buttons
- Bypassing security
- Scraping data
- Any automation actions

## 🔷 The 14-Step Pipeline

```
User URL
  ↓
Browser Launch
  ↓
Page Load & Stabilize
  ↓
DOM Snapshot
  ↓
Interactive Element Extraction
  ↓
Element Normalization
  ↓
Form Grouping
  ↓
Required / Optional Classification
  ↓
Page Type Detection
  ↓
Structured JSON Output
```

## 📦 Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

## 🚀 Usage

### Basic Usage

```bash
python main.py --url "https://example.com/login"
```

### Save Output to File

```bash
python main.py --url "https://example.com/login" --output analysis.json
```

### Run in Visible Mode (Non-Headless)

```bash
python main.py --url "https://example.com/login" --no-headless
```

### Enable Debug Logging

```bash
python main.py --url "https://example.com/login" --debug
```

## 📊 Output Structure

The analyzer produces a structured JSON output:

```json
{
  "url": "https://example.com/login",
  "page_type": "login",
  "forms": [
    {
      "form_id": "form_abc123",
      "form_purpose": "login",
      "fields": [
        {
          "tag_name": "input",
          "input_type": "email",
          "name": "email",
          "classification": "required",
          "visible": true,
          "selector": "input[name='email']"
        },
        {
          "tag_name": "input",
          "input_type": "password",
          "name": "password",
          "classification": "required",
          "visible": true,
          "selector": "input[name='password']"
        }
      ],
      "submit_element": {
        "tag": "button",
        "type": "submit",
        "text": "Sign In"
      }
    }
  ],
  "total_fields": 2,
  "total_required": 2,
  "total_forms": 1
}
```

## 🏗️ Architecture

```
website_field_analyzer/
├── config/          # Settings and browser profiles
├── browser/         # Browser management and page loading
├── analyzer/        # Core analysis components
│   ├── dom_analyzer.py      # Steps 4-7: Extract & normalize
│   ├── form_detector.py     # Steps 8-9: Group & detect submit
│   ├── field_classifier.py  # Step 10: Classify fields
│   └── page_classifier.py   # Steps 11-12: Classify page
├── models/          # Data structures
├── utils/           # Helper functions
└── main.py          # Entry point
```

## 🎓 Classification Logic

### Form Purpose Detection

- **Login**: email/username + password (1 password field)
- **Signup**: email + multiple passwords (confirm password)
- **Search**: single text input + submit
- **Listing**: multiple dropdowns/filters
- **Mixed**: combination of above
- **Unknown**: unclear pattern

### Field Classification

**Required if:**
- Has `required` attribute
- Type is `password`
- Type is `hidden` (tokens like CSRF)
- Name/ID matches common patterns (email, username, etc.)

**Optional if:**
- Dropdown filters
- Checkboxes
- Secondary inputs

**Hidden if:**
- Type is `hidden`
- Not visible on page

### Page Type Detection

Based on all forms present:
- **login page**: Only login forms
- **signup page**: Only signup forms
- **search page**: Only search forms
- **listing page**: Only listing/filter forms
- **mixed page**: Multiple form types
- **unknown page**: Unclear pattern

## ⚠️ Important Notes

> **This is a READ-ONLY analyzer**
> 
> It does NOT:
> - Fill any forms
> - Click any buttons
> - Bypass Cloudflare or security
> - Scrape any data
> - Perform any automation

The analyzer observes and reports what it sees, nothing more.

## 🔧 Configuration

Edit `config/settings.py` to customize:

- Timeouts
- Browser behavior
- Analysis thresholds
- Field classification patterns

## 📝 Examples

### Analyze GitHub Login

```bash
python main.py --url "https://github.com/login"
```

### Analyze Google Search

```bash
python main.py --url "https://www.google.com"
```

### Analyze with Debug Output

```bash
python main.py --url "https://example.com" --debug --output result.json
```

## 🧪 Testing

```bash
# Run tests
python -m pytest tests/

# Run specific test
python -m pytest tests/test_dom_analysis.py
```

## 📄 License

MIT License

## 🤝 Contributing

This is Step-1 of a larger system. Keep it pure and focused on analysis only.

**Do NOT add:**
- Form filling logic
- Click automation
- Cloudflare bypassing
- Data scraping

These belong in Step-2 (Decision Engine) and beyond.

## 🔮 Future Enhancements

- Machine learning-based field classification
- Support for shadow DOM
- iframe analysis
- Dynamic form detection (forms that appear after interaction)
- API endpoint detection from network traffic

---

**Remember**: This analyzer should be able to say:

> "I know exactly what this website expects from a human, without interacting with it."

If it does anything more than observe, it's doing too much.
