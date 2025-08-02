# Custom Instructions for Claude

## On Startup (Beginning of Each Session)
- **ALWAYS** review the project structure and understand what it does fully
- Read the PROJECT_CONTEXT.md file if it exists to understand:
  - Project purpose and main features
  - Current state of implementation
  - Key technologies and frameworks used
  - Important files and their purposes
  - Recent changes and work in progress
- If PROJECT_CONTEXT.md doesn't exist, perform a thorough review:
  - Examine README.md and other documentation
  - Review package.json/requirements.txt for dependencies
  - Understand the project architecture
  - Identify main entry points and key components

## Before Exiting (End of Each Session)
- **ALWAYS** update or create PROJECT_CONTEXT.md with:
  - Summary of work completed in this session
  - Current state of the project
  - Any pending tasks or issues
  - Important context for the next session
  - Key files modified and their current state
- Format the context file clearly for easy understanding in future sessions

## Always Do These Actions

### Before Making Changes
- Always create a descriptive commit message
- Run linting and type checking after code changes
- Test the changes locally before committing

### Code Style
- Use consistent naming conventions (camelCase for variables, PascalCase for components)
- Add TypeScript types where applicable
- Follow existing code patterns in the project

### Git Workflow
- Create feature branches for new work
- Write detailed commit messages with:
  - High-level explanation of changes made
  - Summary of overall functionality at this commit SHA
  - Format: 
    ```
    feat/fix/chore: Brief description
    
    Changes:
    - Detailed change 1
    - Detailed change 2
    
    Current State:
    This commit implements [describe what the app can do at this point]
    ```
- Always push changes to remote after committing

### Testing
- Run `npm test` after making changes
- Ensure all tests pass before marking task complete
- Add tests for new functionality

### Project-Specific
- When working on AI features, always test with sample PDFs
- Verify Firebase configuration is working
- Check both web and mobile app if changes affect shared code

## Midterm Specific Instructions
[Add your midterm-specific requirements here]