import re
from pathlib import Path
from crewai import Crew, Process, Task

# Import agents
from agents.manager import create_manager_agent
from agents.developer import create_developer_agent
from agents.tester import create_tester_agent
from agents.github import create_github_agent

# Import tasks
from tasks.manager_tasks import create_planning_task
from tasks.manager_tasks import create_improvement_planning_task_inline
from tasks.developer_tasks import create_development_task
from tasks.tester_tasks import create_testing_task
from tasks.github_tasks import create_github_deployment_task, create_github_repository_task

# Import config
from backend.config import OUTPUT_DIR, GITHUB_USERNAME


def sanitize_repo_name(name: str) -> str:
    """Convert project name to valid GitHub repository name"""
    name = re.sub(r'[^a-zA-Z0-9\s-]', '', name)
    name = name.lower().strip().replace(' ', '-')
    name = re.sub(r'-+', '-', name)
    return name


def create_project_directory(project_name: str) -> Path:
    """Create and return project directory path"""
    safe_name = sanitize_repo_name(project_name)
    project_dir = OUTPUT_DIR / f"{safe_name}"
    project_dir.mkdir(parents=True, exist_ok=True)
    return project_dir


def display_plan(plan: str, title: str = "TECHNICAL PLAN") -> None:
    """Display the technical plan in a formatted way"""
    print("\n" + "=" * 80)
    print(f"📋 {title}")
    print("=" * 80)
    print(plan)
    print("=" * 80)


def display_project_summary(project_dir: Path) -> None:
    """Display summary of generated project"""
    print("\n" + "=" * 80)
    print("📦 PROJECT SUMMARY")
    print("=" * 80)
    
    print(f"\n📁 Project Location: {project_dir}")
    
    # List key files
    print("\n📄 Key Files Generated:")
    key_patterns = ['README.md', 'requirements.txt', 'package.json', '*.py', '*.js', '*.ts', 'TEST_REPORT.md']
    key_files = []
    
    for pattern in key_patterns:
        key_files.extend(project_dir.glob(pattern))
    
    # Also get files from src/
    if (project_dir / 'src').exists():
        key_files.extend((project_dir / 'src').rglob('*'))
    
    file_count = 0
    displayed_files = set()
    for file in sorted(key_files):
        if file.is_file() and str(file) not in displayed_files:
            file_count += 1
            displayed_files.add(str(file))
            print(f"  {file_count}. {file.relative_to(project_dir)}")
            
            # Show first few lines of important files
            if file.name in ['README.md', 'TEST_REPORT.md']:
                try:
                    with open(file, 'r', encoding='utf-8') as f:
                        lines = f.readlines()[:3]
                        if lines:
                            print(f"     Preview: {lines[0].strip()[:60]}...")
                except:
                    pass
    
    print(f"\n📊 Total Files: {len(list(project_dir.rglob('*')))} files")
    print("=" * 80)


def get_user_approval(phase: str = "plan") -> tuple[bool, str]:
    """
    Get user approval for the plan or final product.
    
    Args:
        phase: 'plan', 'improvement_plan', or 'final' to customize messaging
    
    Returns:
        tuple: (approved: bool, feedback: str)
    """
    print("\n" + "=" * 80)
    print("👤 HUMAN REVIEW REQUIRED")
    print("=" * 80)
    
    if phase == "plan":
        print("\nPlease review the technical plan above.")
    elif phase == "improvement_plan":
        print("\nPlease review the improvement plan above.")
        print("This plan will guide how changes are implemented.")
    else:
        print("\nPlease review the generated project.")
        print("Check the files, run the code, and test the functionality.")
    
    print("\nOptions:")
    if phase in ["plan", "improvement_plan"]:
        print("  1. Approve - Proceed with implementation")
        print("  2. Request Changes - Provide additional requirements")
    else:
        print("  1. Approve - Complete the project")
        print("  2. Request Changes - Provide feedback for improvements")
    print("  3. Cancel - Exit the system")
    
    while True:
        choice = input("\nYour choice (1/2/3): ").strip()
        
        if choice == "1":
            if phase in ["plan", "improvement_plan"]:
                print("\n✓ Plan approved! Proceeding with implementation...")
            else:
                print("\n✓ Project approved! Generation complete!")
            return True, ""
        
        elif choice == "2":
            if phase == "final":
                print("\n📝 What would you like to change or improve?")
                print("Be specific about features, bugs, or improvements needed.")
            elif phase == "improvement_plan":
                print("\n📝 What changes to the improvement plan?")
            else:
                print("\n📝 Please provide your additional requirements or changes:")
            
            print("(You can provide multiple lines. Press Enter twice to finish)\n")
            
            feedback_lines = []
            empty_count = 0
            
            while empty_count < 2:
                line = input()
                if line.strip():
                    feedback_lines.append(line)
                    empty_count = 0
                else:
                    empty_count += 1
            
            feedback = "\n".join(feedback_lines).strip()
            
            if feedback:
                print(f"\n✓ Feedback received ({len(feedback)} characters)")
                return False, feedback
            else:
                print("\n⚠ No feedback provided. Please try again.")
                continue
        
        elif choice == "3":
            print("\n❌ " + ("Project generation cancelled by user." if phase in ["plan", "improvement_plan"] else "Exiting system."))
            return False, "CANCELLED"
        
        else:
            print("\n⚠ Invalid choice. Please enter 1, 2, or 3.")




def main():
    print("=" * 80)
    print("🤖 DEVELOPER AI AGENT SYSTEM")
    print("=" * 80)
    print("\nThis system will:")
    print("1. 📋 Manager creates technical plan")
    print("2. 👤 Get your approval (you can request changes)")
    print("3. 💻 Developer writes code")
    print("4. 🧪 Tester validates code")
    print("5. 🚀 GitHub Manager deploys to repository")
    print("6. 🔄 FEEDBACK LOOP: Manager → Developer → Tester → GitHub")
    print("   (Iterates until you're satisfied!)")
    print("\n" + "=" * 80)
    
    # Get user input
    print("\n📝 PROJECT DETAILS")
    print("-" * 80)
    project_description = input("\nDescribe your project (be detailed): ").strip()
    
    if not project_description:
        print("❌ Project description cannot be empty!")
        return
    
    project_type = input("\nProject type (python/web/ml/javascript) [python]: ").strip() or "python"
    project_name = input("\nProject name (for GitHub repo): ").strip()
    
    if not project_name:
        project_name = "ai-generated-project"

    github_username = GITHUB_USERNAME
    
    # Sanitize repository name
    repo_name = sanitize_repo_name(project_name)
    print(f"\n✓ Repository name will be: {repo_name}")
    
    # Create project directory
    project_dir = OUTPUT_DIR / f"{repo_name}"
    print(f"✓ Project will be created at: {project_dir}")
    
    print("\n" + "=" * 80)
    print("🚀 STARTING PROJECT GENERATION")
    print("=" * 80)
    
    # Create agents (only once)
    print("\n👥 Initializing AI agents...")
    manager = create_manager_agent()
    developer = create_developer_agent()
    tester = create_tester_agent()
    github_manager = create_github_agent()
    print("✓ Agents ready!")

    # =========================================================================
    # PHASE 0: GITHUB REPOSITORY CREATION
    # =========================================================================
    print("\n" + "=" * 80)
    print("🔧 PHASE 0: GITHUB REPOSITORY CREATION")
    print("=" * 80)
    
    try:
        print("\n📦 Creating GitHub repository...")
        
        repo_creation_task = create_github_repository_task(
            github_manager,
            repo_name,
            project_description,
            github_username,
            str(project_dir),
            visibility="public",
            license_type="MIT"
        )
        
        repo_creation_crew = Crew(
            agents=[github_manager],
            tasks=[repo_creation_task],
            process=Process.sequential,
            verbose=True
        )
        
        repo_result = repo_creation_crew.kickoff()
        print("\n✅ GitHub repository created and cloned!")
        print(f"📍 Repository: https://github.com/{github_username}/{repo_name}")
        
    except Exception as e:
        print(f"\n❌ Error creating repository: {str(e)}")
        print("Project generation cannot continue without repository.")
        return
    
    # =========================================================================
    # PHASE 1: PLANNING WITH APPROVAL LOOP
    # =========================================================================
    print("\n" + "=" * 80)
    print("📋 PHASE 1: TECHNICAL PLANNING")
    print("=" * 80)
    
    plan_approved = False
    planning_iteration = 0
    max_planning_iterations = 5
    current_description = project_description
    planning_task = None
    
    while not plan_approved and planning_iteration < max_planning_iterations:
        planning_iteration += 1
        print(f"\n🔄 Planning iteration {planning_iteration}/{max_planning_iterations}...")
        
        planning_task = create_planning_task(
            manager, 
            str(project_dir),
            current_description, 
            project_type
        )
        
        planning_crew = Crew(
            agents=[manager],
            tasks=[planning_task],
            process=Process.sequential,
            verbose=True
        )
        
        try:
            plan_result = planning_crew.kickoff()
            display_plan(str(plan_result))
            
            # Save plan
            plan_file = project_dir / "TECHNICAL_PLAN.md"
            plan_file.write_text(str(plan_result), encoding='utf-8')
            print(f"\n💾 Plan saved to: {plan_file}")
            
            # Get approval
            approved, feedback = get_user_approval(phase="plan")
            
            if feedback == "CANCELLED":
                print("\n👋 Goodbye!")
                return
            
            if approved:
                plan_approved = True
                break
            else:
                current_description = f"""{current_description}

ADDITIONAL REQUIREMENTS (Iteration {planning_iteration}):
{feedback}

Update the technical plan to incorporate these requirements."""
                print("\n🔄 Regenerating plan with your feedback...")
        
        except Exception as e:
            print(f"\n❌ Error during planning: {str(e)}")
            retry = input("\nRetry? (y/n): ").strip().lower()
            if retry != 'y':
                return
    
    if not plan_approved:
        print(f"\n⚠ Max planning iterations ({max_planning_iterations}) reached.")
        return
    
    # =========================================================================
    # PHASE 2: INITIAL IMPLEMENTATION
    # =========================================================================
    print("\n" + "=" * 80)
    print("💻 PHASE 2: CODE IMPLEMENTATION")
    print("=" * 80)
    
    try:
        development_task = create_development_task(
            developer, 
            str(project_dir),
            str(project_type),
            context_tasks=[planning_task]
        )
        
        development_crew = Crew(
            agents=[developer],
            tasks=[development_task],
            process=Process.sequential,
            verbose=True
        )
        
        print("\n🔨 Writing code... This may take several minutes...")
        dev_result = development_crew.kickoff()
        print("\n✅ Code implementation complete!")
        
    except Exception as e:
        print(f"\n❌ Error during development: {str(e)}")
        import traceback
        traceback.print_exc()
        return
    
    # =========================================================================
    # PHASE 3: INITIAL TESTING
    # =========================================================================
    print("\n" + "=" * 80)
    print("🧪 PHASE 3: TESTING & QUALITY ASSURANCE")
    print("=" * 80)
    
    try:
        testing_task = create_testing_task(
            tester,
            str(project_dir),
            str(project_type),
            context_tasks=[planning_task, development_task]
        )
        
        testing_crew = Crew(
            agents=[tester],
            tasks=[testing_task],
            process=Process.sequential,
            verbose=True
        )
        
        print("\n🔍 Running tests and quality checks...")
        test_result = testing_crew.kickoff()
        print("\n✅ Testing complete!")
        
        test_report = project_dir / "TEST_REPORT.md"
        if test_report.exists():
            print(f"\n📊 Test report: {test_report}")
        
    except Exception as e:
        print(f"\n❌ Error during testing: {str(e)}")
        print("⚠ Continuing to deployment...")
        import traceback
        traceback.print_exc()
    
    # =========================================================================
    # PHASE 4: INITIAL GITHUB DEPLOYMENT
    # =========================================================================
    print("\n" + "=" * 80)
    print("🚀 PHASE 4: GITHUB DEPLOYMENT")
    print("=" * 80)
    
    try:
        github_task = create_github_deployment_task(
            agent=github_manager,
            project_dir=str(project_dir),
            repo_name=repo_name,
            github_username=github_username,
            context_tasks=[planning_task, development_task, testing_task]
        )
        
        github_crew = Crew(
            agents=[github_manager],
            tasks=[github_task],
            process=Process.sequential,
            verbose=True
        )
        
        print("\n📤 Deploying to GitHub...")
        github_result = github_crew.kickoff()
        print("\n✅ GitHub deployment complete!")
        print(f"🔗 View at: https://github.com/{github_username}/{repo_name}")
        
    except Exception as e:
        print(f"\n❌ Error during deployment: {str(e)}")
        print("Continuing with feedback loop...")
        import traceback
        traceback.print_exc()
    
    # =========================================================================
    # PHASE 5: POST-DEPLOYMENT FEEDBACK LOOP (WITH MANAGER)
    # =========================================================================
    print("\n" + "=" * 80)
    print("🎯 PHASE 5: FEEDBACK LOOP - ITERATIVE IMPROVEMENTS")
    print("=" * 80)
    
    print("\n📦 Initial project generated and deployed!")
    print(f"\n🔗 GitHub: https://github.com/{github_username}/{repo_name}")
    print(f"📁 Local: {project_dir}")
    
    # Display project summary
    display_project_summary(project_dir)
    
    print("\n" + "=" * 80)
    print("⏸️  PAUSE FOR REVIEW")
    print("=" * 80)
    print("\nPlease take time to:")
    print("  1. 📂 Browse the generated files locally")
    print("  2. 📖 Read the README.md and documentation")
    print("  3. 🧪 Check the TEST_REPORT.md")
    print("  4. 🚀 Run and test the project")
    print("  5. 🔗 Review the GitHub repository")
    
    input("\n⏸️  Press Enter when ready to provide feedback...\n")
    
    # Feedback iteration loop
    feedback_iteration = 0
    max_feedback_iterations = 10  # Continue until user is satisfied
    project_approved = False
    
    while not project_approved:
        feedback_iteration += 1
        print(f"\n" + "=" * 80)
        print(f"🔄 FEEDBACK ITERATION {feedback_iteration}")
        print("=" * 80)
        
        # Get user feedback
        approved, user_feedback = get_user_approval(phase="final")
        
        if user_feedback == "CANCELLED":
            print("\n✓ Project saved locally and on GitHub")
            break
        
        if approved:
            project_approved = True
            print("\n🎉 Project approved! You're satisfied with the result!")
            break
        
        # User wants changes - Process through Manager → Developer → Tester → GitHub
        print("\n" + "=" * 80)
        print(f"📝 PROCESSING FEEDBACK (Iteration {feedback_iteration})")
        print("=" * 80)
        print("\nYour Feedback:")
        print("-" * 80)
        print(user_feedback)
        print("-" * 80)
        
        # Save user feedback
        feedback_file = project_dir / f"USER_FEEDBACK_{feedback_iteration}.md"
        feedback_file.write_text(f"""# User Feedback - Iteration {feedback_iteration}

## Requested Changes:
{user_feedback}

## Status: Processing...
""", encoding='utf-8')
        
        # =====================================================================
        # STEP 1: MANAGER CREATES IMPROVEMENT PLAN
        # =====================================================================
        print("\n" + "=" * 80)
        print("🧠 STEP 1: MANAGER ANALYZING FEEDBACK")
        print("=" * 80)
        
        improvement_plan_approved = False
        improvement_plan_iteration = 0
        max_improvement_plan_iterations = 2
        current_feedback = user_feedback
        improvement_plan_task = None
        
        while not improvement_plan_approved and improvement_plan_iteration < max_improvement_plan_iterations:
            improvement_plan_iteration += 1
            
            if improvement_plan_iteration > 1:
                print(f"\n🔄 Refining improvement plan (attempt {improvement_plan_iteration})...")
            else:
                print("\n🤔 Manager analyzing feedback and creating improvement plan...")
            
            try:
                # Create improvement plan using inline task
                improvement_plan_task = create_improvement_planning_task_inline(
                    manager,
                    str(project_dir),
                    project_type,
                    current_feedback,
                    feedback_iteration,
                    context_tasks=[planning_task, development_task, testing_task]
                )
                
                improvement_crew = Crew(
                    agents=[manager],
                    tasks=[improvement_plan_task],
                    process=Process.sequential,
                    verbose=True
                )
                
                improvement_result = improvement_crew.kickoff()
                
                # Display improvement plan
                display_plan(str(improvement_result), 
                           title=f"IMPROVEMENT PLAN (Iteration {feedback_iteration})")
                
                # Save improvement plan
                plan_file = project_dir / f"IMPROVEMENT_PLAN_{feedback_iteration}.md"
                plan_file.write_text(str(improvement_result), encoding='utf-8')
                print(f"\n💾 Improvement plan saved to: {plan_file}")
                
                # Get approval for improvement plan
                plan_approved, plan_feedback = get_user_approval(phase="improvement_plan")
                
                if plan_feedback == "CANCELLED":
                    print("\n✓ Project saved. You can continue manually.")
                    return
                
                if plan_approved:
                    improvement_plan_approved = True
                    break
                else:
                    current_feedback = f"""{user_feedback}

ADDITIONAL FEEDBACK ON IMPROVEMENT PLAN:
{plan_feedback}

Please update the improvement plan based on this additional feedback."""
                    print("\n🔄 Manager will refine the improvement plan...")
            
            except Exception as e:
                print(f"\n❌ Error creating improvement plan: {str(e)}")
                import traceback
                traceback.print_exc()
                retry = input("\nRetry improvement planning? (y/n): ").strip().lower()
                if retry != 'y':
                    break
        
        if not improvement_plan_approved:
            print("\n⚠ Could not finalize improvement plan.")
            continue_anyway = input("\nSkip this iteration? (y/n): ").strip().lower()
            if continue_anyway != 'y':
                break
            continue
        
        # Update feedback file
        feedback_file.write_text(f"""# User Feedback - Iteration {feedback_iteration}

## Requested Changes:
{user_feedback}

## Status: ✅ Improvement plan created

See IMPROVEMENT_PLAN_{feedback_iteration}.md for details.
""", encoding='utf-8')
        
        # =====================================================================
        # STEP 2: DEVELOPER IMPLEMENTS CHANGES
        # =====================================================================
        print("\n" + "=" * 80)
        print("💻 STEP 2: DEVELOPER IMPLEMENTING CHANGES")
        print("=" * 80)
        
        try:
            print("\n🔨 Implementing improvements based on Manager's plan...")
            
            # Developer implements with improvement plan context
            development_task = create_development_task(
                developer,
                str(project_dir),
                str(project_type),
                context_tasks=[planning_task, improvement_plan_task]
            )
            
            development_crew = Crew(
                agents=[developer],
                tasks=[development_task],
                process=Process.sequential,
                verbose=True
            )
            
            dev_result = development_crew.kickoff()
            print("\n✅ Code changes implemented!")
            
        except Exception as e:
            print(f"\n❌ Error during development: {str(e)}")
            import traceback
            traceback.print_exc()
            retry = input("\nRetry this iteration? (y/n): ").strip().lower()
            if retry != 'y':
                continue
        
        # =====================================================================
        # STEP 3: TESTER VALIDATES CHANGES
        # =====================================================================
        print("\n" + "=" * 80)
        print("🧪 STEP 3: TESTER VALIDATING CHANGES")
        print("=" * 80)
        
        try:
            print("\n🔍 Testing improvements based on Manager's requirements...")
            
            testing_task = create_testing_task(
                tester,
                str(project_dir),
                str(project_type),
                context_tasks=[planning_task, improvement_plan_task, development_task]
            )
            
            testing_crew = Crew(
                agents=[tester],
                tasks=[testing_task],
                process=Process.sequential,
                verbose=True
            )
            
            test_result = testing_crew.kickoff()
            print("\n✅ Testing complete!")
            
        except Exception as e:
            print(f"\n❌ Error during testing: {str(e)}")
            print("⚠ Continuing to deployment...")
            import traceback
            traceback.print_exc()
        
        # =====================================================================
        # STEP 4: GITHUB MANAGER DEPLOYS UPDATES
        # =====================================================================
        print("\n" + "=" * 80)
        print("🚀 STEP 4: DEPLOYING UPDATES TO GITHUB")
        print("=" * 80)
        
        try:
            github_task = create_github_deployment_task(
                agent=github_manager,
                project_dir=str(project_dir),
                repo_name=repo_name,
                github_username=github_username,
                context_tasks=[planning_task, improvement_plan_task, development_task, testing_task]
            )
            
            github_crew = Crew(
                agents=[github_manager],
                tasks=[github_task],
                process=Process.sequential,
                verbose=True
            )
            
            print("\n📤 Deploying improvements to GitHub...")
            github_result = github_crew.kickoff()
            print("\n✅ Deployment complete!")
            print(f"🔗 View updates: https://github.com/{github_username}/{repo_name}")
            
        except Exception as e:
            print(f"\n❌ Error during deployment: {str(e)}")
            print(f"📁 Changes available locally at: {project_dir}")
            import traceback
            traceback.print_exc()
        
        # Update feedback file with completion status
        feedback_file.write_text(f"""# User Feedback - Iteration {feedback_iteration}

## Requested Changes:
{user_feedback}

## Manager's Improvement Plan:
See IMPROVEMENT_PLAN_{feedback_iteration}.md

## Status: ✅ Implemented and Deployed

Changes have been:
1. ✅ Analyzed by Manager Agent
2. ✅ Implemented by Developer Agent
3. ✅ Tested by Tester Agent
4. ✅ Deployed to GitHub

View at: https://github.com/{github_username}/{repo_name}
""", encoding='utf-8')
        
        print("\n✅ Iteration {feedback_iteration} complete!".format(feedback_iteration=feedback_iteration))
        print(f"🔗 Updated project: https://github.com/{github_username}/{repo_name}")
        
        # Display updated summary
        display_project_summary(project_dir)
        
        print("\n⏸️  Please review the updated project...")
        print("     Test the changes and see if they meet your expectations.")
        input("\nPress Enter when ready to continue...\n")
    
    # =========================================================================
    # FINAL SUMMARY
    # =========================================================================
    print("\n" + "=" * 80)
    print("✅ PROJECT GENERATION COMPLETE!")
    print("=" * 80)
    
    print(f"\n📊 Final Statistics:")
    print(f"  - Planning Iterations: {planning_iteration}")
    print(f"  - Feedback Iterations: {feedback_iteration}")
    print(f"  - Project Type: {project_type}")
    print(f"  - Repository: {repo_name}")
    
    total_files = len(list(project_dir.rglob("*")))
    print(f"  - Total Files: {total_files}")
    
    print(f"\n📍 Project Locations:")
    print(f"  🔗 GitHub: https://github.com/{github_username}/{repo_name}")
    print(f"  📁 Local: {project_dir}")
    
    print("\n📚 Documentation Generated:")
    key_files = ['README.md', 'TEST_REPORT.md', 'TECHNICAL_PLAN.md']
    for i in range(1, feedback_iteration + 1):
        key_files.append(f'IMPROVEMENT_PLAN_{i}.md')
        key_files.append(f'USER_FEEDBACK_{i}.md')
    
    for filename in key_files:
        file_path = project_dir / filename
        if file_path.exists():
            print(f"  ✓ {filename}")
    
    print("\n🚀 Next Steps:")
    print(f"  1. Clone: git clone https://github.com/{github_username}/{repo_name}.git")
    print("  2. Follow the README.md for setup")
    print("  3. Run tests to verify everything works")
    print("  4. Start using your project!")
    
    print("\n" + "=" * 80)
    print("🎉 Thank you for using Developer AI Agent System!")
    print("=" * 80)


if __name__ == "__main__":
    main()