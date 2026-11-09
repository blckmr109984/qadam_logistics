"""Порядок роутеров важен: меню — раньше сценариев, fallback — последним."""
from aiogram import Router

from handlers import admin, assistant, calculator, fallback, history, menu, shipment, start, tracking


def get_routers() -> list[Router]:
    routers = [
        start.router,
        menu.router,
        admin.router,
        shipment.router,
        calculator.router,
        tracking.router,
        history.router,
        assistant.router,
        fallback.router,
    ]
    # Роутеры — объекты уровня модуля. Отсоединяем их от прежнего диспетчера,
    # чтобы приложение можно было собрать повторно (например, в каждом тесте).
    for router in routers:
        parent = router.parent_router
        if parent is not None:
            parent.sub_routers.remove(router)
            router._parent_router = None
    return routers
