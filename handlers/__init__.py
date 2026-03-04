from aiogram import Router

from .start import router as start_router
from .help import router as help_router
from .admin import router as admin_router
from .feedback import router as feedback_router
from .text import router as text_router
from .profile import router as profile_router
from .about_us import router as about_us_router
from .earn import router as earn_router
from .buy import router as buy_router
from .subs import router as subs_router
from .payment import router as payment_router
from .stats import router as stats_router

router = Router()
router.include_router(start_router)
router.include_router(help_router)
router.include_router(admin_router)
router.include_router(feedback_router)
router.include_router(text_router)
router.include_router(profile_router)
router.include_router(about_us_router)
router.include_router(earn_router)
router.include_router(buy_router)
router.include_router(subs_router)
router.include_router(payment_router)
router.include_router(stats_router)