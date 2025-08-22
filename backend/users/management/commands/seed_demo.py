from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from datetime import timedelta
from django.apps import apps
from django.db import models as dj_models
from decimal import Decimal

def pick_model(name):
    # Prefer users.<Model>, else fallback to cinema.<Model>
    for label in ("users", "cinema"):
        try:
            return apps.get_model(label, name)
        except LookupError:
            continue
    return None

def fields_map(model):
    return {
        f.name: f
        for f in model._meta.get_fields()
        if getattr(f, "concrete", False) and not getattr(f, "auto_created", False)
    }

def first_existing(candidates, fmap):
    for c in candidates:
        if c in fmap:
            return c
    return None

def safe_char(value: str, f: dj_models.Field, fallback="X"):
    s = (value or fallback)
    maxlen = getattr(f, "max_length", None)
    if maxlen:
        return s[:maxlen]
    return s

class Command(BaseCommand):
    help = "Seed 1 screen (10x10 seats), 2 movies, 2 shows. Auto-detects fields & sets small safe defaults."

    def handle(self, *args, **kwargs):
        Screen = pick_model("Screen")
        Seat   = pick_model("Seat")
        Movie  = pick_model("Movie")
        Show   = pick_model("Show")

        missing = [n for n, m in {"Screen":Screen, "Seat":Seat, "Movie":Movie, "Show":Show}.items() if m is None]
        if missing:
            raise CommandError(f"Required models not found: {missing}")

        # ---------- Screen ----------
        s_fields = fields_map(Screen)
        screen_params = {}

        if "name" in s_fields:
            screen_params["name"] = "Screen 1"

        rows_key = first_existing(["rows","row_count","total_rows","num_rows","n_rows"], s_fields)
        cols_key = first_existing(["cols","columns","col_count","column_count","total_cols","num_cols","n_cols"], s_fields)
        if rows_key:
            screen_params[rows_key] = 10
        if cols_key:
            screen_params[cols_key] = 10

        # Required FK on Screen?
        for fname, f in s_fields.items():
            if isinstance(f, dj_models.ForeignKey) and not f.null and fname not in screen_params:
                rel = f.related_model
                rel_fields = fields_map(rel)
                rel_kwargs = {}
                rel_name_key = first_existing(["name","title","label"], rel_fields)
                if rel_name_key:
                    rel_kwargs[rel_name_key] = f"Default {rel.__name__}"
                rel_obj, _ = rel.objects.get_or_create(**rel_kwargs)
                screen_params[fname] = rel_obj

        screen, _ = Screen.objects.get_or_create(**screen_params)

        # ---------- Seat ----------
        seat_fields = fields_map(Seat)

        # FK to Screen
        seat_fk_name = None
        for fname, f in seat_fields.items():
            if isinstance(f, dj_models.ForeignKey) and f.related_model == Screen:
                seat_fk_name = fname
                break
        if not seat_fk_name:
            seat_fk_name = "screen"

        # Row/Col fields
        seat_row_key = first_existing(["row","row_number","r","seat_row"], seat_fields) or "row"
        seat_col_key = first_existing(["col","column","col_number","c","seat_col"], seat_fields) or "col"

        exists_qs = Seat.objects.filter(**{seat_fk_name: screen})
        if not exists_qs.exists():
            bulk = []
            for r in range(1, 11):
                for c in range(1, 11):
                    data = {seat_fk_name: screen, seat_row_key: r, seat_col_key: c}
                    # Fill other required NOT NULL fields with small safe defaults
                    for fname, f in seat_fields.items():
                        if fname in data:
                            continue
                        if isinstance(f, dj_models.ForeignKey) and not f.null:
                            rel = f.related_model
                            rel_fields = fields_map(rel)
                            rel_kwargs = {}
                            rname = first_existing(["name","title","label"], rel_fields)
                            if rname:
                                rel_kwargs[rname] = f"Default {rel.__name__}"
                            rel_obj, _ = rel.objects.get_or_create(**rel_kwargs)
                            data[fname] = rel_obj
                        elif not getattr(f, "null", True) and getattr(f, "default", dj_models.fields.NOT_PROVIDED) is dj_models.fields.NOT_PROVIDED:
                            if isinstance(f, dj_models.CharField):
                                data[fname] = safe_char(f"S{r}{c}", f, "S")
                            elif isinstance(f, dj_models.IntegerField):
                                data[fname] = 1
                            elif isinstance(f, dj_models.BooleanField):
                                data[fname] = False
                            elif isinstance(f, dj_models.DateTimeField):
                                data[fname] = timezone.now()
                            elif isinstance(f, dj_models.DecimalField):
                                data[fname] = Decimal("0")
                    bulk.append(Seat(**data))
            Seat.objects.bulk_create(bulk)

        # ---------- Movie ----------
        m_fields = fields_map(Movie)
        title_key = first_existing(["title","name"], m_fields)
        if not title_key:
            raise CommandError("Movie model must have a 'title' or 'name' field.")

        def make_movie(title, desc, dur):
            defaults = {}
            # description-ish
            desc_key = first_existing(["description","summary","synopsis","desc"], m_fields)
            if desc_key:
                defaults[desc_key] = safe_char(desc, m_fields[desc_key], "N/A")
            # duration-ish: only if exists
            dur_key = first_existing(["duration_mins","duration","runtime","length","runtime_mins","duration_min"], m_fields)
            if dur_key:
                f = m_fields[dur_key]
                if isinstance(f, dj_models.IntegerField):
                    defaults[dur_key] = int(dur)
                elif isinstance(f, dj_models.DecimalField):
                    defaults[dur_key] = Decimal(str(dur))
                elif isinstance(f, dj_models.CharField):
                    defaults[dur_key] = safe_char(str(dur), f, "120")

            # handle required NOT NULL others (e.g., rating)
            for fname, f in m_fields.items():
                if fname in (title_key,) or fname in defaults:
                    continue
                if isinstance(f, dj_models.ForeignKey) and not f.null:
                    rel = f.related_model
                    rel_fields = fields_map(rel)
                    rel_kwargs = {}
                    rname = first_existing(["name","title","label"], rel_fields)
                    if rname:
                        rel_kwargs[rname] = f"Default {rel.__name__}"
                    rel_obj, _ = rel.objects.get_or_create(**rel_kwargs)
                    defaults[fname] = rel_obj
                elif not getattr(f, "null", True) and getattr(f, "default", dj_models.fields.NOT_PROVIDED) is dj_models.fields.NOT_PROVIDED:
                    if isinstance(f, dj_models.CharField):
                        # If looks like rating/certification, set tiny code 'U'
                        if any(k in fname.lower() for k in ["rating","certificate","certification","censor"]):
                            defaults[fname] = safe_char("U", f, "U")
                        else:
                            defaults[fname] = safe_char(title, f, "X")
                    elif isinstance(f, dj_models.IntegerField):
                        defaults[fname] = int(dur or 120)
                    elif isinstance(f, dj_models.BooleanField):
                        defaults[fname] = False
                    elif isinstance(f, dj_models.DateTimeField):
                        defaults[fname] = timezone.now()
                    elif isinstance(f, dj_models.DecimalField):
                        defaults[fname] = Decimal("0")

            obj, _ = Movie.objects.get_or_create(**{title_key: title}, defaults=defaults)
            return obj

        m1 = make_movie("Inception", "Dream within a dream.", 148)
        m2 = make_movie("Interstellar", "Time & gravity.", 169)

        # ---------- Show ----------
        sh_fields = fields_map(Show)

        def create_show(movie, hours, price):
            params = {}
            # Movie FK
            mk = None
            for fname, f in sh_fields.items():
                if isinstance(f, dj_models.ForeignKey) and f.related_model == Movie:
                    mk = fname; break
            params[mk or "movie"] = movie
            # Screen FK
            sk = None
            for fname, f in sh_fields.items():
                if isinstance(f, dj_models.ForeignKey) and f.related_model == Screen:
                    sk = fname; break
            params[sk or "screen"] = screen
            # Start time
            start_key = first_existing(["start_time","start","starts_at","show_time","start_datetime"], sh_fields) or "start_time"
            params[start_key] = timezone.now() + timedelta(hours=hours)
            # Price (respect field type)
            price_key = first_existing(["price","cost","amount","ticket_price","fare"], sh_fields) or "price"
            pf = sh_fields.get(price_key, None)
            if isinstance(pf, dj_models.DecimalField):
                params[price_key] = Decimal(str(price))
            elif isinstance(pf, dj_models.IntegerField):
                params[price_key] = int(price)
            elif isinstance(pf, dj_models.FloatField):
                params[price_key] = float(price)
            elif isinstance(pf, dj_models.CharField):
                params[price_key] = safe_char(str(price), pf, "250")
            else:
                params[price_key] = price

            Show.objects.get_or_create(**params)

        create_show(m1, 2, 250)
        create_show(m2, 5, 300)

        # Count seats
        seats_count = Seat.objects.filter(**{seat_fk_name: screen}).count()
        self.stdout.write(self.style.SUCCESS(
            f"Seeded OK → screen={getattr(screen,'name','Screen 1')}, seats={seats_count}, movies=2, shows=2"
        ))
