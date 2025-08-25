import logging
from functools import partial

import httpx
from fastapi import HTTPException
from sqlmodel import Session
from tenacity import Future, retry, wait_random, stop_after_attempt
from tenacity.wait import wait_base

import settings
from models import User

from services.slack import slack
from utils import humanize_milliseconds
from utils.logs import ratelimited_log

logger = logging.getLogger("lykd.spotify.retry")


def exception_from_response(response: httpx.Response, prefix=None) -> HTTPException:
    """Create an HTTPException from a httpx response"""
    return HTTPException(
        status_code=response.status_code,
        detail=f"{prefix}: {response.text}" if prefix else response.text,
        headers=response.headers,
    )


class wait_retry_after_or_default(wait_base):
    def __init__(self, default_wait):
        self.default_wait = default_wait

    def __call__(self, retry_state):
        ex = retry_state.outcome.exception()
        if isinstance(ex, HTTPException):
            retry_after = getattr(ex, "headers", {}).get("Retry-After")
            if retry_after is not None:
                try:
                    wait_seconds = max(0, int(retry_after))
                    ratelimited_log(60 * 60)(
                        slack.send_message, "⚠️ Rate-limited by Spotify"
                    )
                    logger.debug(
                        f"Rate-limited, retry after {humanize_milliseconds(wait_seconds * 1000)} seconds"
                    )
                    return wait_seconds
                except ValueError:
                    pass
        return self.default_wait(retry_state)


async def renew_token_if_expired(retry_state):
    """Renew token if the retry is due to an expired token"""
    if retry_state.outcome.failed:
        exception = retry_state.outcome.exception()
        if isinstance(exception, HTTPException):
            if "user" in retry_state.kwargs:
                user: User = retry_state.kwargs[
                    "user"
                ]  # we need a user to renew the token
                db_session: Session = retry_state.kwargs.get("db_session")
                spotify = (
                    retry_state.args[0]
                    if retry_state.args
                    else retry_state.kwargs.get("spotify")
                )
                if (
                    exception.status_code == 401
                    and "access token expired" in exception.detail
                    and spotify is not None
                ):
                    updated_tokens = await spotify.refresh_token(user=user)
                    user.tokens = {
                        **(user.tokens or {}),
                        **updated_tokens,
                    }

                    if db_session:
                        logger.debug(f"Refreshed the user {user} tokens")
                        db_session.add(user)
                        db_session.commit()
                    return  # token refreshed - let's retry
                elif (
                    exception.status_code == 400
                    and "Refresh token revoked" in exception.detail
                ):
                    logger.warning(f"User {user} is gone, marking as inactive")
                    slack.send_message(f"🛑User is gone: {user}. Marking as inactive.")
                    user.tokens = None
                    if db_session:
                        logger.debug(f"Refreshed the user {user} tokens")
                        db_session.add(user)
                        db_session.commit()
                    fut = Future(attempt_number=retry_state.attempt_number)
                    fut.set_result(None)
                    retry_state.outcome = fut  # replace the finished future
                    raise exception
            if 400 <= exception.status_code < 500 and exception.status_code != 429:
                # don't retry on 4xx errors but 429
                raise exception


def before_sleep_log_concise(logger, log_level):
    def log_it(retry_state):
        wait = retry_state.next_action.sleep if retry_state.next_action else None
        if wait is not None:  # wait is in seconds
            wait_str = humanize_milliseconds(wait * 1000)
        else:
            wait_str = "unknown time"
        fn_name = retry_state.fn.__qualname__
        exception = retry_state.outcome.exception() if retry_state.outcome else None
        if exception:
            # Try to extract status code, method, and URL if present
            status_code = getattr(exception, "status_code", None)
            detail = getattr(exception, "detail", "")
            method = None
            url = None
            # Try to parse method and URL from detail string
            if detail:
                import re

                match = re.search(
                    r"(GET|POST|PUT|DELETE|PATCH) (https?://[^ ]+)", detail
                )
                if match:
                    method, url = match.group(1), match.group(2)
            exc_type = type(exception).__name__
            msg = f"Retrying {fn_name} in {wait_str} as it raised {exc_type}:"
            if status_code:
                msg += f" {status_code}:"
            if method and url:
                msg += f" {method} {url} failed"
            else:
                msg += f" {str(exception)}"
        else:
            msg = f"Retrying {fn_name} in {wait_str}"
        logger.log(log_level, msg)

    return log_it


spotify_retry = partial(
    retry,
    before_sleep=before_sleep_log_concise(logger, logging.DEBUG),
    wait=wait_retry_after_or_default(
        default_wait=wait_random(0, 0 if settings.TESTING_MODE else 0.5)
    ),
    stop=stop_after_attempt(2),
    reraise=True,
    after=renew_token_if_expired,
)
