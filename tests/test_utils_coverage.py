"""
Additional tests for utils module to improve coverage.

Covers:
- validate_cron_expression exception handling
- SingletonMeta pattern
- safe_import error handling
- get_default_log_path for different platforms
- ensure_directory
"""

from autocron.core.utils import (
 SingletonMeta,
 ensure_directory,
 get_default_log_path,
 safe_import,
 validate_cron_expression,
)


class TestValidateCronExpression:
 """Test cron expression validation"""

 def test_validate_cron_expression_exception(self):
 """Test validate_cron_expression when croniter raises exception"""
 # Pass invalid type that would cause exception in croniter
 result = validate_cron_expression(None)
 assert result is False


class TestSingletonMeta:
 """Test Singleton metaclass"""

 def test_singleton_pattern(self):
 """Test that Singleton returns same instance"""

 class TestSingleton(metaclass=SingletonMeta):
 def __init__(self):
 self.value = 0

 # Create first instance
 instance1 = TestSingleton()
 instance1.value = 42

 # Create "second" instance - should be same object
 instance2 = TestSingleton()

 assert instance1 is instance2
 assert instance2.value == 42

 def test_singleton_different_classes(self):
 """Test that different Singleton classes have separate instances"""

 class SingletonA(metaclass=SingletonMeta):
 pass

 class SingletonB(metaclass=SingletonMeta):
 pass

 instance_a = SingletonA()
 instance_b = SingletonB()

 assert instance_a is not instance_b
 assert type(instance_a) is not type(instance_b)


class TestSafeImport:
 """Test safe_import utility"""

 def test_safe_import_success(self):
 """Test safe_import with valid module"""
 result = safe_import("os")
 assert result is not None
 assert result.__name__ == "os"

 def test_safe_import_failure(self):
 """Test safe_import with invalid module"""
 result = safe_import("nonexistent_module_xyz123")
 assert result is None


class TestGetDefaultLogPath:
 """Test get_default_log_path utility"""

 def test_get_default_log_path(self):
 """Test default log path returns valid path"""
 path = get_default_log_path()

 assert path is not None
 assert isinstance(path, str)
 assert "autocron" in path.lower() or "AutoCron" in path
 assert "logs" in path.lower() or "logs" in path


class TestEnsureDirectory:
 """Test ensure_directory utility"""

 def test_ensure_directory_creates_dir(self, tmp_path):
 """Test ensure_directory creates new directory"""
 new_dir = tmp_path / "test_dir" / "nested" / "path"

 assert not new_dir.exists()

 self._extracted_from_test_ensure_directory_existing_dir_7(new_dir)

 def test_ensure_directory_existing_dir(self, tmp_path):
 """Test ensure_directory with existing directory"""
 existing_dir = tmp_path / "existing"
 existing_dir.mkdir()

 self._extracted_from_test_ensure_directory_existing_dir_7(existing_dir)

 # TODO Rename this here and in `test_ensure_directory_creates_dir`
 # and `test_ensure_directory_existing_dir`
 def _extracted_from_test_ensure_directory_existing_dir_7(self, arg0):
 ensure_directory(str(arg0))
 assert arg0.exists()
 assert arg0.is_dir()

 def test_ensure_directory_nested_creation(self, tmp_path):
 """Test ensure_directory creates nested directories"""
 nested = tmp_path / "level1" / "level2" / "level3"

 ensure_directory(str(nested))

 assert nested.exists()
 assert (tmp_path / "level1").exists()
 assert (tmp_path / "level1" / "level2").exists()
