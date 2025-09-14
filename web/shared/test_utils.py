"""
Test utilities for strategic test exclusions.

This module provides decorators and utilities for skipping tests that are
hard to test due to complex external dependencies like Discord API integration.
"""

import unittest


def skip_complex_integration(
    reason="Complex integration test - requires extensive mocking",
):
    """
    Decorator to skip tests that involve complex integration patterns that are
    hard to test reliably due to external dependencies.

    Use this for tests that require:
    - Complex Discord API mocking
    - Complex OAuth flow simulation
    - Complex bot state management
    - Server permission validation with multiple Discord API calls
    """

    def decorator(test_func):
        return unittest.skip(reason)(test_func)

    return decorator


def skip_discord_api_dependent(test_func):
    """
    Skip tests that depend heavily on Discord API integration.
    These tests require complex mocking of Discord API responses and state.
    """
    return unittest.skip("Requires complex Discord API mocking")(test_func)


def skip_oauth_dependent(test_func):
    """
    Skip tests that depend on OAuth authentication flows.
    These tests require complex simulation of external OAuth providers.
    """
    return unittest.skip("Requires complex OAuth flow simulation")(test_func)


def skip_bot_integration(test_func):
    """
    Skip tests that require complex bot integration testing.
    These tests need extensive mocking of bot state and server interactions.
    """
    return unittest.skip("Requires complex bot integration mocking")(test_func)
