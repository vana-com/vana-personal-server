"""
Unit tests for file subsetting and general permissions (PRO-695).

Tests the new functionality that allows:
1. Runtime file_ids subsetting
2. Flexible parameters (grant with parameters: {})
3. Both general and narrow access modes
"""

import pytest
from services.operations import OperationsService
from domain.exceptions import ValidationError


class TestFileSubsetting:
    """Tests for _validate_and_select_files method."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create a minimal OperationsService instance (we only test the validation method)
        self.service = OperationsService.__new__(OperationsService)

    def test_no_runtime_file_ids_uses_all_permission_files(self):
        """When request omits file_ids, should use all files from permission."""
        permission_files = [1, 2, 3]
        runtime_files = None

        result = self.service._validate_and_select_files(
            permission_files, runtime_files, "test_req_1"
        )

        assert result == [1, 2, 3]

    def test_valid_subset_accepted(self):
        """When request specifies valid subset, should use those files."""
        permission_files = [1, 2, 3]
        runtime_files = [1, 2]

        result = self.service._validate_and_select_files(
            permission_files, runtime_files, "test_req_2"
        )

        assert result == [1, 2]

    def test_single_file_subset_accepted(self):
        """Should accept request for single file from permission."""
        permission_files = [1, 2, 3]
        runtime_files = [2]

        result = self.service._validate_and_select_files(
            permission_files, runtime_files, "test_req_3"
        )

        assert result == [2]

    def test_all_files_explicitly_requested(self):
        """Should accept request that explicitly lists all permission files."""
        permission_files = [1, 2, 3]
        runtime_files = [1, 2, 3]

        result = self.service._validate_and_select_files(
            permission_files, runtime_files, "test_req_4"
        )

        assert result == [1, 2, 3]

    def test_invalid_subset_rejected(self):
        """Should reject request with files not in permission."""
        permission_files = [1, 2, 3]
        runtime_files = [1, 4]  # File 4 not in permission

        with pytest.raises(ValidationError) as exc_info:
            self.service._validate_and_select_files(
                permission_files, runtime_files, "test_req_5"
            )

        assert "not authorized by permission" in str(exc_info.value)
        assert "4" in str(exc_info.value)

    def test_multiple_invalid_files_rejected(self):
        """Should reject request with multiple unauthorized files."""
        permission_files = [1, 2]
        runtime_files = [1, 3, 4, 5]  # Files 3, 4, 5 not in permission

        with pytest.raises(ValidationError) as exc_info:
            self.service._validate_and_select_files(
                permission_files, runtime_files, "test_req_6"
            )

        assert "not authorized by permission" in str(exc_info.value)

    def test_empty_array_rejected(self):
        """Should reject empty file_ids array."""
        permission_files = [1, 2, 3]
        runtime_files = []

        with pytest.raises(ValidationError) as exc_info:
            self.service._validate_and_select_files(
                permission_files, runtime_files, "test_req_7"
            )

        assert "cannot be empty" in str(exc_info.value)

    def test_completely_disjoint_sets_rejected(self):
        """Should reject request where no files overlap with permission."""
        permission_files = [1, 2, 3]
        runtime_files = [4, 5, 6]

        with pytest.raises(ValidationError) as exc_info:
            self.service._validate_and_select_files(
                permission_files, runtime_files, "test_req_8"
            )

        assert "not authorized by permission" in str(exc_info.value)

    def test_order_preservation(self):
        """Should preserve the order of requested files."""
        permission_files = [1, 2, 3, 4, 5]
        runtime_files = [3, 1, 5]  # Different order

        result = self.service._validate_and_select_files(
            permission_files, runtime_files, "test_req_9"
        )

        assert result == [3, 1, 5]  # Order preserved from request


class TestParameterMerging:
    """Tests for parameter merging with flexible grants."""

    def test_empty_grant_parameters_accepts_runtime(self):
        """Grant with parameters: {} should accept any runtime parameters."""
        from services.parameter_merge import merge_parameters

        grant_params = {}
        runtime_params = {"prompt": "analyze this", "temperature": 0.7}

        result = merge_parameters(grant_params, runtime_params)

        assert result == {"prompt": "analyze this", "temperature": 0.7}

    def test_grant_parameters_override_runtime(self):
        """Grant parameters should take precedence over runtime."""
        from services.parameter_merge import merge_parameters

        grant_params = {"model": "gpt-4", "filters": {"1": "$.publicData"}}
        runtime_params = {"model": "gpt-3.5", "temperature": 0.7}

        result = merge_parameters(grant_params, runtime_params)

        assert result["model"] == "gpt-4"  # Grant wins
        assert result["temperature"] == 0.7  # Runtime added
        assert result["filters"] == {"1": "$.publicData"}  # Grant preserved

    def test_none_runtime_parameters_uses_grant(self):
        """None runtime parameters should use grant as-is."""
        from services.parameter_merge import merge_parameters

        grant_params = {"prompt": "fixed prompt", "model": "gpt-4"}
        runtime_params = None

        result = merge_parameters(grant_params, runtime_params)

        assert result == {"prompt": "fixed prompt", "model": "gpt-4"}

    def test_partial_override(self):
        """Runtime can add new parameters, grant overrides conflicts."""
        from services.parameter_merge import merge_parameters

        grant_params = {"filters": {"1": "$.data"}}
        runtime_params = {"prompt": "hello", "temperature": 0.5, "filters": {"2": "$.other"}}

        result = merge_parameters(grant_params, runtime_params)

        assert result["prompt"] == "hello"
        assert result["temperature"] == 0.5
        assert result["filters"] == {"1": "$.data"}  # Grant filter wins


class TestGeneralPermissionsWorkflow:
    """Integration-style tests for general permissions workflow."""

    def test_reusable_signature_scenario(self):
        """
        Test general access mode (PRO-695 use case).

        Permission grants files [1, 2, 3] with parameters: {}
        App can make multiple requests with different prompts using same permission.
        """
        from services.parameter_merge import merge_parameters

        # Permission setup
        permission_files = [1, 2, 3]
        grant_params = {}  # Flexible grant

        # Request 1: Describe personality
        runtime_params_1 = {"prompt": "Describe this user's personality"}
        merged_1 = merge_parameters(grant_params, runtime_params_1)
        assert merged_1 == {"prompt": "Describe this user's personality"}

        # Request 2: Favorite song (different prompt, same permission)
        runtime_params_2 = {"prompt": "What is this user's favorite song?"}
        merged_2 = merge_parameters(grant_params, runtime_params_2)
        assert merged_2 == {"prompt": "What is this user's favorite song?"}

        # Both requests use same permission_files
        assert permission_files == [1, 2, 3]

    def test_narrow_access_scenario(self):
        """
        Test narrow access mode (PRO-695 use case).

        Permission grants files [1, 2, 3] but request specifies subset [1, 2].
        """
        service = OperationsService.__new__(OperationsService)

        permission_files = [1, 2, 3]
        runtime_files = [1, 2]  # Just LinkedIn and Spotify, not ChatGPT

        result = service._validate_and_select_files(
            permission_files, runtime_files, "narrow_req"
        )

        assert result == [1, 2]
        assert 3 not in result  # ChatGPT excluded
