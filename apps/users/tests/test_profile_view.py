"""
DEPRECATED: This file is superseded by test_me_view.py.

The /profile/ endpoint was renamed to /me/ in Phase 1 per spec §9.
URL name changed from 'profile' to 'me'.

All profile-endpoint tests now live in test_me_view.py. This file is kept
as a thin redirect shim so any external tooling that imports it doesn't
hard-fail, but it contains no test cases.
"""
