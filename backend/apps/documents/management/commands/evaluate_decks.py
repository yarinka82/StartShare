
"""Оценка качества на размеченных синтетических деках.

    python manage.py evaluate_decks testdecks --runs 3
В папке должны лежать PDF и ground_truth.json. Для каждого дека считает по всем прогонам:
  утечки      запрещённые строки (названия, имена, точные цифры) в тексте тизера (должно быть 0)
  выдумки     поля, которые по разметке должны быть пустыми, но заполнены
  покрытие    доля ожидаемых категорий риска, найденных в risk_phrases
  попытки     среднее число вызовов ШІ на прогон
Только синтетические деки, пока TEASER_LLM_PROVIDER = gemini_free.
"""
import json
import os
import re
import time
from collections import Counter

from django.core.management.base import BaseCommand, CommandError

from apps.documents.pdf_extract import DeckExtractionError, extract_deck
from apps.documents.teaser.leak_check import company_terms
from apps.documents.teaser.llm import LLMError, get_client
from apps.documents.teaser.pipeline import PipelineError, run_pipeline


def find_forbidden(text: str, forbidden: list[str]) -> list[str]:
    return [w for w in forbidden
            if re.search(rf"(?<!\w){re.escape(w)}(?!\w)", text, re.IGNORECASE)]


class Command(BaseCommand):
    help = "Прогнать размеченные деки через пайплайн и посчитать утечки, выдумки и покрытие."

    def add_arguments(self, parser):
        parser.add_argument("dir")
        parser.add_argument("--runs", type=int, default=3)
        parser.add_argument("--pause", type=float, default=12.0, help="пауза между вызовами (лимиты бесплатного тарифа)")
        parser.add_argument("--only", default="", help="часть имени файла")

    def handle(self, *args, **opts):
        gt_path = os.path.join(opts["dir"], "ground_truth.json")
        try:
            with open(gt_path, encoding="utf-8") as f:
                truth = json.load(f)
            client = get_client()
        except FileNotFoundError:
            raise CommandError(f"Нет файла {gt_path}")
        except LLMError as exc:
            raise CommandError(f"Провайдер ШІ недоступен: {exc}")

        out = self.stdout.write
        total_leaks = 0
        rows = []
        for name, spec in truth.items():
            if opts["only"] and opts["only"] not in name:
                continue
            path = os.path.join(opts["dir"], name)
            stats = {"ok": 0, "err": 0, "leaks": [], "fab": [], "recall": [], "attempts": [], "blanked": 0,
                     "errors": []}
            for i in range(opts["runs"]):
                if i or rows:
                    time.sleep(opts["pause"])
                try:
                    with open(path, "rb") as f:
                        content = extract_deck(f)
                    r = run_pipeline(content, {"sector": "", "stage": ""}, company_terms(spec.get("company", "")),
                                     client, max_retries=2)
                except (PipelineError, DeckExtractionError) as exc:
                    code = getattr(exc, "code", str(exc))
                    stats["errors"].append(str(exc))   # с причиной: "llm_error: Gemini API error 429 ..."
                    if code == spec.get("expect_error"):
                        stats["ok"] += 1
                    else:
                        stats["err"] += 1
                    continue
                except FileNotFoundError:
                    raise CommandError(f"Файл не найден: {path}")
                if spec.get("expect_error"):
                    stats["err"] += 1
                    stats["errors"].append("expected " + spec["expect_error"] + ", got a draft")
                    continue
                stats["ok"] += 1
                teaser = r.draft["teaser"]
                text = "\n".join(teaser.values())
                stats["leaks"] += find_forbidden(text, spec.get("forbidden", []))
                stats["fab"] += [f for f in spec.get("expected_empty", []) if teaser.get(f, "").strip()]
                expected = set(spec.get("expected_categories", []))
                if expected:
                    found = {p["category_id"] for p in r.risk_phrases}
                    stats["recall"].append(len(expected & found) / len(expected))
                stats["attempts"].append(r.attempts)
                stats["blanked"] += len(r.draft["review"]["blanked_fields"])
            total_leaks += len(stats["leaks"])
            rows.append((name, stats))

        out(f"\n{'дек':<22}{'ok/err':<9}{'утечки':<8}{'выдумки':<9}{'покрытие':<10}{'попытки':<9}очищено")
        for name, s in rows:
            rec = f"{100 * sum(s['recall']) / len(s['recall']):.0f}%" if s["recall"] else "-"
            att = f"{sum(s['attempts']) / len(s['attempts']):.1f}" if s["attempts"] else "-"
            out(f"{name:<22}{str(s['ok']) + '/' + str(s['err']):<9}{len(s['leaks']):<8}{len(s['fab']):<9}{rec:<10}{att:<9}{s['blanked']}")
        for name, s in rows:
            if s["leaks"]:
                out(f"\nУТЕЧКА в {name}: {sorted(set(s['leaks']))}")
            if s["fab"]:
                out(f"ВЫДУМКА в {name}: поля {sorted(set(s['fab']))} должны быть пустыми")
            if s["err"]:
                for msg, n in Counter(s["errors"]).items():
                    out(f"ОШИБКА в {name} (x{n}): {msg}")
        total_err = sum(s["err"] for _, s in rows)
        total_runs = sum(s["ok"] + s["err"] for _, s in rows)
        if total_leaks:
            raise CommandError(f"Найдено утечек: {total_leaks}. Тизер раскрывает данные, которых там быть не должно.")
        if total_err:
            raise CommandError(
                f"ПРОВЕРКА НЕПОЛНАЯ: {total_err} из {total_runs} прогонов завершились ошибкой. "
                "Утечек в успешных прогонах нет, но остальные не проверены. Причины выше.")
        out("\nВсе прогоны завершились. Утечек нет.")