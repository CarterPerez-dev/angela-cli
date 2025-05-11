
**I. Basic Interaction & Context Awareness:**

1.  **`Angela, what is the current directory?`**
    *   *Tests:* Basic NLU, context awareness (PWD).
2.  **`Angela, identify the project root.`**
    *   *Tests:* Project root detection (.git, etc.).
3.  **`Angela, what type of project is this?`**
    *   *Tests:* Project type inference (Python, Node.js, etc.).
4.  **`Angela, show me your version.`**
    *   *Tests:* Basic command execution, version information retrieval.
5.  **`Angela, explain the `grep` command.`**
    *   *Tests:* NLU for meta-queries, potential knowledge base or help invocation.

**II. File System Operations:**

6.  **`Angela, create a new directory named 'docs/images'.`**
    *   *Tests:* File system interaction (mkdir -p), path handling.
7.  **`Angela, list all Python files in the 'src' folder.`**
    *   *Tests:* File system interaction (find/ls), filtering, path handling.
8.  **`Angela, create a file named 'config.yaml' in the project root with the content 'debug: true'.`**
    *   *Tests:* File creation, content writing, project root context.
9.  **`Angela, show me the content of 'README.md'.`**
    *   *Tests:* File reading, console output.
10. **`Angela, delete all files ending with '.tmp' in the current directory.`**
    *   *Tests:* File deletion, pattern matching, confirmation (if implemented).
11. **`Angela, rename 'old_feature.py' to 'new_feature.py' in the 'services' module.`**
    *   *Tests:* File renaming, path resolution within project context.

**III. Version Control (Git Integration):**

12. **`Angela, what is the current git status?`**
    *   *Tests:* Git integration, command execution, output parsing.
13. **`Angela, show me the differences in the last commit.`**
    *   *Tests:* Git integration (`git show` or `git diff HEAD^ HEAD`).
14. **`Angela, create a new git branch named 'feature/user-profile'.`**
    *   *Tests:* Git branch creation.
15. **`Angela, commit all staged changes with the message "Refactor: Improved logging utility".`**
    *   *Tests:* Git commit, argument handling (commit message).
16. **`Angela, switch to the 'develop' branch.`**
    *   *Tests:* Git checkout.

**IV. Container Management (Docker Integration):**

17. **`Angela, list all running docker containers.`**
    *   *Tests:* Docker integration (`docker ps`), output parsing.
18. **`Angela, show the logs for the 'webserver' docker container.`**
    *   *Tests:* Docker logs, container identification.
19. **`Angela, restart the 'database' docker container.`**
    *   *Tests:* Docker restart.
20. **`Angela, build the docker image in the current directory and tag it as 'my-app:latest'.`**
    *   *Tests:* Docker build, argument/option handling.

**V. Code Generation & Manipulation (Early Stages):**

21. **`Angela, generate a Python function in 'utils.py' that calculates the factorial of a number.`**
    *   *Tests:* Basic code generation, file targeting, understanding of programming constructs.
22. **`Angela, create a new Python file 'models.py' with a User class having 'id', 'username', and 'email' attributes.`**
    *   *Tests:* File creation, class structure generation.
23. **`Angela, in 'main.py', add a placeholder comment '# TODO: Implement error handling' before the main function.`**
    *   *Tests:* Simple content manipulation, code structure awareness.

**VI. Multi-Step Intentions & Workflow (Early Stages):**

24. **`Angela, create a new Python project named 'my_new_lib', initialize git, and create a 'setup.py' and a 'README.md'.`**
    *   *Tests:* Multi-step task decomposition (directory creation, git init, file creation).
25. **`Angela, create a feature branch 'docs-update', add a file 'CONTRIBUTING.md', and stage it.`**
    *   *Tests:* Git operations + file operations sequence.

**VII. Universal CLI Translation (Early Stages):**

26. **`Angela, how do I list all files larger than 10MB in the current directory using the shell?`**
    *   *Tests:* NLU to shell command translation (e.g., `find . -size +10M`).
27. **`Angela, use the 'aws' tool to list my S3 buckets.`**
    *   *Tests:* Specific tool invocation, parameter mapping (even if just `--help` based initially).

**VIII. Contextual Dependency Management (Early Stages):**

28. **`Angela, add 'requests' to my Python project's dependencies.`**
    *   *Tests:* Project type context, package manager interaction (`pip install requests`, update `requirements.txt`).
29. **`Angela, install the 'lodash' package for this Node.js project.`**
    *   *Tests:* Project type context, package manager interaction (`npm install lodash` or `yarn add lodash`, update `package.json`).

**IX. Testing Help and Error Handling:**

30. **`Angela, help me with the 'docker run' command.`**
    *   *Tests:* Invoking help for a specific external tool.
31. **`Angela, what went wrong with my last command?`** (Assuming some basic error logging/recall)
    *   *Tests:* Error context recall, basic diagnostic capability.

---
Okay, here are 50 commands and natural language scenarios to test out Angela, designed to cover a wide range of its capabilities:

**Core `angela request` (Natural Language Focus):**

1.  "angela list all files in the current directory, including hidden ones"
2.  "angela what's the git status of this project? I want a summary."
3.  "angela find all python files in `src/` modified in the last 2 days"
4.  "angela create a new directory called 'temp_project' and then a file 'notes.txt' inside it with the content 'Initial notes.'"
5.  "angela show me the disk usage for my home folder in a human-readable format"
6.  "angela search for 'TODO: Refactor' in all `*.py` files within the 'lib' directory."
7.  "angela suggest a command to compress the 'archive_data' folder into a tar.gz file named 'backup.tar.gz'"
8.  "angela how do I check my current python version and where is it installed?"
9.  "angela what are the main dependencies of this Node.js project?"
10. "angela I want to delete all `.log` files in the `logs` directory, but show me what you'd do first."
11. "angela explain the 'process_data' function in 'parser.py'"
12. "angela what other functions call 'get_user_details' in my project?"

**File Operations (`angela files ...` and Natural Language Equivalents):**

13. `angela files ls --all --long ./docs`
14. "angela make a new folder structure 'data/raw/images' for me"
15. `angela files rmdir old_project_files --recursive --force`
16. "angela display the 'config.yaml' file with syntax highlighting"
17. `angela files cp ./src/main.py ./backup/main_v2.py --force`
18. "angela append 'new log entry' to 'application.log'"
19. `angela files find "*.md" --path ./documentation --hidden`
20. "angela give me detailed info about 'README.md' and show me the first 20 lines"
21. `angela files resolve "the main configuration file for the API"`
22. `angela files recent --limit 3 --type created`
23. `angela files project`

**Docker Operations (`angela docker ...` and Natural Language Equivalents):**

24. `angela docker status`
25. "angela list all docker containers, even stopped ones, but just show their IDs"
26. `angela docker logs my_api_container --follow --tail 50 --timestamps`
27. "angela start the docker container named 'postgres_db_server'"
28. `angela docker rmi old_app_image:v1.0 --force`
29. "angela build a docker image from the current directory, tag it 'web-app:latest', and don't use cache"
30. `angela docker run -p 3000:80 -v $(pwd)/public:/usr/share/nginx/html --name my-nginx-instance nginx:alpine --rm`
31. "angela bring up my docker-compose setup in detached mode, rebuilding images if necessary"
32. `angela docker generate-dockerfile . --output Dockerfile.prod --overwrite`
33. `angela docker setup . --no-compose --build`

**Code Generation (`angela generate ...` and Natural Language Equivalents):**

34. "angela create a new Python Flask project for a simple URL shortener, initialize git, and set up basic tests"
35. `angela generate add-feature "implement user profile page with edit functionality" --project_dir ./my-webapp --branch feature/user-profile --generate_tests --auto_commit`
36. "angela refine the 'data_processing.py' file. The 'parse_csv' function is too slow and lacks proper error handling. Apply the changes and create a backup."
37. `angela generate generate-ci gitlab_ci --project_dir ./my-monorepo --project_type node`
38. "angela create a complex project: a microservices-based e-commerce platform with a React frontend, Python (FastAPI) backend for orders, and a Go backend for inventory. Use detailed planning."
39. `angela generate create-framework-project spring "A REST API for managing book inventory" --output_dir my_book_api --with_auth --install_deps`
40. `angela generate generate-tests --project_dir ./my-rust-lib --test_framework cargo-test --focus "src/utils/*.rs"`

**Rollback & Workflow Operations (`angela rollback ...`, `angela workflows ...`):**

41. `angela rollback list --limit 5 --transactions`
42. "angela undo the last file deletion I did"
43. `angela workflows create backup_logs --description "Backup all .log files to archive folder"` (This will likely be interactive to define steps)
44. "angela run the 'deploy_staging' workflow and set the version to 'v1.2.3'"
45. `angela workflows export deploy_staging --output ./deploy_staging_workflow.zip`

**Other Commands & Scenarios:**

46. `angela init` (Test initialization, especially if config is missing/corrupt)
47. `angela status` (Check overall system status and integrations)
48. `angela shell` (Then type a few commands like `list files in /tmp` or `what is the current git branch?`)
49. "angela I want to create a file named 'test.txt' and then another one called 'test.txt'. What happens?" (Tests error handling or overwrite logic for file creation)
50. "angela I need to find a document about 'API rate limits' or maybe it was 'throttling', it's a markdown file in the 'docs' or 'wiki' folder." (Tests ambiguous file reference and content search)
