from __future__ import annotations

from skyadmin_pro.services.tracking import days_until, effective_expiry_date
from skyadmin_pro.ui.theme import TIMELINE_CAUTION, TIMELINE_CRITICAL, TIMELINE_OK, TIMELINE_WARNING


class DashboardViewMixin15:
    def _DashboardView_draw_timeline_p1(self, canvas, snap, width, text_color):
        height = int(canvas.cget("height"))

        if snap is not None:
            expiring = snap.get("expiring", [])
            supplier_expiring = snap.get("supplier_expiring", [])
        elif self._last_snap is not None:
            expiring = self._last_snap.get("expiring", [])
            supplier_expiring = self._last_snap.get("supplier_expiring", [])
        else:
            expiring = self.app.db.list_expiring_documents()
            supplier_expiring = self.app.db.list_expiring_supplier_services()
        # Bucket by days-left
        buckets = {}
        for item in expiring:
            eff = effective_expiry_date(item.get("expiry_date"), item.get("document_type"))
            left = days_until(eff)
            if left is not None and 0 <= left <= 45:
                buckets[left] = buckets.get(left, 0) + 1
        for item in supplier_expiring:
            left = days_until(item.get("expiry_date"))
            if left is not None and 0 <= left <= 45:
                buckets[left] = buckets.get(left, 0) + 1

        max_count = max(buckets.values()) if buckets else 1
        bar_w = max(4, (width - 40) // 45)
        x0 = 20
        baseline = height - 24

        # Day labels
        for day in range(0, 46, 15):
            x = x0 + day * bar_w
            canvas.create_text(x, height - 8, text=f"d{day}", fill=text_color, font=("Segoe UI", 8))

        # Bars
        colors = {0: TIMELINE_CRITICAL, 1: TIMELINE_WARNING, 2: TIMELINE_CAUTION}
        return bar_w, baseline, buckets, colors, height, max_count, x0

    def _DashboardView_draw_timeline_p2(
        self, bar_w, baseline, buckets, canvas, colors, height, max_count, value_color, x0, width, text_color, mode
    ):
        for day in sorted(buckets):
            count = buckets[day]
            bh = max(3, int((count / max_count) * (height - 40)))
            color = colors.get(min(day // 7, 2), TIMELINE_OK) if day <= 14 else TIMELINE_OK
            if day <= 7:
                color = TIMELINE_CRITICAL
            elif day <= 14:
                color = TIMELINE_WARNING
            elif day <= 30:
                color = TIMELINE_CAUTION
            x = x0 + day * bar_w
            canvas.create_rectangle(
                x - bar_w // 2,
                baseline - bh,
                x + bar_w // 2,
                baseline,
                fill=color,
                outline="",
                tags=f"bar_{day}",
            )
            if count > 1:
                canvas.create_text(
                    x,
                    baseline - bh - 10,
                    text=str(count),
                    fill=value_color,
                    font=("Segoe UI", 8),
                )
        # Legend
        lx = width - 180
        for txt, col in [
            ("≤7d", TIMELINE_CRITICAL),
            ("≤14d", TIMELINE_WARNING),
            ("≤30d", TIMELINE_CAUTION),
            ("31-45d", TIMELINE_OK),
        ]:
            canvas.create_rectangle(lx, 6, lx + 8, 14, fill=col, outline="")
            canvas.create_text(lx + 12, 10, text=txt, anchor="w", fill=text_color, font=("Segoe UI", 8))
            lx += 45
        self._timeline_mode = mode
