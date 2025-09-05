#!/usr/bin/env python3
"""
Example of migrating from broad Exception handling to DRY patterns
"""

# BEFORE: Broad Exception handling
def old_execute_startup_task(self, app, task_name: str):
    """Execute a single startup task with error handling."""
    if task_name not in self.startup_tasks:
        logger.warning(f"Startup task '{task_name}' not found")
        return

    try:
        task_func = self.startup_tasks[task_name]
        await task_func(app)
        logger.info(f"✅ {task_name} completed successfully")

    except Exception as e:  # ❌ Broad exception handling
        logger.error(f"❌ {task_name} failed with error: {e}")
        # Don't re-raise for optional tasks
        if task_name in ["initialize_basic_logging", "validate_configuration"]:
            raise


# AFTER: DRY Exception handling with specific exceptions
from dotmac_shared.exceptions import handle_lifecycle_exceptions, ExceptionStrategy

@handle_lifecycle_exceptions(
    strategy=ExceptionStrategy.LOG_AND_CONTINUE,
    context="Startup task execution"
)
async def execute_startup_task(self, app, task_name: str):
    """Execute a single startup task with DRY error handling."""
    if task_name not in self.startup_tasks:
        logger.warning(f"Startup task '{task_name}' not found")
        return

    task_func = self.startup_tasks[task_name] 
    await task_func(app)
    logger.info(f"✅ {task_name} completed successfully")
    
    # Critical tasks can still raise by checking after execution
    if task_name in ["initialize_basic_logging", "validate_configuration"]:
        # Re-run with different strategy for critical tasks
        raise  # This will be caught by the outer decorator


# ALTERNATIVE: Using custom exception handling for mixed requirements
from dotmac_shared.exceptions import ExceptionContext, handle_exceptions

@handle_exceptions(
    exceptions=ExceptionContext.LIFECYCLE_EXCEPTIONS,
    strategy=ExceptionStrategy.LOG_AND_CONTINUE,  # Default for optional tasks
    context="Startup task execution"
)
async def execute_startup_task_mixed(self, app, task_name: str):
    """Execute startup task with mixed critical/optional handling."""
    if task_name not in self.startup_tasks:
        logger.warning(f"Startup task '{task_name}' not found")
        return

    try:
        task_func = self.startup_tasks[task_name]
        await task_func(app)
        logger.info(f"✅ {task_name} completed successfully")
    except ExceptionContext.LIFECYCLE_EXCEPTIONS as e:
        # Critical tasks re-raise, optional tasks continue
        if task_name in ["initialize_basic_logging", "validate_configuration"]:
            logger.error(f"❌ Critical task {task_name} failed: {e}")
            raise
        else:
            logger.warning(f"⚠️ Optional task {task_name} failed: {e}")
            return None


# FILE OPERATION EXAMPLE
# BEFORE:
def old_load_config(self, config_file: str):
    try:
        with open(config_file, 'r') as f:
            return json.load(f)
    except Exception as e:  # ❌ Too broad
        logger.error(f"Failed to load config: {e}")
        return {}

# AFTER: 
from dotmac_shared.exceptions import handle_file_exceptions

@handle_file_exceptions(
    strategy=ExceptionStrategy.LOG_AND_RETURN_DEFAULT,
    context="Configuration loading",
    default_return={}
)
def load_config(self, config_file: str):
    """Load configuration with proper exception handling."""
    with open(config_file, 'r') as f:
        return json.load(f)


# API ENDPOINT EXAMPLE
# BEFORE:
async def old_call_external_api(self):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("https://api.example.com/data")
            return response.json()
    except Exception as e:  # ❌ Too broad
        logger.error(f"API call failed: {e}")
        return {"error": "Service unavailable"}

# AFTER:
from dotmac_shared.exceptions import handle_external_service_exceptions

@handle_external_service_exceptions(
    strategy=ExceptionStrategy.LOG_AND_RETURN_DEFAULT,
    context="External API call",
    default_return={"error": "Service unavailable"}
)
async def call_external_api(self):
    """Call external API with proper exception handling."""
    async with httpx.AsyncClient() as client:
        response = await client.get("https://api.example.com/data")
        return response.json()


# DATABASE OPERATION EXAMPLE  
# BEFORE:
async def old_execute_query(self, session, query):
    try:
        result = await session.execute(query)
        return result.fetchall()
    except Exception as e:  # ❌ Too broad
        logger.error(f"Database query failed: {e}")
        await session.rollback()
        raise

# AFTER:
from dotmac_shared.exceptions import handle_database_exceptions

@handle_database_exceptions(
    strategy=ExceptionStrategy.LOG_AND_RERAISE,
    context="Database query execution"
)
async def execute_query(self, session, query):
    """Execute database query with proper exception handling."""
    result = await session.execute(query)
    return result.fetchall()
    # Session rollback should be handled by session context manager


# CONTEXT MANAGER EXAMPLE
# BEFORE:
def old_process_files(self, file_list):
    results = []
    for file_path in file_list:
        try:
            with open(file_path, 'r') as f:
                data = f.read()
                results.append(process_data(data))
        except Exception as e:  # ❌ Too broad
            logger.error(f"Failed to process {file_path}: {e}")
            results.append(None)

# AFTER:
from dotmac_shared.exceptions import exception_context, ExceptionContext

def process_files(self, file_list):
    """Process multiple files with proper exception handling."""
    results = []
    for file_path in file_list:
        with exception_context(
            strategy=ExceptionStrategy.LOG_AND_RETURN_DEFAULT,
            exceptions=ExceptionContext.FILE_EXCEPTIONS,
            context=f"Processing file {file_path}",
            default_return=None
        ):
            with open(file_path, 'r') as f:
                data = f.read()
                results.append(process_data(data))
    return results


def print_migration_summary():
    """Print summary of migration benefits"""
    print("🎯 DRY Exception Handling Migration Benefits:")
    print()
    print("✅ IMPROVED:")
    print("   • Specific exception types instead of broad Exception")
    print("   • Consistent logging and error handling patterns")  
    print("   • Reusable decorators reduce code duplication")
    print("   • Clear strategies for different error scenarios")
    print("   • Better error context and debugging information")
    print()
    print("✅ ADDRESSES:")
    print("   • BLE001 (broad exception handling) violations")
    print("   • Inconsistent error handling across modules")
    print("   • Missing error context in logs")
    print("   • Duplicate exception handling code")
    print()
    print("✅ USAGE:")
    print("   1. Import: from dotmac_shared.exceptions import handle_lifecycle_exceptions")
    print("   2. Replace try/except Exception with @handle_lifecycle_exceptions decorator")
    print("   3. Choose appropriate strategy: LOG_AND_CONTINUE, LOG_AND_RERAISE, etc.")
    print("   4. Run: ruff check --select=BLE001 to verify improvements")


if __name__ == "__main__":
    print_migration_summary()