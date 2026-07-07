from conf.settings import *  # noqa

# Never attempt real FCM delivery in tests (feed rows are still written).
PUSH_NOTIFICATIONS_ENABLED = False  # noqa

# Run Celery tasks synchronously in-process — .delay() must never reach a broker
# during tests, and task failures should surface as test failures.
CELERY_TASK_ALWAYS_EAGER = True  # noqa
CELERY_TASK_EAGER_PROPAGATES = True  # noqa

# Use local memory cache so throttles don't persist across test runs
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# Match production middleware ordering — insert at position 0
MIDDLEWARE.insert(0, "conf.test_utils.RequestIDMiddleware")  # noqa

# Use mock filter that provides all JSON formatter fields
LOGGING["filters"]["request_id"]["()"] = "conf.test_utils.RequestIDFilter"  # noqa
LOGGING["loggers"]["apps"]["level"] = "DEBUG"  # noqa

# Relax throttling for tests
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["user_login"] = "1000/minute"  # noqa
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["user"] = "1000/minute"  # noqa
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["anon"] = "1000/minute"  # noqa
