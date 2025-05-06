Package Structure Update
Here's the new directory structure we added to the existing structure

angela/
├── ai/
│   ├── __init__.py
│   ├── client.py      # Gemini API client
│   ├── prompts.py     # Prompt engineering
│   ├── parser.py      # Response parsing
│   └── models.py      # AI data models
├── intent/
│   ├── __init__.py
│   └── models.py      # Intent data structures
└── execution/
    ├── __init__.py
    └── engine.py      # Command execution
