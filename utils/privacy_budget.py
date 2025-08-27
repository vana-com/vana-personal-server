"""
Privacy Budget Management System for Differential Privacy.
This system tracks and limits how much information about individuals can be revealed over time.
"""

import logging
import time
import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import numpy as np
from collections import defaultdict
import hashlib

logger = logging.getLogger(__name__)

class PrivacyLevel(Enum):
    """Privacy levels with corresponding epsilon values."""
    CRITICAL = 0.1    # Maximum privacy, minimum utility
    HIGH = 0.5        # High privacy, moderate utility
    MEDIUM = 1.0      # Balanced privacy and utility
    LOW = 2.0         # Lower privacy, higher utility
    MINIMAL = 5.0     # Minimal privacy, maximum utility

@dataclass
class PrivacyBudget:
    """Privacy budget for a user or operation."""
    user_id: str
    total_epsilon: float
    used_epsilon: float
    remaining_epsilon: float
    last_reset: float
    reset_interval: float  # seconds
    operations: List[Dict[str, Any]]
    
    @property
    def is_exhausted(self) -> bool:
        """Check if privacy budget is exhausted."""
        return self.remaining_epsilon <= 0
    
    @property
    def usage_percentage(self) -> float:
        """Get privacy budget usage percentage."""
        if self.total_epsilon <= 0:
            return 100.0
        return (self.used_epsilon / self.total_epsilon) * 100

@dataclass
class OperationPrivacyCost:
    """Privacy cost of a specific operation."""
    operation_id: str
    epsilon_cost: float
    operation_type: str
    timestamp: float
    features_processed: int
    privacy_score: float
    metadata: Dict[str, Any]

class PrivacyBudgetManager:
    """Manages privacy budgets and enforces differential privacy constraints."""
    
    def __init__(self, default_epsilon: float = 1.0, default_reset_interval: float = 86400):
        """
        Initialize privacy budget manager.
        
        Args:
            default_epsilon: Default privacy budget per user
            default_reset_interval: Default reset interval in seconds (24 hours)
        """
        self.default_epsilon = default_epsilon
        self.default_reset_interval = default_reset_interval
        self.user_budgets: Dict[str, PrivacyBudget] = {}
        self.operation_costs: Dict[str, OperationPrivacyCost] = {}
        self.global_settings = {
            "max_epsilon_per_operation": 2.0,
            "min_epsilon_per_operation": 0.1,
            "emergency_epsilon_reserve": 0.5,
            "budget_warning_threshold": 0.8  # 80% usage warning
        }
    
    def get_or_create_budget(self, user_id: str, epsilon: Optional[float] = None) -> PrivacyBudget:
        """
        Get or create privacy budget for a user.
        
        Args:
            user_id: Unique user identifier
            epsilon: Privacy budget amount (uses default if None)
            
        Returns:
            PrivacyBudget for the user
        """
        
        if user_id not in self.user_budgets:
            # Create new budget
            budget = PrivacyBudget(
                user_id=user_id,
                total_epsilon=epsilon or self.default_epsilon,
                used_epsilon=0.0,
                remaining_epsilon=epsilon or self.default_epsilon,
                last_reset=time.time(),
                reset_interval=self.default_reset_interval,
                operations=[]
            )
            self.user_budgets[user_id] = budget
            logger.info(f"Created new privacy budget for user {user_id}: {epsilon or self.default_epsilon} epsilon")
        
        # Check if budget needs reset
        budget = self.user_budgets[user_id]
        if self._should_reset_budget(budget):
            self._reset_budget(budget)
        
        return budget
    
    def check_operation_allowed(self, user_id: str, operation_type: str, 
                               features_count: int, requested_epsilon: float) -> Tuple[bool, str]:
        """
        Check if an operation is allowed based on privacy budget.
        
        Args:
            user_id: User identifier
            operation_type: Type of operation
            features_count: Number of features to be processed
            requested_epsilon: Requested privacy level
            
        Returns:
            Tuple of (is_allowed, reason)
        """
        
        budget = self.get_or_create_budget(user_id)
        
        # Check if budget is exhausted
        if budget.is_exhausted:
            return False, f"Privacy budget exhausted for user {user_id}"
        
        # Check if requested epsilon exceeds remaining budget
        if requested_epsilon > budget.remaining_epsilon:
            return False, f"Requested epsilon {requested_epsilon} exceeds remaining budget {budget.remaining_epsilon}"
        
        # Check if requested epsilon is within allowed range
        if requested_epsilon < self.global_settings["min_epsilon_per_operation"]:
            return False, f"Requested epsilon {requested_epsilon} below minimum {self.global_settings['min_epsilon_per_operation']}"
        
        if requested_epsilon > self.global_settings["max_epsilon_per_operation"]:
            return False, f"Requested epsilon {requested_epsilon} above maximum {self.global_settings['max_epsilon_per_operation']}"
        
        # Check if operation would leave insufficient reserve
        remaining_after_operation = budget.remaining_epsilon - requested_epsilon
        if remaining_after_operation < self.global_settings["emergency_epsilon_reserve"]:
            logger.warning(f"Operation would leave insufficient privacy reserve for user {user_id}")
            # Allow operation but warn
        
        return True, "Operation allowed"
    
    def record_operation_cost(self, user_id: str, operation_id: str, operation_type: str,
                            epsilon_cost: float, features_processed: int, 
                            privacy_score: float, metadata: Dict[str, Any]) -> bool:
        """
        Record the privacy cost of an operation.
        
        Args:
            user_id: User identifier
            operation_id: Unique operation identifier
            operation_type: Type of operation
            epsilon_cost: Privacy cost in epsilon
            features_processed: Number of features processed
            privacy_score: Privacy score of the operation
            metadata: Additional operation metadata
            
        Returns:
            True if operation was recorded successfully
        """
        
        try:
            budget = self.get_or_create_budget(user_id)
            
            # Create operation cost record
            operation_cost = OperationPrivacyCost(
                operation_id=operation_id,
                epsilon_cost=epsilon_cost,
                operation_type=operation_type,
                timestamp=time.time(),
                features_processed=features_processed,
                privacy_score=privacy_score,
                metadata=metadata
            )
            
            # Update budget
            budget.used_epsilon += epsilon_cost
            budget.remaining_epsilon -= epsilon_cost
            budget.operations.append(asdict(operation_cost))
            
            # Store operation cost
            self.operation_costs[operation_id] = operation_cost
            
            logger.info(f"Recorded operation cost for user {user_id}: {epsilon_cost} epsilon")
            
            # Check if budget is running low
            if budget.usage_percentage >= self.global_settings["budget_warning_threshold"]:
                logger.warning(f"Privacy budget running low for user {user_id}: {budget.usage_percentage:.1f}% used")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to record operation cost: {e}")
            return False
    
    def calculate_optimal_epsilon(self, user_id: str, operation_type: str, 
                                features_count: int, privacy_requirement: PrivacyLevel) -> float:
        """
        Calculate optimal epsilon value for an operation.
        
        Args:
            user_id: User identifier
            operation_type: Type of operation
            features_count: Number of features to process
            privacy_requirement: Required privacy level
            
        Returns:
            Optimal epsilon value
        """
        
        budget = self.get_or_create_budget(user_id)
        
        # Start with the privacy requirement
        optimal_epsilon = privacy_requirement.value
        
        # Adjust based on remaining budget
        if optimal_epsilon > budget.remaining_epsilon:
            optimal_epsilon = budget.remaining_epsilon
        
        # Adjust based on features count (more features = higher epsilon needed)
        feature_factor = min(1.5, 1.0 + (features_count / 100.0))
        optimal_epsilon *= feature_factor
        
        # Ensure within bounds
        optimal_epsilon = max(
            self.global_settings["min_epsilon_per_operation"],
            min(optimal_epsilon, self.global_settings["max_epsilon_per_operation"])
        )
        
        # Ensure we don't exceed remaining budget
        optimal_epsilon = min(optimal_epsilon, budget.remaining_epsilon)
        
        return optimal_epsilon
    
    def get_budget_summary(self, user_id: str) -> Dict[str, Any]:
        """
        Get privacy budget summary for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Budget summary dictionary
        """
        
        budget = self.get_or_create_budget(user_id)
        
        # Calculate statistics
        recent_operations = [
            op for op in budget.operations 
            if time.time() - op["timestamp"] < 86400  # Last 24 hours
        ]
        
        daily_usage = sum(op["epsilon_cost"] for op in recent_operations)
        
        return {
            "user_id": user_id,
            "total_epsilon": budget.total_epsilon,
            "used_epsilon": budget.used_epsilon,
            "remaining_epsilon": budget.remaining_epsilon,
            "usage_percentage": budget.usage_percentage,
            "is_exhausted": budget.is_exhausted,
            "last_reset": budget.last_reset,
            "next_reset": budget.last_reset + budget.reset_interval,
            "daily_usage": daily_usage,
            "total_operations": len(budget.operations),
            "recent_operations": len(recent_operations)
        }
    
    def reset_user_budget(self, user_id: str, new_epsilon: Optional[float] = None) -> bool:
        """
        Reset privacy budget for a user.
        
        Args:
            user_id: User identifier
            new_epsilon: New epsilon value (uses current total if None)
            
        Returns:
            True if budget was reset successfully
        """
        
        try:
            if user_id in self.user_budgets:
                budget = self.user_budgets[user_id]
                
                # Update total epsilon if provided
                if new_epsilon is not None:
                    budget.total_epsilon = new_epsilon
                
                # Reset usage
                budget.used_epsilon = 0.0
                budget.remaining_epsilon = budget.total_epsilon
                budget.last_reset = time.time()
                budget.operations = []
                
                logger.info(f"Reset privacy budget for user {user_id}: {budget.total_epsilon} epsilon")
                return True
            else:
                logger.warning(f"Attempted to reset budget for non-existent user: {user_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to reset budget for user {user_id}: {e}")
            return False
    
    def _should_reset_budget(self, budget: PrivacyBudget) -> bool:
        """Check if budget should be reset based on time interval."""
        return time.time() - budget.last_reset >= budget.reset_interval
    
    def _reset_budget(self, budget: PrivacyBudget) -> None:
        """Reset budget to initial state."""
        old_epsilon = budget.remaining_epsilon
        budget.used_epsilon = 0.0
        budget.remaining_epsilon = budget.total_epsilon
        budget.last_reset = time.time()
        budget.operations = []
        
        logger.info(f"Auto-reset budget for user {budget.user_id}: {old_epsilon} -> {budget.remaining_epsilon} epsilon")
    
    def get_global_statistics(self) -> Dict[str, Any]:
        """Get global privacy budget statistics."""
        
        total_users = len(self.user_budgets)
        total_epsilon_allocated = sum(b.total_epsilon for b in self.user_budgets.values())
        total_epsilon_used = sum(b.used_epsilon for b in self.user_budgets.values())
        exhausted_budgets = sum(1 for b in self.user_budgets.values() if b.is_exhausted)
        
        return {
            "total_users": total_users,
            "total_epsilon_allocated": total_epsilon_allocated,
            "total_epsilon_used": total_epsilon_used,
            "global_usage_percentage": (total_epsilon_used / total_epsilon_allocated * 100) if total_epsilon_allocated > 0 else 0,
            "exhausted_budgets": exhausted_budgets,
            "active_budgets": total_users - exhausted_budgets,
            "average_epsilon_per_user": total_epsilon_allocated / total_users if total_users > 0 else 0
        }
    
    def export_budget_data(self, user_id: str) -> Dict[str, Any]:
        """Export budget data for a user (for audit purposes)."""
        
        if user_id not in self.user_budgets:
            return {}
        
        budget = self.user_budgets[user_id]
        
        return {
            "budget_info": asdict(budget),
            "operation_history": budget.operations,
            "export_timestamp": time.time(),
            "export_hash": self._generate_export_hash(user_id)
        }
    
    def _generate_export_hash(self, user_id: str) -> str:
        """Generate hash for export verification."""
        budget = self.user_budgets[user_id]
        data_string = f"{user_id}:{budget.total_epsilon}:{budget.used_epsilon}:{budget.last_reset}"
        return hashlib.sha256(data_string.encode()).hexdigest()

# Global instance
privacy_budget_manager = PrivacyBudgetManager()

# Convenience functions
def get_privacy_budget(user_id: str) -> PrivacyBudget:
    """Get privacy budget for a user."""
    return privacy_budget_manager.get_or_create_budget(user_id)

def check_operation_privacy(user_id: str, operation_type: str, 
                          features_count: int, requested_epsilon: float) -> Tuple[bool, str]:
    """Check if operation is allowed based on privacy budget."""
    return privacy_budget_manager.check_operation_allowed(user_id, operation_type, features_count, requested_epsilon)

def record_privacy_cost(user_id: str, operation_id: str, operation_type: str,
                       epsilon_cost: float, features_processed: int, 
                       privacy_score: float, metadata: Dict[str, Any]) -> bool:
    """Record privacy cost of an operation."""
    return privacy_budget_manager.record_operation_cost(
        user_id, operation_id, operation_type, epsilon_cost, 
        features_processed, privacy_score, metadata
    )

def calculate_optimal_privacy(user_id: str, operation_type: str, 
                            features_count: int, privacy_requirement: PrivacyLevel) -> float:
    """Calculate optimal epsilon value for an operation."""
    return privacy_budget_manager.calculate_optimal_epsilon(
        user_id, operation_type, features_count, privacy_requirement
    )
