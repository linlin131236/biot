"""Strict, sanitized Runtime control-plane HTTP API."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from bolt_core.runtime_control_plane import (
    RuntimeControlPlaneError,
    RuntimeNotFoundError,
    RuntimeUnavailableError,
)


class _RuntimeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class StartRuntimeRequest(_RuntimeRequest):
    task: str = Field(min_length=1, max_length=8192)
    mode: Literal["read_only"] = "read_only"


class EmptyRuntimeRequest(_RuntimeRequest):
    pass


def create_runtime_router(control_plane) -> APIRouter:
    router = APIRouter(prefix="/runtime", tags=["runtime"])

    @router.get("")
    def list_runtimes() -> dict:
        return {"runtimes": control_plane.list_runtimes()}

    @router.post("/hermes/install/verify")
    def verify_hermes_installation(
        _payload: EmptyRuntimeRequest = Body(default_factory=EmptyRuntimeRequest),
    ) -> dict:
        return control_plane.verify_hermes_installation()

    @router.post("/hermes/install")
    def install_hermes(
        _payload: EmptyRuntimeRequest = Body(default_factory=EmptyRuntimeRequest),
    ) -> dict:
        try:
            return control_plane.install_hermes()
        except RuntimeUnavailableError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except RuntimeControlPlaneError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @router.post("/model-profiles/default/test")
    def test_default_model_profile(
        _payload: EmptyRuntimeRequest = Body(default_factory=EmptyRuntimeRequest),
    ) -> dict:
        return control_plane.test_default_profile()

    @router.get("/sessions/{session_id}/status")
    def runtime_session_status(session_id: str) -> dict:
        try:
            return control_plane.session_status(session_id)
        except RuntimeNotFoundError as error:
            raise HTTPException(status_code=404, detail="runtime_session_not_found") from error

    @router.post("/sessions/{session_id}/stop")
    def stop_runtime_session(
        session_id: str,
        _payload: EmptyRuntimeRequest = Body(default_factory=EmptyRuntimeRequest),
    ) -> dict:
        try:
            return control_plane.stop(session_id)
        except RuntimeNotFoundError as error:
            raise HTTPException(status_code=404, detail="runtime_session_not_found") from error
        except RuntimeControlPlaneError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @router.get("/{runtime_id}/status")
    def runtime_status(runtime_id: str) -> dict:
        try:
            return control_plane.runtime_status(runtime_id)
        except RuntimeNotFoundError as error:
            raise HTTPException(status_code=404, detail="runtime_not_found") from error

    @router.get("/{runtime_id}/capabilities")
    def runtime_capabilities(runtime_id: str) -> dict:
        try:
            return control_plane.capabilities(runtime_id)
        except RuntimeNotFoundError as error:
            raise HTTPException(status_code=404, detail="runtime_not_found") from error

    @router.post("/{runtime_id}/sessions", status_code=201)
    def start_runtime_session(runtime_id: str, payload: StartRuntimeRequest) -> dict:
        try:
            return control_plane.start(runtime_id, payload.task, payload.mode)
        except RuntimeNotFoundError as error:
            raise HTTPException(status_code=404, detail="runtime_not_found") from error
        except RuntimeUnavailableError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except RuntimeControlPlaneError as error:
            raise HTTPException(status_code=409, detail="runtime_start_failed") from error

    return router
