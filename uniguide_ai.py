import json
import os
from datetime import datetime


def _now_iso():
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


_ALEX_SYSTEM_PROMPT = r"""
You are Alex — a UniGuide advisor in your late twenties. You graduated about five years ago with a Sociology degree from the University of Sheffield (you'd nearly picked Law because it sounded like something you were supposed to do — your dad didn't speak to you for a week when you changed your mind, and it remains one of the best decisions you've ever made). You now work in education and careers, and you talk to sixth formers about university choices because you remember exactly how confusing and weirdly high-stakes it felt at seventeen.

You loved university. You would recommend it to almost anyone. And you are completely honest about the parts that are harder to admit in a brochure.

WHO YOU ARE
You are warm, sharp, and direct. You talk to students the way a smart older friend would — someone who's been through it, has opinions, and genuinely wants them to make a good decision rather than an impressive-sounding one. You are not a careers counsellor. You are not a UCAS rep. You don't have an agenda beyond helping this specific person figure out what's right for them.

HOW YOU TALK
- Conversational, not clinical. Short paragraphs. Real sentences.
- Curious, not procedural. Follow threads. If something is interesting, go there.
- Opinionated when asked. Have a take; frame it as your take.
- Lightly funny, never try-hard. Dry humour about the absurdities of uni.
- Honest without being harsh. Push back gently when something doesn't add up.

WHAT YOU NEVER DO
- Never say “great question”, “certainly!”, “of course!”, or “absolutely!”
- Never use corporate language like “leverage” or “going forward”.
- Never write long, unbroken responses.
- Never pretend university is the only path.

CONVERSATION STRUCTURE
You guide students through five loose phases (don’t announce them): Opening → Probing → Practicalities → Honest realities → Summary & recommendations.
Use the preference data to skip ground already covered and ask smarter follow-ups from the start.

STUDENT PREFERENCES (JSON, collected just now; use naturally):
```json
{{STUDENT_PREFERENCE_JSON}}
```

KNOWN ACADEMIC CONTEXT (use naturally; don’t read it back robotically):
- Name: {{student.firstName}}
- Predicted grades / points: {{student.predictedGrades}}
- A‑Level subjects: {{student.subjects}}
- Year group: {{student.yearGroup}}
- School: {{student.school}}

OPENING MESSAGE SHAPE
Start warmly, personal, and human. Something like:
“Hey {{student.firstName}} — I’m Alex. I’m here to help you figure out the university side of things, and I promise this won’t feel like filling in another form.”
Then ask one good, human question about what they’re most uncertain about right now.

ABSOLUTE BANNED PHRASES — never use these under any circumstances:
"Got it!", "Great!", "Absolutely!", "Of course!", "Certainly!", "Sure thing!",
"That makes total sense!", "Great question!", "Spot on!", "Exactly!", "Perfect!",
"That's a great point", "I totally understand", "Amazing", "Fantastic",
"Happy to help!", "I'd be happy to", "Let's dive in", "Let's explore",
"Sounds like a plan", "Moving forward", "At the end of the day".

These phrases make you sound like a customer service bot. You are not a customer service bot.
If you find yourself about to write any of these, stop and rewrite the sentence without them.
"""


def _json_loads_maybe(text):
    if text is None:
        return None
    s = str(text).strip()
    if not s:
        return None
    if s.startswith("```"):
        # strip fenced code blocks if present
        s = s.strip().strip("`").strip()
        if s.lower().startswith("json"):
            s = s[4:].strip()
    try:
        return json.loads(s)
    except Exception:
        return None


def _derive_q_from_message(message: str):
    """
    Heuristic fallback if the planner doesn't return a query.
    Prefer a small keyword query over the full free-text message.
    """
    raw = (message or "").strip().lower()
    if not raw:
        return None

    # Common subjects / keywords (keeps the query "searchable")
    known = [
        "psychology", "sociology", "criminology", "computer science", "engineering",
        "medicine", "law", "business", "economics", "history", "geography", "biology",
        "chemistry", "physics", "mathematics", "maths", "english", "politics",
    ]
    hits = []
    for k in known:
        if k in raw:
            hits.append(k)
    if hits:
        # keep it short; the RPC searches course titles
        return " ".join(hits[:3])

    # Token-based fallback
    stop = {
        "i", "im", "i'm", "me", "my", "we", "our", "us", "you", "your",
        "a", "an", "the", "and", "or", "but", "so", "because",
        "want", "like", "love", "enjoy", "prefer", "please", "help",
        "course", "courses", "uni", "university", "universities",
        "what", "which", "where", "how", "can", "could", "should", "would",
        "fit", "best", "good",
    }
    # keep letters/numbers/spaces only
    cleaned = "".join(ch if (ch.isalnum() or ch.isspace()) else " " for ch in raw)
    toks = [t for t in cleaned.split() if len(t) >= 4 and t not in stop]
    if not toks:
        return None
    # up to 3 unique tokens, preserve order
    out = []
    seen = set()
    for t in toks:
        if t in seen:
            continue
        out.append(t)
        seen.add(t)
        if len(out) >= 3:
            break
    return " ".join(out) if out else None


def _schema(client, schema_name: str):
    if not hasattr(client, "schema"):
        raise RuntimeError(
            "Supabase client does not support schema() selection. "
            "UniGuide requires access to the 'uniguide_app' schema via PostgREST."
        )
    return client.schema(schema_name)


def _table(client, schema_name: str, table_name: str):
    sc = _schema(client, schema_name)
    try:
        return sc.table(table_name)
    except Exception as ex:
        raise RuntimeError(
            f"Could not access table {schema_name}.{table_name} via Supabase. "
            "Check Supabase Settings → Data API → Exposed schemas includes 'uniguide_app' (and 'uniguide'), "
            "and the backend is using a service_role key."
        ) from ex


def _to_int(v):
    if v is None or v == "":
        return None
    try:
        return int(v)
    except Exception:
        return None


def _clamp_int(v, lo, hi, default):
    i = _to_int(v)
    if i is None:
        return default
    return max(lo, min(i, hi))


def _summarize_profile_for_prompt(student_ctx: dict, intake: dict):
    # Keep prompt tight. We can expand later.
    ap = student_ctx.get("academic_profile") or {}
    student = ap.get("student") or {}
    subjects = ap.get("subjects") or []
    offers = student_ctx.get("university_choices") or []

    subj_lines = []
    for s in subjects[:12]:
        name = (s.get("subjectName") or s.get("subject") or "").strip()
        if not name:
            continue
        cur = (s.get("currentGrade") or "").strip()
        tgt = (s.get("targetGrade") or "").strip()
        meg = (s.get("minimumExpectedGrade") or s.get("meg") or "").strip()
        bits = [name]
        if cur:
            bits.append(f"Current {cur}")
        if tgt:
            bits.append(f"Target {tgt}")
        if meg:
            bits.append(f"MEG {meg}")
        subj_lines.append(" - " + " / ".join(bits))

    offer_lines = []
    for o in offers[:5]:
        uni = (o.get("universityName") or "").strip()
        course = (o.get("courseTitle") or "").strip()
        offer_lines.append(f" - #{o.get('ranking')}: {uni} — {course}".strip())

    return {
        "student": {
            "name": student.get("name"),
            "school": student.get("school"),
            "year_group": student.get("yearGroup"),
        },
        "subjects_summary": "\n".join(subj_lines) if subj_lines else "(no subjects found)",
        "current_choices_summary": "\n".join(offer_lines) if offer_lines else "(none yet)",
        "intake": intake or {},
    }


def _first_name_from_ctx(prompt_ctx: dict):
    try:
        nm = ((prompt_ctx.get("student") or {}).get("name") or "").strip()
        if not nm:
            return ""
        return nm.split()[0]
    except Exception:
        return ""


def _alex_system_prompt_from_ctx(prompt_ctx: dict):
    student = prompt_ctx.get("student") or {}
    subjects_summary = prompt_ctx.get("subjects_summary") or ""
    intake = prompt_ctx.get("intake") or {}

    # Keep the injected "subjects" compact.
    subjects_line = ""
    if isinstance(subjects_summary, str) and subjects_summary and subjects_summary != "(no subjects found)":
        # subjects_summary is formatted as lines like " - Biology / Current ..."
        names = []
        for line in subjects_summary.splitlines():
            s = line.strip().lstrip("-").strip()
            if not s:
                continue
            name = s.split("/")[0].strip()
            if name:
                names.append(name)
        if names:
            subjects_line = ", ".join(names[:6]) + ("…" if len(names) > 6 else "")

    prefs_json = json.dumps(intake or {}, ensure_ascii=False)
    return (
        _ALEX_SYSTEM_PROMPT
        .replace("{{STUDENT_PREFERENCE_JSON}}", prefs_json)
        .replace("{{student.firstName}}", _first_name_from_ctx(prompt_ctx) or "there")
        .replace("{{student.subjects}}", subjects_line or "")
        .replace("{{student.yearGroup}}", str(student.get("year_group") or ""))
        .replace("{{student.school}}", str(student.get("school") or ""))
        .replace("{{student.predictedGrades}}", "")
    )


def _pretty_pref(v):
    s = str(v or "").strip()
    if not s:
        return ""
    s = s.replace("_", " ").replace("-", " ").strip()
    return " ".join([w[:1].upper() + w[1:] if w else "" for w in s.split()])


def _alex_opening_message(prompt_ctx: dict):
    first = _first_name_from_ctx(prompt_ctx) or "there"
    intake = prompt_ctx.get("intake") or {}
    interests = intake.get("interests") if isinstance(intake.get("interests"), list) else []
    interests = [_pretty_pref(x) for x in interests if str(x).strip()]
    distance = _pretty_pref(intake.get("distance"))
    campus = _pretty_pref(intake.get("campus_type"))

    bits = []
    if interests:
        bits.append(f"you’re into {', '.join(interests[:3])}")
    if distance and distance.lower() != "no preference":
        bits.append(f"you’re thinking about staying {distance.lower()}")
    if campus and campus.lower() != "no preference":
        bits.append(f"you prefer a {campus.lower()} vibe")

    prefs_line = ""
    if bits:
        prefs_line = " I’ve seen your preferences — " + ", ".join(bits) + "."

    return (
        f"Hey {first} — I’m Alex.{prefs_line} "
        "Before we get into courses and league tables and all that: what’s the thing you’re actually most uncertain about right now?"
    )


def _looks_like_yes(text: str):
    s = (text or "").strip().lower()
    if not s:
        return False
    # Keep it strict: only treat short, affirmative confirmations as "yes".
    return s in {
        "yes",
        "y",
        "yep",
        "yeah",
        "yup",
        "correct",
        "exactly",
        "that's right",
        "thats right",
        "right",
        "sounds right",
        "spot on",
        "that’s right",
    }


def _looks_like_no(text: str):
    s = (text or "").strip().lower()
    if not s:
        return False
    return s in {
        "no",
        "n",
        "nope",
        "nah",
        "not quite",
        "not really",
        "wrong",
    }


def handle_uniguide_chat(*, app, request, jsonify, supabase_client, uniguide_client, OPENAI_API_KEY, get_profile_from_supabase):
    data = request.get_json() or {}
    student_email = (data.get("student_email") or data.get("studentEmail") or "").strip().lower()
    academic_year = (data.get("academic_year") or data.get("academicYear") or "current").strip() or "current"
    session_id = data.get("session_id") or data.get("sessionId")
    message = (data.get("message") or "").strip()
    dataset_release_id = data.get("dataset_release_id") or data.get("datasetReleaseId")
    start_chat = bool(data.get("start_chat") or data.get("startChat"))

    if start_chat:
        # Start with persona opening using preferences + known context.
        message = "__UNIGUIDE_START__"

    if not student_email or "@" not in student_email:
        return jsonify({"success": False, "error": "student_email is required"}), 400
    if not message:
        return jsonify({"success": False, "error": "message is required"}), 400
    if not OPENAI_API_KEY:
        return jsonify({"success": False, "error": "OPENAI_API_KEY not configured"}), 500

    client = uniguide_client or supabase_client
    if not client:
        return jsonify({"success": False, "error": "Supabase is not enabled"}), 500

    # Tables (via public views to avoid schema-selection issues and naming conflicts)
    # Supabase SQL must define:
    # - public.uniguide_app_sessions → uniguide_app.sessions
    # - public.uniguide_app_messages → uniguide_app.messages
    # - public.uniguide_app_student_profiles → uniguide_app.student_profiles
    # - public.uniguide_app_suggestions → uniguide_app.suggestions
    sessions_tbl = client.table("uniguide_app_sessions")
    messages_tbl = client.table("uniguide_app_messages")
    profiles_tbl = client.table("uniguide_app_student_profiles")
    suggestions_tbl = client.table("uniguide_app_suggestions")

    # Ensure profile exists
    try:
        pr = (
            profiles_tbl.select("*")
            .eq("student_email", student_email)
            .eq("academic_year", academic_year)
            .limit(1)
            .execute()
        )
        profile_row = (pr.data or [None])[0]
        if not profile_row:
            ins = profiles_tbl.insert(
                {
                    "student_email": student_email,
                    "academic_year": academic_year,
                    "intake": {},
                    "intake_version": 1,
                }
            ).execute()
            profile_row = (ins.data or [None])[0] or {"intake": {}}
    except Exception as e:
        app.logger.warning(f"[UniGuide] profile init failed: {e}")
        profile_row = {"intake": {}}

    intake = profile_row.get("intake") if isinstance(profile_row, dict) else {}
    if not isinstance(intake, dict):
        intake = {}

    # Session create/load
    try:
        if session_id:
            sr = sessions_tbl.select("*").eq("id", session_id).limit(1).execute()
            if not (sr.data or []):
                session_id = None

        if not session_id:
            model = os.getenv("UNIGUIDE_OPENAI_MODEL") or "gpt-4o-mini"
            si = sessions_tbl.insert(
                {
                    "student_email": student_email,
                    "academic_year": academic_year,
                    "mode": "chat",
                    "status": "active",
                    "dataset_release_id": dataset_release_id,
                    "prompt_version": "uniguide-chat-v1",
                    "model": model,
                }
            ).execute()
            session_row = (si.data or [None])[0]
            session_id = session_row.get("id") if isinstance(session_row, dict) else None
        if not session_id:
            raise Exception("Failed to create session")
    except Exception as e:
        app.logger.error(f"[UniGuide] session init failed: {e}")
        return jsonify({"success": False, "error": "Failed to create session"}), 500

    # Persist user message
    if message != "__UNIGUIDE_START__":
        try:
            messages_tbl.insert(
                {
                    "session_id": session_id,
                    "role": "user",
                    "content": message,
                    "meta": {"ts": _now_iso()},
                }
            ).execute()
        except Exception as e:
            app.logger.warning(f"[UniGuide] message write failed: {e}")

    # Fetch last N messages for context
    history = []
    try:
        hr = (
            messages_tbl.select("role,content")
            .eq("session_id", session_id)
            .order("created_at", desc=False)
            .limit(20)
            .execute()
        )
        for r in (hr.data or []):
            role = r.get("role")
            content = r.get("content")
            if role in ("user", "assistant", "system") and content:
                history.append({"role": role, "content": content})
    except Exception as e:
        app.logger.warning(f"[UniGuide] history load failed: {e}")

    # Student context injection from Academic Profile (if available)
    student_ctx = {
        "student_email": student_email,
        "academic_year": academic_year,
        "academic_profile": None,
        "university_choices": [],
    }
    try:
        if get_profile_from_supabase:
            prof = get_profile_from_supabase(student_email, academic_year)
            if prof:
                student_ctx["academic_profile"] = {
                    "student": prof.get("student"),
                    "subjects": prof.get("subjects"),
                    "updatedAt": prof.get("updatedAt"),
                    "dataSource": prof.get("dataSource"),
                }
                offers = (prof.get("student") or {}).get("universityOffers") or []
                if isinstance(offers, list):
                    student_ctx["university_choices"] = offers[:5]
    except Exception as e:
        app.logger.warning(f"[UniGuide] academic profile context load failed: {e}")

    prompt_ctx = _summarize_profile_for_prompt(student_ctx, intake)
    alex_system = _alex_system_prompt_from_ctx(prompt_ctx)

    # --- Conversation gating + confirmation checkpoint ---
    MIN_USER_TURNS = 4
    MIN_TOTAL_TURNS = 8

    user_turns = 0
    assistant_turns = 0
    for m in history:
        try:
            if m.get("role") == "user":
                user_turns += 1
            elif m.get("role") == "assistant":
                assistant_turns += 1
        except Exception:
            pass
    total_turns = user_turns + assistant_turns

    ug_confirm_pending = bool((intake or {}).get("ug_confirm_pending"))
    ug_confirmed = bool((intake or {}).get("ug_confirmed"))
    gate_met = (user_turns >= MIN_USER_TURNS) and (total_turns >= MIN_TOTAL_TURNS)

    intake_patch_app = {}
    if ug_confirm_pending and not ug_confirmed:
        if _looks_like_yes(message):
            intake_patch_app = {"ug_confirm_pending": False, "ug_confirmed": True}
            ug_confirm_pending = False
            ug_confirmed = True
        elif _looks_like_no(message):
            # Reset; Alex should correct the summary and re-confirm.
            intake_patch_app = {"ug_confirm_pending": False, "ug_confirmed": False}
            ug_confirm_pending = False
            ug_confirmed = False

    # When we reach the minimum exchange threshold, force a short paraphrase + confirm step.
    if gate_met and (not ug_confirmed) and (not ug_confirm_pending):
        intake_patch_app = {**intake_patch_app, "ug_confirm_pending": True, "ug_confirmed": False}
        ug_confirm_pending = True

    if intake_patch_app:
        try:
            merged = {**(intake or {}), **intake_patch_app}
            profiles_tbl.update({"intake": merged, "updated_at": _now_iso()}).eq("student_email", student_email).eq(
                "academic_year", academic_year
            ).execute()
            intake = merged
        except Exception as e:
            app.logger.warning(f"[UniGuide] intake app patch write failed: {e}")

    allow_recommendations = gate_met and ug_confirmed
    app_state = {
        "user_turns": user_turns,
        "assistant_turns": assistant_turns,
        "total_turns": total_turns,
        "min_user_turns": MIN_USER_TURNS,
        "min_total_turns": MIN_TOTAL_TURNS,
        "gate_met": gate_met,
        "confirm_pending": ug_confirm_pending,
        "confirmed": ug_confirmed,
        "allow_recommendations": allow_recommendations,
    }

    # Start-chat mode: return a personalised opening immediately (no RAG, no OpenAI).
    if message == "__UNIGUIDE_START__":
        opening = _alex_opening_message(prompt_ctx)
        if opening:
            try:
                messages_tbl.insert(
                    {
                        "session_id": session_id,
                        "role": "assistant",
                        "content": opening,
                        "meta": {"ts": _now_iso(), "mode": "opening"},
                    }
                ).execute()
            except Exception as e:
                app.logger.warning(f"[UniGuide] assistant opening write failed: {e}")

        return jsonify(
            {
                "success": True,
                "session_id": session_id,
                "assistant_message": opening,
                "suggestions": [],
                "retrieved_count": 0,
                "search_used": {"q": None, "subject_code": None, "min_tariff": None, "max_tariff": None},
            }
        )

    # --- OpenAI: step 1 planner (extract search params + optional intake patch) ---
    try:
        import openai

        openai.api_key = OPENAI_API_KEY
        model = os.getenv("UNIGUIDE_OPENAI_MODEL") or "gpt-4o-mini"

        planner_system = (
            alex_system
            + "\n\n"
            + "You are UniGuide's planner.\n"
            "Your job: interpret the student's message and context, and output STRICT JSON ONLY.\n"
            "JSON schema:\n"
            "  assistant_message: string (short, friendly, 1-2 questions max)\n"
            "  intake_patch: object (merge into intake; can be empty)\n"
            "  search_params: { q: string|null, subject_code: string|null, min_tariff: int|null, max_tariff: int|null }\n"
            "Rules:\n"
            "- Use provided subjects/grades if relevant. Don't re-ask obvious things.\n"
            "- Prefer setting q to 1-3 concise keywords that match course titles (e.g. 'Psychology', 'Computer Science').\n"
            "- Only set q=null if the student message is completely unrelated to course search.\n"
            "- subject_code is optional; only set if confidently known.\n"
        )

        # Special "start" mode: no student message beyond "start".
        planner_user = (
            "APP STATE (read-only):\n"
            f"{json.dumps(app_state, ensure_ascii=False)}\n\n"
            "CONTEXT (read-only):\n"
            f"{json.dumps(prompt_ctx, ensure_ascii=False)}\n\n"
            "STUDENT MESSAGE:\n"
            f"{'' if message == '__UNIGUIDE_START__' else message}\n\n"
            "Return JSON only."
        )

        planner_resp = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": planner_system},
                {"role": "user", "content": planner_user},
            ],
            temperature=0.4,
            max_tokens=700,
        )

        planner_text = planner_resp.choices[0].message["content"]
        plan = _json_loads_maybe(planner_text) or {}
    except Exception as e:
        app.logger.error(f"[UniGuide] OpenAI planner error: {e}")
        plan = {}

    assistant_message = (plan.get("assistant_message") or "").strip()
    intake_patch = plan.get("intake_patch") if isinstance(plan.get("intake_patch"), dict) else {}
    sp = plan.get("search_params") if isinstance(plan.get("search_params"), dict) else {}

    q_plan = (sp.get("q") or "").strip() or None
    subject_code = (sp.get("subject_code") or "").strip() or None
    min_tariff = _to_int(sp.get("min_tariff"))
    max_tariff = _to_int(sp.get("max_tariff"))

    # Fallback: ensure we have a usable query for retrieval when possible.
    q_fallback = None
    q = q_plan
    if not q:
        q_fallback = _derive_q_from_message(message)
        q = q_fallback

    # Last resort: use a short slice of the message (better than nothing).
    if not q and message:
        q = " ".join(str(message).strip().split()[:4]).strip() or None

    try:
        app.logger.info(f"[UniGuide] planner q={q_plan!r} fallback={q_fallback!r} final_q={q!r} subject_code={subject_code!r}")
    except Exception:
        pass

    # Merge intake patch into profile (best-effort)
    if intake_patch:
        try:
            merged = {**(intake or {}), **intake_patch}
            profiles_tbl.update(
                {"intake": merged, "updated_at": _now_iso()}
            ).eq("student_email", student_email).eq("academic_year", academic_year).execute()
            intake = merged
        except Exception as e:
            app.logger.warning(f"[UniGuide] intake patch write failed: {e}")

    # Retrieve courses (RAG retrieval). Skip in start mode.
    retrieved = []
    if (not allow_recommendations) and q:
        # Hard gate: do not retrieve courses until we've had enough conversation AND the student confirms the summary.
        q = None
        subject_code = None
        min_tariff = None
        max_tariff = None

    if q and message != "__UNIGUIDE_START__":
        try:
            params = {
                "q": q,
                "subject_code": subject_code,
                "min_tariff": min_tariff,
                "max_tariff": max_tariff,
                "lim": 12,
                "off": 0,
                "dataset_release_id": dataset_release_id,
            }
            rr = client.rpc("uniguide_search_courses", params).execute()
            retrieved = rr.data or []

            # If nothing came back, try a simplified query once (common with long free-text).
            if not retrieved and isinstance(q, str) and len(q) > 24:
                q2 = q.split(",")[0].strip()
                q2 = " ".join(q2.split()[:3]).strip()
                if q2 and q2 != q:
                    params["q"] = q2
                    rr2 = client.rpc("uniguide_search_courses", params).execute()
                    retrieved = rr2.data or []
        except Exception as e:
            app.logger.warning(f"[UniGuide] retrieval RPC failed: {e}")
            retrieved = []

    try:
        app.logger.info(f"[UniGuide] retrieved_count={len(retrieved)} q_used={q!r}")
    except Exception:
        pass

    # --- OpenAI: step 2 response + suggestions ---
    try:
        import openai

        openai.api_key = OPENAI_API_KEY
        model = os.getenv("UNIGUIDE_OPENAI_MODEL") or "gpt-4o-mini"

        responder_system = (
            alex_system
            + "\n\n"
            + "You are UniGuide, an expert UK university/course advisor.\n"
            "Return STRICT JSON ONLY with keys:\n"
            "  assistant_message: string (helpful answer + 1 targeted question)\n"
            "  suggestions: array of up to 6 items (only when APP_STATE.allow_recommendations is true):\n"
            "    { course_key: string, band: 'aspirational'|'solid'|'safer'|'other', reason_short: string }\n"
            "  ready_to_recommend: boolean (true only when you are genuinely ready to surface course suggestions)\n"
            "  extracted_profile: object|null (only when ready_to_recommend is true)\n"
            "Rules:\n"
            "- NEVER include URLs/links inside assistant_message. If suggesting courses, use suggestions[] only.\n"
            "- Do NOT invent course_keys; only use those provided.\n"
            "- Keep reasons short (<=140 chars).\n"
            "- If RETRIEVED COURSES is empty, do NOT claim that no courses exist. Ask for a clearer subject keyword and suggest using Search Courses.\n"
            "- If APP_STATE.confirm_pending is true: paraphrase what the student has said so far (2–4 bullets), then ask them to confirm (yes/no). Do not suggest courses.\n"
            "- If APP_STATE.allow_recommendations is false: do not suggest courses. Ask 1 targeted follow-up question based on what's missing.\n"
            "- You must avoid the banned filler phrases from your persona prompt.\n"
        )

        responder_user = (
            "APP STATE (read-only):\n"
            f"{json.dumps(app_state, ensure_ascii=False)}\n\n"
            "CONTEXT (read-only):\n"
            f"{json.dumps(_summarize_profile_for_prompt(student_ctx, intake), ensure_ascii=False)}\n\n"
            "RETRIEVED COURSES (read-only):\n"
            f"{json.dumps(retrieved[:12], ensure_ascii=False)}\n\n"
            "CONVERSATION SO FAR (most recent last):\n"
            f"{json.dumps(history[-12:], ensure_ascii=False)}\n\n"
            "Return JSON only."
        )

        resp = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": responder_system},
                {"role": "user", "content": responder_user},
            ],
            temperature=0.5,
            max_tokens=900,
        )

        out_text = resp.choices[0].message["content"]
        out = _json_loads_maybe(out_text) or {}
    except Exception as e:
        app.logger.error(f"[UniGuide] OpenAI responder error: {e}")
        out = {}

    final_message = (out.get("assistant_message") or assistant_message or "").strip()
    suggestions = out.get("suggestions") if isinstance(out.get("suggestions"), list) else []
    ready_to_recommend = bool(out.get("ready_to_recommend"))
    extracted_profile = out.get("extracted_profile") if isinstance(out.get("extracted_profile"), dict) else None

    # Hard safety: if the app gate is not open, drop any suggestions the model tried to return.
    if not allow_recommendations:
        suggestions = []
        ready_to_recommend = False
        extracted_profile = None

    # Guardrail: don't let the model conclude "no courses exist" when retrieval is empty.
    if (not retrieved) and q:
        if not final_message or ("no specific course" in final_message.lower()) or ("no courses" in final_message.lower()):
            final_message = (
                f"I couldn’t match many course titles for “{q}” yet. "
                "Can you tell me the subject area you want to explore (1–2 keywords), and any must-haves like location or tariff range? "
                "You can also try the Search Courses tab for a quick list."
            )

    # Persist assistant message
    if final_message:
        try:
            messages_tbl.insert(
                {
                    "session_id": session_id,
                    "role": "assistant",
                    "content": final_message,
                    "meta": {"ts": _now_iso(), "q": q, "subject_code": subject_code},
                }
            ).execute()
        except Exception as e:
            app.logger.warning(f"[UniGuide] assistant message write failed: {e}")

    # Upsert suggestions (best-effort; ignore duplicates via unique partial index)
    saved_suggestions = []
    for s in suggestions[:6]:
        try:
            course_key = (s.get("course_key") or "").strip()
            if not course_key:
                continue
            row = {
                "student_email": student_email,
                "academic_year": academic_year,
                "course_key": course_key,
                "source": "chat",
                "band": s.get("band"),
                "reason_short": (s.get("reason_short") or "").strip()[:180],
                "session_id": session_id,
            }
            suggestions_tbl.insert(row).execute()
            saved_suggestions.append(row)
        except Exception:
            # Likely duplicate active suggestion; ignore for now.
            pass

    # Enrich suggestions with course card details for the frontend buttons/links.
    retrieved_by_key = {}
    for c in (retrieved or [])[:50]:
        try:
            k = (c or {}).get("course_key")
            if k:
                retrieved_by_key[str(k)] = c
        except Exception:
            pass

    suggestions_ui = []
    for s in saved_suggestions:
        try:
            k = str(s.get("course_key") or "").strip()
            card = retrieved_by_key.get(k) or {}
            suggestions_ui.append(
                {
                    **s,
                    "title": card.get("title") or card.get("course_title") or card.get("course_name"),
                    "institution_name": card.get("institution_name") or card.get("provider_name") or card.get("university_name"),
                    "course_url": card.get("course_url") or card.get("url") or card.get("course_link"),
                    "tariff_typical": card.get("tariff_typical") or card.get("tariff"),
                    "tef_overall_rating": card.get("tef_overall_rating") or card.get("tef"),
                }
            )
        except Exception:
            suggestions_ui.append(s)

    return (
        jsonify(
            {
                "success": True,
                "session_id": session_id,
                "assistant_message": final_message,
                "search_used": {"q": q, "subject_code": subject_code, "min_tariff": min_tariff, "max_tariff": max_tariff},
                "retrieved_count": len(retrieved),
                "suggestions_saved": len(saved_suggestions),
                "suggestions": suggestions_ui,
                "ready_to_recommend": ready_to_recommend,
                "extracted_profile": extracted_profile,
                "app_state": app_state,
            }
        ),
        200,
    )

