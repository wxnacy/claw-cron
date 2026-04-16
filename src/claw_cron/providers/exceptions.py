# SPDX-FileCopyrightText: 2026-present wxnacy <371032668@qq.com>
#
# SPDX-License-Identifier: MIT

"""Exception hierarchy for AI provider errors."""


class ProviderError(Exception):
    """Base exception for all provider-related errors.

    This is the parent class for all provider-specific exceptions.
    Catch this to handle any provider error generically.
    """

    def __init__(self, message: str, provider: str | None = None) -> None:
        self.provider = provider
        super().__init__(message)


class ProviderAuthError(ProviderError):
    """Authentication failure (invalid API key or unauthorized access).

    Raised when:
        - API key is invalid, expired, or revoked
        - Account lacks permissions for the requested resource
        - Authentication token is malformed
    """

    pass


class ProviderRateLimitError(ProviderError):
    """Rate limit exceeded.

    Raised when:
        - Too many requests in a time window
        - Token quota exceeded
        - Concurrent request limit reached

    The provider may include retry-after information.
    """

    def __init__(
        self, message: str, provider: str | None = None, retry_after: float | None = None
    ) -> None:
        self.retry_after = retry_after
        super().__init__(message, provider)


class ProviderModelNotFoundError(ProviderError):
    """Requested model is not available.

    Raised when:
        - Model name is misspelled or doesn't exist
        - Model has been deprecated or removed
        - Model is not available in the current region/tier
    """

    pass


class ProviderResponseError(ProviderError):
    """Malformed or unexpected response from provider.

    Raised when:
        - Response JSON is invalid or missing required fields
        - Response format doesn't match expected schema
        - Provider returned an error that couldn't be categorized
    """

    def __init__(
        self, message: str, provider: str | None = None, raw_response: object | None = None
    ) -> None:
        self.raw_response = raw_response
        super().__init__(message, provider)
