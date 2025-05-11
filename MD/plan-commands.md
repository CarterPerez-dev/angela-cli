Okay, here are 3 example commands or test scenarios for each numbered item in the "Incremental Testing & Refinement Plan." These are designed to target the specific functionality being tested at each stage.

Remember to adjust file names, paths, and specific content to match your actual test environment.

---

**Phase 1: Core AI Interaction & Basic Command Execution**

*   **1.1. AI Client & Basic Prompting:**
    1.  `python -c "from angela.ai.client import gemini_client; from angela.ai.prompts import build_prompt; import asyncio; async def main(): prompt = build_prompt('translate hello to spanish', {}); resp = await gemini_client.generate_text(prompt); print(resp.text); asyncio.run(main())"` (Verify "hola" or similar is in output)
    2.  `python -c "from angela.ai.client import gemini_client; from angela.ai.prompts import build_prompt; import asyncio; async def main(): prompt = build_prompt('what is the capital of France', {}); resp = await gemini_client.generate_text(prompt); print(resp.text); asyncio.run(main())"` (Verify "Paris" is in output)
    3.  `python -c "from angela.ai.client import gemini_client; from angela.ai.prompts import build_prompt; import asyncio; async def main(): prompt = build_prompt('list 3 common linux commands', {}); resp = await gemini_client.generate_text(prompt); print(resp.text); asyncio.run(main())"` (Verify it lists commands like ls, cd, pwd)

*   **1.2. AI Response Parsing:**
    1.  `python -c "from angela.ai.parser import parse_ai_response; resp = '{\"command\": \"ls -la\", \"explanation\": \"list all files\", \"intent\": \"file_list\"}'; print(parse_ai_response(resp))"`
    2.  `python -c "from angela.ai.parser import parse_ai_response; resp = '```json\n{\"command\": \"pwd\", \"explanation\": \"print working directory\", \"intent\": \"cwd\"}\n```'; print(parse_ai_response(resp))"`
    3.  `python -c "from angela.ai.parser import parse_ai_response; resp = 'this is not json'; out = None; try: out = parse_ai_response(resp); except ValueError: print('ValueError caught'); else: print(out)"` (Verify "ValueError caught")

*   **1.3. Basic Command Suggestion (Orchestrator Path):**
    1.  `angela request "show current directory" --suggest-only` (Verify suggests `pwd`)
    2.  `angela request "list all items here" --suggest-only` (Verify suggests `ls -a` or similar)
    3.  `angela request "what time is it" --suggest-only` (Verify suggests `date`)

*   **1.4. Safety Validation & Classification (No Execution):**
    1.  `angela request "display contents of /etc/passwd" --suggest-only` (Verify risk level, explanation)
    2.  `angela request "delete my_document.txt" --suggest-only` (Verify risk level is higher than `ls`)
    3.  `angela request "sudo reboot now" --suggest-only` (Verify it's blocked or CRITICAL risk)

*   **1.5. Basic Command Execution with Confirmation:**
    1.  `angela request "make a new folder called temp_test_dir"` (Confirm 'y', verify dir created, then `rm -rf temp_test_dir`)
    2.  `angela request "show my username"` (Should execute `whoami` or similar, possibly without confirmation if low risk)
    3.  `angela request "delete the file deleteme.txt"` (Create `deleteme.txt` first. Confirm 'n', verify file still exists. Then run again, confirm 'y', verify file deleted)

*   **1.6. Context Management (CWD, Basic Project):**
    1.  `mkdir test_project_ctx; cd test_project_ctx; git init; angela request "what is my current git branch" --suggest-only` (Verify prompt context includes project info)
    2.  `cd ..; angela request "list files in test_project_ctx" --suggest-only` (Verify context reflects CWD, not necessarily project)
    3.  `rm -rf test_project_ctx; angela request "show current path" --suggest-only` (Verify context is just CWD)

---

**Phase 2: Enhanced Context & Adaptive Execution**

*   **2.1. Context Enhancement:**
    1.  (Inside a Python git project with uncommitted changes) `angela request "suggest a commit message for my changes" --suggest-only --debug` (Inspect debug output for enhanced context in prompt)
    2.  (Inside a Node.js project) `angela request "how to run tests in this project" --suggest-only --debug` (Check for Node.js project type in context)
    3.  (After accessing a few files) `angela request "summarize the last file I looked at" --suggest-only --debug` (Check if recent files are in context)

*   **2.2. Session Context & History:**
    1.  `angela request "show me the content of constants.py"` then `angela request "what is the RISK_LEVELS in it?"` (Verify "it" refers to `constants.py`)
    2.  `angela request "create a file named session_test.txt"` then `angela request "delete that file"` (Verify "that file" refers to `session_test.txt`)
    3.  Run `angela request "list files"` three times. Then `angela request "what command did I run most recently?" --suggest-only` (Verify history is used).

*   **2.3. File Resolution:**
    1.  (With `config.toml` and `config.yaml` in project) `angela request "show content of config"` (Verify it asks for clarification or picks one based on heuristics/recency)
    2.  `angela request "edit my_very_specific_unique_filename_in_project.py"` (Verify it finds it without full path)
    3.  `angela request "analyze the main script"` (Verify it tries to find `main.py`, `app.py`, etc.)

*   **2.4. Confidence Scoring & Adaptive Confirmation:**
    1.  `angela request "do something very vague and complex"` (Verify confidence score is low, prompts for confirmation)
    2.  `angela request "list files"` (Run multiple times. Verify if it eventually stops asking for confirmation based on preferences/history if risk is low)
    3.  `angela request "delete important_file.txt"` (Verify confidence might be okay, but adaptive confirmation still prompts due to risk)

*   **2.5. Error Analysis & Recovery (Basic):**
    1.  `angela request "run command gs tatus"` (typo for git status) (Verify `ErrorAnalyzer` suggests `git status`)
    2.  `angela request "cat non_existent_file.txt"` (Verify `ErrorAnalyzer` suggests checking path or creating file)
    3.  `angela request "mkdir /root/test_dir_no_perm"` (Verify `ErrorAnalyzer` suggests `sudo` or permission issue)

*   **2.6. Shell Formatting & Inline Feedback (Basic):**
    1.  `angela request "list files"` (Verify output is nicely formatted by `rich`)
    2.  `angela request "run a command that produces a lot of output"` (Verify panel formatting is reasonable)
    3.  (Manually trigger a scenario where inline feedback might show a simple message, e.g., by modifying `ProactiveAssistant` to show a test message on a specific command)

---

**Phase 3: File Content Operations & Workflows**

*   **3.1. File Content Analysis (Read-only):**
    1.  `echo "def foo(): pass\nclass Bar: pass" > analysis_test.py; angela request "analyze analysis_test.py"` (Verify it identifies functions/classes)
    2.  `echo "This is a test document for summarization." > summary_test.txt; angela request "summarize summary_test.txt"`
    3.  `echo "TODO: Fix this later\n# IMPORTANT: Check this" > search_test.txt; angela request "search for TODO in search_test.txt"`

*   **3.2. File Content Manipulation (with Confirmation & Rollback):**
    1.  `echo "old_value = 10" > manipulate_test.py; angela request "in manipulate_test.py, change old_value to new_value"` (Confirm 'y', check file, then `angela rollback last`, check file again)
    2.  `echo "Hello world" > manipulate_text.txt; angela request "append ' from Angela' to manipulate_text.txt"` (Confirm 'y', check, rollback, check)
    3.  `echo "def func_a():\n  print('a')" > manipulate_complex.py; angela request "add a new function func_b that prints 'b' after func_a in manipulate_complex.py"` (Confirm, check, rollback, check)

*   **3.3. Basic Workflow Definition & Execution:**
    1.  `angela request "define workflow 'test_wf_1' to echo hello and then echo world"` (Verify workflow saved)
    2.  `angela workflows run test_wf_1` (Verify "hello" and "world" are printed)
    3.  `angela request "define workflow 'file_ops' to create a dir 'wf_dir', then touch 'wf_dir/file.txt'"` then `angela workflows run file_ops` (Verify dir/file created, then cleanup)

*   **3.4. Rollback for File System Operations:**
    1.  `angela files mkdir rollback_dir_test` then `angela rollback last` (Verify directory is removed)
    2.  `touch rollback_file_test.txt; angela files rm rollback_file_test.txt` then `angela rollback last` (Verify file is restored)
    3.  `echo "original" > rollback_overwrite.txt; angela request "write 'new content' to rollback_overwrite.txt"` (Confirm 'y') then `angela rollback last` (Verify "original" content is back)

---

**Phase 4: Basic Code Generation & Toolchain Integration**

*   **4.1. Single Code File Generation:**
    1.  `angela request "generate a python script named 'hello.py' that prints 'Hello Python'"` (Verify `hello.py` created with correct content)
    2.  `angela request "generate a javascript file 'greet.js' with a function that takes a name and returns 'Hello, name'"`
    3.  `angela request "generate a bash script 'backup.sh' to copy /mydata to /mybackup (use rsync)"`

*   **4.2. Basic Framework Project Scaffolding:**
    1.  `angela generate create-framework-project react "my-simple-react-app"` (Verify basic CRA-like structure: `public/`, `src/App.js`, `src/index.js`, `package.json`)
    2.  `angela generate create-framework-project flask "my-basic-flask-app"` (Verify `app.py`, `templates/`, `static/`, `requirements.txt`)
    3.  `angela generate create-framework-project express "my-express-api"` (Verify `app.js`, `routes/`, `views/`, `package.json`)

*   **4.3. Git Integration:**
    1.  `mkdir git_test_repo; cd git_test_repo; angela request "initialize git here with main branch and a python gitignore"` (Verify `.git` and `.gitignore` created)
    2.  `echo "test" > test.txt; angela request "stage test.txt"` (Verify `git status` shows staged)
    3.  `angela request "commit staged files with message 'Test commit'"` (Verify `git log`)

*   **4.4. Package Manager Integration (Install):**
    1.  (In a new Python project dir) `echo "requests" > requirements.txt; angela request "install dependencies"` (Verify `requests` is installed in current env or venv)
    2.  (In a new Node project dir) `npm init -y; angela request "install lodash for this project"` (Verify `lodash` in `package.json` and `node_modules`)
    3.  (In a new Ruby project dir) `bundle init; angela request "add the 'colorize' gem"` (Verify `Gemfile` updated and gem installed)

*   **4.5. Basic Docker Operations (CLI & Toolchain):**
    1.  `angela docker status` (Verify it shows Docker availability)
    2.  (In a Python project with `app.py` and `requirements.txt`) `angela request "generate a dockerfile for this python app"` (Verify `Dockerfile` created)
    3.  (With a valid Dockerfile) `angela request "build docker image here and tag it test-angela-img:latest"` (Verify image built)

---

**Phase 5: Advanced Code Generation & Semantic Understanding**

*   **5.1. Semantic Analysis Core:**
    1.  `echo "def my_func(a, b):\n  \"\"\"This is a test function.\"\"\"\n  return a + b" > sem_test.py; angela request "analyze sem_test.py"` (Verify semantic analyzer output for functions, docstrings)
    2.  `echo "class MyClass:\n  def method1(self):\n    pass" >> sem_test.py; angela request "analyze sem_test.py"` (Verify class and method detection)
    3.  (Create a small project with inter-file imports) `angela request "analyze the semantic relationships in this project"` (Verify `SemanticContextManager` provides some relationship data)

*   **5.2. Project Architecture Planning:**
    1.  `angela generate create-complex-project "A Python Flask API with user authentication and a PostgreSQL database for storing notes"` (Focus on the *plan* generated, not necessarily full execution yet. Verify components like "UserAuthComponent", "NotesDBComponent", "APIControllerComponent" are planned).
    2.  `angela generate create-complex-project "A simple CLI tool in Go to manage a todo list stored in a local JSON file"` (Verify a simpler architecture is planned).
    3.  `angela generate create-complex-project "React frontend for an e-commerce site with product listing, cart, and checkout"` (Verify frontend components like "ProductListComponent", "ShoppingCartComponent" are planned).

*   **5.3. Multi-File Code Generation with Context:**
    1.  (Using a plan from 5.2 or a simplified one) `angela generate create-complex-project "Python project with a User model in models.py and a UserService in services.py that uses the User model"` (Verify `services.py` correctly imports `User` from `models.py`).
    2.  `angela generate create-complex-project "Node.js Express app with routes in routes/userRoutes.js and controllers in controllers/userController.js, where routes call controller functions"` (Verify connections).
    3.  `angela generate create-complex-project "Java Spring Boot app with an Entity class and a Repository interface for it"` (Verify repository uses the entity).

*   **5.4. Code Refinement with Feedback:**
    1.  (After generating a file `data_processor.py` with a function `process_data`) `angela generate refine-code "in data_processor.py, make the process_data function handle potential file not found errors" --apply`
    2.  (Generate a class) `angela generate refine-code "add a constructor to MyGeneratedClass that accepts name and age" --file MyGeneratedClass.java --apply`
    3.  (Generate a script) `angela generate refine-code "optimize the main loop for better performance" --file script.sh --apply`

*   **5.5. Documentation Generation:**
    1.  (After generating a small project) `angela generate readme .` (Verify a reasonable README.md is created).
    2.  (With a Python file containing classes and functions with docstrings) `angela generate api-docs my_module.py` (Verify API documentation structure).
    3.  (After generating a project) `angela generate user-guide .` (Verify a basic user guide structure).

---

**Phase 6: Advanced Planning, Workflows & Universal CLI**

*   **6.1. Advanced Task Planning (Loops, Decisions):**
    1.  `angela request "for each file in the current directory, if it's a .log file, print its first 3 lines"`
    2.  `angela request "check if 'my_service' is running; if yes, get its logs; if no, try to start it"`
    3.  `angela request "loop 5 times: create a file named loop_test_\$INDEX.txt, then sleep for 1 second (replace \$INDEX with loop number)"`

*   **6.2. Semantic Task Planning & Clarification:**
    1.  (In a project with `UserV1.py` and `UserV2.py`) `angela request "update the login function to use the User model"` (Verify it asks which User model).
    2.  `angela request "refactor the data processing module"` (If multiple modules seem data-related, verify clarification).
    3.  `angela request "connect to the database and fetch users"` (If multiple DB configs or no clear DB setup, verify clarification).

*   **6.3. Universal CLI Translator (Single Tool):**
    1.  `angela request "using aws s3, list all objects in my-bucket-name"`
    2.  `angela request "with kubectl, scale deployment my-app to 3 replicas in namespace prod"`
    3.  `angela request "use ffmpeg to extract audio from video.mp4 into audio.mp3"`

*   **6.4. Complex Workflow Planner & Cross-Tool Engine:**
    1.  `angela request "git clone myrepo.git, then cd into it, run npm install, and then run npm start"`
    2.  `angela request "build my docker image from the current Dockerfile, tag it myapp:v1, push it to my-docker-registry/myapp:v1, and then update my kubernetes deployment 'my-app-deployment' to use this new image"`
    3.  `angela request "create a new feature branch 'new-ui', make a small change to 'src/App.js' (e.g., add a comment), commit it, push the branch, and create a pull request on GitHub"` (This is very advanced, might require GitHub CLI or API interaction).

---

**Phase 7: Monitoring, Proactive Assistance & Shell Integration**

*   **7.1. Shell Hooks & Notification Handling:**
    1.  (With enhanced shell integration active) Run `cd /tmp; ls -l; git status` (in a non-git dir). Check Angela's logs for `pre_exec`, `post_exec`, `dir_change` notifications.
    2.  Run a command that fails, e.g., `cat non_existent_file`. Verify `post_exec` notification includes the error code.
    3.  Run a long command like `sleep 5`. Verify duration is captured.

*   **7.2. Background Monitoring & Basic Insights:**
    1.  (With `--monitor` active, in a git repo) Make some file changes but don't commit. Wait a minute. Verify `BackgroundMonitor` (or `ProactiveAssistant` via callback) logs detection or suggests a commit.
    2.  (If disk space monitoring is robust) Fill up a significant portion of disk (in a VM!). Verify a warning.
    3.  Modify a Python file to introduce a syntax error. Save it. Verify `BackgroundMonitor` (file watcher part) detects it and `ProactiveAssistant` suggests.

*   **7.3. Proactive Assistant & Suggestions:**
    1.  Run `gs tatus` (typo). Verify `ProactiveAssistant` (via `NotificationHandler`'s error analysis) suggests `git status`.
    2.  Run `rm -rf some_dir` (after creating it). If this is a common pattern for the user that Angela could automate (e.g., always followed by `mkdir some_dir`), verify if a workflow suggestion appears. (This is advanced).
    3.  Let a local dev server (e.g., Flask on port 5000) crash. Verify `NetworkMonitor` detects it and `ProactiveAssistant` suggests checking logs or restarting.

*   **7.4. Command Completion:**
    1.  Type `angela f<TAB>`. Verify `files` and `fix` are suggested.
    2.  Type `angela files mk<TAB>`. Verify `mkdir` is suggested.
    3.  Type `angela files ls ./my_d<TAB>` (assuming `my_dir/` exists). Verify `my_dir/` is completed.
    4.  Type `angela fix git <TAB>`. Verify contextual suggestions like "last commit" or "merge conflict" appear.

---

This list should provide a solid foundation for testing each aspect of Angela. Remember to adapt the specific commands and expected outcomes to the actual implementation details as you build them out!
