from functools import partial

import httpx

from models import User
from services.spotify import Spotify, get_spotify_client


def test_spotify_playback_refresh_on_401(
    client, test_user, test_app, httpx_mock, test_session
):
    playback_url = "/spotify/playback"
    playback_state = {"is_playing": True, "item": {"name": "Test Song"}}
    assert (
        test_session.get(User, test_user.id).get_access_token() == "test_access_token"
    )

    def playback_callback(request, response):
        auth = request.headers.get("Authorization", "")
        if auth == "Bearer test_access_token":
            return httpx.Response(
                status_code=401,
                request=request,
                json={"error": {"status": 401, "message": "access token expired"}},
            )
        elif auth == "Bearer new_token":
            return httpx.Response(
                status_code=200,
                request=request,
                json=response,
            )
        return httpx.Response(
            status_code=403,
            request=request,
            json={"error": {"status": 403, "message": "Forbidden"}},
        )

    httpx_mock.add_callback(
        partial(
            playback_callback,
            response=playback_state,
        ),
        method="GET",
        url="https://api.spotify.com/v1/me/player",
        is_reusable=True,
    )
    httpx_mock.add_response(
        method="POST",
        url="https://accounts.spotify.com/api/token",
        status_code=200,
        json={
            "access_token": "new_token",
            "token_type": "Bearer",
            "expires_in": 3600,
        },
    )

    # Dependency overrides for test user and Spotify client
    from routes.deps import current_user

    test_app.dependency_overrides[current_user] = lambda: test_user
    test_app.dependency_overrides[get_spotify_client] = lambda: Spotify()

    response = client.get(playback_url)
    assert response.status_code == 200
    assert response.json()["state"] == playback_state

    assert test_session.get(User, test_user.id).get_access_token() == "new_token"

    # Clean up dependency overrides
    del test_app.dependency_overrides[current_user]
    del test_app.dependency_overrides[get_spotify_client]
