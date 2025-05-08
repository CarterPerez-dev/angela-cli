# angela/cli/generation.py
"""
CLI interface for code generation features in Angela CLI.
"""
import os
import asyncio
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich import print as rich_print
from rich.prompt import Prompt, Confirm
from rich.markdown import Markdown


from angela.utils.logging import get_logger
from angela.generation.engine import code_generation_engine
from angela.toolchain.git import git_integration
from angela.toolchain.package_managers import package_manager_integration
from angela.toolchain.test_frameworks import test_framework_integration
from angela.toolchain.ci_cd import ci_cd_integration
from angela.review.diff_manager import diff_manager
from angela.review.feedback import feedback_manager
from angela.context import context_manager
from angela.generation.refiner import interactive_refiner
from angela.generation.context_manager import generation_context_manager


app = typer.Typer(help="Code generation commands")
console = Console()
logger = get_logger(__name__)

@app.command("create-project")
def create_project(
    description: str = typer.Argument(..., help="Description of the project to generate"),
    output_dir: str = typer.Option(".", help="Directory where the project should be generated"),
    project_type: Optional[str] = typer.Option(None, help="Project type (python, node, etc.)"),
    git_init: bool = typer.Option(True, help="Initialize Git repository"),
    install_deps: bool = typer.Option(False, help="Install dependencies"),
    generate_tests: bool = typer.Option(False, help="Generate test files"),
    ci_platform: Optional[str] = typer.Option(None, help="Generate CI configuration (github, gitlab, etc.)"),
    dry_run: bool = typer.Option(False, help="Preview without creating files")
):
    """
    Generate a complete project from a description.
    """
    console.print(Panel(
        f"[bold green]Generating project from description:[/bold green]\n{description}",
        title="Project Generation",
        expand=False
    ))
    
    try:
        # Get current context
        context = context_manager.get_context_dict()
        
        # Generate project plan
        project_plan = asyncio.run(code_generation_engine.generate_project(
            description=description,
            output_dir=output_dir,
            project_type=project_type,
            context=context
        ))
        
        # Display project plan
        console.print("\n[bold blue]Project Plan:[/bold blue]")
        console.print(f"Name: [bold]{project_plan.name}[/bold]")
        console.print(f"Type: [bold]{project_plan.project_type}[/bold]")
        console.print(f"Files: [bold]{len(project_plan.files)}[/bold]")
        
        # Show the list of files
        table = Table(title="Files to Generate")
        table.add_column("Path", style="cyan")
        table.add_column("Purpose", style="green")
        
        for file in project_plan.files:
            table.add_row(file.path, file.purpose)
        
        console.print(table)
        
        # Create the files if not dry run
        if not dry_run:
            console.print("\n[bold]Creating project files...[/bold]")
            
            with console.status("[bold green]Creating files...[/bold green]"):
                result = asyncio.run(code_generation_engine.create_project_files(project_plan))
            
            console.print(f"[green]Created {result['file_count']} files[/green]")
            
            # Initialize Git repository if requested
            if git_init:
                console.print("\n[bold]Initializing Git repository...[/bold]")
                
                with console.status("[bold green]Initializing Git...[/bold green]"):
                    git_result = asyncio.run(git_integration.init_repository(
                        path=output_dir,
                        initial_branch="main",
                        gitignore_template=project_plan.project_type
                    ))
                
                if git_result["success"]:
                    console.print("[green]Git repository initialized successfully[/green]")
                else:
                    console.print(f"[yellow]Failed to initialize Git repository: {git_result.get('error', 'Unknown error')}[/yellow]")
            
            # Install dependencies if requested
            if install_deps:
                console.print("\n[bold]Installing dependencies...[/bold]")
                
                with console.status("[bold green]Installing dependencies...[/bold green]"):
                    deps_result = asyncio.run(package_manager_integration.install_dependencies(
                        path=output_dir,
                        dependencies=project_plan.dependencies.get("runtime", []),
                        dev_dependencies=project_plan.dependencies.get("development", []),
                        project_type=project_plan.project_type
                    ))
                
                if deps_result["success"]:
                    console.print("[green]Dependencies installed successfully[/green]")
                else:
                    console.print(f"[yellow]Failed to install dependencies: {deps_result.get('error', 'Unknown error')}[/yellow]")
            
            # Generate test files if requested
            if generate_tests:
                console.print("\n[bold]Generating test files...[/bold]")
                
                with console.status("[bold green]Generating tests...[/bold green]"):
                    test_result = asyncio.run(test_framework_integration.generate_test_files(
                        src_files=project_plan.files,
                        project_type=project_plan.project_type,
                        root_dir=output_dir
                    ))
                
                if test_result["success"]:
                    console.print(f"[green]Generated {test_result['file_count']} test files[/green]")
                else:
                    console.print(f"[yellow]Failed to generate test files: {test_result.get('error', 'Unknown error')}[/yellow]")
            
            # Generate CI/CD configuration if requested
            if ci_platform:
                console.print("\n[bold]Generating CI/CD configuration...[/bold]")
                
                with console.status(f"[bold green]Generating {ci_platform} configuration...[/bold green]"):
                    ci_result = asyncio.run(ci_cd_integration.generate_ci_configuration(
                        path=output_dir,
                        platform=ci_platform,
                        project_type=project_plan.project_type
                    ))
                
                if ci_result["success"]:
                    console.print(f"[green]Generated {ci_platform} configuration successfully[/green]")
                else:
                    console.print(f"[yellow]Failed to generate CI/CD configuration: {ci_result.get('error', 'Unknown error')}[/yellow]")
            
            # Create initial commit if Git was initialized
            if git_init:
                console.print("\n[bold]Creating initial commit...[/bold]")
                
                with console.status("[bold green]Creating commit...[/bold green]"):
                    commit_result = asyncio.run(git_integration.commit_changes(
                        path=output_dir,
                        message="Initial project generation",
                        auto_stage=True
                    ))
                
                if commit_result["success"]:
                    console.print("[green]Created initial commit successfully[/green]")
                else:
                    console.print(f"[yellow]Failed to create initial commit: {commit_result.get('error', 'Unknown error')}[/yellow]")
            
            console.print(f"\n[bold green]Project generated successfully in: {output_dir}[/bold green]")
        else:
            console.print("\n[bold yellow]Dry run - no files were created[/bold yellow]")
    
    except Exception as e:
        logger.exception("Error generating project")
        console.print(f"[bold red]Error generating project:[/bold red] {str(e)}")

@app.command("add-feature")
def add_feature(
    description: str = typer.Argument(..., help="Description of the feature to add"),
    project_dir: str = typer.Option(".", help="Project directory"),
    branch: Optional[str] = typer.Option(None, help="Create a feature branch"),
    generate_tests: bool = typer.Option(False, help="Generate test files"),
    install_deps: bool = typer.Option(False, help="Install new dependencies"),
    dry_run: bool = typer.Option(False, help="Preview without creating files"),
    auto_commit: bool = typer.Option(False, help="Commit changes automatically")
):
    """
    Add a new feature to an existing project.
    """
    console.print(Panel(
        f"[bold green]Adding feature to project:[/bold green]\n{description}",
        title="Feature Addition",
        expand=False
    ))
    
    try:
        # Get current context
        context = context_manager.get_context_dict()
        context = asyncio.run(context_enhancer.enrich_context(context))
        
        # Check if project directory exists
        project_path = Path(project_dir)
        if not project_path.exists() or not project_path.is_dir():
            console.print(f"[bold red]Project directory does not exist: {project_dir}[/bold red]")
            return
        
        # Create a feature branch if requested
        if branch:
            console.print(f"\n[bold]Creating feature branch: {branch}[/bold]")
            
            if not dry_run:
                with console.status("[bold green]Creating branch...[/bold green]"):
                    branch_result = asyncio.run(git_integration.create_branch(
                        path=project_dir,
                        branch_name=branch,
                        checkout=True
                    ))
                
                if branch_result["success"]:
                    console.print(f"[green]Created and checked out branch: {branch}[/green]")
                else:
                    console.print(f"[yellow]Failed to create branch: {branch_result.get('error', 'Unknown error')}[/yellow]")
        
        # Get project info
        with console.status("[bold green]Analyzing project...[/bold green]"):
            # Detect project type
            project_type_result = asyncio.run(ci_cd_integration.detect_project_type(project_dir))
            project_type = project_type_result.get("project_type")
            
            if not project_type:
                console.print("[yellow]Could not detect project type. Proceeding anyway...[/yellow]")
            else:
                console.print(f"[green]Detected project type: {project_type}[/green]")
        
        # Generate feature implementation
        console.print("\n[bold]Generating feature implementation...[/bold]")
        
        with console.status("[bold green]Generating feature implementation...[/bold green]"):
            # Use the new feature addition method
            result = asyncio.run(code_generation_engine.add_feature_to_project(
                description=description,
                project_dir=project_dir,
                context=context
            ))
        
        if result["success"]:
            # Display results
            console.print(f"[green]Successfully added feature to project![/green]")
            
            if result.get("new_files"):
                console.print("\n[bold]Created Files:[/bold]")
                for file_path in result["new_files"]:
                    console.print(f"  ✅ {file_path}")
            
            if result.get("modified_files"):
                console.print("\n[bold]Modified Files:[/bold]")
                for file_path in result["modified_files"]:
                    console.print(f"  ✏️ {file_path}")
            
            # Generate tests if requested
            if generate_tests and not dry_run:
                console.print("\n[bold]Generating tests for new feature...[/bold]")
                
                with console.status("[bold green]Generating tests...[/bold green]"):
                    # Create a list of new files with CodeFile objects
                    src_files = []
                    for file_path in result.get("new_files", []):
                        try:
                            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                                content = f.read()
                                
                            rel_path = str(Path(file_path).relative_to(project_dir))
                            src_files.append(CodeFile(
                                path=rel_path,
                                content=content,
                                purpose=f"New feature: {description}",
                                dependencies=[],
                                language=project_type
                            ))
                        except Exception as e:
                            console.print(f"[yellow]Error reading file {file_path}: {str(e)}[/yellow]")
                    
                    if src_files:
                        test_result = asyncio.run(test_framework_integration.generate_test_files(
                            src_files=src_files,
                            project_type=project_type,
                            root_dir=project_dir
                        ))
                        
                        if test_result["success"]:
                            console.print(f"[green]Generated {test_result['file_count']} test files[/green]")
                        else:
                            console.print(f"[yellow]Failed to generate test files: {test_result.get('error', 'Unknown error')}[/yellow]")
                    else:
                        console.print("[yellow]No source files available for test generation[/yellow]")
            
            # Install dependencies if requested
            if install_deps and not dry_run:
                console.print("\n[bold]Installing dependencies...[/bold]")
                
                with console.status("[bold green]Extracting and installing dependencies...[/bold green]"):
                    # Extract dependencies from the feature files
                    dependencies = await code_generation_engine._extract_dependencies_from_feature(
                        feature_files={
                            "new_files": [{"path": path, "content": open(path, 'r', encoding='utf-8', errors='replace').read()} 
                                          for path in result.get("new_files", []) if Path(path).exists()],
                            "modified_files": [{"path": path, 
                                               "original_content": "", # We don't need original content for dependency extraction
                                               "modified_content": open(path, 'r', encoding='utf-8', errors='replace').read()} 
                                              for path in result.get("modified_files", []) if Path(path).exists()]
                        },
                        project_type=project_type
                    )
                    
                    if not dependencies["runtime"] and not dependencies["development"]:
                        console.print("[yellow]No new dependencies detected in the feature.[/yellow]")
                    else:
                        # Install the detected dependencies
                        runtime_deps = dependencies.get("runtime", [])
                        dev_deps = dependencies.get("development", [])
                        
                        if runtime_deps:
                            console.print(f"[bold]Runtime dependencies to install:[/bold] {', '.join(runtime_deps)}")
                            install_result = await package_manager_integration.install_dependencies(
                                path=project_dir,
                                dependencies=runtime_deps,
                                project_type=project_type
                            )
                            
                            if install_result["success"]:
                                console.print(f"[green]Successfully installed runtime dependencies[/green]")
                            else:
                                console.print(f"[yellow]Failed to install runtime dependencies: {install_result.get('error', 'Unknown error')}[/yellow]")
                        
                        if dev_deps:
                            console.print(f"[bold]Development dependencies to install:[/bold] {', '.join(dev_deps)}")
                            dev_install_result = await package_manager_integration.install_dependencies(
                                path=project_dir,
                                dependencies=[],
                                dev_dependencies=dev_deps,
                                project_type=project_type
                            )
                            
                            if dev_install_result["success"]:
                                console.print(f"[green]Successfully installed development dependencies[/green]")
                            else:
                                console.print(f"[yellow]Failed to install development dependencies: {dev_install_result.get('error', 'Unknown error')}[/yellow]")
    
    except Exception as e:
        logger.exception("Error adding feature")
        console.print(f"[bold red]Error adding feature:[/bold red] {str(e)}")

@app.command("refine-code")
def refine_code(
    feedback: str = typer.Argument(..., help="Feedback for code improvement"),
    file_path: str = typer.Argument(..., help="Path to the file to refine"),
    apply: bool = typer.Option(False, help="Apply the changes"),
    backup: bool = typer.Option(True, help="Create backup before applying changes")
):
    """
    Refine code based on feedback.
    """
    console.print(Panel(
        f"[bold green]Refining code based on feedback:[/bold green]\n{feedback}",
        title="Code Refinement",
        expand=False
    ))
    
    try:
        # Get current context
        context = context_manager.get_context_dict()
        
        # Check if file exists
        file = Path(file_path)
        if not file.exists() or not file.is_file():
            console.print(f"[bold red]File does not exist: {file_path}[/bold red]")
            return
        
        # Read file content
        with open(file, 'r', encoding='utf-8', errors='replace') as f:
            original_code = f.read()
        
        # Process feedback
        console.print("\n[bold]Processing feedback...[/bold]")
        
        with console.status("[bold green]Generating improvements...[/bold green]"):
            result = asyncio.run(feedback_manager.process_feedback(
                feedback=feedback,
                original_code=original_code,
                file_path=str(file),
                context=context
            ))
        
        # Display diff
        console.print("\n[bold blue]Code changes:[/bold blue]")
        
        syntax = Syntax(
            result["diff"],
            "diff",
            theme="monokai",
            line_numbers=True,
            word_wrap=True
        )
        console.print(syntax)
        
        # Display explanation
        console.print("\n[bold blue]Explanation:[/bold blue]")
        console.print(result["explanation"])
        
        # Apply changes if requested
        if apply:
            console.print("\n[bold]Applying changes...[/bold]")
            
            refinements = {
                "project_dir": str(file.parent),
                "results": [
                    {
                        "file_path": file.name,
                        "has_changes": original_code != result["improved_code"],
                        "diff": result["diff"],
                        "explanation": result["explanation"]
                    }
                ]
            }
            
            with console.status("[bold green]Applying changes...[/bold green]"):
                apply_result = asyncio.run(feedback_manager.apply_refinements(
                    refinements=refinements,
                    backup=backup
                ))
            
            if apply_result["files_changed"] > 0:
                console.print("[green]Changes applied successfully[/green]")
                if backup:
                    backup_file = apply_result["results"][0].get("backup")
                    if backup_file:
                        console.print(f"[blue]Backup created: {backup_file}[/blue]")
            else:
                console.print("[yellow]No changes were applied[/yellow]")
        else:
            console.print("\n[bold yellow]Changes were not applied. Use --apply to apply changes.[/bold yellow]")
    
    except Exception as e:
        logger.exception("Error refining code")
        console.print(f"[bold red]Error refining code:[/bold red] {str(e)}")

@app.command("refine-project")
def refine_project(
    feedback: str = typer.Argument(..., help="Feedback for project improvement"),
    project_dir: str = typer.Option(".", help="Project directory"),
    focus: Optional[List[str]] = typer.Option(None, help="Files to focus on (glob patterns supported)"),
    apply: bool = typer.Option(False, help="Apply the changes"),
    backup: bool = typer.Option(True, help="Create backup before applying changes")
):
    """
    Refine an entire project based on feedback.
    """
    console.print(Panel(
        f"[bold green]Refining project based on feedback:[/bold green]\n{feedback}",
        title="Project Refinement",
        expand=False
    ))
    
    try:
        # Get current context
        context = context_manager.get_context_dict()
        
        # Check if project directory exists
        project_path = Path(project_dir)
        if not project_path.exists() or not project_path.is_dir():
            console.print(f"[bold red]Project directory does not exist: {project_dir}[/bold red]")
            return
        
        # Process feedback
        console.print("\n[bold]Processing feedback...[/bold]")
        
        with console.status("[bold green]Analyzing project and generating improvements...[/bold green]"):
            result = asyncio.run(feedback_manager.refine_project(
                project_dir=project_path,
                feedback=feedback,
                focus_files=focus,
                context=context
            ))
        
        # Display results
        console.print(f"\n[bold blue]Files analyzed: {len(result['results'])}[/bold blue]")
        
        # Create a table to show the changes
        table = Table(title="Refinement Results")
        table.add_column("File", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Changes", style="yellow")
        
        for file_result in result["results"]:
            file_path = file_result["file_path"]
            
            if "error" in file_result:
                status = "[red]Error[/red]"
                changes = file_result["error"]
            elif not file_result.get("has_changes", False):
                status = "[blue]No changes[/blue]"
                changes = "No changes needed"
            else:
                status = "[green]Changes pending[/green]"
                diff_lines = file_result["diff"].splitlines()
                additions = sum(1 for line in diff_lines if line.startswith('+') and not line.startswith('+++'))
                deletions = sum(1 for line in diff_lines if line.startswith('-') and not line.startswith('---'))
                changes = f"+{additions} -{deletions}"
            
            table.add_row(file_path, status, changes)
        
        console.print(table)
        
        # Show details for files with changes
        changed_files = [r for r in result["results"] if r.get("has_changes", False)]
        if changed_files:
            console.print(f"\n[bold blue]Files with changes ({len(changed_files)}):[/bold blue]")
            
            for file_result in changed_files:
                console.print(f"\n[bold cyan]File: {file_result['file_path']}[/bold cyan]")
                
                # Display diff
                syntax = Syntax(
                    file_result["diff"],
                    "diff",
                    theme="monokai",
                    line_numbers=True,
                    word_wrap=True
                )
                console.print(syntax)
                
                # Display explanation
                if "explanation" in file_result:
                    console.print(f"[italic]{file_result['explanation']}[/italic]")
        
        # Apply changes if requested
        if apply:
            console.print("\n[bold]Applying changes...[/bold]")
            
            with console.status("[bold green]Applying changes...[/bold green]"):
                apply_result = asyncio.run(feedback_manager.apply_refinements(
                    refinements=result,
                    backup=backup
                ))
            
            if apply_result["files_changed"] > 0:
                console.print(f"[green]Changes applied to {apply_result['files_changed']} files[/green]")
                if backup:
                    console.print("[blue]Backups created for modified files[/blue]")
            else:
                console.print("[yellow]No changes were applied[/yellow]")
        else:
            console.print("\n[bold yellow]Changes were not applied. Use --apply to apply changes.[/bold yellow]")
    
    except Exception as e:
        logger.exception("Error refining project")
        console.print(f"[bold red]Error refining project:[/bold red] {str(e)}")

@app.command("generate-ci")
def generate_ci(
    platform: str = typer.Argument(..., help="CI platform (github_actions, gitlab_ci, jenkins, travis, circle_ci)"),
    project_dir: str = typer.Option(".", help="Project directory"),
    project_type: Optional[str] = typer.Option(None, help="Project type (python, node, etc.)")
):
    """
    Generate CI/CD configuration for a project.
    """
    console.print(Panel(
        f"[bold green]Generating CI/CD configuration for platform:[/bold green] {platform}",
        title="CI/CD Configuration",
        expand=False
    ))
    
    try:
        # Check if project directory exists
        project_path = Path(project_dir)
        if not project_path.exists() or not project_path.is_dir():
            console.print(f"[bold red]Project directory does not exist: {project_dir}[/bold red]")
            return
        
        # Detect project type if not provided
        if not project_type:
            console.print("\n[bold]Detecting project type...[/bold]")
            
            with console.status("[bold green]Analyzing project...[/bold green]"):
                detection_result = asyncio.run(ci_cd_integration.detect_project_type(project_dir))
                project_type = detection_result.get("project_type")
            
            if project_type:
                console.print(f"[green]Detected project type: {project_type}[/green]")
            else:
                console.print("[red]Could not detect project type[/red]")
                return
        
        # Generate CI configuration
        console.print(f"\n[bold]Generating {platform} configuration...[/bold]")
        
        with console.status(f"[bold green]Generating configuration...[/bold green]"):
            result = asyncio.run(ci_cd_integration.generate_ci_configuration(
                path=project_dir,
                platform=platform,
                project_type=project_type
            ))
        
        if result["success"]:
            console.print(f"[green]Generated {platform} configuration successfully[/green]")
            console.print(f"Configuration file: [bold]{result['config_file']}[/bold]")
        else:
            console.print(f"[red]Failed to generate configuration: {result.get('error', 'Unknown error')}[/red]")
    
    except Exception as e:
        logger.exception("Error generating CI/CD configuration")
        console.print(f"[bold red]Error generating CI/CD configuration:[/bold red] {str(e)}")




@app.command("create-complex-project")
def create_complex_project(
    description: str = typer.Argument(..., help="Description of the project to generate"),
    output_dir: str = typer.Option(".", help="Directory where the project should be generated"),
    project_type: Optional[str] = typer.Option(None, help="Project type (python, node, etc.)"),
    framework: Optional[str] = typer.Option(None, help="Framework to use (django, react, etc.)"),
    detailed_planning: bool = typer.Option(True, help="Use detailed architecture planning"),
    git_init: bool = typer.Option(True, help="Initialize Git repository"),
    install_deps: bool = typer.Option(False, help="Install dependencies"),
    generate_tests: bool = typer.Option(False, help="Generate test files"),
    ci_platform: Optional[str] = typer.Option(None, help="Generate CI configuration (github, gitlab, etc.)"),
    dry_run: bool = typer.Option(False, help="Preview without creating files")
):
    """
    Generate a complex multi-file project with detailed architecture planning.
    """
    console.print(Panel(
        f"[bold green]Generating complex project from description:[/bold green]\n{description}",
        title="Complex Project Generation",
        expand=False
    ))
    
    try:
        # Get current context
        context = context_manager.get_context_dict()
        
        # Generate complex project
        with console.status("[bold green]Generating project plan and architecture...[/bold green]"):
            project_plan = asyncio.run(code_generation_engine.generate_complex_project(
                description=description,
                output_dir=output_dir,
                project_type=project_type,
                framework=framework,
                use_detailed_planning=detailed_planning,
                context=context
            ))
        
        # Display project plan
        console.print("\n[bold blue]Project Plan:[/bold blue]")
        console.print(f"Name: [bold]{project_plan.name}[/bold]")
        console.print(f"Type: [bold]{project_plan.project_type}[/bold]")
        console.print(f"Files: [bold]{len(project_plan.files)}[/bold]")
        
        # Generate architecture visualization if available
        architecture = generation_context_manager.get_global_context("architecture")
        if architecture:
            console.print("\n[bold blue]Architecture Overview:[/bold blue]")
            console.print(f"Structure: [bold]{architecture.get('structure_type', 'layered')}[/bold]")
            console.print(f"Components: [bold]{len(architecture.get('components', []))}[/bold]")
            console.print(f"Layers: [bold]{', '.join(architecture.get('layers', []))}[/bold]")
            
            # Show design patterns
            if architecture.get("patterns"):
                console.print(f"Design Patterns: [bold]{', '.join(architecture.get('patterns', []))}[/bold]")
        
        # Show the list of files grouped by component/directory
        grouped_files = group_files_by_directory(project_plan.files)
        
        for group, files in grouped_files.items():
            table = Table(title=f"Files in {group}")
            table.add_column("Path", style="cyan")
            table.add_column("Purpose", style="green")
            
            for file in files:
                table.add_row(file.path, file.purpose)
            
            console.print(table)
        
        # Interactive refinement phase
        if not dry_run and Confirm.ask("\nWould you like to refine any aspect of the project before creation?"):
            feedback = Prompt.ask("\nPlease describe what you'd like to refine")
            
            with console.status("[bold green]Refining project based on feedback...[/bold green]"):
                refined_project, refinement_results = asyncio.run(interactive_refiner.process_refinement_feedback(
                    feedback=feedback,
                    project=project_plan
                ))
                
                # Update project plan with refinements
                project_plan = refined_project
            
            # Show refinement summary
            summary = asyncio.run(interactive_refiner.summarize_refinements(refinement_results))
            
            console.print(f"\n[green]Refined {summary['files_modified']} files based on feedback[/green]")
            
            if summary["file_summaries"]:
                for file_summary in summary["file_summaries"]:
                    console.print(f"- [cyan]{file_summary['file_path']}[/cyan]: {file_summary['lines_added']} lines added, {file_summary['lines_deleted']} lines removed")
        
        # Create the files if not dry run
        if not dry_run:
            console.print("\n[bold]Creating project files...[/bold]")
            
            with console.status("[bold green]Creating files...[/bold green]"):
                result = asyncio.run(code_generation_engine.create_project_files(project_plan))
            
            console.print(f"[green]Created {result['file_count']} files[/green]")
            
            # Initialize Git repository if requested
            if git_init:
                console.print("\n[bold]Initializing Git repository...[/bold]")
                
                with console.status("[bold green]Initializing Git...[/bold green]"):
                    git_result = asyncio.run(git_integration.init_repository(
                        path=output_dir,
                        initial_branch="main",
                        gitignore_template=project_plan.project_type
                    ))
                
                if git_result["success"]:
                    console.print("[green]Git repository initialized successfully[/green]")
                else:
                    console.print(f"[yellow]Failed to initialize Git repository: {git_result.get('error', 'Unknown error')}[/yellow]")
            
            # Install dependencies if requested
            if install_deps:
                console.print("\n[bold]Installing dependencies...[/bold]")
                
                with console.status("[bold green]Installing dependencies...[/bold green]"):
                    deps_result = asyncio.run(package_manager_integration.install_dependencies(
                        path=output_dir,
                        dependencies=project_plan.dependencies.get("runtime", []),
                        dev_dependencies=project_plan.dependencies.get("development", []),
                        project_type=project_plan.project_type
                    ))
                
                if deps_result["success"]:
                    console.print("[green]Dependencies installed successfully[/green]")
                else:
                    console.print(f"[yellow]Failed to install dependencies: {deps_result.get('error', 'Unknown error')}[/yellow]")
            
            # Generate test files if requested
            if generate_tests:
                console.print("\n[bold]Generating test files...[/bold]")
                
                with console.status("[bold green]Generating tests...[/bold green]"):
                    test_result = asyncio.run(test_framework_integration.generate_test_files(
                        src_files=project_plan.files,
                        project_type=project_plan.project_type,
                        root_dir=output_dir
                    ))
                
                if test_result["success"]:
                    console.print(f"[green]Generated {test_result['file_count']} test files[/green]")
                else:
                    console.print(f"[yellow]Failed to generate test files: {test_result.get('error', 'Unknown error')}[/yellow]")
            
            # Generate CI/CD configuration if requested
            if ci_platform:
                console.print("\n[bold]Generating CI/CD configuration...[/bold]")
                
                with console.status(f"[bold green]Generating {ci_platform} configuration...[/bold green]"):
                    ci_result = asyncio.run(ci_cd_integration.generate_ci_configuration(
                        path=output_dir,
                        platform=ci_platform,
                        project_type=project_plan.project_type
                    ))
                
                if ci_result["success"]:
                    console.print(f"[green]Generated {ci_platform} configuration successfully[/green]")
                else:
                    console.print(f"[yellow]Failed to generate CI/CD configuration: {ci_result.get('error', 'Unknown error')}[/yellow]")
            
            # Create initial commit if Git was initialized
            if git_init:
                console.print("\n[bold]Creating initial commit...[/bold]")
                
                with console.status("[bold green]Creating commit...[/bold green]"):
                    commit_result = asyncio.run(git_integration.commit_changes(
                        path=output_dir,
                        message="Initial project generation",
                        auto_stage=True
                    ))
                
                if commit_result["success"]:
                    console.print("[green]Created initial commit successfully[/green]")
                else:
                    console.print(f"[yellow]Failed to create initial commit: {commit_result.get('error', 'Unknown error')}[/yellow]")
            
            console.print(f"\n[bold green]Project generated successfully in: {output_dir}[/bold green]")
        else:
            console.print("\n[bold yellow]Dry run - no files were created[/bold yellow]")
    
    except Exception as e:
        logger.exception("Error generating complex project")
        console.print(f"[bold red]Error generating complex project:[/bold red] {str(e)}")

@app.command("create-framework-project")
def create_framework_project(
    framework: str = typer.Argument(..., help="Framework to generate (e.g., react, django)"),
    description: str = typer.Argument(..., help="Description of the project to generate"),
    output_dir: str = typer.Option(".", help="Directory where the project should be generated"),
    variant: Optional[str] = typer.Option(None, help="Framework variant (e.g., nextjs for React)"),
    typescript: Optional[bool] = typer.Option(None, help="Use TypeScript (for JS frameworks)"),
    with_auth: Optional[bool] = typer.Option(None, help="Include authentication"),
    enhanced: bool = typer.Option(True, help="Use enhanced project structure"),
    install_deps: bool = typer.Option(False, help="Install dependencies"),
    git_init: bool = typer.Option(True, help="Initialize Git repository"),
    dry_run: bool = typer.Option(False, help="Preview without creating files")
):
    """
    Generate a project for a specific framework with best practices.
    """
    console.print(Panel(
        f"[bold green]Generating {framework} project:[/bold green]\n{description}",
        title="Framework Project Generation",
        expand=False
    ))
    
    try:
        # Get current context
        context = context_manager.get_context_dict()
        
        # Prepare options
        options = {
            "variant": variant,
            "typescript": typescript,
            "authentication": with_auth
        }
        
        # Remove None values
        options = {k: v for k, v in options.items() if v is not None}
        
        # Generate framework project
        from angela.generation.frameworks import framework_generator
        
        with console.status(f"[bold green]Generating {framework} project...[/bold green]"):
            if enhanced:
                result = asyncio.run(framework_generator.generate_standard_project_structure(
                    framework=framework,
                    description=description,
                    output_dir=output_dir,
                    options=options
                ))
            else:
                result = asyncio.run(framework_generator.generate_framework_structure(
                    framework=framework,
                    description=description,
                    output_dir=output_dir,
                    options=options
                ))
        
        if not result["success"]:
            console.print(f"[bold red]Error generating {framework} project:[/bold red] {result.get('error', 'Unknown error')}")
            return
        
        # Display result information
        console.print("\n[bold blue]Framework Project:[/bold blue]")
        console.print(f"Framework: [bold]{result['framework']}[/bold]")
        
        if result.get("variant"):
            console.print(f"Variant: [bold]{result['variant']}[/bold]")
            
        console.print(f"Files: [bold]{len(result['files'])}[/bold]")
        
        # Group files by directory
        grouped_files = {}
        for file in result["files"]:
            directory = Path(file.path).parent.as_posix()
            if directory == ".":
                directory = "Root"
                
            if directory not in grouped_files:
                grouped_files[directory] = []
                
            grouped_files[directory].append(file)
        
        # Display files by directory
        for directory, files in grouped_files.items():
            table = Table(title=f"Files in {directory}")
            table.add_column("Path", style="cyan")
            table.add_column("Purpose", style="green")
            
            for file in files:
                table.add_row(file.path, file.purpose)
            
            console.print(table)
        
        # Create project if not dry run
        if not dry_run:
            # Create CodeProject object
            from angela.generation.engine import CodeProject
            
            project = CodeProject(
                name=f"{framework}_project",
                description=description,
                root_dir=output_dir,
                files=result["files"],
                dependencies={"runtime": [], "development": []},
                project_type=result["project_type"],
                structure_explanation=f"Standard {framework} project structure"
            )
            
            # Create files
            console.print("\n[bold]Creating project files...[/bold]")
            
            with console.status("[bold green]Creating files...[/bold green]"):
                creation_result = asyncio.run(code_generation_engine.create_project_files(project))
            
            console.print(f"[green]Created {creation_result['file_count']} files[/green]")
            
            # Initialize Git repository if requested
            if git_init:
                console.print("\n[bold]Initializing Git repository...[/bold]")
                
                with console.status("[bold green]Initializing Git...[/bold green]"):
                    git_result = asyncio.run(git_integration.init_repository(
                        path=output_dir,
                        initial_branch="main",
                        gitignore_template=result["project_type"]
                    ))
                
                if git_result["success"]:
                    console.print("[green]Git repository initialized successfully[/green]")
                else:
                    console.print(f"[yellow]Failed to initialize Git repository: {git_result.get('error', 'Unknown error')}[/yellow]")
            
            # Install dependencies if requested
            if install_deps:
                console.print("\n[bold]Installing dependencies...[/bold]")
                
                with console.status("[bold green]Installing dependencies...[/bold green]"):
                    # Use package manager based on framework
                    project_type = result["project_type"]
                    
                    deps_result = asyncio.run(package_manager_integration.install_dependencies(
                        path=output_dir,
                        project_type=project_type
                    ))
                
                if deps_result["success"]:
                    console.print("[green]Dependencies installed successfully[/green]")
                else:
                    console.print(f"[yellow]Failed to install dependencies: {deps_result.get('error', 'Unknown error')}[/yellow]")
            
            console.print(f"\n[bold green]Framework project generated successfully in: {output_dir}[/bold green]")
        else:
            console.print("\n[bold yellow]Dry run - no files were created[/bold yellow]")
    
    except Exception as e:
        logger.exception(f"Error generating {framework} project")
        console.print(f"[bold red]Error generating {framework} project:[/bold red] {str(e)}")

@app.command("refine-generated-project")
def refine_generated_project(
    project_dir: str = typer.Argument(..., help="Directory of the generated project"),
    feedback: str = typer.Argument(..., help="Feedback for project improvement"),
    focus: Optional[List[str]] = typer.Option(None, help="Files to focus on (glob patterns supported)"),
    apply: bool = typer.Option(True, help="Apply the changes"),
    backup: bool = typer.Option(True, help="Create backup before applying changes")
):
    """
    Refine a generated project based on natural language feedback.
    """
    console.print(Panel(
        f"[bold green]Refining project based on feedback:[/bold green]\n{feedback}",
        title="Project Refinement",
        expand=False
    ))
    
    try:
        # Get current context
        context = context_manager.get_context_dict()
        
        # Check if project directory exists
        project_path = Path(project_dir)
        if not project_path.exists() or not project_path.is_dir():
            console.print(f"[bold red]Project directory does not exist: {project_dir}[/bold red]")
            return
        
        # Load project files
        with console.status("[bold green]Loading project files...[/bold green]"):
            project_files = []
            
            for root, _, files in os.walk(project_path):
                for file in files:
                    # Skip common non-source directories
                    if any(excluded in root for excluded in ['.git', 'node_modules', '__pycache__', '.venv']):
                        continue
                    
                    file_path = Path(root) / file
                    rel_path = file_path.relative_to(project_path)
                    
                    # Skip binary files
                    if any(file.endswith(ext) for ext in ['.jpg', '.png', '.gif', '.pdf', '.zip', '.pyc']):
                        continue
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                            content = f.read()
                        
                        # Get file info
                        file_type = detect_file_type(file_path)
                        
                        project_files.append(CodeFile(
                            path=str(rel_path),
                            content=content,
                            purpose="",  # We don't know the purpose
                            dependencies=[],
                            language=file_type.get("language")
                        ))
                    except Exception as e:
                        console.print(f"[yellow]Error reading file {file_path}: {str(e)}[/yellow]")
        
        console.print(f"[green]Loaded {len(project_files)} project files[/green]")
        
        # Create a project object
        from angela.generation.engine import CodeProject
        
        project = CodeProject(
            name=project_path.name,
            description="",  # We don't know the description
            root_dir=str(project_path),
            files=project_files,
            dependencies={"runtime": [], "development": []},
            project_type="unknown",  # We'll try to infer this
            structure_explanation=""
        )
        
        # Try to infer project type
        with console.status("[bold green]Analyzing project...[/bold green]"):
            # Try to detect project type
            from angela.toolchain.ci_cd import ci_cd_integration
            detection_result = asyncio.run(ci_cd_integration.detect_project_type(project_dir))
            
            if detection_result["project_type"]:
                project.project_type = detection_result["project_type"]
                console.print(f"[green]Detected project type: {project.project_type}[/green]")
            
            # Analyze code relationships
            analysis_result = await generation_context_manager.analyze_code_relationships(project.files)
            
            console.print(f"[green]Analyzed {analysis_result.get('entity_count', 0)} entities and {analysis_result.get('dependency_count', 0)} dependencies[/green]")
            
            # Detect architecture patterns
            if analysis_result.get("architecture_patterns"):
                console.print(f"[green]Detected architecture patterns: {', '.join(analysis_result.get('architecture_patterns', []))}[/green]")
        
        # Process feedback
        console.print("\n[bold]Processing feedback...[/bold]")
        
        with console.status("[bold green]Generating improvements based on feedback...[/bold green]"):
            refined_project, refinement_results = asyncio.run(interactive_refiner.process_refinement_feedback(
                feedback=feedback,
                project=project,
                focus_files=focus
            ))
        
        # Display results
        console.print(f"\n[bold blue]Files analyzed: {len(refinement_results['results'])}[/bold blue]")
        
        # Create a table to show the changes
        table = Table(title="Refinement Results")
        table.add_column("File", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Changes", style="yellow")
        
        for file_result in refinement_results["results"]:
            file_path = file_result["file_path"]
            
            if "error" in file_result:
                status = "[red]Error[/red]"
                changes = file_result["error"]
            elif not file_result.get("has_changes", False):
                status = "[blue]No changes[/blue]"
                changes = "No changes needed"
            else:
                status = "[green]Changes pending[/green]"
                diff_lines = file_result["diff"].splitlines()
                additions = sum(1 for line in diff_lines if line.startswith('+') and not line.startswith('+++'))
                deletions = sum(1 for line in diff_lines if line.startswith('-') and not line.startswith('---'))
                changes = f"+{additions} -{deletions}"
            
            table.add_row(file_path, status, changes)
        
        console.print(table)
        
        # Show details for files with changes
        changed_files = [r for r in refinement_results["results"] if r.get("has_changes", False)]
        if changed_files:
            console.print(f"\n[bold blue]Files with changes ({len(changed_files)}):[/bold blue]")
            
            for file_result in changed_files:
                console.print(f"\n[bold cyan]File: {file_result['file_path']}[/bold cyan]")
                
                # Display diff
                syntax = Syntax(
                    file_result["diff"],
                    "diff",
                    theme="monokai",
                    line_numbers=True,
                    word_wrap=True
                )
                console.print(syntax)
                
                # Display explanation
                if "explanation" in file_result:
                    explanation_md = Markdown(file_result["explanation"])
                    console.print(explanation_md)
        
        # Apply changes if requested
        if apply:
            console.print("\n[bold]Applying changes...[/bold]")
            
            with console.status("[bold green]Applying changes...[/bold green]"):
                apply_result = asyncio.run(feedback_manager.apply_refinements(
                    refinements=refinement_results,
                    backup=backup
                ))
            
            if apply_result["files_changed"] > 0:
                console.print(f"[green]Changes applied to {apply_result['files_changed']} files[/green]")
                if backup:
                    console.print("[blue]Backups created for modified files[/blue]")
            else:
                console.print("[yellow]No changes were applied[/yellow]")
        else:
            console.print("\n[bold yellow]Changes were not applied. Use --apply to apply changes.[/bold yellow]")
    
    except Exception as e:
        logger.exception("Error refining project")
        console.print(f"[bold red]Error refining project:[/bold red] {str(e)}")

def group_files_by_directory(files: List[CodeFile]) -> Dict[str, List[CodeFile]]:
    """
    Group files by their directory.
    
    Args:
        files: List of CodeFile objects
        
    Returns:
        Dictionary mapping directory names to lists of files
    """
    grouped = {}
    
    for file in files:
        directory = Path(file.path).parent.as_posix()
        if directory == ".":
            directory = "Root"
            
        if directory not in grouped:
            grouped[directory] = []
            
        grouped[directory].append(file)
    
    return grouped






@app.command("generate-tests")
def generate_tests(
    project_dir: str = typer.Option(".", help="Project directory"),
    test_framework: Optional[str] = typer.Option(None, help="Test framework to use"),
    focus: Optional[List[str]] = typer.Option(None, help="Files to focus on (glob patterns supported)")
):
    """
    Generate test files for a project.
    """
    console.print(Panel(
        "[bold green]Generating test files for project[/bold green]",
        title="Test Generation",
        expand=False
    ))
    
    try:
        # Check if project directory exists
        project_path = Path(project_dir)
        if not project_path.exists() or not project_path.is_dir():
            console.print(f"[bold red]Project directory does not exist: {project_dir}[/bold red]")
            return
        
        # Detect test framework if not provided
        if not test_framework:
            console.print("\n[bold]Detecting test framework...[/bold]")
            
            with console.status("[bold green]Analyzing project...[/bold green]"):
                detection_result = asyncio.run(test_framework_integration.detect_test_framework(project_dir))
                test_framework = detection_result.get("test_framework")
            
            if test_framework:
                console.print(f"[green]Detected test framework: {test_framework}[/green]")
            else:
                console.print("[yellow]Could not detect test framework. Using default for project type...[/yellow]")
        
        # Find source files
        console.print("\n[bold]Finding source files...[/bold]")
        
        src_files = []
        with console.status("[bold green]Scanning project...[/bold green]"):
            # Get project type
            project_type_result = asyncio.run(ci_cd_integration.detect_project_type(project_dir))
            project_type = project_type_result.get("project_type")
            
            # Map of project types to file extensions
            extensions = {
                "python": [".py"],
                "node": [".js", ".jsx", ".ts", ".tsx"],
                "java": [".java"],
                "go": [".go"],
                "rust": [".rs"],
                "ruby": [".rb"]
            }
            
            # Get relevant file extensions
            file_exts = extensions.get(project_type, [".py", ".js", ".java", ".go", ".rs", ".rb"])
            
            # Find all source files
            for root, _, files in os.walk(project_path):
                # Skip common test directories and non-source directories
                if any(excluded in root for excluded in ["test", "tests", "__pycache__", "node_modules", ".git"]):
                    continue
                
                for file in files:
                    _, ext = os.path.splitext(file)
                    if ext in file_exts:
                        # If focus is specified, check if file matches any pattern
                        if focus:
                            file_path = Path(root) / file
                            rel_path = file_path.relative_to(project_path)
                            
                            matched = False
                            for pattern in focus:
                                if Path(pattern).name == file or rel_path.match(pattern):
                                    matched = True
                                    break
                            
                            if not matched:
                                continue
                        
                        # Read file content
                        try:
                            with open(Path(root) / file, 'r', encoding='utf-8', errors='replace') as f:
                                content = f.read()
                            
                            # Create CodeFile object
                            from angela.generation.engine import CodeFile
                            file_path = Path(root) / file
                            rel_path = file_path.relative_to(project_path)
                            
                            src_files.append(CodeFile(
                                path=str(rel_path),
                                content=content,
                                purpose=f"Source file: {file}",
                                dependencies=[],
                                language=project_type
                            ))
                        except Exception as e:
                            console.print(f"[yellow]Error reading file {file}: {str(e)}[/yellow]")
        
        console.print(f"[green]Found {len(src_files)} source files[/green]")
        
        # Generate test files
        console.print("\n[bold]Generating test files...[/bold]")
        
        with console.status("[bold green]Generating tests...[/bold green]"):
            result = asyncio.run(test_framework_integration.generate_test_files(
                src_files=src_files,
                test_framework=test_framework,
                project_type=project_type,
                root_dir=project_dir
            ))
        
        if result["success"]:
            console.print(f"[green]Generated {result['file_count']} test files[/green]")
            
            # Show generated files
            if result["generated_files"]:
                console.print("\n[bold blue]Generated test files:[/bold blue]")
                for file in result["generated_files"]:
                    console.print(f"- {file}")
        else:
            console.print(f"[red]Failed to generate test files: {result.get('error', 'Unknown error')}[/red]")
    
    except Exception as e:
        logger.exception("Error generating test files")
        console.print(f"[bold red]Error generating test files:[/bold red] {str(e)}")

if __name__ == "__main__":
    app()
