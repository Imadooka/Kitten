from datetime import timedelta
from collections import defaultdict

from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models.functions import Lower

from index.models import Ingredient  # แก้ให้ตรงชื่อแอปของคุณ

def expiry_of(obj):
    # expiry = prepared_date + shelf_life_days (property เดิมของโมเดลก็คิดแบบนี้)
    return obj.prepared_date + timedelta(days=obj.shelf_life_days)

class Command(BaseCommand):
    help = "รวมวัตถุดิบย้อนหลังตามชื่อ (case-insensitive) ให้เหลือรายการเดียว/ชื่อ"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="แสดงผลที่จะเปลี่ยนแปลงโดยไม่เขียนจริง",
        )
        parser.add_argument(
            "--case-sensitive",
            action="store_true",
            help="จับคู่ชื่อแบบแยกตัวพิมพ์ (ปกติ: ไม่แยก)",
        )

    def handle(self, *args, **opts):
        dry_run = opts["dry_run"]
        case_sensitive = opts["case_sensitive"]

        qs = Ingredient.objects.select_related("image").all()
        groups = defaultdict(list)

        for obj in qs:
            key = (obj.name or "").strip()
            if not case_sensitive:
                key = key.lower()
            groups[key].append(obj)

        total_groups = len(groups)
        merged_groups = 0
        changed = []

        for key, items in groups.items():
            if not key or len(items) <= 1:
                continue  # ไม่มีซ้ำ

            # รวมข้อมูลของกลุ่มนี้
            items = sorted(items, key=lambda x: x.created_at)  # เก่าสุดก่อน
            anchor = items[0]                                  # รายการหลัก
            others = items[1:]

            total_qty = sum(i.quantity for i in items)
            min_prepared = min(i.prepared_date for i in items)
            min_expiry = min(expiry_of(i) for i in items)
            new_shelf = max(0, (min_expiry - min_prepared).days)

            # เลือกรูปที่ "ไฟล์อยู่จริง"
            best_image = None
            for i in items:
                img_field = getattr(getattr(i, "image", None), "image", None)
                if img_field and getattr(img_field, "name", "") and default_storage.exists(img_field.name):
                    best_image = i.image
                    break

            # รายงานสิ่งที่จะปรับ
            changed.append({
                "name": anchor.name,
                "keep_id": anchor.id,
                "delete_ids": [o.id for o in others],
                "from_qty": [i.quantity for i in items],
                "to_qty": total_qty,
                "prepared": str(min_prepared),
                "expiry": str(min_expiry),
            })

            if dry_run:
                continue

            with transaction.atomic():
                # อัปเดตรายการหลัก
                anchor.quantity = total_qty
                anchor.prepared_date = min_prepared
                anchor.shelf_life_days = new_shelf
                if best_image:
                    anchor.image = best_image
                anchor.save()

                # ลบรายการที่เหลือ
                Ingredient.objects.filter(id__in=[o.id for o in others]).delete()

            merged_groups += 1

        # สรุปผล
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN: ยังไม่ได้เขียนข้อมูลจริง"))
        self.stdout.write(f"พบกลุ่มทั้งหมด: {total_groups}")
        self.stdout.write(f"รวมจริง: {merged_groups if not dry_run else '(ดูผลอย่างเดียว)'}")
        for row in changed:
            self.stdout.write(
                f"- '{row['name']}' keep #{row['keep_id']} "
                f"delete {row['delete_ids']} | qty {row['from_qty']} -> {row['to_qty']} | "
                f"prepared={row['prepared']} expiry={row['expiry']}"
            )
