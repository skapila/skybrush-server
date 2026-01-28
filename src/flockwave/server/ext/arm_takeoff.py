from __future__ import annotations

import random
from inspect import isawaitable
from typing import Any, Dict, List, Optional, Tuple

import trio
from flockwave.server.model.uav import UAV

description = "BotLab custom ops (inbuilt arm + custom takeoff via X-* messages)"
schema = {}
exports = {}
dependencies = ("mavlink",)  # we rely on the mavlink extension API


# -----------------------------
# Helpers
# -----------------------------

async def _await_driver_result(uav: UAV, results: dict) -> Any:
    """
    Driver methods typically return a dict[uav] -> awaitable/exception/value.
    This helper normalizes that.
    """
    r = results.get(uav)
    if isawaitable(r):
        return await r
    if isinstance(r, Exception):
        raise r
    return r


async def _set_guided_if_possible(uav: UAV, log) -> None:
    """
    Many MAVLink stacks require GUIDED/AUTO/OFFBOARD for takeoff commands.
    If the UAV supports set_mode, try GUIDED.
    """
    if hasattr(uav, "set_mode"):
        try:
            await uav.set_mode("guided")
            await trio.sleep(1.5)
        except Exception as e:
            # Not fatal; some setups may already be in a compatible mode
            log.warning(f"{uav.id}: set_mode('guided') failed: {e}")


async def _arm(uav: UAV, log, force: bool = True) -> None:
    """
    For SITL/testing, force=True can help.
    In real ops, you typically want force=False and fix pre-arm checks.
    """
    results = uav.driver.send_motor_start_stop_signal([uav], start=True, force=force)
    await _await_driver_result(uav, results)
    await trio.sleep(2.0)


async def _takeoff(uav: UAV, alt_m: float) -> None:
    """
    Prefer high-level takeoff method if available, else fall back to driver signal.
    """
    if hasattr(uav, "takeoff_to_relative_altitude"):
        await uav.takeoff_to_relative_altitude(alt_m)
        return

    results = uav.driver.send_takeoff_signal([uav])
    await _await_driver_result(uav, results)


def _collect_targets(app ) -> List[UAV]:
    """
    Collect connected UAV objects.
    """
    uav_ids = list(app.object_registry.ids_by_type(UAV))
    uavs: List[UAV] = []
    for uid in uav_ids:
        u = app.find_uav_by_id(uid)
        if u is None:
            continue
        # if UAV has connectivity property, respect it
        if hasattr(u, "is_connected") and not u.is_connected:
            continue
        uavs.append(u)
    return uavs


# -----------------------------
# Core operation
# -----------------------------
async def _arm_and_takeoff(
    uavs: List[UAV],
    alt_m: float,
    log,
) -> Dict[str, Any]:
    """
    Arms + takeoff each UAV concurrently and returns per-UAV results.
    """
    results: Dict[str, Any] = {}
    lock = trio.Lock()
    log.warn(f"Core Command in Loop")
    async def _one(uav: UAV):
        # jitter to reduce network burst
        await trio.sleep(random.random() * 1.5)

        try:
            await _set_guided_if_possible(uav, log)
            log.debug(f"Guided Command Send")
            # await _arm(uav, log, force=True)
            # await _takeoff(uav, alt_m)

            # async with lock:
            #     results[uav.id] = {"ok": True, "stage": "takeoff_sent"}

        except Exception as e:
            async with lock:
                results[uav.id] = {"ok": False, "error": str(e), "stage": "failed"}

    async with trio.open_nursery() as nursery:
        for u in uavs:
            nursery.start_soon(_one, u)

    return results


# -----------------------------
# Message handler (thin)
# -----------------------------
async def handle_X_BOTLAB_ARM_TAKEOFF(message, sender,hub,app,logger):
    """
    Incoming body (example):
    {
      "type": "X-BOTLAB-ARM-TAKEOFF",
      "alt": 10,
      "network": "default"   # optional (kept for future use)
    }
    """
    
    body = message.body or {}
    alt = body.get("alt", None)

    try:
        alt_m = float(alt)
    except Exception:
        return hub.create_response_or_notification(
            body={"ok": False, "error": "alt must be a number"},
            in_response_to=message,
        )

    if alt_m <= 0 or alt_m > 200:
        return hub.create_response_or_notification(
            body={"ok": False, "error": "alt out of allowed range (0..200m)"},
            in_response_to=message,
        )

    # If you later want to target a specific mavlink network, you can use:
    # mavlink = app.import_api("mavlink"); network = mavlink.find_network_by_id(network_id)
    # and fetch UAVs from that network. For now we select from object_registry (works in your setup).

    targets = _collect_targets(app)
    # if not targets:
    #     return hub.create_response_or_notification(
    #         body={"ok": False, "error": f"no {group} UAVs online"},
    #         in_response_to=message,
    #     )

    per_uav = await _arm_and_takeoff(targets, alt_m, logger)

    return hub.create_response_or_notification(
        body={
            "ok": True,
            "type": "X-BOTLAB-ARM-TAKEOFF",
            "alt": alt_m,
            "count": len(targets),
            "targets": [u.id for u in targets],
            "results": per_uav,
        },
        in_response_to=message,
    )


# -----------------------------
# Extension entrypoint
# -----------------------------
async def run(app, configuration, logger):
    logger.info("Arm Takeoff extension loaded")

    async def _handle(message, sender, hub):
        return await handle_X_BOTLAB_ARM_TAKEOFF(message, sender, hub, app, logger)

    handlers = {
        "X-BOTLAB-ARM-TAKEOFF": _handle
    }

    with app.message_hub.use_message_handlers(handlers):
        await trio.sleep_forever()