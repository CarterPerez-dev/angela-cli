Okay, Principal Architect, this is a fantastic and highly ambitious vision! To test the "phases 1-12" (which I'm interpreting as the foundational CLI engine, context awareness, basic NLU, and initial tool integrations before the full-blown AGI capabilities), we need commands that probe these diverse aspects.

Here's a list of ~30 commands designed to cover a wide range of Angela CLI's envisioned abilities. These commands assume that the underlying NLU can map these natural language requests to the appropriate internal actions, even if the full "AGI" decision-making isn't there yet.

**Assumptions for these test commands:**
*   Angela CLI is invoked by typing `Angela ...` or that the shell hook correctly passes the entire line to your Python backend.
*   Phases 1-12 have implemented at least rudimentary versions of context detection (project root, current dir), argument parsing, file system interaction, and basic integrations with tools like Git and Docker.
*   The NLU can differentiate between a command *for* Angela and a command Angela should *translate* or *execute*.

---

### Angela CLI Test Commands (Phases 1-12 Focus)

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

This list should provide a solid starting point for testing the breadth of functionalities you're aiming for in the initial phases. As you test, you'll naturally identify more specific edge cases and variations for each command. Remember to adapt these based on what's actually implemented in your "phases 1-12."
