"""
Full integration tests for dotmac_shared_core package.

Tests the complete package functionality working together in realistic scenarios.
"""

import json
import tempfile
from datetime import timezone
from pathlib import Path

from dotmac_shared_core import (
    JSON,
    Result,
    ValidationError,
    common,
    ensure_in,
    ensure_range,
    is_email,
    is_uuid,
    sanitize_text,
    to_dict,
)


class TestDataProcessingWorkflow:
    """Test complete data processing workflow using multiple components."""

    def test_user_registration_workflow(self):
        """Test a complete user registration workflow."""
        # Simulate user input data
        raw_user_data = {
            "email": "test@example.com\x00\x01",  # Contains control chars
            "age": 25,
            "role": "admin",
            "id": None
        }

        # Step 1: Generate user ID
        user_id = common.ids.new_uuid()
        raw_user_data["id"] = str(user_id)

        # Step 2: Sanitize email
        clean_email = sanitize_text(raw_user_data["email"])

        # Step 3: Validate email format
        if not is_email(clean_email):
            result = Result.failure(ValidationError("Invalid email format", "INVALID_EMAIL"))
        else:
            # Step 4: Validate age range
            try:
                ensure_range(raw_user_data["age"], min_val=18, max_val=120, field="age")
            except ValidationError as e:
                result = Result.failure(e)
            else:
                # Step 5: Validate role
                try:
                    ensure_in(raw_user_data["role"], ["admin", "user", "guest"], "role")
                except ValidationError as e:
                    result = Result.failure(e)
                else:
                    # Step 6: Create final user data
                    user_data = {
                        "id": raw_user_data["id"],
                        "email": clean_email,
                        "age": raw_user_data["age"],
                        "role": raw_user_data["role"],
                        "created_at": common.time.isoformat(common.time.utcnow())
                    }
                    result = Result.success(user_data)

        # Verify successful workflow
        assert result.ok
        user_data = result.value
        assert is_uuid(user_data["id"])
        assert user_data["email"] == "test@example.com"  # Control chars removed
        assert user_data["age"] == 25
        assert user_data["role"] == "admin"
        assert "created_at" in user_data

    def test_file_upload_workflow(self):
        """Test file upload processing workflow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            upload_root = Path(temp_dir) / "uploads"
            upload_root.mkdir()

            # Step 1: Generate upload ID
            upload_id = common.ids.new_uuid()

            # Step 2: Sanitize filename
            raw_filename = "document\x00.pdf\x01"
            clean_filename = sanitize_text(raw_filename)

            # Step 3: Create safe file path
            try:
                file_path = common.paths.safe_join(
                    upload_root,
                    str(upload_id)[:8],  # Use part of ID as folder
                    clean_filename
                )
            except ValidationError as e:
                result = Result.failure(e)
            else:
                # Step 4: Create directory structure
                file_path.parent.mkdir(parents=True, exist_ok=True)

                # Step 5: Save file metadata
                metadata = {
                    "upload_id": str(upload_id),
                    "original_filename": clean_filename,
                    "file_path": str(file_path),
                    "uploaded_at": common.time.isoformat(common.time.utcnow()),
                    "size_bytes": 1024
                }

                result = Result.success(metadata)

        # Verify workflow
        assert result.ok
        metadata = result.value
        assert is_uuid(metadata["upload_id"])
        assert metadata["original_filename"] == "document.pdf"  # Sanitized
        assert "uploaded_at" in metadata

    def test_api_response_formatting(self):
        """Test API response formatting workflow."""
        # Step 1: Process some data that might fail
        def process_user_data(user_input: dict) -> Result[dict]:
            try:
                # Validate required fields
                if "email" not in user_input:
                    return Result.failure(ValidationError("Email required", "MISSING_EMAIL"))

                # Sanitize and validate email
                clean_email = sanitize_text(user_input["email"])
                if not is_email(clean_email):
                    return Result.failure(ValidationError("Invalid email", "INVALID_EMAIL"))

                # Validate age if provided
                if "age" in user_input:
                    ensure_range(user_input["age"], min_val=13, max_val=150, field="age")

                # Success case
                processed_data = {
                    "id": str(common.ids.new_uuid()),
                    "email": clean_email,
                    "age": user_input.get("age"),
                    "processed_at": common.time.isoformat(common.time.utcnow())
                }
                return Result.success(processed_data)

            except ValidationError as e:
                return Result.failure(e)

        # Test successful case
        success_input = {"email": "test@example.com", "age": 25}
        success_result = process_user_data(success_input)

        assert success_result.ok
        success_data = success_result.value

        # Format as JSON-serializable API response
        api_response: JSON = {
            "success": True,
            "data": success_data,
            "error": None
        }

        # Should be JSON serializable
        json_str = json.dumps(api_response)
        assert json_str is not None

        # Test error case
        error_input = {"email": "invalid-email"}
        error_result = process_user_data(error_input)

        assert not error_result.ok

        # Format error as API response
        error_api_response: JSON = {
            "success": False,
            "data": None,
            "error": to_dict(error_result.error)
        }

        # Should be JSON serializable
        error_json_str = json.dumps(error_api_response)
        assert json.loads(error_json_str)["error"]["error_code"] == "INVALID_EMAIL"


class TestErrorHandlingIntegration:
    """Test integrated error handling across modules."""

    def test_validation_chain_with_results(self):
        """Test chaining validations with Result containers."""
        def validate_user_profile(data: dict) -> Result[dict]:
            """Validate user profile data with multiple checks."""
            try:
                # Check email
                email = sanitize_text(data.get("email", ""))
                if not is_email(email):
                    return Result.failure(ValidationError("Invalid email format", "INVALID_EMAIL"))

                # Check age range
                age = data.get("age")
                if age is not None:
                    ensure_range(age, min_val=13, max_val=120, field="age")

                # Check role
                role = data.get("role", "user")
                ensure_in(role, ["admin", "moderator", "user"], "role")

                # If all validations pass
                validated_data = {
                    "email": email,
                    "age": age,
                    "role": role,
                    "validated_at": common.time.isoformat(common.time.utcnow())
                }
                return Result.success(validated_data)

            except ValidationError as e:
                return Result.failure(e)

        # Test valid data
        valid_data = {
            "email": "user@example.com",
            "age": 30,
            "role": "admin"
        }
        result = validate_user_profile(valid_data)
        assert result.ok
        assert result.value["email"] == "user@example.com"

        # Test invalid email
        invalid_email_data = {"email": "not-an-email"}
        result = validate_user_profile(invalid_email_data)
        assert not result.ok
        assert result.error.error_code == "INVALID_EMAIL"

        # Test invalid age
        invalid_age_data = {
            "email": "valid@example.com",
            "age": 200
        }
        result = validate_user_profile(invalid_age_data)
        assert not result.ok
        assert result.error.error_code == "VALUE_OUT_OF_RANGE"

        # Test invalid role
        invalid_role_data = {
            "email": "valid@example.com",
            "role": "superuser"
        }
        result = validate_user_profile(invalid_role_data)
        assert not result.ok
        assert result.error.error_code == "VALUE_NOT_ALLOWED"

    def test_nested_error_propagation(self):
        """Test error propagation through nested operations."""
        def process_document(doc_data: dict) -> Result[dict]:
            """Process document with multiple validation steps."""
            try:
                # Step 1: Validate title
                title = sanitize_text(doc_data.get("title", ""))
                if not title:
                    return Result.failure(ValidationError("Title required", "MISSING_TITLE"))

                # Step 2: Validate category
                category = doc_data.get("category")
                ensure_in(category, ["public", "private", "draft"], "category")

                # Step 3: Create safe file path
                doc_id = str(common.ids.new_uuid())
                safe_path = common.paths.safe_join(
                    Path("/var/docs"),
                    category,
                    f"{doc_id}.txt"
                )

                processed_doc = {
                    "id": doc_id,
                    "title": title,
                    "category": category,
                    "file_path": str(safe_path),
                    "created_at": common.time.isoformat(common.time.utcnow())
                }

                return Result.success(processed_doc)

            except ValidationError as e:
                return Result.failure(e)

        # Test successful processing
        valid_doc = {
            "title": "My Document",
            "category": "public"
        }
        result = process_document(valid_doc)
        assert result.ok
        assert result.value["title"] == "My Document"
        assert "public" in result.value["file_path"]

        # Test missing title
        no_title_doc = {"category": "public"}
        result = process_document(no_title_doc)
        assert not result.ok
        assert result.error.error_code == "MISSING_TITLE"

        # Test invalid category
        invalid_category_doc = {
            "title": "Test Doc",
            "category": "secret"
        }
        result = process_document(invalid_category_doc)
        assert not result.ok
        assert result.error.error_code == "VALUE_NOT_ALLOWED"


class TestConcurrentOperations:
    """Test package behavior under concurrent operations."""

    def test_concurrent_id_generation(self):
        """Test concurrent ID generation doesn't produce duplicates."""
        import threading
        from collections import defaultdict

        results = defaultdict(int)

        def generate_ids():
            """Generate IDs in a thread."""
            thread_ids = set()
            for _ in range(100):
                uuid_id = str(common.ids.new_uuid())
                ulid_id = common.ids.new_ulid()
                thread_ids.add(uuid_id)
                thread_ids.add(ulid_id)

            # Count unique IDs per thread
            results[threading.current_thread().ident] = len(thread_ids)

        # Create multiple threads
        threads = []
        for _ in range(4):
            thread = threading.Thread(target=generate_ids)
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Each thread should have generated 200 unique IDs
        for thread_id, count in results.items():
            assert count == 200

    def test_concurrent_time_operations(self):
        """Test concurrent time operations are consistent."""
        import threading
        import time

        start_times = []
        end_times = []

        def time_operations():
            """Perform time operations in thread."""
            start = common.time.utcnow()
            time.sleep(0.1)  # Small delay
            end = common.time.utcnow()

            start_times.append(start)
            end_times.append(end)

        # Run concurrent time operations
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=time_operations)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # All start times should be before all end times
        min_start = min(start_times)
        max_end = max(end_times)
        assert min_start < max_end

        # All times should be UTC
        for dt in start_times + end_times:
            assert dt.tzinfo == timezone.utc


class TestRealWorldScenarios:
    """Test realistic usage scenarios."""

    def test_web_request_processing(self):
        """Test processing a web request with validation and response formatting."""
        # Simulate incoming request data
        request_data = {
            "user_id": str(common.ids.new_uuid()),
            "action": "update_profile",
            "data": {
                "email": " test@EXAMPLE.com\x00 ",  # Needs sanitization
                "age": "25",  # String that needs conversion
                "preferences": {
                    "theme": "dark",
                    "notifications": True
                }
            },
            "timestamp": common.time.isoformat(common.time.utcnow())
        }

        def process_request(req_data: dict) -> Result[dict]:
            """Process the web request."""
            try:
                # Extract and validate user ID
                user_id = req_data.get("user_id")
                if not user_id or not is_uuid(user_id):
                    return Result.failure(ValidationError("Invalid user ID", "INVALID_USER_ID"))

                # Validate action
                action = req_data.get("action")
                ensure_in(action, ["create_profile", "update_profile", "delete_profile"], "action")

                # Process profile data
                profile_data = req_data.get("data", {})

                # Sanitize and validate email
                raw_email = profile_data.get("email", "")
                clean_email = sanitize_text(raw_email).strip().lower()
                if not is_email(clean_email):
                    return Result.failure(ValidationError("Invalid email", "INVALID_EMAIL"))

                # Validate age
                try:
                    age = int(profile_data.get("age", 0))
                    ensure_range(age, min_val=13, max_val=150, field="age")
                except (ValueError, TypeError):
                    return Result.failure(ValidationError("Invalid age format", "INVALID_AGE"))

                # Validate theme preference
                theme = profile_data.get("preferences", {}).get("theme", "light")
                ensure_in(theme, ["light", "dark", "auto"], "theme")

                # Create response
                response_data = {
                    "user_id": user_id,
                    "action": action,
                    "profile": {
                        "email": clean_email,
                        "age": age,
                        "preferences": {
                            "theme": theme,
                            "notifications": profile_data.get("preferences", {}).get("notifications", False)
                        }
                    },
                    "processed_at": common.time.isoformat(common.time.utcnow()),
                    "request_id": str(common.ids.new_uuid())
                }

                return Result.success(response_data)

            except ValidationError as e:
                return Result.failure(e)
            except Exception as e:
                # Convert unexpected errors to CoreError
                return Result.failure(ValidationError(f"Processing error: {str(e)}", "PROCESSING_ERROR"))

        # Process the request
        result = process_request(request_data)

        # Verify successful processing
        assert result.ok
        response = result.value

        assert is_uuid(response["user_id"])
        assert response["action"] == "update_profile"
        assert response["profile"]["email"] == "test@example.com"  # Cleaned
        assert response["profile"]["age"] == 25
        assert response["profile"]["preferences"]["theme"] == "dark"
        assert "processed_at" in response
        assert is_uuid(response["request_id"])

        # Test error case
        invalid_request = {
            "user_id": "not-a-uuid",
            "action": "update_profile"
        }
        error_result = process_request(invalid_request)
        assert not error_result.ok
        assert error_result.error.error_code == "INVALID_USER_ID"

    def test_batch_data_processing(self):
        """Test processing a batch of data items."""
        # Simulate batch of user registrations
        batch_data = [
            {"email": "user1@example.com", "age": 25, "role": "user"},
            {"email": "invalid-email", "age": 30, "role": "admin"},  # Invalid email
            {"email": "user3@example.com", "age": 16, "role": "user"},
            {"email": "user4@example.com", "age": 200, "role": "user"},  # Invalid age
            {"email": "user5@example.com", "age": 28, "role": "superuser"},  # Invalid role
        ]

        def process_batch(items: list[dict]) -> dict:
            """Process batch of items, collecting successes and failures."""
            successes = []
            failures = []

            for i, item in enumerate(items):
                try:
                    # Sanitize email
                    email = sanitize_text(item.get("email", ""))
                    if not is_email(email):
                        raise ValidationError(f"Invalid email in item {i}", "INVALID_EMAIL")

                    # Validate age
                    age = item.get("age")
                    ensure_range(age, min_val=18, max_val=120, field="age")

                    # Validate role
                    role = item.get("role", "user")
                    ensure_in(role, ["user", "admin", "moderator"], "role")

                    # Success - create processed item
                    processed_item = {
                        "id": str(common.ids.new_uuid()),
                        "email": email,
                        "age": age,
                        "role": role,
                        "processed_at": common.time.isoformat(common.time.utcnow())
                    }
                    successes.append(processed_item)

                except ValidationError as e:
                    failures.append({
                        "item_index": i,
                        "item_data": item,
                        "error": to_dict(e)
                    })

            return {
                "total_items": len(items),
                "successful": len(successes),
                "failed": len(failures),
                "successes": successes,
                "failures": failures,
                "batch_id": str(common.ids.new_uuid()),
                "processed_at": common.time.isoformat(common.time.utcnow())
            }

        result = process_batch(batch_data)

        # Verify batch processing results
        assert result["total_items"] == 5
        assert result["successful"] == 1  # Only first item should succeed
        assert result["failed"] == 4

        # Check successful item
        success = result["successes"][0]
        assert success["email"] == "user1@example.com"
        assert success["age"] == 25
        assert success["role"] == "user"
        assert is_uuid(success["id"])

        # Check failure reasons
        failure_codes = [f["error"]["error_code"] for f in result["failures"]]
        assert "INVALID_EMAIL" in failure_codes
        assert "VALUE_OUT_OF_RANGE" in failure_codes  # Age validation
        assert "VALUE_NOT_ALLOWED" in failure_codes   # Role validation
