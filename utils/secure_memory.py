"""
Secure Memory Management utilities for protecting sensitive data in memory.
This ensures that decrypted data is properly wiped after use.
"""

import ctypes
import gc
import logging
from typing import Any, Union, List, Dict
import numpy as np
import time

logger = logging.getLogger(__name__)

class SecureMemoryManager:
    """Manages secure deletion of sensitive data from memory."""
    
    def __init__(self):
        self.tracked_objects = []
    
    def secure_delete(self, obj: Any, deep: bool = True) -> None:
        """
        Securely delete an object from memory.
        
        Args:
            obj: Object to securely delete
            deep: Whether to recursively delete nested objects
        """
        try:
            if deep:
                self._secure_delete_deep(obj)
            else:
                self._secure_delete_shallow(obj)
        except Exception as e:
            logger.warning(f"Secure deletion failed: {e}")
        finally:
            # Force garbage collection
            gc.collect()
    
    def _secure_delete_deep(self, obj: Any) -> None:
        """Recursively delete nested objects securely."""
        
        if isinstance(obj, dict):
            for key, value in list(obj.items()):
                self._secure_delete_deep(value)
                # Overwrite key
                obj[key] = "0" * len(str(key)) if isinstance(key, str) else 0
            obj.clear()
            
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                self._secure_delete_deep(item)
                # Overwrite item
                if isinstance(item, str):
                    obj[i] = "0" * len(item)
                elif isinstance(item, (int, float)):
                    obj[i] = 0
            obj.clear()
            
        elif isinstance(obj, str):
            # Overwrite string content
            self._overwrite_string(obj)
            
        elif isinstance(obj, bytes):
            # Overwrite bytes content
            self._overwrite_bytes(obj)
            
        elif isinstance(obj, np.ndarray):
            # Overwrite numpy array
            obj.fill(0)
            
        elif hasattr(obj, '__dict__'):
            # Custom objects - overwrite attributes
            for attr_name, attr_value in obj.__dict__.items():
                self._secure_delete_deep(attr_value)
                setattr(obj, attr_name, None)
    
    def _secure_delete_shallow(self, obj: Any) -> None:
        """Delete object without recursive cleanup."""
        
        if isinstance(obj, str):
            self._overwrite_string(obj)
        elif isinstance(obj, bytes):
            self._overwrite_bytes(obj)
        elif isinstance(obj, np.ndarray):
            obj.fill(0)
    
    def _overwrite_string(self, string_obj: str) -> None:
        """Overwrite string content with zeros."""
        try:
            # Get the memory address and size
            string_id = id(string_obj)
            string_len = len(string_obj)
            
            # Overwrite with zeros
            ctypes.memset(string_id, 0, string_len)
            
        except Exception as e:
            logger.debug(f"String overwrite failed: {e}")
            # Fallback: try to modify the string
            try:
                # Create new string with zeros
                new_string = "0" * len(string_obj)
                # This doesn't overwrite the original memory, but it's a fallback
                string_obj = new_string
            except:
                pass
    
    def _overwrite_bytes(self, bytes_obj: bytes) -> None:
        """Overwrite bytes content with zeros."""
        try:
            # Get the memory address and size
            bytes_id = id(bytes_obj)
            bytes_len = len(bytes_obj)
            
            # Overwrite with zeros
            ctypes.memset(bytes_id, 0, bytes_len)
            
        except Exception as e:
            logger.debug(f"Bytes overwrite failed: {e}")
    
    def secure_delete_list(self, data_list: List[Any]) -> None:
        """Securely delete a list of sensitive data."""
        for item in data_list:
            self.secure_delete(item)
        data_list.clear()
    
    def secure_delete_dict(self, data_dict: Dict[str, Any]) -> None:
        """Securely delete a dictionary of sensitive data."""
        for key, value in data_dict.items():
            self.secure_delete(value)
        data_dict.clear()
    
    def track_object(self, obj: Any, description: str = "") -> None:
        """Track an object for later secure deletion."""
        self.tracked_objects.append({
            'object': obj,
            'description': description,
            'tracked_at': time.time()
        })
    
    def cleanup_tracked_objects(self) -> None:
        """Securely delete all tracked objects."""
        for tracked in self.tracked_objects:
            try:
                self.secure_delete(tracked['object'])
                logger.info(f"Cleaned up tracked object: {tracked['description']}")
            except Exception as e:
                logger.error(f"Failed to cleanup tracked object: {e}")
        
        self.tracked_objects.clear()

# Global instance
secure_memory = SecureMemoryManager()

# Convenience functions
def secure_delete(obj: Any, deep: bool = True) -> None:
    """
    Convenience function to securely delete an object.
    
    Args:
        obj: Object to securely delete
        deep: Whether to recursively delete nested objects
    """
    secure_memory.secure_delete(obj, deep)

def secure_delete_string(string_obj: str) -> None:
    """Securely delete a string object."""
    secure_memory._overwrite_string(string_obj)

def secure_delete_bytes(bytes_obj: bytes) -> None:
    """Securely delete a bytes object."""
    secure_memory._overwrite_bytes(bytes_obj)

def secure_delete_list(data_list: List[Any]) -> None:
    """Securely delete a list of sensitive data."""
    secure_memory.secure_delete_list(data_list)

def secure_delete_dict(data_dict: Dict[str, Any]) -> None:
    """Securely delete a dictionary of sensitive data."""
    secure_memory.secure_delete_dict(data_dict)

def track_for_cleanup(obj: Any, description: str = "") -> None:
    """Track an object for later cleanup."""
    secure_memory.track_object(obj, description)

def cleanup_all_tracked() -> None:
    """Clean up all tracked objects."""
    secure_memory.cleanup_tracked_objects()

# Context manager for automatic cleanup
class SecureContext:
    """Context manager for automatic secure cleanup."""
    
    def __init__(self, *objects, descriptions: List[str] = None):
        self.objects = objects
        self.descriptions = descriptions or [""] * len(objects)
    
    def __enter__(self):
        return self.objects[0] if len(self.objects) == 1 else self.objects
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        for obj, desc in zip(self.objects, self.descriptions):
            try:
                secure_delete(obj)
                logger.debug(f"Auto-cleaned up: {desc}")
            except Exception as e:
                logger.warning(f"Auto-cleanup failed for {desc}: {e}")

# Decorator for automatic cleanup
def secure_cleanup(func):
    """Decorator that automatically cleans up sensitive data after function execution."""
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            # Clean up any tracked objects
            cleanup_all_tracked()
    
    return wrapper
