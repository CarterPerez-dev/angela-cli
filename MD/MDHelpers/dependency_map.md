# Dependency Map of angela/

| Module | Exported Components | Imported By |
|--------|---------------------|------------|
| `ai/analyzer.py` | `error_analyzer` | `execution/error_recovery.py`, `monitoring/notification_handler.py` |
| `ai/client.py` | `gemini_client`, `GeminiRequest` | Multiple modules throughout the application |
| `ai/parser.py` | `parse_ai_response`, `CommandSuggestion` | Orchestrator modules, CLI modules |
| `ai/prompts.py` | `build_prompt` | Multiple modules that interact with AI |
| `ai/content_analyzer.py` | `content_analyzer` | Context modules, CLI modules |
| `ai/confidence.py` | `confidence_scorer` | Execution modules, orchestrator |
| `ai/semantic_analyzer.py` | `semantic_analyzer` | Enhanced prompt modules, context modules |
| `monitoring/background.py` | `background_monitor` | Application initialization, CLI modules |
| `monitoring/network_monitor.py` | `network_monitor` | `background.py` |
| `review/diff_manager.py` | `diff_manager` | `feedback.py`, code modification modules |
| `review/feedback.py` | `feedback_manager` | CLI modules, orchestration |
| `utils/logging.py` | `setup_logging`, `get_logger` | Almost every module |
| `utils/enhanced_logging.py` | `EnhancedLogger` | Currently used as a fallback option |
| `cli/__init__.py` | `app` | `__main__.py`, application entry points |
| `execution/engine.py` | `execution_engine` | `adaptive_engine.py`, `orchestrator.py`, CLI modules |
| `execution/adaptive_engine.py` | `adaptive_engine` | `orchestrator.py`, higher-level execution modules |
| `execution/rollback.py` | `rollback_manager` | CLI rollback commands, filesystem operations |
| `execution/filesystem.py` | File operation functions | CLI file commands, execution modules |
| `safety/classifier.py` | `classify_command_risk`, `analyze_command_impact` | `check_command_safety`, adaptive engines |
| `safety/validator.py` | `validate_command_safety` | `check_command_safety`, safety checks |
| `safety/preview.py` | `generate_preview` | `check_command_safety`, confirmation handlers |
| `safety/confirmation.py` | `get_confirmation` | `check_command_safety`, CLI modules |
| `safety/adaptive_confirmation.py` | `get_adaptive_confirmation` | Adaptive execution engines, CLI modules |
| `workflows/__init__.py` | `workflow_manager`, `workflow_sharing_manager` | CLI modules, orchestration modules |
| `workflows/manager.py` | `workflow_manager` | `workflows/__init__.py`, CLI modules |
| `workflows/sharing.py` | `workflow_sharing_manager` | `workflows/__init__.py`, CLI workflow commands |
| `shell/__init__.py` | `terminal_formatter`, `inline_feedback`, `completion_handler` | Execution modules, CLI modules, orchestrator |
| `shell/formatter.py` | `terminal_formatter` | `shell/__init__.py`, `shell/advanced_formatter.py` |
| `shell/advanced_formatter.py` | (extends `terminal_formatter`) | Loaded by `shell/__init__.py` |
| `shell/inline_feedback.py` | `inline_feedback` | `shell/__init__.py`, CLI modules |
| `shell/completion.py` | `completion_handler` | `shell/__init__.py`, CLI modules |
| `integrations/__init__.py` | `semantic_integration`, `phase12_integration` | Modules that need these specific integrations |
| `integrations/enhanced_planner_integration.py` | (applies patches via side effects) | Loaded during application initialization |
| `integrations/semantic_integration.py` | `semantic_integration` | `integrations/__init__.py`, context modules |
| `integrations/phase12_integration.py` | `phase12_integration` | `integrations/__init__.py`, orchestration modules |
| `context/__init__.py` | All listed in `__all__` | Application-wide modules |
| `context/manager.py` | `context_manager` | Many core modules, orchestration |
| `context/file_detector.py` | `detect_file_type`, `get_content_preview` | File operations, content analysis |
| `context/file_resolver.py` | `file_resolver` | CLI file commands, path resolution |
| `context/history.py` | `history_manager` | Command suggestions, error recovery |
| `context/preferences.py` | `preferences_manager` | Confirmation handlers, session management |
| `context/session.py` | `session_manager` | File operations, context tracking |
| `context/file_activity.py` | `file_activity_tracker`, `ActivityType` | Activity monitoring, semantic analysis |
| `context/enhancer.py` | `context_enhancer` | Project awareness, AI integration |
| `context/project_inference.py` | `project_inference` | Project detection, code generation |
| `context/enhanced_file_activity.py` | `enhanced_file_activity_tracker` | Code-aware operations |
| `context/semantic_context_manager.py` | `semantic_context_manager` | AI interactions, code understanding |
| `context/project_state_analyzer.py` | `project_state_analyzer` | Project monitoring, suggestions |
| `generation/__init__.py` | All listed in `__all__` | Application-wide modules |
| `generation/architecture.py` | `architectural_analyzer`, `analyze_project_architecture` | Code structure analysis use cases |
| `generation/documentation.py` | `documentation_generator` | CLI documentation commands, project operations |
| `generation/engine.py` | `code_generation_engine`, `CodeFile`, `CodeProject` | Code generation use cases, CLI commands |
| `generation/frameworks.py` | `framework_generator` | Project scaffolding, templating systems |
| `generation/validators.py` | `validate_code` | Code generation, quality checking |
| `generation/refiner.py` | `interactive_refiner` | Interactive code improvement workflows |
| `generation/planner.py` | `project_planner`, `ProjectArchitecture` | Project scaffolding, architecture design |
| `generation/context_manager.py` (referenced) | `generation_context_manager` | Code generation modules |
| `intent/models.py` | `IntentType`, `Intent`, `ActionPlan` | `intent/planner.py`, `orchestrator.py`, CLI modules |
| `intent/planner.py` | `PlanStep`, `TaskPlan`, `PlanStepType`, `AdvancedPlanStep`, `AdvancedTaskPlan`, `task_planner` | `intent/enhanced_task_planner.py`, `execution/engine.py`, `execution/adaptive_engine.py` |
| `intent/enhanced_task_planner.py` | `EnhancedTaskPlanner`, `enhanced_task_planner`, `StepExecutionContext`, `DataFlowVariable`, `ExecutionResult` | `intent/semantic_task_planner.py`, `intent/complex_workflow_planner.py`, `integrations/enhanced_planner_integration.py` |
| `intent/semantic_task_planner.py` | `IntentClarification`, `SemanticTaskPlanner`, `semantic_task_planner` | `orchestrator.py`, CLI command modules, `integrations/semantic_integration.py` |
| `intent/complex_workflow_planner.py` | `WorkflowStepType`, `WorkflowVariable`, `WorkflowStepDependency`, `WorkflowStep`, `ComplexWorkflowPlan`, `complex_workflow_planner` | `workflows/manager.py`, `cli/workflows.py`, orchestration modules |
| `toolchain/__init__.py` | `git_integration`, `package_manager_integration`, `docker_integration`, `universal_cli_translator`, `ci_cd_integration`, `enhanced_universal_cli`, `cross_tool_workflow_engine` | `angela/__init__.py` (init_application), CLI modules |
| `toolchain/git.py` | `git_integration` | `toolchain/__init__.py`, generation modules, project-related operations |
| `toolchain/package_managers.py` | `package_manager_integration` | `toolchain/__init__.py`, generation modules, project dependency management |
| `toolchain/docker.py` | `docker_integration` | `toolchain/__init__.py`, `angela/__init__.py` (initialization), CLI docker commands |
| `toolchain/unviversal_cli.py` | `universal_cli_translator` | `toolchain/__init__.py`, `toolchain/enhanced_universal_cli.py`, orchestration modules |
| `toolchain/ci_cd.py` | `ci_cd_integration` | `toolchain/__init__.py`, generation modules, CI/CD workflows |
| `toolchain/enhanced_universal_cli.py` | `enhanced_universal_cli` | `toolchain/__init__.py`, `toolchain/cross_tool_workflow_engine.py`, orchestration modules |
| `toolchain/cross_tool_workflow_engine.py` | `cross_tool_workflow_engine` | `toolchain/__init__.py`, workflow modules, CLI workflow commands |
| `interfaces/__init__.py` | `CommandExecutor`, `AdaptiveExecutor`, `SafetyValidator` | Implementation classes throughout the application |
| `interfaces/execution.py` | `CommandExecutor`, `AdaptiveExecutor` | `interfaces/__init__.py`, concrete executor implementations |
| `interfaces/safety.py` | `SafetyValidator` | `interfaces/__init__.py`, concrete safety validator implementations |
| `core/__init__.py` | `registry`, `ServiceRegistry`, `event_bus`, `EventBus` | Application-wide for dependency and event management |
| `core/registry.py` | `registry`, `ServiceRegistry` | `core/__init__.py`, dependency resolution throughout app |
| `core/events.py` | `event_bus`, `EventBus` | `core/__init__.py`, event-based communication throughout app |
