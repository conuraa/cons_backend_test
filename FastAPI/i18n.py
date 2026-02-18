from __future__ import annotations
from typing import Optional, Tuple


def should_send_auto_message(lang: Optional[str]) -> bool:
    if not lang:
        return False
    return lang.strip().lower() == "uz"


def format_consultation_accepted_message(
    *,
    lang: Optional[str],
    number: Optional[str] = None,
    scheduled_date: Optional[str] = None,
    queue_position: Optional[int] = None,
    wait_hours: Optional[float] = None,
    show_wait_time: bool = True,
) -> Optional[str]:
    if not should_send_auto_message(lang):
        return None
    parts = ["Sizning konsultatsiya uchun arizangiz qabul qilindi."]
    if number:
        parts.append(f"Ariza raqami: {number}.")
    if scheduled_date:
        parts.append(f"Rejalashtirilgan sana: {scheduled_date}.")
    if queue_position is not None:
        parts.append(f"Navbatdagi o'rningiz: {queue_position}.")
    if show_wait_time and wait_hours is not None:
        hours = int(wait_hours)
        if hours > 0:
            parts.append(f"Taxminiy kutish vaqti: {hours} soat.")
    return " ".join(parts)


def format_cancellation_message(lang: Optional[str]) -> Optional[str]:
    if not should_send_auto_message(lang):
        return None
    return "Sizning konsultatsiya arizangiz bekor qilindi. Agar savollaringiz bo'lsa, iltimos, qayta murojaat qiling."


def format_telegram_close_message(
    *,
    lang: Optional[str],
    number: Optional[str] = None,
    status: Optional[str] = None,
) -> Tuple[str, str, dict]:
    close_message = f"Konsultatsiya #{number or chr(8212)} yakunlandi. Xizmatimiz sifatini baholashingizni so'raymiz."
    rating_message = "Iltimos, xizmat sifatini 1 dan 5 gacha baholang:"
    button_texts = {"rate": "Baholash", "skip": "Keyinroq"}
    return close_message, rating_message, button_texts
