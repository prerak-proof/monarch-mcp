"""Tests for update_account_balance.

Uses the ``mock_api`` fixture (see conftest.py) so tests are offline: it patches
``ensure_authenticated`` and ``api_call_with_retry``.
"""

from typing import Any
from unittest.mock import AsyncMock

import pytest

import server


def _update_response(balance: float, errors: Any = None) -> dict[str, Any]:
    """Shape returned by the library's update_account."""
    return {
        "updateAccount": {
            "errors": errors,
            "account": {
                "id": "acc_1",
                "displayName": "Citadel",
                "currentBalance": balance,
                "displayBalance": balance,
            },
        }
    }


class TestUpdateAccountBalance:
    @pytest.mark.asyncio
    async def test_sets_balance_and_returns_confirmed_values(self, mock_api: AsyncMock) -> None:
        mock_api.return_value = _update_response(1012878.68)
        result = await server.update_account_balance(account_id="acc_1", balance=1012878.68)
        assert result.account_id == "acc_1"
        assert result.account_name == "Citadel"
        assert result.balance == 1012878.68
        mock_api.assert_awaited_once_with("update_account", account_id="acc_1", account_balance=1012878.68)

    @pytest.mark.asyncio
    async def test_payload_errors_raise(self, mock_api: AsyncMock) -> None:
        mock_api.return_value = _update_response(0.0, errors={"message": "Account is not manual", "code": "INVALID"})
        with pytest.raises(ValueError, match="Monarch rejected the balance update"):
            await server.update_account_balance(account_id="acc_1", balance=1.0)
