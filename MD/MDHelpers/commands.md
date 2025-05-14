Okay, this is a great way to systematically test Angela CLI! I'll provide a list of commands progressing from basic to more complex, along with three key files involved in making each command work.

Please note:
*   "Key files" are a simplification. Real execution paths can be more intricate. I'll focus on the command definition, primary processing, and core logic.
*   `orchestrator.py` is central to many `angela request "..."` commands. I'll specify the main functions involved.
*   For CLI subcommands (e.g., `angela files ls`), the flow often goes from the Typer app definition to an API layer or directly to the component.

Here's a list of commands to test Angela CLI, working your way up:

**Level 1: Basic CLI & Info**

1.  `angela --version`
    *   `__main__.py` (Entry point, calls `init_application`)
    *   `components/cli/main.py` (Typer app definition, `version_callback`)
    *   `__init__.py` (Contains `__version__`)
2.  `angela --help`
    *   `__main__.py` (Entry point)
    *   `components/cli/main.py` (Typer app definition, Typer handles help)
    *   `api/cli.py` (Registers sub-apps, contributing to help text)
3.  `angela init`
    *   `components/cli/main.py` (Typer app definition for `init`)
    *   `orchestrator.py` (Likely a simple passthrough or direct call for `init`)
    *   `config.py` (Handles configuration loading/saving)
4.  `angela status`
    *   `components/cli/main.py` (Typer app definition for `status`)
    *   `orchestrator.py` (Likely a simple passthrough or direct call for `status`)
    *   `components/context/manager.py` (Provides context for status)

**Level 2: Simple Natural Language Requests (Command Suggestion & Execution)**

5.  `angela request "list files in current directory"`
    *   `components/cli/main.py` (Defines `request` command)
    *   `orchestrator.py` (`process_request`, `_process_command_request`, `_get_ai_suggestion`)
    *   `components/ai/client.py` (Or `prompts.py` / `parser.py` for AI interaction)
6.  `angela request "show disk usage"`
    *   `components/cli/main.py`
    *   `orchestrator.py` (`process_request`, `_process_command_request`, `_get_ai_suggestion`)
    *   `components/ai/prompts.py` (For building the prompt to the AI)
7.  `angela request "what is my current directory"`
    *   `components/cli/main.py`
    *   `orchestrator.py` (`process_request`, `_process_command_request`, `_get_ai_suggestion`)
    *   `components/ai/parser.py` (For parsing the AI's response)
8.  `angela request "create a new directory called my_project"`
    *   `components/cli/main.py`
    *   `orchestrator.py` (`process_request`, `_process_command_request`, `_get_ai_suggestion`)
    *   `components/execution/engine.py` (If executed, or `safety/confirmation.py` if confirmation needed)
9.  `angela request "touch a file named example.txt"`
    *   `components/cli/main.py`
    *   `orchestrator.py` (`process_request`, `_process_command_request`, `_get_ai_suggestion`)
    *   `components/execution/adaptive_engine.py` (Handles confirmation and execution flow)
10. `angela request "find all python files here" --suggest-only`
    *   `components/cli/main.py`
    *   `orchestrator.py` (`process_request`, `_process_command_request`, `_get_ai_suggestion` - `execute` flag will be false)
    *   `components/shell/formatter.py` (For displaying the suggestion)

**Level 3: File Operations (CLI Subcommands)**

11. `angela files ls`
    *   `components/cli/files.py` (Typer app definition for `ls`)
    *   `api/cli.py` (Registers `files_app` to main app)
    *   `components/context/manager.py` (`get_directory_contents`)
12. `angela files mkdir test_cli_dir`
    *   `components/cli/files.py` (Typer app definition for `mkdir`)
    *   `api/cli.py`
    *   `components/execution/filesystem.py` (`create_directory` via `api/execution.py`)
13. `angela files cat README.md` (assuming README.md exists)
    *   `components/cli/files.py` (Typer app definition for `cat`)
    *   `api/cli.py`
    *   `components/execution/filesystem.py` (`read_file` via `api/execution.py`)
14. `angela files write new_file.txt --content "Hello Angela"`
    *   `components/cli/files.py` (Typer app definition for `write`)
    *   `api/cli.py`
    *   `components/execution/filesystem.py` (`write_file` via `api/execution.py`)
15. `angela files rm new_file.txt --force` (use with caution)
    *   `components/cli/files.py` (Typer app definition for `rm`)
    *   `api/cli.py`
    *   `components/execution/filesystem.py` (`delete_file` via `api/execution.py`)
16. `angela files info .`
    *   `components/cli/files.py` (Typer app definition for `info`)
    *   `api/cli.py`
    *   `components/context/manager.py` (`get_file_info`)
17. `angela files find "*.py"`
    *   `components/cli/files.py` (Typer app definition for `find`)
    *   `api/cli.py`
    *   `components/context/manager.py` (`find_files`)

**Level 4: Context-Aware Requests** (Assumes you are in a Git Python project)

18. `angela request "what is my current git branch"` (inside a git repo)
    *   `components/cli/main.py`
    *   `orchestrator.py` (`process_request`, `_process_command_request`, `_get_ai_suggestion`, context passed to `build_prompt`)
    *   `components/context/manager.py` (Provides CWD, project root/type)
19. `angela request "show me python files modified recently"`
    *   `components/cli/main.py`
    *   `orchestrator.py` (`process_request`, `_process_command_request`, `_get_ai_suggestion`)
    *   `components/context/file_activity.py` (Accessed via `api/context.py` for recent files)
20. `angela files resolve README.md --scope project` (inside a project)
    *   `components/cli/files_extensions.py` (Defines `resolve` command)
    *   `api/cli.py` (Registers the files app)
    *   `components/context/file_resolver.py` (`resolve_reference` via `api/context.py`)
21. `angela files recent`
    *   `components/cli/files_extensions.py` (Defines `recent` command)
    *   `api/cli.py`
    *   `components/context/file_activity.py` (`get_recent_activities` via `api/context.py`)

**Level 5: Safety Features**

22. `angela request "delete all .tmp files"` (will trigger confirmation)
    *   `components/cli/main.py`
    *   `orchestrator.py` (`process_request`, `_process_command_request`, `execute_command`)
    *   `components/safety/adaptive_confirmation.py` (Via `api/safety.py` for `get_adaptive_confirmation`)
23. `angela request "sudo rm -rf /" --force` (SHOULD BE BLOCKED BY VALIDATOR)
    *   `components/cli/main.py`
    *   `orchestrator.py` (`process_request`, `_process_command_request`, then `adaptive_engine.execute_command`)
    *   `components/safety/validator.py` (`validate_command_safety` via `api/safety.py`)
24. `angela request "show me the contents of /etc/passwd"` (might trigger higher risk)
    *   `components/cli/main.py`
    *   `orchestrator.py` (`process_request`, `_process_command_request`)
    *   `components/safety/classifier.py` (`classify` via `api/safety.py`)
25. `angela request "run rm -rf test_cli_dir"` (after creating it, then trust it)
    *   `components/cli/main.py`
    *   `orchestrator.py` (`process_request`, `_process_command_request`, `adaptive_engine.execute_command`)
    *   `components/safety/adaptive_confirmation.py` (`offer_command_learning` after successful execution and confirmation)

**Level 6: Multi-Step Operations**

26. `angela request "create a directory logs and then create a file app.log inside it"`
    *   `components/cli/main.py`
    *   `orchestrator.py` (`process_request`, `_determine_request_type` -> `MULTI_STEP`, `_process_multi_step_request`)
    *   `components/intent/planner.py` (`plan_task` via `api/intent.py`)
27. `angela request "list python files and then count them"`
    *   `components/cli/main.py`
    *   `orchestrator.py` (`process_request`, `_determine_request_type` -> `MULTI_STEP`, `_process_multi_step_request`)
    *   `components/intent/enhanced_task_planner.py` (If complexity is high, via `api/intent.py`)
28. `angela request "git add all files and then commit with message 'updates'"`
    *   `components/cli/main.py`
    *   `orchestrator.py` (`process_request`, `_determine_request_type` -> `MULTI_STEP`, `_process_multi_step_request`)
    *   `components/execution/rollback.py` (If `transaction_id` is created by orchestrator, via `api/execution.py`)

**Level 7: Workflow Management**

29. `angela workflows create my_workflow --description "Lists files and counts them"` (then enter steps interactively)
    *   `components/cli/workflows.py` (Typer app for `create`)
    *   `api/cli.py`
    *   `components/workflows/manager.py` (`define_workflow` via `api/workflows.py`)
30. `angela workflows list`
    *   `components/cli/workflows.py`
    *   `api/cli.py`
    *   `components/workflows/manager.py` (`list_workflows`)
31. `angela workflows run my_workflow`
    *   `components/cli/workflows.py`
    *   `api/cli.py`
    *   `components/workflows/manager.py` (`execute_workflow`)
32. `angela workflows export my_workflow --output my_workflow_export.zip`
    *   `components/cli/workflows.py`
    *   `api/cli.py`
    *   `components/workflows/sharing.py` (`export_workflow` via `api/workflows.py`)
33. `angela workflows import my_workflow_export.zip --rename imported_workflow`
    *   `components/cli/workflows.py`
    *   `api/cli.py`
    *   `components/workflows/sharing.py` (`import_workflow`)
34. `angela workflows delete imported_workflow --force`
    *   `components/cli/workflows.py`
    *   `api/cli.py`
    *   `components/workflows/manager.py` (`delete_workflow`)

**Level 8: Code Generation (Simple)**

35. `angela request "generate a python script that prints hello world"`
    *   `components/cli/main.py`
    *   `orchestrator.py` (`process_request`, `_determine_request_type` -> `CODE_GENERATION`, `_process_code_generation_request`)
    *   `components/generation/engine.py` (`generate_project` or similar method via `api/generation.py`)
36. `angela request "create a simple html file with a title 'My Page'"`
    *   `components/cli/main.py`
    *   `orchestrator.py` (`process_request`, `_process_code_generation_request`)
    *   `components/generation/planner.py` (If planning is involved via `api/generation.py`)

**Level 9: Toolchain Integration**

37. `angela request "initialize a git repository here"`
    *   `components/cli/main.py`
    *   `orchestrator.py` (`process_request`, `_determine_request_type` -> `TOOLCHAIN_OPERATION`, `_process_toolchain_operation`, `_process_git_operation`)
    *   `components/toolchain/git.py` (`init_repository` via `api/toolchain.py`)
38. `angela request "show me running docker containers"`
    *   `components/cli/main.py`
    *   `orchestrator.py` (`process_request`, `_process_toolchain_operation`, `_process_docker_operation`)
    *   `components/toolchain/docker.py` (`list_containers` via `api/toolchain.py`)
39. `angela docker ps` (CLI subcommand for Docker)
    *   `components/cli/docker.py` (Typer app for `ps`)
    *   `api/cli.py`
    *   `components/toolchain/docker.py` (`list_containers`)
40. `angela docker generate-dockerfile .` (for a Python project)
    *   `components/cli/docker.py`
    *   `api/cli.py`
    *   `components/toolchain/docker.py` (`generate_dockerfile`)
41. `angela request "install flask using pip"`
    *   `components/cli/main.py`
    *   `orchestrator.py` (`process_request`, `_process_toolchain_operation`, `_process_package_operation`)
    *   `components/toolchain/package_managers.py` (`install_dependencies` via `api/toolchain.py`)
42. `angela request "use git to show current branch"`
    *   `components/cli/main.py`
    *   `orchestrator.py` (`process_request`, `_determine_request_type` -> `UNIVERSAL_CLI`, `_process_universal_cli_request`)
    *   `components/toolchain/universal_cli.py` (`translate_request` via `api/toolchain.py`)

**Level 10: Advanced Code Generation & Refinement**

43. `angela generate create-project "a simple flask web app with a homepage"`
    *   `components/cli/generation.py` (Typer app for `create-project`)
    *   `api/cli.py`
    *   `components/generation/engine.py` (`generate_project`)
44. `angela generate add-feature "add a /about page to my flask app" --project-dir ./my_flask_app` (assuming `my_flask_app` exists)
    *   `components/cli/generation.py` (Typer app for `add-feature`)
    *   `api/cli.py`
    *   `components/generation/engine.py` (`add_feature_to_project`)
45. `angela generate refine-code "make this function more readable" ./my_flask_app/app.py --apply`
    *   `components/cli/generation.py` (Typer app for `refine-code`)
    *   `api/cli.py`
    *   `components/review/feedback.py` (`process_feedback`, `apply_refinements` via `api/review.py`)
46. `angela request "generate a django project for a blog"`
    *   `components/cli/main.py`
    *   `orchestrator.py` (`process_request`, `_process_code_generation_request`)
    *   `components/generation/frameworks.py` (`generate_framework_structure` or similar via `api/generation.py`)
47. `angela generate create-framework-project django "a blog platform"`
    *   `components/cli/generation.py`
    *   `api/cli.py`
    *   `components/generation/frameworks.py` (`generate_framework_structure`)
48. `angela generate create-complex-project "a web app with user auth, posts, and comments using Python and Flask"`
    *   `components/cli/generation.py`
    *   `api/cli.py`
    *   `components/generation/engine.py` (`generate_complex_project`)

**Level 11: Complex Workflows & Pipelines**

49. `angela request "setup a CI/CD pipeline for my python project on GitHub Actions"`
    *   `components/cli/main.py`
    *   `orchestrator.py` (`process_request`, `_determine_request_type` -> `CI_CD_PIPELINE`, `_process_ci_cd_pipeline_request`)
    *   `components/toolchain/ci_cd.py` (`create_complete_pipeline` via `api/toolchain.py`)
50. `angela request "create a workflow to build my docker image, tag it, and push to docker hub"`
    *   `components/cli/main.py`
    *   `orchestrator.py` (`process_request`, `_determine_request_type` -> `COMPLEX_WORKFLOW`, `_process_complex_workflow_request`)
    *   `components/toolchain/cross_tool_workflow_engine.py` (`create_workflow` via `api/toolchain.py`)
51. `angela generate generate-ci github_actions .` (in a project directory)
    *   `components/cli/generation.py`
    *   `api/cli.py`
    *   `components/toolchain/ci_cd.py` (`generate_ci_configuration`)
52. `angela request "analyze the architecture of this project"` (in a project directory)
    *   `components/cli/main.py`
    *   `orchestrator.py` (`process_request`, `_determine_request_type` -> `CODE_ARCHITECTURE`, `_process_code_architecture_request`)
    *   `components/generation/architecture.py` (`analyze_project_architecture` via `api/generation.py`)

**Level 12: Rollback & Monitoring** (Monitoring is harder to test with single commands)

53. `angela files mkdir new_dir_for_rollback`
    *   (Covered before)
54. `angela files rmdir new_dir_for_rollback`
    *   (Covered before)
55. `angela rollback list`
    *   `components/execution/rollback_commands.py` (Typer app for `list`)
    *   `api/cli.py`
    *   `components/execution/rollback.py` (`get_recent_operations` via `api/execution.py`)
56. `angela rollback operation <ID_FROM_LIST>` (replace with an actual ID)
    *   `components/execution/rollback_commands.py`
    *   `api/cli.py`
    *   `components/execution/rollback.py` (`rollback_operation`)
57. `angela request "create a file temp.txt then delete it" --force` (to generate a transaction)
    *   (Covered by multi-step, but with `--force` to ensure it runs)
58. `angela rollback list --transactions`
    *   `components/execution/rollback_commands.py`
    *   `api/cli.py`
    *   `components/execution/rollback.py` (`get_recent_transactions`)
59. `angela rollback transaction <TX_ID_FROM_LIST>` (replace with an actual transaction ID)
    *   `components/execution/rollback_commands.py`
    *   `api/cli.py`
    *   `components/execution/rollback.py` (`rollback_transaction`)
60. `angela request "show me logs for container my_app"` (assuming `my_app` container exists)
    *   `components/cli/main.py`
    *   `orchestrator.py` (`process_request`, `_process_toolchain_operation`, `_process_docker_operation`)
    *   `components/toolchain/docker.py` (`get_container_logs`)

This list should give you a solid progression for testing. Remember to adapt file names and specific arguments to your actual test setup. Good luck!
